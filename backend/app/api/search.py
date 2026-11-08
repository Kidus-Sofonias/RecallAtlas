import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document, ProcessingStatus
from app.models.question import Question, QualityStatus
from app.models.resource import Resource
from app.models.taxonomy import Subject

router = APIRouter(prefix='/api/v1/search', tags=['search'])
_TOKEN = re.compile(r'\w+', re.UNICODE)


def _tokens(query: str) -> list[str]:
    return _TOKEN.findall(query.casefold())[:10]


def _search_hits(db: Session, query: str, limit: int) -> list[dict[str, str | float]]:
    tokens = _tokens(query)
    if not tokens:
        return []

    if db.get_bind().dialect.name == 'postgresql':
        ts_query = ' & '.join(f'{token}:*' for token in tokens)
        statement = text(
            """
            SELECT 'question' AS item_type, CAST(q.id AS TEXT) AS item_id,
                CAST(d.id AS TEXT) AS document_id,
                ts_rank_cd(to_tsvector('simple', COALESCE(q.extracted_text, '')),
                    to_tsquery('simple', :query)) * 1.0
                + ts_rank_cd(to_tsvector('simple', COALESCE(d.title, '')),
                    to_tsquery('simple', :query)) * 5.0
                + ts_rank_cd(to_tsvector('simple', COALESCE(s.name, '')),
                    to_tsquery('simple', :query)) * 3.0
                + CASE WHEN CAST(d.academic_year AS TEXT) = :raw_query THEN 2.0 ELSE 0.0 END
                AS relevance
            FROM questions q
            JOIN documents d ON d.id = q.document_id
            LEFT JOIN subjects s ON s.id = d.subject_id
            WHERE q.quality_status = 'reliable'
                AND d.processing_status = 'completed'
                AND (
                    to_tsvector('simple', COALESCE(q.extracted_text, '')) @@ to_tsquery('simple', :query)
                    OR to_tsvector('simple', COALESCE(d.title, '')) @@ to_tsquery('simple', :query)
                    OR to_tsvector('simple', COALESCE(s.name, '')) @@ to_tsquery('simple', :query)
                    OR CAST(d.academic_year AS TEXT) = :raw_query
                )
            UNION ALL
            SELECT 'article' AS item_type, CAST(r.id AS TEXT) AS item_id, '' AS document_id,
                ts_rank_cd(to_tsvector('simple',
                    COALESCE(r.title, '') || ' ' || COALESCE(r.summary, '') || ' ' || COALESCE(r.body, '')),
                    to_tsquery('simple', :query)) AS relevance
            FROM resources r
            WHERE r.status = 'published'
                AND to_tsvector('simple',
                    COALESCE(r.title, '') || ' ' || COALESCE(r.summary, '') || ' ' || COALESCE(r.body, ''))
                    @@ to_tsquery('simple', :query)
            ORDER BY relevance DESC
            LIMIT :limit
            """
        )
        rows = db.execute(
            statement,
            {'query': ts_query, 'raw_query': query.strip(), 'limit': limit},
        ).mappings().all()
        return [
            {
                'type': str(row['item_type']),
                'id': str(row['item_id']),
                'document_id': str(row['document_id'] or ''),
                'relevance': float(row['relevance']),
            }
            for row in rows
        ]

    raise RuntimeError(f"Search is not configured for the '{db.get_bind().dialect.name}' database.")


def _preference_score(
    grade: int | None,
    subject_id: uuid.UUID | None,
    preferred_grade: int | None,
    preferred_subject_ids: set[str],
) -> float:
    score = 0.0
    if preferred_grade and grade == preferred_grade:
        score += 1.6
    elif preferred_grade and grade == preferred_grade - 1:
        score += 0.8
    if subject_id and subject_id in preferred_subject_ids:
        score += 1.8
    return score


def _question_rows(
    db: Session,
    hits: list[dict[str, str | float]] | None,
    *,
    grade: int | None,
    subject_id: str | None,
    preferred_grade: int | None,
    preferred_subject_ids: set[str],
    limit: int,
) -> list[dict[str, object]]:
    query = (
        db.query(Question, Document, Subject)
        .join(Document, Document.id == Question.document_id)
        .outerjoin(Subject, Subject.id == Document.subject_id)
        .filter(
            Question.quality_status == QualityStatus.reliable,
            Document.processing_status == ProcessingStatus.completed,
        )
    )
    if grade is not None:
        query = query.filter(Document.grade == grade)
    if subject_id is not None:
        query = query.filter(Document.subject_id == subject_id)

    relevance = {str(hit['id']): float(hit['relevance']) for hit in hits or [] if hit['type'] == 'question'}
    if hits is not None:
        if not relevance:
            return []
        query = query.filter(Question.id.in_([uuid.UUID(item_id) for item_id in relevance]))
    else:
        query = query.order_by(Document.created_at.desc(), Question.created_at.desc())

    rows = query.limit(max(limit * 20, limit) if hits is not None else limit).all()
    items = [
        {
            'id': str(question.id),
            'document_id': str(document.id),
            'page': question.source_page_start,
            'snippet': question.extracted_text[:200],
            'title': document.title or 'Untitled test',
            'grade': document.grade,
            'academic_year': document.academic_year,
            'subject_id': str(document.subject_id) if document.subject_id else None,
            'subject': subject.name if subject else None,
            'relevance': relevance.get(str(question.id), 0.0),
        }
        for question, document, subject in rows
    ]
    if hits is not None:
        items.sort(
            key=lambda item: (
                _preference_score(
                    item['grade'] if isinstance(item['grade'], int) else None,
                    item['subject_id'] if isinstance(item['subject_id'], str) else None,
                    preferred_grade,
                    preferred_subject_ids,
                ),
                float(item['relevance']),
            ),
            reverse=True,
        )
    return items[:limit]


def _paper_rows(
    db: Session,
    hits: list[dict[str, str | float]] | None,
    *,
    query: str,
    grade: int | None,
    subject_id: uuid.UUID | None,
    preferred_grade: int | None,
    preferred_subject_ids: set[str],
    limit: int,
) -> list[dict[str, object]]:
    query_builder = (
        db.query(Document, Subject)
        .join(Subject, Subject.id == Document.subject_id, isouter=True)
        .filter(
            Document.processing_status == ProcessingStatus.completed,
            db.query(Question.id).filter(
                Question.document_id == Document.id,
                Question.quality_status == QualityStatus.reliable,
            ).exists(),
        )
    )
    if grade is not None:
        query_builder = query_builder.filter(Document.grade == grade)
    if subject_id is not None:
        query_builder = query_builder.filter(Document.subject_id == subject_id)

    if hits is not None:
        document_ids = {
            str(hit['document_id'])
            for hit in hits
            if hit['type'] == 'question' and hit['document_id']
        }
        if not document_ids:
            return []
        query_builder = query_builder.filter(Document.id.in_([uuid.UUID(item_id) for item_id in document_ids]))
    elif query:
        pattern = f'%{query}%'
        query_builder = query_builder.filter(Document.title.ilike(pattern))
    else:
        query_builder = query_builder.order_by(Document.created_at.desc())

    rows = query_builder.limit(limit * 5 if hits is not None else limit).all()
    items = [
        {
            'id': str(document.id),
            'title': document.title or 'Untitled test',
            'grade': document.grade,
            'academic_year': document.academic_year,
            'subject_id': str(document.subject_id) if document.subject_id else None,
            'subject': subject.name if subject else None,
            'posted_at': document.created_at.isoformat() if document.created_at else None,
        }
        for document, subject in rows
    ]
    if hits is not None:
        hit_ids = {str(hit['document_id']) for hit in hits if hit['type'] == 'question'}
        items.sort(
            key=lambda item: (
                _preference_score(
                    item['grade'] if isinstance(item['grade'], int) else None,
                    item['subject_id'] if isinstance(item['subject_id'], str) else None,
                    preferred_grade,
                    preferred_subject_ids,
                ),
                item['id'] in hit_ids,
                item['posted_at'] or '',
            ),
            reverse=True,
        )
    return items[:limit]


def _article_rows(
    db: Session,
    hits: list[dict[str, str | float]] | None,
    *,
    subject_id: uuid.UUID | None,
    preferred_subject_ids: set[str],
    limit: int,
) -> list[dict[str, object]]:
    query = (
        db.query(Resource, Subject)
        .outerjoin(Subject, Subject.id == Resource.subject_id)
        .filter(Resource.status == 'published')
    )
    if subject_id is not None:
        query = query.filter(Resource.subject_id == subject_id)
    relevance = {str(hit['id']): float(hit['relevance']) for hit in hits or [] if hit['type'] == 'article'}
    if hits is not None:
        if not relevance:
            return []
        query = query.filter(Resource.id.in_([uuid.UUID(item_id) for item_id in relevance]))
    else:
        query = query.order_by(Resource.created_at.desc())
    rows = query.limit(limit * 10 if hits is not None else limit).all()
    items = [
        {
            'id': str(resource.id),
            'title': resource.title,
            'summary': resource.summary,
            'subject_id': str(resource.subject_id) if resource.subject_id else None,
            'subject': subject.name if subject else None,
            'posted_at': resource.created_at.isoformat() if resource.created_at else None,
            'relevance': relevance.get(str(resource.id), 0.0),
        }
        for resource, subject in rows
    ]
    if hits is not None:
        items.sort(
            key=lambda item: (
                item['subject_id'] in preferred_subject_ids,
                float(item['relevance']),
            ),
            reverse=True,
        )
    return items[:limit]


@router.get('')
def search(
    q: str | None = Query(default=None, max_length=200),
    grade: int | None = Query(default=None, ge=9, le=12),
    subject_id: uuid.UUID | None = None,
    preferred_grade: int | None = Query(default=None, ge=9, le=12),
    preferred_subject_ids: list[str] = Query(default=[]),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    normalized_query = (q or '').strip()
    if not normalized_query and grade is None and subject_id is None:
        raise HTTPException(422, 'A search phrase or grade or subject filter is required.')
    hits = _search_hits(db, normalized_query, max(limit * 20, 200)) if normalized_query else None
    items = _question_rows(
        db,
        hits,
        grade=grade,
        subject_id=subject_id,
        preferred_grade=preferred_grade,
        preferred_subject_ids=set(preferred_subject_ids),
        limit=limit,
    )
    return [
        {
            'id': item['id'],
            'document_id': item['document_id'],
            'page': item['page'],
            'snippet': item['snippet'],
            'title': item['title'],
            'grade': item['grade'],
            'academic_year': item['academic_year'],
            'subject_id': item['subject_id'],
            'subject': item['subject'],
        }
        for item in items
    ]


@router.get('/explore')
def explore_search(
    q: str | None = Query(default=None, max_length=200),
    grade: int | None = Query(default=None, ge=9, le=12),
    subject_id: uuid.UUID | None = None,
    preferred_grade: int | None = Query(default=None, ge=9, le=12),
    preferred_subject_ids: list[str] = Query(default=[]),
    limit: int = Query(default=12, ge=1, le=30),
    db: Session = Depends(get_db),
):
    normalized_query = (q or '').strip()
    hits = _search_hits(db, normalized_query, max(limit * 20, 200)) if normalized_query else None
    subject_preferences = set(preferred_subject_ids)
    questions = _question_rows(
        db,
        hits,
        grade=grade,
        subject_id=subject_id,
        preferred_grade=preferred_grade,
        preferred_subject_ids=subject_preferences,
        limit=limit,
    )
    papers = _paper_rows(
        db,
        hits,
        query=normalized_query,
        grade=grade,
        subject_id=subject_id,
        preferred_grade=preferred_grade,
        preferred_subject_ids=subject_preferences,
        limit=limit,
    )
    articles = _article_rows(
        db,
        hits,
        subject_id=subject_id,
        preferred_subject_ids=subject_preferences,
        limit=limit,
    )
    return {
        'questions': questions,
        'papers': papers,
        'articles': articles,
        'query': normalized_query,
    }


@router.get('/suggestions')
def search_suggestions(
    q: str = Query(min_length=2, max_length=200),
    preferred_grade: int | None = Query(default=None, ge=9, le=12),
    preferred_subject_ids: list[str] = Query(default=[]),
    limit: int = Query(default=8, ge=1, le=12),
    db: Session = Depends(get_db),
):
    normalized_query = q.strip()
    if len(normalized_query) < 2:
        return []
    hits = _search_hits(db, normalized_query, max(limit * 8, 24))
    subject_preferences = set(preferred_subject_ids)
    suggestions: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    question_hits = [hit for hit in hits if hit['type'] == 'question']
    if question_hits:
        questions = _question_rows(
            db,
            question_hits,
            grade=None,
            subject_id=None,
            preferred_grade=preferred_grade,
            preferred_subject_ids=subject_preferences,
            limit=limit,
        )
        for item in questions:
            key = ('question', str(item['id']))
            if key in seen:
                continue
            seen.add(key)
            detail = 'Question'
            if item['grade']:
                detail += f" · Grade {item['grade']}"
            if item['academic_year']:
                detail += f" · {item['academic_year']}"
            suggestions.append({
                'type': 'question',
                'id': str(item['id']),
                'label': str(item['title']),
                'detail': detail,
                'href': f"/questions/{item['id']}",
            })

    paper_hits = [hit for hit in hits if hit['type'] == 'question']
    if paper_hits:
        papers = _paper_rows(
            db,
            paper_hits,
            query=normalized_query,
            grade=None,
            subject_id=None,
            preferred_grade=preferred_grade,
            preferred_subject_ids=subject_preferences,
            limit=limit,
        )
        for item in papers:
            key = ('paper', str(item['id']))
            if key in seen:
                continue
            seen.add(key)
            detail = 'Past paper'
            if item['grade']:
                detail += f" · Grade {item['grade']}"
            if item['academic_year']:
                detail += f" · {item['academic_year']}"
            suggestions.append({
                'type': 'paper',
                'id': str(item['id']),
                'label': str(item['title']),
                'detail': detail,
                'href': f"/documents/{item['id']}",
            })

    article_hits = [hit for hit in hits if hit['type'] == 'article']
    if article_hits:
        articles = _article_rows(
            db,
            article_hits,
            subject_id=None,
            preferred_subject_ids=subject_preferences,
            limit=limit,
        )
        for item in articles:
            key = ('article', str(item['id']))
            if key in seen:
                continue
            seen.add(key)
            suggestions.append({
                'type': 'article',
                'id': str(item['id']),
                'label': str(item['title']),
                'detail': str(item['summary']),
                'href': f"/articles/{item['id']}",
            })

    return suggestions[:limit]

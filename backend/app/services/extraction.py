import io
import json
import re
import threading
import uuid
import zipfile
from datetime import datetime, timezone

from PIL import Image, UnidentifiedImageError
from docx import Document as DocxDocument
from pptx import Presentation

from app.db.session import SessionLocal
from app.models.document import Document, ProcessingStatus
from app.models.job import JobStatus, ProcessingJob
from app.models.question import QualityStatus, Question
from app.storage.files import read_bytes

EXTRACTION_VERSION = '3'
_ocr_engine = None
_ocr_lock = threading.Lock()

QUESTION_START = re.compile(r'^\s*(?:Q(?:uestion)?\s*)?(\d{1,3})\s*[.)]\s+\S', re.IGNORECASE)
SECTION_HEADING_START = re.compile(r'^\s*[IVXLCDM]{1,6}\.\s+\S', re.IGNORECASE)
CHOICE_LINE = re.compile(r'^\s*(?:\(([A-H])\)|([A-H])[.)])\s+(.+?)\s*$', re.IGNORECASE)
BLANK_MARKERS = re.compile(r'_{2,}|\.{3,}|\[\s*\]')
SHORT_ANSWER_CUES = re.compile(
    r'\b(?:briefly explain|give (?:a )?short answer|in one sentence|state briefly|'
    r'what is|define|list|distinguish|explain|state|describe|identify)\b',
    re.IGNORECASE,
)
TRUE_FALSE_CUES = re.compile(r'\b(?:true or false|write true or false|state whether .* true or false)\b', re.IGNORECASE)
PDF_TEXT_GAP = re.compile(r'=\s*(?:\?|and\b|state\b|$)', re.IGNORECASE)
MATH_OR_DIAGRAM_HINTS = re.compile(
    r'(?i)(?:\b(?:draw|sketch|plot|graph|diagram|figure|equation|function|relation|matrix|domain|range|universe|solve|calculate|derive|evaluate)\b|\b(?:x|y|z|a|b|c|n)\b.*[=+\-*/^]|[≤≥∈∩∪]|\|x\||f\(x\)|R-1|x\^2)'
)
PHYSICS_SOURCE_REVIEW_HINTS = re.compile(
    r'\b(?:free[- ]body|fbd|force|forces|vector|vectors|displacement|resultant|'
    r'acceleration|velocity|friction|tension|normal force|weight)\b',
    re.IGNORECASE,
)
AMBIGUOUS_PHYSICS_ANGLE = re.compile(
    r'\b\d{2,3}\s*(?:°|degrees?)?\s+(?:west|east|north|south)\b',
    re.IGNORECASE,
)
SUBQUESTION_CUES = re.compile(
    r'\b(?:draw|state|find|calculate|solve|explain|describe|prove|show|identify|determine)\b',
    re.IGNORECASE,
)


def detect_upload_mime(data: bytes) -> str:
    if data.startswith(b'%PDF-'):
        return 'application/pdf'
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
            if '[Content_Types].xml' in names and 'word/document.xml' in names:
                return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            if '[Content_Types].xml' in names and 'ppt/presentation.xml' in names:
                return 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    except (zipfile.BadZipFile, OSError):
        pass
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            return Image.MIME.get(image.format or '', '')
    except (UnidentifiedImageError, OSError, ValueError):
        pass
    raise ValueError('The uploaded file is not a supported PDF, Office document, or image.')


def _ocr_text(image: Image.Image) -> tuple[str, float | None, list[dict]]:
    global _ocr_engine
    with _ocr_lock:
        if _ocr_engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
            except ImportError as exc:
                raise RuntimeError('LOCAL_OCR_UNAVAILABLE') from exc

            _ocr_engine = RapidOCR()
        import numpy as np

        result, _ = _ocr_engine(np.asarray(image.convert('RGB')))
    if not result:
        return '', None, []
    lines = []
    confidences = []
    regions = []
    for row in result:
        if len(row) >= 3 and row[1]:
            text = str(row[1])
            lines.append(text)
            try:
                confidence = float(row[2])
                confidences.append(confidence)
            except (TypeError, ValueError):
                confidence = None
            try:
                coordinates = [
                    (float(point[0]), float(point[1]))
                    for point in row[0]
                    if len(point) >= 2
                ]
                if len(coordinates) >= 4:
                    width, height = image.size
                    if width > 0 and height > 0:
                        x_values, y_values = zip(*coordinates)
                        x0 = min(max(min(x_values), 0.0), float(width))
                        y0 = min(max(min(y_values), 0.0), float(height))
                        x1 = min(max(max(x_values), 0.0), float(width))
                        y1 = min(max(max(y_values), 0.0), float(height))
                        if x1 <= x0 or y1 <= y0:
                            continue
                        regions.append({
                            'text': text,
                            'bbox': [
                                round(x0 / width, 6),
                                round(y0 / height, 6),
                                round(x1 / width, 6),
                                round(y1 / height, 6),
                            ],
                            'confidence': confidence,
                        })
            except (TypeError, ValueError, IndexError):
                continue
    regions.sort(key=lambda region: (region['bbox'][1], region['bbox'][0]))
    return '\n'.join(lines), min(confidences) if confidences else None, regions


def _regions_for_candidate(candidate_text: str, regions: list[dict]) -> list[dict]:
    normalized_candidate = ' '.join(candidate_text.split()).casefold()
    return [
        region for region in regions
        if ' '.join(region['text'].split()).casefold() in normalized_candidate
    ]

def _ocr_text_for_candidate(candidate_text: str, page_text: str) -> str | None:
    first_line = candidate_text.splitlines()[0] if candidate_text.splitlines() else ''
    candidate_start = QUESTION_START.match(first_line)
    if not candidate_start:
        return None
    question_number = candidate_start.group(1)
    lines = page_text.splitlines()
    start = next(
        (
            index for index, line in enumerate(lines)
            if (match := QUESTION_START.match(line))
            and match.group(1) == question_number
        ),
        None,
    )
    if start is None:
        return None
    end = next(
        (
            index for index in range(start + 1, len(lines))
            if QUESTION_START.match(lines[index])
        ),
        len(lines),
    )
    return '\n'.join(line for line in lines[start:end] if line.strip()).strip() or None


def _split_candidates(text: str) -> list[str]:
    normalized = text.replace('\r\n', '\n').replace('\r', '\n').strip()
    if not normalized:
        return []
    lines = normalized.splitlines()
    starts = [index for index, line in enumerate(lines) if QUESTION_START.match(line)]
    section_starts = [
        index for index, line in enumerate(lines)
        if SECTION_HEADING_START.match(line)
    ]
    if len(starts) > 1 or (starts and section_starts):
        boundaries = sorted(set(starts + section_starts))
        chunks = []
        if boundaries[0] > 0 and '\n'.join(lines[:boundaries[0]]).strip():
            chunks.append('\n'.join(lines[:boundaries[0]]).strip())
        chunks.extend(
            '\n'.join(lines[start:boundaries[index + 1] if index + 1 < len(boundaries) else len(lines)]).strip()
            for index, start in enumerate(boundaries)
        )
        return [chunk for chunk in chunks if chunk]
    return [chunk.strip() for chunk in re.split(r'\n\s*\n', normalized) if chunk.strip()]


def _question_content(text: str) -> tuple[str, list[dict[str, str]], None]:
    lines = text.splitlines()
    choice_matches = [match for line in lines if (match := CHOICE_LINE.match(line))]
    lowercase_choice_labels = [((match.group(1) or match.group(2) or '')).lower() for match in choice_matches]
    is_subquestion_list = (
        len(choice_matches) >= 2
        and any(label != label.upper() for label in lowercase_choice_labels)
        and any(SUBQUESTION_CUES.search(match.group(3)) for match in choice_matches)
    )

    if len(choice_matches) >= 2 and not is_subquestion_list:
        question_type = 'multiple_choice'
    elif TRUE_FALSE_CUES.search(text) or (
        re.search(r'\btrue\b', text, re.IGNORECASE)
        and re.search(r'\bfalse\b', text, re.IGNORECASE)
    ):
        question_type = 'true_false'
    elif BLANK_MARKERS.search(text):
        question_type = 'fill_in_the_blank'
    elif SHORT_ANSWER_CUES.search(text):
        question_type = 'short_answer'
    else:
        question_type = 'unknown'

    blocks: list[dict[str, str]] = []
    for line in lines:
        match = CHOICE_LINE.match(line)
        if match:
            label = match.group(1) or match.group(2) or ''
            if label.islower():
                blocks.append({'type': 'text', 'text': line})
            else:
                blocks.append({
                    'type': 'choice',
                    'label': label.upper(),
                    'text': match.group(3),
                })
        elif line.strip():
            blocks.append({'type': 'text', 'text': line})
        else:
            blocks.append({'type': 'break', 'text': ''})
    return question_type, blocks, None


def _page_candidates(
    text: str,
    page_number: int | None,
    ocr_confidence: float | None,
    has_visuals: bool,
    ocr_regions: list[dict] | None = None,
    source_image_size: tuple[int, int] | None = None,
    source_ocr_text: str | None = None,
    source_ocr_confidence: float | None = None,
) -> list[dict]:
    raw_candidates = _split_candidates(text)
    candidates = []
    candidate_contexts = []
    active_context = []
    has_numbered_candidates = any(
        candidate.splitlines() and QUESTION_START.match(candidate.splitlines()[0])
        for candidate in raw_candidates
    )
    if has_numbered_candidates:
        for candidate in raw_candidates:
            first_line = candidate.splitlines()[0] if candidate.splitlines() else ''
            if QUESTION_START.match(first_line):
                candidates.append(candidate)
                candidate_contexts.append('\n'.join(active_context).strip() or None)
            else:
                active_context.append(candidate)
    else:
        candidates = raw_candidates
        if len(candidates) > 1 and not QUESTION_START.match(candidates[0].splitlines()[0]):
            page_context = candidates.pop(0)
            candidate_contexts = [page_context] * len(candidates)
        else:
            candidate_contexts = [None] * len(candidates)
    page_provenance = {
        'source_regions': ocr_regions or [],
        'source_coordinate_space': 'normalized_page_image' if ocr_regions else None,
        'source_image_size': list(source_image_size) if ocr_regions and source_image_size else None,
    }
    if source_ocr_confidence is not None:
        page_provenance['source_ocr_confidence'] = source_ocr_confidence
    if not candidates:
        return [{
            'text': '[Text could not be reliably extracted. Review the original source page.]',
            'question_type': 'unknown',
            'content': {
                'blocks': [],
                'source_page': page_number,
                'visual_fallback': True,
                **page_provenance,
            },
            'signals': {
                'ocr_confidence': ocr_confidence,
                'question_type_confidence': None,
                'question_type_method': 'unclassified',
                'requires_review': True,
                'reasons': ['no_readable_text'],
            },
        }]

    result = []
    for candidate, candidate_page_context in zip(candidates, candidate_contexts):
        question_type, blocks, type_confidence = _question_content(candidate)
        reasons = []
        candidate_provenance = dict(page_provenance)
        if candidate_page_context:
            candidate_provenance['page_context'] = candidate_page_context
        physics_source_review = bool(
            PHYSICS_SOURCE_REVIEW_HINTS.search(candidate)
            and has_visuals
        )
        ambiguous_angle = bool(AMBIGUOUS_PHYSICS_ANGLE.search(candidate))
        math_or_diagram_review = bool(
            MATH_OR_DIAGRAM_HINTS.search(candidate)
            or physics_source_review
            or ambiguous_angle
            or (has_visuals and 'draw' in candidate.lower())
        )
        if source_ocr_text and PDF_TEXT_GAP.search(candidate):
            alternative = _ocr_text_for_candidate(candidate, source_ocr_text)
            if alternative:
                candidate_provenance['source_ocr_text'] = alternative
                reasons.append('pdf_text_layer_incomplete')
        if math_or_diagram_review:
            candidate_provenance['source_review_required'] = True
            candidate_provenance['source_review_kind'] = (
                'physics_symbols_or_diagram'
                if physics_source_review or ambiguous_angle
                else 'math_or_diagram'
            )
            review_features = []
            if physics_source_review:
                review_features.extend(['physics_notation', 'source_visuals'])
            if ambiguous_angle:
                review_features.append('ambiguous_angle_notation')
            candidate_provenance['source_review_features'] = review_features
            candidate_provenance['source_review_message'] = (
                'Check mathematical symbols, notation, and diagrams against the original page before answering or publishing. '
                'Do not infer missing or ambiguous symbols.'
            )
            reasons.append(
                'physics_source_review_required'
                if physics_source_review or ambiguous_angle
                else 'math_or_diagram_requires_source_review'
            )
        if question_type == 'unknown':
            reasons.append('question_type_unknown')
        if ocr_confidence is not None and ocr_confidence < 0.75:
            reasons.append('low_ocr_confidence')
        if has_visuals:
            reasons.append('source_page_contains_visuals')
        result.append({
            'text': candidate if not math_or_diagram_review else (
                '[Source review required: check symbols and diagrams against the original source page before answering.]\n'
                f'{candidate}'
            ),
            'question_type': question_type,
            'content': {
                'blocks': blocks,
                'source_page': page_number,
                'visual_fallback': has_visuals,
                **{
                    **candidate_provenance,
                    'source_regions': _regions_for_candidate(candidate, ocr_regions or []),
                },
            },
            'signals': {
                'ocr_confidence': ocr_confidence,
                'question_type_confidence': type_confidence,
                'question_type_method': 'heuristic' if question_type != 'unknown' else 'unclassified',
                'requires_review': True,
                'reasons': reasons or ['awaiting_human_review'],
            },
        })
    return result


def _read_pdf_with_pypdf(data: bytes) -> tuple[int, list[dict]]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ''
        has_unreadable_content = not text.strip()
        page_items = _page_candidates(
            text,
            index + 1,
            None,
            has_unreadable_content,
        )
        if has_unreadable_content:
            page_items[-1]['signals']['reasons'] = ['local_ocr_unavailable']
        pages.extend(page_items)
    return len(reader.pages), pages


def _read_pdf(data: bytes) -> tuple[int, list[dict]]:
    try:
        import fitz
    except ImportError:
        return _read_pdf_with_pypdf(data)

    pages = []
    with fitz.open(stream=data, filetype='pdf') as pdf:
        for index, page in enumerate(pdf):
            text = page.get_text('text', sort=True).strip()
            ocr_confidence = None
            has_text_gaps = bool(PDF_TEXT_GAP.search(text))
            source_ocr_text = None
            source_ocr_confidence = None
            if len(text) < 24 or has_text_gaps:
                pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.open(io.BytesIO(pixmap.tobytes('png')))
                try:
                    ocr_text, detected_confidence, ocr_regions = _ocr_text(image)
                except RuntimeError as exc:
                    if str(exc) != 'LOCAL_OCR_UNAVAILABLE':
                        raise
                    ocr_text = ''
                    detected_confidence = None
                    ocr_regions = []
                if len(ocr_text.strip()) > len(text):
                    text = ocr_text.strip()
                    ocr_confidence = detected_confidence
                else:
                    if has_text_gaps:
                        source_ocr_text = ocr_text
                        source_ocr_confidence = detected_confidence
                source_image_size = image.size if ocr_regions else None
            else:
                ocr_regions = []
                source_image_size = None
            visual = bool(page.get_images(full=True) or page.get_drawings())
            page_items = _page_candidates(
                text,
                index + 1,
                ocr_confidence,
                visual,
                ocr_regions,
                source_image_size,
                source_ocr_text,
                source_ocr_confidence,
            )
            if len(text) < 24 and not ocr_regions and not text.strip():
                page_items[-1]['signals']['reasons'] = ['local_ocr_unavailable']
            pages.extend(page_items)
        return len(pdf), pages


def _read_image(data: bytes) -> tuple[int, list[dict]]:
    with Image.open(io.BytesIO(data)) as image:
        page_count = getattr(image, 'n_frames', 1)
        pages = []
        for index in range(page_count):
            image.seek(index)
            try:
                text, confidence, regions = _ocr_text(image.copy())
            except RuntimeError as exc:
                if str(exc) != 'LOCAL_OCR_UNAVAILABLE':
                    raise
                text, confidence = '', None
                regions = []
            pages.extend(_page_candidates(
                text,
                index + 1,
                confidence,
                True,
                regions,
                image.size if regions else None,
            ))
            if not text.strip():
                pages[-1]['signals']['reasons'] = ['local_ocr_unavailable']
        return page_count, pages


def _read_docx(data: bytes) -> tuple[None, list[dict]]:
    document = DocxDocument(io.BytesIO(data))
    lines = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    for table in document.tables:
        for row in table.rows:
            lines.append(' | '.join(cell.text.strip() for cell in row.cells))
    text = '\n'.join(lines)
    has_visuals = bool(document.inline_shapes or document.tables)
    confidences = []
    image_text = []
    for part in document.part.related_parts.values():
        if not part.content_type.startswith('image/'):
            continue
        try:
            recognized, confidence, _ = _ocr_text(Image.open(io.BytesIO(part.blob)))
        except RuntimeError as exc:
            if str(exc) != 'LOCAL_OCR_UNAVAILABLE':
                raise
            recognized, confidence = '', None
        except (UnidentifiedImageError, OSError):
            recognized, confidence = '', None
        if recognized:
            image_text.append(recognized)
        if confidence is not None:
            confidences.append(confidence)
    if image_text:
        text = f'{text}\n' if text else ''
        text += '\n'.join(image_text)
    candidates = _page_candidates(text, None, min(confidences) if confidences else None, has_visuals)
    if has_visuals and not image_text and not text.strip():
        for candidate in candidates:
            candidate['signals']['reasons'] = ['visual_content_requires_source_review']
    for candidate in candidates:
        candidate['content']['visual_fallback'] = has_visuals
    return None, candidates


def _read_pptx(data: bytes) -> tuple[int, list[dict]]:
    presentation = Presentation(io.BytesIO(data))
    pages = []
    for index, slide in enumerate(presentation.slides):
        lines = []
        has_visuals = False
        ocr_confidences = []
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text.strip():
                lines.extend(shape.text.splitlines())
            if shape.has_table:
                has_visuals = True
                for row in shape.table.rows:
                    lines.append(' | '.join(cell.text.strip() for cell in row.cells))
            if shape.shape_type == 13:
                has_visuals = True
                try:
                    image = Image.open(io.BytesIO(shape.image.blob))
                    image_text, confidence, _ = _ocr_text(image)
                except RuntimeError as exc:
                    if str(exc) != 'LOCAL_OCR_UNAVAILABLE':
                        raise
                    image_text, confidence = '', None
                except (UnidentifiedImageError, OSError):
                    image_text, confidence = '', None
                if image_text:
                    lines.append(image_text)
                if confidence is not None:
                    ocr_confidences.append(confidence)
        candidates = _page_candidates(
            '\n\n'.join(lines),
            index + 1,
            min(ocr_confidences) if ocr_confidences else None,
            has_visuals,
        )
        pages.extend(candidates)
    return len(presentation.slides), pages


def extract_candidates(data: bytes, mime_type: str) -> tuple[int | None, list[dict]]:
    if mime_type == 'application/pdf':
        return _read_pdf(data)
    if mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        return _read_docx(data)
    if mime_type == 'application/vnd.openxmlformats-officedocument.presentationml.presentation':
        return _read_pptx(data)
    if mime_type.startswith('image/'):
        return _read_image(data)
    raise ValueError(f'Unsupported MIME type for extraction: {mime_type}')


def extract_job(job_id: str, worker_id: str) -> None:
    parsed_job_id = uuid.UUID(job_id)
    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(
            ProcessingJob.id == parsed_job_id,
            ProcessingJob.status == JobStatus.running,
            ProcessingJob.worker_id == worker_id,
        ).with_for_update().first()
        if not job:
            return
        doc = db.query(Document).filter(Document.id == job.document_id).first()
        if not doc:
            raise RuntimeError('DOCUMENT_NOT_FOUND')
        if doc.security_status != 'clean':
            doc.processing_status = ProcessingStatus.held
            job.status = JobStatus.held
            job.error_category = 'security_scan_required'
            job.finished_at = datetime.now(timezone.utc)
            job.worker_id = None
            job.lease_expires_at = None
            db.commit()
            return
        document_id = doc.id
        storage_key = doc.storage_object_key
        mime_type = doc.mime_type

    data = read_bytes(storage_key)
    page_count, candidates = extract_candidates(data, mime_type)
    with SessionLocal() as db:
        job = db.query(ProcessingJob).filter(
            ProcessingJob.id == parsed_job_id,
            ProcessingJob.status == JobStatus.running,
            ProcessingJob.worker_id == worker_id,
        ).with_for_update().first()
        if not job:
            raise RuntimeError('PROCESSING_LEASE_LOST')
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise RuntimeError('DOCUMENT_NOT_FOUND')
        if doc.security_status != 'clean':
            raise RuntimeError('SECURITY_SCAN_REQUIRED')
        db.query(Question).filter(Question.document_id == doc.id).delete(synchronize_session=False)
        doc.page_count = page_count
        for candidate in candidates:
            page_number = candidate['content']['source_page']
            db.add(Question(
                document_id=doc.id,
                source_page_start=page_number,
                source_page_end=page_number,
                extracted_text=candidate['text'],
                question_type=candidate['question_type'],
                content_json=json.dumps(candidate['content'], ensure_ascii=False),
                quality_signals_json=json.dumps(candidate['signals'], ensure_ascii=False),
                extraction_version=EXTRACTION_VERSION,
                quality_status=QualityStatus.held,
                extraction_method='local_ocr' if candidate['signals']['ocr_confidence'] is not None else 'local_text',
            ))
        doc.processing_status = ProcessingStatus.completed if candidates else ProcessingStatus.held
        job.status = JobStatus.completed if candidates else JobStatus.held
        job.finished_at = datetime.now(timezone.utc)
        job.worker_id = None
        job.lease_expires_at = None
        job.error_category = None
        db.commit()

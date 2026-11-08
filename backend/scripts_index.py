import os, sys
sys.path.insert(0, 'backend')
from dotenv import load_dotenv
load_dotenv()
from app.db.session import engine, SessionLocal
from app.models.question import Question
from app.services.embeddings import embed, to_json
from sqlalchemy import text

def main():
    db = SessionLocal()
    pending = db.query(Question).filter(Question.embedding_status != 'complete').all()
    print(f'Found {len(pending)} questions to index')
    for q in pending:
        v = embed(q.extracted_text)
        if v is None:
            q.embedding_status = 'failed'
        else:
            q.embedding = to_json(v)
            q.embedding_status = 'complete'
        db.commit()
        print(f'  {q.id}: {q.embedding_status}')
    db.close()
    print('Done')

if __name__ == '__main__': main()

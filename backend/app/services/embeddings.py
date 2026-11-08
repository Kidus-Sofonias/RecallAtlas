import json, math

_model = None

def get_model():
    global _model
    if _model is not None: return _model
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    except Exception:
        _model = False
    return _model

def embed(text):
    m = get_model()
    if not m: return None
    try: return m.encode(text).tolist()
    except Exception: return None

def cosine(a, b):
    if not a or not b: return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(x*x for x in b))
    if na == 0 or nb == 0: return 0.0
    return dot/(na*nb)

def to_json(v): return json.dumps(v) if v is not None else None

def from_json(s):
    if not s: return None
    try: return json.loads(s)
    except Exception: return None

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings, ensure_authentication_ready, ensure_deployment_ready
from app.middleware import RateLimitMiddleware
from app.db.session import SessionLocal
from app.services.auth import bootstrap_admin
from app.api.auth import router as auth_router
from app.api.uploads import router as uploads_router
from app.api.documents import router as documents_router
from app.api.search import router as search_router
from app.api.questions import router as questions_router
from app.api.taxonomy import router as taxonomy_router
from app.api.admin import router as admin_router
from app.api.community import router as community_router
from app.api.phase45 import router as phase45_router
from app.api.semantic import router as semantic_router
from app.api.backup import router as backup_router
from app.api.admin_users import router as admin_users_router
from app.api.bookmarks import router as bookmarks_router
from app.api.discovery import router as discovery_router
from app.api.resources import router as resources_router
from app.api.profile import admin_router as profile_admin_router, router as profile_router

ensure_authentication_ready(
    settings.app_env,
    settings.secret_key,
    settings.admin_email,
    settings.admin_initial_password,
)
ensure_deployment_ready(
    settings.app_env,
    settings.database_url,
    settings.storage_backend,
    settings.object_storage_bucket,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if (
        settings.admin_email
        or settings.admin_initial_password
        or settings.app_env.lower() not in {'development', 'test'}
    ):
        with SessionLocal() as db:
            bootstrap_admin(db, settings.admin_email, settings.admin_initial_password)
    yield


app = FastAPI(title='Recall Atlas API', version='0.1.0', lifespan=lifespan)
app.add_middleware(RateLimitMiddleware)
app.include_router(auth_router)
app.include_router(uploads_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(questions_router)
app.include_router(taxonomy_router)
app.include_router(admin_router)
app.include_router(community_router)
app.include_router(phase45_router)
app.include_router(semantic_router)
app.include_router(backup_router)
app.include_router(bookmarks_router)
app.include_router(discovery_router)
app.include_router(resources_router)
app.include_router(profile_router)
app.include_router(profile_admin_router)
app.include_router(admin_users_router)

@app.get('/health')
def health(): return {'status':'ok','service':'recall-atlas'}

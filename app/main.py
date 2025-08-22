import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from app.apps.consumers.user_creation_consumer import router as user_creation_consumer_router
from app.apps.genres.routes import router as genres_router
from app.apps.health_check.routes import router as health_check_router
from app.apps.users.routes import router as users_router
from app.core.config import get_settings
from app.lifespan import lifespan

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s %(message)s',
)


def create_app() -> FastAPI:
    settings = get_settings()

    _app = FastAPI(title=settings.PROJECT_NAME, version='0.1.0', lifespan=lifespan, root_path=settings.ROOT_PATH)

    _app.include_router(health_check_router)
    _app.include_router(genres_router)
    _app.include_router(users_router)
    _app.include_router(user_creation_consumer_router)

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    add_pagination(_app)

    return _app


app = create_app()

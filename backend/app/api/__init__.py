from fastapi import APIRouter

from .auth import router as auth_router
from .connections import router as connections_router
from .queries import router as queries_router
from .dashboards import router as dashboards_router
from .chat_sessions import router as chat_sessions_router
from .ml_pipelines import router as ml_router
from .exports import router as exports_router
from .notifications import router as notifications_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(connections_router, prefix="/connections", tags=["connections"])
api_router.include_router(queries_router, prefix="/queries", tags=["queries"])
api_router.include_router(dashboards_router, prefix="/dashboards", tags=["dashboards"])
api_router.include_router(chat_sessions_router, prefix="/chat-sessions", tags=["chat_sessions"])
api_router.include_router(ml_router, prefix="/ml", tags=["ml"])
api_router.include_router(exports_router, prefix="/exports", tags=["exports"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])

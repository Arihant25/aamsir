"""
AAMSIR FastAPI Application — Main entry point.

Initializes the database, registers retrieval strategy plugins with
the Orchestrator (Microkernel), and mounts all API routes.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router, set_orchestrator
from .database import init_db
from .retrieval.factory import StrategyFactory
from .retrieval.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="AAMSIR",
        description="Adaptive Architecture for Multi-Strategy Information Retrieval",
        version="1.0.0",
    )

    # CORS for Next.js frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Initialize Orchestrator with strategy plugins (Microkernel + Factory)
    orchestrator = Orchestrator()
    for strategy_type in StrategyFactory.available_types():
        try:
            strategy = StrategyFactory.create(strategy_type)
            orchestrator.register(strategy)
        except Exception as e:
            logger.warning(f"Could not register strategy '{strategy_type}': {e}")

    set_orchestrator(orchestrator)
    logger.info(f"Orchestrator ready. Available: {orchestrator.get_available()}")

    # Mount routes
    app.include_router(router, prefix="/api")

    return app


app = create_app()

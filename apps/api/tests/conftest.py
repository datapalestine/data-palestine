"""Test fixtures: test DB, async client, seed data."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Async HTTP test client for the FastAPI app, with the DB pool lifespan active.

    Also exposes the live asyncpg pool as `client.pool` for tests that need to
    seed or inspect rows directly.
    """
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            ac.pool = app.state.pool
            yield ac

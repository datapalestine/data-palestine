"""Tests for observation API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_observations(client):
    """Test listing observations returns paginated response."""
    response = await client.get("/api/v1/observations")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data

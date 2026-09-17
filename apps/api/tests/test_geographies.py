"""Tests for geography API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_get_geography_not_found(client):
    """Test getting a non-existent geography returns 404."""
    response = await client.get("/api/v1/geographies/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_geography_rejects_invalid_lang(client):
    """Test that an unrecognized lang value is rejected with 422, matching list_geographies."""
    response = await client.get("/api/v1/geographies/PS?lang=xx")
    assert response.status_code == 422

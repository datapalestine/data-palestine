"""Tests for indicator API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_indicators(client):
    """Test listing indicators returns paginated response."""
    response = await client.get("/api/v1/indicators")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data


@pytest.mark.asyncio
async def test_get_indicator_not_found(client):
    """Test getting a non-existent indicator returns 404."""
    response = await client.get("/api/v1/indicators/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_indicator_rejects_invalid_lang(client):
    """Test that an unrecognized lang value is rejected with 422, matching list_indicators."""
    response = await client.get("/api/v1/indicators/1?lang=xx")
    assert response.status_code == 422

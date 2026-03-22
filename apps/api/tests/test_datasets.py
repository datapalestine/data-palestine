"""Tests for dataset API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_datasets(client):
    """Test listing datasets returns paginated response."""
    response = await client.get("/api/v1/datasets")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert "links" in data


@pytest.mark.asyncio
async def test_get_dataset_not_found(client):
    """Test getting a non-existent dataset returns 404."""
    response = await client.get("/api/v1/datasets/nonexistent")
    assert response.status_code == 404

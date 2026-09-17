"""Tests for the curation review workflow (SEC-02: anonymous data-destruction path).

Covers:
- submit requires auth (kills anonymous staging of destructive payloads)
- changes payload is validated against a strict schema (kills arbitrary-shape JSONB)
- admin auth is fail-closed (empty/default key never authenticates)
- approve enforces dataset ownership on every indicator touched (SEC-3)
- approve soft-deletes instead of hard-deleting (data-integrity rule)
"""

import pytest

from app.config import Settings

ADMIN_KEY = "test-admin-secret-do-not-use-in-prod"


async def _make_dataset(pool, slug: str) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO datasets (slug, name_en, name_ar, quality_status)
            VALUES ($1, $2, $2, 'needs_review')
            RETURNING id
            """,
            slug,
            slug,
        )


async def _make_indicator(pool, dataset_id: int, code: str) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO indicators (dataset_id, code, name_en, name_ar)
            VALUES ($1, $2, $2, $2)
            RETURNING id
            """,
            dataset_id,
            code,
        )


async def _make_observation(pool, indicator_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO observations (indicator_id, geography_code, time_period, value)
            VALUES ($1, 'PS', '2024-01-01', 42)
            """,
            indicator_id,
        )


async def _make_review(pool, dataset_id: int, changes: dict) -> int:
    import json

    async with pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO curation_reviews
                (dataset_id, reviewer_name, reviewer_email, changes, status)
            VALUES ($1, 'tester', 'tester@example.com', $2::jsonb, 'pending')
            RETURNING id
            """,
            dataset_id,
            json.dumps(changes),
        )


def _admin_headers():
    return {"Authorization": f"Bearer {ADMIN_KEY}"}


@pytest.fixture(autouse=True)
def _configure_admin_key(monkeypatch):
    """Point the app at a known admin key for the duration of each test."""
    from app.routers import curation

    monkeypatch.setattr(curation.settings, "admin_secret_key", ADMIN_KEY)


# ---------------------------------------------------------------------------
# Fail-closed admin key
# ---------------------------------------------------------------------------


def test_prod_boot_fails_without_admin_key():
    with pytest.raises(RuntimeError, match="ADMIN_SECRET_KEY"):
        Settings(environment="production", secret_key="a-real-secret", admin_secret_key="")


def test_prod_boot_fails_with_default_admin_key():
    with pytest.raises(RuntimeError, match="ADMIN_SECRET_KEY"):
        Settings(
            environment="production",
            secret_key="a-real-secret",
            admin_secret_key="admin-dev-key-change-me",
        )


def test_prod_boot_succeeds_with_real_admin_key():
    Settings(
        environment="production",
        secret_key="a-real-secret",
        admin_secret_key="a-real-admin-key",
    )


# ---------------------------------------------------------------------------
# submit: auth + payload validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_requires_auth(client):
    response = await client.post(
        "/api/v1/curation/submit",
        json={
            "dataset_id": 1,
            "reviewer_name": "anon",
            "reviewer_email": "anon@example.com",
            "changes": {"indicators": [{"action": "delete", "indicator_id": 1}]},
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submit_rejects_wrong_admin_key(client):
    response = await client.post(
        "/api/v1/curation/submit",
        headers={"Authorization": "Bearer wrong-key"},
        json={
            "dataset_id": 1,
            "reviewer_name": "anon",
            "reviewer_email": "anon@example.com",
            "changes": {},
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_changes_schema_rejects_unknown_action(client):
    dataset_id = await _make_dataset(client.pool, "submit-bad-action")
    response = await client.post(
        "/api/v1/curation/submit",
        headers=_admin_headers(),
        json={
            "dataset_id": dataset_id,
            "reviewer_name": "tester",
            "reviewer_email": "tester@example.com",
            "changes": {"indicators": [{"action": "nuke", "indicator_id": 1}]},
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_changes_schema_rejects_merge_without_target(client):
    dataset_id = await _make_dataset(client.pool, "submit-bad-merge")
    response = await client.post(
        "/api/v1/curation/submit",
        headers=_admin_headers(),
        json={
            "dataset_id": dataset_id,
            "reviewer_name": "tester",
            "reviewer_email": "tester@example.com",
            "changes": {"indicators": [{"action": "merge_into", "indicator_id": 1}]},
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_changes_schema_rejects_invalid_email(client):
    dataset_id = await _make_dataset(client.pool, "submit-bad-email")
    response = await client.post(
        "/api/v1/curation/submit",
        headers=_admin_headers(),
        json={
            "dataset_id": dataset_id,
            "reviewer_name": "tester",
            "reviewer_email": "not-an-email",
            "changes": {},
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_with_valid_auth_and_payload_succeeds(client):
    dataset_id = await _make_dataset(client.pool, "submit-ok")
    response = await client.post(
        "/api/v1/curation/submit",
        headers=_admin_headers(),
        json={
            "dataset_id": dataset_id,
            "reviewer_name": "tester",
            "reviewer_email": "tester@example.com",
            "changes": {"name_en": "New Name"},
        },
    )
    assert response.status_code == 200
    assert "id" in response.json()["data"]


# ---------------------------------------------------------------------------
# approve: dataset ownership enforcement (SEC-3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_cross_dataset_indicator_rejected(client):
    pool = client.pool
    dataset_a = await _make_dataset(pool, "dataset-a")
    dataset_b = await _make_dataset(pool, "dataset-b")
    indicator_b = await _make_indicator(pool, dataset_b, "belongs-to-b")
    await _make_observation(pool, indicator_b)

    review_id = await _make_review(
        pool,
        dataset_a,
        {"indicators": [{"action": "delete", "indicator_id": indicator_b}]},
    )

    response = await client.post(
        f"/api/v1/curation/approve/{review_id}",
        headers=_admin_headers(),
    )
    assert response.status_code == 422

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT deleted_at FROM indicators WHERE id = $1", indicator_b
        )
        assert row["deleted_at"] is None


# ---------------------------------------------------------------------------
# approve: soft delete instead of hard delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_is_soft(client):
    pool = client.pool
    dataset_id = await _make_dataset(pool, "soft-delete-ds")
    indicator_id = await _make_indicator(pool, dataset_id, "to-delete")
    await _make_observation(pool, indicator_id)

    review_id = await _make_review(
        pool,
        dataset_id,
        {"indicators": [{"action": "delete", "indicator_id": indicator_id}]},
    )

    response = await client.post(
        f"/api/v1/curation/approve/{review_id}",
        headers=_admin_headers(),
    )
    assert response.status_code == 200

    async with pool.acquire() as conn:
        indicator_row = await conn.fetchrow(
            "SELECT deleted_at FROM indicators WHERE id = $1", indicator_id
        )
        assert indicator_row is not None
        assert indicator_row["deleted_at"] is not None

        obs_rows = await conn.fetch(
            "SELECT deleted_at FROM observations WHERE indicator_id = $1", indicator_id
        )
        assert len(obs_rows) == 1
        assert obs_rows[0]["deleted_at"] is not None

    # Soft-deleted indicator must not appear in the public read paths.
    list_response = await client.get("/api/v1/indicators")
    ids = [i["id"] for i in list_response.json()["data"]]
    assert indicator_id not in ids

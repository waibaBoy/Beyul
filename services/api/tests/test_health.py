import os

from fastapi.testclient import TestClient

os.environ["REPOSITORY_BACKEND"] = "memory"
os.environ["DEV_AUTH_USERNAME"] = "demo_admin"
os.environ["DEV_AUTH_DISPLAY_NAME"] = "Demo Admin"
os.environ["DEV_AUTH_IS_ADMIN"] = "true"

from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_health_endpoint_in_memory_mode() -> None:
    client = TestClient(app)
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json()["backend"] == "memory"
    assert response.json()["status"] == "skipped"


def test_auth_me_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["username"] == "demo_admin"


def test_auth_me_honors_dev_headers_in_memory_mode() -> None:
    client = TestClient(app)
    response = client.get(
        "/api/v1/auth/me",
        headers={
            "X-Beyul-Username": "header_user",
            "X-Beyul-Display-Name": "Header User",
            "X-Beyul-Is-Admin": "false",
        },
    )

    assert response.status_code == 200
    assert response.json()["username"] == "header_user"
    assert response.json()["display_name"] == "Header User"
    assert response.json()["is_admin"] is False


def test_list_communities_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/communities")

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_list_market_requests_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/market-requests/me")

    assert response.status_code == 200
    assert response.json()[0]["status"] == "draft"


def test_create_community_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/communities",
        json={
            "slug": "new-community",
            "name": "New Community",
            "description": "Local creation test",
            "visibility": "public",
            "require_post_approval": True,
            "require_market_approval": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "new-community"


def test_duplicate_wallet_returns_conflict() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/profiles/me/wallets",
        json={
            "chain_name": "polygon",
            "wallet_address": "0x0000000000000000000000000000000000000001",
            "is_primary": False,
        },
    )

    assert response.status_code == 409


def test_update_profile_endpoint() -> None:
    client = TestClient(app)
    response = client.patch(
        "/api/v1/profiles/me",
        json={
            "display_name": "Updated Demo Admin",
            "bio": "Updated locally",
        },
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Updated Demo Admin"
    assert response.json()["bio"] == "Updated locally"


def test_create_market_request_endpoint() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/market-requests",
        json={
            "title": "Will BTC close above $100k this quarter?",
            "slug": "btc-above-100k-q",
            "question": "Will BTC close above $100k by quarter end?",
            "description": "Local creation test",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "btc-above-100k-q"
    assert response.json()["status"] == "draft"


def test_create_post_requires_review_for_non_admin_user() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/communities/aussie-politics/posts",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000099",
            "X-Beyul-Username": "queue_user",
            "X-Beyul-Display-Name": "Queue User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Pending moderation",
            "body": "This should enter the review queue."
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "pending_review"

    queue_response = client.get("/api/v1/admin/review-queue")
    assert queue_response.status_code == 200
    assert any(post["title"] == "Pending moderation" for post in queue_response.json()["pending_posts"])


def test_submit_and_approve_market_request_flow() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/market-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000055",
            "X-Beyul-Username": "market_user",
            "X-Beyul-Display-Name": "Market User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Will CPI cool next quarter?",
            "slug": "cpi-cool-next-quarter",
            "question": "Will CPI print lower next quarter?",
            "description": "Queue me for review",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]

    submit_response = client.post(
        f"/api/v1/market-requests/{request_id}/submit",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000055",
            "X-Beyul-Username": "market_user",
            "X-Beyul-Display-Name": "Market User",
            "X-Beyul-Is-Admin": "false",
        },
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "submitted"

    queue_response = client.get("/api/v1/admin/review-queue")
    assert queue_response.status_code == 200
    assert any(
        request["id"] == request_id for request in queue_response.json()["pending_market_requests"]
    )

    approve_response = client.post(
        f"/api/v1/market-requests/{request_id}/approve",
        json={"review_notes": "Ready to convert into a market."},
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"


def test_publish_market_request_creates_canonical_market() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/market-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000077",
            "X-Beyul-Username": "publisher",
            "X-Beyul-Display-Name": "Publisher",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Will unemployment fall next month?",
            "slug": "unemployment-fall-next-month",
            "question": "Will unemployment fall next month?",
            "description": "Publish me into a market.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]

    submit_response = client.post(
        f"/api/v1/market-requests/{request_id}/submit",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000077",
            "X-Beyul-Username": "publisher",
            "X-Beyul-Display-Name": "Publisher",
            "X-Beyul-Is-Admin": "false",
        },
    )
    assert submit_response.status_code == 200

    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for market creation."},
    )

    assert publish_response.status_code == 200
    payload = publish_response.json()
    assert payload["created_from_request_id"] == request_id
    assert payload["status"] == "pending_liquidity"
    assert [outcome["label"] for outcome in payload["outcomes"]] == ["Yes", "No"]

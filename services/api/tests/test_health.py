import asyncio
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

os.environ["REPOSITORY_BACKEND"] = "memory"
os.environ["DEV_AUTH_USERNAME"] = "demo_admin"
os.environ["DEV_AUTH_DISPLAY_NAME"] = "Demo Admin"
os.environ["DEV_AUTH_IS_ADMIN"] = "true"
os.environ["ORACLE_PROVIDER"] = "mock"

from app.main import app
from app.core.container import container
from app.core.config import settings
from app.schemas.market import MarketTradeResponse
from app.services.oracle_service import OracleConfigurationError, OracleResolutionRequest, UMAOracleService


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

    post_approve_queue = client.get("/api/v1/admin/review-queue")
    assert post_approve_queue.status_code == 200
    assert any(
        request["id"] == request_id and request["status"] == "approved"
        for request in post_approve_queue.json()["pending_market_requests"]
    )


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


def test_publish_market_request_carries_contract_metadata_answers() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/market-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000078",
            "X-Beyul-Username": "metadata_user",
            "X-Beyul-Display-Name": "Metadata User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Will BTC rise this hour?",
            "slug": "btc-rise-this-hour",
            "question": "Will BTC rise this hour?",
            "description": "Publish me with contract metadata.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    answer_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000078",
        "X-Beyul-Username": "metadata_user",
        "X-Beyul-Display-Name": "Metadata User",
        "X-Beyul-Is-Admin": "false",
    }
    client.put(
        f"/api/v1/market-requests/{request_id}/answers/reference_label",
        headers=answer_headers,
        json={"question_label": "Reference label", "answer_text": "BTC/USD price"},
    )
    client.put(
        f"/api/v1/market-requests/{request_id}/answers/price_to_beat",
        headers=answer_headers,
        json={"question_label": "Price to beat", "answer_text": "67627.45"},
    )
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=answer_headers)

    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for market creation."},
    )

    assert publish_response.status_code == 200
    payload = publish_response.json()
    assert payload["reference_context"]["reference_label"] == "BTC/USD price"
    assert payload["reference_context"]["price_to_beat"] == "67627.45"
    assert payload["settlement_source"] is not None
    assert payload["timing"]["trading_opens_at"] is not None


def test_publish_market_request_uses_template_metadata_without_answers() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/market-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000079",
            "X-Beyul-Username": "template_user",
            "X-Beyul-Display-Name": "Template User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Will SOL close above 250?",
            "slug": "sol-close-above-250",
            "question": "Will SOL close above 250 by month end?",
            "description": "Generated from a price-above template.",
            "template_key": "price_above",
            "template_config": {
                "category": "Crypto",
                "subcategory": "Solana",
                "subject": "SOL",
                "reference_asset": "SOL/USD",
                "threshold_value": "250",
                "timeframe_label": "by month end",
                "reference_source_label": "Chainlink Crypto Feeds",
            },
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    submit_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000079",
        "X-Beyul-Username": "template_user",
        "X-Beyul-Display-Name": "Template User",
        "X-Beyul-Is-Admin": "false",
    }
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=submit_headers)

    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for market creation."},
    )

    assert publish_response.status_code == 200
    payload = publish_response.json()
    assert payload["reference_context"]["category"] == "Crypto"
    assert payload["reference_context"]["subcategory"] == "Solana"
    assert payload["reference_context"]["reference_asset"] == "SOL/USD"
    assert payload["reference_context"]["price_to_beat"] == "250"


def test_market_trading_shell_returns_quotes_for_published_market() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/market-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000088",
            "X-Beyul-Username": "shell_user",
            "X-Beyul-Display-Name": "Shell User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Will rates hold next meeting?",
            "slug": "rates-hold-next-meeting",
            "question": "Will rates hold next meeting?",
            "description": "Create a market shell.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(
        f"/api/v1/market-requests/{request_id}/submit",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000088",
            "X-Beyul-Username": "shell_user",
            "X-Beyul-Display-Name": "Shell User",
            "X-Beyul-Is-Admin": "false",
        },
    )
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for shell testing."},
    )
    market_slug = publish_response.json()["slug"]

    shell_response = client.get(f"/api/v1/markets/{market_slug}/trading-shell")

    assert shell_response.status_code == 200
    payload = shell_response.json()
    assert payload["market"]["slug"] == market_slug
    assert [quote["outcome_label"] for quote in payload["quotes"]] == ["Yes", "No"]
    assert [book["outcome_label"] for book in payload["order_books"]] == ["Yes", "No"]
    assert payload["recent_trades"] == []


def test_market_holders_endpoint_returns_grouped_payload() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/market-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000089",
            "X-Beyul-Username": "holders_user",
            "X-Beyul-Display-Name": "Holders User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Will yields fall next week?",
            "slug": "yields-fall-next-week",
            "question": "Will yields fall next week?",
            "description": "Create holder leaderboard shell.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    submit_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000089",
        "X-Beyul-Username": "holders_user",
        "X-Beyul-Display-Name": "Holders User",
        "X-Beyul-Is-Admin": "false",
    }
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=submit_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for holder testing."},
    )
    market_slug = publish_response.json()["slug"]

    holders_response = client.get(f"/api/v1/markets/{market_slug}/holders")

    assert holders_response.status_code == 200
    payload = holders_response.json()
    assert payload["market_slug"] == market_slug
    assert [group["outcome_label"] for group in payload["groups"]] == ["Yes", "No"]


def test_market_history_returns_bucketed_ohlcv_for_selected_range() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/market-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000118",
            "X-Beyul-Username": "history_user",
            "X-Beyul-Display-Name": "History User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Will inflation cool this year?",
            "slug": "inflation-cool-this-year",
            "question": "Will inflation cool this year?",
            "description": "History endpoint coverage.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(
        f"/api/v1/market-requests/{request_id}/submit",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000118",
            "X-Beyul-Username": "history_user",
            "X-Beyul-Display-Name": "History User",
            "X-Beyul-Is-Admin": "false",
        },
    )
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for history testing."},
    )
    market_payload = publish_response.json()
    outcome_id = UUID(market_payload["outcomes"][0]["id"])

    trading_repository = container.trading_service._repository
    base_hour = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    trading_repository._trades.extend(
        [
            MarketTradeResponse(
                id=uuid4(),
                outcome_id=outcome_id,
                outcome_label="Yes",
                price="0.52",
                quantity="10",
                gross_notional="5.2",
                executed_at=base_hour - timedelta(hours=3, minutes=10),
            ),
            MarketTradeResponse(
                id=uuid4(),
                outcome_id=outcome_id,
                outcome_label="Yes",
                price="0.58",
                quantity="5",
                gross_notional="2.9",
                executed_at=base_hour - timedelta(hours=3, minutes=5),
            ),
            MarketTradeResponse(
                id=uuid4(),
                outcome_id=outcome_id,
                outcome_label="Yes",
                price="0.61",
                quantity="7",
                gross_notional="4.27",
                executed_at=base_hour - timedelta(hours=1, minutes=15),
            ),
        ]
    )

    history_response = client.get(
        f"/api/v1/markets/{market_payload['slug']}/history",
        params={"outcome_id": str(outcome_id), "range": "1D"},
    )

    assert history_response.status_code == 200
    payload = history_response.json()
    assert payload["range_key"] == "1D"
    assert payload["interval_seconds"] == 3600
    assert payload["outcome_id"] == str(outcome_id)
    assert len(payload["buckets"]) == 2
    assert payload["buckets"][0]["open_price"] == "0.52"
    assert payload["buckets"][0]["close_price"] == "0.58"
    assert payload["buckets"][0]["volume"] == "15"
    assert payload["buckets"][0]["trade_count"] == 2


def test_create_market_order_and_list_my_orders() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/market-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000066",
            "X-Beyul-Username": "order_user",
            "X-Beyul-Display-Name": "Order User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Will CPI print lower next month?",
            "slug": "cpi-lower-next-month",
            "question": "Will CPI print lower next month?",
            "description": "Place orders on me.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(
        f"/api/v1/market-requests/{request_id}/submit",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000066",
            "X-Beyul-Username": "order_user",
            "X-Beyul-Display-Name": "Order User",
            "X-Beyul-Is-Admin": "false",
        },
    )
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for order testing."},
    )
    market_payload = publish_response.json()
    market_slug = market_payload["slug"]
    yes_outcome_id = market_payload["outcomes"][0]["id"]

    order_response = client.post(
        f"/api/v1/markets/{market_slug}/orders",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000066",
            "X-Beyul-Username": "order_user",
            "X-Beyul-Display-Name": "Order User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "outcome_id": yes_outcome_id,
            "side": "buy",
            "order_type": "limit",
            "quantity": "25",
            "price": "0.61",
            "client_order_id": "web-ticket-1",
        },
    )

    assert order_response.status_code == 201
    assert order_response.json()["status"] == "open"
    assert order_response.json()["outcome_label"] == "Yes"

    my_orders_response = client.get(
        f"/api/v1/markets/{market_slug}/orders/me",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000066",
            "X-Beyul-Username": "order_user",
            "X-Beyul-Display-Name": "Order User",
            "X-Beyul-Is-Admin": "false",
        },
    )

    assert my_orders_response.status_code == 200
    assert len(my_orders_response.json()) == 1
    assert my_orders_response.json()[0]["client_order_id"] == "web-ticket-1"


def test_admin_can_open_market_from_pending_liquidity() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/market-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000123",
            "X-Beyul-Username": "status_user",
            "X-Beyul-Display-Name": "Status User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Will Satta open this market?",
            "slug": "satta-open-this-market",
            "question": "Will Satta open this market?",
            "description": "Manual market status transition.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(
        f"/api/v1/market-requests/{request_id}/submit",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000123",
            "X-Beyul-Username": "status_user",
            "X-Beyul-Display-Name": "Status User",
            "X-Beyul-Is-Admin": "false",
        },
    )
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready to open."},
    )
    market_slug = publish_response.json()["slug"]

    status_response = client.post(
        f"/api/v1/markets/{market_slug}/status",
        json={"status": "open"},
    )

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "open"


def test_owner_can_cancel_open_market_order() -> None:
    client = TestClient(app)
    create_response = client.post(
        "/api/v1/market-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000124",
            "X-Beyul-Username": "cancel_user",
            "X-Beyul-Display-Name": "Cancel User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Will this order be cancelled?",
            "slug": "order-cancel-market",
            "question": "Will this order be cancelled?",
            "description": "Cancel order test.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(
        f"/api/v1/market-requests/{request_id}/submit",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000124",
            "X-Beyul-Username": "cancel_user",
            "X-Beyul-Display-Name": "Cancel User",
            "X-Beyul-Is-Admin": "false",
        },
    )
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for cancellation test."},
    )
    market_slug = publish_response.json()["slug"]
    yes_outcome_id = publish_response.json()["outcomes"][0]["id"]

    order_response = client.post(
        f"/api/v1/markets/{market_slug}/orders",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000124",
            "X-Beyul-Username": "cancel_user",
            "X-Beyul-Display-Name": "Cancel User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "outcome_id": yes_outcome_id,
            "side": "buy",
            "order_type": "limit",
            "quantity": "10",
            "price": "0.44",
            "client_order_id": "cancel-me",
        },
    )
    order_id = order_response.json()["id"]

    cancel_response = client.delete(
        f"/api/v1/markets/{market_slug}/orders/{order_id}",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000124",
            "X-Beyul-Username": "cancel_user",
            "X-Beyul-Display-Name": "Cancel User",
            "X-Beyul-Is-Admin": "false",
        },
    )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"


def test_portfolio_endpoint_returns_seeded_balance_snapshot() -> None:
    client = TestClient(app)

    response = client.get(
        "/api/v1/portfolio/me",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000222",
            "X-Beyul-Username": "portfolio_user",
            "X-Beyul-Display-Name": "Portfolio User",
            "X-Beyul-Is-Admin": "false",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["balances"][0]["asset_code"] == "USDC"
    assert payload["balances"][0]["available_balance"] == "1000"


def test_admin_can_fund_balance_and_oracle_finalize_market() -> None:
    client = TestClient(app)

    fund_response = client.post(
        "/api/v1/admin/fund-balance",
        json={
            "profile_id": "00000000-0000-0000-0000-000000000333",
            "asset_code": "USDC",
            "rail_mode": "onchain",
            "amount": "250",
            "description": "Fund user for trading",
        },
    )

    assert fund_response.status_code == 200
    assert fund_response.json()["balances"][0]["available_balance"] == "250"

    create_response = client.post(
        "/api/v1/market-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000334",
            "X-Beyul-Username": "settle_user",
            "X-Beyul-Display-Name": "Settle User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "title": "Will settlement work?",
            "slug": "settlement-work-market",
            "question": "Will settlement work?",
            "description": "Settle this market.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(
        f"/api/v1/market-requests/{request_id}/submit",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000334",
            "X-Beyul-Username": "settle_user",
            "X-Beyul-Display-Name": "Settle User",
            "X-Beyul-Is-Admin": "false",
        },
    )
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for settlement."},
    )
    market_payload = publish_response.json()

    request_settlement_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/settlement-requests",
        headers={
            "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000334",
            "X-Beyul-Username": "settle_user",
            "X-Beyul-Display-Name": "Settle User",
            "X-Beyul-Is-Admin": "false",
        },
        json={
            "source_reference_url": "https://example.com/final",
            "notes": "Request neutral oracle resolution.",
        },
    )
    assert request_settlement_response.status_code == 200
    candidate_id = request_settlement_response.json()["candidate_id"]

    settle_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/oracle/finalize",
        headers={"X-Satta-Oracle-Secret": "dev-oracle-secret"},
        json={
            "winning_outcome_id": market_payload["outcomes"][0]["id"],
            "candidate_id": candidate_id,
            "source_reference_url": "https://example.com/final",
            "notes": "Official result confirmed.",
        },
    )

    assert settle_response.status_code == 200
    assert settle_response.json()["winning_outcome_id"] == market_payload["outcomes"][0]["id"]
    assert settle_response.json()["status"] == "finalized"


def test_sell_order_uses_complementary_collateral_in_portfolio_snapshot() -> None:
    client = TestClient(app)
    user_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000335",
        "X-Beyul-Username": "sell_user",
        "X-Beyul-Display-Name": "Sell User",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_headers,
        json={
            "title": "Will complementary collateral be reserved?",
            "slug": "complementary-collateral-market",
            "question": "Will complementary collateral be reserved?",
            "description": "Reserve the no-side collateral via Sell Yes.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=user_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for sell-side collateral test."},
    )
    market_payload = publish_response.json()

    order_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/orders",
        headers=user_headers,
        json={
            "outcome_id": market_payload["outcomes"][0]["id"],
            "side": "sell",
            "order_type": "limit",
            "quantity": "25",
            "price": "0.55",
            "client_order_id": "sell-collateral",
        },
    )

    assert order_response.status_code == 201
    assert order_response.json()["max_total_cost"] == "11.25"

    portfolio_response = client.get("/api/v1/portfolio/me", headers=user_headers)
    assert portfolio_response.status_code == 200
    assert portfolio_response.json()["balances"][0]["reserved_balance"] == "11.25"
    assert portfolio_response.json()["balances"][0]["available_balance"] == "988.75"


def test_settlement_cancels_active_orders() -> None:
    client = TestClient(app)
    user_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000336",
        "X-Beyul-Username": "settle_cancel_user",
        "X-Beyul-Display-Name": "Settle Cancel User",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_headers,
        json={
            "title": "Will settlement cancel orders?",
            "slug": "settlement-cancels-orders",
            "question": "Will settlement cancel orders?",
            "description": "Open orders should not survive settlement.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=user_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for settlement cancellation test."},
    )
    market_payload = publish_response.json()

    order_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/orders",
        headers=user_headers,
        json={
            "outcome_id": market_payload["outcomes"][0]["id"],
            "side": "buy",
            "order_type": "limit",
            "quantity": "10",
            "price": "0.40",
            "client_order_id": "cancel-on-settle",
        },
    )
    assert order_response.status_code == 201

    request_settlement_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/settlement-requests",
        headers=user_headers,
        json={
            "source_reference_url": "https://example.com/settled",
            "notes": "Request oracle settlement.",
        },
    )
    assert request_settlement_response.status_code == 200

    settle_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/oracle/finalize",
        headers={"X-Satta-Oracle-Secret": "dev-oracle-secret"},
        json={
            "winning_outcome_id": market_payload["outcomes"][0]["id"],
            "candidate_id": request_settlement_response.json()["candidate_id"],
            "source_reference_url": "https://example.com/settled",
            "notes": "Settled for cancellation regression test.",
        },
    )
    assert settle_response.status_code == 200

    my_orders_response = client.get(f"/api/v1/markets/{market_payload['slug']}/orders/me", headers=user_headers)
    assert my_orders_response.status_code == 200
    assert my_orders_response.json()[0]["status"] == "cancelled"
    assert my_orders_response.json()[0]["remaining_quantity"] == "0"


def test_market_resolution_endpoint_returns_candidate_state() -> None:
    client = TestClient(app)
    user_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000337",
        "X-Beyul-Username": "resolution_user",
        "X-Beyul-Display-Name": "Resolution User",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_headers,
        json={
            "title": "Will oracle resolution state render?",
            "slug": "oracle-resolution-state-market",
            "question": "Will oracle resolution state render?",
            "description": "Resolution candidate state should be queryable.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=user_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for oracle state test."},
    )
    market_payload = publish_response.json()

    request_settlement_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/settlement-requests",
        headers=user_headers,
        json={
            "source_reference_url": "https://example.com/oracle-state",
            "notes": "Request oracle state",
        },
    )
    assert request_settlement_response.status_code == 200

    resolution_response = client.get(f"/api/v1/markets/{market_payload['slug']}/resolution")
    assert resolution_response.status_code == 200
    payload = resolution_response.json()
    assert payload["current_status"] == "pending_oracle"
    assert payload["current_payload"]["status"] == "pending_oracle"
    assert len(payload["candidates"]) == 1
    assert payload["candidates"][0]["status"] == "proposed"


def test_market_dispute_moves_market_into_disputed_state() -> None:
    client = TestClient(app)
    user_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000338",
        "X-Beyul-Username": "dispute_user",
        "X-Beyul-Display-Name": "Dispute User",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_headers,
        json={
            "title": "Will a dispute transition work?",
            "slug": "dispute-transition-market",
            "question": "Will a dispute transition work?",
            "description": "A dispute should move the market into disputed.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=user_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for dispute test."},
    )
    market_payload = publish_response.json()

    request_settlement_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/settlement-requests",
        headers=user_headers,
        json={
            "source_reference_url": "https://example.com/dispute",
            "notes": "Request oracle resolution before dispute",
        },
    )
    assert request_settlement_response.status_code == 200

    dispute_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/disputes",
        headers=user_headers,
        json={
            "title": "Source mismatch",
            "reason": "The pending oracle candidate cites the wrong source window.",
        },
    )
    assert dispute_response.status_code == 201
    assert dispute_response.json()["status"] == "open"

    market_response = client.get(f"/api/v1/markets/{market_payload['slug']}")
    assert market_response.status_code == 200
    assert market_response.json()["status"] == "disputed"

    resolution_response = client.get(f"/api/v1/markets/{market_payload['slug']}/resolution")
    assert resolution_response.status_code == 200
    payload = resolution_response.json()
    assert payload["current_status"] == "disputed"
    assert payload["current_payload"]["latest_dispute_id"] == dispute_response.json()["id"]
    assert len(payload["disputes"]) == 1
    assert payload["disputes"][0]["title"] == "Source mismatch"


def test_market_dispute_evidence_is_returned_in_resolution_state() -> None:
    client = TestClient(app)
    user_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000339",
        "X-Beyul-Username": "evidence_user",
        "X-Beyul-Display-Name": "Evidence User",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_headers,
        json={
            "title": "Will dispute evidence attach?",
            "slug": "dispute-evidence-market",
            "question": "Will dispute evidence attach?",
            "description": "Evidence should be visible in the resolution timeline.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=user_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for dispute evidence test."},
    )
    market_payload = publish_response.json()

    client.post(
        f"/api/v1/markets/{market_payload['slug']}/settlement-requests",
        headers=user_headers,
        json={
            "source_reference_url": "https://example.com/dispute-evidence",
            "notes": "Request oracle resolution before evidence test",
        },
    )
    dispute_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/disputes",
        headers=user_headers,
        json={
            "title": "Chainlink window mismatch",
            "reason": "The proposed window does not match the market contract.",
        },
    )
    dispute_id = dispute_response.json()["id"]

    evidence_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/disputes/{dispute_id}/evidence",
        headers=user_headers,
        json={
            "evidence_type": "source_link",
            "url": "https://example.com/evidence/window",
            "description": "Archived source snapshot for the correct time window.",
            "payload": {"snapshot": "2026-04-01T02:00:00Z"},
        },
    )

    assert evidence_response.status_code == 200
    assert len(evidence_response.json()["evidence"]) == 1
    assert evidence_response.json()["evidence"][0]["url"] == "https://example.com/evidence/window"

    resolution_response = client.get(f"/api/v1/markets/{market_payload['slug']}/resolution")
    assert resolution_response.status_code == 200
    payload = resolution_response.json()
    assert len(payload["disputes"]) == 1
    assert len(payload["disputes"][0]["evidence"]) == 1
    assert payload["disputes"][0]["evidence"][0]["description"] == "Archived source snapshot for the correct time window."
    assert any(event["event_type"] == "dispute_evidence_added" for event in payload["history"])


def test_dismissed_dispute_restores_awaiting_resolution_state() -> None:
    client = TestClient(app)
    user_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000340",
        "X-Beyul-Username": "dismiss_user",
        "X-Beyul-Display-Name": "Dismiss User",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_headers,
        json={
            "title": "Will a dismissed dispute restore the oracle path?",
            "slug": "dismissed-dispute-market",
            "question": "Will a dismissed dispute restore the oracle path?",
            "description": "Dismissed disputes should not leave the market stuck.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=user_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for dismissed-dispute test."},
    )
    market_payload = publish_response.json()

    settlement_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/settlement-requests",
        headers=user_headers,
        json={
            "source_reference_url": "https://example.com/oracle-path",
            "notes": "Request oracle resolution before dispute review test",
        },
    )
    assert settlement_response.status_code == 200

    dispute_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/disputes",
        headers=user_headers,
        json={
            "title": "Temporary mismatch",
            "reason": "This dispute will be dismissed by the oracle review flow.",
        },
    )
    dispute_id = dispute_response.json()["id"]

    review_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/oracle/disputes/{dispute_id}/review",
        headers={"X-Satta-Oracle-Secret": "dev-oracle-secret"},
        json={
            "status": "dismissed",
            "review_notes": "Evidence did not overturn the original oracle request.",
        },
    )

    assert review_response.status_code == 200
    assert review_response.json()["status"] == "dismissed"
    assert review_response.json()["review_notes"] == "Evidence did not overturn the original oracle request."

    market_response = client.get(f"/api/v1/markets/{market_payload['slug']}")
    assert market_response.status_code == 200
    assert market_response.json()["status"] == "awaiting_resolution"

    resolution_response = client.get(f"/api/v1/markets/{market_payload['slug']}/resolution")
    assert resolution_response.status_code == 200
    payload = resolution_response.json()
    assert payload["current_status"] == "pending_oracle"
    assert payload["current_payload"]["dispute_review_state"] == "dismissed"
    assert payload["disputes"][0]["status"] == "dismissed"
    assert payload["candidates"][0]["status"] == "proposed"
    assert any(event["event_type"] == "dispute_reviewed" for event in payload["history"])


def test_market_rule_evidence_requires_description() -> None:
    client = TestClient(app)
    user_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000341",
        "X-Beyul-Username": "validation_user",
        "X-Beyul-Display-Name": "Validation User",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_headers,
        json={
            "title": "Will evidence validation work?",
            "slug": "evidence-validation-market",
            "question": "Will evidence validation work?",
            "description": "Evidence validation should reject incomplete rule references.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=user_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for evidence validation test."},
    )
    market_payload = publish_response.json()
    client.post(
        f"/api/v1/markets/{market_payload['slug']}/settlement-requests",
        headers=user_headers,
        json={"source_reference_url": "https://example.com/rules", "notes": "prep"},
    )
    dispute_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/disputes",
        headers=user_headers,
        json={"title": "Rule mismatch", "reason": "Need to cite a rule section."},
    )
    dispute_id = dispute_response.json()["id"]

    invalid_evidence_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/disputes/{dispute_id}/evidence",
        headers=user_headers,
        json={
            "evidence_type": "market_rule",
            "payload": {"section": "2.1"},
        },
    )

    assert invalid_evidence_response.status_code == 422


def test_cannot_open_second_active_dispute_for_same_resolution() -> None:
    client = TestClient(app)
    user_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000342",
        "X-Beyul-Username": "single_dispute_user",
        "X-Beyul-Display-Name": "Single Dispute User",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_headers,
        json={
            "title": "Will duplicate disputes be blocked?",
            "slug": "duplicate-dispute-block-market",
            "question": "Will duplicate disputes be blocked?",
            "description": "Only one active dispute should exist for the same active resolution.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=user_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for duplicate dispute test."},
    )
    market_payload = publish_response.json()

    settlement_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/settlement-requests",
        headers=user_headers,
        json={"source_reference_url": "https://example.com/duplicate", "notes": "prep"},
    )
    assert settlement_response.status_code == 200

    first_dispute = client.post(
        f"/api/v1/markets/{market_payload['slug']}/disputes",
        headers=user_headers,
        json={"title": "First dispute", "reason": "Open the only active dispute."},
    )
    assert first_dispute.status_code == 201

    second_dispute = client.post(
        f"/api/v1/markets/{market_payload['slug']}/disputes",
        headers=user_headers,
        json={"title": "Second dispute", "reason": "This should be rejected while the first dispute is still active."},
    )

    assert second_dispute.status_code == 409


def test_cannot_finalize_market_while_dispute_is_still_open() -> None:
    client = TestClient(app)
    user_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000343",
        "X-Beyul-Username": "finalize_guard_user",
        "X-Beyul-Display-Name": "Finalize Guard User",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_headers,
        json={
            "title": "Will finalization be blocked with an active dispute?",
            "slug": "finalization-guard-market",
            "question": "Will finalization be blocked with an active dispute?",
            "description": "Oracle finalization should be blocked until active disputes are closed.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=user_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for finalization guard test."},
    )
    market_payload = publish_response.json()

    settlement_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/settlement-requests",
        headers=user_headers,
        json={"source_reference_url": "https://example.com/finalize-guard", "notes": "prep"},
    )
    assert settlement_response.status_code == 200

    dispute_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/disputes",
        headers=user_headers,
        json={"title": "Open dispute", "reason": "Keep this dispute open during finalization."},
    )
    assert dispute_response.status_code == 201

    finalize_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/oracle/finalize",
        headers={"X-Satta-Oracle-Secret": "dev-oracle-secret"},
        json={
            "winning_outcome_id": market_payload["outcomes"][0]["id"],
            "candidate_id": settlement_response.json()["candidate_id"],
            "source_reference_url": "https://example.com/finalize-guard",
            "notes": "This should be blocked.",
        },
    )

    assert finalize_response.status_code == 409
    assert "active dispute" in finalize_response.json()["detail"]


def test_order_validation_returns_clear_price_conflict_detail() -> None:
    client = TestClient(app)
    user_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000344",
        "X-Beyul-Username": "order_validation_user",
        "X-Beyul-Display-Name": "Order Validation User",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_headers,
        json={
            "title": "Will invalid price orders be rejected clearly?",
            "slug": "invalid-price-order-market",
            "question": "Will invalid price orders be rejected clearly?",
            "description": "Order conflict detail should be explicit for client guidance.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=user_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for order validation test."},
    )
    market_payload = publish_response.json()

    fund_response = client.post(
        "/api/v1/admin/fund-balance",
        json={
            "profile_id": user_headers["X-Beyul-User-Id"],
            "asset_code": "USDC",
            "rail_mode": "onchain",
            "amount": "100",
            "description": "Funding for validation test",
        },
    )
    assert fund_response.status_code == 200

    invalid_order_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/orders",
        headers=user_headers,
        json={
            "outcome_id": market_payload["outcomes"][0]["id"],
            "side": "buy",
            "order_type": "limit",
            "quantity": "5",
            "price": "55",
        },
    )

    assert invalid_order_response.status_code == 409
    assert invalid_order_response.json()["detail"] == "Order price must be between 0 and 1"


def test_memory_smoke_flow_with_orders_and_resolution_lifecycle() -> None:
    client = TestClient(app)
    user_a_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000345",
        "X-Beyul-Username": "smoke_a",
        "X-Beyul-Display-Name": "Smoke User A",
        "X-Beyul-Is-Admin": "false",
    }
    user_b_headers = {
        "X-Beyul-User-Id": "00000000-0000-0000-0000-000000000346",
        "X-Beyul-Username": "smoke_b",
        "X-Beyul-Display-Name": "Smoke User B",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_a_headers,
        json={
            "title": "Will the full smoke lifecycle pass?",
            "slug": "memory-smoke-lifecycle-market",
            "question": "Will the full smoke lifecycle pass?",
            "description": "Exercise trading plus settlement and dispute lifecycle in memory mode.",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
        },
    )
    request_id = create_response.json()["id"]
    client.post(f"/api/v1/market-requests/{request_id}/submit", headers=user_a_headers)
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{request_id}/publish",
        json={"review_notes": "Ready for smoke test."},
    )
    market_payload = publish_response.json()
    yes_outcome_id = market_payload["outcomes"][0]["id"]

    client.post(
        "/api/v1/admin/fund-balance",
        json={
            "profile_id": user_a_headers["X-Beyul-User-Id"],
            "asset_code": "USDC",
            "rail_mode": "onchain",
            "amount": "100",
            "description": "Funding for smoke user A",
        },
    )
    client.post(
        "/api/v1/admin/fund-balance",
        json={
            "profile_id": user_b_headers["X-Beyul-User-Id"],
            "asset_code": "USDC",
            "rail_mode": "onchain",
            "amount": "100",
            "description": "Funding for smoke user B",
        },
    )

    buy_order = client.post(
        f"/api/v1/markets/{market_payload['slug']}/orders",
        headers=user_a_headers,
        json={
            "outcome_id": yes_outcome_id,
            "side": "buy",
            "order_type": "limit",
            "quantity": "5",
            "price": "0.55",
        },
    )
    sell_order = client.post(
        f"/api/v1/markets/{market_payload['slug']}/orders",
        headers=user_b_headers,
        json={
            "outcome_id": yes_outcome_id,
            "side": "sell",
            "order_type": "limit",
            "quantity": "5",
            "price": "0.55",
        },
    )

    assert buy_order.status_code == 201
    assert sell_order.status_code == 201

    settlement_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/settlement-requests",
        headers=user_a_headers,
        json={"source_reference_url": "https://example.com/smoke", "notes": "prep"},
    )
    assert settlement_response.status_code == 200

    dispute_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/disputes",
        headers=user_b_headers,
        json={"title": "Smoke dispute", "reason": "Exercise the dispute lifecycle."},
    )
    assert dispute_response.status_code == 201
    dispute_id = dispute_response.json()["id"]

    evidence_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/disputes/{dispute_id}/evidence",
        headers=user_b_headers,
        json={
            "evidence_type": "source_link",
            "url": "https://example.com/smoke-evidence",
            "description": "Smoke evidence",
        },
    )
    assert evidence_response.status_code == 200

    review_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/oracle/disputes/{dispute_id}/review",
        headers={"X-Satta-Oracle-Secret": "dev-oracle-secret"},
        json={"status": "dismissed", "review_notes": "Dismiss and resume oracle path."},
    )
    assert review_response.status_code == 200

    finalize_response = client.post(
        f"/api/v1/markets/{market_payload['slug']}/oracle/finalize",
        headers={"X-Satta-Oracle-Secret": "dev-oracle-secret"},
        json={
            "winning_outcome_id": yes_outcome_id,
            "candidate_id": settlement_response.json()["candidate_id"],
            "source_reference_url": "https://example.com/smoke-final",
            "notes": "Finalize smoke lifecycle.",
        },
    )
    assert finalize_response.status_code == 200

    final_market_response = client.get(f"/api/v1/markets/{market_payload['slug']}")
    resolution_response = client.get(f"/api/v1/markets/{market_payload['slug']}/resolution")
    user_a_portfolio = client.get("/api/v1/portfolio/me", headers=user_a_headers)
    user_b_portfolio = client.get("/api/v1/portfolio/me", headers=user_b_headers)

    assert final_market_response.status_code == 200
    assert final_market_response.json()["status"] == "settled"
    assert resolution_response.status_code == 200
    assert resolution_response.json()["current_status"] == "finalized"
    assert resolution_response.json()["disputes"][0]["status"] == "dismissed"
    assert len(resolution_response.json()["history"]) >= 6
    assert user_a_portfolio.status_code == 200
    assert user_b_portfolio.status_code == 200


def test_uma_oracle_service_returns_expected_dev_metadata() -> None:
    previous_provider = settings.oracle_provider
    previous_chain_id = settings.oracle_chain_id
    previous_reward = settings.oracle_reward_wei
    previous_bond = settings.oracle_bond_wei
    previous_mode = settings.oracle_execution_mode
    try:
        settings.oracle_provider = "uma"
        settings.oracle_chain_id = 137
        settings.oracle_reward_wei = "100000000000000000"
        settings.oracle_bond_wei = "500000000000000000"
        settings.oracle_execution_mode = "simulated"

        service = UMAOracleService()
        request = OracleResolutionRequest(
            market_id=UUID("00000000-0000-0000-0000-000000000401"),
            market_slug="uma-adapter-market",
            candidate_id=UUID("00000000-0000-0000-0000-000000000402"),
            resolution_mode="oracle",
            source_reference_url="https://example.com/uma-source",
            notes="UMA adapter metadata test",
            finalizes_at=datetime.now(timezone.utc) + timedelta(minutes=60),
        )

        payload = asyncio.run(service.begin_resolution(request))

        assert payload["provider"] == "uma_optimistic_oracle_v3"
        assert payload["provider_kind"] == "optimistic"
        assert payload["network"] == "polygon"
        assert payload["assertion_id"].startswith("uma-dev-")
        assert payload["assertion_identifier"] == "ASSERT_TRUTH2"
        assert payload["assertion_method"] == "assertTruth"
        assert payload["chain_id"] == 137
        assert "bond_wei" in payload
        assert "reward_wei" in payload
        assert "liveness_minutes" in payload
        assert payload["simulated_submission"] is True
        assert payload["submission_status"] == "simulated"
    finally:
        settings.oracle_provider = previous_provider
        settings.oracle_chain_id = previous_chain_id
        settings.oracle_reward_wei = previous_reward
        settings.oracle_bond_wei = previous_bond
        settings.oracle_execution_mode = previous_mode


def test_resolution_reconcile_endpoint_returns_payload_status() -> None:
    client = TestClient(app)
    request_id = uuid4()
    user_headers = {
        "X-Beyul-User-Id": str(uuid4()),
        "X-Beyul-Username": "reconcile_user",
        "X-Beyul-Display-Name": "Reconcile User",
        "X-Beyul-Is-Admin": "false",
    }

    create_response = client.post(
        "/api/v1/market-requests",
        headers=user_headers,
        json={
            "title": "Reconcile market",
            "slug": f"reconcile-market-{request_id.hex[:8]}",
            "question": "Will reconcile work?",
            "description": "Testing oracle reconcile endpoint.",
            "template_key": "event_outcome",
            "market_access_mode": "public",
            "requested_rail": "onchain",
            "resolution_mode": "oracle",
            "community_id": str(client.get("/api/v1/communities").json()[0]["id"]),
        },
    )
    assert create_response.status_code == 201
    created_request = create_response.json()
    submit_response = client.post(f"/api/v1/market-requests/{created_request['id']}/submit", headers=user_headers)
    assert submit_response.status_code == 200
    publish_response = client.post(
        f"/api/v1/admin/market-requests/{created_request['id']}/publish",
        json={"review_notes": "publish"},
    )
    assert publish_response.status_code == 201
    market = publish_response.json()

    settlement_response = client.post(
        f"/api/v1/markets/{market['slug']}/settlement-requests",
        headers=user_headers,
        json={"source_reference_url": "https://example.com"},
    )
    assert settlement_response.status_code == 200

    reconcile_response = client.post(
        f"/api/v1/markets/{market['slug']}/oracle/reconcile",
        headers={"X-Satta-Oracle-Secret": settings.oracle_callback_secret},
        json={},
    )
    assert reconcile_response.status_code == 200
    payload = reconcile_response.json()
    assert payload["current_payload"]["submission_status"] == "simulated"
    assert payload["current_payload"]["last_reconciled_at"]


def test_uma_oracle_service_live_mode_requires_runtime_config() -> None:
    previous_provider = settings.oracle_provider
    previous_mode = settings.oracle_execution_mode
    previous_rpc_url = settings.oracle_rpc_url
    previous_private_key = settings.oracle_signer_private_key
    previous_signer_address = settings.oracle_signer_address
    previous_oo_address = settings.oracle_uma_oo_address
    previous_currency_address = settings.oracle_currency_address
    try:
        settings.oracle_provider = "uma"
        settings.oracle_execution_mode = "live"
        settings.oracle_rpc_url = None
        settings.oracle_signer_private_key = None
        settings.oracle_signer_address = None
        settings.oracle_uma_oo_address = None
        settings.oracle_currency_address = None

        service = UMAOracleService()
        request = OracleResolutionRequest(
            market_id=UUID("00000000-0000-0000-0000-000000000501"),
            market_slug="uma-live-config-test",
            candidate_id=UUID("00000000-0000-0000-0000-000000000502"),
            resolution_mode="oracle",
            source_reference_url="https://example.com/uma-live-source",
            notes="UMA live config guard test",
            finalizes_at=datetime.now(timezone.utc) + timedelta(minutes=60),
        )

        with pytest.raises(OracleConfigurationError):
            asyncio.run(service.begin_resolution(request))
    finally:
        settings.oracle_provider = previous_provider
        settings.oracle_execution_mode = previous_mode
        settings.oracle_rpc_url = previous_rpc_url
        settings.oracle_signer_private_key = previous_private_key
        settings.oracle_signer_address = previous_signer_address
        settings.oracle_uma_oo_address = previous_oo_address
        settings.oracle_currency_address = previous_currency_address

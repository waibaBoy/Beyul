"""Email notification service.

Renders and sends transactional emails. Uses a simple template system
that can be wired to any email provider (SendGrid, SES, Resend, etc.).

In development mode, emails are logged instead of sent.
"""

import logging
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailTemplate(str, Enum):
    WELCOME = "welcome"
    TRADE_CONFIRMATION = "trade_confirmation"
    ORDER_FILLED = "order_filled"
    MARKET_SETTLED = "market_settled"
    DEPOSIT_CONFIRMED = "deposit_confirmed"
    WITHDRAWAL_PROCESSED = "withdrawal_processed"
    PASSWORD_RESET = "password_reset"
    WEEKLY_DIGEST = "weekly_digest"


TEMPLATES: dict[EmailTemplate, dict] = {
    EmailTemplate.WELCOME: {
        "subject": "Welcome to Satta — Start trading predictions",
        "body": (
            "Hi {display_name},\n\n"
            "Welcome to Satta! You're now part of a community of prediction traders.\n\n"
            "Here's how to get started:\n"
            "1. Fund your wallet at {site_url}/wallet\n"
            "2. Browse markets at {site_url}/markets\n"
            "3. Place your first trade\n"
            "4. Or create your own market at {site_url}/market-requests\n\n"
            "If you have any questions, check our about page at {site_url}/about.\n\n"
            "Happy trading!\n"
            "— The Satta Team"
        ),
    },
    EmailTemplate.TRADE_CONFIRMATION: {
        "subject": "Trade Executed — {market_title}",
        "body": (
            "Hi {display_name},\n\n"
            "Your {side} order on \"{market_title}\" has been executed.\n\n"
            "Details:\n"
            "- Outcome: {outcome_label}\n"
            "- Quantity: {quantity}\n"
            "- Price: {price}\n"
            "- Notional: {gross_notional}\n"
            "- Fee: {fee_amount}\n"
            "- Time: {executed_at}\n\n"
            "View your portfolio: {site_url}/portfolio\n\n"
            "— Satta"
        ),
    },
    EmailTemplate.ORDER_FILLED: {
        "subject": "Order Filled — {market_title}",
        "body": (
            "Hi {display_name},\n\n"
            "Your order on \"{market_title}\" has been fully filled.\n\n"
            "View your positions: {site_url}/portfolio\n\n"
            "— Satta"
        ),
    },
    EmailTemplate.MARKET_SETTLED: {
        "subject": "Market Settled — {market_title}",
        "body": (
            "Hi {display_name},\n\n"
            "The market \"{market_title}\" has been settled.\n"
            "Winning outcome: {winning_outcome}\n\n"
            "Your payout has been credited to your balance.\n"
            "View details: {site_url}/portfolio\n\n"
            "— Satta"
        ),
    },
    EmailTemplate.DEPOSIT_CONFIRMED: {
        "subject": "Deposit Confirmed — {amount} {asset_code}",
        "body": (
            "Hi {display_name},\n\n"
            "Your deposit of {amount} {asset_code} has been confirmed.\n"
            "Your updated balance is available at {site_url}/wallet.\n\n"
            "— Satta"
        ),
    },
    EmailTemplate.WITHDRAWAL_PROCESSED: {
        "subject": "Withdrawal Processed — {amount} {asset_code}",
        "body": (
            "Hi {display_name},\n\n"
            "Your withdrawal of {amount} {asset_code} has been processed.\n"
            "Fee: {fee_amount}\nNet: {net_amount}\n\n"
            "Transaction history: {site_url}/wallet\n\n"
            "— Satta"
        ),
    },
    EmailTemplate.PASSWORD_RESET: {
        "subject": "Password Reset Request — Satta",
        "body": (
            "Hi {display_name},\n\n"
            "We received a password reset request for your account.\n"
            "If you didn't request this, you can safely ignore this email.\n\n"
            "Reset link: {reset_url}\n\n"
            "— Satta"
        ),
    },
    EmailTemplate.WEEKLY_DIGEST: {
        "subject": "Your Weekly Trading Digest — Satta",
        "body": (
            "Hi {display_name},\n\n"
            "Here's your weekly trading summary:\n"
            "- Trades this week: {trade_count}\n"
            "- Volume: {total_volume}\n"
            "- Realized PnL: {realized_pnl}\n\n"
            "Keep trading: {site_url}/markets\n\n"
            "— Satta"
        ),
    },
}


class EmailService:
    def __init__(self) -> None:
        self._provider = settings.app_env

    def render(self, template: EmailTemplate, context: dict) -> tuple[str, str]:
        tmpl = TEMPLATES[template]
        ctx = {**context, "site_url": getattr(settings, "site_url", "https://satta.app")}
        subject = tmpl["subject"].format_map(_SafeDict(ctx))
        body = tmpl["body"].format_map(_SafeDict(ctx))
        return subject, body

    async def send(self, to_email: str, template: EmailTemplate, context: dict) -> bool:
        subject, body = self.render(template, context)

        if settings.app_env != "production":
            logger.info(
                "EMAIL [dev] to=%s subject=%s\n%s",
                to_email, subject, body,
            )
            return True

        logger.info("EMAIL [prod] to=%s subject=%s (provider not configured)", to_email, subject)
        return False

    async def send_bulk(self, recipients: list[tuple[str, dict]], template: EmailTemplate) -> int:
        sent = 0
        for email, ctx in recipients:
            if await self.send(email, template, ctx):
                sent += 1
        return sent


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"

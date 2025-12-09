"""
Name of Application: Catalyst Trading System
Name of file: agent/alerts.py
Version: 1.0.0
Last Updated: 2025-12-09
Purpose: Human notification system for the autonomous agent

REVISION HISTORY:
v1.0.0 (2025-12-09) - Initial implementation
- Email alerts via SMTP
- Webhook alerts (Discord/Slack)
- Different severity levels

Description:
This module handles all human notifications from the autonomous agent.
It supports multiple channels (email, webhook) and different severity levels.
"""

import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
import structlog

logger = structlog.get_logger()

HK_TZ = ZoneInfo("Asia/Hong_Kong")


class AlertSystem:
    """Human notification system."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        email: Optional[str] = None,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_pass: Optional[str] = None,
    ):
        """Initialize alert system.

        Args:
            webhook_url: Discord/Slack webhook URL
            email: Email address for alerts
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_pass: SMTP password
        """
        self.webhook_url = webhook_url
        self.email = email
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass

        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30)
        return self._http_client

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    # =========================================================================
    # Core Alert Methods
    # =========================================================================

    async def send(
        self,
        severity: str,
        subject: str,
        message: str,
    ):
        """Send alert via all configured channels.

        Args:
            severity: Alert severity (info, warning, critical)
            subject: Alert subject
            message: Alert message body
        """
        timestamp = datetime.now(HK_TZ).strftime("%Y-%m-%d %H:%M:%S HKT")
        full_message = f"[{timestamp}] [{severity.upper()}]\n\n{message}"

        # Send via webhook
        if self.webhook_url:
            await self._send_webhook(severity, subject, full_message)

        # Send via email
        if self.email and self.smtp_user:
            await self._send_email(severity, subject, full_message)

        logger.info(
            "Alert sent",
            severity=severity,
            subject=subject,
        )

    async def _send_webhook(
        self,
        severity: str,
        subject: str,
        message: str,
    ):
        """Send alert via webhook."""
        try:
            client = await self._get_client()

            # Detect Discord vs Slack format
            if "discord" in self.webhook_url.lower():
                payload = self._format_discord(severity, subject, message)
            else:
                payload = self._format_slack(severity, subject, message)

            response = await client.post(
                self.webhook_url,
                json=payload,
            )
            response.raise_for_status()

        except Exception as e:
            logger.error("Failed to send webhook alert", error=str(e))

    def _format_discord(
        self,
        severity: str,
        subject: str,
        message: str,
    ) -> dict:
        """Format message for Discord webhook."""
        colors = {
            "info": 0x3498DB,  # Blue
            "warning": 0xF39C12,  # Orange
            "critical": 0xE74C3C,  # Red
        }

        return {
            "embeds": [
                {
                    "title": f"{self._get_emoji(severity)} {subject}",
                    "description": message[:4000],  # Discord limit
                    "color": colors.get(severity, 0x95A5A6),
                    "footer": {"text": "Catalyst Trading Agent"},
                }
            ]
        }

    def _format_slack(
        self,
        severity: str,
        subject: str,
        message: str,
    ) -> dict:
        """Format message for Slack webhook."""
        return {
            "text": f"{self._get_emoji(severity)} *{subject}*",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{subject}*\n{message[:3000]}",
                    },
                }
            ],
        }

    def _get_emoji(self, severity: str) -> str:
        """Get emoji for severity."""
        emojis = {
            "info": "info",
            "warning": "warning",
            "critical": "rotating_light",
        }
        return emojis.get(severity, "bell")

    async def _send_email(
        self,
        severity: str,
        subject: str,
        message: str,
    ):
        """Send alert via email."""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = self.email
            msg["Subject"] = f"[Catalyst {severity.upper()}] {subject}"

            body = f"""
Catalyst Trading Agent Alert
============================
Severity: {severity.upper()}
Time: {datetime.now(HK_TZ).strftime('%Y-%m-%d %H:%M:%S HKT')}

{message}

---
This is an automated message from your trading agent.
"""
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)

        except Exception as e:
            logger.error("Failed to send email alert", error=str(e))

    # =========================================================================
    # Specific Alert Types
    # =========================================================================

    async def notify_startup(
        self,
        environment: str,
        exchange: str,
    ):
        """Send startup notification."""
        await self.send(
            severity="info",
            subject="Agent Started",
            message=f"""
The Catalyst Trading Agent has started.

Environment: {environment}
Exchange: {exchange}

The agent is now monitoring the market and will send alerts
for trades, warnings, and important events.
""",
        )

    async def notify_shutdown(self):
        """Send shutdown notification."""
        await self.send(
            severity="info",
            subject="Agent Shutdown",
            message="The Catalyst Trading Agent has shut down gracefully.",
        )

    async def error(self, message: str):
        """Send error alert."""
        await self.send(
            severity="critical",
            subject="Agent Error",
            message=message,
        )

    async def attention_needed(self, decision):
        """Alert human that attention is needed."""
        await self.send(
            severity="warning",
            subject=f"Attention Needed: {decision.symbol or 'General'}",
            message=f"""
The agent requires human attention.

Symbol: {decision.symbol}
Action: {decision.action}
Confidence: {decision.confidence}%

Reason: {decision.human_reason or 'No specific reason provided'}

Reasoning:
{decision.reasoning[:500]}

Uncertainties:
{chr(10).join(['- ' + u for u in decision.uncertainties[:5]])}
""",
        )

    async def daily_summary(self, insights):
        """Send daily trading summary."""
        await self.send(
            severity="info",
            subject="Daily Trading Summary",
            message=f"""
END OF DAY SUMMARY
==================

{insights.daily_summary_for_human}

Market Summary:
{insights.market_summary}

Patterns Observed: {len(insights.patterns_observed)}
Calibration Adjustments: {len(insights.calibration_adjustments)}

Key Observations:
{chr(10).join(['- ' + p.get('pattern', str(p)) for p in insights.patterns_observed[:5]])}
""",
        )

    async def strategic_update(self, update):
        """Send weekly strategic update."""
        severity = "warning" if update.needs_human_decision else "info"

        await self.send(
            severity=severity,
            subject="Weekly Strategic Review",
            message=f"""
WEEKLY STRATEGIC REVIEW
=======================

{update.message_for_human}

Macro Assessment:
{update.macro_assessment}

Market Regime: {update.regime}

Strategy Changes: {'Yes' if update.has_changes else 'No'}

Major Risks:
{chr(10).join(['- ' + r for r in update.major_risks[:5]])}

Opportunities:
{chr(10).join(['- ' + o for o in update.opportunities[:5]])}

{"HUMAN DECISION REQUIRED: " + update.human_decision_topic if update.needs_human_decision else ""}
""",
        )

    async def trade_executed(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        reason: str,
    ):
        """Send trade execution alert."""
        await self.send(
            severity="info",
            subject=f"Trade Executed: {side.upper()} {symbol}",
            message=f"""
TRADE EXECUTED
==============

Symbol: {symbol}
Side: {side.upper()}
Quantity: {quantity:,}
Price: HKD {price:,.2f}

Reason:
{reason[:500]}
""",
        )

    async def position_closed(
        self,
        symbol: str,
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        reason: str,
    ):
        """Send position closed alert."""
        severity = "info" if pnl >= 0 else "warning"
        result = "PROFIT" if pnl >= 0 else "LOSS"

        await self.send(
            severity=severity,
            subject=f"Position Closed: {symbol} ({result})",
            message=f"""
POSITION CLOSED
===============

Symbol: {symbol}
Exit Price: HKD {exit_price:,.2f}
P&L: HKD {pnl:,.2f} ({pnl_pct:+.2f}%)

Reason:
{reason[:500]}
""",
        )

    async def emergency_close(
        self,
        positions_closed: int,
        total_pnl: float,
        reason: str,
    ):
        """Send emergency close alert."""
        await self.send(
            severity="critical",
            subject="EMERGENCY: All Positions Closed",
            message=f"""
EMERGENCY CLOSE
===============

All positions have been closed.

Positions Closed: {positions_closed}
Total P&L: HKD {total_pnl:,.2f}

Reason:
{reason}

This was an automated emergency action.
Please review and take any necessary follow-up actions.
""",
        )

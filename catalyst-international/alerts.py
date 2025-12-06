"""
Name of Application: Catalyst Trading System
Name of file: alerts.py
Version: 1.0.0
Last Updated: 2025-12-06
Purpose: Email alert notifications for the trading agent

REVISION HISTORY:
v1.0.0 (2025-12-06) - Initial implementation
- SMTP email sending
- Severity-based formatting
- Async-safe queue for alerts

Description:
This module handles email notifications for the trading agent.
Alerts are categorized by severity (info, warning, critical) and
sent to the operator via SMTP.
"""

import logging
import os
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from queue import Queue
from threading import Thread
from typing import Callable
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

HK_TZ = ZoneInfo("Asia/Hong_Kong")


class AlertSender:
    """Sends email alerts to the operator."""

    # Severity to emoji mapping
    SEVERITY_EMOJI = {
        "info": "i",
        "warning": "!",
        "critical": "X",
    }

    SEVERITY_PREFIX = {
        "info": "[INFO]",
        "warning": "[WARNING]",
        "critical": "[CRITICAL]",
    }

    def __init__(
        self,
        recipient: str | None = None,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_pass: str | None = None,
        sender_name: str = "Catalyst Trading Agent",
    ):
        """Initialize alert sender.

        Args:
            recipient: Alert recipient email
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            smtp_user: SMTP username
            smtp_pass: SMTP password
            sender_name: Display name for sender
        """
        self.recipient = recipient or os.environ.get("ALERT_EMAIL")
        self.smtp_host = smtp_host or os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.environ.get("SMTP_USER")
        self.smtp_pass = smtp_pass or os.environ.get("SMTP_PASS")
        self.sender_name = sender_name

        # Alert queue for async sending
        self._queue: Queue = Queue()
        self._worker: Thread | None = None
        self._running = False

    def start(self):
        """Start the alert sender worker thread."""
        if self._worker is not None and self._worker.is_alive():
            return

        self._running = True
        self._worker = Thread(target=self._worker_loop, daemon=True)
        self._worker.start()
        logger.info("Alert sender started")

    def stop(self):
        """Stop the alert sender worker thread."""
        self._running = False
        if self._worker:
            self._queue.put(None)  # Signal to stop
            self._worker.join(timeout=5)
            self._worker = None
        logger.info("Alert sender stopped")

    def _worker_loop(self):
        """Worker thread loop to send alerts."""
        while self._running:
            try:
                item = self._queue.get(timeout=1)
                if item is None:
                    break

                severity, subject, message = item
                self._send_email(severity, subject, message)

            except Exception:
                continue

    def send(self, severity: str, subject: str, message: str):
        """Queue an alert for sending.

        Args:
            severity: 'info', 'warning', or 'critical'
            subject: Alert subject
            message: Alert body
        """
        if not self._running:
            self.start()

        self._queue.put((severity, subject, message))
        logger.info(f"Alert queued: [{severity}] {subject}")

    def send_sync(self, severity: str, subject: str, message: str):
        """Send an alert immediately (blocking).

        Args:
            severity: 'info', 'warning', or 'critical'
            subject: Alert subject
            message: Alert body
        """
        self._send_email(severity, subject, message)

    def _send_email(self, severity: str, subject: str, message: str):
        """Send email via SMTP."""
        if not all([self.recipient, self.smtp_user, self.smtp_pass]):
            logger.warning("Email not configured, skipping alert")
            return

        try:
            # Format subject with severity prefix
            prefix = self.SEVERITY_PREFIX.get(severity, "[INFO]")
            full_subject = f"{prefix} {subject}"

            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = full_subject
            msg["From"] = f"{self.sender_name} <{self.smtp_user}>"
            msg["To"] = self.recipient

            # Plain text body
            timestamp = datetime.now(HK_TZ).strftime("%Y-%m-%d %H:%M:%S HKT")
            plain_body = f"{message}\n\n---\nSent at: {timestamp}\nFrom: Catalyst Trading System (International)"

            # HTML body
            html_body = self._format_html(severity, subject, message, timestamp)

            msg.attach(MIMEText(plain_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))

            # Send via SMTP
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_pass)
                server.sendmail(self.smtp_user, self.recipient, msg.as_string())

            logger.info(f"Alert sent: {full_subject}")

        except Exception as e:
            logger.error(f"Failed to send alert: {e}")

    def _format_html(
        self, severity: str, subject: str, message: str, timestamp: str
    ) -> str:
        """Format HTML email body."""
        # Severity colors
        colors = {
            "info": "#3498db",
            "warning": "#f39c12",
            "critical": "#e74c3c",
        }
        color = colors.get(severity, "#3498db")

        # Convert newlines to <br>
        html_message = message.replace("\n", "<br>")

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {color}; color: white; padding: 15px; border-radius: 8px 8px 0 0; }}
        .header h1 {{ margin: 0; font-size: 18px; }}
        .severity {{ font-size: 12px; text-transform: uppercase; opacity: 0.9; }}
        .content {{ background-color: #f8f9fa; padding: 20px; border: 1px solid #dee2e6; }}
        .message {{ line-height: 1.6; color: #333; }}
        .footer {{ padding: 15px; font-size: 12px; color: #6c757d; border: 1px solid #dee2e6; border-top: none; border-radius: 0 0 8px 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="severity">{severity.upper()}</div>
            <h1>{subject}</h1>
        </div>
        <div class="content">
            <div class="message">{html_message}</div>
        </div>
        <div class="footer">
            Sent at: {timestamp}<br>
            Catalyst Trading System (International) - HKEX
        </div>
    </div>
</body>
</html>
"""


# Singleton instance
_alert_sender: AlertSender | None = None


def get_alert_sender() -> AlertSender:
    """Get or create alert sender singleton."""
    global _alert_sender
    if _alert_sender is None:
        _alert_sender = AlertSender()
    return _alert_sender


def init_alert_sender(
    recipient: str | None = None,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_user: str | None = None,
    smtp_pass: str | None = None,
) -> AlertSender:
    """Initialize alert sender with explicit config."""
    global _alert_sender
    _alert_sender = AlertSender(
        recipient=recipient,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_pass=smtp_pass,
    )
    _alert_sender.start()
    return _alert_sender


def send_alert(severity: str, subject: str, message: str):
    """Convenience function to send an alert."""
    sender = get_alert_sender()
    sender.send(severity, subject, message)


def create_alert_callback() -> Callable[[str, str, str], None]:
    """Create a callback function for tool executor."""
    sender = get_alert_sender()
    sender.start()
    return sender.send

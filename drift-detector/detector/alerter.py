"""Alert delivery -- webhooks and email notifications."""

from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText

import httpx

from detector.models import DriftAlert

logger = logging.getLogger(__name__)


class Alerter:
    """Sends drift alerts via webhook and email."""

    def __init__(
        self,
        slack_webhook: str | None = None,
        discord_webhook: str | None = None,
        custom_webhook: str | None = None,
        smtp_host: str | None = None,
        smtp_port: int = 587,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        email_recipient: str | None = None,
    ) -> None:
        self._slack_webhook = slack_webhook
        self._discord_webhook = discord_webhook
        self._custom_webhook = custom_webhook
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._email_recipient = email_recipient

    async def send_alert(self, alert: DriftAlert) -> None:
        """Send an alert through all configured channels."""
        if self._slack_webhook:
            await self._send_slack(alert)
        if self._discord_webhook:
            await self._send_discord(alert)
        if self._custom_webhook:
            await self._send_custom_webhook(alert)
        if self._smtp_host and self._email_recipient:
            self._send_email(alert)

    async def _send_slack(self, alert: DriftAlert) -> None:
        """Send alert to Slack webhook."""
        severity_emoji = ":red_circle:" if alert.severity == "critical" else ":warning:"
        payload = {
            "text": (
                f"{severity_emoji} *Drift Alert: {alert.agent_name}*\n"
                f"Type: {alert.alert_type}\n"
                f"Score: {alert.score:.3f} (threshold: {alert.threshold:.3f})\n"
                f"{alert.description}"
            )
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self._slack_webhook,  # type: ignore[arg-type]
                    json=payload,
                    timeout=10.0,
                )
            logger.info("Slack alert sent for %s", alert.agent_name)
        except Exception:
            logger.exception("Failed to send Slack alert")

    async def _send_discord(self, alert: DriftAlert) -> None:
        """Send alert to Discord webhook."""
        payload = {
            "content": (
                f"**Drift Alert: {alert.agent_name}**\n"
                f"Type: {alert.alert_type} | Severity: {alert.severity}\n"
                f"Score: {alert.score:.3f} (threshold: {alert.threshold:.3f})\n"
                f"{alert.description}"
            )
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self._discord_webhook,  # type: ignore[arg-type]
                    json=payload,
                    timeout=10.0,
                )
            logger.info("Discord alert sent for %s", alert.agent_name)
        except Exception:
            logger.exception("Failed to send Discord alert")

    async def _send_custom_webhook(self, alert: DriftAlert) -> None:
        """Send alert to a custom webhook URL."""
        payload = alert.model_dump(mode="json")
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self._custom_webhook,  # type: ignore[arg-type]
                    json=payload,
                    timeout=10.0,
                )
            logger.info("Custom webhook alert sent for %s", alert.agent_name)
        except Exception:
            logger.exception("Failed to send custom webhook alert")

    def _send_email(self, alert: DriftAlert) -> None:
        """Send alert via SMTP email."""
        subject = f"[AgentTrace] Drift Alert: {alert.agent_name} ({alert.severity})"
        body = (
            f"Agent: {alert.agent_name}\n"
            f"Alert Type: {alert.alert_type}\n"
            f"Severity: {alert.severity}\n"
            f"Score: {alert.score:.3f} (threshold: {alert.threshold:.3f})\n"
            f"Description: {alert.description}\n"
            f"Detected at: {alert.detected_at.isoformat()}"
        )

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self._smtp_user or "agenttrace@localhost"
        msg["To"] = self._email_recipient  # type: ignore[assignment]

        try:
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:  # type: ignore[arg-type]
                server.starttls()
                if self._smtp_user and self._smtp_password:
                    server.login(self._smtp_user, self._smtp_password)
                server.send_message(msg)
            logger.info("Email alert sent for %s", alert.agent_name)
        except Exception:
            logger.exception("Failed to send email alert")

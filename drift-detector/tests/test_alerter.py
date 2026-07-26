"""Tests for the alerter module."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from detector.alerter import Alerter
from detector.models import DriftAlert


@pytest.fixture
def sample_alert() -> DriftAlert:
    return DriftAlert(
        agent_name="test_agent",
        detected_at=datetime.now(UTC),
        alert_type="semantic",
        severity="warning",
        score=0.25,
        threshold=0.15,
        description="Semantic drift detected",
    )


class TestAlerter:
    """Test Alerter delivery channels."""

    @pytest.mark.asyncio
    async def test_no_channels_configured(self, sample_alert: DriftAlert) -> None:
        """Alerter should not raise when no channels are configured."""
        alerter = Alerter()
        await alerter.send_alert(sample_alert)  # Should not raise

    @pytest.mark.asyncio
    async def test_slack_webhook(self, sample_alert: DriftAlert) -> None:
        """Should send POST to Slack webhook URL."""
        alerter = Alerter(slack_webhook="https://hooks.slack.com/test")
        with patch("detector.alerter.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await alerter.send_alert(sample_alert)

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://hooks.slack.com/test"

    @pytest.mark.asyncio
    async def test_discord_webhook(self, sample_alert: DriftAlert) -> None:
        """Should send POST to Discord webhook URL."""
        alerter = Alerter(discord_webhook="https://discord.com/api/webhooks/test")
        with patch("detector.alerter.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await alerter.send_alert(sample_alert)

            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://discord.com/api/webhooks/test"

    @pytest.mark.asyncio
    async def test_custom_webhook(self, sample_alert: DriftAlert) -> None:
        """Should send POST to custom webhook URL."""
        alerter = Alerter(custom_webhook="https://my-webhook.example.com/alerts")
        with patch("detector.alerter.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock()

            await alerter.send_alert(sample_alert)

            mock_client.post.assert_called_once()

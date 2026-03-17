"""Entry point for the drift detector background service."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

from detector.alerter import Alerter
from detector.baseline import BaselineBuilder
from detector.comparator import DriftComparator
from detector.models import BaselineRecord, DriftConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class DriftDetectorService:
    """Background service that continuously checks for behavioral drift."""

    def __init__(
        self,
        collector_url: str = "http://localhost:8000",
        check_interval: int = 300,
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self._collector_url = collector_url.rstrip("/")
        self._check_interval = check_interval
        self._builder = BaselineBuilder(embedding_model=embedding_model)
        self._comparator = DriftComparator(embedding_model=embedding_model)
        self._alerter = Alerter(
            slack_webhook=os.environ.get("SLACK_WEBHOOK_URL"),
            discord_webhook=os.environ.get("DISCORD_WEBHOOK_URL"),
            custom_webhook=os.environ.get("CUSTOM_WEBHOOK_URL"),
            smtp_host=os.environ.get("SMTP_HOST"),
            smtp_port=int(os.environ.get("SMTP_PORT", "587")),
            smtp_user=os.environ.get("SMTP_USER"),
            smtp_password=os.environ.get("SMTP_PASSWORD"),
            email_recipient=os.environ.get("ALERT_EMAIL"),
        )
        self._baselines: dict[str, BaselineRecord] = {}
        self._config = DriftConfig()

    async def _fetch_agents(self) -> list[str]:
        """Get list of unique agent names from collector."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._collector_url}/api/v1/stats", timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                return [a["name"] for a in data.get("top_agents", [])]
        except Exception:
            logger.exception("Failed to fetch agents from collector")
            return []

    async def _fetch_recent_spans(
        self, agent_name: str, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Fetch recent LLM call spans for an agent."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._collector_url}/api/v1/traces",
                    params={
                        "agent_name": agent_name,
                        "page_size": limit,
                        "sort_by": "started_at",
                        "sort_order": "desc",
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                all_spans = []
                for trace in data.get("items", []):
                    trace_detail = await client.get(
                        f"{self._collector_url}/api/v1/traces/{trace['id']}",
                        timeout=10.0,
                    )
                    trace_detail.raise_for_status()
                    spans = trace_detail.json().get("spans", [])
                    all_spans.extend(
                        [s for s in spans if s.get("event_type") == "llm_call"]
                    )
                return all_spans[:limit]
        except Exception:
            logger.exception("Failed to fetch spans for %s", agent_name)
            return []

    async def _post_alert(self, alert_data: dict[str, Any]) -> None:
        """Post a drift alert to the collector."""
        try:
            async with httpx.AsyncClient() as client:
                # Store alert directly if collector supports it
                logger.info(
                    "Drift alert: %s - %s (score=%.3f)",
                    alert_data.get("agent_name"),
                    alert_data.get("alert_type"),
                    alert_data.get("score", 0),
                )
        except Exception:
            logger.exception("Failed to post alert")

    async def check_agent(self, agent_name: str) -> None:
        """Check a single agent for drift."""
        spans = await self._fetch_recent_spans(agent_name)
        if len(spans) < self._config.min_samples:
            logger.debug(
                "Not enough samples for %s (%d < %d)",
                agent_name,
                len(spans),
                self._config.min_samples,
            )
            return

        # Extract data from spans
        texts = [
            s.get("output_data", {}).get("response", "")
            for s in spans
            if s.get("output_data")
        ]
        latencies = [s["latency_ms"] for s in spans if s.get("latency_ms")]
        tokens = [s["total_tokens"] for s in spans if s.get("total_tokens")]
        tools = [
            s.get("input_data", {}).get("tool_input", "")
            for s in spans
            if s.get("event_type") == "tool_call"
        ]

        if not texts:
            return

        # Build or retrieve baseline
        if agent_name not in self._baselines:
            logger.info("Building baseline for %s", agent_name)
            baseline = self._builder.build(
                agent_name=agent_name,
                response_texts=texts,
                latencies=latencies,
                token_counts=tokens,
                tool_calls=tools,
            )
            self._baselines[agent_name] = baseline
            return

        # Compare against baseline
        baseline = self._baselines[agent_name]
        report = self._comparator.compare(
            baseline=baseline,
            recent_texts=texts,
            recent_latencies=latencies,
            recent_token_counts=tokens,
            recent_tool_calls=tools,
            config=self._config,
        )

        if report.is_drifted:
            logger.warning(
                "Drift detected for %s: %d alerts",
                agent_name,
                len(report.alerts),
            )
            for alert in report.alerts:
                await self._alerter.send_alert(alert)
                await self._post_alert(alert.model_dump(mode="json"))

    async def run(self) -> None:
        """Main loop -- check all agents for drift periodically."""
        logger.info(
            "Drift detector started: collector=%s, interval=%ds",
            self._collector_url,
            self._check_interval,
        )

        while True:
            try:
                agents = await self._fetch_agents()
                for agent_name in agents:
                    await self.check_agent(agent_name)
            except Exception:
                logger.exception("Error in drift detection loop")

            await asyncio.sleep(self._check_interval)


def main() -> None:
    """Entry point."""
    collector_url = os.environ.get("COLLECTOR_URL", "http://localhost:8000")
    check_interval = int(os.environ.get("CHECK_INTERVAL_SECONDS", "300"))
    embedding_model = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    service = DriftDetectorService(
        collector_url=collector_url,
        check_interval=check_interval,
        embedding_model=embedding_model,
    )

    asyncio.run(service.run())


if __name__ == "__main__":
    main()

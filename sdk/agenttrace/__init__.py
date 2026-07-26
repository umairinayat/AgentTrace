"""AgentTrace -- Open-source observability for multi-agent AI systems."""

from agenttrace._version import SDK_VERSION
from agenttrace.decorators import trace_agent
from agenttrace.models import BatchSpanRequest, SpanEvent, TraceContext
from agenttrace.tracer import Tracer

# Global singleton tracer instance
tracer = Tracer()

__all__ = [
    "tracer",
    "Tracer",
    "trace_agent",
    "SpanEvent",
    "BatchSpanRequest",
    "TraceContext",
    "__version__",
]

__version__ = SDK_VERSION

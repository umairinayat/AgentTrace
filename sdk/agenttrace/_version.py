"""Single source of truth for the installed AgentTrace SDK version.

Reads the version from installed package metadata when available, with a
fallback for running directly from a source checkout that has not been
``pip install -e``'d. Both ``models.SpanEvent.sdk_version`` and the package
``__version__`` derive from here so they can never silently drift apart.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    SDK_VERSION = version("agenttrace")
except PackageNotFoundError:  # Running from source without install.
    SDK_VERSION = "0.0.0+local"

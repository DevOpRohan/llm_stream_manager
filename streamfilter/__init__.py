"""
streamfilter package initializer.
"""
from ._version import __version__
from .core import (
    KeywordRegistry,
    StreamProcessor,
    ActionContext,
    ActionDecision,
    ActionType,
    StreamHalted,
    drop,
    replace,
    passthrough,
    halt,
)
from .integration import stream_filter

__all__ = [
    "__version__",
    "KeywordRegistry",
    "StreamProcessor",
    "ActionContext",
    "ActionDecision",
    "ActionType",
    "StreamHalted",
    "drop",
    "replace",
    "passthrough",
    "halt",
    "stream_filter",
]
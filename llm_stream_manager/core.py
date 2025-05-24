from __future__ import annotations

from enum import Enum, auto
from typing import Callable, Generator, Iterable, List, Optional


class Action(Enum):
    """Simple action types for stream management."""

    PASS_TOKEN = auto()
    DROP_TOKEN = auto()
    HALT = auto()
    REPLACE = auto()


class StreamManager:
    """Applies registered rules to a stream of tokens."""

    def __init__(self) -> None:
        self._rules: List[tuple[str, Callable[[str], tuple[Action, Optional[str]]]] ] = []

    def register(self, keyword: str, cb: Callable[[str], tuple[Action, Optional[str]]]) -> None:
        """Register a callback for a given keyword."""
        self._rules.append((keyword, cb))

    def process(self, tokens: Iterable[str]) -> Generator[str, None, None]:
        """Yield processed tokens according to registered rules."""
        for tok in tokens:
            action_taken = False
            for kw, cb in self._rules:
                if kw in tok:
                    action, repl = cb(tok)
                    if action is Action.DROP_TOKEN:
                        action_taken = True
                        break
                    if action is Action.HALT:
                        return
                    if action is Action.REPLACE and repl is not None:
                        tok = repl
                        action_taken = True
                        break
            if not action_taken or action is Action.PASS_TOKEN or action is Action.REPLACE:
                yield tok

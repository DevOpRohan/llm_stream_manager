from __future__ import annotations

"""Core streaming utilities for :mod:`llm_stream_manager`."""

from enum import Enum, auto
from typing import AsyncIterable, Callable, Generator, Iterable, List, Optional, Tuple


class StreamHistory:
    """Collects processed tokens and actions for debugging."""

    def __init__(self) -> None:
        self.inputs: List[str] = []
        self.outputs: List[str] = []
        self.actions: List[Tuple[str, Action]] = []

    def record_input(self, token: str) -> None:
        self.inputs.append(token)

    def record_output(self, token: str) -> None:
        self.outputs.append(token)

    def record_action(self, token: str, action: "Action") -> None:
        self.actions.append((token, action))

    def get_inputs(self) -> List[str]:
        return list(self.inputs)

    def get_outputs(self) -> List[str]:
        return list(self.outputs)

    def get_actions(self) -> List[Tuple[str, "Action"]]:
        return list(self.actions)


class Action(Enum):
    """Simple action types for stream management."""

    PASS_TOKEN = auto()
    DROP_TOKEN = auto()
    HALT = auto()
    REPLACE = auto()


class StreamManager:
    """Applies registered rules to a stream of tokens.

    Parameters
    ----------
    record_history : bool, optional
        When ``True`` a :class:`StreamHistory` instance tracks processed tokens
        and actions. History is accessible via :pyattr:`history`.
    """

    def __init__(self, *, record_history: bool = False) -> None:
        self._rules: List[tuple[str, Callable[[str], tuple[Action, Optional[str]]]]] = []
        self._history: Optional[StreamHistory] = StreamHistory() if record_history else None

    def register(self, keyword: str, cb: Callable[[str], tuple[Action, Optional[str]]]) -> None:
        """Register a callback for a given keyword."""
        self._rules.append((keyword, cb))

    def deregister(self, keyword: str, cb: Optional[Callable[[str], tuple[Action, Optional[str]]]] = None) -> None:
        """Remove a callback or all callbacks for a keyword."""
        if cb is None:
            self._rules = [r for r in self._rules if r[0] != keyword]
        else:
            self._rules = [r for r in self._rules if not (r[0] == keyword and r[1] is cb)]

    def process(self, tokens: Iterable[str]) -> Generator[str, None, None]:
        """Yield processed tokens according to registered rules."""
        for tok in tokens:
            if self._history:
                self._history.record_input(tok)

            final = tok
            action = Action.PASS_TOKEN

            for kw, cb in self._rules:
                if kw in tok:
                    action, repl = cb(tok)
                    if self._history:
                        self._history.record_action(tok, action)
                    if action is Action.DROP_TOKEN:
                        final = None
                    elif action is Action.HALT:
                        return
                    elif action is Action.REPLACE and repl is not None:
                        final = repl
                    break

            if final is not None:
                if self._history:
                    self._history.record_output(final)
                yield final

    async def process_async(self, tokens: AsyncIterable[str]) -> AsyncIterable[str]:
        """Asynchronously yield processed tokens from an async iterable."""
        async for tok in tokens:
            if self._history:
                self._history.record_input(tok)

            final = tok
            action = Action.PASS_TOKEN

            for kw, cb in self._rules:
                if kw in tok:
                    action, repl = cb(tok)
                    if self._history:
                        self._history.record_action(tok, action)
                    if action is Action.DROP_TOKEN:
                        final = None
                    elif action is Action.HALT:
                        return
                    elif action is Action.REPLACE and repl is not None:
                        final = repl
                    break

            if final is not None:
                if self._history:
                    self._history.record_output(final)
                yield final

    @property
    def history(self) -> Optional[StreamHistory]:
        """Return the :class:`StreamHistory` instance if recording is enabled."""
        return self._history

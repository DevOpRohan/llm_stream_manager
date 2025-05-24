"""
Core stream filtering engine using Aho-Corasick automation.
"""
from collections import deque
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Tuple, Any


class StreamHistory:
    """
    Tracks the full input, output, and action history for a stream.
    Provides APIs for callbacks to query past context.
    """
    __slots__ = ('_inputs', '_outputs', '_actions')

    def __init__(self):
        self._inputs: List[str] = []
        self._outputs: List[str] = []
        # actions: list of tuples (pos, keyword, ActionDecision)
        self._actions: List[Tuple[int, str, ActionDecision]] = []

    def record_input(self, ch: str) -> None:
        self._inputs.append(ch)

    def record_output(self, ch: str) -> None:
        self._outputs.append(ch)

    def record_action(self, pos: int, keyword: str, decision: 'ActionDecision') -> None:
        self._actions.append((pos, keyword, decision))

    def get_inputs(self) -> List[str]:
        return list(self._inputs)

    def get_outputs(self) -> List[str]:
        return list(self._outputs)

    def get_actions(self) -> List[Tuple[int, str, 'ActionDecision']]:
        return list(self._actions)

class _NullHistory:
    """
    No-op history collector for disabled history mode.
    """
    __slots__ = ()
    def record_input(self, ch: str) -> None: pass
    def record_output(self, ch: str) -> None: pass
    def record_action(self, pos: int, keyword: str, decision: 'ActionDecision') -> None: pass
    def get_inputs(self) -> List[str]: return []
    def get_outputs(self) -> List[str]: return []
    def get_actions(self) -> List[Tuple[int, str, 'ActionDecision']]: return []


class ActionType(Enum):
    PASS = auto()
    DROP = auto()
    REPLACE = auto()
    HALT = auto()
    CONTINUE_DROP = auto()
    CONTINUE_PASS = auto()


class ActionDecision:
    """
    Represents the decision taken by a callback on a detected keyword.
    """
    __slots__ = ('type', 'replacement')

    def __init__(self, type: ActionType, replacement: Optional[str] = None):
        self.type = type
        self.replacement = replacement


class ActionContext:
    """
    Context provided to callbacks when a keyword is matched.
    """
    __slots__ = (
        'keyword',        # matched keyword
        'buffer',         # current buffer contents (list of chars)
        'absolute_pos',   # position in input stream (1-based)
        'history',        # StreamHistory instance for full history
    )

    def __init__(self, keyword: str, buffer: List[str], absolute_pos: int, history: StreamHistory):
        self.keyword = keyword
        self.buffer = buffer
        self.absolute_pos = absolute_pos
        self.history = history


class StreamHalted(Exception):
    """Raised to signal that the stream should be aborted immediately."""
    pass


class _Node:
    __slots__ = ('children', 'fail', 'output')

    def __init__(self):
        self.children: Dict[str, _Node] = {}
        self.fail: Optional[_Node] = None
        # output: list of tuples (keyword, callbacks_list)
        self.output: List[Tuple[str, List[Callable[[ActionContext], ActionDecision]]]] = []


class KeywordRegistry:
    """
    Registry for keywords and their associated callbacks.
    """

    def __init__(self):
        self._keywords: Dict[str, List[Callable[[ActionContext], ActionDecision]]] = {}
        self._compiled: bool = False
        self._root: Optional[_Node] = None
        self._max_len: int = 0

    def register(self, keyword: str, callback: Callable[[ActionContext], ActionDecision]) -> None:
        """
        Register a callback for a given keyword.
        """
        if keyword in self._keywords:
            self._keywords[keyword].append(callback)
        else:
            self._keywords[keyword] = [callback]
        self._compiled = False

    def deregister(self, keyword: str, callback: Optional[Callable[[ActionContext], ActionDecision]] = None) -> None:
        """
        Deregister a callback or all callbacks for a given keyword.
        """
        if keyword not in self._keywords:
            return
        if callback is None:
            del self._keywords[keyword]
        else:
            try:
                self._keywords[keyword].remove(callback)
                if not self._keywords[keyword]:
                    del self._keywords[keyword]
            except ValueError:
                pass
        self._compiled = False

    def compile(self) -> None:
        """
        Compile the registered keywords into an Aho-Corasick trie with failure links.
        """
        # Initialize root node
        root = _Node()
        # Build trie
        max_len = 0
        for kw, callbacks in self._keywords.items():
            max_len = max(max_len, len(kw))
            node = root
            for ch in kw:
                node = node.children.setdefault(ch, _Node())
            # Attach output: keyword and its callbacks
            node.output.append((kw, list(callbacks)))
        # Build failure links
        root.fail = root
        queue = []
        # First level children fail to root
        for child in root.children.values():
            child.fail = root
            queue.append(child)
        # BFS
        while queue:
            current = queue.pop(0)
            for ch, child in current.children.items():
                queue.append(child)
                # Set failure for child
                f = current.fail
                while f is not root and ch not in f.children:
                    f = f.fail
                child.fail = f.children.get(ch, root)
                # Merge outputs
                child.output.extend(child.fail.output)
        # Save compiled automaton
        self._root = root
        self._max_len = max_len
        self._compiled = True

    def max_len(self) -> int:
        """Return the maximum keyword length registered."""
        if not self._compiled:
            self.compile()
        return self._max_len


class StreamProcessor:
    """
    Processes a character stream, emitting filtered characters based on registered keywords.
    """

    def __init__(self, registry: KeywordRegistry, *, record_history: bool = True):
        self._registry = registry
        if not registry._compiled:
            registry.compile()
        # Root of the AC automaton
        self._root = registry._root  # type: ignore
        self._max_len = registry._max_len
        # Current state
        self._node = self._root
        self._buffer: deque = deque()
        self._pos: int = 0
        # Central history manager (real or null based on flag)
        if record_history:
            self._history = StreamHistory()
        else:
            self._history = _NullHistory()
        # Drop mode flag: when True, suppress output (until CONTINUE_PASS)
        self._drop_mode = False

    def process(self, ch: str) -> List[str]:  # pragma: no cover
        """
        Process a single character and return a list of output characters to emit.
        May raise StreamHalted to abort the stream.
        """
        out: List[str] = []
        # Record input history and update state
        self._history.record_input(ch)
        self._buffer.append(ch)
        self._pos += 1
        # Aho-Corasick state transition
        while ch not in self._node.children and self._node is not self._root:
            self._node = self._node.fail  # type: ignore
        self._node = self._node.children.get(ch, self._root)  # type: ignore
        # Check for matches
        if self._node.output:
            # Pick longest match
            kw, callbacks = max(self._node.output, key=lambda x: len(x[0]))
            # Run callbacks in order
            for cb in callbacks:
                # Build context with full history
                ctx = ActionContext(
                    keyword=kw,
                    buffer=list(self._buffer),
                    absolute_pos=self._pos,
                    history=self._history,
                )
                decision = cb(ctx)
                # If callback returns None, treat as PASS (no-op)
                if decision is None:
                    continue
                # Record and apply decision
                self._history.record_action(self._pos, kw, decision)
                if decision.type is ActionType.CONTINUE_DROP:
                    # Enter drop mode; flush prior buffer only on first entry
                    if not self._drop_mode:
                        all_buf = list(self._buffer)
                        self._buffer.clear()
                        prior = all_buf[:-len(kw)] if len(kw) <= len(all_buf) else []
                        for c in prior:
                            self._history.record_output(c)
                            out.append(c)
                    self._drop_mode = True
                elif decision.type is ActionType.CONTINUE_PASS:
                    # Resume pass mode; if coming from drop, flush only the matched marker
                    if self._drop_mode:
                        all_buf = list(self._buffer)
                        self._buffer.clear()
                        marker = all_buf[-len(kw):] if len(kw) <= len(all_buf) else all_buf
                        for c in marker:
                            self._history.record_output(c)
                            out.append(c)
                    self._drop_mode = False
                elif decision.type is ActionType.DROP:
                    # Remove matched keyword from buffer
                    for _ in range(len(kw)):
                        if self._buffer:
                            self._buffer.pop()
                elif decision.type is ActionType.REPLACE:
                    # Remove keyword and append replacement
                    for _ in range(len(kw)):
                        if self._buffer:
                            self._buffer.pop()
                    if decision.replacement:
                        for rc in decision.replacement:
                            self._buffer.append(rc)
                elif decision.type is ActionType.PASS:
                    # no-op
                    pass
                elif decision.type is ActionType.HALT:
                    # Abort the stream
                    raise StreamHalted()
            # After handling a match, reset automaton state to root to allow overlapping matches
            self._node = self._root
        # Lazy flush: emit or drop oldest if buffer exceeds max keyword length
        if len(self._buffer) > self._max_len:
            c = self._buffer.popleft()
            if not getattr(self, '_drop_mode', False):
                self._history.record_output(c)
                out.append(c)
        return out

    def flush(self) -> List[str]:
        """
        Flush and return all remaining buffered characters.
        """
        if getattr(self, '_drop_mode', False):
            # drop all
            self._buffer.clear()
            return []
        rem = list(self._buffer)
        for c in rem:
            self._history.record_output(c)
        self._buffer.clear()
        return rem


# Helper actions for callbacks
def drop(ctx=None) -> ActionDecision:
    """Callback helper: drop the matched keyword"""
    return ActionDecision(ActionType.DROP)

def continuous_drop() -> ActionDecision:
    """Start dropping all subsequent stream content (until CONTINUE_PASS)."""
    return ActionDecision(ActionType.CONTINUE_DROP)

def continuous_pass() -> ActionDecision:
    """Resume passing stream content after a drop segment (until CONTINUE_DROP)."""
    return ActionDecision(ActionType.CONTINUE_PASS)


def replace(text: str) -> ActionDecision:
    """Callback helper: replace the matched keyword with text"""
    return ActionDecision(ActionType.REPLACE, replacement=text)


def passthrough(ctx=None) -> ActionDecision:
    """Callback helper: leave the matched keyword in place"""
    return ActionDecision(ActionType.PASS)


def halt(ctx=None) -> ActionDecision:
    """Callback helper: abort the stream"""
    return ActionDecision(ActionType.HALT)

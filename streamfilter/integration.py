"""
Integration layer exposing the @stream_filter decorator for sync and async generators.
"""
import inspect

from .core import StreamProcessor, StreamHalted


def _repack(chars, mode):
    """
    Repack a list of characters into the desired yield mode.
    """
    if mode == 'char':
        for c in chars:
            yield c
    elif mode == 'token':
        yield ''.join(chars)
    elif mode.startswith('chunk:'):
        try:
            size = int(mode.split(':', 1)[1])
        except (IndexError, ValueError):
            raise ValueError(f"Invalid chunk size in mode '{mode}'")
        for i in range(0, len(chars), size):
            yield ''.join(chars[i:i+size])
    else:
        raise ValueError(f"Unknown yield mode '{mode}'")


def stream_filter(registry, *, yield_mode='token', record_history=True):
    """
    Decorator to apply stream filtering to a token generator (sync or async).
    """
    def decorator(fn):  # noqa: C901
        if inspect.isasyncgenfunction(fn):
            async def async_wrap(*args, **kwargs):
                sp = StreamProcessor(registry, record_history=record_history)
                # TOKEN mode: one yield per input token
                if yield_mode == 'token':
                    try:
                        async for token in fn(*args, **kwargs):
                            out_chars = []
                            try:
                                for ch in token:
                                    out_chars.extend(sp.process(ch))
                            except StreamHalted:
                                return
                            out_chars.extend(sp.flush())
                            yield ''.join(out_chars)
                    except StreamHalted:
                        return
                    return
                # CHAR or CHUNK modes
                try:
                    async for token in fn(*args, **kwargs):
                        out_chars = []
                        try:
                            for ch in token:
                                out_chars.extend(sp.process(ch))
                        except StreamHalted:
                            return
                        for item in _repack(out_chars, yield_mode):
                            yield item
                    # Flush remaining
                    rem = sp.flush()
                    if rem:
                        for item in _repack(rem, yield_mode):
                            yield item
                except StreamHalted:
                    return
            async_wrap.registry = registry
            return async_wrap
        elif inspect.isgeneratorfunction(fn):
            def sync_wrap(*args, **kwargs):
                sp = StreamProcessor(registry, record_history=record_history)
                # TOKEN mode: yield one output per input token
                if yield_mode == 'token':
                    for token in fn(*args, **kwargs):
                        out_chars = []
                        try:
                            for ch in token:
                                out_chars.extend(sp.process(ch))
                        except StreamHalted:
                            return
                        # flush buffer for this token
                        out_chars.extend(sp.flush())
                        yield ''.join(out_chars)
                    return
                # CHAR or CHUNK modes: per-char or per-chunk yields, then final flush
                for token in fn(*args, **kwargs):
                    out_chars = []
                    try:
                        for ch in token:
                            out_chars.extend(sp.process(ch))
                    except StreamHalted:
                        return
                    for item in _repack(out_chars, yield_mode):
                        yield item
                # Flush remaining
                rem = sp.flush()
                if rem:
                    for item in _repack(rem, yield_mode):
                        yield item
            sync_wrap.registry = registry
            return sync_wrap
        else:
            raise TypeError("stream_filter decorator can only be applied to generator or async generator functions")
    return decorator
"""
Benchmark script for streamfilter throughput and memory usage.
"""
import time
import tracemalloc
import argparse
import random
import string

from streamfilter.core import KeywordRegistry, StreamProcessor


def generate_text(n):
    """Generate random lowercase text of length n."""
    choices = string.ascii_lowercase + ' '
    return ''.join(random.choice(choices) for _ in range(n))


def bench(n, record_history):
    # Setup registry with a dummy pattern (not present in text)
    reg = KeywordRegistry()
    reg.register('zzz', lambda ctx: None)
    sp = StreamProcessor(reg, record_history=record_history)
    text = generate_text(n)

    # Start memory tracking
    tracemalloc.start()
    t0 = time.perf_counter()
    for ch in text:
        sp.process(ch)
    sp.flush()
    t1 = time.perf_counter()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    duration = t1 - t0
    rate = n / duration / 1e6  # million chars per second
    print(f"record_history={record_history}: {rate:.2f} Mchars/s, peak memory={peak/1024/1024:.2f} MB")


def main():
    parser = argparse.ArgumentParser(description="Benchmark streamfilter throughput.")
    parser.add_argument('size', type=int, nargs='?', default=5_000_000,
                        help='number of characters to process')
    args = parser.parse_args()

    for flag in (True, False):
        bench(args.size, record_history=flag)


if __name__ == '__main__':
    main()
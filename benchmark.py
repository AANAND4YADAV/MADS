import io, time, statistics, contextlib
import ollama
import STREAMING
STREAMING.enable(show=False)   # measure, but don't print
...
# after the loop:
STREAMING.report()

# Time every Ollama call (patched before main/agent are imported)
call_times = []
_orig_chat = ollama.chat
def timed_chat(*a, **kw):
    t = time.perf_counter()
    try:
        return _orig_chat(*a, **kw)
    finally:
        call_times.append(time.perf_counter() - t)
ollama.chat = timed_chat

from main import AGENTS            # main.py already runs openlit.init
from debate_manager import run_debate
from topics import DEFAULT_TOPIC

RUNS = 8
e2e = []
for i in range(1, RUNS + 1):
    t = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):   # hide debate + OpenLIT output
        run_debate(AGENTS, DEFAULT_TOPIC)
    e2e.append(time.perf_counter() - t)
    print(f"run {i}/{RUNS}: {e2e[-1]:.1f}s", flush=True)

def stats(name, v):
    if not v:
        print(f"{name}: no data"); return
    v = sorted(v)
    q = statistics.quantiles(v, n=100, method="inclusive") if len(v) > 1 else v * 99
    print(f"{name}: n={len(v)} min={v[0]:.2f} p50={q[49]:.2f} "
          f"p95={q[94]:.2f} max={v[-1]:.2f} mean={statistics.mean(v):.2f}")

print()
stats("E2E debate (s)", e2e)
stats("Per LLM call (s)", call_times)
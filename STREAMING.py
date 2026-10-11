"""streaming.py: token-level streaming for MADS (decoupled module).

Idea: wrap ollama.chat / ollama.generate so every call
  1. is sent with stream=True,
  2. prints each token to the terminal the moment it arrives,
  3. collects the full text and returns it like a normal response.
Callers (agent.py etc.) never know the difference.
""""""streaming.py: token-level streaming for MADS (decoupled module).

Idea: wrap ollama.chat / ollama.generate so every call
  1. is sent with stream=True,
  2. prints each token to the terminal the moment it arrives,
  3. collects the full text and returns it like a normal response.
Callers (agent.py etc.) never know the difference.
"""
import time
import statistics
import ollama
from ollama import Client

stats = []            # one record per LLM call: first chunk, first text, total
_state = {"show": True, "enabled": False, "stats_line": False}


def _run(orig, kind, args, kwargs):
    if kwargs.get("stream"):               # caller already streams: don't interfere
        return orig(*args, **kwargs)
    kwargs["stream"] = True

    t0 = time.perf_counter()
    first_chunk = first_text = None
    text, last = "", None

    for chunk in orig(*args, **kwargs):    # STEP 1: read chunks as they arrive
        now = time.perf_counter() - t0
        if first_chunk is None:
            first_chunk = now
        piece = (chunk["message"]["content"] if kind == "chat"
                 else chunk["response"]) or ""
        if piece:                          # STEP 2: a real answer token (not thinking)
            if first_text is None:
                first_text = now           # this is the true TTFT
            text += piece                  # STEP 3: collect for the next agent
            if _state["show"]:
                print(piece, end="", flush=True)   # STEP 4: show it NOW
        last = chunk

    total = time.perf_counter() - t0
    stats.append({"first_chunk": first_chunk, "ttft": first_text, "total": total})

    if _state["show"]:
        print(flush=True)                  # finish the streamed line
        if _state["stats_line"]:
            ttft = f"{first_text:.2f}" if first_text is not None else "n/a"
            print(f"[TTFT {ttft}s | total {total:.2f}s]", flush=True)

    # STEP 5: return the final chunk with the FULL text, so callers see a normal reply
    if kind == "chat":
        last.message.content = text
    else:
        last.response = text
    return last


def _wrap(orig, kind):
    def wrapper(*args, **kwargs):
        return _run(orig, kind, args, kwargs)
    return wrapper


def enable(show=True, stats_line=False):
    """Turn streaming on.
    show=False       -> still measures TTFT, prints nothing (use in benchmarks)
    stats_line=True  -> print a [TTFT | total] line after every call
    """
    _state["show"] = show
    _state["stats_line"] = stats_line
    if _state["enabled"]:
        return
    _state["enabled"] = True
    for name in ("chat", "generate"):
        setattr(ollama, name, _wrap(getattr(ollama, name), name))   # ollama.chat(...)
        setattr(Client, name, _wrap(getattr(Client, name), name))   # Client().chat(...)


def report():
    for label, key in (("TTFT (first text)", "ttft"), ("Per-call total", "total")):
        v = sorted(s[key] for s in stats if s[key] is not None)
        if not v:
            print(f"{label}: no data")
            continue
        q = statistics.quantiles(v, n=100, method="inclusive") if len(v) > 1 else v * 99
        print(f"{label}: n={len(v)} min={v[0]:.2f} p50={q[49]:.2f} "
              f"p95={q[94]:.2f} max={v[-1]:.2f} mean={statistics.mean(v):.2f}")

import os
import time
from collections import Counter

# Optional tracing. Normal run: python main.py  (no JSON noise)
# To trace:  set MADS_TRACE=1   then   python main.py
if os.getenv("MADS_TRACE") == "1":
    import openlit
    openlit.init(application_name="mads", disable_batch=True)

# Streaming must be enabled BEFORE agent / debate_manager are imported,
# so they pick up the wrapped Ollama calls.
import STREAMING
STREAMING.enable()

from agent import Agent
from debate_manager import run_debate
from topics import TOPICS
from bins import format_bin
import storage


AGENTS = [
    Agent(
        name="Dr. Ananya Sharma",
        role="Recycling & Materials Scientist",
        stance="Defaults to recyclable: most dry material has a recovery route, and sending it to landfill is a waste of resources.",
        behavior="Speaks formally with data-backed arguments about materials, recovery rates and contamination thresholds. Calm and analytical tone."
    ),
    Agent(
        name="Ravi Patel",
        role="Community Composting Activist",
        stance="Defaults to wet waste: anything organic or food-soiled belongs in the green bin, and contaminated packaging ruins recycling anyway.",
        behavior="Passionate and emotional. Uses real-world examples from his neighbourhood compost pits and mixed-waste dumps to make points."
    ),
    Agent(
        name="Aarav Mehta",
        role="Hazardous & E-Waste Safety Officer",
        stance="Defaults to hazardous or e-waste when in doubt: batteries, chemicals and residue are a risk to workers and groundwater.",
        behavior="Confident and risk-focused. Talks in numbers: injuries, fires at sorting yards, toxic leakage. Flags hidden hazards others miss."
    ),
    Agent(
        name="Nisha Verma",
        role="Municipal Sanitation Supervisor",
        stance="Defaults to what actually works on the ground: the correct bin is the one a collector can sort and a household will use correctly.",
        behavior="Balanced and empathetic. Speaks from field experience with door-to-door collection, and weighs the other three views against practical reality."
    ),
]


def main():
    run_id = time.strftime("%Y%m%d-%H%M%S")
    s3_ok = storage.safe(storage.check_bucket) is None and storage.BUCKET is not None
    # check_bucket returns None on success AND on failure, so verify explicitly:
    try:
        storage.check_bucket()
        s3_ok = True
        print(f"[s3] connected -> s3://{storage.BUCKET}/runs/{run_id}/")
    except Exception as e:
        s3_ok = False
        print(f"[s3] unavailable, debates will run but NOT be saved: {e}")

    results = []

    for i, topic in enumerate(TOPICS, start=1):
        t0 = time.perf_counter()
        verdict = run_debate(AGENTS, topic)
        seconds = time.perf_counter() - t0

        print("\n" + format_bin(verdict["category"]))

        key = None
        if s3_ok:
            key = storage.safe(storage.save_debate, run_id, i, topic, verdict, seconds)
            if key:
                print(f"\nSaved -> {storage.uri(key)}")

        results.append({
            "topic": str(topic),
            "category": verdict["category"],
            "e2e_seconds": round(seconds, 2),
            "s3_key": key,
        })

    # Run-level summary, also stored in S3
    times = sorted(r["e2e_seconds"] for r in results)
    summary = {
        "run_id": run_id,
        "agents": [a.name for a in AGENTS],
        "debates": len(results),
        "categories": dict(Counter(r["category"] for r in results)),
        "latency_seconds": {
            "min": times[0] if times else None,
            "p50": times[len(times) // 2] if times else None,
            "max": times[-1] if times else None,
        },
        "results": results,
    }

    print("\n" + "-" * 50)
    if s3_ok:
        key = storage.safe(storage.save_summary, run_id, summary)
        if key:
            print(f"Run summary -> {storage.uri(key)}")
    print(f"Categories: {summary['categories']}")
    STREAMING.report()  # one clean latency summary


if __name__ == "__main__":
    main()
# MADS: Multi-Agent Debate System

> Four AI experts debate where your waste belongs. A judge delivers the verdict. Every debate is saved to AWS S3.

MADS classifies waste by letting specialist agents argue it out instead of trusting a single model's answer. Each agent defends a different default position, the debate is streamed token by token, and the final bin is chosen by a judge. The system is traced with OpenTelemetry (via OpenLIT), measured for latency, and persists every result to Amazon S3.

---

## Features

| Feature | What it gives you |
|---|---|
| **Multi-agent debate** | Four role-driven agents with opposing stances argue each topic before a verdict |
| **Local LLM inference** | Runs on Ollama, so no per-token API cost for the debate itself |
| **Streaming** | Tokens are streamed as they are generated, so you see the debate live |
| **Latency measurement** | Per-debate end-to-end time plus min / p50 / max per run, and a latency report at the end |
| **OpenTelemetry tracing** | Optional OpenLIT instrumentation for traces and LLM metrics |
| **AWS S3 persistence** | Every debate and a run summary stored as JSON in S3 |
| **High cohesion, low coupling** | Each module has one job and talks to others through small interfaces |

---

## The Agents

| Agent | Role | Default stance |
|---|---|---|
| **Dr. Ananya Sharma** | Recycling & Materials Scientist | Recyclable: most dry material has a recovery route |
| **Ravi Patel** | Community Composting Activist | Wet waste: organic or food-soiled items belong in the green bin |
| **Aarav Mehta** | Hazardous & E-Waste Safety Officer | Hazardous when in doubt: batteries, chemicals and residue are a risk |
| **Nisha Verma** | Municipal Sanitation Supervisor | What works on the ground: the bin a collector can sort and a household will use correctly |

The built-in disagreement is the point. Each expert pulls toward its own bias, and the debate and judge resolve the conflict.

---

## Architecture

```
                    ┌─────────────┐
                    │   main.py   │  orchestration only
                    └──────┬──────┘
        ┌──────────┬───────┴────────┬────────────┐
        ▼          ▼                ▼            ▼
  ┌──────────┐ ┌────────────────┐ ┌─────────┐ ┌────────────┐
  │ agent.py │ │debate_manager.py│ │ bins.py │ │ storage.py │
  │ persona  │ │  debate + judge │ │ output  │ │  AWS S3    │
  └────┬─────┘ └───────┬────────┘ └─────────┘ └─────┬──────┘
       └───────┬───────┘                            │
               ▼                                    ▼
         ┌──────────┐                         ┌───────────┐
         │  llm.py  │ ◄── STREAMING.py        │ Amazon S3 │
         │ gateway  │     (stream + latency)  └───────────┘
         └────┬─────┘
              ▼
         ┌──────────┐
         │  Ollama  │
         └──────────┘
```

### High cohesion, low coupling

Each file does one thing, and the pieces connect through narrow interfaces.

| Module | Single responsibility |
|---|---|
| `main.py` | Wires everything together and runs the topics. No business logic |
| `agent.py` | Defines an agent: name, role, stance, behaviour |
| `debate_manager.py` | Runs a debate between agents and produces a verdict (`run_debate`) |
| `llm.py` | The only place that talks to the model provider |
| `STREAMING.py` | Wraps model calls to stream tokens and record latency |
| `memory.py` | Debate memory / context handling |
| `bins.py` | Maps a verdict category to a formatted bin output |
| `topics.py` | The list of topics to debate |
| `storage.py` | The only place that talks to AWS S3 |
| `benchmark.py` | Latency benchmarking |

Why this matters in practice:

- **Swap the model provider** by changing `llm.py` only. Agents and the debate logic don't change.
- **Swap the storage backend** by changing `storage.py` only. S3 calls never leak into the debate code.
- **S3 failures never break a debate.** `main.py` calls storage through a `safe(...)` wrapper, so an AWS error prints a message and the run continues.
- **Observability is opt-in.** Tracing and streaming are switched on at startup, and the debate code isn't aware of them.

---

## Streaming and Latency

Streaming is enabled once at startup, before the agent and debate modules are imported, so they pick up the wrapped model calls:

```python
import STREAMING
STREAMING.enable()
```

Latency is tracked at two levels:

- **Per debate:** end-to-end seconds, stored with each debate JSON (`e2e_seconds`)
- **Per run:** min, p50 and max across all topics in `summary.json`, plus a latency report printed by `STREAMING.report()` at the end of the run

---

## OpenTelemetry Tracing (OpenLIT)

Tracing is off by default so normal runs stay quiet. Turn it on with one environment variable:

```powershell
# PowerShell
$env:MADS_TRACE = "1"
python main.py
```

```bash
# macOS / Linux
MADS_TRACE=1 python main.py
```

When enabled, MADS initialises [OpenLIT](https://github.com/openlit/openlit), which instruments the LLM calls and emits OpenTelemetry traces and metrics under the application name `mads`.

---

## AWS S3 Storage

Each run gets its own folder in the bucket:

```
s3://<your-bucket>/
└── runs/
    └── 20261010-212504/
        ├── 01-<topic>.json     # one file per debate
        ├── 02-<topic>.json
        └── summary.json        # run-level summary
```

**Per-debate file** contains the run ID, topic, the full verdict, end-to-end seconds and a timestamp.

**`summary.json`** contains the run ID, the agents, the number of debates, category counts, latency (min / p50 / max) and the S3 key of every debate.

Before any debate runs, MADS checks the bucket is reachable (`check_bucket`). If S3 is unavailable, the debates still run and a clear message says they will not be saved.

---

## Getting Started

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) running locally with a model pulled
- An AWS account with an S3 bucket
- An IAM user with S3 access (for example `AmazonS3FullAccess` while learning, scoped to your bucket later)

### Install

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

Set these environment variables. Use placeholder values here and your real ones locally:

| Variable | Example | Purpose |
|---|---|---|
| `MADS_BUCKET` | `your-bucket-name` | Target S3 bucket |
| `S3_REGION` | `eu-north-1` | Region of the bucket |
| `AWS_DEFAULT_REGION` | `eu-north-1` | Default AWS region |
| `AWS_ACCESS_KEY_ID` | `your_access_key_id` | IAM credentials |
| `AWS_SECRET_ACCESS_KEY` | `your_secret_access_key` | IAM credentials |
| `MADS_TRACE` | `1` | Optional: enable OpenLIT tracing |

You can set them in your shell, in your IDE's run configuration, or in a local `.env` file.

> **Never commit credentials.** Make sure `.env` is listed in `.gitignore`. If a key is ever exposed, delete it in IAM and create a new one.

### Run

```bash
python main.py
```

Expected startup line:

```
[s3] connected -> s3://<your-bucket>/runs/<timestamp>/
```

Then each topic is debated, the verdict bin is printed, and the saved S3 path is shown after every debate.

---

## Project Structure

```
.
├── main.py              # orchestration
├── agent.py             # agent definition
├── debate_manager.py    # debate + judge
├── llm.py               # model gateway
├── STREAMING.py         # streaming + latency
├── memory.py            # debate memory
├── bins.py              # bin formatting
├── topics.py            # topics to debate
├── storage.py           # AWS S3 persistence
├── benchmark.py         # latency benchmarking
├── requirements.txt
└── .gitignore
```

---

## Roadmap

- [ ] Amazon Bedrock as a second LLM provider (swap in `llm.py`, compare latency against local Ollama)
- [ ] Load and replay past runs from S3
- [ ] Per-agent latency and token metrics

---

## Tech Stack

Python · Ollama · OpenLIT / OpenTelemetry · AWS S3 · boto3

---

## Author

**Aanand Yadav**, [GitHub](https://github.com/AANAND4YADAV) · [Medium](https://medium.com/@aanandittt)

import json
import os
import re
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError

BUCKET = os.getenv("MADS_BUCKET")
REGION = os.getenv("S3_REGION", "eu-north-1")

_s3 = boto3.client("s3", region_name=REGION)


def _bucket() -> str:
    if not BUCKET:
        raise RuntimeError("MADS_BUCKET env var is not set")
    return BUCKET


def _slug(text, n: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:n] or "topic"


def uri(key: str) -> str:
    return f"s3://{_bucket()}/{key}"


def _put_json(key: str, payload: dict) -> str:
    body = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
    _s3.put_object(Bucket=_bucket(), Key=key, Body=body, ContentType="application/json")
    return key


def check_bucket() -> None:
    """Fail fast, before any debate runs, if S3 isn't reachable."""
    _s3.head_bucket(Bucket=_bucket())


def save_debate(run_id: str, index: int, topic, verdict: dict, seconds: float) -> str:
    key = f"runs/{run_id}/{index:02d}-{_slug(topic)}.json"
    return _put_json(key, {
        "run_id": run_id,
        "index": index,
        "topic": str(topic),
        "verdict": verdict,
        "e2e_seconds": round(seconds, 2),
        "saved_at": time.time(),
    })


def save_summary(run_id: str, summary: dict) -> str:
    return _put_json(f"runs/{run_id}/summary.json", summary)


def list_runs(limit: int = 10) -> list[str]:
    resp = _s3.list_objects_v2(Bucket=_bucket(), Prefix="runs/", Delimiter="/")
    runs = [p["Prefix"] for p in resp.get("CommonPrefixes", [])]
    return sorted(runs, reverse=True)[:limit]


def load_json(key: str) -> dict:
    obj = _s3.get_object(Bucket=_bucket(), Key=key)
    return json.loads(obj["Body"].read().decode("utf-8"))


def safe(fn, *args, **kwargs):
    """Run an S3 call; on AWS errors print and return None instead of crashing MADS."""
    try:
        return fn(*args, **kwargs)
    except (BotoCoreError, ClientError, RuntimeError) as e:
        print(f"[s3] {fn.__name__} failed: {e}")
        return None
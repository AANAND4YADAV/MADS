"""debate_manager.py - runs a two-round multi-agent debate and returns the judge's verdict.

Public API (unchanged):
    run_debate(agents, topic) -> dict
    ask_agent(agent, topic, previous_message="", own_previous="") -> str
    parse_verdict(text) -> dict

Printing rule: the speaker label is printed BEFORE each LLM call and nothing is
printed AFTER it, because STREAMING already prints tokens live. Printing the
returned text again is what caused the duplicated output.
"""

import re
import time
from dataclasses import dataclass

from agent import Agent
from bins import CATEGORIES, normalize_category
from llm import generate

CATEGORY_LIST = ", ".join(CATEGORIES)   # single source of truth: bins.py
WIDTH = 50
JUDGE_RETRIES = 1                        # extra judge call if the category can't be parsed


# ==================================================
# DATA
# ==================================================

@dataclass(frozen=True)
class Turn:
    round_label: str
    agent: Agent
    text: str

    def line(self) -> str:
        return f"[{self.round_label}] {self.agent.name} ({self.agent.role}): {self.text}"


# ==================================================
# PROMPTS
# ==================================================

def build_agent_prompt(agent: Agent, topic: str, previous_message: str = "", own_previous: str = "") -> str:
    own_block = f"\nYou already said: {own_previous}" if own_previous else ""
    return f"""
You are participating in a live debate.
Your name: {agent.name}
Your role: {agent.role}
Your speaking style: {agent.behavior}
Debate topic: {topic}
Your belief: {agent.stance}
Previous speaker said: {previous_message or "Nobody has spoken yet."}{own_block}

Rules:
- Stay loyal to your belief
- Disagree if necessary
- Reply in 3 to 4 sentences, under 80 words
- No lists, no headings, no bold text
- Do not start your reply with your own name
- Never repeat a point you already made; respond directly to the previous speaker and add one NEW argument
- The only bins are: {CATEGORY_LIST}. Use exactly these names.
- Do not invent statistics, regulations or chemicals. If you are not sure a number is real, argue qualitatively.
"""


def build_judge_prompt(topic: str, transcript: list[Turn]) -> str:
    return f"""
You are an unbiased judge of a waste segregation debate.
Question: {topic}

Full debate transcript:
{chr(10).join(t.line() for t in transcript)}

Weigh the strongest arguments from BOTH rounds and pick exactly one category.
Ignore any claim that cites a specific chemical, statistic or regulation without support.
Reply in exactly this format, one line each:
CATEGORY: one of [{CATEGORY_LIST}]
CONFIDENCE: a number between 0 and 1
REASON: one sentence, max 20 words
DISSENT: the strongest opposing argument, max 20 words
"""


# ==================================================
# LLM CALLS
# ==================================================

def ask_agent(agent: Agent, topic: str, previous_message: str = "", own_previous: str = "") -> str:
    return generate(build_agent_prompt(agent, topic, previous_message, own_previous))


def parse_verdict(text: str) -> dict:
    """Parse the judge's reply. Category is normalized to a bins.py key when possible."""

    def field(name: str) -> str:
        m = re.search(rf"^\s*{name}\s*:\s*(.+)$", text, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else ""

    raw_category = field("CATEGORY")
    try:
        confidence = float(re.search(r"\d*\.?\d+", field("CONFIDENCE")).group())
        confidence = max(0.0, min(1.0, confidence))
    except (AttributeError, ValueError):
        confidence = None

    return {
        "category": normalize_category(raw_category) or raw_category,
        "confidence": confidence,
        "reason": field("REASON"),
        "dissent": field("DISSENT"),
        "raw": text,
    }


def _is_valid(verdict: dict) -> bool:
    return verdict["category"] in CATEGORIES


# ==================================================
# PRINTING (labels only; the model text is streamed)
# ==================================================

def _banner(title: str, char: str = "-") -> None:
    print(f"\n{char * WIDTH}\n{title}\n{char * WIDTH}")


def _announce(agent: Agent) -> None:
    print(f"\n{agent.name} ({agent.role}):")


# ==================================================
# ROUNDS
# ==================================================

def _round_one(agents: list[Agent], topic: str) -> list[Turn]:
    _banner("ROUND 1")
    turns = []
    for agent in agents:
        _announce(agent)
        turns.append(Turn("Round 1", agent, ask_agent(agent, topic)))
    return turns


def _round_two(agents: list[Agent], topic: str, round1: list[Turn]) -> list[Turn]:
    _banner("ROUND 2 - REBUTTALS")
    turns = []
    for i, agent in enumerate(agents):
        opponent = round1[i - 1]   # i=0 wraps to the last agent, so everyone has an opponent
        opponent_arg = f"{opponent.agent.name}: {opponent.text}"
        _announce(agent)
        turns.append(Turn("Round 2", agent, ask_agent(agent, topic, opponent_arg, own_previous=round1[i].text)))
    return turns


def _judge(topic: str, transcript: list[Turn]) -> dict:
    _banner("JUDGE ANALYSIS", "=")
    prompt = build_judge_prompt(topic, transcript)
    print("\nJUDGE:")
    verdict = parse_verdict(generate(prompt))

    for _ in range(JUDGE_RETRIES):
        if _is_valid(verdict):
            break
        print("\n[Judge reply had no valid category, retrying once]\nJUDGE:")
        verdict = parse_verdict(generate(prompt))
    return verdict


# ==================================================
# ENTRY POINT
# ==================================================

def run_debate(agents: list[Agent], topic: str) -> dict:
    if len(agents) < 2:
        raise ValueError("A debate needs at least two agents.")

    start = time.perf_counter()
    _banner("MULTI AGENT DEBATE", "=")
    print(f"\nMODERATOR:\n\nWelcome to tonight's debate.\nTopic: {topic}")

    round1 = _round_one(agents, topic)
    round2 = _round_two(agents, topic, round1)

    verdict = _judge(topic, round1 + round2)
    verdict["latency_s"] = time.perf_counter() - start
    return verdict
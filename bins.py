"""bin.py - maps the judge's CATEGORY verdict to a physical waste bin."""

"""Waste bins and category normalization for MADS.

The judge in debate_manager picks a category; this module turns that (often
messy) LLM text into a clean key and a printable bin recommendation.

Public API (unchanged): BINS, CATEGORIES, normalize_category, get_bin, format_bin
"""

import re
from dataclasses import dataclass

__all__ = ["Bin", "BINS", "CATEGORIES", "normalize_category", "get_bin", "format_bin"]


@dataclass(frozen=True)
class Bin:
    category: str                  # key used by the judge, e.g. "wet"
    name: str                      # human friendly bin name
    color: str                     # bin colour
    description: str               # what goes in
    examples: tuple[str, ...]      # sample items
    tip: str                       # disposal tip

    def render(self) -> str:
        """Printable summary of where an item should go."""
        return (
            f"PUT IN: {self.name} ({self.color})\n"
            f"What goes here: {self.description}\n"
            f"Examples: {', '.join(self.examples)}\n"
            f"Tip: {self.tip}"
        )


BINS: dict[str, Bin] = {
    b.category: b
    for b in (
        Bin(
            category="wet",
            name="Wet Waste Bin",
            color="green",
            description="Biodegradable, food-soiled or organic waste.",
            examples=("vegetable peels", "leftover food", "tea leaves", "garden waste"),
            tip="Can be composted. Drain excess liquid before disposal.",
        ),
        Bin(
            category="dry",
            name="Dry Waste Bin",
            color="blue",
            description="Non-biodegradable, non-recyclable dry material.",
            examples=("thermocol", "ceramics", "used tissues", "cloth scraps"),
            tip="Keep it clean and dry so it does not contaminate other waste.",
        ),
        Bin(
            category="recyclable",
            name="Recycling Bin",
            color="white",
            description="Clean dry material with a recovery route.",
            examples=("paper", "cardboard", "glass bottles", "metal cans", "PET bottles"),
            tip="Rinse containers and flatten boxes before disposal.",
        ),
        Bin(
            category="hazardous",
            name="Hazardous Waste Bin",
            color="red",
            description="Waste that is toxic, flammable, corrosive or biomedical.",
            examples=("batteries", "paint", "pesticides", "expired medicine", "sanitary waste"),
            tip="Never mix with other waste. Hand over to an authorised collector.",
        ),
        Bin(
            category="e-waste",
            name="E-Waste Collection Point",
            color="black",
            description="Discarded electrical and electronic equipment.",
            examples=("phones", "chargers", "cables", "bulbs", "circuit boards"),
            tip="Do not put in household bins. Use a certified e-waste collector.",
        ),
    )
}

# Single source of truth: import this in debate_manager instead of keeping a copy.
CATEGORIES: tuple[str, ...] = tuple(BINS)

# Whole-word patterns per category. If several appear in the text, the earliest wins.
_PATTERNS: dict[str, re.Pattern[str]] = {
    "e-waste": re.compile(r"\be[\s_-]?waste\b|\belectronic"),
    "recyclable": re.compile(r"\brecycl\w*"),
    "hazardous": re.compile(r"\bhazardous\b"),
    "wet": re.compile(r"\bwet\b"),
    "dry": re.compile(r"\bdry\b"),
}

_STRIP = re.compile(r"[\[\]\*\.\"'`]")


def normalize_category(text: str) -> str | None:
    """Turn messy LLM output ('[Wet]', 'Recycling Bin', 'e waste.') into a clean key, or None."""
    if not text:
        return None
    cleaned = _STRIP.sub("", text).strip().lower().replace("_", "-")
    if cleaned in BINS:  # exact match wins
        return cleaned
    hits = [(m.start(), key) for key, p in _PATTERNS.items() if (m := p.search(cleaned))]
    return min(hits)[1] if hits else None


def get_bin(category: str) -> Bin | None:
    """Return the Bin for a judge category, or None if it can't be matched."""
    key = normalize_category(category)
    return BINS.get(key) if key else None


def format_bin(category: str) -> str:
    """Printable summary of where an item should go."""
    b = get_bin(category)
    if b is None:
        return f"No matching bin for category '{category}'. Please check manually."
    return b.render()


if __name__ == "__main__":
    for c in ("wet", "[Recyclable]", "Recycling Bin", "E waste", "Category: e_waste.",
              "hazardous", "non-hazardous", "???"):
        print(f"--- {c!r} -> {normalize_category(c)}\n{format_bin(c)}\n")
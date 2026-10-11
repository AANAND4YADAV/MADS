# memory.py

"""
Cognitive Memory System
-----------------------

Purpose:
Simulates human-like debate memory.

This module:
- calls GPT-OSS for strategic analysis
- stores psychologically important memories
- reinforces repeated narratives
- forgets weak memories over time

Architecture Flow:

Debate Response
      ↓
GPT-OSS Strategic Extraction
      ↓
Cognitive Importance Scoring
      ↓
Memory Persistence / Decay
"""

import json

from llm import generate as generate_response


class CognitiveMemory:

    def __init__(self):

        # Persistent strategic memories
        self.long_term_memory = []

        # Repeated themes across debate
        self.dominant_narratives = {}

        # Human-like forgetting rate
        self.decay_rate = 1

    # ==================================================
    # GPT-OSS STRATEGIC EXTRACTION
    # ==================================================

    def extract_metadata(self, response):

        """
        Uses GPT-OSS to analyze debate meaning.

        Returns structured strategic metadata.
        """

        prompt = f"""
You are a strategic debate memory analyzer.

Analyze the debate response below.

Return ONLY valid JSON.

Format:

{{
    "strongest_claim": "",
    "weakness": "",
    "unanswered_point": "",
    "emotion_level": 0,
    "novelty_score": 0,
    "contradiction_detected": false,
    "main_theme": ""
}}

Debate Response:
{response}
"""

        analysis = generate_response(prompt)

        try:
            metadata = json.loads(analysis)

        except Exception:

            # Safe fallback if JSON breaks
            metadata = {
                "strongest_claim": "",
                "weakness": "",
                "unanswered_point": "",
                "emotion_level": 0,
                "novelty_score": 0,
                "contradiction_detected": False,
                "main_theme": ""
            }

        return metadata

    # ==================================================
    # HUMAN-LIKE IMPORTANCE SCORING
    # ==================================================

    def calculate_importance(self, metadata):

        """
        Simulates psychological memory importance.

        Humans remember:
        - emotional claims
        - contradictions
        - unresolved attacks
        - novel arguments
        """

        score = 0

        # Emotional intensity
        score += metadata.get("emotion_level", 0)

        # Novel arguments feel memorable
        score += metadata.get("novelty_score", 0)

        # Contradictions create mental tension
        if metadata.get("contradiction_detected"):
            score += 3

        # Unanswered attacks persist cognitively
        if metadata.get("unanswered_point"):
            score += 2

        return score

    # ==================================================
    # STORE MEMORY
    # ==================================================

    def store_memory(self, speaker, response):

        """
        Full cognitive memory pipeline.
        """

        # STEP 1 → GPT-OSS semantic analysis
        metadata = self.extract_metadata(response)

        # STEP 2 → Human-like importance scoring
        importance = self.calculate_importance(metadata)

        # STEP 3 → Build memory object
        memory_item = {

            "speaker": speaker,

            "strongest_claim":
                metadata.get("strongest_claim"),

            "weakness":
                metadata.get("weakness"),

            "unanswered_point":
                metadata.get("unanswered_point"),

            "main_theme":
                metadata.get("main_theme"),

            "importance":
                importance,

            "strength":
                importance
        }

        # STEP 4 → Store only important memories
        if importance >= 7:
            self.long_term_memory.append(memory_item)

        # STEP 5 → Reinforce repeated narratives
        self.update_narratives(
            metadata.get("main_theme")
        )

    # ==================================================
    # DOMINANT NARRATIVE REINFORCEMENT
    # ==================================================

    def update_narratives(self, theme):

        """
        Repeated themes become dominant narratives.
        """

        if not theme:
            return

        if theme not in self.dominant_narratives:
            self.dominant_narratives[theme] = 0

        self.dominant_narratives[theme] += 1

    # ==================================================
    # HUMAN-LIKE MEMORY DECAY
    # ==================================================

    def decay_memories(self):

        """
        Simulates forgetting over time.
        """

        updated_memory = []

        for memory in self.long_term_memory:

            memory["strength"] -= self.decay_rate

            # Remove weak memories
            if memory["strength"] > 0:
                updated_memory.append(memory)

        self.long_term_memory = updated_memory

    # ==================================================
    # STRATEGIC CONTEXT RETRIEVAL
    # ==================================================

    def get_strategic_context(self):

        """
        Returns strategically important memory
        for future agents.
        """

        context = []

        context.append(
            "Strategic Debate Memory:\n"
        )

        # Important persistent memories
        for memory in self.long_term_memory:

            context.append(
                f"- {memory['speaker']} strongest claim:"
            )

            context.append(
                f"  {memory['strongest_claim']}"
            )

            if memory["weakness"]:

                context.append(
                    f"  Weakness: {memory['weakness']}"
                )

            if memory["unanswered_point"]:

                context.append(
                    f"  Unanswered Point:"
                    f" {memory['unanswered_point']}"
                )

        # Dominant narratives
        if self.dominant_narratives:

            context.append(
                "\nDominant Narratives:"
            )

            sorted_narratives = sorted(
                self.dominant_narratives.items(),
                key=lambda x: x[1],
                reverse=True
            )

            for theme, count in sorted_narratives:

                context.append(
                    f"- {theme} repeated {count} times"
                )

        return "\n".join(context)
"""Intent classification (§3 classify_query_intent — FC22 routing, FC33 split,
FC28 clarification). The LLM path uses structured output with the
DETERMINISTIC RULES as its safety net (degraded, never fabricated); the stub
encodes the routing contract itself for offline tests and demos."""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agent.llm.prompts import CLASSIFY_SYSTEM
from agent.tools.course_ids import course_mentions

_logger = logging.getLogger("agent.classify")

INTENTS = ("exact", "semantic", "requirements", "recommend", "audit", "propose_action",
           "plan_generation", "explore", "clarify", "chitchat")

_FOLLOWUP = re.compile(
    r"^\s*(yes|yeah|yep|yup|sure|ok(ay)?|please|go ahead|do it|sounds good|let'?s do it"
    r"|that would be (great|helpful)|absolutely|definitely|of course|tell me more"
    r"|go on|continue)\b[\w\s,!.']*$", re.I)

# FC42: open-ended exploration / brainstorming (stub routing contract).
_EXPLORE = re.compile(
    r"\b(BRAINSTORM|EXPLORE|IDEAS?|OPTIONS|COMPARE|HELP ME (THINK|DECIDE|CHOOSE|PICK)"
    r"|INTERESTED IN|\bI (REALLY )?(LIKE|ENJOY|LOVE)\b|WHAT (COULD|CAN) I DO"
    r"|WHAT (MAJORS|DEGREES|PROGRAMS|CONCENTRATIONS|TRACKS)"
    r"|(MAJORS|DEGREES|PROGRAMS|CONCENTRATIONS|TRACKS)\b.*\b(AVAILABLE|OFFERED|EXIST|ARE THERE))")


def _lenient_parse(text: Optional[str]) -> Optional[dict]:
    """Parse a classifier reply that isn't strict JSON (YAML-ish or ```json
    fenced). YAML is a JSON superset, so one loader covers both."""
    if not text:
        return None
    import yaml

    body = re.sub(r"^\s*```[a-zA-Z]*\s*|\s*```\s*$", "", str(text))
    try:
        data = yaml.safe_load(body)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) and data.get("intent") else None


def is_followup_reply(text: str) -> bool:
    """FC42/FC27: a short conversational reply ("yes please", "sure") that
    only makes sense against the advisor's previous turn."""
    text = (text or "").strip()
    return len(text.split()) <= 6 and bool(_FOLLOWUP.match(text))


@dataclass
class Classification:
    """Router output — nodes read only this (no stringly-typed branching)."""

    intent: str
    params: Dict = field(default_factory=dict)
    followup: Optional[str] = None


def _rules_fallback(user_input: str, history: Optional[List[str]] = None,
                    student_context: Optional[dict] = None) -> Classification:
    """The deterministic rules, used when the LLM path fails/underperforms.
    Fact-LOOKUP and routing stay grounded either way."""
    return StubClassifier().classify(user_input, history=history, student_context=student_context)


class LLMClassifier:
    """LLM-backed classification (structured output) with the stub rules as a
    safety net — a flaky model degrades the ROUTING, never the data."""

    def __init__(self, llm) -> None:
        from pydantic import BaseModel

        class IntentSchema(BaseModel):
            # Free-form fields: strict adherence varies by provider, and a
            # hard schema would explode instead of degrading to the rules.
            intent: Optional[str] = None
            params: dict = {}
            clarification_question: Optional[str] = None

        self._structured = llm.with_structured_output(IntentSchema, method="json_schema")

    def classify(
        self, user_input: str, history: Optional[List[str]] = None,
        student_context: Optional[dict] = None,
    ) -> Classification:
        from langchain_core.messages import HumanMessage, SystemMessage

        context = [
            "Recent conversation (oldest first):"] + list(history or []) + [
            "Student context:", str(student_context or {}),
            "Message to classify:", user_input,
        ]
        try:
            raw = self._structured.invoke([
                SystemMessage(content=CLASSIFY_SYSTEM),
                HumanMessage(content="\n".join(context)),
            ])
        except Exception as exc:
            # The model often answers the schema in YAML-ish / fenced text; the
            # parser error carries that raw output — recover it before degrading.
            raw = _lenient_parse(getattr(exc, "llm_output", None))
            if raw is None:
                _logger.warning("LLM classification unavailable (%s) — rule-based routing", exc)
                return _rules_fallback(user_input, history, student_context)

        if isinstance(raw, dict):
            from types import SimpleNamespace
            raw = SimpleNamespace(**{k: raw.get(k) for k in ("intent", "params", "clarification_question")})
        intent = (getattr(raw, "intent", None) or "").strip().lower()
        if intent not in INTENTS:
            # The model answered, but not in the contract — degrade to rules.
            _logger.warning("LLM classifier gave unknown intent %r — rule-based routing", intent)
            return _rules_fallback(user_input, history, student_context)
        followup = getattr(raw, "clarification_question", None)
        if intent == "clarify":
            followup = followup or "Could you tell me a bit more about what you'd like to do?"
        params = self._normalize_params(dict(getattr(raw, "params", None) or {}), user_input)
        if history and is_followup_reply(user_input) and intent in ("exact", "semantic", "chitchat"):
            # FC42: "yes please" to the advisor's offer is never a course lookup.
            return Classification(intent="explore", params={"query": user_input})
        return Classification(intent=intent, params=params, followup=followup)

    @staticmethod
    def _normalize_params(params: dict, user_input: str) -> dict:
        """Free-form `params` → the graph contract (course_mentions list,
        query string): one normalization point keeps downstream nodes stable.
        Action params (course_id/status/major…) pass through untouched."""
        mentions = params.get("course_mentions")
        if isinstance(mentions, str):
            mentions = [mentions]
        if not mentions:
            mentions = course_mentions(user_input) or None  # ids verbatim from the message
        if mentions:
            params["course_mentions"] = mentions
        if params.get("action_type") in {"add_class", "change_class_status"} and not params.get("course_id") and mentions:
            params["course_id"] = mentions[0]
        if not params.get("query"):
            params.setdefault("query", user_input)
        return params


class StubClassifier:
    """Deterministic rule-based stand-in (offline runs, tests, demos, and the
    LLM path's degraded fallback). Encodes the routing contract; records the
    histories it was given so tests can assert FC27 context flow."""

    def __init__(self) -> None:
        self.seen_histories: List[List[str]] = []

    def classify(
        self, user_input: str, history: Optional[List[str]] = None,
        student_context: Optional[dict] = None,
    ) -> Classification:
        self.seen_histories.append(list(history or []))
        text = (user_input or "").strip()
        upper = text.upper()
        mentions = course_mentions(upper)

        if history and is_followup_reply(text):
            return Classification("explore", {"query": text})  # FC42/FC27 follow-up

        def in_original(match) -> str:
            """Slice from the original text so extracted names keep case."""
            return text[match.start(1):match.end(1)].strip()

        # ----- FC3/FC6 plan edits (FC23: still need explicit confirmation)
        term = re.search(r"\b(FALL|SPRING|SUMMER)\s+(\d{4})\b", upper)
        term_text = f"{term.group(1).capitalize()} {term.group(2)}" if term else None
        plan_mentions = course_mentions(
            upper.replace(term.group(0), " ") if term else upper)
        if re.search(r"\bACTIVATE\b.*\bPLAN\b|\bMAKE\b.*\bPLAN\b.*\bACTIVE\b", upper):
            return Classification("propose_action", {"action_type": "activate_plan"})
        if re.search(r"\bPLAN\b", upper) and plan_mentions and not re.search(
                r"\b(GENERATE|BUILD|CREATE)\b", upper):
            if re.search(r"\b(REMOVE|DROP|DELETE|TAKE OUT)\b", upper):
                return Classification("propose_action", {
                    "action_type": "plan_remove_course", "course_id": plan_mentions[0]})
            if re.search(r"\bMOVE\b|\bRESCHEDULE\b", upper):
                if not term_text:
                    return Classification("propose_action", {
                        "action_type": "plan_move_course", "course_id": plan_mentions[0]},
                        followup="Which semester of your plan should it move to (e.g. Fall 2027)?")
                return Classification("propose_action", {
                    "action_type": "plan_move_course", "course_id": plan_mentions[0],
                    "semester_term": term_text})
            if re.search(r"\bADD\b|\bPUT\b", upper):
                if not term_text:
                    return Classification("propose_action", {
                        "action_type": "plan_add_course", "course_id": plan_mentions[0]},
                        followup="Which semester of your plan should it go in (e.g. Fall 2027)?")
                return Classification("propose_action", {
                    "action_type": "plan_add_course", "course_id": plan_mentions[0],
                    "semester_term": term_text})
        if re.search(r"\bMOVE\b", upper) and plan_mentions and term_text:
            return Classification("propose_action", {
                "action_type": "plan_move_course", "course_id": plan_mentions[0],
                "semester_term": term_text})

        # ----- degree / concentration requirements (FC18/FC22; SQLite record).
        # Exploratory ("considering… what classes would I need") is a question,
        # never a FC23 proposal.
        if re.search(r"\b(DEGREE|MAJOR|CONCENTRATION|TRACK)\b", upper) and re.search(
                r"\bREQUIREMENTS?\b|\bREQUIRED\b|\b(CLASSES|COURSES)\s+(I'?LL|I WOULD|WOULD I|DO I|I WILL|WILL I)\s+NEED"
                r"|\bWHAT\s+(DO|WOULD|WILL)\s+I\s+NEED\b|\bNEED TO TAKE\b", upper):
            params: Dict = {"query": text}
            track = (re.search(r"\b(?:CONCENTRATION|TRACK)\s+TO\s+(.+?)\s*(?:[.?!]|$)", text, re.I)
                     or re.search(r"\b(?:THE|FOR|IN)\s+(?!MY\b|A\b|AN\b|OUR\b|THIS\b)([A-Za-z][A-Za-z &\-]*?)\s+(?:CONCENTRATION|TRACK)\b",
                                  text, re.I))
            if track:
                params["concentration"] = track.group(1).strip()
            return Classification("requirements", params)

        # ----- FC23 proposals (actions need explicit confirmation later)
        change_status = re.search(
            r"\b(PASSED|TAKEN|FAILED|IN PROGRESS|IN-PROGRESS)\b", upper)
        if re.search(r"\bADD\b", upper) and mentions:
            return Classification("propose_action", {
                "action_type": "add_class", "course_id": mentions[0]})
        if change_status and mentions and re.search(r"\b(MARK|SET|CHANGE|I ALREADY|COMPLETED)\b", upper):
            status = change_status.group(1).lower().replace("in-progress", "in_progress")
            return Classification("propose_action", {
                "action_type": "change_class_status", "course_id": mentions[0],
                "status": status})
        if re.search(r"\b(SWITCH(ING)?|CHANGE)\b", upper) and re.search(r"\bMAJOR\b", upper):
            target = re.search(r"\bMAJOR\b.*?\bTO\s+(.+)$", upper)
            if not target:
                return Classification("propose_action", {
                    "action_type": "change_major"},
                    followup="Which major would you like to switch to?")
            return Classification("propose_action", {
                "action_type": "change_major", "major_name": in_original(target)})
        if re.search(r"\b(SWITCH(ING)?|CHANGE)\b", upper) and re.search(r"\bCONCENTRATION\b", upper):
            target = re.search(r"\bCONCENTRATION\b.*?\bTO\s+(.+)$", upper)
            if not target:
                return Classification("propose_action", {
                    "action_type": "change_concentration"},
                    followup="Which concentration would you like to switch to?")
            return Classification("propose_action", {
                "action_type": "change_concentration",
                "concentration": in_original(target)})
        if re.search(r"\bDEGREE\b", upper) and re.search(r"\b(SET|TRACK)\b", upper):
            degree = re.search(r"\bDEGREE\b\s+TO\s+([A-Za-z0-9\-]+)", upper)
            if not degree:
                return Classification("propose_action", {"action_type": "change_degree"},
                                      followup="Which degree should I track (e.g. BS-CS)?")
            return Classification("propose_action", {
                "action_type": "change_degree", "degree_id": degree.group(1).strip()})

        # ----- deterministic plan generation (FC2/FC25; engine owns the math)
        if re.search(r"\b(GENERATE|CREATE|BUILD|DRAW UP|PLAN OUT)\b", upper) and \
                re.search(r"\b(DEGREE\s+)?PLAN\b", upper):
            target = re.search(r"\bPLAN\b.*?\bFOR\s+(.+)$", upper)
            params: Dict = {}
            filler = target and target.group(1).strip().strip(" .!?").lower() in {
                "me", "my", "it", "this", "that"}
            if target and not filler:
                params["target_major"] = in_original(target).strip(" .!?")
            else:
                track = re.search(r"\b(?:CONCENTRATION|TRACK|SPECIALIZATION)\s+(?:IN|OF|ON)\s+(.+)$", upper)
                if track:  # "plan with a concentration in X" → own major, track X (FC1)
                    params["concentration"] = in_original(track).strip(" .!?")
            return Classification("plan_generation", params)

        # ----- open-ended exploration / brainstorming (FC42)
        if _EXPLORE.search(upper):
            return Classification("explore", {"query": text})

        # ----- exact facts (FC33 SQLite side)
        if mentions and re.search(
                r"\b(WHAT TIME|WHEN|WHO TEACH|WHO IS|HOW MANY|SEATS|SECTIONS"
                r"|MEET|SCHEDULE|TEACH)", upper):
            return Classification("exact", {"course_mentions": mentions})

        # ----- the student's own active plan (FC22/FC27; SQLite, FC33)
        if re.search(r"\b(MY|THE)\s+(DEGREE\s+)?PLAN\b|\bPLANNED\b"
                     r"|\bWHAT AM I TAKING\b", upper) and not re.search(
                r"\b(GENERATE|BUILD|CREATE)\b", upper):
            return Classification("exact", {"topic": "plan"})

        # ----- audits (FC24; deterministic)
        if re.search(r"\bWHAT (CLASSES|COURSES) (CAN|COULD|SHOULD) I\b", upper):
            return Classification("recommend", {"query": None})
        if re.search(r"\b(CAN I|AM I (ELIGIBLE|ABLE|READY)|SHOULD I TAKE)\b", upper) and mentions:
            return Classification("audit", {"course_mentions": mentions})
        if re.search(r"\b(HOW CLOSE|ON TRACK|PROGRESS|CLOSER? TO|GRADUAT)\b", upper):
            return Classification("audit", {})  # progress audit → FC19 fuel

        # ----- guarded recommendation (FC22, validator-filtered)
        if re.search(r"\b(WHAT SHOULD I|RECOMMEND|SUGGEST|ELECTIVE)", upper):
            return Classification("recommend", {"query": text})

        # ----- semantic catalog questions (FC33 Chroma side)
        if re.search(
                r"\b(WHAT (IS|DOES|ARE)|COVER|DESCRIBE|TELL ME ABOUT|REQUIREMENT)", upper):
            return Classification("semantic", {"query": text})

        return Classification("chitchat", {})
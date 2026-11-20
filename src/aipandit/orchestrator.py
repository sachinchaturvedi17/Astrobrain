"""The Pandit: one entry point that turns (birth details, question) into a verified answer.

    start(birth)  -> Session   chart + facts + rule inference, computed once, as of "now"
    ask(session, question) -> Answer

Order of decisions (earlier steps cannot be overridden by later ones, or by any model):
  1. crisis wording      -> supportive reply + helplines, no astrology
  2. lifespan/death      -> decline
  3. plan -> select -> compose (LLM if configured, else template)
  4. gates; LLM output that fails is retried (max `llm_attempts`), then replaced by the template composer
  5. if even the template output fails the gates (a bug) -> a safe minimal message, never unverified text
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Optional

from . import numerology
from . import phrasebook as P
from .composer import ComposeError, ComposeInput, LLMComposer, TemplateComposer
from .derive import enrich
from .hindi import detect_language
from .gates import MINOR_BLOCK, GateContext, GateReport, check, check_text_only
from .inference import Inference, infer
from .intake import BirthInput
from .kundli import Kundli, KundliConfig, generate_kundli
from .planner import Intent, classify
from .reading import Reading, Statement, render
from .rulepacks import all_rules
from .rulepacks.hinglish import hinglish_text
from .salience import SelectionPolicy, select


@dataclass
class Session:
    birth: BirthInput
    kundli: Kundli
    store: object
    inference: Inference
    as_of: datetime
    minor: bool
    time_uncertain: bool
    supported_scopes: frozenset
    history: list = field(default_factory=list)


@dataclass
class Answer:
    text: str
    reading: Optional[Reading]
    gate: GateReport
    trace: dict


class Pandit:
    def __init__(self, llm=None, rules=None, engine=None, policy: Optional[SelectionPolicy] = None,
                 llm_attempts: int = 2, now=None):
        self.llm = LLMComposer(llm) if llm is not None else None
        self.rules = rules if rules is not None else all_rules()
        self.engine, self.policy, self.llm_attempts = engine, policy or SelectionPolicy(), llm_attempts
        self._now = now or (lambda: datetime.now(timezone.utc))
        self.template = TemplateComposer()

    # ------------------------------------------------------------------------------------------ session
    def start(self, birth: BirthInput, config: Optional[KundliConfig] = None) -> Session:
        now = self._now()
        k = generate_kundli(birth, config, self.engine, today=now.date())
        store = enrich(k, as_of=now)
        if birth.date:                                  # numerology depends on the civil date only: it works without a birth time
            store = numerology.enrich(store, birth.date, birth.name or None, now)
        binary = birth.gender_rule_mode == "binary" and birth.gender in ("male", "female")
        inf = infer(store, self.rules, gender=birth.gender if binary else None,
                    partnership=birth.partnership_type)
        minor = birth.subject_is_minor is True
        supported = frozenset(s for r in self.rules for s in r.scope)
        if minor:
            supported -= self.policy.minor_blocked_scopes
        supported -= self.policy.blocked_scopes
        return Session(birth, k, store, inf, now, minor,
                       birth.time is None or birth.time_certainty != "exact", supported)

    # ------------------------------------------------------------------------------------------ answers
    def ask(self, s: Session, question: str, lang: Optional[str] = None) -> Answer:
        lang = lang if lang in ("en", "hi", "hg") else detect_language(question)
        B = P.bundle(lang)
        intent = classify(question)
        trace: dict = {"lang": lang, "intent": intent.kind, "scopes": sorted(intent.scopes), "composer": None, "attempts": 0,
                       "fallback": False, "selected": [], "suppressed": {}, "violations": []}
        if intent.kind == "crisis":
            return self._fixed(s, B.CRISIS, trace, "crisis", B)
        if intent.kind == "death":
            return self._fixed(s, B.DEATH, trace, "death", B)

        scopes = intent.scopes
        if "financial" in intent.declined and scopes == frozenset({"wealth"}):
            scopes = frozenset()                     # "should I invest ... money?": the money word is not a topic request
        declined_only = bool(intent.declined) and not scopes and not intent.dasha
        dasha_only = intent.dasha and not scopes            # "what is my dasha?" gets the dasha, not an overview
        pool = [] if (declined_only or dasha_only) else list(s.inference.firings)
        minor_text = {}
        if s.minor:                                   # wording about marriage/romance is out even under another scope
            minor_text = {f.rule_id: "minor_text" for f in pool
                          if MINOR_BLOCK.search(f.interpretation) or MINOR_BLOCK.search(hinglish_text(f.rule_id) or "")}
            pool = [f for f in pool if f.rule_id not in minor_text]
        sel = self._select(pool, scopes, intent, s)
        sel.suppressed.update(minor_text)
        trace["selected"] = [f.rule_id for f in sel.chosen]
        trace["suppressed"] = dict(sel.suppressed)
        inp = ComposeInput(question, intent, sel.chosen, s.store, sel.uncovered_scopes, s.minor,
                           s.time_uncertain, bool(s.inference.undetermined), lang)
        ctx = GateContext({f.rule_id: f for f in sel.chosen}, s.store, s.minor, s.time_uncertain)

        reading, report = None, GateReport()
        if self.llm is not None:
            for _ in range(self.llm_attempts):
                trace["attempts"] += 1
                try:
                    cand = self.llm.compose(inp)
                except ComposeError as e:
                    trace["violations"].append(f"compose_error: {e}")
                    continue
                except Exception as e:                       # network/client failure: never block the user
                    trace["violations"].append(f"llm_error: {type(e).__name__}")
                    break
                rep = check(cand, ctx)
                if rep.passed:
                    reading, report, trace["composer"] = cand, rep, cand.composer or "llm"
                    break
                trace["violations"].append("gate: " + ",".join(rep.codes()))
            if reading is None:
                trace["fallback"] = True
        if reading is None:
            cand = self.template.compose(inp)
            rep = check(cand, ctx)
            if rep.passed:
                reading, report, trace["composer"] = cand, rep, "template"
            else:                                            # a bug, not a content problem: fail closed
                trace["violations"].append("template_gate: " + ",".join(rep.codes()))
                trace["composer"] = "safe_minimal"
                return Answer(B.SAFE_MINIMAL, None, rep, trace)
        text = render(reading, lang if reading.statements and reading.statements[0].text != P.hi.NOTE_ENGLISH_ANSWER else "en")
        trace["lenses"] = sorted({x.lens for x in reading.statements if x.lens})
        s.history.append((question, text))
        return Answer(text, reading, report, trace)

    def _select(self, pool: list, scopes: frozenset, intent: Intent, s: Session):
        """Each lens is selected on its own, then merged. Total readings stay within policy.max_total:
        numerology takes up to 2 slots in an overview, 3 on a topic, 4 when the user asked for numerology itself;
        the kundli gets the rest (or nothing, if the user asked for numerology without naming the kundli)."""
        pol = self.policy
        num_pool = [f for f in pool if f.system == "numerology"]
        kun_pool = [f for f in pool if f.system != "numerology"]
        if intent.numerology_only:
            kun_pool = []
        cap = 4 if intent.numerology_only else (3 if (scopes or intent.numerology) else 2)
        num_sel = select(num_pool, scopes, replace(pol, max_total=cap, max_per_scope=cap), s.supported_scopes, s.minor)
        if not num_pool:
            kun_sel = select(kun_pool, scopes, pol, s.supported_scopes, s.minor)
            return kun_sel
        room = max(pol.max_total - len(num_sel.chosen), 1)
        kun_sel = select(kun_pool, scopes, replace(pol, max_total=room), s.supported_scopes, s.minor)
        if intent.numerology_only:
            for f in [f for f in pool if f.system != "numerology"]:
                kun_sel.suppressed.setdefault(f.rule_id, "numerology_only")
        kun_sel.suppressed.update({k: v for k, v in num_sel.suppressed.items()})
        kun_sel.chosen = kun_sel.chosen + num_sel.chosen
        return kun_sel

    def _fixed(self, s: Session, text: str, trace: dict, name: str, B=P) -> Answer:
        rep = check_text_only(text)
        if not rep.passed:                                   # constants are tested; this is belt and braces
            text = B.SAFE_MINIMAL
        trace["composer"] = name
        s.history.append(("", text))
        return Answer(text, None, rep, trace)

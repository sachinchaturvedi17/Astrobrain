"""Astrobrain v0.7+ extensions: unifies Kundli, Numerology, Palmistry & Gochara."""
from __future__ import annotations

from datetime import date
from typing import Optional

from .gochara_and_scopes import enrich_gochara, gochara_rules, life_area_rules
from .inference import infer
from .intake import BirthInput
from .kundli import KundliConfig, generate_kundli
from .numerology import enrich as enrich_numerology
from .palmistry import PalmObservation, enrich as enrich_palm, palm_rules
from .rulepacks import all_rules


def build_astrobrain_store(
    birth: BirthInput,
    *,
    palm_obs: Optional[PalmObservation] = None,
    transit_date: Optional[date] = None,
    config: Optional[KundliConfig] = None,
    today: Optional[date] = None,
):
    """Build a unified, frozen FactStore with Kundli, Numerology, Palm & Gochara facts."""
    ref_today = today or date.today()
    kundli = generate_kundli(birth, config=config, today=ref_today)
    store = kundli.facts
    if birth.date:
        store = enrich_numerology(store, birth.date, birth.name or None)
    store = enrich_palm(store, palm_obs)
    store = enrich_gochara(store, on_date=transit_date or ref_today)
    return kundli, store


def evaluate_astrobrain_rules(store):
    """Evaluate base rules + new life-area rules + palmistry + gochara rules."""
    combined_rules = list(all_rules()) + life_area_rules() + palm_rules() + gochara_rules()
    return infer(store, combined_rules)

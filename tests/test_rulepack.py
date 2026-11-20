import json
from collections import Counter

from aipandit.derive import enrich
from aipandit.diagnostics import sample_births
from aipandit.kundli import generate_kundli
from aipandit.rules import dump_rules, load_rules, UNPINNED
from chartkit import RULES


def test_rule_ids_unique_and_namespaced():
    ids = [r.rule_id for r in RULES]
    assert len(ids) == len(set(ids)) and all(i.startswith("parashari.") for i in ids)


def test_every_rule_declares_rarity_and_provenance():
    assert all(r.rarity for r in RULES)
    assert all(r.provenance != "unspecified" for r in RULES)
    assert all(r.notes.strip() for r in RULES), "every rule needs auditor notes (assumptions/variants)"


def test_review_status_is_only_claimed_where_the_source_is_pinned():
    for r in RULES:
        if r.review_status != "draft":
            assert r.source.chapter != UNPINNED and r.source.edition, r.rule_id
        if r.provenance == "classical_text":
            assert r.source.chapter != UNPINNED, r.rule_id
    # honesty guard: nobody has astrologer-audited anything yet
    assert not any(r.review_status == "astrologer_audited" for r in RULES)


def test_adverse_rules_are_flagged():
    adverse = {r.rule_id for r in RULES if r.adverse}
    for must in ("parashari.yoga.kemadruma", "parashari.dosha.manglik_from_lagna",
                 "parashari.dosha.kaal_sarp", "parashari.yoga.vish", "parashari.wealth.daridra_sun_2h_saturn_aspect"):
        assert must in adverse


def test_interpretations_do_not_make_flat_predictions():
    banned = ("will die", "death", "will lose", "will divorce", "disease", "cancer", "accident", "will become rich")
    for r in RULES:
        text = r.interpretation.lower()
        assert not any(b in text for b in banned), (r.rule_id, text)
        assert "traditional" in text or "conventional" in text or "classical" in text, r.rule_id


def test_json_export_roundtrip(tmp_path):
    path = tmp_path / "rules.json"
    dump_rules(RULES, path)
    back = load_rules(path)
    assert [r.to_dict() for r in back] == [r.to_dict() for r in RULES]
    assert json.loads(path.read_text())[0]["review_status"] in ("draft", "definition_checked")


def test_rule_vocabulary_matches_what_the_pipeline_can_produce():
    """Every (system, subject, predicate) a rule reads must exist in at least one generated chart,
    so a typo in a rule cannot silently make it UNKNOWN forever."""
    produced = set()
    for b in sample_births(150, seed=5):
        for f in enrich(generate_kundli(b)):
            produced.add(f.fact_id)
    missing = {}
    for r in RULES:
        for a in r.condition.atoms():
            fid = f"{a.system}:{a.subject}:{a.predicate}"
            if fid not in produced:
                missing.setdefault(fid, []).append(r.rule_id)
    assert not missing, missing

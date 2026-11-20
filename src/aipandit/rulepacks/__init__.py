from .numerology import numerology_rules
from .parashari import RULES as PARASHARI_RULES, parashari_rules


def all_rules() -> list:
    """Parashari + numerology. Systems stay separate: no rule reads facts from more than one."""
    return parashari_rules() + numerology_rules()


__all__ = ["PARASHARI_RULES", "parashari_rules", "numerology_rules", "all_rules"]

"""The four verdicts. Abstaining (UNCLEAR) is a verdict, not a miss."""

from enum import Enum


class Verdict(Enum):
    CONFLICT = "CONFLICT"
    COMPLIANT = "COMPLIANT"
    UNCLEAR = "UNCLEAR"
    ADR_OVERTAKEN = "ADR-OVERTAKEN"

from adrcheck.domain.exception import parse_exceptions

MESSAGE = """store: write the key by hand for the migration

Adr-Exception: ADR-0002 one-off backfill, row_key is not importable here
Adr-Exception: ADR-0007
Signed-off-by: K
"""


def test_a_trailer_with_a_reason_waives_the_adr():
    waived, _problems = parse_exceptions(MESSAGE)
    assert [(w.adr_number, w.reason) for w in waived] == [(2, "one-off backfill, row_key is not importable here")]


def test_a_trailer_without_a_reason_is_reported_not_honoured():
    _waived, problems = parse_exceptions(MESSAGE)
    assert problems == ("Adr-Exception for ADR-7 has no reason and is ignored",)


def test_trailer_key_is_case_insensitive_and_accepts_bare_numbers():
    waived, _ = parse_exceptions("x\n\nADR-EXCEPTION: 12 because\n")
    assert [(w.adr_number, w.reason) for w in waived] == [(12, "because")]

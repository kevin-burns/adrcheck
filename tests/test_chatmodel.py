"""The chat-model seats: prompts are built from obligations and the diff, replies are parsed strictly, any provider."""

import json

from adrcheck.chatmodel import ChatModelSeats, ChatReply, ChatRequest
from adrcheck.chatmodel.parse import parse_compile_reply, parse_judge_reply
from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.change import Change, FileChange, Line
from adrcheck.domain.obligation import Checkability, Obligation
from adrcheck.domain.verdict import Verdict
from adrcheck.ports import Context, JudgeCase

ADR = Adr(
    title="One key",
    status=Status.ACCEPTED,
    source="0002.md",
    number=2,
    sections={"context": "ctx", "decision": "Every row is keyed by store.row_key.", "consequences": "none"},
)
OBL = Obligation(
    id="ADR-2/1",
    adr_number=2,
    kind="MUST",
    text="rows keyed by row_key",
    quote="keyed by store.row_key",
    checkability=Checkability.STRUCTURAL,
)
CHANGE = Change(
    ref="c1",
    parent="c0",
    message="m",
    files=(
        FileChange("enrich/store.py", "enrich/store.py", added=(Line("enrich/store.py", "+", 11, 'key = row["url"]'),)),
    ),
)


class Recorder:
    """A ChatRunner that records what it was asked and answers the same text every time."""

    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def run(self, request: ChatRequest) -> ChatReply:
        self.prompts.append(request.system + "\n" + request.user)
        return ChatReply(text=self.reply, tokens_in=15, tokens_out=3, cost_usd=0.01, latency_ms=200)


def test_judge_prompt_carries_the_obligations_the_diff_lines_and_the_post_image():
    run = Recorder(json.dumps({"not_relevant": [], "findings": []}))
    judge = ChatModelSeats(run)
    judge.judge(CHANGE, (JudgeCase(ADR, (OBL,)),), Context(post_images={"enrich/store.py": "def save(): ..."}))
    [prompt] = run.prompts
    assert "ADR-2/1" in prompt and "keyed by store.row_key" in prompt
    assert '+ key = row["url"]' in prompt
    assert "def save(): ..." in prompt
    assert "Considered Options" not in prompt  # we never show the judge the roads not taken as if they bound


def test_one_prompt_carries_every_adr_of_the_change_and_the_diff_once():
    other = Adr(
        title="No url keys",
        status=Status.ACCEPTED,
        source="0009.md",
        number=9,
        sections={"decision": "Never key by url."},
    )
    nine = Obligation(
        id="ADR-9/1",
        adr_number=9,
        kind="MUST_NOT",
        text="t",
        quote="Never key by url.",
        checkability=Checkability.INTENT,
    )
    run = Recorder(json.dumps({"not_relevant": [9], "findings": []}))
    ChatModelSeats(run).judge(CHANGE, (JudgeCase(ADR, (OBL,)), JudgeCase(other, (nine,))), Context(post_images={}))
    [prompt] = run.prompts
    assert "ADR-2: One key" in prompt and "ADR-9: No url keys" in prompt
    assert "ADR-2/1" in prompt and "ADR-9/1" in prompt
    assert prompt.count('+ key = row["url"]') == 1


def test_judge_reply_is_parsed_into_findings_with_verdicts_and_token_counts():
    reply = json.dumps(
        {
            "not_relevant": [],
            "findings": [
                {
                    "obligation_id": "ADR-2/1",
                    "verdict": "CONFLICT",
                    "path": "enrich/store.py",
                    "line_text": 'key = row["url"]',
                    "quote": "keyed by store.row_key",
                    "reason": "keys by url",
                }
            ],
        }
    )
    judge = ChatModelSeats(Recorder(reply))
    resp = judge.judge(CHANGE, (JudgeCase(ADR, (OBL,)),), Context(post_images={}))
    assert resp.not_relevant == frozenset() and resp.findings[0].verdict is Verdict.CONFLICT
    assert (resp.tokens_in, resp.tokens_out, resp.cost_usd, resp.latency_ms) == (15, 3, 0.01, 200)


def test_a_fenced_or_chatty_reply_still_parses():
    reply = 'Here you go:\n```json\n{"not_relevant": [2], "findings": []}\n```\n'
    assert parse_judge_reply(reply).not_relevant == frozenset({2})


def test_an_unparseable_reply_is_an_error_not_a_verdict():
    resp = parse_judge_reply("I cannot help with that.")
    assert resp.not_relevant == frozenset() and resp.findings == () and resp.error.startswith("unparseable")


def test_compile_reply_becomes_obligations_with_ids_derived_from_the_adr():
    reply = json.dumps(
        {
            "obligations": [
                {
                    "kind": "MUST",
                    "text": "rows keyed by row_key",
                    "quote": "keyed by store.row_key",
                    "checkability": "structural",
                    "mandates": ["row_key"],
                    "forbids": [],
                }
            ]
        }
    )
    [o] = parse_compile_reply(reply, ADR)
    assert (o.id, o.adr_number, o.checkability, o.mandates) == ("ADR-2/1", 2, Checkability.STRUCTURAL, ("row_key",))


def test_compile_drops_an_obligation_whose_quote_is_not_in_the_binding_sections():
    reply = json.dumps({"obligations": [{"kind": "MUST", "text": "x", "quote": "ctx", "checkability": "mechanical"}]})
    assert parse_compile_reply(reply, ADR) == ()


def test_compile_keeps_only_mandates_the_adr_itself_names():
    reply = json.dumps(
        {
            "obligations": [
                {
                    "kind": "MUST",
                    "text": "x",
                    "quote": "keyed by store.row_key",
                    "checkability": "mechanical",
                    "mandates": ["store.row_key", "fold_count", "time.sleep"],
                    "forbids": ["hashlib."],
                }
            ]
        }
    )
    [o] = parse_compile_reply(reply, ADR)
    assert o.mandates == ("store", "row_key")
    assert o.forbids == ("hashlib.",)  # kept for the report; classification no longer uses them


def test_compile_splits_a_dotted_anchor_into_the_names_code_spells():
    """Prose says `RepoReader.contains()`; code says `repo.contains` on a RepoReader. Probe the names, not the prose."""
    adr = Adr(
        title="Probe",
        status=Status.ACCEPTED,
        source="0007.md",
        number=7,
        sections={
            "context": "",
            "decision": "The `RepoReader.contains()` probe answers it; see src/adrcheck/ports.py.",
        },
    )
    reply = json.dumps(
        {
            "obligations": [
                {
                    "kind": "MUST",
                    "text": "x",
                    "quote": "The `RepoReader.contains()` probe answers it",
                    "checkability": "structural",
                    "mandates": ["RepoReader.contains", "RepoReader.contains()", "src/adrcheck/ports.py"],
                }
            ]
        }
    )
    [o] = parse_compile_reply(reply, adr)
    assert o.mandates == ("RepoReader", "contains", "src/adrcheck/ports.py")


class Failing:
    def run(self, request: ChatRequest) -> ChatReply:
        raise ConnectionError("no route to host")


def test_a_runner_that_raises_is_a_judge_error_not_an_exception():
    """ADR-3: an unreachable model yields UNCLEAR with a reason, never a crash and never COMPLIANT."""
    resp = ChatModelSeats(Failing()).judge(CHANGE, (JudgeCase(ADR, (OBL,)),), Context(post_images={}))
    assert resp.findings == () and resp.error.startswith("ConnectionError")


def test_the_compile_prompt_is_unchanged_by_the_move_so_the_cache_keys_still_hold():
    from adrcheck.chatmodel.prompts import PROMPT_VERSION, compile_request

    req = compile_request(ADR)
    assert req.system == "" and req.user.startswith("You compile an architecture decision record")
    assert PROMPT_VERSION == "2026-11-07.1"

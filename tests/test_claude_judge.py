"""The claude -p judge: prompts are built from obligations and the diff, replies are parsed strictly."""

import json

from adrcheck.adapters.claude_judge import ClaudeJudge, parse_compile_reply, parse_judge_reply
from adrcheck.domain.adr import Adr, Status
from adrcheck.domain.change import Change, FileChange, Line
from adrcheck.domain.obligation import Checkability, Obligation
from adrcheck.domain.verdict import Verdict
from adrcheck.ports import Context

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
    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def __call__(self, prompt, model):
        self.prompts.append(prompt)
        return {
            "result": self.reply,
            "usage": {"input_tokens": 10, "cache_read_input_tokens": 5, "output_tokens": 3},
            "total_cost_usd": 0.01,
            "duration_api_ms": 200,
        }


def test_judge_prompt_carries_the_obligations_the_diff_lines_and_the_post_image():
    run = Recorder(json.dumps({"relevant": True, "findings": []}))
    judge = ClaudeJudge(run=run, model="sonnet")
    judge.judge(CHANGE, ADR, (OBL,), Context(post_images={"enrich/store.py": "def save(): ..."}))
    [prompt] = run.prompts
    assert "ADR-2/1" in prompt and "keyed by store.row_key" in prompt
    assert '+ key = row["url"]' in prompt
    assert "def save(): ..." in prompt
    assert "Considered Options" not in prompt  # we never show the judge the roads not taken as if they bound


def test_judge_reply_is_parsed_into_findings_with_verdicts_and_token_counts():
    reply = json.dumps(
        {
            "relevant": True,
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
    judge = ClaudeJudge(run=Recorder(reply), model="sonnet")
    resp = judge.judge(CHANGE, ADR, (OBL,), Context(post_images={}))
    assert resp.relevant and resp.findings[0].verdict is Verdict.CONFLICT
    assert (resp.tokens_in, resp.tokens_out, resp.cost_usd, resp.latency_ms) == (15, 3, 0.01, 200)


def test_a_fenced_or_chatty_reply_still_parses():
    reply = 'Here you go:\n```json\n{"relevant": false, "findings": []}\n```\n'
    assert parse_judge_reply(reply).relevant is False


def test_an_unparseable_reply_is_an_error_not_a_verdict():
    resp = parse_judge_reply("I cannot help with that.")
    assert resp.relevant is True and resp.findings == () and resp.error.startswith("unparseable")


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
    assert o.mandates == ("store.row_key",)
    assert o.forbids == ("hashlib.",)  # kept for the report; classification no longer uses them

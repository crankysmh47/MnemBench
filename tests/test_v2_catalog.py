"""Smoke tests for MnemBench v2."""

from __future__ import annotations

from mnembench.runner import _extract_response_text
from mnembench.v2_scenarios import build_v2_scenarios


def test_v2_profile_sizes() -> None:
    assert len(build_v2_scenarios("smoke")) == 13
    assert len(build_v2_scenarios("standard")) == 65
    assert len(build_v2_scenarios("paper")) == 195


def test_v2_scenarios_have_probe_steps() -> None:
    scenarios = build_v2_scenarios("smoke")
    assert all(s.probe_steps for s in scenarios)
    assert {s.metadata["domain"] for s in scenarios} >= {
        "recall",
        "current_truth",
        "prospective",
        "poison",
    }


def test_extract_response_text_accepts_openai_style() -> None:
    payload = {"choices": [{"message": {"content": "hello from adapter"}}]}
    assert _extract_response_text(payload) == "hello from adapter"

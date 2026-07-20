"""Regression tests for MnemBench scoring."""

from __future__ import annotations

from mnembench.scenarios import CONTRADICTION_CHAIN
from mnembench.scoring import (
    compute_dimension_scores,
    score_contradiction_resolved,
)


# ---------------------------------------------------------------------------
# Unit: contradiction_resolved
# ---------------------------------------------------------------------------

def test_contradiction_resolved_has_new_not_old() -> None:
    """score=1.0 when response has new value and NOT the old value."""
    assert score_contradiction_resolved("We use Fastify now.", "Express", "Fastify") == 1.0


def test_contradiction_resolved_has_both() -> None:
    """score=0.5 when response contains both old and new values."""
    assert score_contradiction_resolved("We moved from Express to Fastify.", "Express", "Fastify") == 0.5


def test_contradiction_resolved_only_old() -> None:
    """score=0.0 when response only contains the old/stale value."""
    assert score_contradiction_resolved("We use Express.", "Express", "Fastify") == 0.0


def test_contradiction_resolved_neither() -> None:
    """score=0.0 when response mentions neither value."""
    assert score_contradiction_resolved("We use Koa.", "Express", "Fastify") == 0.0


# ---------------------------------------------------------------------------
# Regression: contradiction_score dimension must not be inverted
# ---------------------------------------------------------------------------

def test_contradiction_dimension_perfect_resolution() -> None:
    """A perfectly resolved contradiction contributes 1.0 to contradiction_score."""
    # Provide correct (new-value, not-old) responses for every step that has
    # a contradiction_resolved check: steps 4, 6, 8.
    responses: dict[int, str] = {s.step_index: "" for s in CONTRADICTION_CHAIN.steps}
    responses[4] = "We use Fastify now."
    responses[6] = "The team is using Koa now."
    responses[8] = "We are going with Hono."

    result = compute_dimension_scores(CONTRADICTION_CHAIN, responses)

    # Step 4 contradiction_resolved("Express|Fastify") → 1.0
    # Step 6 contradiction_resolved("Fastify|Koa")   → 1.0
    # Step 8 contradiction_resolved("Koa|Hono")      → 1.0
    # Mean = 1.0 (no inversion!).
    assert result["contradiction_score"] == 1.0, (
        f"Expected 1.0 for perfectly resolved contradictions, "
        f"got {result['contradiction_score']}"
    )


def test_contradiction_dimension_stale_value() -> None:
    """A response stuck on the stale value contributes 0.0 to contradiction_score."""
    # Respond with old/stale values for every step that has a
    # contradiction_resolved check: steps 4, 6, 8.
    responses: dict[int, str] = {s.step_index: "" for s in CONTRADICTION_CHAIN.steps}
    responses[4] = "We still use Express."
    responses[6] = "We still use Fastify actually."
    responses[8] = "Sticking with Koa."

    result = compute_dimension_scores(CONTRADICTION_CHAIN, responses)

    # Step 4 contradiction_resolved("Express|Fastify") → 0.0 (only old)
    # Step 6 contradiction_resolved("Fastify|Koa")   → 0.0 (only old)
    # Step 8 contradiction_resolved("Koa|Hono")      → 0.0 (only old)
    # Mean = 0.0
    assert result["contradiction_score"] == 0.0, (
        f"Expected 0.0 for stale-only responses, "
        f"got {result['contradiction_score']}"
    )

"""Regression tests for MnemBench scoring, focused on contradiction dimension.

Issue #1: compute_dimension_scores inverted the contradiction_score by applying
1.0 - mean(). A perfectly resolved contradiction (new value present, old value
absent) should yield contradiction_score=1.0, not 0.0.
"""

from __future__ import annotations

from mnembench.scenarios import CONTRADICTION_CHAIN
from mnembench.scoring import compute_dimension_scores


class TestContradictionDimension:
    """Regression tests for contradiction_score aggregation."""

    def _build_default_responses(self) -> dict[int, str]:
        """Build responses that satisfy keyword_present checks for all scored steps.

        Uses CONTRADICTION_CHAIN fixture probe responses that perfectly resolve
        each contradiction: each response contains only the latest value.
        """
        return {
            2: "We use Express for our API.",
            4: "We migrated to Fastify.",              # has Fastify, not Express
            6: "Our API framework is now Koa.",         # has Koa, not Fastify
            8: "We are using Hono for all new development.",  # has Hono, not Koa
        }

    # ------------------------------------------------------------------
    # Regression: the 1.0 - mean() inversion
    # ------------------------------------------------------------------

    def test_perfect_resolution_gives_1(self) -> None:
        """Perfect contradiction resolution → contradiction_score == 1.0."""
        responses = self._build_default_responses()
        result = compute_dimension_scores(CONTRADICTION_CHAIN, responses)
        # All 3 contradiction_resolved checks score 1.0
        assert result["contradiction_score"] == 1.0, (
            f"Expected 1.0, got {result['contradiction_score']}"
        )

    def test_all_stale_only_gives_0(self) -> None:
        """Responses containing only old values → contradiction_score == 0.0."""
        # Step 4 contradiction_resolved(Express|Fastify): mentions only Express → 0.0
        # Step 6 contradiction_resolved(Fastify|Koa): mentions only Express → 0.0
        # Step 8 contradiction_resolved(Koa|Hono): mentions only Express → 0.0
        # Mean = 0.0, should remain 0.0 (no inversion)
        responses = {
            2: "We use Express for our API.",
            4: "Express remains the best framework.",
            6: "I still think Express is the way to go.",
            8: "Express all the way.",
        }
        result = compute_dimension_scores(CONTRADICTION_CHAIN, responses)
        assert result["contradiction_score"] == 0.0, (
            f"Expected 0.0 for stale-only responses, got {result['contradiction_score']}"
        )

    def test_partial_resolution_gives_0_5(self) -> None:
        """Responses with both old and new values → contradiction_score == 0.5."""
        # Step 4 contradiction_resolved(Express|Fastify): has both → 0.5
        # Step 6 contradiction_resolved(Fastify|Koa): has both → 0.5
        # Step 8 contradiction_resolved(Koa|Hono): has both → 0.5
        # Mean = 0.5, should remain 0.5
        responses = {
            2: "We use Express for our API.",
            4: "We migrated from Express to Fastify.",
            6: "We moved from Fastify to Koa.",
            8: "We transitioned from Koa to Hono.",
        }
        result = compute_dimension_scores(CONTRADICTION_CHAIN, responses)
        assert result["contradiction_score"] == 0.5, (
            f"Expected 0.5 for mixed responses, got {result['contradiction_score']}"
        )



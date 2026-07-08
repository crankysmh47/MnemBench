"""MnemBench runner - orchestrates scenario execution against any memory-enabled API.

Supports any OpenAI-compatible chat endpoint. Auto-seeds memory via
/api/memory/store for teach steps. Collects per-step responses, latency,
and memory dumps for multi-dimensional scoring.
"""

from __future__ import annotations

import asyncio
import statistics
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from mnembench.fixtures import (
    get_fixture_latency,
    get_fixture_memory_dump,
    get_fixture_response,
    get_fixture_token_count,
)
from mnembench.scenarios import ALL_MNEMBENCH_SCENARIOS, MemorySeed, MnemBenchScenario, MnemBenchStep
from mnembench.scoring import compute_comparison_scores, score_mnembench_scenario


@dataclass
class MnemBenchStepResult:
    """Result of executing a single scenario step."""

    step_index: int
    phase: str
    response: str
    latency_ms: float
    memory_dump: str = ""
    token_count: int = 0
    error: str | None = None


@dataclass
class MnemBenchScenarioRun:
    """Result of running one scenario against one server."""

    scenario_id: str
    mode: str  # "with_memory" or "without_memory"
    step_results: dict[int, MnemBenchStepResult] = field(default_factory=dict)
    score_summary: dict = field(default_factory=dict)
    dimensions: dict = field(default_factory=dict)

    @property
    def average_probe_score(self) -> float:
        return self.score_summary.get("average_probe_score", 0.0)

    @property
    def composite_score(self) -> float:
        return self.score_summary.get("composite_score", 0.0)


@dataclass
class MnemBenchReport:
    """Full benchmark report for one mode."""

    mode: str
    runs: list[MnemBenchScenarioRun] = field(default_factory=list)

    @property
    def average_score(self) -> float:
        if not self.runs:
            return 0.0
        return statistics.mean(r.average_probe_score for r in self.runs)

    @property
    def average_composite(self) -> float:
        if not self.runs:
            return 0.0
        return statistics.mean(r.composite_score for r in self.runs)

    @property
    def pass_rate(self) -> float:
        if not self.runs:
            return 0.0
        passed = sum(1 for r in self.runs if r.score_summary.get("pass", False))
        return passed / len(self.runs)


@dataclass
class MnemBenchComparison:
    """Side-by-side comparison between with-memory and without-memory."""

    with_report: MnemBenchReport
    without_report: MnemBenchReport
    comparisons: dict[str, dict] = field(default_factory=dict)
    aggregate: dict = field(default_factory=dict)

    def build(self) -> MnemBenchComparison:
        """Compute per-scenario comparisons and aggregate metrics."""
        without_by_id = {r.scenario_id: r for r in self.without_report.runs}

        all_score_deltas: list[float] = []
        all_composite_deltas: list[float] = []
        dim_deltas_accum: dict[str, list[float]] = {}

        for with_run in self.with_report.runs:
            without_run = without_by_id.get(with_run.scenario_id)
            if without_run is None:
                continue

            comp = compute_comparison_scores(
                with_run.score_summary, without_run.score_summary
            )
            self.comparisons[with_run.scenario_id] = comp

            all_score_deltas.append(comp["score_delta"])
            all_composite_deltas.append(comp["composite_delta"])

            for dim, delta in comp.get("dimension_deltas", {}).items():
                if dim not in dim_deltas_accum:
                    dim_deltas_accum[dim] = []
                dim_deltas_accum[dim].append(delta)

        n = len(all_score_deltas) or 1
        avg_dim_deltas = {}
        for dim, deltas in dim_deltas_accum.items():
            avg_dim_deltas[dim] = round(sum(deltas) / len(deltas), 3)

        self.aggregate = {
            "with_avg_score": self.with_report.average_score,
            "without_avg_score": self.without_report.average_score,
            "with_avg_composite": self.with_report.average_composite,
            "without_avg_composite": self.without_report.average_composite,
            "with_pass_rate": self.with_report.pass_rate,
            "without_pass_rate": self.without_report.pass_rate,
            "avg_score_delta": round(
                statistics.mean(all_score_deltas) if all_score_deltas else 0.0, 3
            ),
            "avg_composite_delta": round(
                statistics.mean(all_composite_deltas) if all_composite_deltas else 0.0,
                3,
            ),
            "scenarios_improved": sum(1 for d in all_score_deltas if d > 0),
            "scenarios_total": len(all_score_deltas),
            "avg_dimension_deltas": avg_dim_deltas,
        }
        return self


class MnemBenchRunner:
    """Execute MnemBench scenarios against any OpenAI-compatible API.

    Args:
        server_url: Base URL for the memory-enabled server.
        mode: "with_memory" or "without_memory".
        dry_run: If True, use fixture responses instead of calling APIs.
        seed_memory: If True, pre-store teach-step facts via /api/memory/store.
        store_endpoint: API endpoint for memory storage (default: /api/memory/store).
        chat_endpoint: API endpoint for chat (default: /chat).
        memory_endpoint: API endpoint for memory dump (default: /api/memory/context).
        repeat: Number of times to repeat each scenario (for statistical significance).
    """

    def __init__(
        self,
        server_url: str,
        mode: str,
        dry_run: bool = False,
        seed_memory: bool = True,
        store_endpoint: str = "/api/memory/store",
        chat_endpoint: str = "/chat",
        memory_endpoint: str = "/api/memory/context",
        repeat: int = 1,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.mode = mode
        self.dry_run = dry_run
        self.seed_memory = seed_memory
        self.store_endpoint = store_endpoint
        self.chat_endpoint = chat_endpoint
        self.memory_endpoint = memory_endpoint
        self.repeat = repeat

    async def _store_memory_seed(
        self,
        client: httpx.AsyncClient,
        user_id: str,
        seed: MemorySeed,
    ) -> None:
        """Persist a teach-step fact via API."""
        await client.post(
            f"{self.server_url}{self.store_endpoint}",
            json={
                "user_id": user_id,
                "entity": seed.entity,
                "relation": seed.relation,
                "value": seed.value,
                "category": seed.category,
                "conviction": seed.conviction,
            },
        )

    async def _chat(
        self,
        client: httpx.AsyncClient,
        user_id: str,
        session_id: str,
        message: str,
    ) -> tuple[str, float]:
        """Send a chat message and return (response, latency_ms)."""
        start = time.monotonic()
        resp = await client.post(
            f"{self.server_url}{self.chat_endpoint}",
            json={
                "user_id": user_id,
                "session_id": session_id,
                "message": message,
            },
        )
        elapsed = (time.monotonic() - start) * 1000  # convert to ms
        return _extract_response_text(resp.json()), elapsed

    async def _fetch_memory_dump(
        self,
        client: httpx.AsyncClient,
        user_id: str,
        session_id: str,
    ) -> tuple[str, float]:
        """Fetch memory dump for a user."""
        return await self._chat(client, user_id, session_id, "/memory")

    async def _fetch_context(self, client: httpx.AsyncClient, user_id: str) -> str:
        """Fetch memory context for token count measurement."""
        try:
            resp = await client.get(
                f"{self.server_url}{self.memory_endpoint}",
                params={"user_id": user_id},
            )
            return resp.text
        except Exception:
            return ""

    async def run_scenario(self, scenario: MnemBenchScenario) -> MnemBenchScenarioRun:
        """Run all steps in one scenario sequentially.

        Returns:
            MnemBenchScenarioRun with step results and scores.
        """
        run_suffix = uuid.uuid4().hex[:8] if not self.dry_run else "dry"
        user_id = f"mnembench_{scenario.id}_{self.mode}_{run_suffix}"

        step_results: dict[int, MnemBenchStepResult] = {}
        memory_dumps: dict[int, str] = {}
        latencies: dict[int, float] = {}

        if self.dry_run:
            synthetic_dump = _build_synthetic_memory_dump(scenario, self.mode)
            for step in scenario.steps:
                response = get_fixture_response(scenario.id, step.step_index, self.mode)
                if scenario.metadata.get("suite") == "v2":
                    response = _build_synthetic_response(step, self.mode, response)
                latency = get_fixture_latency(scenario.id, step.step_index, self.mode)
                dump = get_fixture_memory_dump(scenario.id) or synthetic_dump

                if step.phase in ("probe", "contradict", "measure"):
                    memory_dumps[step.step_index] = dump

                step_result = MnemBenchStepResult(
                    step_index=step.step_index,
                    phase=step.phase,
                    response=response,
                    latency_ms=latency,
                    memory_dump=dump,
                )
                step_results[step.step_index] = step_result
                latencies[step.step_index] = latency
        else:
            async with httpx.AsyncClient(timeout=120.0) as client:
                for step in scenario.steps:
                    # Seed memory for teach steps
                    if (
                        self.seed_memory
                        and self.mode == "with_memory"
                        and step.memory_seed is not None
                    ):
                        await self._store_memory_seed(client, user_id, step.memory_seed)
                        await asyncio.sleep(0.3)

                    # Measure step for context window
                    if step.phase == "measure" and step.metadata.get("measure_type") == "context_size":
                        context_text = await self._fetch_context(client, user_id)
                        token_estimate = len(context_text.split())
                        step_result = MnemBenchStepResult(
                            step_index=step.step_index,
                            phase="measure",
                            response=context_text,
                            latency_ms=0.0,
                            token_count=token_estimate,
                        )
                        step_results[step.step_index] = step_result
                        continue

                    # Chat step
                    response, latency = await self._chat(
                        client, user_id, step.session_id, step.user_message
                    )
                    step_result = MnemBenchStepResult(
                        step_index=step.step_index,
                        phase=step.phase,
                        response=response,
                        latency_ms=latency,
                    )
                    step_results[step.step_index] = step_result
                    latencies[step.step_index] = latency

                    # Fetch memory dump after probe / contradict steps
                    if step.phase in ("probe", "contradict") and step.expectations:
                        await asyncio.sleep(1.0)
                        dump, _ = await self._fetch_memory_dump(client, user_id, step.session_id)
                        memory_dumps[step.step_index] = dump
                        step_result.memory_dump = dump

                    # Brief pause after teach/contradict steps for memory consolidation
                    if step.phase in ("teach", "contradict") and step.memory_seed:
                        await asyncio.sleep(0.5)

        # Score the scenario
        score_summary = score_mnembench_scenario(scenario, {
            idx: sr.response for idx, sr in step_results.items()
        }, memory_dumps, latencies)
        dimensions = score_summary.get("dimensions", {})

        return MnemBenchScenarioRun(
            scenario_id=scenario.id,
            mode=self.mode,
            step_results=step_results,
            score_summary=score_summary,
            dimensions=dimensions,
        )

    async def run_all(
        self,
        scenarios: list[MnemBenchScenario] | None = None,
        progress_callback: Any | None = None,
    ) -> MnemBenchReport:
        """Run all (or specified) scenarios, optionally repeating each.

        Args:
            scenarios: List of scenarios to run. Defaults to all.
            progress_callback: Optional async callback(scenario_id, run_index, total).

        Returns:
            MnemBenchReport with all runs.
        """
        scenarios = scenarios or ALL_MNEMBENCH_SCENARIOS
        report = MnemBenchReport(mode=self.mode)

        total_runs = len(scenarios) * self.repeat
        run_count = 0

        for scenario in scenarios:
            for rep in range(self.repeat):
                run_count += 1
                if progress_callback:
                    await progress_callback(scenario.id, rep + 1, self.repeat)

                run_result = await self.run_scenario(scenario)
                report.runs.append(run_result)

        return report


def _extract_response_text(payload: dict[str, Any]) -> str:
    """Parse common chat response envelopes."""

    for key in ("response", "answer", "content", "text"):
        value = payload.get(key)
        if isinstance(value, str):
            return value

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            if isinstance(first.get("text"), str):
                return first["text"]

    return ""


def _build_synthetic_memory_dump(scenario: MnemBenchScenario, mode: str) -> str:
    """Build a deterministic dry-run memory dump for generated scenarios."""

    if mode != "with_memory":
        return ""

    current: dict[tuple[str, str], MemorySeed] = {}
    for step in scenario.steps:
        if step.memory_seed is None:
            continue
        seed = step.memory_seed
        current[(seed.entity.lower(), seed.relation.lower())] = seed

    return "\n".join(
        f"{seed.entity} -> {seed.relation} -> {seed.value}"
        for seed in current.values()
    )


def _build_synthetic_response(step: MnemBenchStep, mode: str, fallback: str) -> str:
    """Create useful v2 dry-run responses from expectations."""

    if step.phase not in ("probe", "contradict"):
        return fallback

    if mode != "with_memory":
        return "I do not have enough stored memory to answer that reliably."

    present_terms: list[str] = []
    for check_type, check_value, _desc in step.expectations:
        if check_type == "keyword_present" and check_value:
            present_terms.append(check_value)
        elif check_type == "contradiction_resolved":
            parts = check_value.split("|", 1)
            if len(parts) == 2:
                present_terms.append(parts[1])
        elif check_type == "memory_state":
            parts = check_value.split("|", 1)
            if parts and parts[0]:
                present_terms.append(parts[0])

    if not present_terms:
        return "The relevant memory did not fire for this prompt."

    unique_terms = list(dict.fromkeys(present_terms))
    return "The relevant stored memory is: " + ", ".join(unique_terms) + "."

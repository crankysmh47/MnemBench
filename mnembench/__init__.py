"""MnemBench - persistent-memory agent benchmark.

A standalone benchmark suite for evaluating memory-augmented language model
agents. Supports any memory system with a compatible chat endpoint.
"""

from __future__ import annotations

from mnembench.scenarios import ALL_MNEMBENCH_SCENARIOS, MnemBenchScenario
from mnembench.v2_scenarios import build_v2_scenarios
from mnembench.runner import MnemBenchRunner
from mnembench.scoring import score_mnembench_scenario
from mnembench.cli import main

__version__ = "2.0.0"
__all__ = [
    "ALL_MNEMBENCH_SCENARIOS",
    "MnemBenchScenario",
    "MnemBenchRunner",
    "build_v2_scenarios",
    "score_mnembench_scenario",
    "main",
]

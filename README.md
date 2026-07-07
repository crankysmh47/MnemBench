# MnemBench

Long-running benchmark for memory-augmented agents.

MnemBench tests whether an agent memory system can remember useful facts, reject noise, resolve contradictions, avoid stale recall, and keep context usage bounded across multi-session workflows.

It is system-agnostic. If your product exposes an OpenAI-style chat endpoint, you can run MnemBench against it. If your product also exposes a memory seeding endpoint, MnemBench can pre-load scenario facts before probe turns.

## Table of contents

- [Install](#install)
- [Quick start](#quick-start)
- [What it measures](#what-it-measures)
- [Endpoint contract](#endpoint-contract)
- [Scenarios](#scenarios)
- [CLI reference](#cli-reference)
- [Reports](#reports)
- [Examples](#examples)
- [Development](#development)
- [License](#license)

## Install

Clone the repository:

```bash
git clone https://github.com/crankysmh47/MnemBench.git
cd MnemBench
```

Install in editable mode:

```bash
python -m pip install -e .
```

Python 3.10+ is required.

## Quick start

List scenarios:

```bash
mnembench --list
```

Run without making API calls:

```bash
mnembench --dry-run
```

Run against a memory-enabled candidate server:

```bash
mnembench --server http://localhost:8000 --no-baseline
```

Run candidate versus baseline:

```bash
mnembench --server http://localhost:8000 --baseline http://localhost:8002
```

Write a compact judge-facing report:

```bash
mnembench --server http://localhost:8000 --baseline http://localhost:8002 --judge-report
```

Reports are written to `reports/` by default.

## What it measures

| Dimension | What it checks |
|-----------|----------------|
| Cross-session recall | Facts taught in earlier sessions are recalled later |
| Contradiction handling | New values replace stale values |
| Salience gating | Definitive facts are stored; hedged noise is rejected |
| Interference prevention | Stale or irrelevant facts do not leak into answers |
| Dormant recall | Older useful facts can resurface after distraction |
| Overload resistance | Important facts survive many distractors |
| Multi-hop association | Connected facts can be used together |
| Temporal decay | Old facts can fade while recent facts persist |
| Context efficiency | Memory injection stays bounded as memory grows |
| User isolation | One user's memories do not leak into another user's answers |

## Endpoint contract

MnemBench expects a candidate chat server.

### Required chat endpoint

Default endpoint:

```text
POST <server>/chat
```

Expected request shape:

```json
{
  "user_id": "bench-user-123",
  "session_id": "scenario-session-1",
  "message": "Remember that my backend framework is FastAPI."
}
```

Expected response shape:

```json
{
  "response": "Got it. Your backend framework is FastAPI."
}
```

MnemBench accepts common alternatives such as `answer`, `content`, or OpenAI-style `choices[0].message.content` when parsing responses.

### Optional memory seed endpoint

If available, MnemBench can seed facts directly:

```text
POST <server>/api/memory/store
```

Expected request shape:

```json
{
  "user_id": "bench-user-123",
  "entity": "backend",
  "relation": "framework",
  "value": "FastAPI",
  "category": "preference",
  "conviction": 1.0
}
```

If your system does not expose direct memory storage, run with:

```bash
mnembench --server http://localhost:8000 --no-seed-memory
```

## Scenarios

| ID | Purpose |
|----|---------|
| `ten_session_recall` | Recall 10 facts spread across 10 sessions |
| `contradiction_chain` | Track repeated updates to the same entity |
| `salience_gate` | Store clear facts and reject low-conviction statements |
| `interference_gauntlet` | Avoid leaking stale facts after updates |
| `dormant_resurrection` | Recall an older fact after many distractors |
| `overload_resistance` | Preserve important facts under memory pressure |
| `multi_hop_association` | Use linked facts together |
| `temporal_decay` | Handle old versus recent facts |
| `context_window_efficiency` | Keep injected memory bounded |
| `cross_user_isolation` | Prevent cross-user leakage |

Run one scenario:

```bash
mnembench --scenario contradiction_chain --dry-run
```

Repeat a scenario:

```bash
mnembench --scenario ten_session_recall --repeat 3 --server http://localhost:8000
```

## CLI reference

```text
mnembench [options]

--server URL          Candidate memory server. Default: http://localhost:8000
--baseline URL        Baseline server without memory. Default: http://localhost:8002
--scenario ID ...     Scenario IDs to run. Default: all
--output-dir PATH     Report output directory. Default: reports
--repeat N            Repeat each scenario N times
--dry-run             Use fixture responses; no API calls
--no-baseline         Skip baseline comparison
--no-seed-memory      Do not call /api/memory/store
--judge-report        Also write a compact Markdown summary
--list                List scenarios
--version             Print version
```

## Reports

Each run writes a Markdown report, a JSON report, and optionally a compact judge summary.

Comparison reports include candidate score, baseline score, score delta, composite delta, pass rate, per-scenario scores, and latency.

## Examples

See `examples/openai_compatible_adapter.py` for a minimal FastAPI adapter that exposes the endpoint shape MnemBench expects.

## Development

Run dry-run smoke tests:

```bash
python -m mnembench --dry-run --scenario contradiction_chain --judge-report
```

Run the package directly from source:

```bash
python -m pip install -e .
python -m mnembench --list
```

## License

MIT. See [LICENSE](LICENSE).

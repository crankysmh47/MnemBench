# MnemBench

Research-scale benchmark for persistent-memory agents.

MnemBench tests whether an agent can accumulate experience across sessions, remember the current truth, reject noisy memory writes, avoid stale recall, preserve user isolation, and keep injected context bounded as memory grows. It is system-agnostic: any product with a compatible chat endpoint can be evaluated.

## Why v2 Exists

Most memory demos prove one pleasant case: teach a fact, open a new chat, ask for the fact. That is necessary, but too easy. Real memory systems fail through interference, stale recall, over-storage, user identity drift, and unbounded context injection.

MnemBench v2 turns those failure modes into a larger generated benchmark:

| Profile | Scenarios | Use |
|---------|----------:|-----|
| `smoke` | 13 | CI and quick adapter checks |
| `standard` | 65 | Product comparisons and demos |
| `paper` | 195 | Long-running, research-style evaluation |

The original 10 hand-authored scenarios remain available as `--suite v1`.

## Install

```bash
git clone https://github.com/crankysmh47/MnemBench.git
cd MnemBench
python -m pip install -e .
```

Python 3.10+ is required.

## Quick Start

List the v2 smoke catalog:

```bash
mnembench --suite v2 --profile smoke --list
```

Run without API calls:

```bash
mnembench --suite v2 --profile smoke --dry-run --no-baseline
```

Run a standard candidate-vs-baseline comparison:

```bash
mnembench --suite v2 --profile standard \
  --server http://localhost:8000 \
  --baseline http://localhost:8002 \
  --judge-report
```

Run the long paper profile:

```bash
mnembench --suite v2 --profile paper \
  --server http://localhost:8000 \
  --baseline http://localhost:8002 \
  --repeat 3
```

Reports are written to `reports/` by default.

## What It Measures

| Domain | What It Catches |
|--------|-----------------|
| Cross-session recall | Facts taught in earlier sessions are recalled later |
| Current truth tracking | Updated facts replace stale values |
| Salience boundary | Certain facts are stored, hedged noise is rejected |
| Interference suppression | Nearby stale facts do not leak into answers |
| Overload resistance | Critical facts survive many distractors |
| Dormant resurfacing | Old but relevant facts can return when cued |
| Associative multi-hop | Linked facts compose into useful answers |
| Context budget | Injected memory stays bounded as stored facts grow |
| User identity continuity | New sessions keep the same user namespace |
| Proper noun grounding | Arbitrary codenames and IDs are remembered exactly |
| Memory poison resistance | Prompt-injected memory rewrites fail |
| Feedback learning | Repeatedly useful facts become easier to retrieve |
| Cue-triggered prospective memory | Intentions fire on cue, not merely with time |

## Endpoint Contract

MnemBench expects a candidate chat server.

### Required Chat Endpoint

```text
POST <server>/chat
```

Request:

```json
{
  "user_id": "bench-user-123",
  "session_id": "scenario-session-1",
  "message": "Remember that my backend framework is FastAPI."
}
```

Accepted response shapes:

```json
{ "response": "Got it." }
```

```json
{ "answer": "Got it." }
```

```json
{
  "choices": [
    { "message": { "content": "Got it." } }
  ]
}
```

### Optional Memory Seed Endpoint

If available, MnemBench can seed deterministic facts directly:

```text
POST <server>/api/memory/store
```

Request:

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

If your system does not expose direct memory storage, run:

```bash
mnembench --suite v2 --profile smoke --server http://localhost:8000 --no-seed-memory
```

## CLI Reference

```text
mnembench [options]

--suite v1|v2        Benchmark suite. Default: v1
--profile NAME       V2 size: smoke, standard, paper
--server URL         Candidate memory server. Default: http://localhost:8000
--baseline URL       Baseline server without memory. Default: http://localhost:8002
--scenario ID ...    Scenario IDs to run. Default: all
--output-dir PATH    Report output directory. Default: reports
--repeat N           Repeat each scenario N times
--dry-run            Use fixture/synthetic responses; no API calls
--no-baseline        Skip baseline comparison
--no-seed-memory     Do not call /api/memory/store
--judge-report       Also write a compact Markdown summary
--list               List scenarios
--version            Print version
```

## Reports

Each run writes:

- Markdown report for human review
- JSON report for programmatic analysis
- Optional judge-facing summary with `--judge-report`

Comparison reports include candidate score, baseline score, score delta, composite delta, pass rate, per-scenario scores, latency, and dimension-level deltas.

## Examples

See `examples/openai_compatible_adapter.py` for a minimal adapter that exposes the endpoint shape MnemBench expects.

## Development

```bash
python -m pip install -e .
python -m mnembench --suite v2 --profile smoke --dry-run --no-baseline --judge-report
python -m mnembench --suite v1 --dry-run --scenario contradiction_chain
```

## License

MIT. See [LICENSE](LICENSE).

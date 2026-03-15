# Quick Start

## Installation

```bash
pip install agentra
```

## 1. Initialize agentra

```python
import agentra
agentra.init()  # Enables SQLite persistence and SDK cost tracking
```

## 2. Red team your chatbot

```python
def my_chatbot(prompt: str) -> str:
    """My AI assistant."""
    return call_your_llm(prompt)

report = agentra.red_team(
    my_chatbot,
    plugins=["jailbreak", "pii", "harmful"],
    n_attacks=10,
)
report.summary()
```

## 3. Attack heatmap across models

```python
fp = agentra.guard.fingerprint({
    "gpt-4o-mini": gpt_fn,
    "claude-haiku": claude_fn,
})
fp.heatmap()
```

## 4. Auto-generate test cases

```python
ds = agentra.auto_dataset(my_chatbot, n=20, focus="adversarial")
print(f"Generated {len(ds)} test cases")
```

## 5. Evaluate quality

```python
ds = agentra.dataset("qa")
ds.add(input="What is 2+2?", expected_output="4")

exp = agentra.experiment("math-test", dataset=ds, fn=my_chatbot,
                          scorers=[agentra.scorers.exact_match])
exp.run().summary()
```

## 6. Launch dashboard

```bash
agentra serve
# Opens http://localhost:7234
```

## v0.4.0 quick examples

### Benchmark latency (p50/p95/p99)

```python
result = agentra.benchmark_latency(my_chatbot, n=100)
print(f"p50={result.p50_ms}ms  p95={result.p95_ms}ms  p99={result.p99_ms}ms")
```

### Scan multi-turn conversations

```python
report = agentra.scan_conversation(
    my_chatbot,
    attacks=["jailbreak", "pii"],
    turns=5,
    n_attacks=10,
)
report.summary()
```

### DSL-based webhook alerting

```python
from agentra.monitor import AlertManager

alerts = AlertManager(webhook="https://hooks.slack.com/...")
alerts.on("vulnerability_rate > 0.10", severity="high")
alerts.on("cost_usd > 1.00", severity="medium")
alerts.watch(my_chatbot, interval_seconds=300)
```

## CLI quick reference

```bash
agentra scan myapp:chatbot                           # Red team
agentra scan myapp:chatbot --fast                    # Quick scan (5 attacks per plugin)
agentra scan myapp:chatbot --git-compare main        # With regression check
agentra fingerprint myapp:gpt_fn myapp:claude_fn     # Attack heatmap
agentra auto-dataset myapp:chatbot --n 50            # Generate test cases
agentra serve                                        # Dashboard
agentra history                                      # Past scans
agentra costs --days 7                               # Cost summary
```

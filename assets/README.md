# Brand assets — TSLIT-DSPy

## Design principles

1. **One idea** — time-shift (two clocks out of phase)
2. **Few strokes** — rings + hands only
3. **High contrast** — white on black (or `currentColor` mono)
4. **No ornament** — no neural nets, shields, wordmarks, or gradients in the mark
5. **Reads at 16px**

## Files

| File | Use |
|------|-----|
| **`tslit-dspy-icon.svg`** | App / GitHub tile — white dual clocks on black rounded square |
| **`tslit-dspy-icon-mono.svg`** | Inline mark using `currentColor` (inherits text color) |

| Element | Meaning |
|---------|---------|
| Left full-opacity clock | Baseline / neutral probe time |
| Right ghosted, offset clock | Shifted probe time |
| Different hand angles | Behavior can change with time |

## README usage

```markdown
<p align="center">
  <img src="assets/tslit-dspy-icon.svg" alt="TSLIT-DSPy" width="96">
</p>
```

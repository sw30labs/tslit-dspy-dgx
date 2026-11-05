# Architecture Decision Records

Retrospective ADRs for `sw30labs/tslit-dspy-dgx`, written 2026-11-05 from main at `862b002`. Inferred reasons are labelled; open questions are in [../assumptions.md](../assumptions.md).

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-detector-target-model-origin-split.md) | Separate detector stack from scan target by model origin | Accepted (retrospective, inferred 2026-11-05) |
| [0002](0002-ollama-only-local-serving.md) | Serve all models through local Ollama only | Accepted (retrospective, inferred 2026-11-05) |
| [0003](0003-dspy-four-stage-analyzer.md) | Four-stage DSPy ChainOfThought analyzer with hard grounding checks | Accepted (retrospective, inferred 2026-11-05) |
| [0004](0004-json-adapter-without-format-json.md) | Custom JSON adapter that drops Ollama format=json and keeps detector thinking off | Accepted (retrospective, inferred 2026-11-05) |
| [0005](0005-composite-metric-weights.md) | Composite MIPROv2 metric 0.50/0.20/0.20/0.10 | Accepted (retrospective, inferred 2026-11-05) |
| [0006](0006-virtual-clock-time-hygiene.md) | Virtual clock in system message with pre-flight hygiene, canaries and no tools | Accepted (retrospective, inferred 2026-11-05) |
| [0007](0007-thinking-off-one-shot-scope.md) | Live probes are one-shot, tools-none, target thinking off (agreed scope) | Accepted (retrospective, inferred 2026-11-05) |
| [0008](0008-campaign-catalogue.md) | Fixed campaign catalogue (mini, plus, sharp, jwt2x2, lang2x2, full) | Accepted (retrospective, inferred 2026-11-05) |
| [0009](0009-pairwise-triage.md) | Pairwise sibling triage before Muse analysis | Accepted (retrospective, inferred 2026-11-05) |
| [0010](0010-data-splits-and-hash-guards.md) | Frozen cartoon exam, hash-guarded live holdout, curated compile mix | Accepted (retrospective, inferred 2026-11-05) |
| [0011](0011-named-compiled-artifacts-and-promotion.md) | Named compiled detector JSONs with manual promotion; Muse-light active | Accepted (retrospective, inferred 2026-11-05) |
| [0012](0012-fail-open-to-none.md) | Analysis errors resolve to `none` so campaigns keep moving | Accepted (retrospective, inferred 2026-11-05) |
| [0013](0013-withdraw-autoresearch-loop.md) | Withdraw the Karpathy overnight autoresearch loop | Accepted (retrospective, inferred 2026-11-05) |
| [0014](0014-docs-consolidation-and-whitepapers.md) | Docs consolidated into README, PAPER, SECURITY; versioned whitepapers in-tree | Accepted (retrospective, inferred 2026-11-05) |
| [0015](0015-pinned-dependencies-vulnops.md) | Exact dependency pins maintained by VulnOps | Accepted (retrospective, inferred 2026-11-05) |

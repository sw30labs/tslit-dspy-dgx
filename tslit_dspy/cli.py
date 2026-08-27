#!/usr/bin/env python3
"""CLI for TSLIT-DSPy on NVIDIA DGX Spark (Ollama-only local serving)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def cmd_doctor(_: argparse.Namespace) -> int:
    from tslit_dspy.lm import health_check_ollama, host_preflight, ollama_settings
    from tslit_dspy.model_policy import (
        DEFAULT_DETECTION_MODEL,
        describe_policy,
        is_allowed_detection_model,
        strip_ollama_prefix,
    )

    print("TSLIT-DSPy DGX doctor")
    print("=====================")
    findings = host_preflight()
    if findings:
        print("Host findings:")
        for f in findings:
            print(f"  ! {f}")
    else:
        print("Host: OK (Linux / GPU tools present)")

    cfg = ollama_settings()
    configured = strip_ollama_prefix(cfg["model"])
    print(f"\nConfigured detection model: {configured}")
    print(f"OLLAMA_BASE_URL:            {cfg['base_url']}")
    if not is_allowed_detection_model(configured):
        print("  ERROR: configured OLLAMA_MODEL is NOT allowed for the detection stack")
        print(f"  Use: {DEFAULT_DETECTION_MODEL}")
        return 1
    print("  origin policy: ALLOWED for detection")

    health = health_check_ollama()
    print(f"\nOllama health @ {health['base_url']}:")
    if health["ok"]:
        print("  reachable: yes")
        print(f"  served models: {health['models'] or '(none)'}")
        if health["detection_allowed"]:
            print(f"  detection-allowed: {health['detection_allowed']}")
        if health["detection_blocked"]:
            print(
                "  detection-blocked (scan targets only): "
                f"{health['detection_blocked']}"
            )
        if configured not in health["models"] and health["models"]:
            print(
                f"  WARN: configured model {configured!r} not in Ollama catalog — "
                f"ollama pull {configured}"
            )
    else:
        print(f"  reachable: no ({health['error']})")
        print("  Start: ollama serve")

    data = PROJECT_ROOT / "workspace" / "data"
    for name in (
        "train.jsonl",
        "dev.jsonl",
        "test.jsonl",
        "train_live_qwen.jsonl",
        "live_holdout.jsonl",
        "synthetic_long.jsonl",
        "train_augmented.jsonl",
    ):
        p = data / name
        status = "OK" if p.is_file() else "MISSING"
        print(f"  data {name}: {status}")
    hold_hash = PROJECT_ROOT / "workspace" / ".live_holdout_hash"
    print(f"  live_holdout hash: {'OK' if hold_hash.is_file() else 'MISSING'}")

    compiled_dir = PROJECT_ROOT / "workspace" / "compiled"
    for name, label in (
        ("tslit_analyzer_optimized.json", "active detective"),
        ("tslit_analyzer_optimized.muse-light.json", "Muse-light named"),
        ("tslit_analyzer_optimized.claude-era.json", "Claude-era backup"),
    ):
        p = compiled_dir / name
        print(f"  compiled {label}: {'OK' if p.is_file() else 'MISSING'} ({name})")

    print("\n" + describe_policy())
    return 0


def cmd_policy(_: argparse.Namespace) -> int:
    from tslit_dspy.model_policy import describe_policy

    print(describe_policy())
    return 0


def cmd_test_ollama(args: argparse.Namespace) -> int:
    from tslit_dspy.lm import health_check_ollama, make_lm, ollama_settings
    from tslit_dspy.model_policy import assert_detection_model

    health = health_check_ollama()
    print(json.dumps(health, indent=2))
    if not health["ok"]:
        print("Ollama not reachable — start with: ollama serve", file=sys.stderr)
        return 1
    cfg = ollama_settings()
    try:
        assert_detection_model(cfg["model"], role="detection")
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    if args.skip_invoke:
        return 0

    import dspy

    lm = make_lm("ollama", role="inference")
    dspy.configure(lm=lm)
    try:
        pred = lm("Reply with exactly: TSLIT_OK")
        print("invoke result:", pred if isinstance(pred, str) else pred)
    except Exception as exc:  # noqa: BLE001
        print(f"invoke failed: {exc}", file=sys.stderr)
        return 1
    return 0


def cmd_evaluate(args: argparse.Namespace) -> int:
    from tslit_dspy.evaluate import run_evaluation

    root = PROJECT_ROOT
    test = Path(args.test or root / "workspace" / "data" / "dev.jsonl")
    out = Path(args.output or root / "workspace" / "evaluation" / "dgx_eval.md")
    compiled = Path(args.compiled) if args.compiled else None
    if args.compiled is None and args.use_compiled:
        default_c = root / "workspace" / "compiled" / "tslit_analyzer_optimized.json"
        if default_c.is_file():
            compiled = default_c
    run_evaluation(
        test_path=test,
        output_path=out,
        model=args.model,
        model_base_url=args.model_base_url or "",
        compiled_path=compiled,
        title=args.title,
    )
    print(f"Report: {out}")
    return 0


def _experiment_config() -> dict:
    path = PROJECT_ROOT / "config" / "experiment_config.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def cmd_optimize(args: argparse.Namespace) -> int:
    from tslit_dspy.optimize import run_optimization

    root = PROJECT_ROOT
    cfg = _experiment_config()
    td = cfg.get("training_data") or {}
    mipro = cfg.get("mipro") or {}
    if args.train:
        train_path = Path(args.train)
    elif td.get("use_augmented"):
        train_path = root / td.get("augmented_path", "workspace/data/train_augmented.jsonl")
        if not train_path.is_file():
            print(f"[optimize] augmented mix missing at {train_path} — falling back to train.jsonl")
            train_path = root / "workspace" / "data" / "train.jsonl"
    else:
        train_path = root / "workspace" / "data" / "train.jsonl"
    labeled = args.max_labeled_demos
    if labeled is None:
        labeled = int(mipro.get("max_labeled_demos", 12))
    print(f"[optimize] train={train_path} max_labeled_demos={labeled}")
    run_optimization(
        train_path=train_path,
        dev_path=Path(args.dev or root / "workspace" / "data" / "dev.jsonl"),
        output_path=Path(
            args.output
            or root / "workspace" / "compiled" / "tslit_analyzer_optimized.muse-light.json"
        ),
        compile_model=args.compile_model,
        auto=args.auto,
        num_threads=args.num_threads,
        max_bootstrapped_demos=args.max_bootstrapped_demos,
        max_labeled_demos=labeled,
        num_trials=args.num_trials,
        num_candidates=args.num_candidates,
        val_size=args.val_size,
    )
    return 0


def cmd_experiment(args: argparse.Namespace) -> int:
    import subprocess

    script = PROJECT_ROOT / "scripts" / "run_experiment.sh"
    cmd = ["bash", str(script)]
    if args.mini:
        cmd.append("--mini")
    return subprocess.call(cmd, cwd=str(PROJECT_ROOT))


def cmd_scan(args: argparse.Namespace) -> int:
    """Probe a target model (e.g. Qwen) then optionally analyze with Muse Glimmer."""
    import logging

    from tslit_dspy.lm import ollama_settings
    from tslit_dspy.model_policy import DEFAULT_TARGET_MODEL
    from tslit_dspy.probe_campaign import (
        analyze_artifacts,
        load_existing_probe_ids,
        run_probe_campaign,
        save_campaign,
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    root = PROJECT_ROOT
    artifacts = Path(args.artifacts or root / "workspace" / "scans" / "qwen_live")
    phase = args.phase
    target = args.target_model or DEFAULT_TARGET_MODEL
    cfg = ollama_settings()
    base = args.base_url or cfg["openai_base_url"]

    if phase in {"probe", "all"}:
        dump_dir = artifacts / "request_dumps"
        skip_ids = set()
        if args.skip_existing:
            skip_ids = load_existing_probe_ids(artifacts)
        print(f"[scan] PROBE target={target} base={base} campaign={args.campaign}")
        print(
            "[scan] time-shift controls: system virtual clock, tools=none, "
            f"dump={dump_dir}, canaries={not args.no_canary}, "
            f"strict_hygiene={not args.no_strict_hygiene}, "
            f"skip_existing={len(skip_ids)}"
        )
        result = run_probe_campaign(
            base_url=base,
            model=target,
            api_key=cfg["api_key"],
            max_tokens=args.max_tokens,
            limit=args.limit,
            include_canaries=not args.no_canary,
            dump_dir=dump_dir,
            strict_hygiene=not args.no_strict_hygiene,
            fetch_rendered=args.fetch_rendered,
            campaign=args.campaign,
            skip_ids=skip_ids or None,
            disable_thinking=not args.thinking,
        )
        if not result.records:
            print("[scan] nothing to probe (empty campaign or all probe_ids already on disk)")
        else:
            ndjson = save_campaign(result, artifacts)
            print(f"[scan] probes saved → {ndjson} ({len(result.records)} records)")
        print(f"[scan] request dumps → {dump_dir}")
        if result.canary_summary:
            print(
                f"[scan] canaries: {result.canary_summary.get('n_canaries', 0)} "
                f"real_calendar_leaks={result.canary_summary.get('real_calendar_leaks', 0)}"
            )
            for c in result.canary_summary.get("results") or []:
                print(
                    f"  canary {c.get('probe_id')}: {c.get('status')} "
                    f"→ {c.get('response_text', '')[:80]!r}"
                )
        refusals = sum(
            1
            for r in result.records
            if any("refusal" in f or "gatekeeping" in f for f in r.get("detector_flags", []))
        )
        print(f"[scan] heuristic flags with refusal/gatekeeping: {refusals}/{len(result.records)}")

    if phase in {"analyze", "all"}:
        compiled = Path(
            args.compiled
            or root / "workspace" / "compiled" / "tslit_analyzer_optimized.json"
        )
        if not compiled.is_file():
            compiled = None
            print("[scan] no compiled artifact — zero-shot detector")
        print(f"[scan] ANALYZE artifacts={artifacts} detector={args.detector_model}")
        summary = analyze_artifacts(
            artifacts,
            compiled_path=compiled,
            detector_model=args.detector_model,
            output_path=artifacts / "analysis_report.md",
            model_names=[target],
        )
        print(json.dumps(summary, indent=2))
        print(f"[scan] report → {summary.get('output')}")

    return 0


def cmd_smoke(args: argparse.Namespace) -> int:
    """Offline smoke: load data + modules without GPU."""
    from tslit_dspy.metrics import tslit_metric
    from tslit_dspy.modules import TSLITAnalyzer
    from tslit_dspy.model_policy import assert_detection_model, is_adversary_origin
    from tslit_dspy.schemas import AnalysisResult

    assert_detection_model("muse-glimmer:30b-bf16")
    assert_detection_model("ollama_chat/llama3.1")
    assert is_adversary_origin("qwen3.8:27b-mtp-bf16")
    try:
        assert_detection_model("qwen3.8:27b-mtp-bf16")
        print("FAIL: Qwen should be blocked", file=sys.stderr)
        return 1
    except ValueError:
        pass

    train = PROJECT_ROOT / "workspace" / "data" / "train.jsonl"
    n = sum(1 for line in train.open() if line.strip())
    print(f"train examples: {n}")
    print(f"TSLITAnalyzer import: {TSLITAnalyzer}")
    print(f"metric: {tslit_metric}")
    print(f"schema: {AnalysisResult}")
    compiled = PROJECT_ROOT / "workspace" / "compiled" / "tslit_analyzer_optimized.json"
    if compiled.is_file():
        a = TSLITAnalyzer()
        a.load(str(compiled))
        print(f"compiled artifact load: OK ({compiled.name})")
    print("smoke: OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tslit",
        description="TSLIT-DSPy on NVIDIA DGX Spark — Ollama serving, non-adversary detection",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Host + Ollama + policy health")
    sub.add_parser("policy", help="Print model-origin policy")

    t = sub.add_parser("test-ollama", help="Catalog (+ optional invoke) against local Ollama")
    t.add_argument("--skip-invoke", action="store_true")

    e = sub.add_parser("evaluate", help="Run detector eval on JSONL")
    e.add_argument("--test", default=None)
    e.add_argument("--output", default=None)
    e.add_argument("--model", default="ollama")
    e.add_argument("--model-base-url", default="")
    e.add_argument("--compiled", default=None)
    e.add_argument("--use-compiled", action="store_true")
    e.add_argument("--title", default="TSLIT-DSPy DGX Evaluation")

    o = sub.add_parser("optimize", help="MIPROv2 compile (expensive)")
    o.add_argument("--train", default=None)
    o.add_argument("--dev", default=None)
    o.add_argument("--output", default=None)
    o.add_argument("--compile-model", default="ollama")
    o.add_argument("--auto", default="light", choices=["light", "medium", "heavy"])
    o.add_argument("--num-threads", type=int, default=2)
    o.add_argument("--max-bootstrapped-demos", type=int, default=2)
    o.add_argument(
        "--max-labeled-demos",
        type=int,
        default=None,
        help="Labeled demos per module (default: experiment_config mipro.max_labeled_demos)",
    )
    o.add_argument(
        "--num-trials",
        type=int,
        default=None,
        help="If set, ignore --auto and run this many Optuna trials",
    )
    o.add_argument("--num-candidates", type=int, default=None)
    o.add_argument(
        "--val-size",
        type=int,
        default=None,
        help="Stratified valset size drawn from train (default 16 with --num-trials)",
    )

    x = sub.add_parser("experiment", help="scripts/run_experiment.sh wrapper")
    x.add_argument("--mini", action="store_true")

    s = sub.add_parser(
        "scan",
        help="Live probe campaign against a target (Qwen) + analyze with non-adversary detector",
    )
    s.add_argument(
        "--phase",
        choices=["probe", "analyze", "all"],
        default="probe",
        help="probe=target only; analyze=detector only; all=both (same Ollama server)",
    )
    s.add_argument(
        "--target-model",
        default=None,
        help="Target Ollama tag (default: qwen3.8:27b-mtp-bf16)",
    )
    s.add_argument(
        "--detector-model",
        default="ollama",
        help="Detection LM tag/alias (must pass non-adversary policy; default OLLAMA_MODEL)",
    )
    s.add_argument("--base-url", default=None, help="Ollama OpenAI base (default: …:11434/v1)")
    s.add_argument("--artifacts", default=None)
    s.add_argument("--compiled", default=None)
    s.add_argument(
        "--campaign",
        default="mini",
        choices=["mini", "plus", "sharp", "jwt2x2"],
        help="mini=14; plus=old TSLIT leftover; sharp=clock-native; jwt2x2=four jwt_time cells",
    )
    s.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip probe_ids already present under --artifacts (increment in place)",
    )
    s.add_argument("--limit", type=int, default=None, help="Cap number of probes (debug)")
    s.add_argument("--max-tokens", type=int, default=2048)
    s.add_argument(
        "--thinking",
        action="store_true",
        help="Enable target chain-of-thought (default off; agreed scope is thinking-off)",
    )
    s.add_argument(
        "--no-canary",
        action="store_true",
        help="Skip date canary probes (What is today's date?)",
    )
    s.add_argument(
        "--no-strict-hygiene",
        action="store_true",
        help="Log hygiene violations but do not abort the campaign",
    )
    s.add_argument(
        "--fetch-rendered",
        action="store_true",
        help="Try POST /tokenize (vLLM leftover; Ollama does not expose this)",
    )

    sub.add_parser("smoke", help="Offline import + policy checks (no GPU)")
    return p


def main(argv: list[str] | None = None) -> int:
    _load_env()
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "doctor": cmd_doctor,
        "policy": cmd_policy,
        "test-ollama": cmd_test_ollama,
        "evaluate": cmd_evaluate,
        "optimize": cmd_optimize,
        "experiment": cmd_experiment,
        "scan": cmd_scan,
        "smoke": cmd_smoke,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())

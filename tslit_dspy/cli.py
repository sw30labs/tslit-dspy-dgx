#!/usr/bin/env python3
"""CLI for TSLIT-DSPy on NVIDIA DGX Spark."""

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
    from tslit_dspy.lm import health_check_vllm, host_preflight, vllm_settings
    from tslit_dspy.model_policy import (
        DEFAULT_DETECTION_MODEL,
        describe_policy,
        is_allowed_detection_model,
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

    cfg = vllm_settings()
    print(f"\nConfigured detection model: {cfg['model']}")
    print(f"VLLM_BASE_URL:              {cfg['base_url']}")
    if not is_allowed_detection_model(cfg["model"]):
        print("  ERROR: configured VLLM_MODEL is NOT allowed for the detection stack")
        print(f"  Use: {DEFAULT_DETECTION_MODEL}")
        print("  Start: ~/Desktop/start-vllm.sh nemotron-super")
        return 1
    print("  origin policy: ALLOWED for detection")

    health = health_check_vllm()
    print(f"\nvLLM health @ {health['base_url']}:")
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
        if cfg["model"] not in health["models"] and health["models"]:
            print(
                f"  WARN: configured model {cfg['model']!r} not in /v1/models — "
                "set VLLM_MODEL to a served id or restart vLLM with nemotron-super"
            )
    else:
        print(f"  reachable: no ({health['error']})")
        print("  Start detection LM: ~/Desktop/start-vllm.sh nemotron-super")

    data = PROJECT_ROOT / "workspace" / "data"
    for name in ("train.jsonl", "dev.jsonl", "test.jsonl"):
        p = data / name
        status = "OK" if p.is_file() else "MISSING"
        print(f"  data {name}: {status}")

    compiled = PROJECT_ROOT / "workspace" / "compiled" / "tslit_analyzer_optimized.json"
    print(f"  compiled artifact: {'OK' if compiled.is_file() else 'missing (run optimize)'}")

    print("\n" + describe_policy())
    return 0 if not findings else 0  # host arch warnings non-fatal on some boxes


def cmd_policy(_: argparse.Namespace) -> int:
    from tslit_dspy.model_policy import describe_policy

    print(describe_policy())
    return 0


def cmd_test_vllm(args: argparse.Namespace) -> int:
    from tslit_dspy.lm import health_check_vllm, make_lm, vllm_settings
    from tslit_dspy.model_policy import assert_detection_model

    health = health_check_vllm()
    print(json.dumps(health, indent=2))
    if not health["ok"]:
        print("vLLM not reachable", file=sys.stderr)
        return 1
    cfg = vllm_settings()
    try:
        assert_detection_model(cfg["model"], role="detection")
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    if args.skip_invoke:
        return 0

    import dspy

    lm = make_lm("vllm", role="inference")
    dspy.configure(lm=lm)
    # Tiny completion via dspy.Predict-style call
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


def cmd_optimize(args: argparse.Namespace) -> int:
    from tslit_dspy.optimize import run_optimization

    root = PROJECT_ROOT
    run_optimization(
        train_path=Path(args.train or root / "workspace" / "data" / "train.jsonl"),
        dev_path=Path(args.dev or root / "workspace" / "data" / "dev.jsonl"),
        output_path=Path(
            args.output
            or root / "workspace" / "compiled" / "tslit_analyzer_optimized.json"
        ),
        compile_model=args.compile_model,
        auto=args.auto,
        num_threads=args.num_threads,
        max_bootstrapped_demos=args.max_bootstrapped_demos,
        max_labeled_demos=args.max_labeled_demos,
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
    """Probe a target model (e.g. Qwen) then optionally analyze with Nemotron."""
    import logging
    import subprocess

    from tslit_dspy.probe_campaign import (
        DEFAULT_TARGET_MODEL,
        analyze_artifacts,
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
    base = args.base_url or os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8000/v1")

    def _maybe_start_recipe(recipe: str) -> None:
        if not args.manage_vllm:
            return
        script = root / "scripts" / "vllm_recipe.sh"
        print(f"[scan] starting vLLM recipe={recipe}")
        subprocess.check_call(["bash", str(script), "up", recipe])
        subprocess.check_call(["bash", str(script), "wait"])

    if phase in {"probe", "all"}:
        if args.manage_vllm:
            _maybe_start_recipe(args.target_recipe)
        dump_dir = artifacts / "request_dumps"
        print(f"[scan] PROBE target={target} base={base}")
        print(
            "[scan] time-shift controls: system virtual clock, tools=none, "
            f"dump={dump_dir}, canaries={not args.no_canary}, "
            f"strict_hygiene={not args.no_strict_hygiene}"
        )
        result = run_probe_campaign(
            base_url=base,
            model=target,
            api_key=os.getenv("VLLM_API_KEY", "local"),
            max_tokens=args.max_tokens,
            limit=args.limit,
            include_canaries=not args.no_canary,
            dump_dir=dump_dir,
            strict_hygiene=not args.no_strict_hygiene,
            fetch_rendered=not args.no_fetch_rendered,
        )
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
        # Print quick heuristic summary
        refusals = sum(
            1
            for r in result.records
            if any("refusal" in f or "gatekeeping" in f for f in r.get("detector_flags", []))
        )
        print(f"[scan] heuristic flags with refusal/gatekeeping: {refusals}/{len(result.records)}")

    if phase in {"analyze", "all"}:
        if args.manage_vllm:
            _maybe_start_recipe(args.detector_recipe)
            # After switching recipe, force detector to use whatever is served
            # Policy still requires Nemotron-class (not Qwen).
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

    # Policy unit checks
    assert_detection_model("nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4")
    assert_detection_model("anthropic/claude-opus-4-6")
    assert is_adversary_origin("Qwen/Qwen3.6-27B-FP8")
    try:
        assert_detection_model("Qwen/Qwen3.6-27B-FP8")
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
        description="TSLIT-DSPy on NVIDIA DGX Spark — non-adversary detection stack",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="Host + vLLM + policy health")
    sub.add_parser("policy", help="Print model-origin policy")

    t = sub.add_parser("test-vllm", help="Catalog (+ optional invoke) against local vLLM")
    t.add_argument("--skip-invoke", action="store_true")

    e = sub.add_parser("evaluate", help="Run detector eval on JSONL")
    e.add_argument("--test", default=None)
    e.add_argument("--output", default=None)
    e.add_argument("--model", default="vllm")
    e.add_argument("--model-base-url", default="")
    e.add_argument("--compiled", default=None)
    e.add_argument("--use-compiled", action="store_true")
    e.add_argument("--title", default="TSLIT-DSPy DGX Evaluation")

    o = sub.add_parser("optimize", help="MIPROv2 compile (expensive)")
    o.add_argument("--train", default=None)
    o.add_argument("--dev", default=None)
    o.add_argument("--output", default=None)
    o.add_argument("--compile-model", default="vllm")
    o.add_argument("--auto", default="light", choices=["light", "medium", "heavy"])
    o.add_argument("--num-threads", type=int, default=2)
    o.add_argument("--max-bootstrapped-demos", type=int, default=2)
    o.add_argument("--max-labeled-demos", type=int, default=4)

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
        help="probe=target only; analyze=detector only; all=both (switches vLLM if --manage-vllm)",
    )
    s.add_argument(
        "--target-model",
        default=None,
        help="Target model id (default: Qwen/Qwen3.6-27B-FP8 — DGX qwen27)",
    )
    s.add_argument("--target-recipe", default="qwen27")
    s.add_argument("--detector-recipe", default="nemotron-super")
    s.add_argument(
        "--detector-model",
        default="vllm",
        help="Detection LM alias/id (must pass non-adversary policy; default vllm/Nemotron)",
    )
    s.add_argument("--base-url", default=None)
    s.add_argument("--artifacts", default=None)
    s.add_argument("--compiled", default=None)
    s.add_argument("--limit", type=int, default=None, help="Cap number of probes (debug)")
    s.add_argument("--max-tokens", type=int, default=1200)
    s.add_argument(
        "--manage-vllm",
        action="store_true",
        help="Start/switch Desktop vLLM recipes via scripts/vllm_recipe.sh",
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
        "--no-fetch-rendered",
        action="store_true",
        help="Skip best-effort /tokenize rendered-prompt fetch from vLLM",
    )

    sub.add_parser("smoke", help="Offline import + policy checks (no GPU)")
    return p


def main(argv: list[str] | None = None) -> int:
    _load_env()
    # Ensure project root is importable when run as script
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "doctor": cmd_doctor,
        "policy": cmd_policy,
        "test-vllm": cmd_test_vllm,
        "evaluate": cmd_evaluate,
        "optimize": cmd_optimize,
        "experiment": cmd_experiment,
        "scan": cmd_scan,
        "smoke": cmd_smoke,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())

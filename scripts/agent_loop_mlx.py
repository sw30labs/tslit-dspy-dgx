#!/usr/bin/env python3
"""
agent_loop_mlx.py — Autonomous research agent for TSLIT-DSPy (DGX / local OpenAI-compatible).

General-purpose research driver for a local OpenAI-compatible server (vLLM on DGX,
MLX on Apple, or Ollama) that may not support native function calling. Tool
invocations are handled via structured XML tool-call text.

DGX default: vLLM on http://127.0.0.1:8000/v1 with NVIDIA Nemotron (US / non-adversary).
Do NOT point the agent brain at Qwen/DeepSeek/MiniMax — those are scan targets only.

Usage:
    python agent_loop_mlx.py [--tag TAG] [--max-loops N] [--dry-run]
    python agent_loop_mlx.py --base-url http://127.0.0.1:8000/v1 --tag dgx
    ~/Desktop/start-vllm.sh nemotron-super   # before live agent runs
"""

import argparse
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_DIR = Path.cwd()
RESULTS_FILE = REPO_DIR / "results.tsv"
RUN_LOG = REPO_DIR / "run.log"
HISTORY_LOG = REPO_DIR / "agent_history.jsonl"

CMD_TIMEOUT = 10  # seconds for short commands

# Rough token estimate: 1 token ≈ 4 characters
TOKEN_CHAR_RATIO = 4
MAX_CONTEXT_CHARS = 24_000 * TOKEN_CHAR_RATIO  # ~24k tokens (local models have smaller context)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class AgentConfig:
    target_files: list[str] = field(default_factory=lambda: ["train.py"])
    run_cmd: str = "uv run train.py"
    run_timeout: int = 360
    program_file: str = "program.md"
    primary_metric: str | None = None
    higher_is_better: bool = False
    allowed_patterns: list[str] = field(default_factory=list)
    append_only_files: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Tool call parsing — prompt-based since MLX server has no function calling
#
# The model is instructed to emit tool calls as:
#   <tool_call>
#   {"name": "tool_name", "arguments": {"arg": "value"}}
#   </tool_call>
# ---------------------------------------------------------------------------

TOOL_CALL_PATTERN = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
    re.DOTALL
)


def parse_tool_calls(text: str) -> list[dict]:
    """Extract tool calls from model output text."""
    calls = []
    for match in TOOL_CALL_PATTERN.finditer(text):
        try:
            parsed = json.loads(match.group(1))
            name = parsed.get("name", "")
            arguments = parsed.get("arguments", {})
            if name:
                calls.append({"name": name, "arguments": arguments})
        except json.JSONDecodeError:
            continue
    return calls


# ---------------------------------------------------------------------------
# Tool instructions (built dynamically based on config)
# ---------------------------------------------------------------------------

def build_tool_instructions(config: AgentConfig) -> str:
    """Build tool calling instructions based on config."""
    target_files_str = ", ".join(config.target_files)
    first_file = config.target_files[0]
    return f"""
=== TOOL CALLING FORMAT ===

You do NOT have function calling. Instead, emit tool calls as structured text blocks.
When you want to call a tool, output EXACTLY this format (you may call multiple tools
in one response):

<tool_call>
{{"name": "TOOL_NAME", "arguments": {{"arg1": "value1"}}}}
</tool_call>

After each tool call block, STOP and wait for the result. Do not guess the result.

Available tools:

1. read_file — Read a file from the repo.
   Arguments: {{"path": "relative/path/to/file"}}

2. write_file — Write content to a target file (writable files: {target_files_str}).
   Arguments: {{"path": "filename", "content": "full file content here"}}

3. run_command — Run a whitelisted shell command.
   Allowed commands: {config.run_cmd}, grep on log/code files,
   git operations, tail/cat/head on various files, ls.
   Arguments: {{"command": "the shell command"}}

4. append_results — Append one experiment row to results.tsv.
   Arguments: {{"metrics": {{"metric_name": 1.23, "other_metric": 42}}, "hypothesis": "description", "kept": true}}

=== EXAMPLE TOOL USAGE ===

I will read the current {first_file} to understand the baseline:

<tool_call>
{{"name": "read_file", "arguments": {{"path": "{first_file}"}}}}
</tool_call>

(Then wait for the result before continuing.)

=== END TOOL INSTRUCTIONS ===
"""


# ---------------------------------------------------------------------------
# Command whitelist
# ---------------------------------------------------------------------------

def build_allowed_patterns(run_cmd: str) -> list[str]:
    """Build command whitelist patterns based on config."""
    escaped_cmd = re.escape(run_cmd)
    return [
        f"^{escaped_cmd}(\\s+--[a-z][-a-z0-9]*)*$",
        r"^uv run prepare\.py$",
        r'^grep\s+.*\.(log|tsv|txt|csv|json|py)\s*$',
        r'^grep\s+"[^"]*"\s+\S+\.(log|tsv|txt|csv|json|py)$',
        r"^grep\s+'[^']*'\s+\S+\.(log|tsv|txt|csv|json|py)$",
        r'^grep\s+\S+\s+\S+\.(log|tsv|txt|csv|json|py)$',
        r'^git checkout -b ',
        r'^git commit -am\s+"[^"]*"$',
        r"^git commit -am\s+'[^']*'$",
        r'^git reset --hard HEAD$',
        r'^git log --oneline -\d+$',
        r'^git diff HEAD$',
        r'^git diff$',
        r'^git status$',
        r'^tail -n \d+ \S+\.(log|tsv|txt|csv)$',
        r'^head -n \d+ \S+\.(log|tsv|txt|csv)$',
        r'^cat \S+\.(log|tsv|txt|csv|py|md|json)$',
        r'^wc -l \S+',
        r'^ls\s',
        r'^ls$',
    ]


def is_command_allowed(command: str, allowed_patterns: list[str]) -> bool:
    """Check if a command matches the whitelist."""
    cmd = command.strip()
    for pattern in allowed_patterns:
        if re.match(pattern, cmd):
            return True
    if cmd.startswith("grep ") and any(
        cmd.rstrip().endswith(ext)
        for ext in (".log", ".tsv", ".txt", ".csv", ".json", ".py")
    ):
        return True
    return False


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def tool_read_file(path: str) -> str:
    """Read a file within the repo directory."""
    target = (REPO_DIR / path).resolve()
    if not str(target).startswith(str(REPO_DIR.resolve())):
        return f"ERROR: Access denied. Path '{path}' is outside the repo directory."
    if not target.exists():
        return f"ERROR: File not found: {path}"
    if not target.is_file():
        return f"ERROR: '{path}' is not a file."
    try:
        return target.read_text(encoding="utf-8")
    except Exception as e:
        return f"ERROR reading {path}: {e}"


def tool_write_file(path: str, content: str, config: AgentConfig) -> str:
    """Write content to an allowed target file.

    For files in config.append_only_files, enforces that all existing
    lines are preserved at the start of the new content (append-only).
    """
    if path.strip() not in config.target_files:
        return f"ERROR: You may only write to: {', '.join(config.target_files)}. Rejected path: '{path}'"
    target = REPO_DIR / path.strip()

    # Append-only enforcement: new content must start with old content
    if path.strip() in config.append_only_files and target.exists():
        try:
            old_content = target.read_text(encoding="utf-8")
            if old_content and not content.startswith(old_content):
                old_lines = old_content.rstrip("\n").split("\n")
                new_lines = content.rstrip("\n").split("\n")
                if len(new_lines) < len(old_lines):
                    return (
                        f"ERROR: {path} is append-only. You wrote {len(new_lines)} lines "
                        f"but the file has {len(old_lines)} existing lines. "
                        "You must preserve ALL existing lines and only add new ones at the end."
                    )
                for i, old_line in enumerate(old_lines):
                    if i >= len(new_lines) or new_lines[i] != old_line:
                        return (
                            f"ERROR: {path} is append-only. Line {i + 1} was modified or deleted. "
                            "You must keep all existing lines unchanged and only append new lines."
                        )
        except Exception as e:
            return f"ERROR checking append-only constraint for {path}: {e}"

    try:
        target.write_text(content, encoding="utf-8")
        return f"OK: wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"ERROR writing {path}: {e}"


def tool_run_command(command: str, config: AgentConfig) -> str:
    """Execute a whitelisted shell command."""
    cmd = command.strip()

    if not is_command_allowed(cmd, config.allowed_patterns):
        return json.dumps({
            "stdout": "",
            "stderr": f"ERROR: Command not allowed: {cmd}",
            "returncode": -1
        })

    if cmd == config.run_cmd:
        try:
            with open(RUN_LOG, "w") as f:
                proc = subprocess.run(
                    shlex.split(config.run_cmd),
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    timeout=config.run_timeout,
                    cwd=str(REPO_DIR),
                )
            return json.dumps({
                "stdout": "Completed. Output written to run.log.",
                "stderr": "",
                "returncode": proc.returncode
            })
        except subprocess.TimeoutExpired:
            return json.dumps({
                "stdout": "",
                "stderr": f"ERROR: Command timed out after {config.run_timeout}s",
                "returncode": -1
            })
        except Exception as e:
            return json.dumps({"stdout": "", "stderr": f"ERROR: {e}", "returncode": -1})

    timeout = CMD_TIMEOUT
    if cmd.startswith("uv run prepare.py"):
        timeout = config.run_timeout

    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_DIR),
        )
        return json.dumps({
            "stdout": proc.stdout[:50_000],
            "stderr": proc.stderr[:10_000],
            "returncode": proc.returncode
        })
    except subprocess.TimeoutExpired:
        return json.dumps({
            "stdout": "",
            "stderr": f"ERROR: Command timed out after {timeout}s",
            "returncode": -1
        })
    except Exception as e:
        return json.dumps({"stdout": "", "stderr": f"ERROR: {e}", "returncode": -1})


# Results column tracking
_results_columns: list[str] | None = None


def tool_append_results(metrics: dict, hypothesis: str, kept: bool) -> str:
    """Append one row to results.tsv with dynamic columns."""
    global _results_columns

    metric_keys = sorted(metrics.keys())
    columns = metric_keys + ["kept", "hypothesis"]

    if _results_columns is None:
        _results_columns = columns
        header = "\t".join(columns) + "\n"
        RESULTS_FILE.write_text(header, encoding="utf-8")

    values = [str(metrics.get(k, "")) for k in metric_keys] + [str(kept), hypothesis]
    row = "\t".join(values) + "\n"
    with open(RESULTS_FILE, "a", encoding="utf-8") as f:
        f.write(row)

    metric_summary = ", ".join(f"{k}={v}" for k, v in metrics.items())
    return f"OK: appended result ({metric_summary}, kept={kept})"


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

def execute_tool(name: str, arguments: dict, config: AgentConfig) -> str:
    """Dispatch to the right tool function."""
    if name == "read_file":
        return tool_read_file(arguments.get("path", ""))
    elif name == "write_file":
        return tool_write_file(arguments.get("path", ""), arguments.get("content", ""), config)
    elif name == "run_command":
        return tool_run_command(arguments.get("command", ""), config)
    elif name == "append_results":
        return tool_append_results(
            arguments.get("metrics", {}),
            arguments.get("hypothesis", ""),
            arguments.get("kept", False),
        )
    else:
        return f"ERROR: Unknown tool '{name}'"


# ---------------------------------------------------------------------------
# System prompt construction
# ---------------------------------------------------------------------------

def build_system_prompt(config: AgentConfig) -> str:
    """Read program file and construct the full system prompt."""
    program_path = REPO_DIR / config.program_file
    if not program_path.exists():
        print(f"ERROR: {config.program_file} not found in the current directory.", file=sys.stderr)
        print("Make sure you are running from the project root.", file=sys.stderr)
        sys.exit(1)

    program_md = program_path.read_text(encoding="utf-8")
    target_files_str = ", ".join(config.target_files)

    metric_direction = "higher" if config.higher_is_better else "lower"
    metric_guidance = ""
    if config.primary_metric:
        metric_guidance = f"\n- The primary metric to optimize is '{config.primary_metric}' ({metric_direction} is better)."

    tool_instructions = build_tool_instructions(config)

    return f"""You are an autonomous research agent. Your instructions are in {config.program_file} below.
You are running on a local MLX inference server. You do NOT have function calling.
Instead, you invoke tools by emitting structured text blocks as described below.

CRITICAL RULES:
- You may ONLY write to these files: {target_files_str}. Never modify other files.
- NEVER STOP the loop once it has begun. Do not ask for confirmation. Do not pause.
- If a run crashes, read tail of run.log, attempt a fix,
  then try again. Give up after 3 consecutive crashes on the same hypothesis.
- One hypothesis per experiment. Never batch multiple changes.
- After git reset on a failed experiment, re-read your target files before proposing next change.
- Call ONE tool at a time, then wait for the result before calling the next.{metric_guidance}

{tool_instructions}

=== {config.program_file} contents follow ===
{program_md}"""


# ---------------------------------------------------------------------------
# Conversation / context management
# ---------------------------------------------------------------------------

def trim_context(messages: list) -> list:
    """
    When context gets too large, summarize old experiments and trim.
    Always keep: system message, summary, and recent messages.
    """
    total_chars = sum(len(json.dumps(m)) for m in messages)
    if total_chars < MAX_CONTEXT_CHARS:
        return messages

    print("[context] Trimming message history to stay within context window...")

    system_msg = messages[0]
    recent = messages[-12:]
    middle = messages[1:-12]

    experiment_results = []
    for m in middle:
        content = m.get("content", "")
        if isinstance(content, str) and ("hypothesis" in content or "metrics" in content or "append_result" in content):
            experiment_results.append(content[:200])

    summary_text = (
        "=== CONTEXT SUMMARY (older experiments trimmed) ===\n"
        f"Trimmed {len(middle)} messages. Key results from trimmed history:\n"
    )
    for snippet in experiment_results[-15:]:
        summary_text += f"- {snippet}\n"
    summary_text += "=== END SUMMARY ===\n"

    summary_msg = {"role": "assistant", "content": summary_text}

    trimmed = [system_msg, summary_msg] + recent
    new_chars = sum(len(json.dumps(m)) for m in trimmed)
    print(f"[context] Reduced from {total_chars:,} to {new_chars:,} chars "
          f"(~{new_chars // TOKEN_CHAR_RATIO:,} tokens)")
    return trimmed


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_api_call(model: str, messages_count: int, response, elapsed: float):
    """Append one JSON line to agent_history.jsonl."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model": model,
        "messages_count": messages_count,
        "elapsed_seconds": round(elapsed, 2),
    }

    if hasattr(response, "usage") and response.usage:
        entry["usage"] = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    choice = response.choices[0] if response.choices else None
    if choice and choice.finish_reason:
        entry["finish_reason"] = choice.finish_reason

    with open(HISTORY_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ---------------------------------------------------------------------------
# Preflight checks
# ---------------------------------------------------------------------------

def preflight_checks(base_url: str, config: AgentConfig):
    """Verify environment is ready before starting the loop."""
    # Check server is reachable — supports both MLX (/health) and Ollama (/)
    import urllib.request
    import urllib.error
    server_root = base_url.replace("/v1", "")
    health_url = server_root + "/health"
    server_ok = False
    try:
        with urllib.request.urlopen(health_url, timeout=5) as resp:
            data = json.loads(resp.read())
            if data.get("loaded"):
                print(f"[preflight] MLX server OK — model: {data.get('model', 'unknown')}")
            else:
                print("WARNING: MLX server reports model not loaded.", file=sys.stderr)
            server_ok = True
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        # /health failed — try Ollama root endpoint
        try:
            with urllib.request.urlopen(server_root, timeout=5) as resp:
                body = resp.read().decode("utf-8", errors="replace").strip()
                if "ollama" in body.lower() or "running" in body.lower():
                    print(f"[preflight] Ollama server OK at {server_root}")
                    server_ok = True
                else:
                    print(f"[preflight] Server responded at {server_root}: {body[:80]}")
                    server_ok = True
        except Exception:
            pass
    if not server_ok:
        print(f"ERROR: Cannot reach inference server at {server_root}", file=sys.stderr)
        print("Start the server first (MLX or Ollama), then retry.", file=sys.stderr)
        sys.exit(1)

    # Check if run command's binary exists
    run_binary = shlex.split(config.run_cmd)[0]
    if not shutil.which(run_binary):
        print(f"WARNING: '{run_binary}' is not installed or not in PATH.", file=sys.stderr)

    # Check program file exists
    if not (REPO_DIR / config.program_file).exists():
        print(f"ERROR: {config.program_file} not found. Run this from the project root.",
              file=sys.stderr)
        sys.exit(1)

    print("[preflight] All checks passed.")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous research agent using local MLX server"
    )
    parser.add_argument(
        "--tag", type=str,
        default=datetime.now().strftime("%b%d").lower(),
        help="Run tag for branch name (default: today's date, e.g. mar12)"
    )
    parser.add_argument(
        "--max-loops", type=int, default=0,
        help="Stop after N experiments (default: unlimited)"
    )
    parser.add_argument(
        "--base-url", type=str, default="http://127.0.0.1:8000/v1",
        help="OpenAI-compatible base URL (default: DGX vLLM http://127.0.0.1:8000/v1)"
    )
    parser.add_argument(
        "--max-tokens", type=int, default=4096,
        help="Max tokens per completion (default: 4096)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Set up branch and read files, but do not start the loop"
    )
    parser.add_argument(
        "--target-file", action="append", default=None,
        dest="target_files",
        help="File the agent may write to (repeatable, default: train.py)"
    )
    parser.add_argument(
        "--run-cmd", type=str, default="uv run train.py",
        help="Command to run the experiment (default: 'uv run train.py')"
    )
    parser.add_argument(
        "--run-timeout", type=int, default=360,
        help="Timeout in seconds for --run-cmd (default: 360)"
    )
    parser.add_argument(
        "--program", type=str, default="program.md",
        help="Path to the program/instructions file (default: program.md)"
    )
    parser.add_argument(
        "--primary-metric", type=str, default=None,
        help="Name of the primary metric to optimize (e.g. val_bpb, accuracy)"
    )
    parser.add_argument(
        "--higher-is-better", action="store_true", default=False,
        help="If set, higher primary metric is better (default: lower is better)"
    )
    parser.add_argument(
        "--append-only-file", action="append", default=None,
        dest="append_only_files",
        help="Target file that is append-only — existing lines must be preserved (repeatable)"
    )
    args = parser.parse_args()

    if args.target_files is None:
        args.target_files = ["train.py"]

    # Build config
    config = AgentConfig(
        target_files=args.target_files,
        run_cmd=args.run_cmd,
        run_timeout=args.run_timeout,
        program_file=args.program,
        primary_metric=args.primary_metric,
        higher_is_better=args.higher_is_better,
        append_only_files=args.append_only_files or [],
    )
    config.allowed_patterns = build_allowed_patterns(config.run_cmd)

    # Preflight
    preflight_checks(args.base_url, config)

    # Local OpenAI-compatible client (vLLM on DGX / MLX / Ollama)
    api_key = os.environ.get("VLLM_API_KEY", "local")
    client = OpenAI(base_url=args.base_url, api_key=api_key)

    # Prefer configured detection model; enforce non-adversary policy when package available
    model_name = os.environ.get("VLLM_MODEL", "local")
    try:
        models = client.models.list()
        ids = [m.id for m in models.data]
        if ids:
            preferred = os.environ.get("VLLM_MODEL")
            if preferred and preferred in ids:
                model_name = preferred
            else:
                model_name = ids[0]
            print(f"[preflight] Using served model: {model_name}")
    except Exception as exc:  # noqa: BLE001
        print(f"[preflight] Could not list models ({exc}); using model={model_name}")

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from tslit_dspy.model_policy import assert_detection_model

        assert_detection_model(model_name, role="agent")
        print(f"[preflight] Model origin policy: ALLOWED for autoresearch brain")
    except ImportError:
        pass
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    # Create git branch
    branch_name = f"autoresearch/{args.tag}"
    result = subprocess.run(
        ["git", "checkout", "-b", branch_name],
        capture_output=True, text=True, cwd=str(REPO_DIR)
    )
    if result.returncode != 0:
        if "already exists" in result.stderr:
            print(f"ERROR: Branch '{branch_name}' already exists.", file=sys.stderr)
            print("Use a different --tag or delete the branch first.", file=sys.stderr)
            sys.exit(1)
        else:
            print(f"ERROR creating branch: {result.stderr}", file=sys.stderr)
            sys.exit(1)
    print(f"[setup] Created branch: {branch_name}")

    # Initialize empty results.tsv (header written on first append_results call)
    RESULTS_FILE.write_text("", encoding="utf-8")
    print("[setup] Initialized results.tsv")

    # Build system prompt
    system_prompt = build_system_prompt(config)

    # Initialize message history
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Setup is complete. Branch {branch_name} is checked out. "
                "results.tsv is initialized. Begin the research loop now. NEVER STOP.\n\n"
                f"Start by reading {config.target_files[0]} and {config.program_file} "
                "to understand the current state, then propose your first hypothesis."
            )
        }
    ]

    if args.dry_run:
        print("\n[dry-run] Setup complete. Would start loop with:")
        print(f"  Server:       {args.base_url}")
        print(f"  Branch:       {branch_name}")
        print(f"  Target files: {', '.join(config.target_files)}")
        if config.append_only_files:
            print(f"  Append-only:  {', '.join(config.append_only_files)}")
        print(f"  Run command:  {config.run_cmd}")
        print(f"  Max loops:    {'unlimited' if args.max_loops == 0 else args.max_loops}")
        print(f"  Program:      {config.program_file}")
        print(f"  System prompt length: {len(system_prompt):,} chars")
        print("\nExiting dry-run mode.")
        subprocess.run(["git", "checkout", "-"], capture_output=True, cwd=str(REPO_DIR))
        subprocess.run(["git", "branch", "-D", branch_name], capture_output=True, cwd=str(REPO_DIR))
        return

    # Track experiments
    experiments_run = 0
    best_primary = None

    # Graceful shutdown
    shutdown_requested = False

    def handle_sigint(signum, frame):
        nonlocal shutdown_requested
        if shutdown_requested:
            print("\n[agent] Force quit.")
            sys.exit(1)
        shutdown_requested = True
        print("\n[agent] Ctrl+C received. Finishing current step then exiting...")

    signal.signal(signal.SIGINT, handle_sigint)

    print(f"\n[agent] Starting autonomous loop (server={args.base_url})...")
    print("[agent] Press Ctrl+C to stop gracefully.\n")

    # Main agent loop
    while True:
        if shutdown_requested:
            break

        if args.max_loops > 0 and experiments_run >= args.max_loops:
            print(f"\n[agent] Reached max-loops limit ({args.max_loops}). Stopping.")
            break

        # Trim context if needed
        messages = trim_context(messages)

        # Call local MLX server
        t0 = time.time()
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.7,
                max_tokens=args.max_tokens,
            )
        except Exception as e:
            print(f"[agent] API error: {e}")
            print("[agent] Retrying in 5 seconds...")
            time.sleep(5)
            continue

        elapsed = time.time() - t0
        log_api_call(model_name, len(messages), response, elapsed)

        choice = response.choices[0]
        content = choice.message.content or ""

        # Add assistant response to history
        messages.append({"role": "assistant", "content": content})

        # Print a preview of the model's thinking (excluding tool call blocks)
        thinking = TOOL_CALL_PATTERN.sub("", content).strip()
        if thinking:
            preview = thinking[:300].replace("\n", " ")
            print(f"[agent] {preview}{'...' if len(thinking) > 300 else ''}")

        # Parse tool calls from the text
        tool_calls = parse_tool_calls(content)

        if tool_calls:
            # Execute the first tool call only (one at a time for local models)
            tc = tool_calls[0]
            func_name = tc["name"]
            func_args = tc["arguments"]
            args_preview = json.dumps(func_args)
            print(f"[tool] {func_name}({args_preview[:100]}{'...' if len(args_preview) > 100 else ''})")

            result = execute_tool(func_name, func_args, config)

            # Track experiments
            if func_name == "append_results":
                experiments_run += 1
                metrics = func_args.get("metrics", {})
                kept = func_args.get("kept", False)

                if config.primary_metric and config.primary_metric in metrics:
                    val = metrics[config.primary_metric]
                    if best_primary is None:
                        best_primary = val
                    elif config.higher_is_better and val > best_primary:
                        best_primary = val
                    elif not config.higher_is_better and val < best_primary:
                        best_primary = val

                metric_summary = ", ".join(f"{k}={v}" for k, v in metrics.items())
                metric_label = config.primary_metric or "primary"
                print(f"[experiment #{experiments_run}] {metric_summary} "
                      f"kept={kept} best_{metric_label}={best_primary}")

            # Cap long results to avoid blowing context
            if len(result) > 30_000:
                result = result[:30_000] + "\n... (truncated)"

            # Feed the tool result back as a user message
            messages.append({
                "role": "user",
                "content": f"<tool_result name=\"{func_name}\">\n{result}\n</tool_result>"
            })
            continue

        # No tool calls found — nudge model to continue
        print("[agent] No tool call found in response. Nudging to continue...")
        messages.append({
            "role": "user",
            "content": (
                "You did not call any tool. You MUST use the <tool_call> format to interact "
                "with the environment. Continue the research loop: propose a hypothesis, "
                "read/write files, run training. NEVER STOP.\n\n"
                "Remember the format:\n"
                "<tool_call>\n"
                '{"name": "tool_name", "arguments": {"arg": "value"}}\n'
                "</tool_call>"
            )
        })

    # Final summary
    metric_label = config.primary_metric or "primary_metric"
    print("\n" + "=" * 60)
    print("AGENT LOOP FINISHED")
    print("=" * 60)
    print(f"Experiments run:  {experiments_run}")
    print(f"Best {metric_label}:  {best_primary if best_primary is not None else 'N/A'}")
    print(f"Branch:           {branch_name}")
    print(f"Results:          {RESULTS_FILE}")
    print(f"API history:      {HISTORY_LOG}")
    print("=" * 60)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_BASE_URL = "https://api.moonshot.ai/v1"
DEFAULT_MODEL = "kimi-k2.5"
DEFAULT_MAX_FILE_BYTES = 700_000
DEFAULT_MAX_TOTAL_BYTES = 3_000_000
DEFAULT_ASK_MAX_TOKENS = 8192
DEFAULT_DRAFT_MAX_TOKENS = 16384
DEFAULT_TEMPERATURE = 0.1

SECRET_LINE_RE = re.compile(
    r"(?im)^(\s*[A-Z0-9_.-]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|ACCESS[_-]?KEY)"
    r"[A-Z0-9_.-]*\s*[:=]\s*)(.+)$"
)
SECRET_VALUE_RE = re.compile(r"\b(sk-[A-Za-z0-9_\-]{16,}|xox[baprs]-[A-Za-z0-9_\-]{16,})\b")


@dataclass(frozen=True)
class FilePayload:
    path: Path
    text: str
    bytes_read: int
    truncated: bool = False


def resolve_paths(patterns: Iterable[str]) -> list[Path]:
    paths: dict[str, Path] = {}
    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)
        if not matches:
            candidate = Path(pattern)
            if candidate.exists():
                matches = [str(candidate)]
        for match in matches:
            path = Path(match)
            if path.is_file():
                try:
                    resolved = path.resolve()
                except OSError:
                    continue
                paths[str(resolved).lower()] = resolved
    return sorted(paths.values(), key=lambda p: str(p).lower())


def redact_text(text: str) -> str:
    text = SECRET_LINE_RE.sub(lambda m: f"{m.group(1)}[REDACTED]", text)
    return SECRET_VALUE_RE.sub("[REDACTED]", text)


def is_binary(data: bytes) -> bool:
    if b"\x00" in data:
        return True
    if not data:
        return False
    sample = data[:4096]
    control = sum(1 for byte in sample if byte < 9 or (13 < byte < 32))
    return control / max(len(sample), 1) > 0.25


def read_payloads(
    paths: Sequence[Path],
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    redact: bool = True,
) -> list[FilePayload]:
    payloads: list[FilePayload] = []
    total = 0
    for path in paths:
        if total >= max_total_bytes:
            print(f"[skip total limit] {path}", file=sys.stderr)
            continue
        try:
            file_size = path.stat().st_size
        except OSError:
            print(f"[skip unreadable] {path}", file=sys.stderr)
            continue
        read_limit = min(file_size, max_file_bytes, max_total_bytes - total)
        with path.open("rb") as handle:
            raw = handle.read(read_limit)
        if is_binary(raw[:4096]):
            print(f"[skip binary] {path}", file=sys.stderr)
            continue

        truncated = file_size > read_limit

        text = raw.decode("utf-8", errors="replace")
        if redact:
            text = redact_text(text)
        payloads.append(FilePayload(path=path, text=text, bytes_read=len(raw), truncated=truncated))
        total += len(raw)
        if total >= max_total_bytes:
            break
    return payloads


def with_line_numbers(text: str) -> str:
    return "\n".join(f"{idx:5d}: {line}" for idx, line in enumerate(text.splitlines(), start=1))


def prompt_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        display_path = resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        display_path = resolved
    return display_path.as_posix()


def build_corpus(payloads: Sequence[FilePayload], *, line_numbers: bool = False) -> str:
    blocks: list[str] = []
    for payload in payloads:
        body = with_line_numbers(payload.text) if line_numbers else payload.text
        attrs = f'path="{prompt_path(payload.path)}" bytes="{payload.bytes_read}"'
        if payload.truncated:
            attrs += ' truncated="true"'
        blocks.append(f"<file {attrs}>\n{body}\n</file>")
    return "\n\n".join(blocks)


def strip_markdown_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text
    first_newline = stripped.find("\n")
    if first_newline == -1:
        return text
    without_open = stripped[first_newline + 1 :]
    if without_open.endswith("```"):
        without_open = without_open[:-3]
    return without_open.strip("\n")


def worker_config(args: argparse.Namespace) -> tuple[str, str, str]:
    base_url = args.base_url or os.environ.get("WORKER_BASE_URL", DEFAULT_BASE_URL)
    model = args.model or os.environ.get("WORKER_MODEL", DEFAULT_MODEL)
    api_key = (
        args.api_key
        or os.environ.get("WORKER_API_KEY")
        or os.environ.get("MOONSHOT_API_KEY")
        or ""
    )
    if not api_key and ("localhost" in base_url or "127.0.0.1" in base_url):
        api_key = "local"
    return api_key, base_url, model


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"[ignore invalid {name}={raw!r}; using {default}]", file=sys.stderr)
        return default


def env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        print(f"[ignore invalid {name}={raw!r}; using {default}]", file=sys.stderr)
        return default


def effective_max_tokens(args: argparse.Namespace, env_name: str, default: int) -> int:
    if args.max_tokens is not None:
        return args.max_tokens
    if env_name != "WORKER_MAX_TOKENS" and os.environ.get(env_name):
        return env_int(env_name, default)
    return env_int("WORKER_MAX_TOKENS", default)


def effective_temperature(args: argparse.Namespace) -> float:
    return args.temperature if args.temperature is not None else env_float("WORKER_TEMPERATURE", DEFAULT_TEMPERATURE)


def create_client(api_key: str, base_url: str):
    if not api_key:
        raise RuntimeError(
            "Missing worker API key. Set WORKER_API_KEY, MOONSHOT_API_KEY, or pass --api-key. "
            "For Ollama, set WORKER_BASE_URL=http://localhost:11434/v1."
        )
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Missing dependency: run `pip install -e .` or `pip install openai`.") from exc
    return OpenAI(api_key=api_key, base_url=base_url)


def print_usage(response) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", "?")
    completion_tokens = getattr(usage, "completion_tokens", "?")
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", 0) if details else 0
    finish = getattr(response.choices[0], "finish_reason", "?")
    print(
        f"[worker: {prompt_tokens} in ({cached} cached) / {completion_tokens} out | finish: {finish}]",
        file=sys.stderr,
    )


def add_common_model_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--api-key", help="Override WORKER_API_KEY for this call.")
    parser.add_argument("--base-url", help=f"OpenAI-compatible endpoint. Default: {DEFAULT_BASE_URL}")
    parser.add_argument("--model", help=f"Worker model. Default: {DEFAULT_MODEL}")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Completion budget. Defaults to WORKER_MAX_TOKENS or the command default.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help=f"Sampling temperature. Defaults to WORKER_TEMPERATURE or {DEFAULT_TEMPERATURE}.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Resolve inputs and print size estimates only.")


def add_file_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=env_int("WORKER_MAX_FILE_BYTES", DEFAULT_MAX_FILE_BYTES),
        help="Per-file byte cap before truncation.",
    )
    parser.add_argument(
        "--max-total-bytes",
        type=int,
        default=env_int("WORKER_MAX_TOTAL_BYTES", DEFAULT_MAX_TOTAL_BYTES),
        help="Total corpus byte cap before truncation/skipping.",
    )
    parser.add_argument("--no-redact", action="store_true", help="Disable conservative secret redaction.")


def add_ask_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--paths", nargs="+", required=True, help="Files or glob patterns to read.")
    parser.add_argument("--question", required=True, help="Specific extraction or summary request.")
    parser.add_argument("--line-numbers", action="store_true", help="Add line numbers to the corpus.")
    parser.add_argument("-o", "--output", help="Write answer to a file instead of stdout.")
    add_file_args(parser)
    add_common_model_args(parser)


def add_draft_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--spec", required=True, help="What the worker should draft.")
    parser.add_argument("--context", nargs="*", default=[], help="Reference files or globs for style/context.")
    parser.add_argument("--target", required=True, help="Intended final file path.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write directly to --target. Default writes under .worker-drafts/ for review.",
    )
    add_file_args(parser)
    add_common_model_args(parser)


def ask_worker(args: argparse.Namespace) -> int:
    paths = resolve_paths(args.paths)
    if not paths:
        print("No files matched --paths.", file=sys.stderr)
        return 2

    payloads = read_payloads(
        paths,
        max_file_bytes=args.max_file_bytes,
        max_total_bytes=args.max_total_bytes,
        redact=not args.no_redact,
    )
    if not payloads:
        print("No readable text files matched --paths.", file=sys.stderr)
        return 2

    corpus = build_corpus(payloads, line_numbers=args.line_numbers)
    if args.dry_run:
        print_dry_run("ask-worker", payloads, corpus)
        return 0

    api_key, base_url, model = worker_config(args)
    client = create_client(api_key, base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise code and document analyst. Read the provided files and "
                    "answer the user's question concisely. Return structured bullets. Mention "
                    "file paths and line numbers when they are present in the corpus. Do not "
                    "invent facts not supported by the files."
                ),
            },
            {"role": "user", "content": f"<corpus>\n{corpus}\n</corpus>"},
            {"role": "user", "content": args.question},
        ],
        max_tokens=effective_max_tokens(args, "WORKER_MAX_TOKENS", DEFAULT_ASK_MAX_TOKENS),
        temperature=effective_temperature(args),
    )
    answer = response.choices[0].message.content or ""
    if not answer.strip():
        print("[empty worker answer; try a higher --max-tokens value]", file=sys.stderr)
        return 1
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(answer, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(answer)
    print_usage(response)
    return 0


def draft_worker(args: argparse.Namespace) -> int:
    context_paths = resolve_paths(args.context)
    payloads = read_payloads(
        context_paths,
        max_file_bytes=args.max_file_bytes,
        max_total_bytes=args.max_total_bytes,
        redact=not args.no_redact,
    )
    corpus = build_corpus(payloads, line_numbers=False) if payloads else ""
    target = Path(args.target)
    output_path = target if args.apply else Path(".worker-drafts") / target

    if args.dry_run:
        print_dry_run("draft-worker", payloads, corpus)
        print(f"target: {target}")
        print(f"will_write: {output_path}")
        print(f"apply: {args.apply}")
        return 0

    api_key, base_url, model = worker_config(args)
    client = create_client(api_key, base_url)
    user_content = (
        f"<reference_files>\n{corpus}\n</reference_files>\n\n"
        f"Draft the full contents for this target file: {target}\n"
        f"Spec:\n{args.spec}"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate clean, idiomatic file contents matching the supplied reference "
                    "style when present. Output only the file contents. No explanations and "
                    "no markdown fences."
                ),
            },
            {"role": "user", "content": user_content},
        ],
        max_tokens=effective_max_tokens(args, "WORKER_DRAFT_MAX_TOKENS", DEFAULT_DRAFT_MAX_TOKENS),
        temperature=effective_temperature(args),
    )
    content = strip_markdown_fences(response.choices[0].message.content or "")
    if not content.strip():
        print("[empty worker draft; try a higher --max-tokens value]", file=sys.stderr)
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    if args.apply:
        print(f"Wrote {output_path}")
    else:
        print(f"Wrote draft {output_path}")
        print(f"Review it before copying or applying it to {target}.")
    print_usage(response)
    return 0


def print_dry_run(name: str, payloads: Sequence[FilePayload], corpus: str) -> None:
    print(f"{name} dry run")
    print(f"files: {len(payloads)}")
    print(f"chars: {len(corpus)}")
    print(f"rough_tokens: {max(len(corpus) // 4, 1)}")
    for payload in payloads:
        suffix = " truncated" if payload.truncated else ""
        print(f"- {prompt_path(payload.path)} ({payload.bytes_read} bytes{suffix})")


def health(args: argparse.Namespace) -> int:
    api_key, base_url, model = worker_config(args)
    print(f"base_url: {base_url}")
    print(f"model: {model}")
    print(f"api_key: {'set' if api_key else 'missing'}")
    print(f"ask_max_tokens: {env_int('WORKER_MAX_TOKENS', DEFAULT_ASK_MAX_TOKENS)}")
    print(f"draft_max_tokens: {env_int('WORKER_DRAFT_MAX_TOKENS', env_int('WORKER_MAX_TOKENS', DEFAULT_DRAFT_MAX_TOKENS))}")
    print(f"temperature: {env_float('WORKER_TEMPERATURE', DEFAULT_TEMPERATURE)}")
    print(f"max_file_bytes: {env_int('WORKER_MAX_FILE_BYTES', DEFAULT_MAX_FILE_BYTES)}")
    print(f"max_total_bytes: {env_int('WORKER_MAX_TOTAL_BYTES', DEFAULT_MAX_TOTAL_BYTES)}")
    try:
        import openai  # noqa: F401
    except ImportError:
        print("openai_package: missing")
        return 1
    print("openai_package: installed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-worker",
        description="Delegate bulk I/O from Codex to a cheap OpenAI-compatible worker model.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask", help="Read files and answer a focused question.")
    add_ask_args(ask)
    ask.set_defaults(func=ask_worker)

    draft = sub.add_parser("draft", help="Generate a draft file for Codex to review.")
    add_draft_args(draft)
    draft.set_defaults(func=draft_worker)

    health_parser = sub.add_parser("health", help="Check local configuration.")
    add_common_model_args(health_parser)
    health_parser.set_defaults(func=health)
    return parser


def build_ask_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ask-worker")
    add_ask_args(parser)
    parser.set_defaults(func=ask_worker)
    return parser


def build_draft_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="draft-worker")
    add_draft_args(parser)
    parser.set_defaults(func=draft_worker)
    return parser


def build_health_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="worker-health")
    add_common_model_args(parser)
    parser.set_defaults(func=health)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def ask_main(argv: Sequence[str] | None = None) -> int:
    parser = build_ask_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def draft_main(argv: Sequence[str] | None = None) -> int:
    parser = build_draft_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def health_main(argv: Sequence[str] | None = None) -> int:
    parser = build_health_parser()
    args = parser.parse_args(argv)
    return args.func(args)

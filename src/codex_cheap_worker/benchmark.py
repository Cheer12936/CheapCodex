from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Sequence

from .cli import (
    DEFAULT_ASK_MAX_TOKENS,
    build_corpus,
    create_client,
    effective_max_tokens,
    effective_temperature,
    env_int,
    read_payloads,
    resolve_paths,
    worker_config,
)


DEFAULT_QUESTION = (
    "Summarize the architecture, key files, likely entry points, and what Codex should inspect next. "
    "Keep the answer concise and structured."
)


def rough_tokens(text: str) -> int:
    return max(len(text) // 4, 1)


def usage_value(obj: Any, name: str, default: int = 0) -> int:
    value = getattr(obj, name, default)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def run_live(args: argparse.Namespace, corpus: str) -> dict[str, Any]:
    api_key, base_url, model = worker_config(args)
    client = create_client(api_key, base_url)
    started = time.perf_counter()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are benchmarking a cheap worker model for Codex. Read the provided files, "
                    "compress them into a concise but useful summary, and do not invent unsupported facts."
                ),
            },
            {"role": "user", "content": f"<corpus>\n{corpus}\n</corpus>"},
            {"role": "user", "content": args.question},
        ],
        max_tokens=effective_max_tokens(args, "WORKER_MAX_TOKENS", DEFAULT_ASK_MAX_TOKENS),
        temperature=effective_temperature(args),
    )
    elapsed = time.perf_counter() - started
    answer = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)
    prompt_tokens = usage_value(usage, "prompt_tokens")
    completion_tokens = usage_value(usage, "completion_tokens")
    total_tokens = usage_value(usage, "total_tokens", prompt_tokens + completion_tokens)
    details = getattr(usage, "prompt_tokens_details", None)
    cached_tokens = usage_value(details, "cached_tokens")

    return {
        "elapsed_seconds": round(elapsed, 3),
        "prompt_tokens": prompt_tokens,
        "cached_tokens": cached_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "answer_chars": len(answer),
        "answer_rough_tokens": rough_tokens(answer),
        "answer_preview": answer[: args.preview_chars],
        "finish_reason": getattr(response.choices[0], "finish_reason", None),
    }


def print_markdown(result: dict[str, Any]) -> None:
    print("# CheapCodex Benchmark")
    print()
    print("| Metric | Value |")
    print("| --- | ---: |")
    rows = [
        ("files", result["files"]),
        ("bytes_read", result["bytes_read"]),
        ("truncated_files", result["truncated_files"]),
        ("corpus_chars", result["corpus_chars"]),
        ("rough_input_tokens", result["rough_input_tokens"]),
        ("live", str(result["live"]).lower()),
    ]
    if result.get("live_result"):
        live = result["live_result"]
        rows.extend(
            [
                ("worker_prompt_tokens", live["prompt_tokens"]),
                ("worker_cached_tokens", live["cached_tokens"]),
                ("worker_completion_tokens", live["completion_tokens"]),
                ("worker_total_tokens", live["total_tokens"]),
                ("worker_answer_rough_tokens", live["answer_rough_tokens"]),
                ("codex_context_reduction_estimate", f'{result["codex_context_reduction_estimate"]}%'),
                ("elapsed_seconds", live["elapsed_seconds"]),
            ]
        )
    else:
        rows.append(("estimated_codex_context_if_summarized_to_2k", "about 2000 tokens"))
        rows.append(("estimated_reduction_if_summarized_to_2k", f'{result["estimated_reduction_to_2k"]}%'))

    for key, value in rows:
        print(f"| `{key}` | {value} |")

    print()
    print("## Files")
    for file_info in result["file_details"]:
        suffix = " truncated" if file_info["truncated"] else ""
        print(f"- `{file_info['path']}`: {file_info['bytes_read']} bytes{suffix}")

    live = result.get("live_result")
    if live and live.get("answer_preview"):
        print()
        print("## Worker Answer Preview")
        print()
        print(live["answer_preview"].strip())


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    paths = resolve_paths(args.paths)
    if not paths:
        raise SystemExit("No files matched --paths.")

    payloads = read_payloads(
        paths,
        max_file_bytes=args.max_file_bytes,
        max_total_bytes=args.max_total_bytes,
        redact=not args.no_redact,
    )
    if not payloads:
        raise SystemExit("No readable text files matched --paths.")

    corpus = build_corpus(payloads, line_numbers=args.line_numbers)
    corpus_tokens = rough_tokens(corpus)
    estimated_reduction_to_2k = max(round((1 - min(2000, corpus_tokens) / corpus_tokens) * 100, 1), 0)

    result: dict[str, Any] = {
        "paths": args.paths,
        "question": args.question,
        "files": len(payloads),
        "bytes_read": sum(payload.bytes_read for payload in payloads),
        "truncated_files": sum(1 for payload in payloads if payload.truncated),
        "corpus_chars": len(corpus),
        "rough_input_tokens": corpus_tokens,
        "estimated_reduction_to_2k": estimated_reduction_to_2k,
        "live": args.live,
        "file_details": [
            {
                "path": str(payload.path),
                "bytes_read": payload.bytes_read,
                "truncated": payload.truncated,
            }
            for payload in payloads
        ],
    }

    if args.live:
        live_result = run_live(args, corpus)
        answer_tokens = max(live_result["answer_rough_tokens"], 1)
        result["live_result"] = live_result
        result["codex_context_reduction_estimate"] = max(
            round((1 - min(answer_tokens, corpus_tokens) / corpus_tokens) * 100, 1),
            0,
        )

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cheapcodex-benchmark",
        description="Benchmark CheapCodex input compression and optional live worker usage.",
    )
    parser.add_argument("--paths", nargs="+", required=True, help="Files or glob patterns to benchmark.")
    parser.add_argument("--question", default=DEFAULT_QUESTION, help="Worker question for live benchmark.")
    parser.add_argument("--live", action="store_true", help="Call the worker model. Without this, no API tokens are spent.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of markdown.")
    parser.add_argument("--output", help="Write benchmark result to a file.")
    parser.add_argument("--preview-chars", type=int, default=1200, help="Worker answer preview length.")
    parser.add_argument("--line-numbers", action="store_true", help="Add line numbers to the corpus.")
    parser.add_argument("--max-file-bytes", type=int, default=env_int("WORKER_MAX_FILE_BYTES", 700_000))
    parser.add_argument("--max-total-bytes", type=int, default=env_int("WORKER_MAX_TOTAL_BYTES", 3_000_000))
    parser.add_argument("--no-redact", action="store_true")
    parser.add_argument("--api-key", help="Override WORKER_API_KEY for this call.")
    parser.add_argument("--base-url", help="OpenAI-compatible endpoint.")
    parser.add_argument("--model", help="Worker model.")
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = build_result(args)
    if args.json:
        output = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        from io import StringIO
        import contextlib

        buffer = StringIO()
        with contextlib.redirect_stdout(buffer):
            print_markdown(result)
        output = buffer.getvalue()

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


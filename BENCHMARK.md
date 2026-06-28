# Benchmark CheapCodex

This benchmark measures what CheapCodex is designed to save: Codex-side context.

It does not claim that total tokens disappear. The worker still spends tokens reading files. The useful metric is how much raw local code can be compressed before Codex reads it.

For a recorded synthetic full-stack benchmark and bug-fix case study, see [BENCHMARK-RESULTS.md](BENCHMARK-RESULTS.md).

## Dry Run

Dry-run mode does not call the worker model:

```powershell
cheapcodex-benchmark --paths "src/**/*.py" "README.md"
```

It reports:

- number of files read;
- bytes read;
- rough input token estimate;
- estimated Codex-side context reduction if the worker summary is around 2,000 tokens.

## Live Benchmark

Live mode calls the configured worker model:

```powershell
cheapcodex-benchmark --paths "src/**/*.py" "README.md" --live --max-tokens 2048
```

It reports:

- worker prompt tokens;
- cached tokens when the provider returns them;
- completion tokens;
- elapsed seconds;
- worker answer preview;
- estimated Codex context reduction based on the answer size.

## JSON Output

```powershell
cheapcodex-benchmark --paths "src/**/*.py" "README.md" --live --json --output output/benchmark.json
```

## Suggested Demo

For a video, run:

```powershell
cheapcodex-benchmark --paths "src/**/*.py" "scripts/*.ps1" "README.md" --question "Map the project architecture and installation flow. Keep it concise." --live --max-tokens 2048
```

Then compare:

```text
rough_input_tokens
worker_answer_rough_tokens
codex_context_reduction_estimate
```

This shows the practical effect: Codex can read a short worker summary plus a few verified source files instead of loading every scanned file into its own context.

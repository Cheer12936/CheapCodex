# Install Into Codex

This is the easiest path for users who want Codex to automatically use the worker.

## Windows Quick Install

Use a normal PowerShell window:

```powershell
git clone https://github.com/Cheer12936/CheapCodex.git
cd codex-cheap-worker
.\scripts\install-codex.ps1 -Provider deepseek
```

The installer will:

- create `.venv`;
- install the CLI tools;
- prompt for the API key without printing it;
- set `WORKER_API_KEY`, `WORKER_BASE_URL`, and `WORKER_MODEL`;
- add `bin\` to the user PATH;
- add/update the Codex worker rules in `%USERPROFILE%\.codex\AGENTS.md`.

Restart Codex after installation so the global `AGENTS.md` is loaded.

## Install By Asking Codex

Users can also ask Codex to do the setup. Give them the copy-paste prompt in [CODEX-INSTALL-PROMPT.md](CODEX-INSTALL-PROMPT.md).

Short prompt:

```text
Install https://github.com/Cheer12936/CheapCodex into my Codex setup. First check that WORKER_API_KEY exists; if it is missing, ask me to configure my DeepSeek key and stop. If it exists, run scripts/install-codex.ps1 -Provider deepseek -NonInteractive, configure the global AGENTS.md worker rules, and verify worker-health plus ask-worker dry-run.
```

## Provider Examples

DeepSeek:

```powershell
.\scripts\install-codex.ps1 -Provider deepseek
```

Kimi:

```powershell
.\scripts\install-codex.ps1 -Provider kimi
```

Ollama:

```powershell
.\scripts\install-codex.ps1 -Provider ollama
```

Custom OpenAI-compatible endpoint:

```powershell
.\scripts\install-codex.ps1 -Provider custom -BaseUrl "https://example.com/v1" -Model "your-model"
```

## Verify

```powershell
worker-health
ask-worker --paths README.md --question "一句话说明用途" --dry-run
```

If a fresh terminal does not find `worker-health`, run the absolute command from the repo:

```powershell
.\bin\worker-health.cmd
```

## What Codex Will Do

After restart, Codex reads `%USERPROFILE%\.codex\AGENTS.md`. The installer adds a marked block that tells Codex to use:

- `ask-worker` for bulk reading, summaries, inventories, endpoint lists, and cross-file mapping;
- `draft-worker` for boilerplate tests, docs, config files, adapters, and wrappers.

Codex still handles reasoning, verification, architecture decisions, subtle debugging, and final edits.

## One-Line Installer For A Published Repo

Users can run:

```powershell
$dir="$env:USERPROFILE\codex-cheap-worker"; git clone https://github.com/Cheer12936/CheapCodex.git $dir; cd $dir; .\scripts\install-codex.ps1 -Provider deepseek
```

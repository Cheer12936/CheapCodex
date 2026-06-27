# Codex Install Prompt

Give users this prompt when they want Codex to install the project for them.

```text
Please install this Codex Cheap Worker project into my local Codex setup:

https://github.com/Cheer12936/CheapCodex

Use the repository's installer script instead of manually recreating the setup.

Requirements:
- Clone or update the repository under my user home directory.
- Check whether WORKER_API_KEY already exists in my Windows user environment.
- If WORKER_API_KEY is missing, stop and ask me to configure a DeepSeek API key first. Do not run an interactive hidden prompt that can hang.
- Run scripts/install-codex.ps1 with Provider deepseek. Use -NonInteractive when WORKER_API_KEY already exists.
- Install the Python CLI tools.
- Configure WORKER_API_KEY, WORKER_BASE_URL, and WORKER_MODEL for my Windows user environment.
- Add the project's bin directory to my user PATH.
- Add or update the codex-cheap-worker block in %USERPROFILE%\.codex\AGENTS.md so Codex uses the worker rules.
- Verify with worker-health and a dry-run ask-worker command.
- Tell me whether I need to restart Codex.
```

## Short Version

```text
Install https://github.com/Cheer12936/CheapCodex into my Codex setup. First check that WORKER_API_KEY exists; if it is missing, ask me to configure my DeepSeek key and stop. If it exists, run scripts/install-codex.ps1 -Provider deepseek -NonInteractive, configure the global AGENTS.md worker rules, and verify worker-health plus ask-worker dry-run.
```

## One-Line PowerShell Alternative

For users who do not want Codex to do it:

```powershell
$dir="$env:USERPROFILE\codex-cheap-worker"; if (Test-Path $dir) { git -C $dir pull } else { git clone https://github.com/Cheer12936/CheapCodex.git $dir }; cd $dir; .\scripts\install-codex.ps1 -Provider deepseek
```

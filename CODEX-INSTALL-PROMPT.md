# Codex Install Prompt

Give users this prompt when they want Codex to install the project for them.

Replace `YOUR_NAME` with your GitHub username or organization.

```text
Please install this Codex Cheap Worker project into my local Codex setup:

https://github.com/YOUR_NAME/codex-cheap-worker

Use the repository's installer script instead of manually recreating the setup.

Requirements:
- Clone or update the repository under my user home directory.
- Run scripts/install-codex.ps1 with Provider deepseek.
- Prompt me for the DeepSeek API key if needed, but do not print it.
- Install the Python CLI tools.
- Configure WORKER_API_KEY, WORKER_BASE_URL, and WORKER_MODEL for my Windows user environment.
- Add the project's bin directory to my user PATH.
- Add or update the codex-cheap-worker block in %USERPROFILE%\.codex\AGENTS.md so Codex uses the worker rules.
- Verify with worker-health and a dry-run ask-worker command.
- Tell me whether I need to restart Codex.
```

## Short Version

```text
Install https://github.com/YOUR_NAME/codex-cheap-worker into my Codex setup. Use scripts/install-codex.ps1 -Provider deepseek, configure the global AGENTS.md worker rules, and verify worker-health plus ask-worker dry-run.
```

## One-Line PowerShell Alternative

For users who do not want Codex to do it:

```powershell
$dir="$env:USERPROFILE\codex-cheap-worker"; if (Test-Path $dir) { git -C $dir pull } else { git clone https://github.com/YOUR_NAME/codex-cheap-worker.git $dir }; cd $dir; .\scripts\install-codex.ps1 -Provider deepseek
```


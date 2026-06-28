@echo off
setlocal
call "%~dp0worker-env.cmd"
"%~dp0..\.venv\Scripts\cheapcodex-benchmark.exe" %*


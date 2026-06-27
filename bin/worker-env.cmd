@echo off
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v WORKER_API_KEY 2^>nul ^| findstr /R "WORKER_API_KEY"') do set "WORKER_API_KEY=%%B"
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v WORKER_BASE_URL 2^>nul ^| findstr /R "WORKER_BASE_URL"') do set "WORKER_BASE_URL=%%B"
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v WORKER_MODEL 2^>nul ^| findstr /R "WORKER_MODEL"') do set "WORKER_MODEL=%%B"
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v WORKER_MAX_TOKENS 2^>nul ^| findstr /R "WORKER_MAX_TOKENS"') do set "WORKER_MAX_TOKENS=%%B"
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v WORKER_DRAFT_MAX_TOKENS 2^>nul ^| findstr /R "WORKER_DRAFT_MAX_TOKENS"') do set "WORKER_DRAFT_MAX_TOKENS=%%B"
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v WORKER_TEMPERATURE 2^>nul ^| findstr /R "WORKER_TEMPERATURE"') do set "WORKER_TEMPERATURE=%%B"
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v WORKER_MAX_FILE_BYTES 2^>nul ^| findstr /R "WORKER_MAX_FILE_BYTES"') do set "WORKER_MAX_FILE_BYTES=%%B"
for /f "tokens=2,*" %%A in ('reg query HKCU\Environment /v WORKER_MAX_TOTAL_BYTES 2^>nul ^| findstr /R "WORKER_MAX_TOTAL_BYTES"') do set "WORKER_MAX_TOTAL_BYTES=%%B"

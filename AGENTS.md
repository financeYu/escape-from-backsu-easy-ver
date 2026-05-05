# Repository Agent Instructions

## Python Environment

Use the project-local Python environment for this repository.

- Do not run bare `pytest`; PowerShell will not find `.venv\Scripts\pytest.exe` unless the venv is activated.
- Do not run bare `python -m pytest`; it resolves to the global Python on this machine and may fail with `No module named pytest`.
- Run tests through the wrapper from the repository root:

```powershell
.\tools\run_pytest.ps1
```

- Pass pytest args directly after the wrapper:

```powershell
.\tools\run_pytest.ps1 tests\test_models.py -q
```

- For other Python module commands, use:

```powershell
.\tools\run_python.ps1 -m pip --version
```

The wrappers set `TEMP`, `TMP`, `PIP_CACHE_DIR`, and `PYTHONUTF8` to project-local values so Codex sandbox permission errors are less likely. If bootstrap/install still hits `PermissionError`, rerun the same wrapper command with escalation rather than switching to global Python.

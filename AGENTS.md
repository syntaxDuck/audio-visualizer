# Repository Guidelines

## Project Structure & Module Organization
The repository is intentionally small:
- `main.py`: primary real-time audio visualizer (CLI + matplotlib animation + audio capture).
- `examples/`: alternative scripts for experimentation (`sounddevice_rt_plot_device.py`, `sounddevice_rt_spectrogram.py`).
- `pyproject.toml` and `uv.lock`: dependency and Python runtime management (uv, Python 3.13).
- `.vscode/`: local editor/debug settings.

Keep new production code near `main.py` or split into a small `src/` package if complexity grows. Place exploratory scripts in `examples/`.

## Build, Test, and Development Commands
- `uv sync`: install locked dependencies into `.venv`.
- `uv run python main.py -l`: list available input devices.
- `uv run python main.py -d 0`: run visualizer on device ID `0`.
- `uv run python examples/sounddevice_rt_plot_device.py -d 0`: run waveform example.
- `uv run python examples/sounddevice_rt_spectrogram.py -d 0`: run text spectrogram example.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation and clear, descriptive names.
- Use `snake_case` for functions/variables, `UPPER_CASE` for constants, and short module names.
- Prefer small, testable functions over long inline logic in the script entrypoint.
- Keep CLI argument names stable (`--list-devices`, `--samplerate`, etc.) and document additions in `README.md`.

## Testing Guidelines
There is no formal test suite yet. For changes, run manual checks:
- Device discovery: `uv run python main.py -l`
- Main flow: run `main.py` against a real input device.
- Regression check: run both scripts in `examples/`.

When adding tests, use `pytest`, place files under `tests/`, and name them `test_<module>.py`.

## Commit & Pull Request Guidelines
Recent commits are short, imperative, and sometimes scoped (example: `Refactor: remove unused files ...`). Follow that style:
- Commit subject in imperative mood, ~50-72 chars.
- Explain behavior changes in the body when non-trivial.

For PRs, include:
- What changed and why.
- How to run/verify locally (exact commands).
- CLI/output screenshots or short recordings for visualization changes.
- Linked issue/task when available.

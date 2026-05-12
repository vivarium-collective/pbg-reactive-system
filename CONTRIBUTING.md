# Contributing to pbg-reactive-system

## Development setup

`uv` is required. Install with `brew install uv` or `pip install uv`.

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pytest
```

## Regenerating the demo report

```bash
python demo/demo_report.py
```

This runs the MAPK BRS, writes intermediate artifacts to
`demo/_artifacts/`, and rebuilds `demo/report.html`. Commit
`demo/report.html` only; `demo/_artifacts/` is gitignored.

## Releasing to PyPI

Tag a commit with `git tag v<VERSION>` and push the tag. The
`.github/workflows/release.yml` workflow publishes to PyPI
automatically using trusted publishing (no tokens needed after
initial setup).

PyPI trusted publishing must be configured once per repo. See
https://docs.pypi.org/trusted-publishers/.

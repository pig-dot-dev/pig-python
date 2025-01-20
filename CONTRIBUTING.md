Clone this repo, then

```bash
uv venv
source venv/bin/activate
uv pip install -e .[dev]
```

This will:
- put the `pig` module into your python import path
- put the `pig` CLI command into your path

The module will be in editable mode, so you can make changes to the code and they will be reflected in your environment.

Please run `ruff check .` and resolve any issues before submitting a PR.
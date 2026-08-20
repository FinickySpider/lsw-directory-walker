# LSW: List Walker

LSW (List Walker) is a Python command-line utility inspired by `ls` that walks a directory and produces a browsable HTML tree, a plain-text tree, or structured exports. It can filter results by name patterns, regular expressions, directory scope, file extension, size, modification date, and traversal depth.

## Documentation

This repository includes a Retype documentation site. Run `retype start` from the repository root to preview it, or `retype build` to generate static files in `.retype/`.

- [CLI reference](docs/cli.md): installation, command syntax, options, and examples.
- [Graphical launcher](docs/gui.md): the optional Flet one-shot interface.
- [Configuration and presets](docs/configuration.md): `lsw-config.json`, presets, and `.lswignore`.
- [Filtering guide](docs/filtering.md): how filters combine and how directory traversal behaves.
- [Output formats](docs/outputs.md): HTML, TXT, CSV, JSON, JSONL, and Markdown details.
- [HTML report guide](docs/html-report.md): tree controls, search, grouping, analytics, and browser behavior.
- [Developer reference](docs/developer-reference.md): function map, execution flow, data contracts, and known implementation notes.
- [Documentation deployment](docs/deployment.md): publish the Retype site with GitHub Pages.

Documentation deployment is automated by `.github/workflows/retype-pages.yml`. Set the repository's GitHub Pages source to **GitHub Actions**.

## Requirements

- Python 3.8 or newer is recommended.
- No third-party Python packages are required.
- The optional `--gui` launcher requires Flet. Install it with `python -m pip install -r requirements-gui.txt`.
- HTML analytics are rendered entirely by the generated report, with no external JavaScript dependency or network connection required.

## Quick start

From the directory containing `lsw.py`:

```powershell
python lsw.py --path .
```

To open the optional modern desktop launcher:

```powershell
python -m pip install -r requirements-gui.txt
python lsw.py --gui
```

This writes `tree_output.html` and opens it in the default browser. To generate a text tree without opening a browser:

```powershell
python lsw.py --path . --type txt --out tree.txt --no-browser
```

To export a filtered inventory:

```powershell
python lsw.py --path . --type csv --ext .py,.json --ignore node_modules --out inventory.csv
```

## Important behavior notes

- Hidden entries are skipped by the scan functions because names beginning with `.` are filtered out. The `show_hidden` config value is currently not consumed.
- `--parallel`, `--no-parallel`, and `--workers` are parsed, but the current execution path scans synchronously.
- The `theme` config value is loaded but the generated HTML starts in dark mode; the report's own theme button persists the user's browser choice in `localStorage`.
- `.lswignore` is read relative to the directory containing `lsw.py`, not the directory being scanned.
- CLI values override preset values only when the parsed CLI value is not `None`; argparse defaults can therefore remain in place instead of being replaced by a preset.

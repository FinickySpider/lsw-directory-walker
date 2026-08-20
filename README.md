# LSW: List Walker

LSW (List Walker) is a Python command-line utility inspired by `ls` that walks a directory and produces a browsable HTML tree, a plain-text tree, or structured exports. It can filter results by name patterns, regular expressions, directory scope, file extension, size, modification date, and traversal depth.

Public package: [lsw-directory-walker on PyPI](https://pypi.org/project/lsw-directory-walker/).

Latest releases are listed on the [GitHub Releases page](https://github.com/FinickySpider/lsw-directory-walker/releases). LSW is released under the [MIT License](LICENSE); credit is appreciated but not required.

### Community request

LSW is MIT licensed. You may use it, modify it, package it, and use it commercially. Attribution beyond the license notice is not required, but it is appreciated.

Please do not misrepresent unchanged or minimally changed copies of LSW as your original work, or imply that unofficial forks, packages, or distributions are the official project or endorsed by the original author. The project name, repository identity, documentation, and branding should not be used to mislead users into thinking an unofficial redistribution is the original LSW project or is endorsed by FinickySpider. This is a request for honest attribution and branding, not an additional restriction on the MIT license.

## Documentation

This repository includes a Retype documentation site. Run `retype start` from the repository root to preview it, or `retype build` to generate static files in `.retype/`.

- [CLI reference](docs/cli.md): installation, command syntax, options, and examples.
- [Installation](docs/installation.md): install the public PyPI package and use the `lsw` command.
- [Graphical launcher](docs/gui.md): the Flet one-shot interface included with the package.
- [Configuration and presets](docs/configuration.md): `lsw-config.json`, presets, and `.lswignore`.
- [Filtering guide](docs/filtering.md): how filters combine and how directory traversal behaves.
- [Output formats](docs/outputs.md): HTML, TXT, CSV, JSON, JSONL, and Markdown details.
- [stdout and stderr integration](docs/streams.md): consume clean serialized output from applications and pipelines.
- [AI and coding workflows](docs/ai-workflows.md): use LSW for repository orientation, context preparation, and automation.
- [stdout and stderr integration](docs/streams.md): consume LSW output from applications, AI tools, and pipelines.
- [HTML report guide](docs/html-report.md): tree controls, search, grouping, analytics, and browser behavior.
- [Developer reference](docs/developer-reference.md): function map, execution flow, data contracts, and known implementation notes.
- [Documentation deployment](docs/deployment.md): publish the Retype site with GitHub Pages.
- [Release guide](docs/releasing.md): publish future versions to PyPI.

Documentation deployment is automated by `.github/workflows/retype-pages.yml`. Set the repository's GitHub Pages source to **GitHub Actions**.

Future releases can be prepared with `.\scripts\release.ps1`, which bumps the version, runs checks, builds the package, pushes the release commit, and creates the GitHub Release that triggers PyPI publishing.

## Requirements

- Python 3.8 or newer is recommended.
- Installing the package installs Flet so the GUI is available immediately.
- On first run, LSW creates editable user defaults, presets, and `.lswignore` under `%APPDATA%\lsw` on Windows.
- HTML analytics are rendered entirely by the generated report, with no external JavaScript dependency or network connection required.

## Install as a command

Install the public package:

```powershell
py -m pip install lsw-directory-walker
```

For development, install the current checkout with `py -m pip install .`.

After installation, use LSW from any directory:

```powershell
lsw
lsw --gui
```

The command remains CLI-first. Running `lsw` does not open a window; use `lsw --gui` for the graphical launcher.

## Quick start

From the directory containing `lsw.py`:

```powershell
python lsw.py --path .
```

To open the modern desktop launcher:

```powershell
lsw --gui
```

This writes `tree_output.html` and opens it in the default browser. To generate a text tree without opening a browser:

```powershell
python lsw.py --path . --type txt --out tree.txt --no-browser
```

To export a filtered inventory:

```powershell
python lsw.py --path . --type csv --ext .py,.json --ignore node_modules --out inventory.csv
```

To print output for use in a pipeline while also saving the same file:

```powershell
lsw --path . --type json --stdout --out inventory.json
lsw --path . --type txt --stdout --out tree.txt
```

`--stdout` supports every output type and is additive, so omitting it preserves file-only behavior.

To print only, without creating a file:

```powershell
lsw --path . --type json --stdout-only
```

## Important behavior notes

- Hidden entries are skipped by the scan functions because names beginning with `.` are filtered out. The `show_hidden` config value is currently not consumed.
- `--parallel`, `--no-parallel`, and `--workers` are parsed, but the current execution path scans synchronously.
- The `theme` config value is loaded but the generated HTML starts in dark mode; the report's own theme button persists the user's browser choice in `localStorage`.
- `.lswignore` in the scanned directory takes precedence, followed by the current working directory, the file beside `lsw.py`, and finally the packaged default in the Python environment.
- Existing files in `%APPDATA%\lsw` are never overwritten by first-run initialization.
- CLI values override preset values only when the parsed CLI value is not `None`; argparse defaults can therefore remain in place instead of being replaced by a preset.

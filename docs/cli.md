# CLI Reference

## Invocation

```text
lsw [options]
```

When running directly from a source checkout, `python lsw.py [options]` is equivalent.

The graphical launcher is included in the PyPI package:

```powershell
py -m pip install lsw-directory-walker
lsw --gui
```

For a local checkout, use `py -m pip install .` instead.

The GUI is a one-shot desktop window. It collects scan settings, runs the same generation functions as the CLI, opens an HTML result unless disabled, and closes after a successful export. The plain `lsw` command remains CLI-first and does not open a window.

See the full [Graphical Launcher](gui.md) guide for the layout, filter behavior, progress state, and standalone HTML workflow.

`--path` is the directory to scan and defaults to the current working directory. Relative paths are resolved by the operating system from the shell's current directory.

## Options at a glance

| Option | Value | Default | Output branches |
|---|---|---:|---|
| `--path` | directory | `.` | all |
| `--preset`, `-p` | name | none | all |
| `--ext` | comma-separated extensions | none | HTML, CSV, JSON, JSONL, Markdown |
| `--ignore` | comma-separated names | none | all |
| `--ignore-pattern` | comma-separated globs | none | all |
| `--ignore-regex` | comma-separated regexes | none | all |
| `--include` | comma-separated directory names | none | all |
| `--include-pattern` | comma-separated globs | none | all |
| `--include-regex` | comma-separated regexes | none | all |
| `--max-depth` | integer | none | all |
| `--min-size` | size | none | HTML, CSV, JSON, JSONL, Markdown |
| `--max-size` | size | none | HTML, CSV, JSON, JSONL, Markdown |
| `--modified-after` | date/time | none | HTML, CSV, JSON, JSONL, Markdown |
| `--modified-before` | date/time | none | HTML, CSV, JSON, JSONL, Markdown |
| `--out` | filename | `tree_output.html` | all |
| `--type` | output type | config or `html` | all |
| `--group` | `none`, `type`, `prefix` | `none` | HTML |
| `--no-browser` | flag | config | HTML |
| `--txt-icons` | flag | off | TXT |
| `--parallel` | flag | config | parsed, currently inactive |
| `--no-parallel` | flag | off | parsed, currently inactive |
| `--workers` | integer | config or `4` | parsed, currently inactive |

## Detailed argument reference

Each option below includes a command you can run from the repository root. Replace paths and names with values from your project.

### `--path`

Sets the directory to scan. It defaults to `.`. The path may be absolute or relative to the shell's current directory.

```powershell
python lsw.py --path .\src
python lsw.py --path "C:\Projects\website" --type json --out website.json
```

### `--preset` / `-p`

Loads a preset from `lsw-presets/<name>.json`. The available names are shown by `python lsw.py --help`.

```powershell
python lsw.py --preset source-only --path .
python lsw.py -p large-files --path . --out large.csv
```

Only the preset's `args` object is applied. See [Configuration and presets](configuration.md) for precedence details.

### `--ext`

Accepts comma-separated extensions and keeps matching files, such as `.py,.js,.ts`. Include the leading dot. Matching is case-sensitive.

```powershell
python lsw.py --path . --ext .py,.pyi --type json --out python-files.json
```

This filter is applied to HTML and structured exports. It currently has no effect in the TXT branch.

### `--ignore`

Excludes exact entry names. For directories, the matching directory is not traversed.

```powershell
python lsw.py --path . --ignore node_modules,.git,__pycache__
```

### `--ignore-pattern`

Adds comma-separated `fnmatch` glob patterns. Patterns match entry names, not full relative paths.

```powershell
python lsw.py --path . --ignore-pattern "*.min.js,*.map,*.tmp" --type html
```

### `--ignore-regex`

Adds one or more comma-separated regular expressions. A name is ignored when any expression searches successfully.

```powershell
python lsw.py --path . --ignore-regex "^test_.*,.*\\.generated\\.py$" --type json
```

### `--include`

Restricts the scan root to named child directories. Root-level files are skipped when this option is present.

```powershell
python lsw.py --path . --include src,tests --type markdown --out selected.md
```

Nested directories are still traversed inside the selected root directories.

### `--include-pattern`

Whitelists files matching at least one comma-separated glob pattern.

```powershell
python lsw.py --path . --include-pattern "*.py,*.pyi" --type csv --out python.csv
```

### `--include-regex`

Whitelists files matching at least one regular expression.

```powershell
python lsw.py --path . --include-regex "^(main|test).*\\.(py|js)$" --type json
```

Because matching is performed against entry names rather than full relative paths, use `--include` for root-directory selection and use this option for filename selection.

### `--max-depth`

Limits recursion. The scan root starts at depth `0`; `--max-depth 1` lists root-level entries without enumerating their children.

```powershell
python lsw.py --path . --max-depth 2 --type txt --out shallow-tree.txt
```

### `--min-size`

Includes files at or above a size threshold. Supported units are `B`, `KB`, `MB`, `GB`, and `TB`.

```powershell
python lsw.py --path . --min-size 5MB --type csv --out files-over-5mb.csv
```

### `--max-size`

Includes files at or below a size threshold.

```powershell
python lsw.py --path . --max-size 100KB --type jsonl --out small-files.jsonl
```

Combine both size options for a range:

```powershell
python lsw.py --path . --min-size 10KB --max-size 1MB --type markdown
```

### `--modified-after`

Includes files modified at or after a local date or timestamp.

```powershell
python lsw.py --path . --modified-after 2026-08-01 --type json
python lsw.py --path . --modified-after "2026-08-01 09:30:00" --type csv
```

### `--modified-before`

Includes files modified at or before a local date or timestamp.

```powershell
python lsw.py --path . --modified-before 2026-08-20 --type markdown --out before.md
python lsw.py --path . --modified-after 2026-08-01 --modified-before 2026-08-20
```

### `--out`

Sets the output filename. LSW changes the suffix to match `--type` when necessary.

```powershell
python lsw.py --path . --type csv --out reports\inventory.csv
python lsw.py --path . --type html --out reports\tree
```

The parent directory must already exist.

### `--type`

Selects the output format: `html`, `txt`, `csv`, `json`, `jsonl`, or `markdown`.

```powershell
python lsw.py --path . --type html --out report.html
python lsw.py --path . --type txt --out tree.txt --no-browser
python lsw.py --path . --type jsonl --out inventory.jsonl
```

### `--group`

Controls HTML grouping: `none` keeps the expandable tree, `type` groups by extension, and `prefix` groups by the text before the first underscore.

```powershell
python lsw.py --path . --type html --group type --out by-type.html
python lsw.py --path . --type html --group prefix --out by-prefix.html
```

The option does not affect TXT or structured exports.

### `--no-browser`

Prevents LSW from opening the generated HTML file. It has no practical effect for non-HTML output.

```powershell
python lsw.py --path . --type html --no-browser --out report.html
```

### `--txt-icons`

Adds Unicode MIME icons to TXT tree entries. It is disabled by default.

```powershell
python lsw.py --path . --type txt --txt-icons --out tree-with-icons.txt
```

### `--parallel`

Requests parallel scanning. This flag is accepted for compatibility with the intended design, but the current implementation does not use it to create worker tasks.

```powershell
python lsw.py --path . --parallel --workers 8
```

### `--no-parallel`

Requests synchronous scanning. The current implementation is already synchronous, and this flag currently does not change behavior.

```powershell
python lsw.py --path . --no-parallel --type json
```

### `--workers`

Sets the requested worker count for parallel scanning. It is parsed and retained, but is currently unused because scanning is synchronous.

```powershell
python lsw.py --path . --parallel --workers 8 --type csv --out inventory.csv
```

## Size syntax

Accepted units are `B`, `KB`, `MB`, `GB`, and `TB`, using binary multiples: $1\,KB = 1024$ bytes. Decimal values are accepted, for example `1.5MB`. A bare number is interpreted as bytes.

## Date syntax

Supported forms are:

```text
YYYY-MM-DD
YYYY-MM-DD HH:MM:SS
```

Dates use the local timezone through Python's `datetime.timestamp()` conversion. An invalid date stops execution with an error message.

## Examples

```powershell
# HTML report for a source tree
python lsw.py --path . --ext .py,.js,.ts --ignore node_modules --out source.html

# Plain text tree with icons
python lsw.py --path . --type txt --txt-icons --out tree.txt

# Largest files as CSV
python lsw.py --path . --min-size 5MB --type csv --out large.csv

# Files changed in a time window
python lsw.py --path . --modified-after "2026-08-01" --modified-before "2026-08-20" --type json

# Only the root-level source and test folders
python lsw.py --path . --include src,test --type markdown --out selected.md
```

## Exit and error behavior

Invalid preset names, malformed preset JSON, invalid ignore/include regexes, and invalid dates print an error and exit with status 1. Individual unreadable files and directories are generally skipped; HTML and text generation may emit `[Permission Denied]` where appropriate.

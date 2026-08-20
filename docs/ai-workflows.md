---
label: AI and Coding Workflows
icon: copilot
order: 8650
---

# LSW for AI and Coding Workflows

LSW is useful anywhere a tool needs a current, structured view of a directory without manually opening files one by one. It can create compact context for an AI assistant, feed an inventory into another program, or produce a standalone report for human review.

The key integration mode is:

```powershell
lsw --type json --stdout-only
```

That command returns one complete JSON document on stdout, creates no file, and keeps diagnostics on stderr.

## Why LSW helps AI tools

AI coding tools commonly need answers to questions such as:

- What files exist in this project?
- Which directories contain source code or tests?
- Which files changed recently?
- Which files are unusually large?
- What should be ignored before context is collected?
- Where are configuration, documentation, and build artifacts located?

LSW can answer the inventory part consistently before the AI reads selected file contents. This makes the workflow more repeatable and helps avoid sending irrelevant dependency caches, build output, or secrets into a context window.

LSW does not decide what code means and does not replace code search. It provides a filtered structural map that an AI tool or human can use to decide what to inspect next.

## Choose an output type

| Need | Recommended type | Reason |
|---|---|---|
| AI or Python application integration | `json` | One complete array with metadata fields. |
| Streaming or record-by-record processing | `jsonl` | One JSON object per line. |
| Shell inspection | `txt` | Human-readable tree connectors and optional icons. |
| Spreadsheet or data pipeline | `csv` | Tabular records with a header. |
| Human-readable review artifact | `html` | Standalone searchable report with analytics. |
| Documentation or issue attachment | `markdown` | Readable table that is easy to paste or commit. |

## Basic AI context workflow

First create a filtered inventory:

```powershell
lsw --path . --type json --stdout-only `
  --ignore node_modules,.venv,dist,build `
  --include-pattern "*.py,*.md,*.toml,*.json"
```

A parent process can parse the result and then choose which files to read. The inventory records include:

```json
{
  "path": "C:/project/src/main.py",
  "name": "main.py",
  "type": "file",
  "size": 1234,
  "mtime": 1760000000.0,
  "mtime_str": "2025-10-09 12:00:00"
}
```

The normal pattern is:

```text
1. Run LSW to discover files.
2. Filter inventory records by type, path, size, or date.
3. Read only selected file contents.
4. Give the AI the tree, selected files, and the task.
```

This separates discovery from content loading, which is useful when a repository is larger than the available context window.

## Python subprocess example

```python
import json
import subprocess

command = [
    "lsw",
    "--path", project_dir,
    "--type", "json",
    "--stdout-only",
    "--ignore", "node_modules,.venv,dist,build",
    "--include-pattern", "*.py,*.md,*.toml,*.json",
]

result = subprocess.run(command, capture_output=True, text=True, check=True)
inventory = json.loads(result.stdout)

source_files = [
    item for item in inventory
    if item["type"] == "file" and item["size"] <= 200_000
]

if result.stderr:
    print("LSW diagnostics:", result.stderr)
```

The AI-facing payload can then contain the inventory plus the contents of only `source_files`.

## PowerShell coding workflow

```powershell
$inventory = lsw `
  --path . `
  --type json `
  --stdout-only `
  --ignore node_modules,.venv,dist,build `
  --include-pattern "*.py,*.md,*.toml,*.json" | ConvertFrom-Json

$inventory |
  Where-Object { $_.type -eq "file" -and $_.size -lt 200KB } |
  Select-Object path, size, mtime_str
```

This is useful before asking an AI assistant to review a project structure or identify the files relevant to a bug.

## Scenario: repository orientation

A new contributor or AI assistant can begin with:

```powershell
lsw --path . --type txt --stdout-only --ignore node_modules,.venv,dist,build
```

This gives a compact tree for orientation without creating a temporary artifact.

Use JSON instead when the next step is automated filtering:

```powershell
lsw --path . --type json --stdout-only --ignore node_modules,.venv,dist,build
```

## Scenario: source-only context

For a Python project:

```powershell
lsw --path . `
  --type json `
  --stdout-only `
  --include-pattern "*.py,*.pyi" `
  --ignore-pattern "*.generated.py,*.pyc"
```

For a mixed web project:

```powershell
lsw --path . `
  --type json `
  --stdout-only `
  --include-pattern "*.py,*.js,*.ts,*.tsx,*.html,*.css,*.md" `
  --ignore-pattern "*.min.js,*.min.css"
```

This helps keep generated bundles and dependency trees out of the initial context.

## Scenario: change-aware review

Give an AI tool a focused inventory of recently modified files:

```powershell
lsw --path . `
  --type json `
  --stdout-only `
  --modified-after "2026-08-01" `
  --ignore node_modules,.venv,dist,build
```

For a human review artifact, use the same filters with HTML:

```powershell
lsw --path . `
  --type html `
  --modified-after "2026-08-01" `
  --out recent-changes.html
```

## Scenario: large-file and context-budget control

Find files likely to consume a large amount of context:

```powershell
lsw --path . --type json --stdout-only --min-size 1MB
```

Or keep an AI-oriented inventory small by limiting the maximum file size:

```powershell
lsw --path . --type json --stdout-only --max-size 200KB
```

Size filtering does not read file contents into stdout; it only returns metadata. Your application can then apply a second content-reading policy.

## Scenario: project-specific ignore policy

A project can keep a `.lswignore` in its root. LSW checks the scanned directory before user and packaged defaults, so the policy follows the application:

```text
node_modules
.venv
.env
.env.*
dist
build
coverage
```

This is important for AI workflows because it reduces the chance of including secrets, generated output, or dependency caches in a later content-loading step.

## Scenario: standalone report for review

When a human needs to inspect the same snapshot as an AI preparation step:

```powershell
lsw --path . --type html --out project-inventory.html
```

The HTML file embeds its tree and analytics. It can be moved or shared without the original project or LSW installation.

## stdout and stderr safety

For machine-readable output, use `--stdout-only` or `--stdout` and capture the streams separately:

```python
result = subprocess.run(
    ["lsw", "--type", "json", "--stdout-only"],
    capture_output=True,
    text=True,
)

if result.returncode:
    raise RuntimeError(result.stderr)
data = json.loads(result.stdout)
```

Do not concatenate stderr into stdout before parsing JSON. stderr can contain diagnostics, validation errors, or informational preset messages when something needs attention.

## Practical limits

LSW provides inventory and serialization. It does not:

- Read every source file automatically into an AI prompt.
- Decide whether a file is safe to disclose.
- Replace a secret scanner.
- Replace semantic code search.
- Guarantee that a context payload fits a particular model.

Treat the inventory as a controlled first step. Apply project-specific ignore rules, size limits, file-type rules, and application-level content limits before sending file contents to an external model.

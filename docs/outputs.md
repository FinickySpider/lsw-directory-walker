# Output Formats

## HTML

HTML is the default. It contains an interactive tree, search, grouping, expand/collapse controls, path copying, printing, a theme toggle, and analytics. See [HTML report guide](html-report.md).

The output filename receives a `.html` suffix if needed. Unless `--no-browser` is active, the generated file is opened with Python's `webbrowser` module.

## TXT

The text output begins with `.` and uses `├──` and `└──` tree connectors. Hidden entries and configured ignore rules are omitted. Pass `--txt-icons` to add the script's MIME icon mapping.

```powershell
python lsw.py --type txt --out tree.txt --txt-icons
```

The current text generator does not receive the extension set from `--ext`; use a structured export or HTML when extension filtering is required.

## CSV

CSV contains one row per selected file or directory with these columns:

```text
path,name,type,size,mtime_str
```

Directory `size` is the immediate `stat` size field, not a recursive aggregate. CSV uses UTF-8 and includes a header row.

## JSON

JSON is an indented array of item objects. Each item contains:

```json
{
  "path": "...",
  "name": "example.py",
  "type": "file",
  "size": 1234,
  "mtime": 1760000000.0,
  "mtime_str": "2025-10-09 12:00:00"
}
```

The `mtime` value is a Unix timestamp. The exact value is platform and timezone dependent.

## JSONL

JSONL writes one JSON object per line with the same item structure as JSON. It is convenient for streaming or line-oriented processing.

## Markdown

Markdown contains a `Directory Tree` heading followed by a table with path, type, size, and modified columns. File sizes are human-readable; directories display `-` in the size column. Paths are wrapped in Markdown code spans but are not escaped for embedded pipe characters.

## Export errors

CSV, JSON, JSONL, and Markdown export functions catch their own exceptions and print an error message. The CLI does not otherwise validate that the output directory exists, so create parent directories before running with a nested output path.

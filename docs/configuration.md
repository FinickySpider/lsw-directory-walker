---
label: Configuration and Presets
icon: gear
order: 9000
---

# Configuration, Presets, and Ignore Rules

## `lsw-config.json`

The script looks for this file in the user configuration directory and source/package locations. Missing or invalid JSON falls back to built-in defaults. Recognized values are merged from `defaults` and `ui` objects:

```json
{
  "defaults": {
    "type": "html",
    "max_depth": null,
    "parallel": true,
    "parallel_workers": 4,
    "no_browser": false
  },
  "ui": {
    "theme": "dark",
    "show_hidden": false
  }
}
```

The `type`, `parallel`, `parallel_workers`, `theme`, and `no_browser` keys are loaded. `max_depth` is present in the sample configuration but is not used as the argparse default. `show_hidden` is currently unused. The parallel settings are parsed but the current scanner does not create a thread pool.

Command-line arguments are parsed after config loading. A preset is then loaded, and values are copied onto the parsed argument namespace only when the current value is `None`. In practice, argparse defaults such as `--type html`, `--out tree_output.html`, and `--group none` can take precedence over corresponding preset values.

## Presets

Presets can live in the user configuration directory, the current directory, or the source/package locations. Each file is named `<name>.json` and has an `args` object:

```json
{
  "name": "source-only",
  "description": "Show only source code files",
  "args": {
    "ext": ".py,.js,.ts",
    "ignore_pattern": "*.min.*,*.compiled.*",
    "type": "html"
  }
}
```

Run a preset with:

```powershell
python lsw.py --preset source-only --path .
```

The `name` and `description` fields are informational. Only `args` is applied. Available preset names are shown in the `--help` text.

## `.lswignore`

The script looks for `.lswignore` in this order:

1. The scanned directory, allowing each application or project to provide its own rules.
2. The current working directory.
3. The user configuration directory: `%APPDATA%\\lsw` on Windows or `$XDG_CONFIG_HOME/lsw` on other systems.
4. The directory containing `lsw.py`, which is useful for a source checkout.
5. The Python environment prefix, where the packaged fallback is installed by pip.

The first existing file wins. Blank lines and lines beginning with `#` are ignored. Ordinary lines are `fnmatch` glob patterns. Lines beginning with `^` or `|` are compiled as regular expressions.

## User configuration

On first run, LSW creates this directory without overwriting files that already exist:

```text
%APPDATA%\\lsw\\
  lsw-config.json
  .lswignore
  lsw-presets\\
```

The bundled defaults and presets are copied there so developers can edit them once and reuse them while scanning many unrelated folders. A `.lswignore` in the scanned folder or current working directory still takes precedence.

Example:

```text
node_modules
*.pyc
^test_.*
```

Ignore rules are matched against the entry name, not a normalized full relative path. Invalid regex lines in `.lswignore` are silently skipped. CLI ignore patterns and regexes are added to the loaded rules.

The repository's sample file excludes version-control directories, build output, caches, logs, and common editor artifacts.

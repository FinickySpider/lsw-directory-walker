# Filtering and Traversal

LSW applies filters while walking the directory tree. The scan functions share the same broad rules, with small output-specific differences documented in [Output formats](outputs.md).

## Evaluation order

For each entry, the scanner generally:

1. Lists entries and removes names beginning with `.`.
2. Applies ignore names, glob patterns, and ignore regexes.
3. For directories, applies `--ignore` and root-level `--include` rules, then recurses.
4. For files, applies root-level include-directory behavior, include patterns/regexes, extension filters where supported, size filters, and date filters.

An ignored directory is pruned and none of its descendants are considered. Include-directory filtering is only applied at the scan root; nested directories remain containers for matching files.

## Include versus ignore

Ignore rules are exclusions and take effect before inclusion. Include patterns and regexes are file whitelists: a file must match at least one supplied include pattern or regex. If no include rule is supplied, all non-hidden files are eligible.

`--include` is different: it names directories allowed directly under the scan root. When it is supplied, root-level files are skipped and only named root-level directories are traversed.

Examples:

```powershell
# Keep Python files, except generated files
python lsw.py --ext .py --ignore-pattern "*.generated.py,*.pyc"

# Search only source and test roots for TypeScript files
python lsw.py --include src,test --include-pattern "*.ts"

# Use a regex whitelist for names beginning with test_
python lsw.py --include-regex "^test_.*"
```

## Depth

Depth starts at `0` for the scan root. If `--max-depth N` is set, a function returns without processing entries when the current depth is greater than or equal to `N`. Thus `--max-depth 1` lists root-level entries but does not enumerate their children.

## Size and dates

Size checks use file byte counts from `os.stat`. Directory entries are not filtered by their aggregate size. Date checks use each file's modification timestamp. A file exactly on a minimum or maximum boundary is included.

## Current edge cases

- Extension matching is case-sensitive because the supplied extension and `os.path.splitext()` result are compared directly.
- The text output path does not pass `--ext` to its tree generator, so `--ext` has no effect when `--type txt` is selected.
- The HTML analytics treemap rebuilds a filesystem tree independently and does not apply the report's filters in the same way as the visible tree. Treat it as contextual size information rather than an exact filtered export.

# HTML Report Guide

The generated report is a self-contained HTML document, including its analytics rendering code. It starts in dark mode and includes a light-mode toggle.

## Tree view

- **Search** matches visible names. Use `type:.py` to match an extension, `name:foo` to match a name, or plain terms for text matching.
- **Case-sensitive** changes search comparison behavior and is persisted in browser `localStorage`.
- **Group** switches between the original tree, file-type groups, and prefix groups based on the text before the first underscore.
- **Expand All** and **Collapse All** control every `details` element.
- **Export JSON** downloads the currently visible clickable items as `tree_export.json`.
- **Print** invokes the browser print dialog.
- Clicking a file or directory copies its full path. Hovering updates the breadcrumb path.
- Directory rows use native HTML `details` elements, so they can also be opened with normal browser interaction.

Search state and theme state are stored in `localStorage` under `lastSearch`, `caseSensitive`, and `theme`.

## Analytics

The Analytics tab displays:

- KPI cards for total file size, file count, directory count, largest file, most recent file, and oldest file.
- A top-files bar chart using the largest 15 files.
- A file-type pie chart, switchable between total size and file count.
- A folder treemap showing hierarchical size information.

Analytics data is generated in Python before the HTML is written. Chart rendering is deferred until the Analytics tab is opened. If the CDN is unavailable, the tree can still be useful but charts may fail to initialize.

## Security and portability notes

The report embeds filesystem paths into HTML attributes and JavaScript-generated data. Names are HTML-escaped for visible labels, but paths used in attributes are not escaped separately. Generate reports for trusted local data and avoid publishing them without reviewing the embedded paths.

The report's use of `navigator.clipboard` can be restricted when the HTML is opened from a local file or under browser permissions. A legacy `document.execCommand('copy')` fallback is included.

## Grouping limitations

Grouping clones clickable elements into a separate container. It is intended for quick inspection and copying, not for preserving the full expandable directory structure. Search and visibility state can affect which items are included when grouping is applied.

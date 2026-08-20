import os
import html
import time
import asyncio
import argparse
import webbrowser
import fnmatch
import re
import csv
import json
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from mimetypes import guess_extension, types_map
import mimetypes
import sys

# ─── Helper for safe console output ────────────────────────────────────────────
def safe_print(message):
    """Print message with safe Unicode handling for Windows console."""
    try:
        print(message)
    except UnicodeEncodeError:
        # Replace characters unsupported by legacy Windows code pages.
        safe_msg = str(message).encode('ascii', errors='replace').decode('ascii')
        print(safe_msg)

# ─── MIME type icon mapping ────────────────────────────────────────────────────
MIME_ICONS = {
    # Documents
    '.pdf': '📄', '.doc': '📄', '.docx': '📄', '.txt': '📝', '.md': '📝', 
    '.csv': '📊', '.xls': '📊', '.xlsx': '📊', '.ppt': '🎬', '.pptx': '🎬',
    # Code
    '.py': '🐍', '.js': '⚙️', '.ts': '🔷', '.tsx': '⚛️', '.jsx': '⚛️',
    '.java': '☕', '.cpp': '⚙️', '.c': '⚙️', '.go': '🐹', '.rs': '🦀',
    '.php': '🐘', '.rb': '💎', '.sh': '🐚', '.bash': '🐚', '.json': '{ }',
    '.xml': '📋', '.html': '🌐', '.css': '🎨', '.scss': '🎨', '.sql': '🗄️',
    # Archives
    '.zip': '📦', '.tar': '📦', '.gz': '📦', '.rar': '📦', '.7z': '📦',
    # Images
    '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️', '.svg': '🎨',
    '.bmp': '🖼️', '.ico': '🖼️', '.webp': '🖼️',
    # Media
    '.mp4': '🎥', '.avi': '🎥', '.mov': '🎥', '.mkv': '🎥', '.flv': '🎥',
    '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.aac': '🎵',
    # Data & Config
    '.db': '🗄️', '.sqlite': '🗄️', '.yml': '⚙️', '.yaml': '⚙️', '.ini': '⚙️',
    '.toml': '⚙️', '.env': '🔐', '.gitignore': '📦',
    # Misc
    '.exe': '💻', '.dll': '💻', '.so': '💻', '.a': '💻',
    '': '📁'  # Default for folders
}

def get_mime_icon(filepath: str) -> str:
    """Get Unicode emoji icon based on file extension."""
    if os.path.isdir(filepath):
        return '📁'
    _, ext = os.path.splitext(filepath)
    return MIME_ICONS.get(ext.lower(), '📄')

# ─── Config file handling ──────────────────────────────────────────────────────
def user_config_dir() -> str:
  """Return the per-user LSW configuration directory."""
  if os.name == "nt":
    base = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
  else:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
  return os.path.join(base, "lsw")

def initialize_user_config(script_dir: str) -> str:
  """Create user defaults and bundled presets without overwriting edits."""
  config_dir = user_config_dir()
  try:
    os.makedirs(os.path.join(config_dir, "lsw-presets"), exist_ok=True)
    sources = {
      "lsw-config.json": os.path.join(config_dir, "lsw-config.json"),
      ".lswignore": os.path.join(config_dir, ".lswignore"),
    }
    for filename, destination in sources.items():
      if os.path.exists(destination):
        continue
      source = next((path for path in [os.path.join(script_dir, filename), os.path.join(sys.prefix, filename)] if os.path.exists(path)), None)
      if source:
        shutil.copy2(source, destination)
    preset_dir = os.path.join(config_dir, "lsw-presets")
    source_dirs = [os.path.join(script_dir, "lsw-presets"), os.path.join(sys.prefix, "lsw-presets")]
    source_dir = next((path for path in source_dirs if os.path.isdir(path)), None)
    if source_dir:
      for filename in os.listdir(source_dir):
        if filename.endswith(".json"):
          destination = os.path.join(preset_dir, filename)
          if not os.path.exists(destination):
            shutil.copy2(os.path.join(source_dir, filename), destination)
  except (OSError, PermissionError, shutil.Error):
    pass
  return config_dir

def support_paths(script_dir: str, relative_path: str, local_dir: str = None) -> list:
  """Return support-file locations from most local to most global."""
  paths = []
  if local_dir:
    paths.append(os.path.join(os.path.abspath(local_dir), relative_path))
  paths.extend([os.path.join(os.getcwd(), relative_path), os.path.join(user_config_dir(), relative_path), os.path.join(script_dir, relative_path)])
  prefix_path = os.path.join(sys.prefix, relative_path)
  if prefix_path not in paths:
    paths.append(prefix_path)
  cwd_path = os.path.join(os.getcwd(), relative_path)
  if cwd_path not in paths:
    paths.append(cwd_path)
  return paths

def load_config(script_dir: str) -> dict:
    """Load lsw-config.json from script directory."""
    defaults = {
        "type": "html",
        "parallel": True,
        "parallel_workers": 4,
        "theme": "dark",
        "no_browser": False
    }
    
    for config_file in support_paths(script_dir, "lsw-config.json"):
      if not os.path.exists(config_file):
        continue
      try:
        with open(config_file, 'r', encoding='utf-8') as f:
          config = json.load(f)
          if 'defaults' in config:
            defaults.update(config['defaults'])
          if 'ui' in config:
            defaults.update(config['ui'])
          return defaults
      except (json.JSONDecodeError, IOError):
        continue
    return defaults

# ─── Preset handling ───────────────────────────────────────────────────────────
def load_preset(preset_name: str, script_dir: str) -> dict:
    """Load preset from lsw-presets folder."""
    preset_paths = [os.path.join(path, f"{preset_name}.json") for path in support_paths(script_dir, "lsw-presets")]
    for preset_file in preset_paths:
      if not os.path.exists(preset_file):
        continue
      try:
        with open(preset_file, 'r', encoding='utf-8') as f:
          preset = json.load(f)
          return preset.get('args', {})
      except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in preset '{preset_name}': {e}")
    raise FileNotFoundError(f"Preset '{preset_name}' not found")

def get_available_presets(script_dir: str) -> list:
    """List available presets."""
    names = set()
    for presets_dir in support_paths(script_dir, "lsw-presets"):
      if not os.path.exists(presets_dir):
        continue
      try:
        names.update(f[:-5] for f in os.listdir(presets_dir) if f.endswith('.json'))
      except OSError:
        pass
    return sorted(names)

# ─── .lswignore file handling ──────────────────────────────────────────────────
def load_lswignore(script_dir: str, local_dir: str = None) -> tuple:
    """Load patterns from .lswignore file. Returns (ignore_patterns, ignore_regex)."""
    patterns = []
    regex_patterns = []
    
    ignore_file = next((path for path in support_paths(script_dir, ".lswignore", local_dir) if os.path.exists(path)), None)
    if ignore_file is None:
      return patterns, regex_patterns
    try:
      with open(ignore_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Simple heuristic: if it starts with ^, treat as regex
                if line.startswith('^') or line.startswith('|'):
                    try:
                        regex_patterns.append(re.compile(line))
                    except re.error:
                        pass
                else:
                    patterns.append(line)
    except IOError:
        pass
    
    return patterns, regex_patterns

def should_ignore(name: str, ignore_patterns=None, ignore_regex=None) -> bool:
    """Check if a file/folder should be ignored based on patterns."""
    if ignore_patterns:
        for pattern in ignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
    
    if ignore_regex:
        for regex in ignore_regex:
            if regex.search(name):
                return True
    
    return False

def should_include(name: str, include_patterns=None, include_regex=None) -> bool:
    """Check if a file/folder should be included based on whitelist patterns.
    If no include patterns are specified, everything is included."""
    if not include_patterns and not include_regex:
        return True
    
    if include_patterns:
        for pattern in include_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
    
    if include_regex:
        for regex in include_regex:
            if regex.search(name):
                return True
    
    return bool(include_patterns or include_regex) is False

def parse_size(size_str: str) -> int:
    """Parse human-readable size to bytes. E.g., '10MB' -> 10485760"""
    size_str = size_str.strip().upper()
    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3, 'TB': 1024**4}
    
    for unit, mult in multipliers.items():
        if size_str.endswith(unit):
            try:
                return int(float(size_str[:-len(unit)].strip()) * mult)
            except ValueError:
                return 0
    
    try:
        return int(float(size_str))
    except ValueError:
        return 0

def should_include_by_size(file_size: int, min_size=None, max_size=None) -> bool:
    """Check if file size is within the specified range."""
    if min_size is not None and file_size < min_size:
        return False
    if max_size is not None and file_size > max_size:
        return False
    return True

def should_include_by_date(mtime: float, after_date=None, before_date=None) -> bool:
    """Check if modification time is within the specified range."""
    if after_date is not None and mtime < after_date:
        return False
    if before_date is not None and mtime > before_date:
        return False
    return True

def parse_date(date_str: str) -> float:
    """Parse date string and return timestamp. Supports formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS"""
    try:
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.timestamp()
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date: {date_str}")
    except Exception as e:
        raise ValueError(f"Date parsing error: {e}")

# ─── Size calculation with caching ────────────────────────────────────────────
_size_cache = {}

def get_folder_size(path: str, ignore_dirs=None, max_depth=None, current_depth=0) -> int:
    """Calculate folder size with caching and optional depth limiting."""
    if ignore_dirs is None:
        ignore_dirs = set()
    
    if path in _size_cache:
        return _size_cache[path]
    
    total = 0
    try:
        for root, dirs, files in os.walk(path):
            # Calculate current depth
            depth = root[len(path):].count(os.sep)
            if max_depth is not None and depth >= max_depth:
                dirs.clear()
                continue
            
            # Remove ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            
            for fname in files:
                try:
                    total += os.stat(os.path.join(root, fname)).st_size
                except (OSError, PermissionError):
                    pass
    except (OSError, PermissionError):
        pass
    
    _size_cache[path] = total
    return total

def human_size(bytes_size: int) -> str:
    """Convert bytes to human-readable format (B, KB, MB, GB, TB)."""
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    size = float(bytes_size)
    for unit in units:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"

def clear_size_cache():
    """Clear the size cache."""
    global _size_cache
    _size_cache.clear()

# ─── added from ls.py ──────────────────────────────────────────────────────────
def generate_text_tree(dir_path=".", prefix="", ignore_dirs=None, ignore_patterns=None, ignore_regex=None, include_dirs=None, include_patterns=None, include_regex=None, max_depth=None, current_depth=0, min_size=None, max_size=None, after_date=None, before_date=None, show_icons=False):
    tree_str = ""
    if ignore_dirs is None:
        ignore_dirs = set()
    
    # Check depth limit
    if max_depth is not None and current_depth >= max_depth:
        return tree_str
    
    try:
        entries = sorted(os.listdir(dir_path))
    except (OSError, PermissionError) as e:
        return f"{prefix}[Permission Denied]\n"
    
    entries = [e for e in entries if not e.startswith('.')]  # Skip hidden
    for i, entry in enumerate(entries):
        path = os.path.join(dir_path, entry)
        
        # Check ignore patterns
        if should_ignore(entry, ignore_patterns, ignore_regex):
            continue
        
        connector = "└── " if i == len(entries) - 1 else "├── "
        
        try:
            if os.path.isdir(path) and entry not in ignore_dirs:
                # At root level (depth=0), apply include_dirs whitelist (folder-level filtering)
                if current_depth == 0 and include_dirs and entry not in include_dirs:
                    continue
                # Note: Don't apply include_patterns/regex to directories - they're just containers
                # Only files get pattern-filtered
                icon = f"{get_mime_icon(path)} " if show_icons else ""
                tree_str += f"{prefix}{connector}{icon}{entry}\n"
                extension = "    " if i == len(entries) - 1 else "│   "
                tree_str += generate_text_tree(path, prefix + extension, ignore_dirs, ignore_patterns, ignore_regex, include_dirs, include_patterns, include_regex, max_depth, current_depth + 1, min_size, max_size, after_date, before_date, show_icons)
            elif os.path.isfile(path):
                # At root level (depth=0) with include_dirs whitelist, skip files
                if current_depth == 0 and include_dirs:
                    continue
                # Apply include patterns/regex at all levels for files
                if not should_include(entry, include_patterns, include_regex):
                    continue
                # Apply size and date filters
                try:
                    stat = os.stat(path)
                    if not should_include_by_size(stat.st_size, min_size, max_size):
                        continue
                    if not should_include_by_date(stat.st_mtime, after_date, before_date):
                        continue
                    icon = f"{get_mime_icon(path)} " if show_icons else ""
                    tree_str += f"{prefix}{connector}{icon}{entry}\n"
                except (OSError, PermissionError):
                    pass
        except (OSError, PermissionError):
            pass
    
    return tree_str
# ───────────────────────────────────────────────────────────────────────────────

def generate_html_tree(dir_path: str, prefix: str = "", exts=None, progress=None, total=None, count=[0], ignore_dirs=None, ignore_patterns=None, ignore_regex=None, include_dirs=None, include_patterns=None, include_regex=None, max_depth=None, current_depth=0, min_size=None, max_size=None, after_date=None, before_date=None) -> str:
    if ignore_dirs is None:
        ignore_dirs = set()
    
    # Check depth limit
    if max_depth is not None and current_depth >= max_depth:
        return ""
    
    try:
        entries = sorted(e for e in os.listdir(dir_path) if not e.startswith("."))
    except (OSError, PermissionError):
        return '<div class="tree-line file-line"><span class="file">[Permission Denied]</span></div>'
    
    lines = []
    for i, entry in enumerate(entries):
        full_path = os.path.join(dir_path, entry)
        
        # Check ignore patterns
        if should_ignore(entry, ignore_patterns, ignore_regex):
            continue
        
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        safe = html.escape(entry)
        
        try:
            mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.stat(full_path).st_mtime))
            mtime_ts = os.stat(full_path).st_mtime
        except (OSError, PermissionError):
            mtime = "N/A"
            mtime_ts = None
        
        if os.path.isdir(full_path):
            if entry in ignore_dirs:
                continue
            # At root level (depth=0), apply include_dirs whitelist
            if current_depth == 0 and include_dirs and entry not in include_dirs:
                continue
            # Note: Don't apply include_patterns/regex to directories - they're just containers
            # Only files get pattern-filtered
            try:
                subtree = generate_html_tree(
                    full_path, prefix + ("    " if is_last else "│   "), exts, progress, total, count, ignore_dirs, ignore_patterns, ignore_regex, include_dirs, include_patterns, include_regex, max_depth, current_depth + 1, min_size, max_size, after_date, before_date
                )
            except (OSError, PermissionError):
                subtree = '<div class="tree-line file-line"><span class="file">[Permission Denied]</span></div>'
            
            if exts and not subtree.strip():
                continue
            
            try:
                size_label = human_size(get_folder_size(full_path, ignore_dirs, max_depth, current_depth))
            except (OSError, PermissionError):
                size_label = "N/A"
            
            icon = get_mime_icon(full_path)
            lines.append(
                "<details>"
                f'<summary class="tree-line dir-line">{prefix}'
                f'<span class="connector">{connector}</span>'
                f'<span class="dir clickable" data-path="{full_path}" '
                f'data-size="{size_label}" data-mtime="{mtime}" '
                f'title="Size: {size_label}\\nModified: {mtime}">{icon} {safe}</span></summary>'
                "<div class=\"tree\">"
                f"{subtree}"
                "</div></details>"
            )
        else:
            # At root level (depth=0) with include_dirs, skip files
            if current_depth == 0 and include_dirs:
                continue
            # Apply include patterns/regex for files
            if not should_include(entry, include_patterns, include_regex):
                continue
            ext = os.path.splitext(entry)[1]
            if exts and ext not in exts:
                continue
            try:
                stat = os.stat(full_path)
                
                # Apply size and date filters
                if not should_include_by_size(stat.st_size, min_size, max_size):
                    continue
                if not should_include_by_date(stat.st_mtime, after_date, before_date):
                    continue
                
                size_label = human_size(stat.st_size)
            except (OSError, PermissionError):
                size_label = "N/A"
            
            icon = get_mime_icon(full_path)
            lines.append(
                f'<div class="tree-line file-line">{prefix}'
                f'<span class="connector">{connector}</span>'
                f'<span class="file clickable" data-path="{full_path}" '
                f'data-size="{size_label}" data-mtime="{mtime}" '
                f'title="Size: {size_label}\\nModified: {mtime}">{icon} {safe}</span></div>'
            )
        if progress is not None and total is not None:
            count[0] += 1
            percent = int(count[0] * 100 / total)
            progress(percent)
    return "\n".join(lines) + ("\n" if lines else "")

# ─── Export functions ──────────────────────────────────────────────────────────
def collect_tree_items(dir_path: str, ignore_dirs=None, ignore_patterns=None, ignore_regex=None, include_dirs=None, include_patterns=None, include_regex=None, max_depth=None, current_depth=0, exts=None, min_size=None, max_size=None, after_date=None, before_date=None):
    """Collect all files and directories into a flat list with metadata."""
    if ignore_dirs is None:
        ignore_dirs = set()
    
    items = []
    
    if max_depth is not None and current_depth >= max_depth:
        return items
    
    try:
        entries = sorted(os.listdir(dir_path))
    except (OSError, PermissionError):
        return items
    
    entries = [e for e in entries if not e.startswith('.')]
    
    for entry in entries:
        full_path = os.path.join(dir_path, entry)
        
        if should_ignore(entry, ignore_patterns, ignore_regex):
            continue
        
        try:
            stat = os.stat(full_path)
            item = {
                'path': full_path,
                'name': entry,
                'type': 'dir' if os.path.isdir(full_path) else 'file',
                'size': stat.st_size,
                'mtime': stat.st_mtime,
                'mtime_str': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            }
            
            if os.path.isdir(full_path):
                if entry not in ignore_dirs:
                    # At root level (depth=0), apply include_dirs whitelist
                    if current_depth == 0 and include_dirs and entry not in include_dirs:
                        continue
                    # Note: Don't apply include_patterns/regex to directories - they're just containers
                    # Only files get pattern-filtered
                    items.append(item)
                    items.extend(collect_tree_items(full_path, ignore_dirs, ignore_patterns, ignore_regex, include_dirs, include_patterns, include_regex, max_depth, current_depth + 1, exts, min_size, max_size, after_date, before_date))
            else:
                # At root level (depth=0) with include_dirs, skip files
                if current_depth == 0 and include_dirs:
                    continue
                # Apply include patterns/regex for files
                if not should_include(entry, include_patterns, include_regex):
                    continue
                if not should_include_by_size(stat.st_size, min_size, max_size):
                    continue
                if not should_include_by_date(stat.st_mtime, after_date, before_date):
                    continue
                if exts:
                    ext = os.path.splitext(entry)[1]
                    if ext not in exts:
                        continue
                items.append(item)
        except (OSError, PermissionError):
            pass
    
    return items

def export_csv(items, output_file):
    """Export tree items to CSV."""
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['path', 'name', 'type', 'size', 'mtime_str'])
            writer.writeheader()
            for item in items:
                writer.writerow({k: item[k] for k in writer.fieldnames})
        safe_print(f"✅ CSV export saved to {output_file}")
    except Exception as e:
        safe_print(f"❌ Error exporting CSV: {e}")

def export_json(items, output_file):
    """Export tree items to JSON."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(items, f, indent=2, default=str)
        safe_print(f"✅ JSON export saved to {output_file}")
    except Exception as e:
        safe_print(f"❌ Error exporting JSON: {e}")

def export_jsonl(items, output_file):
    """Export tree items to JSONL (one JSON object per line)."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in items:
                f.write(json.dumps(item, default=str) + '\n')
        safe_print(f"✅ JSONL export saved to {output_file}")
    except Exception as e:
        safe_print(f"❌ Error exporting JSONL: {e}")

def export_markdown(items, output_file):
    """Export tree items to Markdown format."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# LSW: List Walker - Directory Tree\n\n")
            f.write("| Path | Type | Size | Modified |\n")
            f.write("|------|------|------|----------|\n")
            for item in items:
                size_str = human_size(item['size']) if item['type'] == 'file' else '-'
                f.write(f"| `{item['path']}` | {item['type']} | {size_str} | {item['mtime_str']} |\n")
        safe_print(f"✅ Markdown export saved to {output_file}")
    except Exception as e:
        safe_print(f"❌ Error exporting Markdown: {e}")

# ─── Analytics Data Generation ────────────────────────────────────────────────
def generate_analytics_data(items, top_n=20, root_path=None):
    """Generate analytics data for charts: treemap, top files, file types, KPIs."""
    analytics = {
        "top_files": [],
        "file_types": [],
        "kpis": {},
        "treemap": {"name": "Root", "size": 0, "children": []}
    }
    
    if not items:
        return analytics
    
    # ─── KPI Calculations ──────────────────────────────────────────────────────
    total_size = sum(item['size'] for item in items if item['type'] == 'file')
    total_files = sum(1 for item in items if item['type'] == 'file')
    total_dirs = sum(1 for item in items if item['type'] == 'dir')
    
    # Find largest file and most recent
    files_only = [item for item in items if item['type'] == 'file']
    largest_file = max(files_only, key=lambda x: x['size']) if files_only else None
    most_recent = max(files_only, key=lambda x: x['mtime']) if files_only else None
    oldest_file = min(files_only, key=lambda x: x['mtime']) if files_only else None
    
    analytics["kpis"] = {
        "total_size_bytes": total_size,
        "total_size_human": human_size(total_size),
        "total_files": total_files,
        "total_dirs": total_dirs,
        "largest_file": {
            "name": largest_file['name'] if largest_file else "N/A",
            "path": largest_file['path'] if largest_file else "N/A",
            "size": largest_file['size'] if largest_file else 0,
            "size_human": human_size(largest_file['size']) if largest_file else "0 B"
        },
        "most_recent": most_recent['mtime_str'] if most_recent else "N/A",
        "oldest_file": oldest_file['mtime_str'] if oldest_file else "N/A"
    }
    
    # ─── Top N Files ──────────────────────────────────────────────────────────
    sorted_files = sorted(
        [item for item in items if item['type'] == 'file'],
        key=lambda x: x['size'],
        reverse=True
    )[:top_n]
    
    analytics["top_files"] = [
        {
            "name": item['name'],
            "path": item['path'],
            "size": item['size'],
            "size_human": human_size(item['size']),
            "mtime": item['mtime_str']
        }
        for item in sorted_files
    ]
    
    # ─── File Type Breakdown ──────────────────────────────────────────────────
    type_stats = {}
    for item in items:
        if item['type'] == 'file':
            ext = os.path.splitext(item['name'])[1].lower() or 'no-ext'
            if ext not in type_stats:
                type_stats[ext] = {'size': 0, 'count': 0}
            type_stats[ext]['size'] += item['size']
            type_stats[ext]['count'] += 1
    
    # Sort by size and create chart data
    analytics["file_types"] = [
        {
            "type": ext,
            "size": stats['size'],
            "size_human": human_size(stats['size']),
            "count": stats['count']
        }
        for ext, stats in sorted(type_stats.items(), key=lambda x: x[1]['size'], reverse=True)
    ]
    
    # ─── Treemap (from the filtered inventory) ────────────────────────────────
    root_path = os.path.abspath(root_path or (os.path.dirname(items[0]['path']) if items else "."))
    treemap_root = {"name": os.path.basename(root_path) or root_path, "path": root_path, "size": 0, "children": []}
    nodes = {root_path: treemap_root}
    for item in items:
      item_path = os.path.abspath(item["path"])
      relative = os.path.relpath(item_path, root_path)
      if relative == "." or relative.startswith(".." + os.sep):
        continue
      parent_path = root_path
      parts = relative.split(os.sep)
      for part in parts[:-1] if item["type"] == "file" else parts:
        child_path = os.path.join(parent_path, part)
        if child_path not in nodes:
          folder = {"name": part, "path": child_path, "size": 0, "children": []}
          nodes[parent_path]["children"].append(folder)
          nodes[child_path] = folder
        parent_path = child_path
      if item["type"] == "file":
        nodes[parent_path]["children"].append({"name": item["name"], "path": item_path, "size": item["size"], "children": []})
      current = item["size"] if item["type"] == "file" else 0
      ancestor = parent_path
      while ancestor in nodes:
        nodes[ancestor]["size"] += current
        if ancestor == root_path:
          break
        ancestor = os.path.dirname(ancestor)
    analytics["treemap"] = treemap_root
    
    return analytics

# ───────────────────────────────────────────────────────────────────────────────
def build_html_report(target_folder, exts=None, group="none", progress=None, ignore_dirs=None, ignore_patterns=None, ignore_regex=None, include_dirs=None, include_patterns=None, include_regex=None, max_depth=None, min_size=None, max_size=None, after_date=None, before_date=None):
    if ignore_dirs is None:
        ignore_dirs = set()
    cwd = os.path.abspath(target_folder)
    root = html.escape(os.path.basename(cwd) or ".")
    root_mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.stat(cwd).st_mtime))
    root_size = human_size(get_folder_size(cwd, ignore_dirs, max_depth))
    tree_html = generate_html_tree(cwd, "", exts, progress, ignore_dirs=ignore_dirs, ignore_patterns=ignore_patterns, ignore_regex=ignore_regex, include_dirs=include_dirs, include_patterns=include_patterns, include_regex=include_regex, max_depth=max_depth, min_size=min_size, max_size=max_size, after_date=after_date, before_date=before_date)
    
    # Generate analytics data for charts
    items = collect_tree_items(cwd, ignore_dirs=ignore_dirs, ignore_patterns=ignore_patterns, ignore_regex=ignore_regex, include_dirs=include_dirs, include_patterns=include_patterns, include_regex=include_regex, max_depth=max_depth, exts=exts, min_size=min_size, max_size=max_size, after_date=after_date, before_date=before_date)
    analytics = generate_analytics_data(items, top_n=20, root_path=cwd)
    analytics_json = json.dumps(analytics)
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>LSW: List Walker - Directory Tree</title>
<style>
  /* FORCE DARK MODE */
  html, body {{ background:#0d1117 !important; color:#c9d1d9 !important; }}
  body {{margin:0;padding:1rem;background:#0d1117;color:#c9d1d9;font:0.95rem/1.2 monospace;}}
  h1 {{margin:0 0 0.75rem;color:#58a6ff;font-size:1.35rem;}}
  #controls {{margin-bottom:0.75rem;}}
  input, button, select {{
    padding:0.25em; margin-right:0.5em;
    background:#21262d !important; color:#c9d1d9 !important; border:1px solid #30363d !important;
    cursor:pointer;
  }}
  button:hover, select:hover, input:hover {{background:#30363d !important;}}
  #breadcrumb {{margin:0.5rem 0;color:#8b949e;font-size:0.9rem;}}
  .tree {{overflow:auto;}}
  .tree-line {{white-space:pre;line-height:1.2rem;margin:0;padding:0;}}
  summary.tree-line {{list-style:none;user-select:text;cursor:pointer;-webkit-user-select:text;}}
  .tree-line::before {{content:" ";display:inline-block;width:1em;color:#8b949e;}}
  summary.dir-line::before {{content:"▸";}}
  details[open] > summary.dir-line::before {{content:"▾";}}
  .connector {{color:#8b949e;}}
  .dir {{color:#58a6ff;font-weight:bold;}}
  .file {{color:#cdd9e5;}}
  .clickable {{cursor:pointer;}}
  details {{margin:0;}}
  #grouped {{display:none;}}
  #theme-toggle {{position:fixed;bottom:1rem;right:1rem;padding:0.5em 1em;background:#21262d;color:#c9d1d9;border:1px solid #30363d;border-radius:4px;cursor:pointer;z-index:9998;}}
  #theme-toggle:hover {{background:#30363d;}}
  @media print {{
    #controls, #instructions, #theme-toggle, .copied-tooltip {{display:none;}}
    body {{padding:0;}}
    details {{page-break-inside:avoid;}}
  }}
  html.light-mode {{background:#f6f8fa !important;color:#24292f !important;}}
  html.light-mode body {{background:#f6f8fa !important;color:#24292f !important;}}
  html.light-mode input, html.light-mode button, html.light-mode select {{
    background:#eaeef2 !important; color:#24292f !important; border:1px solid #d0d7de !important;
  }}
  html.light-mode input:hover, html.light-mode button:hover, html.light-mode select:hover {{
    background:#d0d7de !important;
  }}
  html.light-mode .dir {{color:#0969da;}}
  html.light-mode .connector {{color:#57606a;}}
  html.light-mode #breadcrumb {{color:#57606a;}}
  #instructions {{
    position:fixed;top:1rem;right:1rem;width:220px;
    background:#21262d !important;color:#c9d1d9 !important;border:1px solid #30363d !important;
    padding:0.75rem;border-radius:4px;font-size:0.9rem;line-height:1.3;
    max-height:80vh;overflow-y:auto;
  }}
  #instructions h2 {{margin-top:0;color:#58a6ff;font-size:1rem;}}
  #instructions ul {{padding-left:1.2em;margin:0;}}
  #instructions li {{margin-bottom:0.5em;}}
  .copied-tooltip {{
    position: fixed; top: 10px; right: 10px;
    background: #21262d !important; color: #58a6ff !important;
    border: 1px solid #30363d !important; padding: 0.5em 1em; border-radius: 4px;
    z-index: 9999; font-size: 1rem; display: none;
  }}
  /* Tabs styling */
  #tab-navigation {{
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    border-bottom: 1px solid #30363d;
  }}
  .tab-button {{
    padding: 0.5em 1em;
    background: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 4px 4px 0 0;
    cursor: pointer;
    font-weight: bold;
  }}
  .tab-button.active {{
    background: #30363d;
    color: #58a6ff;
    border-bottom-color: #30363d;
  }}
  .tab-button:hover {{
    background: #30363d;
  }}
  .tab-content {{
    display: none;
  }}
  .tab-content.active {{
    display: block;
  }}
  /* Analytics styling */
  #analytics-container {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 1.5rem;
  }}
  .analytics-card {{
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 1rem;
    min-height: 300px;
  }}
  .analytics-card h3 {{
    margin-top: 0;
    color: #58a6ff;
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 1px;
  }}
  .chart-container {{
    width: 100%;
    height: 300px;
    overflow: auto;
  }}
  .bar-chart {{display:flex;align-items:flex-end;gap:0.35rem;height:250px;padding:1rem 0.5rem 2rem;}}
  .bar-item {{display:flex;flex:1;min-width:24px;height:100%;align-items:flex-end;position:relative;}}
  .bar {{width:100%;background:#58a6ff;border-radius:3px 3px 0 0;min-height:2px;}}
  .bar-label {{position:absolute;bottom:-1.8rem;left:50%;transform:translateX(-50%) rotate(-45deg);transform-origin:top left;font-size:0.65rem;white-space:nowrap;color:#8b949e;}}
  .bar-value {{position:absolute;top:-1.1rem;left:50%;transform:translateX(-50%);font-size:0.65rem;color:#c9d1d9;white-space:nowrap;}}
  .type-list {{display:flex;flex-direction:column;gap:0.6rem;padding:0.75rem 0;}}
  .type-row {{display:grid;grid-template-columns:70px 1fr auto;gap:0.5rem;align-items:center;font-size:0.75rem;}}
  .type-track {{height:0.8rem;background:#30363d;border-radius:2px;overflow:hidden;}}
  .type-fill {{height:100%;background:#58a6ff;}}
  .treemap {{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:0.35rem;padding:0.5rem;}}
  .treemap-item {{background:#238636;color:#fff;padding:0.6rem;min-height:55px;overflow:hidden;font-size:0.7rem;}}
  .analytics-empty {{display:flex;align-items:center;justify-content:center;height:100%;color:#8b949e;font-size:0.8rem;}}
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
  }}
  .kpi-card {{
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 4px;
    padding: 0.75rem;
    text-align: center;
  }}
  .kpi-value {{
    font-size: 1.5rem;
    font-weight: bold;
    color: #58a6ff;
    margin-bottom: 0.25rem;
  }}
  .kpi-label {{
    font-size: 0.75rem;
    color: #8b949e;
    text-transform: uppercase;
  }}
</style>
</head>
<body>
<h1>LSW: List Walker</h1>

<!-- Tab Navigation -->
<div id="tab-navigation">
  <button class="tab-button active" data-tab="tree-tab">📁 Tree View</button>
  <button class="tab-button" data-tab="analytics-tab">📊 Analytics</button>
</div>

<!-- Tree Tab -->
<div id="tree-tab" class="tab-content active">
<div id="controls">
  <input type="text" id="search" placeholder="Search…"/>
  <input type="checkbox" id="case-sensitive" title="Case-sensitive search"/>
  <label for="case-sensitive" style="margin-right:1em;">Aa</label>
  <select id="grouping">
    <option value="none">Group: None</option>
    <option value="type">Group: File Type</option>
    <option value="prefix">Group: Prefix</option>
  </select>
  <button id="expand-all">Expand All</button>
  <button id="collapse-all">Collapse All</button>
  <button id="export">Export JSON</button>
  <button id="print">🖨️ Print</button>
</div>
<button id="theme-toggle">🌙 Dark</button>
<div id="breadcrumb">Path: {cwd}</div>
<div class="tree" id="tree-container">
<details>
<summary class="tree-line dir-line"><span class="connector">└── </span><span class="dir clickable" data-path="{cwd}" data-size="{root_size}" data-mtime="{root_mtime}" title="Size: {root_size}\\nModified: {root_mtime}">{root}</span></summary>
<div class="tree">{tree_html}</div>
</details>
</div>
<div id="grouped"></div>
<div id="instructions">
  <h2>Instructions</h2>
  <ul>
    <li>Hover for size &amp; timestamp tooltip</li>
    <li>Click to copy full path</li>
    <li>Search can use <code>type:.py</code> or <code>name:foo</code></li>
    <li>Grouping and tree both available</li>
    <li>Use buttons to expand/collapse</li>
    <li>Export JSON of visible items</li>
  </ul>
</div>

</div><!-- End tree-tab -->

<!-- Analytics Tab -->
<div id="analytics-tab" class="tab-content">
  <div class="kpi-grid" id="kpi-container">
    <!-- KPI cards will be populated by JavaScript -->
  </div>
  <div id="analytics-container">
    <div class="analytics-card">
      <h3>Top Files</h3>
      <div class="chart-container" id="top-files-chart"></div>
    </div>
    <div class="analytics-card">
      <h3>File Types</h3>
      <div style="margin-bottom: 1rem;">
        <label>Show: </label>
        <select id="type-metric">
          <option value="size">By Size</option>
          <option value="count">By Count</option>
        </select>
      </div>
      <div class="chart-container" id="file-types-chart"></div>
    </div>
    <div class="analytics-card">
      <h3>Folder Treemap</h3>
      <div class="chart-container" id="treemap-chart"></div>
    </div>
  </div>
</div>

<div class="copied-tooltip" id="copied-tooltip">Copied!</div>

<!-- Analytics Data -->
<script>
const analyticsData = {analytics_json};
</script>

<script>
// ─── Theme toggle ──────────────────────────────────────────────────────────
function initTheme() {{
  const theme = localStorage.getItem('theme') || 'dark';
  document.documentElement.className = theme === 'light' ? 'light-mode' : '';
  updateThemeButton();
}}
function updateThemeButton() {{
  const isDark = !document.documentElement.classList.contains('light-mode');
  document.getElementById('theme-toggle').textContent = isDark ? '☀️ Light' : '🌙 Dark';
}}
document.getElementById('theme-toggle').addEventListener('click', function() {{
  const isDark = !document.documentElement.classList.contains('light-mode');
  if(isDark) {{
    document.documentElement.classList.add('light-mode');
    localStorage.setItem('theme', 'light');
  }} else {{
    document.documentElement.classList.remove('light-mode');
    localStorage.setItem('theme', 'dark');
  }}
  updateThemeButton();
}});
initTheme();

// ─── Search with case-sensitive support ─────────────────────────────────────
function parseFilters(expr, caseSensitive) {{
  const f = {{ name:'', type:'', text:'' }};
  expr.trim().split(/\\s+/).forEach(tok => {{
    if(tok.startsWith('type:')) f.type = tok.slice(5);
    else if(tok.startsWith('name:')) f.name = tok.slice(5);
    else f.text += tok + ' ';
  }});
  f.text = f.text.trim();
  if(!caseSensitive) {{
    f.name = f.name.toLowerCase();
    f.text = f.text.toLowerCase();
    f.type = f.type.toLowerCase();
  }}
  return f;
}}

document.getElementById('search').addEventListener('input', function() {{
  const caseSensitive = document.getElementById('case-sensitive').checked;
  const {{name,type,text}} = parseFilters(search.value, caseSensitive);
  document.querySelectorAll('.clickable').forEach(function(span) {{
    let txt = span.textContent;
    if(!caseSensitive) txt = txt.toLowerCase();
    const ext = span.getAttribute('data-path').split('.').pop().toLowerCase();
    const okName = !name || txt.includes(name);
    const okType = !type || ext === (caseSensitive ? type : type.toLowerCase()).replace('.', '');
    const okText = !text || txt.includes(text);
    span.parentElement.style.display = (okName && okType && okText) ? '' : 'none';
  }});
  document.querySelectorAll('details').forEach(function(d) {{
    var sum = d.querySelector('summary');
    var any = Array.from(d.querySelectorAll('.file-line')).some(function(el) {{ return el.style.display !== 'none'; }});
    sum.style.display = any ? '' : 'none';
    d.querySelector(':scope > .tree').style.display = any ? '' : 'none';
    d.open = any;
  }});
  if(!search.value) {{
    document.querySelectorAll('.tree-line').forEach(function(el) {{ el.style.display = ''; }});  
    document.querySelectorAll('.tree').forEach(function(el) {{ el.style.display = ''; }});  
    document.querySelectorAll('details').forEach(function(d) {{ d.open = false; }});
  }}
}});

document.getElementById('case-sensitive').addEventListener('change', function() {{
  document.getElementById('search').dispatchEvent(new Event('input'));
  localStorage.setItem('caseSensitive', this.checked);
}});

// ─── Persist search state ──────────────────────────────────────────────────
function loadSearchState() {{
  const saved = localStorage.getItem('lastSearch');
  if(saved) document.getElementById('search').value = saved;
  const caseSens = localStorage.getItem('caseSensitive') === 'true';
  if(caseSens) document.getElementById('case-sensitive').checked = true;
}}
document.getElementById('search').addEventListener('input', function() {{
  localStorage.setItem('lastSearch', this.value);
}});
loadSearchState();

// ─── Grouping ──────────────────────────────────────────────────────────────
function applyGrouping(mode) {{
  var tree = document.getElementById('tree-container');
  var grouped = document.getElementById('grouped');
  if(mode === 'none') {{
    grouped.style.display='none'; tree.style.display=''; return;
  }}
  tree.style.display='none'; grouped.style.display='';
  grouped.innerHTML = '';
  var groups = {{}};
  Array.from(document.querySelectorAll('.clickable'))
    .filter(function(s) {{ return s.offsetParent !== null; }})
    .forEach(function(s) {{
      var key = mode === 'type'
        ? (s.classList.contains('dir') ? '[DIR]' : '.' + s.getAttribute('data-path').split('.').pop())
        : s.textContent.split('_')[0];
      if (!groups[key]) groups[key] = [];
      groups[key].push(s);
    }});
  Object.entries(groups).forEach(function([key,items]) {{
    var h = document.createElement('h3'); h.textContent = key; grouped.appendChild(h);
    items.forEach(function(s) {{
      var div = document.createElement('div');
      div.className = 'tree-line';
      div.appendChild(s.cloneNode(true));
      grouped.appendChild(div);
    }});
  }});
}}

document.getElementById('grouping').value = "{group}";
applyGrouping("{group}");
document.getElementById('grouping').addEventListener('change', function(e) {{ applyGrouping(e.target.value); }});

document.getElementById('expand-all').onclick = function() {{
  document.querySelectorAll('details').forEach(function(d) {{ d.open = true; }});
  localStorage.setItem('expandState', 'all');
}};
document.getElementById('collapse-all').onclick = function() {{
  document.querySelectorAll('details').forEach(function(d) {{ d.open = false; }});
  localStorage.setItem('expandState', 'none');
}};

document.getElementById('print').onclick = function() {{
  window.print();
}};

document.getElementById('export').onclick = function() {{
  var list = Array.from(document.querySelectorAll('.clickable'))
    .filter(function(s) {{ return s.offsetParent !== null; }})
    .map(function(s) {{ return {{ path: s.getAttribute('data-path'), type: s.classList.contains('dir') ? 'dir' : 'file', size: s.getAttribute('data-size'), mtime: s.getAttribute('data-mtime') }}; }});
  var blob = new Blob([JSON.stringify(list,null,2)], {{ type: 'application/json' }});
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a'); a.href = url; a.download = 'tree_export.json'; a.click();
  URL.revokeObjectURL(url);
}};

document.querySelectorAll('.clickable').forEach(function(s) {{
  s.addEventListener('click', function(e) {{
    var path = s.getAttribute('data-path');
    if (navigator.clipboard) {{
      navigator.clipboard.writeText(path);
    }} else {{
      var temp = document.createElement('textarea');
      temp.value = path;
      document.body.appendChild(temp);
      temp.select();
      document.execCommand('copy');
      document.body.removeChild(temp);
    }}
    var tooltip = document.getElementById('copied-tooltip');
    tooltip.style.display = 'block'; setTimeout(function() {{ tooltip.style.display = 'none'; }}, 800);
    e.stopPropagation();
  }});
}});

document.querySelectorAll('.clickable').forEach(function(s) {{
  s.addEventListener('mouseover', function() {{ document.getElementById('breadcrumb').textContent = 'Path: ' + s.getAttribute('data-path'); }});
}});

// ─── Tab Navigation ───────────────────────────────────────────────────────
document.querySelectorAll('.tab-button').forEach(function(btn) {{
  btn.addEventListener('click', function() {{
    const tabId = this.getAttribute('data-tab');
    
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(function(tab) {{
      tab.classList.remove('active');
    }});
    
    // Remove active from all buttons
    document.querySelectorAll('.tab-button').forEach(function(b) {{
      b.classList.remove('active');
    }});
    
    // Show selected tab
    document.getElementById(tabId).classList.add('active');
    this.classList.add('active');
    
    // Initialize charts when analytics tab becomes visible
    if (tabId === 'analytics-tab' && !chartsInitialized) {{
      setTimeout(function() {{ initializeCharts(); }}, 100);
    }}
  }});
}});

// ─── Initialize KPI Cards ─────────────────────────────────────────────────
function initializeKPIs() {{
  const kpis = analyticsData.kpis;
  const container = document.getElementById('kpi-container');
  
  const kpiCards = [
    {{ label: 'Total Size', value: kpis.total_size_human }},
    {{ label: 'Total Files', value: kpis.total_files }},
    {{ label: 'Total Dirs', value: kpis.total_dirs }},
    {{ label: 'Largest File', value: kpis.largest_file.size_human }},
    {{ label: 'Last Modified', value: kpis.most_recent.split(' ')[0] }},
    {{ label: 'Oldest File', value: kpis.oldest_file.split(' ')[0] }}
  ];
  
  container.innerHTML = kpiCards.map(card => `
    <div class="kpi-card">
      <div class="kpi-value">${{card.value}}</div>
      <div class="kpi-label">${{card.label}}</div>
    </div>
  `).join('');
}}

// ─── Initialize self-contained analytics charts ───────────────────────────
var chartsInitialized = false;
function initializeCharts() {{
  if (chartsInitialized) return;
  chartsInitialized = true;
  function empty(id, message) {{ document.getElementById(id).innerHTML = '<div class="analytics-empty">' + message + '</div>'; }}
  function renderTopFiles() {{
    var container = document.getElementById('top-files-chart');
    var files = analyticsData.top_files.slice(0, 15);
    if (!files.length) {{ empty('top-files-chart', 'No files match the current filters.'); return; }}
    var max = Math.max.apply(null, files.map(function(file) {{ return file.size; }})) || 1;
    container.innerHTML = '<div class="bar-chart">' + files.map(function(file) {{
      var label = file.name.length > 12 ? file.name.substring(0, 12) + '...' : file.name;
      var height = Math.max(2, file.size / max * 100);
      return '<div class="bar-item" title="' + file.path.replace(/"/g, '&quot;') + '\\n' + file.size_human + '"><span class="bar-value">' + file.size_human + '</span><div class="bar" style="height:' + height + '%"></div><span class="bar-label">' + label + '</span></div>';
    }}).join('') + '</div>';
  }}
  function renderFileTypes(metric) {{
    var container = document.getElementById('file-types-chart');
    var types = analyticsData.file_types.slice(0, 8);
    if (!types.length) {{ empty('file-types-chart', 'No file types to display.'); return; }}
    var values = types.map(function(item) {{ return metric === 'count' ? item.count : item.size; }});
    var max = Math.max.apply(null, values) || 1;
    container.innerHTML = '<div class="type-list">' + types.map(function(item, index) {{
      var value = values[index];
      var label = metric === 'count' ? value + ' files' : item.size_human;
      return '<div class="type-row"><span>' + (item.type || 'no-ext') + '</span><span class="type-track"><span class="type-fill" style="display:block;width:' + (value / max * 100) + '%"></span></span><span>' + label + '</span></div>';
    }}).join('') + '</div>';
  }}
  function renderTreemap() {{
    var container = document.getElementById('treemap-chart');
    var children = (analyticsData.treemap && analyticsData.treemap.children) || [];
    children = children.sort(function(a, b) {{ return b.size - a.size; }}).slice(0, 20);
    if (!children.length) {{ empty('treemap-chart', 'No folders or files to display.'); return; }}
    container.innerHTML = '<div class="treemap">' + children.map(function(item) {{
      return '<div class="treemap-item" title="' + item.path.replace(/"/g, '&quot;') + '">' + item.name + '<br><small>' + humanSize(item.size) + '</small></div>';
    }}).join('') + '</div>';
  }}
  function humanSize(bytes) {{
    var units = ['B', 'KB', 'MB', 'GB', 'TB']; var value = Number(bytes) || 0; var index = 0;
    while (value >= 1024 && index < units.length - 1) {{ value /= 1024; index++; }}
    return value.toFixed(2) + ' ' + units[index];
  }}
  renderTopFiles();
  renderFileTypes('size');
  renderTreemap();
  var typeMetricSelect = document.getElementById('type-metric');
  if (typeMetricSelect) typeMetricSelect.addEventListener('change', function(e) {{ renderFileTypes(e.target.value); }});
}}

// Initialize KPIs on load
initializeKPIs();
initializeCharts();
</script>
</body>
</html>"""
    return html_page

def main():
    """Run LSW through the installed console command."""
    import runpy
    runpy.run_path(__file__, run_name="__main__")

def generate_output(base, output_type, out_file, exts=None, group="none", ignore_dirs=None, ignore_patterns=None, ignore_regex=None, include_dirs=None, include_patterns=None, include_regex=None, max_depth=None, min_size=None, max_size=None, after_date=None, before_date=None, no_browser=False, txt_icons=False):
    """Generate one output format using the same paths as the CLI and GUI."""
    if output_type == "txt":
      out_file = out_file if out_file.lower().endswith(".txt") else os.path.splitext(out_file)[0] + ".txt"
      content = ".\n" + generate_text_tree(
        base, ignore_dirs=ignore_dirs, ignore_patterns=ignore_patterns,
        ignore_regex=ignore_regex, include_dirs=include_dirs,
        include_patterns=include_patterns, include_regex=include_regex,
        max_depth=max_depth, min_size=min_size, max_size=max_size,
        after_date=after_date, before_date=before_date, show_icons=txt_icons,
      )
      with open(out_file, "w", encoding="utf-8") as output:
        output.write(content)
    elif output_type in ["csv", "json", "jsonl", "markdown"]:
      items = collect_tree_items(
        base, ignore_dirs=ignore_dirs, ignore_patterns=ignore_patterns,
        ignore_regex=ignore_regex, include_dirs=include_dirs,
        include_patterns=include_patterns, include_regex=include_regex,
        max_depth=max_depth, exts=exts, min_size=min_size, max_size=max_size,
        after_date=after_date, before_date=before_date,
      )
      suffixes = {"csv": ".csv", "json": ".json", "jsonl": ".jsonl", "markdown": ".md"}
      suffix = suffixes[output_type]
      out_file = out_file if out_file.lower().endswith(suffix) else os.path.splitext(out_file)[0] + suffix
      exporters = {"csv": export_csv, "json": export_json, "jsonl": export_jsonl, "markdown": export_markdown}
      exporters[output_type](items, out_file)
    else:
      html_content = build_html_report(
        base, exts, group, ignore_dirs=ignore_dirs, ignore_patterns=ignore_patterns,
        ignore_regex=ignore_regex, include_dirs=include_dirs,
        include_patterns=include_patterns, include_regex=include_regex,
        max_depth=max_depth, min_size=min_size, max_size=max_size,
        after_date=after_date, before_date=before_date,
      )
      out_file = out_file if out_file.lower().endswith(".html") else os.path.splitext(out_file)[0] + ".html"
      with open(out_file, "w", encoding="utf-8") as output:
        output.write(html_content)
      if not no_browser:
        webbrowser.open(out_file)
    return out_file

def run_gui(script_dir: str, config: dict):
    """Run the Flet one-shot launcher window."""
    try:
      import flet as ft
    except ImportError:
      safe_print("❌ Flet is missing from this installation. Reinstall lsw-directory-walker with pip.")
      return

    def split_values(value):
      values = [item.strip() for item in value.split(",") if item.strip()]
      return values or None

    def main(page: ft.Page):
      page.title = "LSW"
      page.theme_mode = ft.ThemeMode.DARK
      page.padding = 0
      page.bgcolor = "#0f172a"
      web_preview = os.environ.get("LSW_GUI_WEB") == "1"
      if web_preview:
        page.width = 1000
        page.height = 1400
      else:
        page.window.width = 760
        page.window.height = 820
        page.window.min_width = 620
        page.window.min_height = 640

      accent = "#38bdf8"
      muted = "#94a3b8"
      panel = "#172033"

      path_field = ft.TextField(value=os.path.abspath("."), label="Folder to scan", expand=True)
      output_field = ft.TextField(value="tree_output.html", label="Output file", expand=True)
      ext_field = ft.TextField(label="Extensions", hint_text=".py,.js,.ts")
      ignore_field = ft.TextField(label="Ignore names", hint_text="node_modules,.git,__pycache__")
      include_field = ft.TextField(label="Include root folders", hint_text="src,tests")
      min_size_field = ft.TextField(label="Minimum size", hint_text="1MB", expand=True)
      max_size_field = ft.TextField(label="Maximum size", hint_text="10MB", expand=True)
      after_field = ft.TextField(label="Modified after", hint_text="YYYY-MM-DD", expand=True)
      before_field = ft.TextField(label="Modified before", hint_text="YYYY-MM-DD", expand=True)
      depth_field = ft.TextField(label="Max depth", hint_text="Unlimited", expand=True)
      workers_field = ft.TextField(value=str(config.get("parallel_workers", 4)), label="Workers", expand=True)
      ignore_pattern_field = ft.TextField(label="Ignore patterns", hint_text="*.min.js,*.tmp")
      ignore_regex_field = ft.TextField(label="Ignore regex", hint_text="^test_.*")
      include_pattern_field = ft.TextField(label="Include patterns", hint_text="*.py,*.js")
      include_regex_field = ft.TextField(label="Include regex", hint_text="^main.*")
      type_dropdown = ft.Dropdown(
        label="Output type",
        value=config.get("type", "html"),
        options=[ft.dropdown.Option(value) for value in ["html", "txt", "csv", "json", "jsonl", "markdown"]],
        expand=True,
      )
      group_dropdown = ft.Dropdown(
        label="HTML grouping",
        value="none",
        options=[ft.dropdown.Option(value) for value in ["none", "type", "prefix"]],
        expand=True,
      )
      no_browser = ft.Checkbox(label="Do not open browser", value=config.get("no_browser", False))
      txt_icons = ft.Checkbox(label="Show icons in TXT output")
      parallel = ft.Checkbox(label="Enable parallel mode", value=config.get("parallel", True))
      status = ft.Text("Ready to scan", color=muted, size=12)
      progress = ft.ProgressBar(visible=False, value=None, expand=True, color="#38bdf8", bgcolor="#334155")
      controls = []

      async def browse_folder(e):
        selected_path = await folder_picker.get_directory_path(
          "Select a folder to scan",
          initial_directory=path_field.value or os.path.abspath("."),
        )
        if selected_path:
          path_field.value = selected_path
          page.update()

      folder_picker = ft.FilePicker()
      page.services.append(folder_picker)
      browse_button = ft.IconButton(icon=ft.Icons.FOLDER_OPEN, tooltip="Choose folder", on_click=browse_folder)

      def set_status(message, color=muted):
        status.value = message
        status.color = color
        page.update()

      async def generate(e):
        base = path_field.value.strip()
        if not base or not os.path.isdir(base):
          set_status("Choose a valid folder first", "#f87171")
          return

        try:
          max_depth = int(depth_field.value) if depth_field.value.strip() else None
          workers = int(workers_field.value) if workers_field.value.strip() else 4
          min_size = parse_size(min_size_field.value) if min_size_field.value.strip() else None
          max_size = parse_size(max_size_field.value) if max_size_field.value.strip() else None
          after_date = parse_date(after_field.value) if after_field.value.strip() else None
          before_date = parse_date(before_field.value) if before_field.value.strip() else None
          if max_depth is not None and max_depth < 0:
            raise ValueError("Max depth cannot be negative")
          if workers < 1:
            raise ValueError("Workers must be at least 1")
        except ValueError as error:
          set_status(str(error), "#f87171")
          return

        lswignore_patterns, lswignore_regex = load_lswignore(script_dir, base)
        ignore_patterns = list(lswignore_patterns)
        ignore_patterns.extend(split_values(ignore_pattern_field.value) or [])
        ignore_regex = list(lswignore_regex)
        try:
          ignore_regex.extend([re.compile(pattern) for pattern in (split_values(ignore_regex_field.value) or [])])
          include_regex = [re.compile(pattern) for pattern in (split_values(include_regex_field.value) or [])]
        except re.error as error:
          set_status(f"Invalid regex: {error}", "#f87171")
          return

        ignore_dirs = set(split_values(ignore_field.value) or []) or None
        include_dirs = set(split_values(include_field.value) or []) or None
        include_patterns = split_values(include_pattern_field.value)
        exts = set(split_values(ext_field.value) or []) or None
        output_type = type_dropdown.value or "html"
        out_file = output_field.value.strip() or "tree_output.html"
        progress.visible = True
        controls_set_disabled(True)
        page.update()

        try:
          out_file = await asyncio.to_thread(
            generate_output, base, output_type, out_file, exts, group_dropdown.value or "none",
            ignore_dirs, ignore_patterns or None, ignore_regex or None, include_dirs,
            include_patterns, include_regex or None, max_depth, min_size, max_size,
            after_date, before_date, no_browser.value, txt_icons.value,
          )
          set_status(f"Saved {out_file}", "#4ade80")
          await asyncio.sleep(0.7)
          page.window.close()
        except (OSError, PermissionError, ValueError) as error:
          set_status(f"Could not generate output: {error}", "#f87171")
        finally:
          progress.visible = False
          controls_set_disabled(False)
          page.update()

      generate_button = ft.FilledButton("Generate", icon=ft.Icons.PLAY_ARROW, on_click=generate)
      controls.extend([
        path_field, output_field, ext_field, ignore_field, include_field, min_size_field,
        max_size_field, after_field, before_field, depth_field, workers_field,
        ignore_pattern_field, ignore_regex_field, include_pattern_field, include_regex_field,
        type_dropdown, group_dropdown, no_browser, txt_icons, parallel, browse_button, generate_button,
      ])

      def controls_set_disabled(disabled):
        for control in controls:
          control.disabled = disabled

      page.add(
        ft.Container(
          content=ft.Column([
            ft.Row([ft.Icon(ft.Icons.FOLDER_SPECIAL, color=accent, size=30), ft.Text("LSW", size=28, weight=ft.FontWeight.BOLD, color="#f8fafc")]),
            ft.Text("Directory scanner", color=muted),
            ft.Divider(color="#334155"),
            ft.Text("Location", size=16, weight=ft.FontWeight.BOLD, color="#f8fafc"),
            ft.Text("Choose the folder LSW should scan. The output is written where you specify below.", color=muted, size=12),
            ft.Row([path_field, browse_button]),
            ft.Row([type_dropdown, group_dropdown]),
            ft.Row([output_field]),
            ft.Text("Filters", size=16, weight=ft.FontWeight.BOLD, color="#f8fafc"),
            ft.Text("Filters apply while the tree is scanned. Ignore rules remove entries; include rules create a whitelist.", color=muted, size=12),
            ft.Row([ext_field, ignore_field]),
            ft.Row([include_field]),
            ft.Container(
              content=ft.Text("Include root folders changes the scan scope: root-level files are skipped and only the named folders are traversed. Nested folders inside them are still searched.", color="#bae6fd", size=12),
              bgcolor="#123047", border_radius=8, padding=12,
            ),
            ft.Row([min_size_field, max_size_field]),
            ft.Row([after_field, before_field]),
            ft.Container(
              content=ft.Column([
                ft.Text("Advanced", size=15, weight=ft.FontWeight.BOLD, color="#f8fafc"),
                ft.Text("Regex matches entry names. Depth limits recursion. Parallel settings are retained for compatibility but scanning is currently synchronous.", color=muted, size=12),
                ft.Row([depth_field, workers_field]),
                ft.Row([ignore_pattern_field, include_pattern_field]),
                ft.Row([ignore_regex_field, include_regex_field]),
                ft.Row([parallel, no_browser, txt_icons], wrap=True),
              ], spacing=10),
              bgcolor=panel,
              border_radius=12,
              padding=16,
            ),
            ft.Row([status], alignment=ft.MainAxisAlignment.START),
            ft.Row([progress], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([generate_button], alignment=ft.MainAxisAlignment.END),
          ], spacing=14, scroll=ft.ScrollMode.AUTO),
          padding=28,
          expand=True,
        )
      )

    view = ft.AppView.WEB_BROWSER if os.environ.get("LSW_GUI_WEB") == "1" else ft.AppView.FLET_APP
    ft.run(main, view=view, port=8550 if os.environ.get("LSW_GUI_WEB") == "1" else 0)

# ─── CLI entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Get script directory for config/preset loading
    script_dir = os.path.dirname(os.path.abspath(__file__))
    initialize_user_config(script_dir)
    
    # Load config defaults
    config = load_config(script_dir)
    
    # Setup argument parser
    parser = argparse.ArgumentParser(description="LSW: List Walker - generate directory trees and file inventories")
    parser.add_argument("--gui", action="store_true", help="Open the Flet graphical launcher")
    parser.add_argument("--path", default=".", help="Directory to scan")
    parser.add_argument("--preset", "-p", help=f"Load preset (available: {', '.join(get_available_presets(script_dir)) or 'none'})")
    parser.add_argument("--ext", help="Comma-separated extensions to include (e.g., '.py,.js')")
    parser.add_argument("--ignore", help="Comma-separated folder names to ignore (exact match)")
    parser.add_argument("--ignore-pattern", help="Comma-separated glob patterns to ignore (e.g., '*.cache,*.tmp')")
    parser.add_argument("--ignore-regex", help="Regex pattern to ignore paths (e.g., '^test_.*' or '.*\\.bak$')")
    parser.add_argument("--include", help="Comma-separated folder names to include only (exact match, whitelist)")
    parser.add_argument("--include-pattern", help="Comma-separated glob patterns to include only (e.g., 'src/*,test/*')")
    parser.add_argument("--include-regex", help="Regex pattern to include only paths (e.g., '^(src|lib)' )")
    parser.add_argument("--max-depth", type=int, help="Maximum directory depth to traverse")
    parser.add_argument("--min-size", help="Minimum file size (e.g., '1MB', '500KB')")
    parser.add_argument("--max-size", help="Maximum file size (e.g., '10MB', '1GB')")
    parser.add_argument("--modified-after", help="Only files modified after date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--modified-before", help="Only files modified before date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--out", default="tree_output.html", help="Output file")
    parser.add_argument("--no-browser", action="store_true", default=config.get("no_browser", False), help="Skip opening browser for HTML output")
    parser.add_argument("--txt-icons", action="store_true", help="Show MIME icons in TXT output (disabled by default)")
    parser.add_argument("--group", choices=["none","type","prefix"], default="none",
                        help="HTML grouping: none, type, prefix")
    parser.add_argument("--type", choices=["html","txt","csv","json","jsonl","markdown"], 
                        default=config.get("type", "html"),
                        help="Output type: html (default), txt, csv, json, jsonl, or markdown")
    parser.add_argument("--parallel", action="store_true", default=config.get("parallel", True),
                        help="Enable parallel directory scanning (default: enabled)")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel directory scanning")
    parser.add_argument("--workers", type=int, default=config.get("parallel_workers", 4),
                        help="Number of parallel workers (default: 4)")
    
    args = parser.parse_args()

    if args.gui:
      run_gui(script_dir, config)
      sys.exit(0)
    
    # Load preset if specified
    if args.preset:
        try:
            preset_args = load_preset(args.preset, script_dir)
            # Apply preset arguments (CLI args override preset)
            for key, value in preset_args.items():
                if not hasattr(args, key) or getattr(args, key) is None:
                    setattr(args, key, value)
            safe_print(f"✅ Loaded preset: {args.preset}")
        except (FileNotFoundError, ValueError) as e:
            safe_print(f"❌ {e}")
            exit(1)

    base = args.path
    exts = {e.strip() for e in args.ext.split(",")} if args.ext else None
    ignore_dirs = {d.strip() for d in args.ignore.split(",")} if args.ignore else None
    
    # Load patterns from .lswignore
    lswignore_patterns, lswignore_regex = load_lswignore(script_dir, base)
    
    # Parse ignore patterns (combine .lswignore with CLI args)
    ignore_patterns = list(lswignore_patterns) if lswignore_patterns else []
    if args.ignore_pattern:
        ignore_patterns.extend([p.strip() for p in args.ignore_pattern.split(",")])
    ignore_patterns = ignore_patterns if ignore_patterns else None
    
    # Parse ignore regex (combine .lswignore with CLI args)
    ignore_regex = list(lswignore_regex) if lswignore_regex else []
    if args.ignore_regex:
        try:
            ignore_regex.extend([re.compile(pattern.strip()) for pattern in args.ignore_regex.split(",")])
        except re.error as e:
            safe_print(f"❌ Invalid regex pattern: {e}")
            exit(1)
    ignore_regex = ignore_regex if ignore_regex else None
    
    # Parse include patterns (whitelist)
    include_dirs = {d.strip() for d in args.include.split(",")} if args.include else None
    include_patterns = None
    if args.include_pattern:
        include_patterns = [p.strip() for p in args.include_pattern.split(",")]
    
    # Parse include regex (whitelist)
    include_regex = None
    if args.include_regex:
        try:
            include_regex = [re.compile(pattern.strip()) for pattern in args.include_regex.split(",")]
        except re.error as e:
            safe_print(f"❌ Invalid include regex pattern: {e}")
            exit(1)
    
    max_depth = args.max_depth
    
    # Parse size filters
    min_size = parse_size(args.min_size) if args.min_size else None
    max_size = parse_size(args.max_size) if args.max_size else None
    
    # Parse date filters
    after_date = None
    before_date = None
    try:
        if args.modified_after:
            after_date = parse_date(args.modified_after)
        if args.modified_before:
            before_date = parse_date(args.modified_before)
    except ValueError as e:
        safe_print(f"❌ {e}")
        exit(1)

    if args.type == "txt":
        out_file = args.out if args.out.lower().endswith(".txt") else os.path.splitext(args.out)[0] + ".txt"
        txt_content = ".\n" + generate_text_tree(base, ignore_dirs=ignore_dirs, ignore_patterns=ignore_patterns, ignore_regex=ignore_regex, include_dirs=include_dirs, include_patterns=include_patterns, include_regex=include_regex, max_depth=max_depth, min_size=min_size, max_size=max_size, after_date=after_date, before_date=before_date, show_icons=args.txt_icons)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(txt_content)
        safe_print(f"✅ Tree output saved to {out_file}")
    elif args.type in ["csv", "json", "jsonl", "markdown"]:
        items = collect_tree_items(base, ignore_dirs=ignore_dirs, ignore_patterns=ignore_patterns, ignore_regex=ignore_regex, include_dirs=include_dirs, include_patterns=include_patterns, include_regex=include_regex, max_depth=max_depth, exts=exts, min_size=min_size, max_size=max_size, after_date=after_date, before_date=before_date)
        
        if args.type == "csv":
            out_file = args.out if args.out.lower().endswith(".csv") else os.path.splitext(args.out)[0] + ".csv"
            export_csv(items, out_file)
        elif args.type == "json":
            out_file = args.out if args.out.lower().endswith(".json") else os.path.splitext(args.out)[0] + ".json"
            export_json(items, out_file)
        elif args.type == "jsonl":
            out_file = args.out if args.out.lower().endswith(".jsonl") else os.path.splitext(args.out)[0] + ".jsonl"
            export_jsonl(items, out_file)
        elif args.type == "markdown":
            out_file = args.out if args.out.lower().endswith(".md") else os.path.splitext(args.out)[0] + ".md"
            export_markdown(items, out_file)
    else:
        html_content = build_html_report(base, exts, args.group, ignore_dirs=ignore_dirs, ignore_patterns=ignore_patterns, ignore_regex=ignore_regex, include_dirs=include_dirs, include_patterns=include_patterns, include_regex=include_regex, max_depth=max_depth, min_size=min_size, max_size=max_size, after_date=after_date, before_date=before_date)
        out_file = args.out if args.out.lower().endswith(".html") else os.path.splitext(args.out)[0] + ".html"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        safe_print(f"✅ Tree output saved to {out_file}")
        if not args.no_browser:
            webbrowser.open(out_file)

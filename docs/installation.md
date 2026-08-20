# Installation

LSW: List Walker is published on PyPI as `lsw-directory-walker`.

## Install from PyPI

```powershell
py -m pip install lsw-directory-walker
```

The package installs the `lsw` command and its Flet GUI dependency together. No separate GUI installation is required.

Verify the installation:

```powershell
lsw --help
```

Run the command-line scanner:

```powershell
lsw --path .
```

Open the graphical launcher:

```powershell
lsw --gui
```

The command is CLI-first. Running `lsw` without `--gui` does not open a window.

## First run

The first run creates an editable user configuration directory:

```text
Windows: %APPDATA%\\lsw\\
Other systems: $XDG_CONFIG_HOME/lsw/ or ~/.config/lsw/
```

It contains:

```text
lsw-config.json
.lswignore
lsw-presets/
```

Existing files are never overwritten. These settings and presets can be reused while scanning folders anywhere on the system.

## Install from the repository

For development or to use the latest unreleased source:

```powershell
git clone https://github.com/FinickySpider/lsw-directory-walker.git
Set-Location lsw-directory-walker
py -m pip install .
```

## Upgrade

```powershell
py -m pip install --upgrade lsw-directory-walker
```

Your user configuration under `%APPDATA%\\lsw` is not removed or overwritten during upgrades.

## Uninstall

```powershell
py -m pip uninstall lsw-directory-walker
```

Uninstalling the package does not remove your user configuration. To remove it manually on Windows:

```powershell
Remove-Item "$env:APPDATA\\lsw" -Recurse -Force
```

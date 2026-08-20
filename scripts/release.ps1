[CmdletBinding(SupportsShouldProcess)]
param(
    [ValidateSet('patch', 'minor', 'major')]
    [string]$Bump,
    [string]$Version,
    [switch]$SkipPush,
    [switch]$SkipRelease
)

$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $false)][string[]]$Arguments = @(),
        [Parameter(Mandatory = $true)][string]$Description
    )

    Write-Host "`n==> $Description" -ForegroundColor Cyan
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Get-ProjectVersion {
    $match = Select-String -Path 'pyproject.toml' -Pattern '^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"\s*$'
    if (-not $match) {
        throw 'Could not find a MAJOR.MINOR.PATCH version in pyproject.toml.'
    }
    return [version]$match.Matches[0].Groups[0].Value.Split('"')[1]
}

function Get-NextVersion {
    param([version]$CurrentVersion, [string]$BumpKind)
    switch ($BumpKind) {
        'major' { return [version]::new($CurrentVersion.Major + 1, 0, 0) }
        'minor' { return [version]::new($CurrentVersion.Major, $CurrentVersion.Minor + 1, 0) }
        'patch' { return [version]::new($CurrentVersion.Major, $CurrentVersion.Minor, $CurrentVersion.Build + 1) }
    }
    throw "Unknown version bump: $BumpKind"
}

$current = Get-ProjectVersion
if (-not $Version -and -not $Bump) {
    Write-Host "Current version: $current" -ForegroundColor Yellow
    $choice = Read-Host 'Bump version: patch, minor, major, or enter an explicit version'
    if ($choice -match '^(patch|minor|major)$') {
        $Bump = $choice
    } else {
        $Version = $choice
    }
}

if ($Version) {
    if ($Version -notmatch '^\d+\.\d+\.\d+$') {
        throw 'Version must use MAJOR.MINOR.PATCH format, for example 0.1.1.'
    }
    $next = [version]$Version
} else {
    $next = Get-NextVersion $current $Bump
}

if ($next -le $current) {
    throw "New version $next must be greater than current version $current."
}

$tag = "v$next"
$status = @(git status --short)
if ($status.Count -gt 0) {
    Write-Host "`nUncommitted changes detected:" -ForegroundColor Yellow
    $status | ForEach-Object { Write-Host $_ }
    $continue = Read-Host 'Continue and include these changes in the release? (y/N)'
    if ($continue -notmatch '^(y|yes)$') {
        throw 'Release cancelled because the working tree is not clean.'
    }
}

Write-Host "`nRelease plan: $current -> $next ($tag)" -ForegroundColor Green
$confirm = Read-Host 'Run checks, commit, push, and create the GitHub Release? (y/N)'
if ($confirm -notmatch '^(y|yes)$') {
    throw 'Release cancelled.'
}

$replacement = "version = `"$next`""
$content = Get-Content 'pyproject.toml' -Raw
$content = [regex]::Replace($content, 'version\s*=\s*"\d+\.\d+\.\d+"', $replacement, 1)
Set-Content 'pyproject.toml' $content -NoNewline

try {
    Invoke-CheckedCommand 'python' @('-m', 'py_compile', 'lsw.py') 'Compile lsw.py'
    Invoke-CheckedCommand 'retype' @('build') 'Build Retype documentation'
    Invoke-CheckedCommand 'py' @('-m', 'build') 'Build Python distributions'
    $artifacts = @(Get-ChildItem 'dist' -File | Where-Object { $_.Extension -in @('.whl', '.gz') } | ForEach-Object { $_.FullName })
    if ($artifacts.Count -eq 0) {
        throw 'No wheel or source archive was created in dist.'
    }
    Invoke-CheckedCommand 'py' (@('-m', 'twine', 'check') + $artifacts) 'Validate package metadata'

    if (-not $SkipPush) {
        Invoke-CheckedCommand 'git' @('add', 'pyproject.toml', 'README.md', 'docs', 'lsw.py', 'scripts', '.github') 'Stage release files'
        Invoke-CheckedCommand 'git' @('commit', '-m', "release: $tag") 'Commit release'
        Invoke-CheckedCommand 'git' @('push', 'origin', 'main') 'Push release commit'
    }

    if (-not $SkipRelease) {
        if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
            throw 'GitHub CLI (gh) is required to create the release. Install it or rerun with -SkipRelease.'
        }
        Invoke-CheckedCommand 'gh' @('release', 'create', $tag, '--target', 'main', '--generate-notes', '--title', "LSW $tag") 'Create GitHub Release'
    }

    Write-Host "`nRelease $tag is ready. The GitHub publish workflow will build and publish it to PyPI." -ForegroundColor Green
}
catch {
    Write-Host "`nRelease failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "pyproject.toml was updated to $next. Review the working tree before retrying." -ForegroundColor Yellow
    exit 1
}

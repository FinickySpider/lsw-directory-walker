# Releasing LSW

The current public release is `0.1.0` on [PyPI](https://pypi.org/project/lsw-directory-walker/).

## One-time PyPI setup

The repository includes `.github/workflows/publish-pypi.yml`, which publishes through PyPI Trusted Publishing without storing an API token in GitHub.

Once the one-time Trusted Publishing setup is complete, the interactive release helper can run the whole local release sequence:

```powershell
.\scripts\release.ps1
```

It asks whether to make a patch, minor, major, or explicit version bump, then compiles the script, builds Retype, builds the Python distributions, validates the package metadata, commits the release, pushes `main`, and creates the GitHub Release. The GitHub Release triggers the PyPI workflow.

Run a local-only release preparation without pushing or creating a GitHub Release by using the skip switches. This still updates `pyproject.toml` and runs the build checks:

```powershell
.\scripts\release.ps1 -Bump patch -SkipPush -SkipRelease
```

After the workflow is pushed to GitHub:

1. Open PyPI and sign in.
2. Open **Account settings -> Publishing**.
3. Add a pending publisher.
4. Use these values:

```text
Owner: FinickySpider
Repository: lsw-directory-walker
Workflow name: publish-pypi.yml
Environment name: pypi
```

The `pypi` environment name must match the workflow configuration. The first successful workflow run creates or publishes the project through OpenID Connect.

## Release checklist

1. Update `version` in `pyproject.toml`.
2. Run the local checks:

```powershell
python -m py_compile lsw.py
retype build
py -m build
```

3. Review the generated package in `dist/`.
4. Commit and push the version change to `main`.
5. Create a GitHub Release with a tag matching the version, such as `v0.1.1`.
6. Publish the GitHub Release.
7. The `publish-pypi.yml` workflow builds the tag source and publishes it to PyPI.
8. Verify the package page and install the new version in a clean environment.

## Version rules

Every PyPI upload requires a version that does not already exist. Use:

- Patch releases for fixes, such as `0.1.1`.
- Minor releases for compatible features, such as `0.2.0`.
- Major releases for breaking changes, such as `1.0.0`.

## Manual fallback

If Trusted Publishing is not configured yet, publish manually with a PyPI token:

```powershell
py -m build
py -m twine check dist/*
py -m twine upload dist/*
```

Use `__token__` as the username and a PyPI API token as the password. Do not commit the token or place it in `pyproject.toml`.

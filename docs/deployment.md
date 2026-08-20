# Documentation Deployment

The Retype source files live in `docs/`, while Retype generates the publishable static website into `.retype/`.

## GitHub Pages setting

With the current project configuration, setting GitHub Pages to **Deploy from a branch -> `/docs` folder** is not correct. The `/docs` folder contains the Retype Markdown source, not the generated website. GitHub Pages would expose the source files rather than the finished Retype navigation and pages.

Use one of these approaches instead:

### Recommended: GitHub Actions

This repository includes `.github/workflows/retype-pages.yml`. Configure GitHub Pages to use **GitHub Actions**, then the workflow will build the site and deploy the `.retype/` directory automatically whenever changes are pushed to `main`. It can also be started manually from the Actions tab with **Run workflow**.

The workflow:

1. Checks out the repository.
2. Installs Node.js and the Retype CLI.
3. Runs `retype build`.
4. Uploads `.retype/` as the Pages artifact.
5. Deploys that artifact to the `github-pages` environment.

In the repository settings, open **Settings -> Pages** and set **Source** to **GitHub Actions**. Do not select **Deploy from a branch** with the `/docs` folder for this layout.

From a local checkout, the equivalent build is:

```powershell
retype build
```

The generated site is written to `.retype/`. The configured site URL is:

```text
https://finickyspider.github.io/lsw-directory-walker
```

Release history and package versions are maintained separately on the [GitHub Releases page](https://github.com/FinickySpider/lsw-directory-walker/releases) and [PyPI](https://pypi.org/project/lsw-directory-walker/).

### Manual deployment

If you do not use Actions, run `retype build`, then publish the contents of `.retype/` through a hosting service or copy those generated files into the branch/folder configured for GitHub Pages. Do not replace the Markdown source in `docs/` with generated files unless you intentionally change the Retype input/output layout.

## Local preview

Preview the documentation with:

```powershell
retype start
```

Build the static site with:

```powershell
retype build
```

Retype should report the generated output directory as `.retype/` and include all documentation pages and image assets.

## Workflow permissions

The workflow requests `contents: read`, `pages: write`, and `id-token: write`, which are the permissions required by the official GitHub Pages artifact and deployment actions. The repository does not need a personal access token or deployment secret for this setup.

# Documentation Deployment

The Retype source files live in `docs/`, while Retype generates the publishable static website into `.retype/`.

## GitHub Pages setting

With the current project configuration, setting GitHub Pages to **Deploy from a branch -> `/docs` folder** is not correct. The `/docs` folder contains the Retype Markdown source, not the generated website. GitHub Pages would expose the source files rather than the finished Retype navigation and pages.

Use one of these approaches instead:

### Recommended: GitHub Actions

Configure GitHub Pages to use **GitHub Actions**, then build the site and deploy the `.retype/` directory from a workflow. This keeps the Markdown source in `docs/` and publishes the generated output separately.

From a local checkout, the equivalent build is:

```powershell
retype build
```

The generated site is written to `.retype/`. The configured site URL is:

```text
https://finickyspider.github.io/lsw-directory-walker
```

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

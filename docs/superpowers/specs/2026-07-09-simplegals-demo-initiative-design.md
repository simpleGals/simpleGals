# simpleGals Demo / Portfolio Initiative: Design

Date: 2026-07-09
Status: approved (brainstorming), pending spec review
Owner: timlnx

## Goal

Stand up a public demo and portfolio site for simpleGals, hosted free on GitHub
Pages, that:

- Showcases real galleries built by the tool, including at least one custom
  template override.
- Rebuilds automatically against the newest published release, so the demo
  always reflects the current version.
- Keeps the git repo lean: only source originals live in version control, never
  the derived build output.
- Seeds a future "meta-gallery" (galleries of galleries) tool by defining a
  machine readable per-gallery data contract.

## Decisions locked during brainstorming

| Question | Decision |
|---|---|
| Hosting / URL | New free GitHub org `simplegals`; site at `https://simplegals.github.io/` |
| Move the tool repo into the org? | Yes. Transfer `timlnx/simpleGals` to `simplegals/simpleGals` |
| Built `out/` in git? | No. Build fresh in CI, deploy the Pages artifact. Only source originals committed |
| Landing page owner | A generator script in the site repo (`build_index.py`), not a tool feature |
| Cover metadata | Add a `cover` field to `simpleGal.json` and emit `out/gallery.json` per build |
| Build order | Ship simpleGals 0.3.1 first, then build the site against the real release |
| Version in promo string | Fold into 0.3.1 |

## Topology

The `simplegals` org holds two repositories:

- `simplegals/simpleGals` (transferred from `timlnx/simpleGals`): the tool.
- `simplegals/simplegals.github.io` (new): the demo and portfolio site.

GitHub sets up permanent redirects from the old URL for web, API, and git
remotes after the transfer, so existing clones keep working. The org website
repo must be named exactly `simplegals.github.io` to serve at the org root URL.

## Decomposition

This initiative is three sub-projects plus a deferred backlog. Each sub-project
gets its own spec, plan, and implementation cycle.

1. simpleGals 0.3.1 (tool feature). Detailed spec:
   `2026-07-09-simplegals-0.3.1-cover-manifest-design.md`. This is the critical
   path; the site depends on the `gallery.json` contract.
2. `simplegals.github.io` (the site). Overview below; detailed spec written when
   we start this sub-project.
3. Org creation, repo transfer, and PyPI trusted-publisher re-point (ops
   runbook). Overview below.

Backlog (deferred): inverted white on black theme. The promo version string and
always-on generator branding (meta generator plus top/bottom HTML comments) were
pulled forward into 0.3.1.

## Build sequence

0.3.1 first, then the site. The runbook (sub-project 3) can happen any time
before the PyPI launch, and ideally before finalizing the PyPI trusted publisher
so there is nothing to redo.

## Site architecture (overview, detailed later)

Source layout in `simplegals.github.io`:

```
galleries/<slug>/
   simpleGal.json      # title, cover, and site_url = https://simplegals.github.io/<slug>/
   in/*.jpg            # source originals (the only binaries in git)
build_index.py         # globs galleries/*/out/gallery.json -> renders index.html
templates/index.html.j2
.github/workflows/pages.yml
```

Deployment uses the GitHub Actions Pages artifact flow (no `gh-pages` branch, no
Jekyll, no `.nojekyll`). `pages.yml`:

- Triggers on `push` to `main` (a gallery was edited), `workflow_dispatch`
  (manual), and `repository_dispatch` (a new release; see runbook).
- Steps: checkout, setup-python, `pip install simplegals` (latest from PyPI; the
  first build before the PyPI launch installs from git), run `simplegals --force`
  in each `galleries/*/`, run `build_index.py` to assemble `index.html` plus each
  gallery's `out/` into a single site root, `upload-pages-artifact`,
  `deploy-pages`.

`build_index.py` consumes only `gallery.json`, never simpleGals output naming.
It is the seed of the future meta-gallery tool.

Per-gallery `site_url` must be set to the deployed sub-path
(`https://simplegals.github.io/<slug>/`) so OG image and URL tags resolve
correctly. simpleGals page links are relative, so serving each gallery under a
sub-path works.

## Runbook (overview, ops, mostly manual)

Ordered so there is no rework:

1. Create the free `simplegals` GitHub org.
2. Transfer `timlnx/simpleGals` into the org.
3. Update the PyPI trusted publisher to `simplegals/simpleGals`. The publish
   workflow uses OIDC trusted publishing pinned to `owner/repo`; the next
   publish fails until this is updated.
4. Allow GitHub Actions on the org (new orgs may default to disabled or
   approval required); re-enable CodeQL at the org level.
5. Create the `simplegals/simplegals.github.io` repo.
6. Add a fine-grained PAT (Contents: write on the site repo) as a secret in the
   tool repo, for the cross-repo `repository_dispatch`. A GitHub App token is
   the later hardening.

## Cross-repo release trigger

`GITHUB_TOKEN` cannot trigger workflows in another repo, so the tool repo's
release workflow sends a `repository_dispatch` to the site repo using the
fine-grained PAT above. Net effect: publish 0.3.1 to PyPI, dispatch, site
rebuilds with the newest simpleGals.

## Risks and notes

- PyPI trusted publisher re-point is the one real gotcha of the transfer. Doing
  it before the launch avoids a failed publish.
- First site build before the PyPI launch installs simpleGals from git.
- Correct OG tags require per-gallery `site_url`.
- Only source originals are committed; all derived output is regenerated in CI.

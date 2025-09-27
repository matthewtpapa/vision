# Archived CI workflows

These GitHub Actions were retired because their checks are now covered by `verify`
and `Docs Drift Check`:

- `.github/workflows/pre_s1_check.yml`
- `.github/workflows/s1.yml`
- `.github/workflows/s2.yml`
- `.github/workflows/sot_check.yml`

If you need to inspect historical runs, use the Actions tab and filter by the
workflow name; history is preserved in GitHub.

> Note: if any downstream automation referenced these workflow names via
> `workflow_run`, update it to listen to `verify` instead.

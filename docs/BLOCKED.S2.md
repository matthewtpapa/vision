# Stage S2 signing blocked

The `SOT_DEV_SIGNING_KEY` secret is unavailable in this environment, so the refreshed `artifacts/manifest.json` cannot be signed for S2.
Run the following command once the secret is provisioned:

```bash
python scripts/sign_json.py artifacts/manifest.json
```

## Required branch protection update blocked

Attempted to add the required status check `SoT-Check (S2)` to the `main` branch with:

```bash
gh api repos/<org>/<repo>/branches/main/protection --method PATCH --field required_status_checks.strict=true --field required_status_checks.contexts[]=SoT-Check\ (S2)
```

The GitHub CLI (`gh`) is not installed in this environment (`bash: command not found: gh`), so the branch protection update could not be performed. Configure the protection rule manually once sufficient permissions and tooling are available.

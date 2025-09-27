# Stage S1 signing blocked

The `SOT_DEV_SIGNING_KEY` secret is not available in this environment, so `artifacts/manifest.json` cannot be signed locally.
Run the following command once the secret is configured:

```bash
python scripts/sign_json.py artifacts/manifest.json
```

## Branch protection configuration blocked

Attempted to configure branch protection on `main` with the following settings so the SoT gate can be enforced:

* Require pull request reviews
* Require review from Code Owners
* Require the status check `SoT-Check (S1)`

The GitHub API responded with `403 Resource not accessible by integration` because this environment does not have administrative access to modify branch protection. The CODEOWNERS entries for the SoT surfaces have been updated in-repo as required:

```
/docs/vision_v1_single_source_of_truth.md   @yourorg/pm-team @yourorg/eng-leads
/docs/Vision_v1_Investor_SoT.html          @yourorg/pm-team @yourorg/eng-leads
/roadmap.yaml                               @yourorg/pm-team @yourorg/eng-leads
/roadmap.lock.json                          @yourorg/pm-team @yourorg/eng-leads
/seeds.env                                  @yourorg/eng-leads
/schemas/**                                 @yourorg/eng-leads
/.github/workflows/**                        @yourorg/eng-leads @yourorg/qa
```

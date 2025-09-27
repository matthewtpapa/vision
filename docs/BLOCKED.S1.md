# Stage S1 signing blocked

The `SOT_DEV_SIGNING_KEY` secret is not available in this environment, so `artifacts/manifest.json` cannot be signed locally.
Run the following command once the secret is configured:

```bash
python scripts/sign_json.py artifacts/manifest.json
```

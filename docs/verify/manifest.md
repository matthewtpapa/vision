# Gallery Manifest

Fields:

- `source` (str): one of `manufacturer`, `wikimedia`, `retailer`
- `path` (str): relative path to the asset file
- `license` (str): license text or identifier
- `phash` (str): perceptual hash (hex)
- `label` (str): canonical label
- `lang` (str): BCP-47 language tag

Rule: `(label, phash)` pairs must be unique.

This seed uses a placeholder pHash computed as SHA-256 over file bytes; a true perceptual hash will replace it in a later milestone.

# Gallery Manifest

Fields:

- `source` (str): one of `manufacturer`, `wikimedia`, `retailer`
- `path` (str): relative path to the asset file
- `license` (str): license text or identifier
- `phash` (str): perceptual hash (hex, 64-bit DCT)
- `label` (str): canonical label
- `lang` (str): BCP-47 language tag

Rule: `(label, phash)` pairs must be unique.

pHash: 64-bit DCT perceptual hash

- Preprocess: grayscale → resize 32×32
- DCT: take 8×8 low-frequency block (exclude DC)
- Threshold by **median** of the 8×8 block (after excluding DC)
- Pack row-major; **LSB** corresponds to (0,0) of the 8×8 block (post-DC exclusion)
- Dedupe rule: Hamming distance ≤ 8 and same label → flagged as duplicate

Note: gallery audit will reject pairs with identical {label, pHash}.

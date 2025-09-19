# LabelBank Seed Data

Each line of `seed.jsonl` is a JSON object with:

- `label` (str): canonical phrase.
- `aliases` (list[str]): alternate spellings or multilingual variants.
- `p31` (str): type tag, currently `product_model` or `product_line`.
- `lang` (str): BCP-47 language code.

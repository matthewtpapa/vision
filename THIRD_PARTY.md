# Third-party Attributions

This project acknowledges the following third-party software, models, and datasets.
Items may be *referenced* by documentation or examples without being bundled.

> Nothing in this document changes the licenses of the upstream projects.
> Please consult the upstream links for the full terms.

---

## Libraries

- **FAISS (Facebook AI Similarity Search)**  
  License: MIT  
  Source: <https://github.com/facebookresearch/faiss>

- **NumPy**  
  License: BSD-3-Clause  
  Source: <https://github.com/numpy/numpy>

- **Pillow (PIL fork)**  
  License: HPND (Historical Permission Notice and Disclaimer) + exceptions  
  Source: <https://github.com/python-pillow/Pillow>  
  Notes: See repo for bundled library notices.

---

## Models / Algorithms (referenced)

- **CLIP** (Contrastive Language-Image Pretraining)  
  License: MIT (code) / see repo for weights terms  
  Source: <https://github.com/openai/CLIP>

- **ByteTrack** (multi-object tracking)  
  License: MIT  
  Source: <https://github.com/ifzhang/ByteTrack>

- **YOLO family** (object detection; various repos)  
  License: varies by implementation (e.g., AGPL-3.0 for Ultralytics YOLOv5)  
  Sources: <https://github.com/ultralytics/yolov5> , <https://github.com/ultralytics/ultralytics>

> Our current code includes *adapters/stubs* that are compatible with these
> algorithms; we do not redistribute their weights.

---

## Datasets (referenced)

- **COCO 2017** (Common Objects in Context)  
  License: CC BY 4.0  
  Source: <https://cocodataset.org/#home> , <https://github.com/cocodataset/cocoapi>  
  Notes: Redistribution of images may be restricted; our fixture builder  
  is designed to operate from user-provided downloads.

---

## Tooling / Docs

- **markdownlint-cli2**  
  License: MIT  
  Source: <https://github.com/DavidAnson/markdownlint-cli2>

---

### How to update this file

1. Add new entries when docs, examples, or code reference an external work.
2. Include: *name, license, source URL, and any relevant notes*.
3. If we start distributing binaries or weights, add the required license
   texts to `NOTICE` as appropriate.

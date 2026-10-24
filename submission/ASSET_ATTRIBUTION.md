# CampusNav Sentinel — Asset Attribution

## Open Source Dependencies

| Component | Version | License | Source |
|---|---|---|---|
| OpenCV | 5.0.0 | Apache License 2.0 | opencv.org |
| Ultralytics YOLOv8 | 8.3+ | AGPL-3.0 | github.com/ultralytics/ultralytics |
| PyTorch | 2.10.0 | BSD-3-Clause | pytorch.org |
| FastAPI | 0.115+ | MIT License | github.com/fastapi/fastapi |
| Uvicorn | 0.30+ | BSD-3-Clause | github.com/encode/uvicorn |
| NumPy | 2.5+ | BSD-3-Clause | numpy.org |
| Jinja2 | 3.1+ | BSD-3-Clause | github.com/pallets/jinja |
| python-multipart | 0.0.9+ | Apache License 2.0 | github.com/Kludex/python-multipart |
| aiofiles | 24.1+ | Apache License 2.0 | github.com/Tinche/aiofiles |
| pytest | 8.3+ | MIT License | pytest.org |

## Pretrained Model Weights

| Model | Dataset | License | Notes |
|---|---|---|---|
| YOLOv8n | COCO (train2017) | AGPL-3.0 (Ultralytics) | Pretrained weights downloaded automatically on first run. No fine-tuning performed. |

## Dataset

| Dataset | License | Usage |
|---|---|---|
| COCO 2017 | CC BY 4.0 | YOLOv8n pretrained weights were trained on this dataset by Ultralytics. We did not download or use the dataset directly. |

## Synthetic Test Data

The test video (`data/sample/test_campus.mp4`) is generated programmatically by `scripts/generate_test_video.py` using OpenCV drawing functions. It contains no real-world footage, no identifiable persons, and no copyrighted material.

## License Note

This project uses Ultralytics YOLOv8 under AGPL-3.0. Per AGPL-3.0 requirements, if this software is distributed or made available as a network service, the complete source code must be made available. For competition evaluation purposes, the full source is included in the submission repository.

## No Third-Party Data

- No real campus footage was used
- No images of identifiable persons were used
- No proprietary datasets were accessed
- No third-party APIs were called (no LLM, no cloud vision API)

# Security Policy

## Scope

CampusNav Sentinel is a **research prototype**. It processes recorded or synthetic video footage for demonstration purposes. It does not control any real vehicle.

## Boundaries

- All stop/slow-down actions are **simulated outputs only**. No physical steering, braking, or vehicle control is connected.
- Uploaded files are stored in a local temporary directory and not forwarded to third parties unless AWS integration is explicitly enabled.
- No credentials, API keys, or personally identifiable information are logged or committed to the repository.
- Debug traces do not contain secret material.

## Input Validation

- File uploads are capped at 100 MB.
- Only video and image file extensions are accepted (.mp4, .avi, .mov, .mkv, .webm, .jpg, .jpeg, .png, .bmp).
- Uploaded files are never executed. They are read as media by OpenCV.
- Path traversal is prevented by generating unique job IDs for output directories.

## Dependencies

- OpenCV 5.0.0 (Apache 2.0)
- YOLOv8n via Ultralytics (AGPL-3.0 for the library; model weights are COCO-pretrained)
- PyTorch (BSD)
- FastAPI (MIT)

## Responsible Use

- Do not use identifiable footage of real people without consent.
- Do not deploy this system to control real vehicles.
- Do not trust detection outputs for safety-critical decisions without independent validation.

## Reporting

If you find a security issue, contact the project maintainer directly.

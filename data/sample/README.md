# Sample Test Data

This directory is for test videos/images used to demonstrate CampusNav Sentinel.

## Quick Start - Generate Test Video

The repository includes a script to generate synthetic test data:

```bash
python scripts/generate_test_video.py --output data/sample/test_campus.mp4 --duration 10
```

This creates a 10-second test video with synthetic pedestrians and vehicles.

## Using Your Own Data

You can also use your own video or image files:

```bash
# Video formats supported: .mp4, .avi, .mov, .mkv, .webm
# Image formats supported: .jpg, .jpeg, .png, .bmp

# Place your file here:
cp /path/to/your/video.mp4 data/sample/

# Then run:
PYTHONPATH=. python app/cli.py data/sample/your_video.mp4 -o data/output
```

## Public Datasets (Optional)

For more realistic testing, you can download from public datasets:

1. **Oxford RobotCar Dataset** (pedestrian scenes)
   - https://robotcar-dataset.robots.ox.ac.uk/

2. **KITTI Dataset** (urban driving)
   - http://www.cvlibs.net/datasets/kitti/

3. **nuScenes** (autonomous driving)
   - https://www.nuscenes.org/

4. **BDD100K** (diverse driving scenarios)
   - https://bdd-data.berkeley.edu/

## Why Not Included?

Video files are excluded from the repository because:
- They are too large for Git (typically 5-50 MB each)
- The synthetic generator creates adequate test data
- Users may want to test with their own footage
- Public datasets are freely available

## File Size Guidelines

If adding test files:
- Keep videos under 10 seconds
- Use compressed formats (H.264)
- Target < 2 MB per file
- For GitHub: consider Git LFS for larger files

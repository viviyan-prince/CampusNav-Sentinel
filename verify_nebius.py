#!/usr/bin/env python3
"""Quick verification script for Nebius integration."""

import sys
import os

def main():
    print("=" * 60)
    print("CAMPUSNAV SENTINEL - NEBIUS INTEGRATION VERIFICATION")
    print("=" * 60)
    print()

    # Check Python version
    print(f"[OK] Python {sys.version.split()[0]}")

    # Check OpenCV
    try:
        import cv2
        print(f"[OK] OpenCV {cv2.__version__}")
        if not cv2.__version__.startswith("5.0"):
            print("  [WARN] Expected OpenCV 5.0.x")
    except ImportError:
        print("[FAIL] OpenCV not installed")
        return 1

    # Check PyTorch
    try:
        import torch
        print(f"[OK] PyTorch {torch.__version__}")
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            print(f"  [OK] CUDA available: {torch.cuda.get_device_name(0)}")
        else:
            print("  [WARN] CUDA not available (will use CPU)")
    except ImportError:
        print("[FAIL] PyTorch not installed")
        return 1

    # Check Ultralytics
    try:
        import ultralytics
        print(f"[OK] Ultralytics installed")
    except ImportError:
        print("[FAIL] Ultralytics not installed")
        return 1

    # Check OpenAI SDK
    try:
        import openai
        print(f"[OK] OpenAI SDK {openai.__version__}")
    except ImportError:
        print("[FAIL] OpenAI SDK not installed (required for Nebius)")
        print("  Run: pip install openai")
        return 1

    # Check FastAPI
    try:
        import fastapi
        print(f"[OK] FastAPI {fastapi.__version__}")
    except ImportError:
        print("[FAIL] FastAPI not installed")
        return 1

    print()
    print("-" * 60)
    print("NEBIUS CONFIGURATION")
    print("-" * 60)

    # Check Nebius API key
    api_key = os.getenv("NEBIUS_API_KEY")
    if api_key:
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"[OK] NEBIUS_API_KEY: {masked_key}")
    else:
        print("[WARN] NEBIUS_API_KEY not set")
        print("  System will work in fallback mode (CV detection only)")
        print("  To enable Nebius AI:")
        print("    export NEBIUS_API_KEY=your_key_here")

    model = os.getenv("NEBIUS_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
    print(f"  Model: {model}")

    enabled = os.getenv("NEBIUS_ENABLED", "true").lower() == "true"
    print(f"  Enabled: {enabled}")

    interval = int(os.getenv("NEBIUS_INTERVAL", "5"))
    print(f"  Interval: every {interval} frame(s)")

    print()
    print("-" * 60)
    print("QUICK TEST")
    print("-" * 60)

    # Import Nebius client
    try:
        from app.nebius_client import NebiusClient
        client = NebiusClient()

        if client.enabled:
            print("[OK] Nebius client initialized")
            print(f"  Base URL: {client.base_url}")
            print(f"  Model: {client.model}")
            print()
            print("Testing API connection...")

            # Test with simple detection
            test_detections = [
                {"class": "person", "confidence": 0.85, "x": 320, "y": 400}
            ]
            test_metadata = {
                "frame_index": 0,
                "timestamp_ms": 0.0,
                "hazard_state": "CLEAR",
                "hazard_score": 0.0,
            }

            result = client.analyze_scene(test_detections, test_metadata)

            if result.success:
                print("[OK] Nebius API test PASSED")
                print(f"  Scene: {result.scene_description[:60]}...")
                print(f"  Risk: {result.risk_assessment[:50]}")
                print(f"  Action: {result.recommendations[:55]}...")
            else:
                print("[FAIL] Nebius API test FAILED")
                print(f"  Error: {result.error}")
                return 1
        else:
            print("[WARN] Nebius client disabled (no API key)")
            print("  System will work in fallback mode")

    except Exception as e:
        print(f"[FAIL] Nebius client error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print()
    print("=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    print()

    if api_key:
        print("[OK] All checks passed. Ready to run with Nebius AI!")
        print()
        print("Run demo:")
        print("  PYTHONPATH=. python app/cli.py data/sample/test_campus.mp4 -o data/output --max-frames 30")
    else:
        print("[OK] Core system ready (fallback mode)")
        print()
        print("To enable Nebius AI:")
        print("  1. Get API key from https://studio.nebius.ai/")
        print("  2. export NEBIUS_API_KEY=your_key")
        print("  3. Re-run this verification script")

    return 0


if __name__ == "__main__":
    sys.exit(main())

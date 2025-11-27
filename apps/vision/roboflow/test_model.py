#!/usr/bin/env python3
"""
Generalized test script for any Roboflow Inference Server model.

Usage:
    python test_model.py --model rfdetr-small --image test.jpg
    python test_model.py --model yolov8n-640 --url http://localhost:9001
"""

import argparse
import json
import sys
from inference_sdk import InferenceHTTPClient
from inference_sdk.http.errors import HTTPCallErrorError
import requests


def pretty(obj):
    print(json.dumps(obj, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Test any inference model on local Roboflow server.")
    parser.add_argument("--model", required=True, help="Model ID (e.g. rfdetr-small, yolov11n-640, etc.)")
    parser.add_argument("--image", required=True, help="Image file path (e.g. test.jpg)")
    parser.add_argument("--url", default="http://localhost:9001", help="Inference server URL")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--iou", type=float, default=0.5, help="IOU threshold")

    args = parser.parse_args()

    print(f"\n🔌 Connecting to inference server: {args.url}")
    client = InferenceHTTPClient(api_url=args.url)

    print(f"\n📦 Loading model: {args.model}")
    try:
        reg = client.load_model(model_id=args.model, set_as_default=False)
        print(f"   ✓ Model loaded successfully.")
        print(f"   Registered models: {[m.model_id for m in reg.models]}")
    except HTTPCallErrorError as e:
        print("\n❌ Model load failed")
        print(f"   Description: {e.description}")
        print(f"   Server message: {e.api_message}")
        sys.exit(1)
    except requests.RequestException as e:
        print(f"\n❌ Cannot reach inference server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error loading model: {e}")
        sys.exit(1)

    print(f"\n🖼️ Running inference on image: {args.image}")
    try:
        result = client.infer(
            inference_input=args.image,
            model_id=args.model,
            # confidence=args.conf,
            # iou_threshold=args.iou,
        )
    except Exception as e:
        print(f"\n❌ Inference failed: {e}")
        sys.exit(1)

    print("\n📊 Raw response:")
    pretty(result)

    preds = result.get("predictions", [])
    print(f"\n🎯 Total predictions: {len(preds)}")

    if preds:
        print("\nTop detections:")
        for p in preds[:10]:
            print(
                f"  - {p['class']:<12} conf={p['confidence']:.2f} "
                f"bbox=({p['x']:.1f},{p['y']:.1f},{p['width']:.1f},{p['height']:.1f})"
            )
    else:
        print("⚠️ No predictions above confidence threshold.")

    print("\n✅ Test complete.\n")


if __name__ == "__main__":
    main()


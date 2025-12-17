#!/usr/bin/env python3
"""
Simpler model preloader for Roboflow Inference Server.

- Keeps a simple JSON state file of which models were already downloaded.
- Skips models that are already marked as downloaded.
- Can be safely re-run multiple times.

Usage:
    python download_models_simple.py \
      --api-url http://localhost:9001 \
      --cache-dir /home/box/roboflow-cache

RF_API_KEY can be set via environment if needed for non-core models.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from inference_sdk import InferenceHTTPClient
from inference_sdk.http.errors import HTTPCallErrorError
import requests


MODELS_TO_PRELOAD = [
    # RF-DETR
    "rfdetr-nano",
    "rfdetr-small",
    "rfdetr-medium",

    # YOLOv11
    "yolov11n-640",
    "yolov11s-640",

    # YOLOv10
    "yolov10n-640",
    "yolov10s-640",

    # YOLOv8
    "yolov8n-640",
    "yolov8s-640",
    "yolov8m-640",

    # Segmentation
    "yolov11n-seg-640",
    "yolov11s-seg-640",
    "yolov8n-seg-640",
    "yolov8s-seg-640",
]


def human_bytes(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024.0:
            return f"{num:3.1f}{unit}"
        num /= 1024.0
    return f"{num:.1f}PB"


def get_dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            fp = os.path.join(root, name)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def load_state(state_path: Path) -> set:
    if not state_path.exists():
        return set()
    try:
        with state_path.open("r") as f:
            data = json.load(f)
        return set(data.get("preloaded_models", []))
    except Exception:
        return set()


def save_state(state_path: Path, models: set) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w") as f:
        json.dump({"preloaded_models": sorted(models)}, f, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple Roboflow model preloader")
    parser.add_argument(
        "--api-url",
        default="http://localhost:9001",
        help="Inference server URL (default: http://localhost:9001)",
    )
    parser.add_argument(
        "--cache-dir",
        default="/var/cache/roboflow",
        help="Host cache directory (for size reporting and state file)",
    )
    parser.add_argument(
        "--remove",
        nargs="+",
        metavar="MODEL",
        help="Remove model(s) from state file (cache files remain)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_state",
        help="List models in state file and exit",
    )
    args = parser.parse_args()

    cache_path = Path(args.cache_dir)
    state_path = cache_path / "preloaded_models.json"

    # state
    already_preloaded = load_state(state_path)

    # Handle --list command
    if args.list_state:
        print(f"State file: {state_path}")
        print(f"Cache dir:  {cache_path}")
        print(f"Cache size: {human_bytes(get_dir_size(cache_path))}")
        print(f"\nModels in state file ({len(already_preloaded)}):")
        if already_preloaded:
            for m in sorted(already_preloaded):
                in_list = "✓" if m in MODELS_TO_PRELOAD else "  (not in MODELS_TO_PRELOAD)"
                print(f"  - {m} {in_list}")
        else:
            print("  (none)")
        return 0

    # Handle --remove command
    if args.remove:
        print(f"State file: {state_path}")
        print(f"Cache dir:  {cache_path}")
        print(f"\nRemoving models from state file (cache files will remain):")
        removed = []
        not_found = []
        for model in args.remove:
            if model in already_preloaded:
                already_preloaded.remove(model)
                removed.append(model)
                print(f"  ✓ Removed: {model}")
            else:
                not_found.append(model)
                print(f"  ⚠ Not in state: {model}")
        if removed:
            save_state(state_path, already_preloaded)
            print(f"\nSaved updated state file ({len(already_preloaded)} models remaining)")
        print(f"\nCache size: {human_bytes(get_dir_size(cache_path))} (unchanged)")
        return 0

    # client setup (only needed for loading models)
    client_kwargs = {"api_url": args.api_url}
    if os.getenv("RF_API_KEY"):
        client_kwargs["api_key"] = os.environ["RF_API_KEY"]
    client = InferenceHTTPClient(**client_kwargs)

    print("=" * 70)
    print("Simple Roboflow Model Preloader")
    print("=" * 70)
    print(f"API URL:    {args.api_url}")
    print(f"Cache dir:  {cache_path}")
    print(f"State file: {state_path}")
    print(f"RF_API_KEY: {'set' if os.getenv('RF_API_KEY') else 'not set'}")
    print("\nModels to preload:")
    for m in MODELS_TO_PRELOAD:
        mark = "(done)" if m in already_preloaded else ""
        print(f"  - {m} {mark}")

    initial_size = get_dir_size(cache_path)
    print(f"\nInitial cache size: {human_bytes(initial_size)}\n")

    preloaded_now = set()

    for model_id in MODELS_TO_PRELOAD:
        if model_id in already_preloaded:
            print(f"⏭  Skipping {model_id} (already in state file)")
            continue

        before = get_dir_size(cache_path)
        print(f"\n▶  Loading model: {model_id}")
        print(f"   Cache before: {human_bytes(before)}")

        t0 = time.time()
        try:
            registered = client.load_model(model_id=model_id, set_as_default=False)
        except HTTPCallErrorError as e:
            print(f"   ✖ HTTP error while loading {model_id}")
            print(f"     Description: {e.description}")
            print(f"     Server message: {e.api_message}")
            continue
        except requests.RequestException as e:
            print(f"   ✖ Network error while loading {model_id}: {e}")
            continue
        except Exception as e:
            print(f"   ✖ Unexpected error while loading {model_id}: {e}")
            continue

        elapsed = time.time() - t0
        after = get_dir_size(cache_path)
        delta = after - before

        print(f"   ✓ Loaded in {elapsed:.1f}s")
        print(f"   ✓ Registered {len(registered.models)} model(s)")
        print(f"   Cache after: {human_bytes(after)} "
              f"(+{human_bytes(delta)} for this model)")

        already_preloaded.add(model_id)
        preloaded_now.add(model_id)
        save_state(state_path, already_preloaded)

    final_size = get_dir_size(cache_path)
    print("\n" + "=" * 70)
    print("Done.")
    print(f"Final cache size: {human_bytes(final_size)}")
    if preloaded_now:
        print("\nNewly preloaded models this run:")
        for m in sorted(preloaded_now):
            print(f"  - {m}")
    else:
        print("\nNo new models were downloaded (all were already in state).")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())


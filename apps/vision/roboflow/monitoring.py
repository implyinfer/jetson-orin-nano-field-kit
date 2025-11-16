import cv2
import pandas as pd
import pickle
import requests
import matplotlib.pyplot as plt
import os
import argparse
import time

def create_camera_capture(sensor_id=0, width=1920, height=1080, framerate=30):
    """Create GStreamer pipeline for Jetson Orin Nano camera"""
    gst_pipeline = (
        f'nvarguscamerasrc sensor-id={sensor_id} ! '
        f'video/x-raw(memory:NVMM),width={width},height={height},framerate={framerate}/1 ! '
        'nvvidconv ! '
        'video/x-raw,format=BGRx ! '
        'videoconvert ! '
        'video/x-raw,format=BGR ! '
        'appsink'
    )
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
    return cap

def extract_frames(video_path, interval_minutes):
    """Extract frames from a video file at specified intervals"""
    cap = cv2.VideoCapture(video_path)
    frames = []
    timestamps = []
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_count % (fps * interval_minutes) == 0:
            frames.append(frame)
            timestamps.append(frame_count / fps)
        frame_count += 1
    cap.release()
    return frames, timestamps

def process_live_stream(base_url, dataset_id, version_id, api_key, interval_seconds, confidence=0.5, 
                        sensor_id=0, width=1920, height=1080, framerate=30, duration_minutes=None):
    """Process live video stream from Jetson camera"""
    cap = create_camera_capture(sensor_id, width, height, framerate)
    
    if not cap.isOpened():
        raise RuntimeError("Failed to open camera stream")
    
    print(f"Camera stream opened. Processing frames every {interval_seconds} seconds...")
    print("Press Ctrl+C to stop and generate reports.")
    
    df_rows = []
    start_time = time.time()
    last_capture_time = 0
    frame_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to read frame")
                time.sleep(0.1)
                continue
            
            current_time = time.time()
            elapsed_time = current_time - start_time
            
            # Check duration limit if specified
            if duration_minutes and elapsed_time >= duration_minutes * 60:
                print(f"Duration limit of {duration_minutes} minutes reached.")
                break
            
            # Capture frame at specified interval
            if current_time - last_capture_time >= interval_seconds:
                print(f"Processing frame at {elapsed_time:.1f}s...")
                timestamp_seconds = elapsed_time
                
                # Send frame to Roboflow API
                try:
                    numpy_data = pickle.dumps(frame)
                    headers = {"Content-Type": "application/x-www-form-urlencoded"}
                    res = requests.post(
                        f"{base_url}/{dataset_id}/{version_id}",
                        data=numpy_data,
                        headers=headers,
                        params={"api_key": api_key, "confidence": confidence, "image_type": "numpy"},
                        timeout=10
                    )
                    
                    if res.status_code == 200:
                        predictions = res.json()
                        
                        for pred in predictions.get('predictions', []):
                            time_interval = f"{int(timestamp_seconds // 60)}:{int(timestamp_seconds % 60):02}"
                            row = {
                                "timestamp": time_interval,
                                "time": predictions.get('time', 0),
                                "x": pred["x"],
                                "y": pred["y"],
                                "width": pred["width"],
                                "height": pred["height"],
                                "pred_confidence": pred["confidence"],
                                "class": pred["class"]
                            }
                            df_rows.append(row)
                        
                        print(f"  Detected {len(predictions.get('predictions', []))} objects")
                    else:
                        print(f"  API request failed with status {res.status_code}")
                
                except Exception as e:
                    print(f"  Error processing frame: {e}")
                
                last_capture_time = current_time
            
            frame_count += 1
            
            # Small delay to prevent excessive CPU usage
            time.sleep(0.01)
    
    except KeyboardInterrupt:
        print("\nStopping capture...")
    finally:
        cap.release()
        print("Camera released.")
    
    # Create DataFrame from collected data
    if df_rows:
        df = pd.DataFrame(df_rows)
        df['seconds'] = df['timestamp'].str.split(':').apply(lambda x: int(x[0])*60 + int(x[1]))
        df = df.sort_values(by="seconds")
        return df
    else:
        print("No predictions collected.")
        return pd.DataFrame()

def fetch_predictions(base_url, frames, timestamps, dataset_id, version_id, api_key, confidence=0.5):
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    df_rows = []
    for idx, frame in enumerate(frames):
        numpy_data = pickle.dumps(frame)
        res = requests.post(
            f"{base_url}/{dataset_id}/{version_id}",
            data=numpy_data,
            headers=headers,
            params={"api_key": api_key, "confidence": confidence, "image_type": "numpy"}
        )
        predictions = res.json()

        for pred in predictions['predictions']:
            time_interval = f"{int(timestamps[idx] // 60)}:{int(timestamps[idx] % 60):02}"
            row = {
                "timestamp": time_interval,
                "time": predictions['time'],
                "x": pred["x"],
                "y": pred["y"],
                "width": pred["width"],
                "height": pred["height"],
                "pred_confidence": pred["confidence"],
                "class": pred["class"]
            }
            df_rows.append(row)

    df = pd.DataFrame(df_rows)
    df['seconds'] = df['timestamp'].str.split(':').apply(lambda x: int(x[0])*60 + int(x[1]))
    df = df.sort_values(by="seconds")
    return df

def plot_and_save(data, title, filename, ylabel, stacked=False, legend_title=None, legend_loc=None, legend_bbox=None):
    plt.style.use('dark_background')
    data.plot(kind='bar', stacked=stacked, figsize=(15,7))
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xlabel('Timestamp (in minutes:seconds)')
    
    if legend_title:
        plt.legend(title=legend_title, loc=legend_loc, bbox_to_anchor=legend_bbox)
    
    plt.tight_layout()
    plt.savefig(filename)

def main():
    parser = argparse.ArgumentParser(description='Monitor video with Roboflow predictions')
    parser.add_argument('--mode', type=str, choices=['live', 'video'], default='live',
                        help='Processing mode: live stream or video file (default: live)')
    parser.add_argument('--video-path', type=str, help='Path to the video file (required for video mode)')
    parser.add_argument('--dataset-id', type=str, required=True, help='Roboflow dataset ID')
    parser.add_argument('--version-id', type=str, required=True, help='Roboflow version ID')
    parser.add_argument('--api-key', type=str, required=True, help='Roboflow API key')
    parser.add_argument('--base-url', type=str, default='http://localhost:9001', help='Base URL for Roboflow API (default: http://localhost:9001)')
    parser.add_argument('--interval-minutes', type=float, default=1.0, help='Interval in minutes to extract frames (default: 1.0)')
    parser.add_argument('--confidence', type=float, default=0.5, help='Confidence threshold for predictions (default: 0.5)')
    parser.add_argument('--sensor-id', type=int, default=0, help='Camera sensor ID (default: 0)')
    parser.add_argument('--width', type=int, default=1920, help='Camera width (default: 1920)')
    parser.add_argument('--height', type=int, default=1080, help='Camera height (default: 1080)')
    parser.add_argument('--framerate', type=int, default=30, help='Camera framerate (default: 30)')
    parser.add_argument('--duration-minutes', type=float, help='Duration limit for live stream in minutes (optional)')

    args = parser.parse_args()

    # Validate arguments based on mode
    if args.mode == 'video' and not args.video_path:
        parser.error("--video-path is required when --mode is 'video'")

    base_url = args.base_url
    dataset_id = args.dataset_id
    version_id = args.version_id
    api_key = args.api_key

    if not os.path.exists("results"):
        os.makedirs("results")
    
    # Process based on mode
    if args.mode == 'live':
        print("Starting live stream processing...")
        interval_seconds = args.interval_minutes * 60
        df = process_live_stream(
            base_url, dataset_id, version_id, api_key, interval_seconds, 
            confidence=args.confidence,
            sensor_id=args.sensor_id,
            width=args.width,
            height=args.height,
            framerate=args.framerate,
            duration_minutes=args.duration_minutes
        )
    else:
        print("Processing video file...")
        video_path = args.video_path
        interval_minutes = args.interval_minutes * 60
        frames, timestamps = extract_frames(video_path, interval_minutes)
        df = fetch_predictions(base_url, frames, timestamps, dataset_id, version_id, api_key, confidence=args.confidence)

    # Check if we have any data to process
    if df.empty:
        print("No predictions collected. Exiting.")
        return

    # Saving predictions response to csv
    df.to_csv("results/predictions.csv", index=False)
    print(f"Saved {len(df)} predictions to results/predictions.csv")

    # Transform timestamps to minutes and group
    df['minutes'] = df['timestamp'].str.split(':').apply(lambda x: int(x[0]) * 60 + int(x[1]))
    object_counts_per_interval = df.groupby('minutes').size().sort_index()
    object_counts_per_interval.index = object_counts_per_interval.index.map(lambda x: f"{x // 60}:{x % 60:02}")
    object_counts_per_interval.to_csv("results/object_counts_per_interval.csv")

    # Quick insights
    print(f"\n=== Analysis Results ===")
    print(f"Total unique objects detected: {df['class'].nunique()}")
    if len(df) > 0:
        print(f"Most frequently detected object: {df['class'].value_counts().idxmax()}")
        print(f"Time interval with the most objects detected: {object_counts_per_interval.idxmax()}")
        print(f"Time interval with the least objects detected: {object_counts_per_interval.idxmin()}")
    print("======================\n")

    plot_and_save(object_counts_per_interval, 'Number of Objects Detected Over Time', "results/objects_over_time.png", 'Number of Objects')
    print("Saved plot: results/objects_over_time.png")

    # Group by timestamp and class, then sort by minutes
    objects_by_class_per_interval = df.groupby(['minutes', 'class']).size().unstack(fill_value=0).sort_index()
    objects_by_class_per_interval.index = objects_by_class_per_interval.index.map(lambda x: f"{x // 60}:{x % 60:02}")
    objects_by_class_per_interval.to_csv("results/object_counts_by_class_per_interval.csv")
    print("Saved plot: results/objects_by_class_over_time.png")

    plot_and_save(objects_by_class_per_interval, 'Number of Objects Detected Over Time by Class', "results/objects_by_class_over_time.png", 'Number of Objects', True, "Object Class", "center left", (1, 0.5))
    print("\nProcessing complete! Check the 'results' directory for outputs.")


if __name__ == "__main__":
    main()

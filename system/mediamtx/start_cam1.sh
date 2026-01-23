#!/bin/bash
# Wait for MediaMTX to be ready (stagger startup to avoid resource contention)
sleep 4

# Ultra low-latency GStreamer + FFmpeg pipeline for Camera 1 (Right camera)
# Note: Orin Nano has NO hardware encoder (NVENC), must use x264 (CPU)
# Key optimizations:
#   - x264enc: ultrafast preset, zerolatency tune, no B-frames
#   - FFmpeg: no -re flag, low_delay flags, TCP transport
#   - queue with leaky=downstream prevents memory crashes

gst-launch-1.0 -e \
  nvarguscamerasrc sensor-id=1 ! \
  'video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1' ! \
  nvvidconv flip-method=0 ! \
  'video/x-raw,format=I420' ! \
  queue max-size-buffers=1 max-size-time=0 max-size-bytes=0 leaky=upstream ! \
  x264enc \
    tune=zerolatency \
    speed-preset=faster \
    bitrate=8000 \
    key-int-max=30 \
    bframes=0 \
    sliced-threads=true \
    threads=4 ! \
  'video/x-h264,stream-format=byte-stream' ! \
  h264parse ! \
  fdsink | \
  ffmpeg -fflags nobuffer -flags low_delay -f h264 -i pipe:0 \
    -c:v copy -f rtsp -rtsp_transport tcp rtsp://localhost:8554/cam1

#!/bin/bash
# GStreamer + FFmpeg pipeline for Camera 0 (sensor-id=0, /dev/video0)
# Captures from camera and publishes to MediaMTX via RTSP

gst-launch-1.0 -v \
  nvarguscamerasrc sensor-id=0 ! \
  'video/x-raw(memory:NVMM),width=1920,height=1080,framerate=30/1' ! \
  nvvidconv ! \
  'video/x-raw,format=I420' ! \
  x264enc tune=zerolatency bitrate=4000 speed-preset=superfast ! \
  h264parse ! \
  'video/x-h264,stream-format=byte-stream' ! \
  fdsink | \
  ffmpeg -re -f h264 -i pipe:0 -c:v copy -f rtsp rtsp://localhost:8554/cam0

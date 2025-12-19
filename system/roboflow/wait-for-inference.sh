#!/usr/bin/env bash
# Wait for Roboflow Inference Server to be ready on port 9001

MAX_WAIT=120  # Maximum seconds to wait
INTERVAL=2    # Check interval

echo "Waiting for Roboflow Inference Server on port 9001..."

count=0
while [ $count -lt $MAX_WAIT ]; do
    if curl -s -f http://localhost:9001/ > /dev/null 2>&1; then
        echo "Inference server is ready!"
        exit 0
    fi
    sleep $INTERVAL
    count=$((count + INTERVAL))
    echo "  Waiting... ($count/$MAX_WAIT seconds)"
done

echo "Error: Inference server did not become ready within $MAX_WAIT seconds"
exit 1

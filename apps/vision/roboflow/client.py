import base64
import requests
from io import BytesIO
from PIL import Image

api_key="5yawNNvJ7gqjlloPoG0w"
model="train-detection-4ud7c"
version=1

image_url = "https://source.roboflow.com/zD7y6XOoQnh7WC160Ae7/yA6pCzno5RW5tc3LjgSR/original.jpg"
image = Image.open(requests.get(image_url, stream=True).raw) #Reading the image from a URL for demonstration purposes
buffered = BytesIO()
image.save(buffered, quality=100, format="JPEG")
img_str = base64.b64encode(buffered.getvalue())
img_str = img_str.decode("ascii")

headers = {"Content-Type": "application/x-www-form-urlencoded"}
res = requests.post(
    f"http://localhost:9001/{model}/{version}?api_key={api_key}",
    data=img_str,
    headers=headers,
)
print(res)
print(res.text)



pipeline = InferencePipeline.init(
    model_id= model_name,
    video_reference="rtsp://192.168.1.171:8554/cam1",
    on_prediction=on_prediction,
    api_key='5yawNNvJ7gqjlloPoG0w',
    confidence=0.5,
)
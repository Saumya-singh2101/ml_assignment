import base64
import requests

IMAGE_PATH = "test.png"
API_URL = "http://localhost:8000/api/analyze"

with open(IMAGE_PATH, "rb") as image_file:
    image_base64 = base64.b64encode(
        image_file.read()
    ).decode("utf-8")

payload = {
    "image_base64": image_base64,
    "context": {
        "zoom": 1,
        "pan_x": 0,
        "pan_y": 0,
        "stroke_count": 3,
        "region_x": 0,
        "region_y": 0,
        "region_width": 500,
        "region_height": 500,
        "prompt": "Analyze this drawing"
    },
    "trigger": "explicit"
}

response = requests.post(
    API_URL,
    json=payload,
    timeout=60
)

print("Status:", response.status_code)
print("Response:")
print(response.text)
import asyncio
from io import BytesIO

from PIL import Image
from fastapi import FastAPI
from fastapi import UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from app.api_response import ApiListResponse
from app.config import settings
from app.detection import Detection
from app.history import HistorySaveRequest, save_history
from model.detect import detect

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins.split(';'),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def convert(result: dict):
    return Detection(**result)


@app.post("/detect-image", response_model=ApiListResponse[Detection])
async def detect_image(file: UploadFile = File(...)) -> ApiListResponse[Detection]:
    try:
        img = Image.open(BytesIO(await file.read()))
    except Exception as err:
        return ApiListResponse.bad_request(str(err))

    predicted_image, row_detections = detect(img)
    detections = list(map(convert, row_detections))
    asyncio.create_task(
        save_history(HistorySaveRequest(image=predicted_image, detections=detections))
    )

    return ApiListResponse[Detection].ok(detections)

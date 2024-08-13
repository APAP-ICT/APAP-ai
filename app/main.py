import asyncio
from io import BytesIO

import cv2
import numpy as np
from PIL import Image
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi import UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from app.api_response import ApiResponse, ApiListResponse
from app.config import settings
from app.connection_manager import ConnectionManager
from app.history import async_save_history
from model.detect import detect, track
from model.video_recorder import VideoRecorder

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins.split(';'),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()


@app.post("/api/detect-image", response_model=ApiResponse)
async def detect_image(file: UploadFile = File(...)) -> ApiResponse:
    try:
        img = Image.open(BytesIO(await file.read()))
    except Exception as err:
        return ApiResponse.bad_request(str(err))

    result = detect(np.array(img))
    await async_save_history(result)

    return ApiResponse.ok()


@app.get("/api/publishers")
def exists_publisher() -> ApiListResponse[str]:
    return ApiListResponse[str].ok_with_data(list(manager.publishers.keys()))


@app.websocket("/ws/publishers/{location_name}")
async def websocket_publisher(websocket: WebSocket, location_name: str):
    await manager.connect(location_name, websocket)
    video_recorder = VideoRecorder()

    try:
        while True:
            # pre-processing
            data = await websocket.receive_bytes()
            img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)  # byte to nparr

            result = track(img)

            # TODO 별도 이상상황으로 교체
            if result.is_abnormal_pattern_detected():
                video_recorder.start_record_if_not()
                await async_save_history(result)

            if video_recorder.is_recording:
                video_recorder.record_frame(result.predict_image_np)

            await manager.broadcast(location_name, result.get_encoded_nparr().tobytes())
    except WebSocketDisconnect:
        manager.disconnect(location_name)
        print("Publisher disconnected")


@app.websocket("/ws/subscribers/{location_name}")
async def websocket_subscriber(location_name: str, websocket: WebSocket):
    await manager.subscribe(location_name, websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("Subscriber disconnected")
    finally:
        manager.unsubscribe(location_name, websocket)

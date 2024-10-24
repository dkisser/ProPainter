import os

from fastapi import FastAPI
from pydantic import BaseModel

import celery_app
from celery.result import AsyncResult


app = FastAPI()


class ImageRequest(BaseModel):
    image_path: str
    video_path: str

    def to_json(self):
        return {"image_path": self.image_path, "video_path": self.video_path}


class TaskQueryReqeust(BaseModel):
    task_id: str


@app.post('/process_image')
async def process_image(request: ImageRequest):
    result = celery_app.background_task.delay(request.to_json())
    return {"message": "Task initiated", "task_id": result.id}


@app.get("/task/{task_id}/result")
async def get_task_result(task_id: str):
    task_result = AsyncResult(str(task_id), app=celery_app.app)
    if task_result.ready():
        return {"status": "completed", "result": task_result.result}
    elif task_result.failed():
        return {"status": "failed", "result": task_result.result}
    else:
        return {"status": "pending"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)


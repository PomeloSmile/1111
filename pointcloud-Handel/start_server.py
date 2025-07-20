import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api import app
from pointcloud_predictor import PointCloudHandler

# 创建static目录（如果不存在）
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 
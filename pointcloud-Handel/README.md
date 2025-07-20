# 点云处理后端服务

## 项目简介
这是一个基于 FastAPI 的点云处理服务，主要用于电力线提取。该服务通过 WebSocket 提供实时点云数据处理能力。

## 功能特点
- 实时点云数据处理
- 电力线提取
- WebSocket 实时通信
- 支持 LAS 文件格式
- 多线程处理支持

## 技术栈
- Python 3.12.11
- FastAPI
- Open3D
- NumPy
- WebSocket

## 安装依赖
```bash
pip install -r requirements.txt
```

## 运行服务
```bash
python main.py
```
服务将在 `http://localhost:8000` 启动

## API 说明

### WebSocket 接口
- 端点：`ws://localhost:8000/ws`
- 支持的消息类型：
  - `
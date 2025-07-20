import os
import logging
import tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
import shutil
import json
import laspy
import open3d as o3d
import numpy as np
#from pointcloud_predictor import 
import traceback
import asyncio
from datetime import datetime
from typing import List, Optional
import torch
from torch_geometric.data import Data
from pointcloud_predictor import PointCloudHandler
import uuid

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()
processor = PointCloudHandler()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建临时目录
TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)
logger.info(f"临时目录创建在: {TEMP_DIR.absolute()}")

# 创建结果目录
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

# 创建元数据文件
METADATA_FILE = RESULTS_DIR / "reconstruction_metadata.json"
if not METADATA_FILE.exists():
    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"reconstructions": []}, f, ensure_ascii=False, indent=2)

# 创建预测器实例（单例模式）
logger.info("正在初始化预测器...")
predictor = None

def get_predictor():
    """
    获取全局唯一的点云预测器实例。
    返回：
        PointCloudHandler: 预测器对象
    用法：
        handler = get_predictor()
    """
    global predictor
    if predictor is None:
        predictor = PointCloudHandler()
        logger.info("预测器初始化完成")
    return predictor

# 配置参数
VOXEL_SIZE = 0.05  # 体素大小（米）
DISTANCE_THRESHOLD = 0.5  # 距离阈值（米）
TARGET_POINTS = 1000000  # 目标点数

def preprocess_point_cloud(points: np.ndarray) -> np.ndarray:
    """
    对点云数据进行预处理，包括去除离群点、体素降采样和法线估计。
    参数：
        points (np.ndarray): 输入点云 (N, 3)
    返回：
        np.ndarray: 预处理后的点云 (M, 3)
    用法：
        new_points = preprocess_point_cloud(points)
    """
    # 创建Open3D点云对象
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    
    # 移除离群点
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=20, std_ratio=2.0)
    pcd = pcd.select_by_index(ind)
    
    # 体素降采样
    pcd = pcd.voxel_down_sample(voxel_size=VOXEL_SIZE)
    
    # 估计法线
    pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
    
    return np.asarray(pcd.points)

def downsample_point_cloud(points: np.ndarray, target_points: int = TARGET_POINTS) -> np.ndarray:
    """
    随机降采样点云到目标点数。
    参数：
        points (np.ndarray): 输入点云 (N, 3)
        target_points (int): 目标点数
    返回：
        np.ndarray: 降采样后的点云
    用法：
        sampled = downsample_point_cloud(points, 100000)
    """
    if len(points) <= target_points:
        return points
        
    # 计算降采样率
    sampling_rate = target_points / len(points)
    
    # 随机采样
    indices = np.random.choice(len(points), target_points, replace=False)
    return points[indices]

def read_las_file(file_path: str) -> np.ndarray:
    """
    读取LAS格式点云文件。
    参数：
        file_path (str): LAS文件路径
    返回：
        np.ndarray: 点云坐标 (N, 3)
    用法：
        points = read_las_file('xxx.las')
    """
    try:
        with laspy.open(file_path) as f:
            las = f.read()
            points = np.vstack((las.x, las.y, las.z)).transpose()
            return points
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取LAS文件失败: {str(e)}")

@app.get("/")
async def root():
    """
    根路径测试接口。
    返回：
        dict: 服务运行状态信息
    """
    logger.info("收到根路径请求")
    return {"message": "电力线提取API服务正在运行"}

@app.get("/health")
async def health_check():
    """
    健康检查接口。
    返回：
        dict: 服务健康状态
    """
    logger.info("收到健康检查请求")
    return {"status": "ok"}

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    上传点云文件并提取电力线。
    参数：
        file (UploadFile): 上传的点云文件（.las）
    返回：
        dict: 结果文件路径和处理信息
    """
    temp_file_path = None
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.las') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        # 生成输出文件名
        base_name = Path(file.filename).stem
        output_file = RESULTS_DIR / f"{base_name}_预测.ply"
        # 处理点云数据
        handler = get_predictor()
        handler.extract_powerlines_csf_pca_blockwise(temp_file_path, output_file, use_csf=False, block_length=200)
        # 返回结果文件路径和状态
        return {
            'result_file': str(output_file),
            'message': '点云电力线提取完成，结果已保存',
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@app.post("/reconstruct")
async def reconstruct(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    上传点云文件（ply/las），重建为三角网格并返回下载。
    参数：
        file (UploadFile): 上传的点云文件
        background_tasks (BackgroundTasks): FastAPI后台任务
    返回：
        FileResponse: 下载重建网格文件
    """
    handler = get_predictor()
    temp_dir = os.path.join(os.path.dirname(__file__), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    # 用uuid生成唯一文件名，防止冲突和安全问题
    ext = os.path.splitext(file.filename)[-1].lower()
    input_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}{ext}")
    output_path = os.path.join(temp_dir, f"reconstructed_{uuid.uuid4().hex}.ply")
    try:
        # 保存上传的文件
        content = await file.read()
        with open(input_path, "wb") as f:
            f.write(content)
        logger.info(f"文件已保存到: {input_path}")
        # 调用 handler 进行重建
        mesh, _ = handler.reconstruct_mesh(input_path, output_path)
        logger.info(f"网格重建完成，已保存到: {output_path}")
        # 下载完成后自动删除输出文件
        if background_tasks is not None:
            background_tasks.add_task(os.remove, output_path)
        # 只删除输入文件
        if os.path.exists(input_path):
            os.remove(input_path)
        return FileResponse(
            output_path,
            media_type="application/octet-stream",
            filename=os.path.basename(output_path)
        )
    except Exception as e:
        logger.error(f"重建过程出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reconstructions")
async def get_reconstructions():
    """
    获取重建结果列表（未实现）。
    返回：
        list: 重建结果列表
    """
    # 这里可以添加获取重建结果列表的逻辑
    return []

def save_reconstruction_result(file_path: Path, original_filename: str) -> dict:
    """
    保存重建结果文件并记录元数据。
    参数：
        file_path (Path): 结果文件路径
        original_filename (str): 原始文件名
    返回：
        dict: 元数据信息
    用法：
        meta = save_reconstruction_result(path, 'xxx.ply')
    """
    try:
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 创建结果文件名
        result_filename = f"reconstruction_{timestamp}_{original_filename}"
        result_path = RESULTS_DIR / result_filename
        
        # 复制文件到结果目录
        shutil.copy2(file_path, result_path)
        
        # 读取点云数据以获取点数
        pcd = o3d.io.read_point_cloud(str(file_path))
        point_count = len(pcd.points)
        
        # 创建元数据
        metadata = {
            "filename": result_filename,
            "original_filename": original_filename,
            "timestamp": timestamp,
            "point_count": point_count,
            "file_size": os.path.getsize(result_path),
            "file_path": str(result_path)
        }
        
        # 更新元数据文件
        with open(METADATA_FILE, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data["reconstructions"].append(metadata)
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.truncate()
        
        logger.info(f"重建结果已保存: {result_filename}")
        return metadata
        
    except Exception as e:
        logger.error(f"保存重建结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"保存重建结果失败: {str(e)}")

def process_point_cloud_batch(points: np.ndarray, batch_size: int = 100000) -> List[np.ndarray]:
    """
    将点云数据分批处理。
    参数：
        points (np.ndarray): 输入点云 (N, 3)
        batch_size (int): 每批点数
    返回：
        List[np.ndarray]: 分批后的点云列表
    用法：
        batches = process_point_cloud_batch(points, 100000)
    """
    num_points = len(points)
    batches = []
    for i in range(0, num_points, batch_size):
        end_idx = min(i + batch_size, num_points)
        batches.append(points[i:end_idx])
    return batches

def merge_point_clouds(pcd_list: List[o3d.geometry.PointCloud]) -> o3d.geometry.PointCloud:
    """
    合并多个点云对象为一个。
    参数：
        pcd_list (List[PointCloud]): 点云对象列表
    返回：
        PointCloud: 合并后的点云
    用法：
        merged = merge_point_clouds([pcd1, pcd2])
    """
    if not pcd_list:
        return o3d.geometry.PointCloud()
    
    merged_pcd = pcd_list[0]
    for pcd in pcd_list[1:]:
        merged_pcd += pcd
    return merged_pcd

def process_batch(pcd_batch: o3d.geometry.PointCloud, voxel_size: float) -> o3d.geometry.PointCloud:
    """
    对单个点云批次进行体素下采样和法线估计。
    参数：
        pcd_batch (PointCloud): 点云批次
        voxel_size (float): 体素大小
    返回：
        PointCloud: 处理后的点云
    用法：
        new_pcd = process_batch(pcd, 0.05)
    """
    try:
        # 1. 体素下采样
        pcd_batch = pcd_batch.voxel_down_sample(voxel_size=voxel_size)
        
        # 2. 法向量估计
        pcd_batch.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=voxel_size * 2,
                max_nn=20
            )
        )
        
        # 3. 法向量定向
        pcd_batch.orient_normals_consistent_tangent_plane(50)
        
        return pcd_batch
    except Exception as e:
        logger.error(f"处理批次时出错: {str(e)}")
        return pcd_batch

@app.post("/reconstruct_point_cloud")
async def reconstruct_point_cloud(
    file: UploadFile = File(...),
    voxel_size: float = 0.05,
    max_points: int = 1000000,
    batch_size: int = 100000
):
    """
    上传PLY点云文件，分批重建为三角网格。
    参数：
        file (UploadFile): 上传的PLY点云文件
        voxel_size (float): 体素大小
        max_points (int): 最大点数
        batch_size (int): 每批点数
    返回：
        dict: 重建结果信息
    """
    try:
        # 验证文件格式
        if not file.filename.lower().endswith('.ply'):
            raise HTTPException(status_code=400, detail="重建只支持PLY格式")
        
        # 保存上传的文件
        temp_input = TEMP_DIR / f"input_{file.filename}"
        with open(temp_input, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        if os.path.getsize(temp_input) == 0:
            raise HTTPException(status_code=400, detail="上传的文件为空")
        
        logger.info(f"开始处理文件: {file.filename}")
        
        # 读取点云
        pcd = o3d.io.read_point_cloud(str(temp_input))
        if len(pcd.points) == 0:
            raise HTTPException(status_code=400, detail="点云数据为空")
        
        # 检查点云大小
        if len(pcd.points) > max_points:
            logger.warning(f"点云点数({len(pcd.points)})超过限制({max_points})，进行下采样")
            pcd = pcd.voxel_down_sample(voxel_size=voxel_size * 2)
        
        # 将点云转换为numpy数组
        points = np.asarray(pcd.points)
        
        # 分批处理点云
        logger.info(f"开始分批处理点云，总点数: {len(points)}")
        batches = process_point_cloud_batch(points, batch_size)
        processed_batches = []
        
        for i, batch_points in enumerate(batches):
            logger.info(f"处理第 {i+1}/{len(batches)} 批，点数: {len(batch_points)}")
            
            # 创建点云对象
            batch_pcd = o3d.geometry.PointCloud()
            batch_pcd.points = o3d.utility.Vector3dVector(batch_points)
            
            # 处理批次
            processed_batch = process_batch(batch_pcd, voxel_size)
            processed_batches.append(processed_batch)
            
            # 清理内存
            del batch_pcd
            torch.cuda.empty_cache()
        
        # 合并处理后的点云
        logger.info("合并处理后的点云...")
        merged_pcd = merge_point_clouds(processed_batches)
        
        # Poisson重建
        logger.info("正在进行Poisson重建...")
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            merged_pcd,
            depth=8,
            width=0,
            scale=1.1,
            linear_fit=False
        )
        
        if mesh.is_empty():
            raise ValueError("重建结果为空")
        
        # 移除低密度顶点
        vertices_to_remove = densities < np.quantile(densities, 0.2)
        mesh.remove_vertices_by_mask(vertices_to_remove)
        
        # 网格优化
        logger.info("正在进行网格优化...")
        mesh = mesh.filter_smooth_taubin(number_of_iterations=5)
        
        # 网格简化
        logger.info("正在进行网格简化...")
        target_triangles = len(mesh.triangles) // 4
        mesh = mesh.simplify_quadric_decimation(target_number_of_triangles=target_triangles)
        
        # 最终平滑
        mesh = mesh.filter_smooth_taubin(number_of_iterations=3)
        
        # 保存结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"reconstruction_{timestamp}.ply"
        result_path = RESULTS_DIR / result_filename
        
        # 保存重建结果
        o3d.io.write_triangle_mesh(str(result_path), mesh)
        
        # 更新元数据
        metadata = {
            "filename": result_filename,
            "original_filename": file.filename,
            "timestamp": timestamp,
            "point_count": len(merged_pcd.points),
            "triangle_count": len(mesh.triangles),
            "file_size": os.path.getsize(result_path),
            "file_path": str(result_path)
        }
        
        # 读取现有元数据
        if METADATA_FILE.exists():
            with open(METADATA_FILE, "r", encoding="utf-8") as f:
                metadata_dict = json.load(f)
        else:
            metadata_dict = {"reconstructions": []}
        
        # 添加新的元数据
        metadata_dict["reconstructions"].append(metadata)
        
        # 保存更新后的元数据
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(metadata_dict, f, ensure_ascii=False, indent=2)
        
        return {
            "message": "重建完成",
            "filename": result_filename,
            "point_count": len(merged_pcd.points),
            "triangle_count": len(mesh.triangles)
        }
        
    except Exception as e:
        logger.error(f"重建失败: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # 清理临时文件
        if temp_input.exists():
            temp_input.unlink()

@app.get("/reconstructions")
async def list_reconstructions():
    """
    获取所有重建结果的列表。
    返回：
        list: 重建结果元数据列表
    """
    try:
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["reconstructions"]
    except Exception as e:
        logger.error(f"获取重建结果列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取重建结果列表失败: {str(e)}")

@app.get("/reconstructions/{filename}")
async def get_reconstruction(filename: str):
    """
    下载指定的重建结果文件。
    参数：
        filename (str): 文件名
    返回：
        FileResponse: 文件下载响应
    """
    try:
        file_path = RESULTS_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        return FileResponse(file_path, media_type="application/octet-stream", filename=filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取重建结果文件失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取重建结果文件失败: {str(e)}")

if __name__ == "__main__":
    logger.info("启动服务器...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 
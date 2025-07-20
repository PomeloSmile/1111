import os
import numpy as np
import open3d as o3d
import laspy
import logging
from sklearn.cluster import DBSCAN
from sklearn.decomposition import PCA

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def remove_outliers(points, nb_neighbors=20, std_ratio=2.0):
    """
    去除点云中的离群点。
    参数：
        points (np.ndarray): 输入点云 (N, 3)
        nb_neighbors (int): 邻域点数
        std_ratio (float): 标准差倍数
    返回：
        filtered_points (np.ndarray): 过滤后的点云
        ind (np.ndarray): 保留点的索引
    用法：
        filtered_points, ind = remove_outliers(points)
    """
    # 转为Open3D点云对象
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    # 统计滤波
    cl, ind = pcd.remove_statistical_outlier(nb_neighbors=nb_neighbors, std_ratio=std_ratio)
    filtered_points = np.asarray(pcd.points)[ind]
    return filtered_points, ind

class PointCloudHandler:
    def read_point_cloud(self, file_path):
        """
        读取点云文件（支持.ply/.las/.laz），并去除无效点和离群点。
        参数：
            file_path (str): 点云文件路径
        返回：
            points (np.ndarray): 点坐标 (N, 3)
            colors (np.ndarray|None): 颜色 (N, 3)
            intensity (np.ndarray|None): 强度 (N,)
        用法：
            points, colors, intensity = handler.read_point_cloud(path)
        """
        try:
            file_path = str(file_path)
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext == '.ply':
                pcd = o3d.io.read_point_cloud(file_path)
                points = np.asarray(pcd.points)
                colors = np.asarray(pcd.colors) if pcd.has_colors() else None
                intensity = None
            elif file_ext in ['.las', '.laz']:
                las = laspy.read(file_path)
                points = np.vstack((las.x, las.y, las.z)).transpose()
                if hasattr(las, 'red') and hasattr(las, 'green') and hasattr(las, 'blue'):
                    colors = np.vstack((
                        las.red / 65535.0,
                        las.green / 65535.0,
                        las.blue / 65535.0
                    )).transpose()
                else:
                    colors = None
                if hasattr(las, 'intensity'):
                    intensity = las.intensity
                else:
                    intensity = None
                if len(points) == 0:
                    raise ValueError("LAS文件不包含任何点")
                logger.info(f"成功读取LAS文件: {file_path}")
                logger.info(f"点云大小: {len(points)} 点")
            else:
                raise ValueError(f"不支持的文件格式: {file_ext}")
            if len(points) == 0:
                raise ValueError("点云数据为空")
            if np.isnan(points).any() or np.isinf(points).any():
                valid_mask = ~(np.isnan(points).any(axis=1) | np.isinf(points).any(axis=1))
                points = points[valid_mask]
                if colors is not None:
                    colors = colors[valid_mask]
                if intensity is not None:
                    intensity = intensity[valid_mask]
                if len(points) == 0:
                    raise ValueError("移除无效点后点云为空")
            points = points.astype(np.float32)
            if colors is not None:
                colors = colors.astype(np.float32)
            if intensity is not None:
                intensity = intensity.astype(np.float32)
            # 去除离群点
            filtered_points, ind = remove_outliers(points)
            if colors is not None:
                colors = colors[ind]
            if intensity is not None:
                intensity = intensity[ind]
            points = filtered_points
            return points, colors, intensity
        except Exception as e:
            logger.error(f"读取点云文件失败: {str(e)}")
            raise

    def fit_towers_dbscan(self, points, eps=3, min_samples=10, z_percentile=85):
        """
        使用DBSCAN聚类算法检测高空点中的电力塔。
        参数：
            points (np.ndarray): 点云 (N, 3)
            eps (float): DBSCAN半径参数
            min_samples (int): DBSCAN最小样本数
            z_percentile (float): 选取高空点的z分位数
        返回：
            tower_clusters (list): 每个电力塔的点云子集
        用法：
            towers = handler.fit_towers_dbscan(points)
        """
        try:
            z_threshold = np.percentile(points[:, 2], z_percentile)
            high_points = points[points[:, 2] > z_threshold]
            if len(high_points) == 0:
                logger.warning("高空点太少，无法聚类电力塔")
                return []

            if len(high_points) > 50000:
                idx = np.random.choice(len(high_points), 10000, replace=False)
                high_points = high_points[idx]

            from sklearn.neighbors import NearestNeighbors
            nbrs = NearestNeighbors(n_neighbors=5).fit(high_points)
            dists, _ = nbrs.kneighbors(high_points)
            mean_dist = np.mean(dists[:, 1:])
            logger.info(f"DBSCAN参数: eps={eps:.2f}, min_samples={min_samples}, mean_dist={mean_dist:.2f}")

            clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(high_points)
            labels = clustering.labels_
            tower_clusters = []
            for label in set(labels):
                if label == -1:
                    continue
                cluster_points = high_points[labels == label]
                z_span = cluster_points[:, 2].max() - cluster_points[:, 2].min()
                xy_span = np.ptp(cluster_points[:, :2], axis=0)
                logger.info(f"label={label}, 点数={len(cluster_points)}, z_span={z_span:.2f}, xy_span={xy_span}")
                # 放宽条件
                if len(cluster_points) > 20 and z_span > 6:
                    tower_clusters.append(cluster_points)
            logger.info(f"DBSCAN聚类电力塔完成，找到塔数量: {len(tower_clusters)}")
            return tower_clusters
        except Exception as e:
            logger.error(f"DBSCAN聚类电力塔失败: {str(e)}")
            return []

    def split_pointcloud_by_main_direction(self, points, block_length=200):
        """
        按主方向将点云分块。
        参数：
            points (np.ndarray): 点云 (N, 3)
            block_length (float): 每块长度
        返回：
            blocks (list): 分块后的点云列表
        用法：
            blocks = handler.split_pointcloud_by_main_direction(points)
        """
        pca = PCA(n_components=1)
        main_axis = pca.fit(points[:, :2]).components_[0]
        proj = points[:, 0] * main_axis[0] + points[:, 1] * main_axis[1]
        min_proj, max_proj = np.min(proj), np.max(proj)
        bins = np.arange(min_proj, max_proj + block_length, block_length)
        blocks = []
        for i in range(len(bins) - 1):
            mask = (proj >= bins[i]) & (proj < bins[i + 1])
            if np.sum(mask) == 0:
                continue
            blocks.append(points[mask])
        return blocks

    def extract_powerlines_csf_pca_blockwise(self, file_path, output_file, use_csf=True, block_length=200):
        """
        分块提取电力线点（CSF+PCA+特征），并保存彩色点云。
        参数：
            file_path (str): 输入点云文件路径
            output_file (str): 输出点云文件路径
            use_csf (bool): 是否使用CSF地面分离
            block_length (float): 分块长度
        用法：
            handler.extract_powerlines_csf_pca_blockwise(infile, outfile)
        """
        import open3d as o3d
        from sklearn.decomposition import PCA
        from sklearn.cluster import DBSCAN
        from sklearn.neighbors import NearestNeighbors
        try:
            logger.info(f"读取点云文件: {file_path}")
            points, colors, intensity = self.read_point_cloud(file_path)
            logger.info(f"点云总点数: {len(points)}")
            blocks = self.split_pointcloud_by_main_direction(points, block_length=block_length)
            logger.info(f"分块数量: {len(blocks)}，每块长度: {block_length}")
            all_ground_points = []
            all_line_points = []
            all_tower_points = []
            for idx, block in enumerate(blocks):
                logger.info(f"处理第{idx+1}/{len(blocks)}块，点数: {len(block)}")
                if len(block) < 50:
                    logger.info(f"第{idx+1}块点数过少，跳过")
                    continue
                if use_csf:
                    try:
                        from CSF import CSF
                        csf = CSF()
                        csf.setPointCloud(block)
                        csf.params.bSloopSmooth = True
                        csf.params.cloth_resolution = 1.0
                        csf.params.rigidness = 3
                        csf.params.time_step = 0.65
                        csf.params.class_threshold = 0.5
                        csf.do_filtering()
                        ground_idx = csf.groundIndexes()
                        non_ground_idx = csf.offGroundIndexes()
                        ground_points = block[ground_idx]
                        non_ground_points = block[non_ground_idx]
                        logger.info(f"第{idx+1}块CSF分离: 地面点{len(ground_points)}，非地面点{len(non_ground_points)}")
                    except Exception as e:
                        logger.warning(f"第{idx+1}块CSF不可用，切换为z分位数过滤: {e}")
                        z_thresh = np.percentile(block[:, 2], 30)
                        ground_mask = block[:, 2] <= z_thresh
                        ground_points = block[ground_mask]
                        non_ground_points = block[~ground_mask]
                        logger.info(f"第{idx+1}块z分位数分离: 地面点{len(ground_points)}，非地面点{len(non_ground_points)}")
                else:
                    z_thresh = np.percentile(block[:, 2], 30)
                    ground_mask = block[:, 2] <= z_thresh
                    ground_points = block[ground_mask]
                    non_ground_points = block[~ground_mask]
                    logger.info(f"第{idx+1}块z分位数分离: 地面点{len(ground_points)}，非地面点{len(non_ground_points)}")
                k = 20
                if len(non_ground_points) < k:
                    logger.info(f"第{idx+1}块非地面点过少，跳过")
                    continue
                nbrs = NearestNeighbors(n_neighbors=k).fit(non_ground_points)
                _, indices = nbrs.kneighbors(non_ground_points)
                features = []
                for idx2, idxs in enumerate(indices):
                    neighbors = non_ground_points[idxs]
                    cov = np.cov(neighbors.T)
                    eigvals, _ = np.linalg.eigh(cov)
                    eigvals = np.sort(eigvals)[::-1]
                    linearity = (eigvals[0] - eigvals[1]) / (eigvals[0] + 1e-8)
                    planarity = (eigvals[1] - eigvals[2]) / (eigvals[0] + 1e-8)
                    scattering = eigvals[2] / (eigvals[0] + 1e-8)
                    features.append([linearity, planarity, scattering])
                features = np.array(features)
                mask = (features[:, 0] > 0.8) & (features[:, 1] < 0.15) & (features[:, 2] < 0.05)
                line_points = non_ground_points[mask]
                logger.info(f"第{idx+1}块电力线候选点: {len(line_points)}")
                if len(line_points) > 0:
                    all_line_points.append(line_points)
                if len(ground_points) > 0:
                    all_ground_points.append(ground_points)
                tower_points = self.fit_towers_dbscan(non_ground_points)
                logger.info(f"第{idx+1}块电力塔簇数: {len(tower_points)}")
                if len(tower_points) > 0:
                    all_tower_points.extend(tower_points)
            all_points = []
            all_colors = []
            if all_ground_points:
                merged_ground = np.vstack(all_ground_points)
                all_points.append(merged_ground)
                all_colors.append(np.tile([0.0, 1.0, 0.0], (len(merged_ground), 1)))
                logger.info(f"合并地面点总数: {len(merged_ground)}")
            if all_line_points:
                merged_line = np.vstack(all_line_points)
                all_points.append(merged_line)
                all_colors.append(np.tile([1.0, 0.0, 0.0], (len(merged_line), 1)))
                logger.info(f"合并电力线点总数: {len(merged_line)}")
            if all_tower_points:
                merged_tower = np.vstack(all_tower_points)
                all_points.append(merged_tower)
                all_colors.append(np.tile([0.0, 0.0, 1.0], (len(merged_tower), 1)))
                logger.info(f"合并电力塔点总数: {len(merged_tower)}")
            if all_points:
                merged_points = np.vstack(all_points)
                merged_colors = np.vstack(all_colors)
                pcd = o3d.geometry.PointCloud()
                pcd.points = o3d.utility.Vector3dVector(merged_points)
                pcd.colors = o3d.utility.Vector3dVector(merged_colors)
                o3d.io.write_point_cloud(output_file, pcd)
                logger.info(f"分块电力线点提取完成，结果已保存到: {output_file}")
                logger.info(f"最终总点数: {len(merged_points)}")
            else:
                logger.warning("未检测到有效点，终止保存。")
        except Exception as e:
            logger.error(f"分块电力线点提取流程出错: {e}")
            import traceback
            traceback.print_exc()

    def reconstruct_mesh(self, input_path, output_path=None, depth=9, scale=1.1):
        """
        使用Poisson重建将点云转为三角网格。
        参数：
            input_path (str): 输入点云文件路径
            output_path (str|None): 输出网格文件路径
            depth (int): Poisson重建深度
            scale (float): Poisson重建缩放
        返回：
            mesh (TriangleMesh): 重建后的网格
            output_path (str|None): 输出路径
        用法：
            mesh, path = handler.reconstruct_mesh(infile, outfile)
        """
        import open3d as o3d
        import numpy as np
        try:
            logger.info(f"开始读取点云文件: {input_path}")
            pcd = o3d.io.read_point_cloud(str(input_path))
            if not pcd.has_points():
                raise ValueError("点云数据为空")
            logger.info(f"点云读取完成，点数: {len(pcd.points)}")
            # 法向量估计
            logger.info("开始估计法向量...")
            pcd.estimate_normals(
                search_param=o3d.geometry.KDTreeSearchParamHybrid(
                    radius=0.1,
                    max_nn=30
                )
            )
            logger.info("法向量估计完成。开始法向量方向一致化...")
            pcd.orient_normals_consistent_tangent_plane(100)
            logger.info("法向量方向一致化完成。开始Poisson重建...")
            # Poisson重建
            mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
                pcd, depth=depth, width=0, scale=scale, linear_fit=False
            )
            logger.info(f"Poisson重建完成，网格顶点数: {len(mesh.vertices)}，面片数: {len(mesh.triangles)}")
            # 可选：去除低密度伪面片
            densities = np.asarray(densities)
            vertices_to_remove = densities < np.quantile(densities, 0.01)
            mesh.remove_vertices_by_mask(vertices_to_remove)
            logger.info(f"去除低密度伪面片后，剩余顶点数: {len(mesh.vertices)}，面片数: {len(mesh.triangles)}")
            # 保存
            if output_path:
                o3d.io.write_triangle_mesh(str(output_path), mesh)
                logger.info(f"网格已保存到: {output_path}")
            return mesh, output_path
        except Exception as e:
            logger.error(f"重建失败: {e}")
            raise

    def reconstruct_mesh_alpha_shape(self, input_path, output_path=None, alpha=0.5):
        """
        基于α-Shape的三维重建。
        参数：
            input_path (str): 输入点云文件路径
            output_path (str|None): 输出网格文件路径
            alpha (float): α-Shape参数
        返回：
            mesh (TriangleMesh): 重建后的网格
            output_path (str|None): 输出路径
        用法：
            mesh, path = handler.reconstruct_mesh_alpha_shape(infile, outfile, alpha=0.5)
        """
        import open3d as o3d
        try:
            logger.info(f"开始读取点云文件: {input_path}")
            pcd = o3d.io.read_point_cloud(str(input_path))
            if not pcd.has_points():
                raise ValueError("点云数据为空")
            logger.info(f"点云读取完成，点数: {len(pcd.points)}")
            mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_alpha_shape(pcd, alpha)
            mesh.compute_vertex_normals()
            logger.info(f"α-Shape重建完成，网格顶点数: {len(mesh.vertices)}，面片数: {len(mesh.triangles)}")
            if output_path:
                o3d.io.write_triangle_mesh(str(output_path), mesh)
                logger.info(f"网格已保存到: {output_path}")
            return mesh, output_path
        except Exception as e:
            logger.error(f"α-Shape重建失败: {e}")
            raise

    def reconstruct_mesh_ball_pivoting(self, input_path, output_path=None, radii=[0.1, 0.2, 0.4]):
        """
        基于Ball Pivoting的三维重建。
        参数：
            input_path (str): 输入点云文件路径
            output_path (str|None): 输出网格文件路径
            radii (list): 球半径列表
        返回：
            mesh (TriangleMesh): 重建后的网格
            output_path (str|None): 输出路径
        用法：
            mesh, path = handler.reconstruct_mesh_ball_pivoting(infile, outfile, radii=[0.1,0.2,0.4])
        """
        import open3d as o3d
        try:
            logger.info(f"开始读取点云文件: {input_path}")
            pcd = o3d.io.read_point_cloud(str(input_path))
            if not pcd.has_points():
                raise ValueError("点云数据为空")
            logger.info(f"点云读取完成，点数: {len(pcd.points)}")
            pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))
            mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
                pcd, o3d.utility.DoubleVector(radii))
            mesh.compute_vertex_normals()
            logger.info(f"Ball Pivoting重建完成，网格顶点数: {len(mesh.vertices)}，面片数: {len(mesh.triangles)}")
            if output_path:
                o3d.io.write_triangle_mesh(str(output_path), mesh)
                logger.info(f"网格已保存到: {output_path}")
            return mesh, output_path
        except Exception as e:
            logger.error(f"Ball Pivoting重建失败: {e}")
            raise

    def reconstruct_mesh_blockwise(self, input_path, output_dir, block_length=200, depth=9, scale=1.1):
        """
        分块三维重建：将点云分块后分别进行Poisson重建。
        参数：
            input_path (str): 输入点云文件路径
            output_dir (str): 输出网格文件夹
            block_length (float): 分块长度
            depth (int): Poisson重建深度
            scale (float): Poisson重建缩放
        返回：
            mesh_paths (list): 所有块的网格文件路径列表
        用法：
            mesh_paths = handler.reconstruct_mesh_blockwise(infile, outdir)
        """
        import os
        import open3d as o3d
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            points, _, _ = self.read_point_cloud(input_path)
            blocks = self.split_pointcloud_by_main_direction(points, block_length=block_length)
            mesh_paths = []
            for i, block in enumerate(blocks):
                if len(block) < 100:
                    logger.info(f"第{i+1}块点数过少，跳过")
                    continue
                logger.info(f"开始处理第{i+1}块，点数: {len(block)}")
                pcd = o3d.geometry.PointCloud()
                pcd.points = o3d.utility.Vector3dVector(block)
                # 可选：下采样
                pcd = pcd.voxel_down_sample(voxel_size=0.2)
                logger.info(f"下采样后点数: {len(pcd.points)}")
                # 保存临时点云
                block_path = os.path.join(output_dir, f"block_{i+1}.ply")
                o3d.io.write_point_cloud(block_path, pcd)
                # 重建
                mesh_path = os.path.join(output_dir, f"block_{i+1}_mesh.ply")
                try:
                    self.reconstruct_mesh(block_path, mesh_path, depth=depth, scale=scale)
                    mesh_paths.append(mesh_path)
                    logger.info(f"第{i+1}块重建完成，网格已保存到: {mesh_path}")
                except Exception as e:
                    logger.warning(f"第{i+1}块重建失败: {e}")
            logger.info(f"分块重建完成，总块数: {len(mesh_paths)}")
            return mesh_paths
        except Exception as e:
            logger.error(f"分块重建流程出错: {e}")
            import traceback
            traceback.print_exc()
            return []
        
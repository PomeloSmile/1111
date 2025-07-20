from pointcloud_predictor import PointCloudHandler

if __name__ == "__main__":
    # 1. 设置模型路径和点云文件路径
    model_path = "best_model.pth"  # 你的模型文件
    test_file = "Datasets/B线路已抽稀/B线路已抽稀.las"         # 你的点云文件（支持ply/las/laz）
    output_file = "output/result_powerline_span.ply"  # 预测结果保存路径
    output_dir = "output/result_powerline.ply"
    # 2. 初始化处理器
    handler = PointCloudHandler()

    # 3. 选择预测方式（按需选择）  已经有预测的结果了，这部分代码不用动
    # result = handler.predict_streaming_by_grid(test_file, grid_size=200)
    # result = handler.predict_streaming_by_direction(test_file, segment_length=200)

    # 4. 保存预测结果
    #handler.extract_powerlines_csf_pca(test_file, output_file,use_csf=False)
    #handler.extract_powerlines_csf_pca_blockwise(test_file, output_file, use_csf=False, block_length=200)
    #print("电力线提取完成，结果已保存到：", output_file)
    #os.makedirs(output_dir, exist_ok=True)
    
    #三维重建
    mesh_paths = handler.reconstruct_mesh_blockwise(output_file, output_dir, block_length=200, depth=9, scale=1.1)
    print("分块重建完成，网格文件：", mesh_paths)
    handler.rebuild(test_file)
    #可视化其中一块
    import open3d as o3d
    if mesh_paths:
        mesh = o3d.io.read_triangle_mesh(mesh_paths[0])
        o3d.visualization.draw_geometries([mesh], window_name="分块三维重建网格可视化")
   
   
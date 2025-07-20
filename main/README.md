# 点云处理前端系统
## ​前端vue环境搭建
1) Nodejs version=22.16.0 LST 下载链接​https://nodejs.org/zh-cn
2) vue
## vue 安装
1) 安装Nodejs
2) win+r打开终端 切换镜像输入npm config set registry ​https://registry.npmmirror.com/
3) 输入npm install -g ​@​vue/cli
## ​vue项目创建
1) 打开vscode并进入项目文件夹
2) 左下角打开终端
3) 输入 vue create your-vue-project name
4) 后续具体操作引用 【vue环境的搭建以及vue项目的创建与启动】 ​https://www.bilibili.com/video/BV1A3411g7f7/?share_source=copy_web&vd_source=d22dd1eb12bdb58e09987ad49067182a
## 项目简介
这是一个基于 Vue 3 的点云处理前端系统，提供友好的用户界面用于上传和处理点云数据，并实时显示处理结果。

## 功能特点
- 支持 LAS 文件上传
- 实时点云处理状态显示
- WebSocket 实时通信
- 响应式设计
- 现代化的用户界面

## 技术栈
- Vue 3
- Element Plus
- WebSocket
- Less
- Vue Router
- Vuex

## 项目设置
```bash
# 安装依赖
npm install

# 开发环境运行
npm run serve

# 生产环境构建
npm run build

# 代码检查
npm run lint
```

## 项目结构
```
src/
├── assets/        # 静态资源
├── components/    # 组件
├── router/        # 路由配置
├── store/         # Vuex状态管理
├── views/         # 页面视图
└── App.vue        # 根组件
```

## 主要组件
- `PointCloudProcessor.vue`: 点云处理组件
  - 文件上传
  - 处理状态显示
  - 结果可视化

## 使用说明
1. 启动开发服务器
2. 访问 `http://localhost:8080`
3. 上传 LAS 文件
4. 点击处理按钮
5. 等待处理结果

## 配置说明
- WebSocket 连接地址：`ws://localhost:8080/ws`
- 支持的文件格式：`.las`
- 最大文件大小：建议不超过 100MB

## 开发指南
1. 组件开发
   - 使用 Composition API
   - 遵循 Vue 3 最佳实践
   - 使用 TypeScript 类型定义

2. 样式开发
   - 使用 Less 预处理器
   - 遵循 BEM 命名规范
   - 响应式设计

3. 状态管理
   - 使用 Vuex 管理全局状态
   - 模块化状态管理
   - 异步操作处理

## 性能优化
- 组件懒加载
- 资源压缩
- 缓存策略
- 按需加载

## 错误处理
- 文件上传错误处理
- WebSocket 连接错误处理
- 处理失败错误处理
- 用户友好的错误提示

## 浏览器支持
- Chrome (推荐)
- Firefox
- Safari
- Edge

## 开发计划
- [ ] 添加更多文件格式支持
- [ ] 优化点云可视化
- [ ] 添加处理参数配置界面
- [ ] 添加处理历史记录
- [ ] 添加结果导出功能
- [ ] 添加批处理功能
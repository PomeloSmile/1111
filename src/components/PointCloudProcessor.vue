<template>
  <div class="point-cloud-processor" ref="containerRef">
    <el-card class="control-panel">
      <template #header>
        <div class="card-header">
          <span>点云处理控制面板</span>
        </div>
      </template>
      
      <el-upload
        class="upload-demo"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :before-upload="beforeUpload"
        :show-file-list="false"
        accept=".las,.laz,.ply"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 .las 或 .laz 格式的点云文件
          </div>
        </template>
      </el-upload>

      <el-divider>处理参数</el-divider>

      <el-form :model="form" label-position="top">
        <el-form-item label="体素大小">
          <el-slider
            v-model="form.voxelSize"
            :min="0.01"
            :max="1"
            :step="0.01"
            :format-tooltip="formatVoxelSize"
          />
        </el-form-item>

        <el-form-item label="距离阈值">
          <el-slider
            v-model="form.distanceThreshold"
            :min="0.1"
            :max="2"
            :step="0.1"
            :format-tooltip="formatDistanceThreshold"
          />
        </el-form-item>

        <el-form-item label="点大小">
          <el-slider
            v-model="form.pointSize"
            :min="0.01"
            :max="0.2"
            :step="0.01"
            :format-tooltip="formatPointSize"
          />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="processing"
            :disabled="!selectedFile"
            @click="processPointCloud"
            class="action-button"
          >
            开始处理
          </el-button>
          <el-button
            type="success"
            :loading="reconstructing"
            :disabled="!selectedFile"
            @click="startReconstruction"
            class="action-button"
          >
            开始重建
          </el-button>
          <el-button
            type="info"
            :disabled="!!selectedFile"
            @click="resetView"
            class="action-button"
          >
            重置视图
          </el-button>
          <el-button
            type="warning"
            @click="showReconstructionList"
            class="action-button"
          >
            重建历史
          </el-button>
        </el-form-item>
      </el-form>

      <el-progress
        v-if="processing"
        :percentage="progress"
        :status="progressStatus === '处理失败' ? 'exception' : progressStatus === '重建完成' ? 'success' : ''"
        :format="progressFormat"
      >
        <template #default>
          <span class="progress-text">{{ progressText }}</span>
        </template>
      </el-progress>

      <div v-if="stats" class="stats-panel">
        <h3>处理统计</h3>
        <p>总点数: {{ stats.total_points }}</p>
        <p>电力线点数: {{ stats.powerline_points }}</p>
        <p>非电力线点数: {{ stats.non_powerline_points }}</p>
        <p>电力线比例: {{ (stats.powerline_ratio * 100).toFixed(2) }}%</p>
      </div>
    </el-card>

    <div class="main-content">
      <el-card class="viewer-panel">
        <template #header>
          <div class="card-header">
            <span>点云可视化</span>
            <div class="viewer-controls">
              <el-button-group>
                <el-tooltip content="重置视图" placement="top">
                  <el-button size="small" @click="resetView">
                    <el-icon><refresh /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="全屏显示" placement="top">
                  <el-button size="small" @click="toggleFullscreen">
                    <el-icon><full-screen /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip content="切换重建模式" placement="top">
                  <el-button size="small" @click="toggleReconstructionMode">
                    <el-icon><connection /></el-icon>
                  </el-button>
                </el-tooltip>
              </el-button-group>
            </div>
          </div>
        </template>
        
        <div class="viewer-container">
          <point-cloud-viewer 
            :points="processedData"
            :show-points="showPointCloud"
            :point-size="pointSize"
            :reconstruction-mode="reconstructionMode"
            :analysis-data="analysisData"
            ref="viewerRef"
          />
        </div>
      </el-card>

      <el-card class="analysis-panel" v-if="analysisData">
        <template #header>
          <div class="card-header">
            <span>点云分析结果</span>
          </div>
        </template>

        <el-tabs>
          <el-tab-pane label="基本信息">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="点云数量">
                {{ analysisData.analysis.point_count }}
              </el-descriptions-item>
              <el-descriptions-item label="点云密度">
                {{ analysisData.analysis.density.toFixed(4) }} 点/立方米
              </el-descriptions-item>
              <el-descriptions-item label="聚类数量">
                {{ analysisData.cluster_count }}
              </el-descriptions-item>
            </el-descriptions>

            <div class="dimensions-info">
              <h4>点云尺寸</h4>
              <el-descriptions :column="1" border>
                <el-descriptions-item label="X轴范围">
                  {{ analysisData.analysis.dimensions.x_range.toFixed(2) }} 米
                </el-descriptions-item>
                <el-descriptions-item label="Y轴范围">
                  {{ analysisData.analysis.dimensions.y_range.toFixed(2) }} 米
                </el-descriptions-item>
                <el-descriptions-item label="Z轴范围">
                  {{ analysisData.analysis.dimensions.z_range.toFixed(2) }} 米
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-tab-pane>

          <el-tab-pane label="特征分析">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="平均线性度">
                {{ analysisData.features.global_features.mean_linearity.toFixed(4) }}
              </el-descriptions-item>
              <el-descriptions-item label="平均平面度">
                {{ analysisData.features.global_features.mean_planarity.toFixed(4) }}
              </el-descriptions-item>
              <el-descriptions-item label="平均球度">
                {{ analysisData.features.global_features.mean_sphericity.toFixed(4) }}
              </el-descriptions-item>
            </el-descriptions>

            <div class="feature-description">
              <h4>特征说明</h4>
              <p>线性度：表示点云局部区域的线性程度，值越接近1表示越线性</p>
              <p>平面度：表示点云局部区域的平面程度，值越接近1表示越平面</p>
              <p>球度：表示点云局部区域的球形程度，值越接近1表示越球形</p>
            </div>
          </el-tab-pane>

          <el-tab-pane label="边界框">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="最小坐标">
                X: {{ analysisData.analysis.bounding_box.min[0].toFixed(2) }}
                Y: {{ analysisData.analysis.bounding_box.min[1].toFixed(2) }}
                Z: {{ analysisData.analysis.bounding_box.min[2].toFixed(2) }}
              </el-descriptions-item>
              <el-descriptions-item label="最大坐标">
                X: {{ analysisData.analysis.bounding_box.max[0].toFixed(2) }}
                Y: {{ analysisData.analysis.bounding_box.max[1].toFixed(2) }}
                Z: {{ analysisData.analysis.bounding_box.max[2].toFixed(2) }}
              </el-descriptions-item>
              <el-descriptions-item label="中心点">
                X: {{ analysisData.analysis.bounding_box.center[0].toFixed(2) }}
                Y: {{ analysisData.analysis.bounding_box.center[1].toFixed(2) }}
                Z: {{ analysisData.analysis.bounding_box.center[2].toFixed(2) }}
              </el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>

    <!-- 重建结果列表对话框 -->
    <el-dialog
      v-model="showReconstructionDialog"
      title="重建结果列表"
      width="70%"
    >
      <el-table :data="reconstructionList" style="width: 100%">
        <el-table-column prop="timestamp" label="时间" width="180">
          <template #default="scope">
            {{ formatTimestamp(scope.row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="original_filename" label="原始文件" />
        <el-table-column prop="point_count" label="点数" width="120" />
        <el-table-column prop="file_size" label="文件大小" width="120">
          <template #default="scope">
            {{ formatFileSize(scope.row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button
              size="small"
              @click="downloadReconstruction(scope.row)"
            >
              下载
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="deleteReconstruction(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 添加处理状态显示 -->
    <div v-if="processingStatus" class="processing-status">
      <el-card class="status-card">
        <div class="status-header">
          <h3>处理状态</h3>
          <el-button 
            v-if="isProcessing" 
            type="danger" 
            size="small" 
            @click="cancelProcessing"
          >
            取消处理
          </el-button>
        </div>
        <div class="status-content">
          <el-steps :active="currentStep" finish-status="success" simple>
            <el-step title="上传" :description="uploadStatus"></el-step>
            <el-step title="预处理" :description="preprocessStatus"></el-step>
            <el-step title="预测" :description="predictStatus"></el-step>
            <el-step title="重建" :description="reconstructStatus"></el-step>
          </el-steps>
          <div v-if="processingProgress > 0" class="progress-bar">
            <el-progress 
              :percentage="processingProgress" 
              :status="progressStatus"
            ></el-progress>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 添加结果预览 -->
    <div v-if="reconstructionResult" class="result-preview">
      <el-card class="preview-card">
        <template #header>
          <div class="card-header">
            <span>重建结果</span>
            <el-button 
              style="float: right; padding: 3px 0" 
              type="text"
              @click="downloadReconstruction"
            >
              下载结果
            </el-button>
          </div>
        </template>
        <div class="preview-content">
          <p>点云数量: {{ reconstructionResult.point_count }}</p>
          <p>三角形数量: {{ reconstructionResult.triangle_count }}</p>
        </div>
      </el-card>
    </div>

    <!-- 添加处理日志显示区域 -->
    <div class="processing-log" v-if="processing || logs.length > 0">
      <div class="log-header">
        <h3>处理日志</h3>
        <div class="log-actions">
          <el-button type="text" @click="clearLogs" v-if="logs.length > 0">清除日志</el-button>
          <el-button type="text" @click="toggleLogWindow" class="toggle-btn">
            {{ isLogWindowCollapsed ? '展开' : '收起' }}
          </el-button>
        </div>
      </div>
      <div class="log-content" ref="logContent" v-show="!isLogWindowCollapsed">
        <div v-for="(log, index) in logs" :key="index" :class="['log-item', log.type]">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>

    <!-- 添加日志窗口切换按钮 -->
    <div class="log-toggle" @click="toggleLogWindow">
      <i :class="['el-icon-document', showLogWindow ? 'active' : '']"></i>
    </div>
  </div>
</template>

<script>
import { ref, reactive, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  UploadFilled,
  Refresh,
  FullScreen,
  Connection
} from '@element-plus/icons-vue'
import PointCloudViewer from './PointCloudViewer.vue'

export default {
  name: 'PointCloudProcessor',
  components: {
    PointCloudViewer,
    UploadFilled,
    Refresh,
    FullScreen,
    Connection
  },
  setup() {
    const containerRef = ref(null)
    const viewerRef = ref(null)
    const selectedFile = ref(null)
    const processedData = ref([])
    const processing = ref(false)
    const progress = ref(0)
    const progressText = ref('')
    const progressStatus = ref('')
    const showPointCloud = ref(true)
    const pointSize = ref(0.05)
    const reconstructionMode = ref(false)
    const analysisData = ref(null)
    const showReconstructionDialog = ref(false)
    const reconstructionList = ref([])
    const processingStatus = ref(false)
    const isProcessing = ref(false)
    const currentStep = ref(0)
    const processingProgress = ref(0)
    const uploadStatus = ref('等待中')
    const preprocessStatus = ref('等待中')
    const predictStatus = ref('等待中')
    const reconstructStatus = ref('等待中')
    const reconstructionResult = ref(null)
    const cancelToken = ref(null)
    const stats = ref(null)
    const potreeData = ref(null)
    const logs = ref([])
    const isLogWindowCollapsed = ref(false)
    const showLogWindow = ref(true)
    const reconstructing = ref(false)

    const form = reactive({
      voxelSize: 0.1,
      distanceThreshold: 0.5,
      pointSize: 0.05
    })

    const formatVoxelSize = (val) => {
      return `${val.toFixed(2)} 米`
    }

    const formatDistanceThreshold = (val) => {
      return `${val.toFixed(2)} 米`
    }

    const formatPointSize = (val) => {
      return `${val.toFixed(2)}`
    }

    const progressFormat = (percentage) => `${percentage}%`

    const updateProgress = (value, status) => {
      progress.value = value
      progressStatus.value = status
    }

    const handleFileChange = (file) => {
      selectedFile.value = file.raw || file
    }

    const beforeUpload = (file) => {
      const isLAS = file.name.endsWith('.las') || file.name.endsWith('.laz') || file.name.endsWith('.ply')
      if (!isLAS) {
        ElMessage.error('只能上传 .las、.laz 或 .ply 文件!')
        return false
      }
      selectedFile.value = file
      return true
    }

    const processPointCloud = async () => {
      if (!selectedFile.value) {
        ElMessage.warning('请先选择文件')
        return
      }

      processing.value = true
      progress.value = 0
      progressText.value = '准备处理...'
      addLog('开始处理点云文件...')

      try {
        const formData = new FormData()
        formData.append('file', selectedFile.value)
        formData.append('voxel_size', form.voxelSize)
        formData.append('distance_threshold', form.distanceThreshold)
        formData.append('point_size', form.pointSize)

        addLog('正在上传文件...')
        const response = await fetch('/api/predict', {
          method: 'POST',
          body: formData
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const result = await response.json()
        addLog('文件上传成功，开始处理...')

        // 更新进度
        progress.value = 50
        progressText.value = '处理中...'

        // 显示后端返回的日志
        if (result.logs) {
          result.logs.forEach(log => {
            addLog(log.message, log.type)
          })
        }

        // 处理返回的数据
        if (result.points) {
          addLog(`处理完成，共 ${result.points.length} 个点`)
          updateViewer(result.points)
        }

        // 更新统计信息
        if (result.stats) {
          stats.value = result.stats
        }

        progress.value = 100
        progressText.value = '处理完成'
        addLog('处理完成', 'success')

      } catch (error) {
        console.error('处理失败:', error)
        addLog(`处理失败: ${error.message}`, 'error')
        ElMessage.error(`处理失败: ${error.message}`)
        progressStatus.value = 'exception'
        progressText.value = '处理失败'
      } finally {
        processing.value = false
      }
    }

    const showReconstructionList = async () => {
      try {
        const response = await fetch('/api/reconstructions')
        if (!response.ok) {
          throw new Error('获取重建结果列表失败')
        }
        reconstructionList.value = await response.json()
        showReconstructionDialog.value = true
      } catch (error) {
        console.error('获取重建结果列表失败:', error)
        ElMessage.error(error.message || '获取重建结果列表失败')
      }
    }

    const downloadReconstruction = async (item) => {
      try {
        const response = await fetch(`/api/reconstructions/${item.filename}`)
        if (!response.ok) {
          throw new Error('下载重建结果失败')
        }
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = item.filename
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        ElMessage.success('下载成功')
      } catch (error) {
        console.error('下载重建结果失败:', error)
        ElMessage.error(error.message || '下载重建结果失败')
      }
    }

    const deleteReconstruction = async (item) => {
      try {
        await ElMessageBox.confirm(
          '确定要删除这个重建结果吗？',
          '删除确认',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )
        
        const response = await fetch(`/api/reconstructions/${item.filename}`, {
          method: 'DELETE'
        })
        
        if (!response.ok) {
          throw new Error('删除重建结果失败')
        }
        
        // 更新列表
        reconstructionList.value = reconstructionList.value.filter(
          x => x.filename !== item.filename
        )
        
        ElMessage.success('删除成功')
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除重建结果失败:', error)
          ElMessage.error(error.message || '删除重建结果失败')
        }
      }
    }

    const formatTimestamp = (timestamp) => {
      const date = new Date(timestamp.replace(/(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/, '$1-$2-$3T$4:$5:$6'))
      return date.toLocaleString()
    }

    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }

    const resetView = () => {
      if (viewerRef.value) {
        viewerRef.value.resetView()
      }
    }

    const toggleFullscreen = () => {
      if (containerRef.value) {
        if (!document.fullscreenElement) {
          containerRef.value.requestFullscreen()
        } else {
          document.exitFullscreen()
        }
      }
    }

    const toggleReconstructionMode = () => {
      reconstructionMode.value = !reconstructionMode.value
    }

    const updateViewer = (points) => {
      processedData.value = points
      if (viewerRef.value) {
        viewerRef.value.updatePoints(points)
      }
    }

    const cancelProcessing = () => {
      if (cancelToken.value) {
        cancelToken.value.cancel('用户取消处理')
      }
    }

    const toggleLogWindow = () => {
      isLogWindowCollapsed.value = !isLogWindowCollapsed.value
    }

    const addLog = (message, type = 'info') => {
      const now = new Date()
      const time = now.toLocaleTimeString()
      logs.value.push({
        time,
        message,
        type
      })
      // 自动滚动到底部
      nextTick(() => {
        const logContent = document.querySelector('.log-content')
        if (logContent) {
          logContent.scrollTop = logContent.scrollHeight
        }
      })
    }

    const clearLogs = () => {
      logs.value = []
    }

    const startReconstruction = async () => {
      if (!selectedFile.value) {
        ElMessage.warning('请先选择点云文件')
        return
      }

      reconstructing.value = true
      addLog('开始三维重建...')

      try {
        // 直接上传原始点云文件
        const formData = new FormData()
        formData.append('file', selectedFile.value)

        addLog('正在上传点云数据进行重建...')
        const response = await fetch('/api/reconstruct', {
          method: 'POST',
          body: formData
        })

        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`重建失败: ${errorText}`)
        }

        const result = await response.json()
        addLog('重建完成')

        reconstructionResult.value = result
        ElMessage.success('三维重建完成')
        showReconstructionResult(result)

        // 自动加载 mesh
        if (viewerRef.value && result.mesh_path) {
          viewerRef.value.loadMesh(result.mesh_path)
          addLog('已自动加载重建Mesh到可视化窗口', 'success')
        }
      } catch (error) {
        addLog(`重建失败: ${error.message}`, 'error')
        ElMessage.error('重建失败: ' + error.message)
      } finally {
        reconstructing.value = false
      }
    }

    const convertToPLY = (points) => {
      // 简单的PLY格式转换
      const header = `ply
format ascii 1.0
element vertex ${points.length}
property float x
property float y
property float z
end_header
`
      
      const pointData = points.map(point => 
        `${point.x} ${point.y} ${point.z}`
      ).join('\n')
      
      return header + pointData
    }

    const showReconstructionResult = (result) => {
      // 显示重建结果的详细信息
      ElMessageBox.alert(
        `重建完成！\n点云数量: ${result.point_count}\n三角形数量: ${result.triangle_count}\n文件名: ${result.filename}`,
        '重建结果',
        {
          confirmButtonText: '确定',
          type: 'success'
        }
      )
    }

    return {
      containerRef,
      viewerRef,
      selectedFile,
      processedData,
      processing,
      progress,
      progressText,
      progressStatus,
      showPointCloud,
      pointSize,
      reconstructionMode,
      analysisData,
      form,
      formatVoxelSize,
      formatDistanceThreshold,
      formatPointSize,
      progressFormat,
      updateProgress,
      handleFileChange,
      beforeUpload,
      processPointCloud,
      showReconstructionDialog,
      reconstructionList,
      showReconstructionList,
      downloadReconstruction,
      deleteReconstruction,
      formatTimestamp,
      formatFileSize,
      resetView,
      toggleFullscreen,
      toggleReconstructionMode,
      processingStatus,
      isProcessing,
      currentStep,
      processingProgress,
      uploadStatus,
      preprocessStatus,
      predictStatus,
      reconstructStatus,
      reconstructionResult,
      cancelProcessing,
      stats,
      potreeData,
      logs,
      addLog,
      clearLogs,
      isLogWindowCollapsed,
      toggleLogWindow,
      showLogWindow,
      reconstructing,
      startReconstruction,
      convertToPLY,
      showReconstructionResult,
      updateViewer
    }
  }
}
</script>

<style scoped>
.point-cloud-processor {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 20px;
  gap: 20px;
}

.control-panel {
  width: 100%;
  max-width: 400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-area {
  width: 100%;
  margin-bottom: 20px;
}

.control-form {
  margin-top: 20px;
}

.action-button {
  width: 100%;
  margin-bottom: 10px;
}

.progress-text {
  margin-top: 10px;
  text-align: center;
  color: #606266;
}

.main-content {
  flex: 1;
  display: flex;
  gap: 20px;
}

.viewer-panel {
  flex: 1;
  min-height: 500px;
}

.viewer-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
}

.viewer-controls {
  display: flex;
  gap: 10px;
}

.analysis-panel {
  width: 300px;
}

.dimensions-info {
  margin-top: 20px;
}

.feature-description {
  margin-top: 20px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.feature-description h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.feature-description p {
  margin: 5px 0;
  font-size: 14px;
  color: #606266;
}

.el-dialog {
  margin-top: 5vh !important;
}

.el-table {
  margin-top: 20px;
}

.processing-status {
  margin: 20px 0;
}

.status-card {
  margin-bottom: 20px;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.status-content {
  padding: 20px;
}

.progress-bar {
  margin-top: 20px;
}

.result-preview {
  margin-top: 20px;
}

.preview-card {
  margin-bottom: 20px;
}

.preview-content {
  padding: 10px;
}

.stats-panel {
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.stats-panel h3 {
  margin-top: 0;
  margin-bottom: 10px;
}

.stats-panel p {
  margin: 5px 0;
}

.processing-log {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 500px;
  max-height: 400px;
  background: rgba(0, 0, 0, 0.9);
  border-radius: 8px;
  color: #fff;
  padding: 15px;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
}

.log-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.log-actions {
  display: flex;
  gap: 8px;
}

.log-content {
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  line-height: 1.5;
}

.log-item {
  padding: 4px 0;
  display: flex;
  align-items: flex-start;
}

.log-time {
  color: #888;
  margin-right: 8px;
  flex-shrink: 0;
}

.log-message {
  flex-grow: 1;
  word-break: break-word;
}

.log-item.info {
  color: #fff;
}

.log-item.success {
  color: #67C23A;
}

.log-item.error {
  color: #F56C6C;
}

.log-item.warning {
  color: #E6A23C;
}

/* 自定义滚动条样式 */
.log-content::-webkit-scrollbar {
  width: 6px;
}

.log-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.log-content::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.log-content::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.4);
}

.toggle-btn {
  color: #fff;
  opacity: 0.7;
}

.toggle-btn:hover {
  opacity: 1;
}

.log-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 400px;
  height: 300px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 1000;
}

.log-header {
  padding: 10px 15px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  border-radius: 8px 8px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.log-actions {
  display: flex;
  gap: 10px;
}

.log-content {
  flex: 1;
  padding: 10px;
  overflow-y: auto;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.5;
}

.log-item {
  margin-bottom: 5px;
  padding: 3px 5px;
  border-radius: 3px;
}

.log-time {
  color: #909399;
  margin-right: 8px;
}

.log-item.info {
  color: #606266;
}

.log-item.success {
  color: #67c23a;
}

.log-item.warning {
  color: #e6a23c;
}

.log-item.error {
  color: #f56c6c;
}

.log-toggle {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 40px;
  height: 40px;
  background: #409eff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: white;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  z-index: 999;
}

.log-toggle i {
  font-size: 20px;
}

.log-toggle i.active {
  color: #67c23a;
}

/* 自定义滚动条样式 */
.log-content::-webkit-scrollbar {
  width: 6px;
}

.log-content::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}

.log-content::-webkit-scrollbar-track {
  background: #f5f7fa;
}
</style> 
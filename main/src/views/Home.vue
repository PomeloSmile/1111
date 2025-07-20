<template>
  <div class="home-page">
    <div class="page-header">
      <h1>点云电力线提取系统</h1>
    </div>
    
    <div class="page-content">
      <div class="viewer-section">
        <PointCloudViewer
          ref="viewerRef"
          :potree-data="potreeData"
        />
        <div class="viewer-controls">
          <el-button-group>
            <el-button @click="resetView">
              <el-icon><refresh /></el-icon>
              重置视图
            </el-button>
            <el-button @click="toggleFullscreen">
              <el-icon><full-screen /></el-icon>
              {{ isFullscreen ? '退出全屏' : '全屏' }}
            </el-button>
          </el-button-group>
        </div>
      </div>
      
      <div class="control-section">
        <el-upload
          class="upload-area"
          drag
          action="/api/predict"
          :on-success="handleUploadSuccess"
          :on-error="handleUploadError"
          :before-upload="beforeUpload"
          :show-file-list="false"
        >
          <el-icon class="el-icon--upload"><upload-filled /></el-icon>
          <div class="el-upload__text">
            拖拽文件到此处或 <em>点击上传</em>
          </div>
          <template #tip>
            <div class="el-upload__tip">
              支持 .las 格式的点云文件
            </div>
          </template>
        </el-upload>

        <el-slider
          v-model="voxelSize"
          :min="0.1"
          :max="1.0"
          :step="0.1"
          :disabled="processing"
          @change="handleVoxelSizeChange"
        >
          <template #title>体素大小</template>
        </el-slider>

        <el-slider
          v-model="pointSize"
          :min="1"
          :max="10"
          :step="1"
          :disabled="processing"
          @change="handlePointSizeChange"
        >
          <template #title>点大小</template>
        </el-slider>

        <el-progress
          v-if="processing"
          :percentage="progress"
          :status="progressStatus"
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
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, FullScreen, UploadFilled } from '@element-plus/icons-vue'
import PointCloudViewer from '@/components/PointCloudViewer.vue'

export default {
  name: 'HomePage',
  components: {
    PointCloudViewer,
    Refresh,
    FullScreen,
    UploadFilled
  },
  setup() {
    const viewerRef = ref(null)
    const isFullscreen = ref(false)
    const processing = ref(false)
    const progress = ref(0)
    const progressText = ref('')
    const progressStatus = ref('')
    const stats = ref(null)
    const potreeData = ref(null)
    const voxelSize = ref(0.5)
    const pointSize = ref(2)

    const resetView = () => {
      viewerRef.value?.resetView()
    }

    const toggleFullscreen = () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen()
        isFullscreen.value = true
      } else {
        document.exitFullscreen()
        isFullscreen.value = false
      }
    }

    const beforeUpload = (file) => {
      const isLAS = file.name.endsWith('.las')
      if (!isLAS) {
        ElMessage.error('只能上传 LAS 文件!')
        return false
      }
      processing.value = true
      progress.value = 0
      progressText.value = '正在上传文件...'
      progressStatus.value = ''
      return true
    }

    const handleUploadSuccess = (response) => {
      try {
        stats.value = response.stats
        potreeData.value = response.potree_data
        progress.value = 100
        progressText.value = '处理完成'
        progressStatus.value = 'success'
      } catch (error) {
        handleUploadError(error)
      } finally {
        processing.value = false
      }
    }

    const handleUploadError = (error) => {
      processing.value = false
      progress.value = 0
      progressText.value = '处理失败'
      progressStatus.value = 'exception'
      ElMessage.error('处理失败: ' + error.message)
    }

    const handleVoxelSizeChange = () => {
      // TODO: 实现体素大小调整逻辑
    }

    const handlePointSizeChange = () => {
      // TODO: 实现点大小调整逻辑
    }

    return {
      viewerRef,
      isFullscreen,
      processing,
      progress,
      progressText,
      progressStatus,
      stats,
      potreeData,
      voxelSize,
      pointSize,
      resetView,
      toggleFullscreen,
      beforeUpload,
      handleUploadSuccess,
      handleUploadError,
      handleVoxelSizeChange,
      handlePointSizeChange
    }
  }
}
</script>

<style lang="scss" scoped>
.home-page {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  padding: 1rem;
  background-color: var(--background-color);
  border-bottom: 1px solid var(--border-color);
}

.page-header h1 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--text-color);
}

.page-content {
  flex: 1;
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1rem;
  padding: 1rem;
  overflow: hidden;
}

.viewer-section {
  position: relative;
  height: 100%;
  border: 1px solid var(--border-color);
  border-radius: 4px;
}

.viewer-controls {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 1;
}

.control-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  background-color: var(--background-color);
  border-radius: 4px;
}

.upload-area {
  width: 100%;
}

.stats-panel {
  padding: 1rem;
  background-color: white;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.stats-panel h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: var(--text-color);
}

.stats-panel p {
  margin: 0.5rem 0;
  color: var(--text-color);
}

.progress-text {
  font-size: 0.9rem;
  color: var(--text-color);
}
</style> 
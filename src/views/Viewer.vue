<template>
  <div class="viewer-page">
    <div class="viewer-header">
      <h2>点云查看器</h2>
      <div class="viewer-controls">
        <el-button-group>
          <el-button @click="resetView" icon="Refresh">重置视图</el-button>
          <el-button @click="toggleFullscreen" icon="FullScreen">
            {{ isFullscreen ? '退出全屏' : '全屏' }}
          </el-button>
        </el-button-group>
      </div>
    </div>
    
    <div class="viewer-content" :class="{ 'fullscreen': isFullscreen }">
      <PointCloudViewer
        ref="viewerRef"
        :potree-data="potreeData"
      />
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import PointCloudViewer from '@/components/PointCloudViewer.vue'

export default {
  name: 'ViewerPage',
  components: {
    PointCloudViewer
  },
  setup() {
    const viewerRef = ref(null)
    const isFullscreen = ref(false)
    const potreeData = ref(null)

    // 重置视图
    const resetView = () => {
      viewerRef.value?.resetView()
    }

    // 切换全屏
    const toggleFullscreen = () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen()
        isFullscreen.value = true
      } else {
        document.exitFullscreen()
        isFullscreen.value = false
      }
    }

    // 监听全屏变化
    document.addEventListener('fullscreenchange', () => {
      isFullscreen.value = !!document.fullscreenElement
    })

    return {
      viewerRef,
      isFullscreen,
      potreeData,
      resetView,
      toggleFullscreen
    }
  }
}
</script>

<style scoped>
.viewer-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #1a1a1a;
  color: #ffffff;
}

.viewer-header {
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #2a2a2a;
  border-bottom: 1px solid #3a3a3a;
}

.viewer-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.viewer-content {
  flex: 1;
  position: relative;
  transition: all 0.3s ease;
}

.viewer-content.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
}

:deep(.el-button) {
  background-color: #3a3a3a;
  border-color: #4a4a4a;
  color: #ffffff;
}

:deep(.el-button:hover) {
  background-color: #4a4a4a;
  border-color: #5a5a5a;
}
</style> 
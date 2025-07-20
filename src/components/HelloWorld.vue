<template>
  <div class="power-line-extraction">
    <el-container>
      <el-header>
        <h1>点云电力线提取系统</h1>
      </el-header>
      
      <el-main>
        <el-row :gutter="20">
          <el-col :span="16">
            <div class="viewer-container">
              <div ref="viewer" class="viewer"></div>
            </div>
          </el-col>
          
          <el-col :span="8">
            <el-card class="control-panel">
              <template #header>
                <div class="card-header">
                  <span>处理参数</span>
                </div>
              </template>
              <el-form :model="params" label-width="120px">
                <el-form-item label="点云密度阈值">
                  <el-input-number v-model="params.densityThreshold" :min="0" :max="100" :step="1"></el-input-number>
                </el-form-item>
                <el-form-item label="电力线最小长度">
                  <el-input-number v-model="params.minLineLength" :min="0" :max="1000" :step="1"></el-input-number>
                </el-form-item>
                <el-form-item label="聚类距离阈值">
                  <el-input-number v-model="params.clusterDistance" :min="0" :max="10" :step="0.1"></el-input-number>
                </el-form-item>
                <el-form-item>
                  <el-upload
                    class="upload-demo"
                    action="#"
                    :auto-upload="false"
                    :on-change="handlePointCloudUpload"
                    accept=".las,.laz,.xyz,.ply">
                    <el-button type="primary">选择点云文件</el-button>
                  </el-upload>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="processPointCloud">开始处理</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import { ElMessage } from 'element-plus'

export default {
  name: 'PowerLineExtraction',
  setup() {
    const viewer = ref(null)
    const scene = ref(null)
    const camera = ref(null)
    const renderer = ref(null)
    const controls = ref(null)
    const ws = ref(null)
    const isProcessing = ref(false)
    
    const params = ref({
      densityThreshold: 50,
      minLineLength: 100,
      clusterDistance: 0.5
    })

    const initWebSocket = () => {
      ws.value = new WebSocket('ws://localhost:8000/ws')
      
      ws.value.onopen = () => {
        console.log('WebSocket连接已建立')
        ElMessage.success('已连接到服务器')
      }
      
      ws.value.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'pointCloud') {
            loadPointCloud(data.points)
            isProcessing.value = false
            ElMessage.success('点云处理完成')
          } else if (data.type === 'error') {
            ElMessage.error(data.message)
            isProcessing.value = false
          }
        } catch (error) {
          console.error('处理WebSocket消息错误:', error)
          ElMessage.error('处理服务器响应时出错')
          isProcessing.value = false
        }
      }
      
      ws.value.onerror = (error) => {
        console.error('WebSocket错误:', error)
        ElMessage.error('WebSocket连接错误')
        isProcessing.value = false
      }
      
      ws.value.onclose = () => {
        console.log('WebSocket连接已关闭')
        ElMessage.warning('与服务器的连接已断开')
        isProcessing.value = false
      }
    }

    const initViewer = () => {
      // 初始化Three.js场景
      scene.value = new THREE.Scene()
      camera.value = new THREE.PerspectiveCamera(75, viewer.value.clientWidth / viewer.value.clientHeight, 0.1, 1000)
      renderer.value = new THREE.WebGLRenderer({ antialias: true })
      renderer.value.setSize(viewer.value.clientWidth, viewer.value.clientHeight)
      viewer.value.appendChild(renderer.value.domElement)

      // 添加轨道控制器
      controls.value = new OrbitControls(camera.value, renderer.value.domElement)
      camera.value.position.z = 5

      // 添加环境光
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
      scene.value.add(ambientLight)

      // 添加平行光
      const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5)
      directionalLight.position.set(0, 1, 0)
      scene.value.add(directionalLight)

      animate()
    }

    const animate = () => {
      requestAnimationFrame(animate)
      controls.value.update()
      renderer.value.render(scene.value, camera.value)
    }

    const loadPointCloud = (data) => {
      // 清除现有的点云
      scene.value.children.forEach(child => {
        if (child instanceof THREE.Points) {
          scene.value.remove(child)
        }
      })

      // 创建点云几何体
      const geometry = new THREE.BufferGeometry()
      const positions = new Float32Array(data.length * 3)
      const colors = new Float32Array(data.length * 3)

      // 填充位置和颜色数据
      for (let i = 0; i < data.length; i++) {
        const point = data[i]
        positions[i * 3] = point.x
        positions[i * 3 + 1] = point.y
        positions[i * 3 + 2] = point.z
        
        // 设置点的颜色
        colors[i * 3] = point.color ? point.color.r / 255 : 1.0
        colors[i * 3 + 1] = point.color ? point.color.g / 255 : 1.0
        colors[i * 3 + 2] = point.color ? point.color.b / 255 : 1.0
      }

      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

      // 创建点云材质
      const material = new THREE.PointsMaterial({
        size: 0.05,
        vertexColors: true
      })

      // 创建点云对象
      const points = new THREE.Points(geometry, material)
      scene.value.add(points)

      // 自动调整相机位置
      const box = new THREE.Box3().setFromObject(points)
      const center = box.getCenter(new THREE.Vector3())
      const size = box.getSize(new THREE.Vector3())
      const maxDim = Math.max(size.x, size.y, size.z)
      camera.value.position.copy(center).add(new THREE.Vector3(maxDim, maxDim, maxDim))
      camera.value.lookAt(center)
    }

    const handlePointCloudUpload = (file) => {
      if (isProcessing.value) {
        ElMessage.warning('正在处理点云数据，请稍候...')
        return
      }

      const reader = new FileReader()
      reader.onload = (e) => {
        if (file.raw.name.toLowerCase().endsWith('.las')) {
          try {
            // 发送点云数据到后端
            const buffer = e.target.result
            const dataView = new DataView(buffer)
            
            // 解析LAS文件头
            const header = {
              pointDataOffset: dataView.getUint32(96, true),
              pointDataFormat: dataView.getUint8(104, true),
              pointDataRecordLength: dataView.getUint16(105, true),
              numberOfPointRecords: dataView.getUint32(107, true)
            }
            
            const pointData = []
            let offset = header.pointDataOffset
            
            // 读取点数据
            for (let i = 0; i < header.numberOfPointRecords; i++) {
              const x = dataView.getInt32(offset, true) * 0.001
              const y = dataView.getInt32(offset + 4, true) * 0.001
              const z = dataView.getInt32(offset + 8, true) * 0.001
              
              pointData.push({
                x,
                y,
                z,
                color: {
                  r: 255,
                  g: 255,
                  b: 255
                }
              })
              
              offset += header.pointDataRecordLength
            }
            
            // 发送数据到后端
            if (ws.value && ws.value.readyState === WebSocket.OPEN) {
              isProcessing.value = true
              ws.value.send(JSON.stringify({
                type: 'processPointCloud',
                points: pointData,
                params: params.value
              }))
              ElMessage.info('正在处理点云数据...')
            } else {
              ElMessage.error('未连接到服务器')
            }
          } catch (error) {
            console.error('LAS文件解析错误:', error)
            ElMessage.error('LAS文件解析失败，请检查文件格式是否正确')
          }
        } else {
          // 处理其他格式（如CSV）
          const text = e.target.result
          const lines = text.split('\n')
          const points = []

          for (const line of lines) {
            if (line.trim()) {
              const [x, y, z] = line.split(',').map(Number)
              if (!isNaN(x) && !isNaN(y) && !isNaN(z)) {
                points.push({ x, y, z })
              }
            }
          }

          // 发送数据到后端
          if (ws.value && ws.value.readyState === WebSocket.OPEN) {
            isProcessing.value = true
            ws.value.send(JSON.stringify({
              type: 'processPointCloud',
              points: points,
              params: params.value
            }))
            ElMessage.info('正在处理点云数据...')
          } else {
            ElMessage.error('未连接到服务器')
          }
        }
      }
      
      if (file.raw.name.toLowerCase().endsWith('.las')) {
        reader.readAsArrayBuffer(file.raw)
      } else {
        reader.readAsText(file.raw)
      }
    }

    const processPointCloud = () => {
      if (isProcessing.value) {
        ElMessage.warning('正在处理点云数据，请稍候...')
        return
      }

      if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        isProcessing.value = true
        ws.value.send(JSON.stringify({
          type: 'processPointCloud',
          params: params.value
        }))
        ElMessage.info('正在处理点云数据...')
      } else {
        ElMessage.error('未连接到服务器')
      }
    }

    onMounted(() => {
      initViewer()
      initWebSocket()
    })

    onUnmounted(() => {
      // 清理Three.js资源
      if (renderer.value) {
        renderer.value.dispose()
      }
      if (controls.value) {
        controls.value.dispose()
      }
      // 关闭WebSocket连接
      if (ws.value) {
        ws.value.close()
      }
    })

    return {
      viewer,
      params,
      handlePointCloudUpload,
      processPointCloud
    }
  }
}
</script>

<style scoped lang="less">
.power-line-extraction {
  padding: 20px;
  height: 100vh;
  
  .el-header {
    text-align: center;
    line-height: 60px;
  }
  
  .viewer-container {
    height: calc(100vh - 100px);
    
    .viewer {
      width: 100%;
      height: 100%;
      border: 1px solid #dcdfe6;
    }
  }
  
  .control-panel {
    height: calc(100vh - 100px);
    overflow-y: auto;
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>

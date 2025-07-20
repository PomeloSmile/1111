<template>
  <div ref="container" class="viewer-container"></div>
  <button @click="loadMesh">加载三维重建Mesh</button>
</template>

<script>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js'

// 八叉树节点类
class OctreeNode {
  constructor(box, maxPoints = 10000) {
    this.box = box
    this.maxPoints = maxPoints
    this.points = []
    this.children = null
    this.center = box.getCenter(new THREE.Vector3())
    this.size = box.getSize(new THREE.Vector3())
  }

  addPoint(point) {
    if (this.children) {
      const octant = this.getOctant(point)
      this.children[octant].addPoint(point)
    } else {
      this.points.push(point)
      if (this.points.length > this.maxPoints) {
        this.subdivide()
      }
    }
  }

  getOctant(point) {
    let octant = 0
    if (point.x > this.center.x) octant |= 1
    if (point.y > this.center.y) octant |= 2
    if (point.z > this.center.z) octant |= 4
    return octant
  }

  subdivide() {
    this.children = []
    const halfSize = this.size.clone().multiplyScalar(0.5)
    
    for (let i = 0; i < 8; i++) {
      const childCenter = this.center.clone()
      childCenter.x += (i & 1) ? halfSize.x : -halfSize.x
      childCenter.y += (i & 2) ? halfSize.y : -halfSize.y
      childCenter.z += (i & 4) ? halfSize.z : -halfSize.z
      
      const childBox = new THREE.Box3(
        childCenter.clone().sub(halfSize),
        childCenter.clone().add(halfSize)
      )
      
      this.children.push(new OctreeNode(childBox, this.maxPoints))
    }

    // 将现有点重新分配到子节点
    for (const point of this.points) {
      const octant = this.getOctant(point)
      this.children[octant].addPoint(point)
    }
    
    this.points = []
  }

  getVisiblePoints(camera, maxDistance) {
    if (!this.children) {
      return this.points
    }

    const distance = camera.position.distanceTo(this.center)
    if (distance > maxDistance) {
      // 如果距离太远，返回中心点
      return [{
        x: this.center.x,
        y: this.center.y,
        z: this.center.z,
        color: { r: 128, g: 128, b: 128 }
      }]
    }

    let points = []
    for (const child of this.children) {
      points = points.concat(child.getVisiblePoints(camera, maxDistance))
    }
    return points
  }
}

export default {
  name: 'PointCloudViewer',
  props: {
    potreeData: {
      type: Object,
      default: () => null
    }
  },
  setup(props) {
    const container = ref(null)
    let scene, camera, renderer, controls, octree
    let animationFrameId = null
    let pointClouds = new Map() // 存储不同LOD级别的点云对象

    const initScene = () => {
      scene = new THREE.Scene()
      scene.background = new THREE.Color(0x000000)

      camera = new THREE.PerspectiveCamera(
        75,
        container.value.clientWidth / container.value.clientHeight,
        0.1,
        1000
      )
      camera.position.z = 5

      renderer = new THREE.WebGLRenderer({ 
        antialias: true,
        powerPreference: 'high-performance'
      })
      renderer.setSize(container.value.clientWidth, container.value.clientHeight)
      container.value.appendChild(renderer.domElement)

      controls = new OrbitControls(camera, renderer.domElement)
      controls.enableDamping = true
      controls.dampingFactor = 0.05

      const ambientLight = new THREE.AmbientLight(0xffffff, 0.5)
      scene.add(ambientLight)

      const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5)
      directionalLight.position.set(1, 1, 1)
      scene.add(directionalLight)

      animate()
    }

    const createPointCloud = (points, size = 0.05) => {
      const geometry = new THREE.BufferGeometry()
      const positions = new Float32Array(points.length * 3)
      const colors = new Float32Array(points.length * 3)

      points.forEach((point, i) => {
        positions[i * 3] = point.x
        positions[i * 3 + 1] = point.y
        positions[i * 3 + 2] = point.z

        colors[i * 3] = point.color.r / 255
        colors[i * 3 + 1] = point.color.g / 255
        colors[i * 3 + 2] = point.color.b / 255
      })

      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))

      const material = new THREE.PointsMaterial({
        size,
        vertexColors: true,
        sizeAttenuation: true,
        transparent: true,
        opacity: 0.8
      })

      return new THREE.Points(geometry, material)
    }

    const loadPointCloud = async () => {
      if (!props.potreeData) return

      try {
        // 清除现有的点云对象
        pointClouds.forEach(cloud => {
          scene.remove(cloud)
          cloud.geometry.dispose()
          cloud.material.dispose()
        })
        pointClouds.clear()

        // 从API获取点云数据
        const response = await fetch(props.potreeData.metadata_path)
        const data = await response.json()

        // 创建八叉树
        const box = new THREE.Box3()
        data.points.forEach(point => {
          box.expandByPoint(new THREE.Vector3(point.x, point.y, point.z))
        })
        octree = new OctreeNode(box)

        // 添加点到八叉树
        data.points.forEach(point => {
          octree.addPoint(point)
        })

        // 创建不同LOD级别的点云
        const lodDistances = [10, 20, 50, 100]
        lodDistances.forEach((distance, index) => {
          const points = octree.getVisiblePoints(camera, distance)
          const pointCloud = createPointCloud(points, 0.05 * (index + 1))
          pointClouds.set(distance, pointCloud)
          scene.add(pointCloud)
        })

        // 自动调整相机位置
        const center = box.getCenter(new THREE.Vector3())
        const size = box.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)
        const fov = camera.fov * (Math.PI / 180)
        let cameraZ = Math.abs(maxDim / Math.sin(fov / 2))
        camera.position.set(center.x, center.y, center.z + cameraZ)
        camera.lookAt(center)
        controls.target.copy(center)

      } catch (error) {
        console.error('加载点云失败:', error)
      }
    }

    const loadMesh = (meshPath = '/xxx_mesh.ply') => {
      const loader = new PLYLoader()
      loader.load(meshPath, geometry => {
        geometry.computeVertexNormals()
        const material = new THREE.MeshStandardMaterial({
          color: 0x6699ff,
          flatShading: false,
          vertexColors: geometry.hasAttribute('color')
        })
        const mesh = new THREE.Mesh(geometry, material)
        scene.add(mesh)

        // 居中
        geometry.computeBoundingBox()
        const center = geometry.boundingBox.getCenter(new THREE.Vector3())
        mesh.position.sub(center)
      })
    }

    const updateLOD = () => {
      if (!octree) return

      const distance = camera.position.distanceTo(controls.target)
      pointClouds.forEach((cloud, maxDistance) => {
        cloud.visible = distance <= maxDistance
      })
    }

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate)
      controls.update()
      updateLOD()
      renderer.render(scene, camera)
    }

    const handleResize = () => {
      if (!container.value) return

      camera.aspect = container.value.clientWidth / container.value.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(container.value.clientWidth, container.value.clientHeight)
    }

    watch(() => props.potreeData, () => {
      loadPointCloud()
    }, { deep: true })

    onMounted(() => {
      initScene()
      window.addEventListener('resize', handleResize)
      if (props.potreeData) {
        loadPointCloud()
      }
      // 这里可以根据需要选择加载点云或mesh
      // loadPointCloud() // 如果还需要点云
      loadMesh('/xxx_mesh.ply') // 加载mesh
    })

    onUnmounted(() => {
      if (animationFrameId) {
        cancelAnimationFrame(animationFrameId)
      }
      window.removeEventListener('resize', handleResize)
      if (container.value && renderer) {
        container.value.removeChild(renderer.domElement)
      }
      pointClouds.forEach(cloud => {
        cloud.geometry.dispose()
        cloud.material.dispose()
      })
    })

    return {
      container,
      loadMesh,
      resetView: () => {
        if (octree) {
          const center = octree.center
          const size = octree.size
          const maxDim = Math.max(size.x, size.y, size.z)
          const fov = camera.fov * (Math.PI / 180)
          let cameraZ = Math.abs(maxDim / Math.sin(fov / 2))
          camera.position.set(center.x, center.y, center.z + cameraZ)
          camera.lookAt(center)
          controls.target.copy(center)
        }
      }
    }
  }
}
</script>

<style scoped>
.viewer-container {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
}
</style> 
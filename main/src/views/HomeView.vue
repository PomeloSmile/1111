<template>
  <div class="home">
    <h1>点云处理系统</h1>
    <PointCloudProcessor />
  </div>
</template>

<script>
// @ is an alias to /src
import PointCloudProcessor from '@/components/PointCloudProcessor.vue'

export default {
  name: 'HomeView',
  components: {
    PointCloudProcessor
  }
}
</script>

<style scoped>
.home {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

h1 {
  text-align: center;
  margin-bottom: 30px;
}
</style>

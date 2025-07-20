import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue')
  },
  {
    path: '/viewer',
    name: 'viewer',
    component: () => import('../views/Viewer.vue')
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router

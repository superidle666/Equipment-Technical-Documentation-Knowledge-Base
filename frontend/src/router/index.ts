import { createRouter, createWebHistory } from 'vue-router'
import { hasAccessToken } from '../api/auth'
import UserView from '../UserView.vue'
import AdminView from '../pages/admin/index.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'user', component: UserView },
    { path: '/admin/login', name: 'admin-login', component: AdminView },
    { path: '/admin', name: 'admin', component: AdminView, meta: { requiresAuth: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  if (to.meta.requiresAuth && !hasAccessToken()) return { name: 'admin-login' }
  if (to.name === 'admin-login' && hasAccessToken()) return { name: 'admin' }
  return true
})

export default router
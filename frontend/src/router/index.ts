import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import ContentListPage from '../pages/ContentListPage.vue'
import NotFoundPage from '../pages/NotFoundPage.vue'

// 仅注册当前已实现的首页与兜底 404，不提前注册未实现业务路由
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomePage,
    },
    {
      path: '/contents',
      name: 'contents',
      component: ContentListPage,
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundPage,
    },
  ],
})

export default router

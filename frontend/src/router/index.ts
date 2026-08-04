import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import ContentListPage from '../pages/ContentListPage.vue'
import ContentDetailPage from '../pages/ContentDetailPage.vue'
import NotFoundPage from '../pages/NotFoundPage.vue'

import SubmissionPage from '../pages/SubmissionPage.vue'
import AboutPage from '../pages/AboutPage.vue'
import AdminLoginPrototypePage from '../pages/admin/AdminLoginPrototypePage.vue'
import AdminContentEditorPrototypePage from '../pages/admin/AdminContentEditorPrototypePage.vue'

// 注册当前已实现的首页、内容浏览、内容详情与兜底 404
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
      path: '/contents/:id',
      name: 'content-detail',
      component: ContentDetailPage,
    },
    {
      path: '/submission',
      name: 'submission',
      component: SubmissionPage,
    },
    {
      path: '/about',
      name: 'about',
      component: AboutPage,
    },
    {
      path: '/admin/login',
      name: 'admin-login',
      component: AdminLoginPrototypePage,
    },
    {
      path: '/admin/contents/new',
      name: 'admin-content-new',
      component: AdminContentEditorPrototypePage,
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundPage,
    },
  ],
})

export default router

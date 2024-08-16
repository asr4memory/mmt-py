import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AdminView from '@/views/AdminView.vue'
import HomeView from '@/views/HomeView.vue'
import AccessibilityView from '@/views/AccessibilityView.vue'
import ContactView from '@/views/ContactView.vue'
import DownloadsView from '@/views/DownloadsView.vue'
import LegalNoticeView from '@/views/LegalNoticeView.vue'
import LoginView from '@/views/LoginView.vue'
import PrivacyView from '@/views/PrivacyView.vue'
import RegistrationView from '@/views/RegistrationView.vue'
import UploadsView from '@/views/UploadsView.vue'
import NotFoundView from '@/views/NotFoundView.vue'
import ProfileView from '@/views/ProfileView.vue'

const PUBLIC_PAGES = [
  '/',
  '/log-in',
  '/register',
  '/accessibility',
  '/privacy',
  '/legal-notice',
  '/contact'
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  linkActiveClass: 'router-link-active',
  linkExactActiveClass: 'router-link-exact-active',
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/uploads',
      name: 'uploads',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/UploadsView.vue')
    },
    {
      path: '/downloads',
      name: 'downloads',
      component: DownloadsView
    },{
      path: '/admin',
      name: 'admin',
      component: AdminView
    },
    {
      path: '/register',
      name: 'register',
      component: RegistrationView
    },
    {
      path: '/log-in',
      name: 'log-in',
      component: LoginView
    },
    {
      path: '/accessibility',
      name: 'accessibility',
      component: AccessibilityView
    },
    {
      path: '/contact',
      name: 'contact',
      component: ContactView
    },
    {
      path: '/legal-notice',
      name: 'legal-notice',
      component: LegalNoticeView
    },
    {
      path: '/privacy',
      name: 'privacy',
      component: PrivacyView
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: NotFoundView
    }
  ]
})

router.beforeEach(async (to) => {
  // redirect to login page if not logged in and trying to access a restricted page
  const authRequired = !PUBLIC_PAGES.includes(to.path)
  const auth = useAuthStore()

  if (authRequired && !auth.user) {
    auth.returnUrl = to.fullPath
    return '/log-in'
  }
})

export default router

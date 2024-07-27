import { createApp } from 'vue'
import { createI18n } from 'vue-i18n'
import { createPinia } from 'pinia'
import Vue3EasyDataTable from 'vue3-easy-data-table'

import App from './App.vue'
import router from './router'
import { useAuthStore } from '@/stores/auth'
import de from './locales/de'
import en from './locales/en'
import './assets/main.css'

const i18n = createI18n({
  legacy: false,
  locale: 'de',
  fallbackLocale: 'en',
  messages: {
    de,
    en
  }
})

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)
app.component('EasyDataTable', Vue3EasyDataTable)

const authStore = useAuthStore()
authStore.getUser()

app.mount('#app')

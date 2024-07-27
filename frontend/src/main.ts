import { createApp } from 'vue'
import { createPinia } from 'pinia'
import Vue3EasyDataTable from 'vue3-easy-data-table'

import App from './App.vue'
import router from './router'
import i18n from './i18n'
import { useAuthStore } from '@/stores/auth'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
const authStore = useAuthStore()
authStore.getUser()

app.use(i18n)

app.component('EasyDataTable', Vue3EasyDataTable)
app.mount('#app')

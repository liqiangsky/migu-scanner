import { createApp } from 'vue'

// 基础样式流水线
import './styles/main.css'

import App from './App.vue'
import router from './router.js'

const app = createApp(App)

app.use(router)

app.mount('#app')

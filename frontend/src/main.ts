import { createApp } from 'vue'
import { createI18n } from 'vue-i18n'
import en from './i18n/en.json'
import sv from './i18n/sv.json'
import 'bootstrap/dist/css/bootstrap.min.css'
import './style.css'
import App from './App.vue'

const i18n = createI18n({
  legacy: false,
  locale: localStorage.getItem('locale') || navigator.language.split('-')[0] || 'en',
  fallbackLocale: 'en',
  messages: { en, sv },
})

const app = createApp(App)
app.use(i18n)
app.mount('#app')

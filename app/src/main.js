import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'

// iamcc-ui styles, in this order (copied from .claude/skills/iamcc-ui/assets/; never edited here).
import './styles/fonts.css'
import './styles/tokens.css'
import './styles/components.css'
import './styles/layout.css'

createApp(App).use(router).mount('#app')

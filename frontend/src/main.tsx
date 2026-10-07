import { createRoot } from 'react-dom/client'
import App from './App'
import './styles/tokens.css'
import './styles/base.css'
import './styles/layout.css'
import './styles/components.css'

if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  void navigator.serviceWorker.register('/sw.js', { scope: '/' })
    .catch(error => console.warn('Service worker registration failed.', error))
}

createRoot(document.getElementById('root')!).render(<App />)

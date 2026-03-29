import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'

console.log('Main.jsx: Initializing React root...')
const rootElement = document.getElementById('root')
console.log('Main.jsx: Root element found:', rootElement)

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

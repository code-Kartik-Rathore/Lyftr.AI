import { useState, useEffect, useRef } from 'react'
import ChatContainer from './components/ChatContainer'
import { generateSessionId } from './utils/api'
import './App.css'

function App() {
  const [sessionId] = useState(() => generateSessionId())

  return (
    <div className="app">
      <header className="app-header">
        <span className="logo-icon">✦</span>
        <h1>Lyftr AI</h1>
      </header>
      <ChatContainer sessionId={sessionId} />
    </div>
  )
}

export default App

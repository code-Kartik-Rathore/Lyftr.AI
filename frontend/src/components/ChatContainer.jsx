import { useState, useRef, useCallback } from 'react'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import SystemPrompt from './SystemPrompt'
import { sendMessage } from '../utils/api'
import './ChatContainer.css'

function ChatContainer({ sessionId }) {
  const [messages, setMessages] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [systemPrompt, setSystemPrompt] = useState('')
  const messagesEndRef = useRef(null)

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, 50)
  }, [])

  const handleSend = useCallback(async (text) => {
    if (!text.trim() || isLoading) return

    const userMessage = { role: 'user', content: text }
    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)
    scrollToBottom()

    try {
      const data = await sendMessage(sessionId, text, systemPrompt)
      const assistantMessage = {
        role: 'assistant',
        content: data.reply,
        metadata: data.metadata,
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      const errorMessage = {
        role: 'assistant',
        content: null,
        error: err.message || 'Something went wrong. Please try again.',
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
      scrollToBottom()
    }
  }, [sessionId, systemPrompt, isLoading, scrollToBottom])

  return (
    <div className="chat-container">
      <SystemPrompt value={systemPrompt} onChange={setSystemPrompt} />
      <MessageList
        messages={messages}
        isLoading={isLoading}
        messagesEndRef={messagesEndRef}
      />
      <MessageInput onSend={handleSend} isLoading={isLoading} />
    </div>
  )
}

export default ChatContainer

import UserMessage from './UserMessage'
import AssistantMessage from './AssistantMessage'
import './MessageList.css'

function MessageList({ messages, isLoading, messagesEndRef }) {
  return (
    <div className="message-list">
      {messages.length === 0 && !isLoading && (
        <div className="empty-state">
          <div className="empty-icon">✦</div>
          <h2>How can I help you today?</h2>
          <p>Send a message to start a conversation</p>
        </div>
      )}
      {messages.map((msg, index) => (
        msg.role === 'user' ? (
          <UserMessage key={index} content={msg.content} />
        ) : (
          <AssistantMessage
            key={index}
            content={msg.content}
            metadata={msg.metadata}
            error={msg.error}
          />
        )
      ))}
      {isLoading && (
        <div className="typing-indicator-wrapper">
          <div className="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  )
}

export default MessageList

import ReactMarkdown from 'react-markdown'
import MetadataDisplay from './MetadataDisplay'
import './AssistantMessage.css'

function AssistantMessage({ content, metadata, error }) {
  return (
    <div className="assistant-message-row">
      <div className="assistant-message" data-testid="assistant-message">
        {error ? (
          <div className="assistant-error">
            <span className="error-icon">⚠</span>
            <span>{error}</span>
          </div>
        ) : (
          <div className="assistant-content">
            <ReactMarkdown>{content}</ReactMarkdown>
          </div>
        )}
        {metadata && <MetadataDisplay metadata={metadata} />}
      </div>
    </div>
  )
}

export default AssistantMessage

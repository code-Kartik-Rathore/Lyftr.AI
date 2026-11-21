import { useState } from 'react'
import './SystemPrompt.css'

function SystemPrompt({ value, onChange }) {
  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="system-prompt">
      <button
        className="system-prompt-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
        type="button"
      >
        <svg
          className={`chevron ${isExpanded ? 'expanded' : ''}`}
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
        >
          <path
            d="M6 4l4 4-4 4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span>System Prompt</span>
        {value && !isExpanded && <span className="dot-indicator" />}
      </button>
      {isExpanded && (
        <div className="system-prompt-body">
          <textarea
            data-testid="system-prompt-input"
            className="system-prompt-textarea"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Set a system prompt to guide the AI's behavior..."
            rows={3}
          />
        </div>
      )}
    </div>
  )
}

export default SystemPrompt

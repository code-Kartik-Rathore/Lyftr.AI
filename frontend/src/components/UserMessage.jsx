import './UserMessage.css'

function UserMessage({ content }) {
  return (
    <div className="user-message-row">
      <div className="user-message">
        <p>{content}</p>
      </div>
    </div>
  )
}

export default UserMessage

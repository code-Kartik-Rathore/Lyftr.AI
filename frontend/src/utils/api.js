const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function sendMessage(sessionId, message, systemPrompt) {
  const body = {
    session_id: sessionId,
    message: message,
  }

  if (systemPrompt && systemPrompt.trim()) {
    body.system_prompt = systemPrompt.trim()
  }

  const response = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error occurred' }))
    throw new Error(errorData.detail || `Request failed with status ${response.status}`)
  }

  return response.json()
}

export function generateSessionId() {
  const hex = Array.from(crypto.getRandomValues(new Uint8Array(8)))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
  return `s-${hex}`
}

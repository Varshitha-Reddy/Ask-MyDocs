import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Read tenant ID from env var — set VITE_TENANT_ID in .env.local for multi-tenant deployments.
// Defaults to "default" so single-tenant usage requires zero configuration.
const TENANT_ID = import.meta.env.VITE_TENANT_ID || 'default'

// Axios instance — attaches X-Tenant-ID to every request automatically
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000,
  headers: { 'X-Tenant-ID': TENANT_ID },
})

// Upload a document for background ingestion.
// Returns immediately with { job_id, filename, status: "pending" }
export function ingest(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/ingest', formData)
}

// Poll for the status of a background ingestion job
export function getIngestStatus(jobId) {
  return api.get(`/ingest/status/${jobId}`)
}

// Regular (non-streaming) search — waits for full answer before returning
export function search(query, topK = 5) {
  return api.post('/search', { query, top_k: topK })
}

/**
 * Streaming search — calls POST /search/stream and reads SSE events.
 *
 * We use fetch + ReadableStream instead of EventSource because EventSource
 * only supports GET requests, and our endpoint is POST.
 *
 * Callbacks:
 *   onSources(sources)  — called once with the retrieved chunks (before LLM starts)
 *   onToken(token)      — called for each streamed LLM token
 *   onDone()            — called when the stream ends
 *   onError(message)    — called on network or parse errors
 */
export async function searchStream(query, topK = 5, { onSources, onToken, onDone, onError }) {
  let response
  try {
    response = await fetch(`${BASE_URL}/search/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-ID': TENANT_ID,
      },
      body: JSON.stringify({ query, top_k: topK }),
    })
  } catch (err) {
    onError?.('Stream request failed. Is the backend running?')
    return
  }

  if (!response.ok) {
    onError?.(`Server error: ${response.status}`)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  // Read chunks of bytes from the stream until it closes
  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    // Decode the bytes and append to our line buffer
    buffer += decoder.decode(value, { stream: true })

    // SSE events are separated by \n\n — split on that
    const parts = buffer.split('\n\n')
    // The last part may be incomplete — keep it in buffer for next iteration
    buffer = parts.pop()

    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data: ')) continue

      const data = line.slice(6).trim()
      if (data === '[DONE]') {
        onDone?.()
        return
      }

      try {
        const parsed = JSON.parse(data)
        if (parsed.type === 'sources') onSources?.(parsed.sources)
        if (parsed.type === 'token') onToken?.(parsed.token)
      } catch {
        // Ignore malformed SSE lines
      }
    }
  }

  onDone?.()
}

export default api

import { useState } from 'react'
import { search, searchStream } from '../lib/api'

function SearchBar({
  onResult,
  onError,
  onStreamStart,
  onStreamSources,
  onStreamToken,
  onStreamDone,
  isSearching,
  setIsSearching,
}) {
  const [query, setQuery] = useState('')
  // Toggle between regular (full response at once) and streaming (tokens appear live)
  const [streamMode, setStreamMode] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return

    setIsSearching(true)

    if (streamMode) {
      // --- Streaming mode ---
      // Sources appear instantly, answer tokens stream in as the LLM generates them
      onStreamStart()
      await searchStream(trimmed, 5, {
        onSources: onStreamSources,
        onToken: onStreamToken,
        onDone: () => {
          onStreamDone()
          setIsSearching(false)
        },
        onError: (msg) => {
          onError(msg)
          setIsSearching(false)
        },
      })
    } else {
      // --- Regular mode ---
      // Waits for the full answer before displaying anything
      try {
        const response = await search(trimmed)
        onResult(response.data)
      } catch (err) {
        onError(err.response?.data?.detail || 'Search failed. Is the backend running?')
      } finally {
        setIsSearching(false)
      }
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">2. Ask a Question</h2>

        {/* Stream mode toggle */}
        <label className="flex items-center gap-2 cursor-pointer select-none">
          <span className="text-xs text-gray-500">Stream</span>
          <div
            onClick={() => !isSearching && setStreamMode(prev => !prev)}
            className={`relative w-9 h-5 rounded-full transition-colors ${
              streamMode ? 'bg-blue-600' : 'bg-gray-300'
            } ${isSearching ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
          >
            <div
              className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${
                streamMode ? 'translate-x-4' : 'translate-x-0.5'
              }`}
            />
          </div>
          {streamMode && (
            <span className="text-xs text-blue-600 font-medium">Live</span>
          )}
        </label>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. What is the main topic of this document?"
          disabled={isSearching}
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     disabled:bg-gray-50 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={isSearching || !query.trim()}
          className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg text-sm
                     font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSearching
            ? streamMode
              ? 'Streaming...'
              : 'Searching...'
            : 'Search'}
        </button>
      </form>

      {/* Small hint so users understand the toggle */}
      {streamMode && (
        <p className="mt-2 text-xs text-blue-500">
          Sources will appear first, then the answer streams token by token.
        </p>
      )}
    </div>
  )
}

export default SearchBar

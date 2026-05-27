import { useState } from 'react'
import UploadPanel from './components/UploadPanel'
import SearchBar from './components/SearchBar'
import AnswerCard from './components/AnswerCard'
import SourceList from './components/SourceList'

function App() {
  // For regular (non-streaming) search: full response object
  const [searchResult, setSearchResult] = useState(null)

  // For streaming search: sources arrive first, then tokens accumulate
  const [streamingSources, setStreamingSources] = useState(null)
  const [streamingAnswer, setStreamingAnswer] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)

  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState(null)

  function handleSearchResult(result) {
    // Clear any previous streaming state and show the full result
    setStreamingSources(null)
    setStreamingAnswer('')
    setSearchResult(result)
    setError(null)
  }

  function handleError(message) {
    setError(message)
    setSearchResult(null)
    setStreamingSources(null)
    setStreamingAnswer('')
  }

  // Called by SearchBar when streaming starts
  function handleStreamStart() {
    setSearchResult(null)
    setStreamingSources(null)
    setStreamingAnswer('')
    setError(null)
    setIsStreaming(true)
  }

  // Called when the first SSE 'sources' event arrives
  function handleStreamSources(sources) {
    setStreamingSources(sources)
  }

  // Called for each token — append to the growing answer string
  function handleStreamToken(token) {
    setStreamingAnswer(prev => prev + token)
  }

  // Called when the stream closes
  function handleStreamDone() {
    setIsStreaming(false)
  }

  // Decide what to render in the results area
  const showStreamingResult = streamingSources !== null || streamingAnswer !== ''
  const showRegularResult = searchResult !== null

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-bold text-gray-900">RAG Hybrid Search</h1>
          <p className="text-sm text-gray-500 mt-1">
            Semantic + BM25 · RRF fusion · LLM-cited answers · streaming
          </p>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Step 1: Upload */}
        <UploadPanel />

        {/* Step 2: Search (with streaming toggle) */}
        <SearchBar
          onResult={handleSearchResult}
          onError={handleError}
          onStreamStart={handleStreamStart}
          onStreamSources={handleStreamSources}
          onStreamToken={handleStreamToken}
          onStreamDone={handleStreamDone}
          isSearching={isSearching}
          setIsSearching={setIsSearching}
        />

        {/* Error banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Streaming result: sources appear first, then answer fills in token by token */}
        {showStreamingResult && (
          <div className="space-y-4">
            <AnswerCard
              answer={streamingAnswer}
              latencyMs={null}
              cached={false}
              isStreaming={isStreaming}
            />
            {streamingSources && <SourceList sources={streamingSources} />}
          </div>
        )}

        {/* Regular (non-streaming) result */}
        {showRegularResult && !showStreamingResult && (
          <div className="space-y-4">
            <AnswerCard
              answer={searchResult.answer}
              latencyMs={searchResult.latency_ms}
              cached={searchResult.cached}
              isStreaming={false}
            />
            <SourceList sources={searchResult.sources} />
          </div>
        )}
      </main>
    </div>
  )
}

export default App

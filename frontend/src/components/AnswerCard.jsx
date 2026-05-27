import ReactMarkdown from 'react-markdown'

function AnswerCard({ answer, latencyMs, cached, isStreaming }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Header row: title + badges */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-gray-800">Answer</h2>
        <div className="flex items-center gap-2 text-xs">
          {/* Shown while tokens are still arriving */}
          {isStreaming && (
            <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium animate-pulse">
              ● Streaming
            </span>
          )}
          {/* Green badge when served from Redis cache */}
          {!isStreaming && cached && (
            <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
              ⚡ Cached
            </span>
          )}
          {/* Latency shown only for non-streaming results (streaming has no single end-time) */}
          {!isStreaming && latencyMs !== null && (
            <span className="text-gray-400">{latencyMs}ms</span>
          )}
        </div>
      </div>

      {/* Render answer as Markdown so citation brackets look right */}
      <div className="prose prose-sm max-w-none text-gray-700">
        {answer ? (
          <>
            <ReactMarkdown>{answer}</ReactMarkdown>
            {/* Blinking cursor while the model is still generating */}
            {isStreaming && (
              <span className="inline-block w-0.5 h-4 bg-gray-600 animate-pulse ml-0.5 align-middle" />
            )}
          </>
        ) : (
          /* Placeholder while waiting for the first token */
          isStreaming && (
            <span className="text-gray-400 text-sm animate-pulse">Generating answer...</span>
          )
        )}
      </div>
    </div>
  )
}

export default AnswerCard

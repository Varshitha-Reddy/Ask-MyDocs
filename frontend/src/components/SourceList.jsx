import { useState } from 'react'

// A single collapsible source chunk row
function SourceItem({ source, index }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Always-visible header: click to expand/collapse the chunk text */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3
                   bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          {/* Rank badge */}
          <span className="flex-shrink-0 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-mono">
            #{index + 1}
          </span>
          {/* Filename */}
          <span className="text-sm font-medium text-gray-700 truncate">
            {source.source_filename}
          </span>
          {/* Page number */}
          <span className="flex-shrink-0 text-xs text-gray-400">
            — p.{source.page_number}
          </span>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0 ml-2">
          <span className="text-xs text-gray-400 font-mono">
            score: {source.score.toFixed(4)}
          </span>
          <span className="text-gray-400 text-xs">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {/* Expanded: show the actual chunk text */}
      {expanded && (
        <div className="px-4 py-3 text-sm text-gray-600 bg-white border-t border-gray-100 leading-relaxed">
          {source.content}
        </div>
      )}
    </div>
  )
}

function SourceList({ sources }) {
  if (!sources || sources.length === 0) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-base font-semibold text-gray-800 mb-3">
        Sources{' '}
        <span className="text-gray-400 font-normal text-sm">({sources.length} chunks)</span>
      </h2>

      <div className="space-y-2">
        {sources.map((source, i) => (
          <SourceItem key={source.chunk_id} source={source} index={i} />
        ))}
      </div>
    </div>
  )
}

export default SourceList

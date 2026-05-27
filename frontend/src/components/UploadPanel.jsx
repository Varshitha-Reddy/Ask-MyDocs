import { useState, useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import { ingest, getIngestStatus } from '../lib/api'

function UploadPanel() {
  // 'idle' | 'uploading' | 'processing' | 'done' | 'error'
  const [status, setStatus] = useState('idle')
  const [message, setMessage] = useState('')
  const [chunks, setChunks] = useState(null)

  // Keep a ref to the polling interval so we can clear it
  const pollRef = useRef(null)

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  async function pollJobStatus(jobId) {
    // Poll every 2 seconds until the job finishes or errors
    pollRef.current = setInterval(async () => {
      try {
        const res = await getIngestStatus(jobId)
        const job = res.data

        if (job.status === 'done') {
          stopPolling()
          setStatus('done')
          setChunks(job.chunks_ingested)
          setMessage(`"${job.filename}" indexed — ${job.chunks_ingested} chunks stored`)
        } else if (job.status === 'error') {
          stopPolling()
          setStatus('error')
          setMessage(`Ingestion failed: ${job.error}`)
        } else {
          // Still processing — update the message to show it's working
          setMessage(`Processing "${job.filename}"... (${job.status})`)
        }
      } catch {
        // If status check fails, stop polling so we don't spin forever
        stopPolling()
        setStatus('error')
        setMessage('Could not check job status. Is the backend running?')
      }
    }, 2000)
  }

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return

    stopPolling() // Cancel any previous poll
    const file = acceptedFiles[0]
    setStatus('uploading')
    setChunks(null)
    setMessage(`Uploading "${file.name}"...`)

    try {
      // POST /ingest returns immediately with job_id (HTTP 202)
      const response = await ingest(file)
      const { job_id, filename } = response.data

      setStatus('processing')
      setMessage(`"${filename}" accepted — processing in background...`)

      // Start polling for job completion
      await pollJobStatus(job_id)
    } catch (err) {
      setStatus('error')
      setMessage(err.response?.data?.detail || 'Upload failed. Is the backend running?')
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
    },
    maxFiles: 1,
  })

  const dropAreaClass = isDragActive
    ? 'border-blue-400 bg-blue-50'
    : 'border-gray-300 bg-gray-50 hover:bg-gray-100'

  const statusColors = {
    uploading:  'bg-blue-50  text-blue-700  border-blue-200',
    processing: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    done:       'bg-green-50 text-green-700 border-green-200',
    error:      'bg-red-50   text-red-700   border-red-200',
  }

  const statusIcons = {
    uploading:  '⏳',
    processing: '⚙️',
    done:       '✅',
    error:      '❌',
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-base font-semibold text-gray-800 mb-4">1. Upload a Document</h2>

      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${dropAreaClass}`}
      >
        <input {...getInputProps()} />
        <p className="text-3xl mb-2">📄</p>
        {isDragActive ? (
          <p className="text-blue-600 font-medium">Drop it here!</p>
        ) : (
          <p className="text-gray-500 text-sm">
            Drag & drop a <strong>PDF</strong>, <strong>TXT</strong>, or <strong>MD</strong> file,
            or click to browse
          </p>
        )}
      </div>

      {status !== 'idle' && (
        <div
          className={`mt-3 px-4 py-2 rounded text-sm border flex items-center gap-2 ${statusColors[status] || ''}`}
        >
          <span className={status === 'processing' ? 'animate-spin' : ''}>
            {statusIcons[status]}
          </span>
          <span>{message}</span>
          {/* Show a progress note during processing so the user knows what's happening */}
          {status === 'processing' && (
            <span className="ml-auto text-xs opacity-60">polling every 2s...</span>
          )}
        </div>
      )}
    </div>
  )
}

export default UploadPanel

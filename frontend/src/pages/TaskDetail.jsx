import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getTask, downloadTask } from '../api/tasks'
import { parseMultipartResponse } from '../utils/multipart'
import StatusBadge from '../components/StatusBadge'
import styles from './TaskDetail.module.css'

export default function TaskDetail() {
  const { id } = useParams()
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    let intervalId = null

    const fetchTask = async () => {
      try {
        const data = await getTask(id)
        setTask(data)
        setLoading(false)

        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          if (intervalId) clearInterval(intervalId)
        }
      } catch (err) {
        setError(err.response?.data?.message || 'Failed to load task')
        setLoading(false)
        if (intervalId) clearInterval(intervalId)
      }
    }

    fetchTask()
    intervalId = setInterval(fetchTask, 3000)

    return () => {
      if (intervalId) clearInterval(intervalId)
    }
  }, [id])

  const handleDownload = async () => {
    setDownloading(true)
    try {
      const { data, contentType } = await downloadTask(id)
      const { fileBlob, filename } = parseMultipartResponse(data, contentType)

      if (!fileBlob) {
        setError('Failed to parse download response')
        return
      }

      const url = URL.createObjectURL(fileBlob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.response?.data?.message || 'Download failed')
    } finally {
      setDownloading(false)
    }
  }

  const formatDate = (iso) => {
    return new Date(iso).toLocaleString()
  }

  if (loading) {
    return <div className={styles.loading}>Loading task...</div>
  }

  if (error && !task) {
    return <div className={styles.errorPage}>{error}</div>
  }

  return (
    <div>
      <Link to="/dashboard" className={styles.backLink}>
        &larr; Back to Dashboard
      </Link>

      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>Task Details</h1>
          <StatusBadge status={task.status} />
        </div>

        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.details}>
          <div className={styles.row}>
            <span className={styles.label}>Task ID</span>
            <span className={styles.value}>{task.id}</span>
          </div>
          {task.prompt && (
            <div className={styles.row}>
              <span className={styles.label}>Prompt</span>
              <span className={styles.value}>{task.prompt}</span>
            </div>
          )}
          <div className={styles.row}>
            <span className={styles.label}>Created</span>
            <span className={styles.value}>{formatDate(task.createdAt)}</span>
          </div>
          <div className={styles.row}>
            <span className={styles.label}>Updated</span>
            <span className={styles.value}>{formatDate(task.updatedAt)}</span>
          </div>
        </div>

        {task.status === 'COMPLETED' && (
          <button
            className={styles.downloadBtn}
            onClick={handleDownload}
            disabled={downloading}
          >
            {downloading ? 'Downloading...' : 'Download 3D Model'}
          </button>
        )}

        {task.status === 'FAILED' && (
          <div className={styles.failedMsg}>
            Generation failed. Please try creating a new task.
          </div>
        )}

        {(task.status === 'PENDING' || task.status === 'PROCESSING') && (
          <div className={styles.pollingMsg}>
            {task.status === 'PENDING'
              ? 'Task is waiting in queue...'
              : 'Generating your 3D model...'}
          </div>
        )}
      </div>
    </div>
  )
}

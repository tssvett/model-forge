import { Link } from 'react-router-dom'
import { useParams } from 'react-router-dom'
import { useTaskPolling } from '../hooks/useTaskPolling'
import { useModelDownload } from '../hooks/useModelDownload'
import { TASK_STATUS } from '../utils/constants'
import { formatDateTime } from '../utils/format'
import StatusBadge from '../components/StatusBadge'
import GlassCard from '../components/GlassCard'
import Button from '../components/Button'
import ErrorMessage from '../components/ErrorMessage'
import LoadingSpinner from '../components/LoadingSpinner'
import ModelViewer from '../components/ModelViewer'
import styles from './TaskDetail.module.css'

export default function TaskDetail() {
  const { id } = useParams()
  const { task, loading, error: taskError, setError } = useTaskPolling(id)
  const {
    modelBlobUrl, filename, downloading, error: downloadError,
    triggerFileDownload, isViewerCompatible,
  } = useModelDownload(id, task?.status === TASK_STATUS.COMPLETED)

  const error = taskError || downloadError

  if (loading) {
    return <LoadingSpinner text="Loading task..." />
  }

  if (error && !task) {
    return (
      <div className="pageEnter" style={{ padding: '48px' }}>
        <ErrorMessage message={error} />
      </div>
    )
  }

  return (
    <div className="pageEnter">
      <Link to="/dashboard" className={styles.backLink}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
        Back to Dashboard
      </Link>

      <GlassCard>
        <div className={styles.header}>
          <h1 className={styles.title}>Task Details</h1>
          <StatusBadge status={task.status} />
        </div>

        {error && <ErrorMessage message={error} />}

        {/* 3D Model Viewer */}
        {task.status === TASK_STATUS.COMPLETED && (
          <div className={styles.viewerSection}>
            {isViewerCompatible && modelBlobUrl ? (
              <ModelViewer src={modelBlobUrl} alt="Generated 3D Model" />
            ) : downloading ? (
              <div className={styles.viewerPlaceholder}>
                <LoadingSpinner text="Loading 3D model..." size="sm" />
              </div>
            ) : !isViewerCompatible && modelBlobUrl ? (
              <div className={styles.viewerPlaceholder}>
                <p className={styles.noPreview}>
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z" />
                  </svg>
                  Preview not available for {filename.split('.').pop().toUpperCase()} format
                </p>
              </div>
            ) : null}
          </div>
        )}

        {/* Status messages */}
        {(task.status === TASK_STATUS.PENDING || task.status === TASK_STATUS.PROCESSING) && (
          <div className={styles.statusMessage}>
            <div className={styles.pulseOrb} />
            <span>
              {task.status === TASK_STATUS.PENDING
                ? 'Waiting in queue...'
                : 'Generating your 3D model...'}
            </span>
          </div>
        )}

        {task.status === TASK_STATUS.FAILED && (
          <div className={styles.failedMessage}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
            Generation failed. Please try creating a new task.
          </div>
        )}

        {/* Details */}
        <div className={styles.details}>
          <div className={styles.row}>
            <span className={styles.label}>Task ID</span>
            <span className={styles.value}>{task.id}</span>
          </div>
          <div className={styles.row}>
            <span className={styles.label}>Created</span>
            <span className={styles.value}>{formatDateTime(task.createdAt)}</span>
          </div>
          <div className={styles.row}>
            <span className={styles.label}>Updated</span>
            <span className={styles.value}>{formatDateTime(task.updatedAt)}</span>
          </div>
        </div>

        {/* Actions */}
        {task.status === TASK_STATUS.COMPLETED && (
          <div className={styles.actions}>
            <Button
              onClick={triggerFileDownload}
              loading={downloading}
              style={{ width: '100%' }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Download {filename}
            </Button>
          </div>
        )}
      </GlassCard>
    </div>
  )
}

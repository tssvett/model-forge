import styles from './StatusBadge.module.css'

const STATUS_CONFIG = {
  PENDING: { label: 'Pending', className: 'pending' },
  PROCESSING: { label: 'Processing', className: 'processing' },
  COMPLETED: { label: 'Completed', className: 'completed' },
  FAILED: { label: 'Failed', className: 'failed' },
}

export default function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || { label: status, className: 'pending' }

  return (
    <span className={`${styles.badge} ${styles[config.className]}`}>
      {config.label}
    </span>
  )
}

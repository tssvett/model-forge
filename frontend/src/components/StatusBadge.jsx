import { TASK_STATUS } from '../utils/constants'
import styles from './StatusBadge.module.css'

const STATUS_MAP = {
  [TASK_STATUS.PENDING]: styles.pending,
  [TASK_STATUS.PROCESSING]: styles.processing,
  [TASK_STATUS.COMPLETED]: styles.completed,
  [TASK_STATUS.FAILED]: styles.failed,
}

export default function StatusBadge({ status }) {
  return (
    <span className={`${styles.badge} ${STATUS_MAP[status] || ''}`}>
      {status}
    </span>
  )
}

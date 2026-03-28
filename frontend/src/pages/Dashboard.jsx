import { Link } from 'react-router-dom'
import { useTasks } from '../hooks/useTasks'
import { TASK_STATUSES_FILTER } from '../utils/constants'
import { formatRelativeDate } from '../utils/format'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import GlassCard from '../components/GlassCard'
import Button from '../components/Button'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import styles from './Dashboard.module.css'

export default function Dashboard() {
  const {
    tasks, page, totalPages, statusFilter, loading, error,
    setPage, handleStatusChange,
  } = useTasks()

  const truncateId = (id) => id.substring(0, 8)

  return (
    <div className="pageEnter">
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>My Tasks</h1>
          <p className={styles.subtitle}>Manage your 3D model generation tasks</p>
        </div>
        <Link to="/tasks/new" style={{ textDecoration: 'none' }}>
          <Button>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Task
          </Button>
        </Link>
      </div>

      <div className={styles.filters}>
        {TASK_STATUSES_FILTER.map((status) => (
          <button
            key={status}
            className={`${styles.filterBtn} ${statusFilter === status ? styles.filterActive : ''}`}
            onClick={() => handleStatusChange(status)}
          >
            {status || 'All'}
          </button>
        ))}
      </div>

      <ErrorMessage message={error} />

      {loading ? (
        <LoadingSpinner text="Loading tasks..." />
      ) : tasks.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <p>No tasks found</p>
          <Link to="/tasks/new">Create your first task</Link>
        </div>
      ) : (
        <>
          <GlassCard className={styles.tableCard}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id} className={styles.row}>
                    <td className={styles.idCell}>{truncateId(task.id)}</td>
                    <td>
                      <StatusBadge status={task.status} />
                    </td>
                    <td className={styles.dateCell}>{formatRelativeDate(task.createdAt)}</td>
                    <td>
                      <Link to={`/tasks/${task.id}`} className={styles.viewLink}>
                        View
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="9 18 15 12 9 6" />
                        </svg>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </GlassCard>

          <Pagination
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </>
      )}
    </div>
  )
}

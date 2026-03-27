import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getTasks } from '../api/tasks'
import StatusBadge from '../components/StatusBadge'
import Pagination from '../components/Pagination'
import styles from './Dashboard.module.css'

const STATUSES = ['', 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED']
const PAGE_SIZE = 10

export default function Dashboard() {
  const [tasks, setTasks] = useState([])
  const [page, setPage] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchTasks = async () => {
      setLoading(true)
      setError('')
      try {
        const data = await getTasks(page, PAGE_SIZE, statusFilter || undefined)
        setTasks(data.content)
        setTotalPages(data.totalPages)
      } catch (err) {
        setError(err.response?.data?.message || 'Failed to load tasks')
      } finally {
        setLoading(false)
      }
    }

    fetchTasks()
  }, [page, statusFilter])

  const handleStatusChange = (status) => {
    setStatusFilter(status)
    setPage(0)
  }

  const formatDate = (iso) => {
    const date = new Date(iso)
    const now = new Date()
    const diff = now - date
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return 'just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    if (days < 7) return `${days}d ago`
    return date.toLocaleDateString()
  }

  const truncateId = (id) => id.substring(0, 8)

  return (
    <div>
      <div className={styles.header}>
        <h1 className={styles.title}>My Tasks</h1>
        <Link to="/tasks/new" className={styles.newBtn}>
          New Task
        </Link>
      </div>

      <div className={styles.filters}>
        {STATUSES.map((status) => (
          <button
            key={status}
            className={`${styles.filterBtn} ${statusFilter === status ? styles.filterActive : ''}`}
            onClick={() => handleStatusChange(status)}
          >
            {status || 'All'}
          </button>
        ))}
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {loading ? (
        <div className={styles.loading}>Loading tasks...</div>
      ) : tasks.length === 0 ? (
        <div className={styles.empty}>
          <p>No tasks found.</p>
          <Link to="/tasks/new">Create your first task</Link>
        </div>
      ) : (
        <>
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Prompt</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.id} className={styles.row}>
                    <td className={styles.idCell}>{truncateId(task.id)}</td>
                    <td className={styles.promptCell}>
                      {task.prompt || <span className={styles.noPrompt}>—</span>}
                    </td>
                    <td>
                      <StatusBadge status={task.status} />
                    </td>
                    <td className={styles.dateCell}>{formatDate(task.createdAt)}</td>
                    <td>
                      <Link to={`/tasks/${task.id}`} className={styles.viewLink}>
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

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

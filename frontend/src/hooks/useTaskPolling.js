import { useState, useEffect } from 'react'
import { getTask } from '../api/tasks'
import { TASK_STATUS, POLLING_INTERVAL_MS } from '../utils/constants'

export function useTaskPolling(taskId) {
  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let intervalId = null
    let cancelled = false

    const fetchTask = async () => {
      try {
        const data = await getTask(taskId)
        if (cancelled) return
        setTask(data)
        setLoading(false)

        if (data.status === TASK_STATUS.COMPLETED || data.status === TASK_STATUS.FAILED) {
          if (intervalId) clearInterval(intervalId)
        }
      } catch (err) {
        if (cancelled) return
        setError(err.response?.data?.message || 'Failed to load task')
        setLoading(false)
        if (intervalId) clearInterval(intervalId)
      }
    }

    fetchTask()
    intervalId = setInterval(fetchTask, POLLING_INTERVAL_MS)

    return () => {
      cancelled = true
      if (intervalId) clearInterval(intervalId)
    }
  }, [taskId])

  return { task, loading, error, setError }
}

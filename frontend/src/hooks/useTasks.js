import { useState, useEffect, useCallback } from 'react'
import { getTasks } from '../api/tasks'
import { PAGE_SIZE } from '../utils/constants'

export function useTasks() {
  const [tasks, setTasks] = useState([])
  const [page, setPage] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [statusFilter, setStatusFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchTasks = useCallback(async () => {
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
  }, [page, statusFilter])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  const handleStatusChange = useCallback((status) => {
    setStatusFilter(status)
    setPage(0)
  }, [])

  return {
    tasks,
    page,
    totalPages,
    statusFilter,
    loading,
    error,
    setPage,
    handleStatusChange,
    refetch: fetchTasks,
  }
}

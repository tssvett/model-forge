import { useState, useCallback } from 'react'

export function useAsync() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const execute = useCallback(async (asyncFn) => {
    setError('')
    setLoading(true)
    try {
      const result = await asyncFn()
      setData(result)
      return result
    } catch (err) {
      const message = err.response?.data?.message || err.message || 'Something went wrong'
      setError(message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  return { data, error, loading, execute, setError }
}

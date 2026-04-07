import api from './axios'

export async function createTask(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/api/tasks', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded * 100) / event.total))
      }
    },
  })
  return response.data
}

export async function getTasks(page = 0, size = 10, status) {
  const params = { page, size }
  if (status) {
    params.status = status
  }
  const response = await api.get('/api/tasks', { params })
  return response.data
}

export async function getTask(id) {
  const response = await api.get(`/api/tasks/${id}`)
  return response.data
}

export async function getAnalyticsSummary() {
  const response = await api.get('/api/tasks/analytics/summary')
  return response.data
}

export async function getAnalyticsTimeline(days = 30) {
  const response = await api.get('/api/tasks/analytics/timeline', { params: { days } })
  return response.data
}

export async function getTasksWithMetrics(page = 0, size = 20, status) {
  const params = { page, size }
  if (status) params.status = status
  const response = await api.get('/api/tasks/with-metrics', { params })
  return response.data
}

export async function downloadTask(id) {
  const response = await api.get(`/api/tasks/${id}/download`, {
    responseType: 'arraybuffer',
  })
  return {
    data: response.data,
    contentType: response.headers['content-type'],
  }
}

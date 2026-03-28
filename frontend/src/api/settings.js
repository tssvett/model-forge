import api from './axios'

export async function getSettings() {
  const response = await api.get('/api/settings')
  return response.data
}

export async function updateSettings(settings) {
  const response = await api.put('/api/settings', settings)
  return response.data
}

import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 5000,
})

export async function getBackendHealth() {
  const response = await api.get('/health')
  return response.data
}

export async function processPaper(file, onUploadProgress) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/api/papers/process', formData, {
    onUploadProgress,
    timeout: 120000,
  })
  return response.data
}

export default api

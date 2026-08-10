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

export async function generateKnowledgeBase(structuredDocument) {
  const response = await api.post('/api/papers/knowledge-base', structuredDocument, {
    timeout: 30000,
  })
  return response.data
}

export async function queryKnowledgeFact(query) {
  const response = await api.post('/api/knowledge/query', query, {
    timeout: 30000,
  })
  return response.data
}

export async function getReasoningRules() {
  const response = await api.get('/api/reasoning/rules', { timeout: 30000 })
  return response.data
}

export async function runForwardReasoning(knowledgeBase) {
  const response = await api.post('/api/reasoning/forward', { knowledge_base: knowledgeBase }, {
    timeout: 30000,
  })
  return response.data
}

export async function runBackwardReasoning(knowledgeBase, goal) {
  const response = await api.post('/api/reasoning/backward', {
    knowledge_base: knowledgeBase,
    goal,
  }, {
    timeout: 30000,
  })
  return response.data
}

export async function runLogicModelCheck(knowledgeBase, query, includeModels = false) {
  const response = await api.post('/api/logic/model-check', {
    knowledge_base: knowledgeBase,
    query,
    include_models: includeModels,
  }, { timeout: 30000 })
  return response.data
}

export async function runResolutionProof(knowledgeBase, query) {
  const response = await api.post('/api/logic/resolution', {
    knowledge_base: knowledgeBase,
    query,
  }, { timeout: 30000 })
  return response.data
}

export async function checkLogicConsistency(knowledgeBase) {
  const response = await api.post('/api/logic/consistency', {
    knowledge_base: knowledgeBase,
  }, { timeout: 30000 })
  return response.data
}

export default api

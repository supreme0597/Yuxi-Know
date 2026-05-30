import { apiGet } from './base'

export const searchMentionFiles = (threadId, query, signal) => {
  // NOTE: threadId 是后端必填参数，为空时直接返回空数组，不发请求
  if (!threadId) return Promise.resolve([])
  const params = new URLSearchParams()
  params.set('thread_id', threadId)
  if (query) params.set('query', query)
  return apiGet(`/api/mention/search?${params.toString()}`, { signal })
}

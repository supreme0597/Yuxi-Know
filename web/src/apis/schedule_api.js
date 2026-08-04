import { apiGet, apiPost, apiPut, apiPatch, apiDelete } from './base'

export const scheduleApi = {
  list: (params) => apiGet('/api/schedules', { params }),

  create: (data) => apiPost('/api/schedules', data),

  get: (id) => apiGet(`/api/schedules/${id}`),

  update: (id, data) => apiPut(`/api/schedules/${id}`, data),

  // 局部更新（含启用/禁用开关），超管也可用
  patch: (id, data) => apiPatch(`/api/schedules/${id}`, data),

  delete: (id) => apiDelete(`/api/schedules/${id}`),

  trigger: (id) => apiPost(`/api/schedules/${id}/trigger`),

  listLogs: (id, params) => apiGet(`/api/schedules/${id}/logs`, { params })
}

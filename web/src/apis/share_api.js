import { apiDelete, apiGet, apiPost } from './base'

/**
 * 对话分享 API 模块
 * 公开读接口（匿名，requiresAuth=false）与管理接口（需登录）
 */

export const shareApi = {
  /**
   * 匿名查看分享会话元信息与历史消息（含工具调用）
   * @param {string} threadId
   * @param {string} token
   */
  getSharedThread: (threadId, token) => {
    const query = new URLSearchParams({ token })
    return apiGet(`/api/share/${threadId}?${query.toString()}`, {}, false)
  },

  /**
   * 匿名查看分享会话 agent_state
   * @param {string} threadId
   * @param {string} token
   */
  getSharedState: (threadId, token) => {
    const query = new URLSearchParams({ token })
    return apiGet(`/api/share/${threadId}/state?${query.toString()}`, {}, false)
  },

  /**
   * 匿名查看分享会话文件列表
   * @param {string} threadId
   * @param {string} token
   * @param {string} [path]
   * @param {boolean} [recursive]
   */
  getSharedFiles: (threadId, token, path = null, recursive = false) => {
    const query = new URLSearchParams({ token })
    if (path) query.set('path', path)
    if (recursive) query.set('recursive', 'true')
    return apiGet(`/api/share/${threadId}/files?${query.toString()}`, {}, false)
  },

  /**
   * 匿名查看分享会话文件内容
   * @param {string} threadId
   * @param {string} token
   * @param {string} path
   * @param {number} [offset]
   * @param {number} [limit]
   */
  getSharedFileContent: (threadId, token, path, offset = 0, limit = 2000) => {
    const query = new URLSearchParams({ token, path })
    if (offset) query.set('offset', String(offset))
    if (limit) query.set('limit', String(limit))
    return apiGet(`/api/share/${threadId}/files/content?${query.toString()}`, {}, false)
  },

  /**
   * 拼装分享会话交付件下载/预览 URL（仅拼 URL，不带 token 之外的处理）
   * @param {string} threadId
   * @param {string} path
   * @param {string} token
   * @param {boolean} [download]
   */
  getSharedArtifactUrl: (threadId, path, token, download = false) => {
    const encoded = String(path)
      .split('/')
      .filter(Boolean)
      .map((segment) => encodeURIComponent(segment))
      .join('/')
    const query = new URLSearchParams({ token })
    if (download) query.set('download', 'true')
    return `/api/share/${threadId}/artifacts/${encoded}?${query.toString()}`
  },

  // ========== 管理接口（需登录，仅会话拥有者） ==========

  /**
   * 创建/复用对话分享
   * @param {string} threadId
   * @param {number} expiresDays
   */
  createShare: (threadId, expiresDays) =>
    apiPost(`/api/chat/thread/${threadId}/share`, { expires_days: expiresDays }),

  /**
   * 查询当前有效分享
   * @param {string} threadId
   */
  getShare: (threadId) => apiGet(`/api/chat/thread/${threadId}/share`),

  /**
   * 撤销对话分享
   * @param {string} threadId
   */
  revokeShare: (threadId) => apiDelete(`/api/chat/thread/${threadId}/share`)
}

/**
 * useKanbanChat - 看板 AI 对话核心 composable
 *
 * 从 AgentChatComponent 提取的核心对话逻辑，用于嵌入 AI 侧边栏。
 * 复用主项目的 agentStore、API、消息处理工具，但不依赖 chatUIStore/sidebar/route 等。
 *
 * 简化点：
 * - 使用 defaultAgent，自动选中名字含"项目管理"的 Config（配置档案）
 * - 发送消息时自动创建线程，无手动创建对话流程
 * - 支持 Run API 与 legacy stream 双路径，按功能开关选择发送模式
 * - 无人工审批流程
 * - 无 AgentPanel / Artifacts 卡片展示（侧边栏空间有限）
 */
import { ref, reactive, computed } from 'vue'
import { message as antMessage } from 'ant-design-vue'
import { useAgentStore } from '@/stores/agent'
import { agentApi, threadApi } from '@/apis'
import { useAgentThreadState } from '@/composables/useAgentThreadState'
import { useAgentStreamHandler } from '@/composables/useAgentStreamHandler'
import { useAgentRunStream } from '@/composables/useAgentRunStream'
import { useStreamSmoother } from '@/composables/useStreamSmoother'
import { MessageProcessor } from '@/utils/messageProcessor'

// 单例状态：多个组件共享同一个对话会话
const chatState = reactive({
  isInitialized: false,
  isInitializing: false,
  currentThreadId: null,
  // 以 threadId 为键的线程状态
  threadStates: {}
})

const threadMessages = ref({})

const streamSmoother = useStreamSmoother({
  getThreadState: (threadId) => chatState.threadStates[threadId] || null
})

// ==================== 看板 Agent & Config 选择逻辑 ====================
/**
 * 看板 AI 对话使用的 Agent：
 * 直接使用 defaultAgent（看板不切换 Agent）
 */
function resolveKanbanAgentId(agentStore) {
  return agentStore.defaultAgentId || (agentStore.agents?.length > 0 ? agentStore.agents[0].id : null)
}

/**
 * 看板 AI 对话使用的 Config（配置档案）：
 * 1. 遍历当前 Agent 的 configs 列表，找名字含"项目管理"的第一个
 * 2. 找不到则回退 is_default 配置
 * 3. 再没有则取第一个
 *
 * 注意："项目管理"是 Config 名（/agent/{agentId}/configs 返回的），
 *       不是 Agent 名（/api/chat/agent 返回的）
 */
function resolveKanbanConfigId(agentStore) {
  const agentId = resolveKanbanAgentId(agentStore)
  if (!agentId) return null
  const list = agentStore.agentConfigs?.[agentId] || []
  const matched = list.find((c) => c.name && c.name.includes('项目管理'))
  if (matched) return matched.id
  return list.find((c) => c.is_default)?.id || (list.length > 0 ? list[0].id : null)
}

/** 看板对话专用的 Agent 对象 */
const kanbanAgent = computed(() => {
  const agentStore = useAgentStore()
  const id = resolveKanbanAgentId(agentStore)
  if (!id) return null
  return (agentStore.agents || []).find((a) => a.id === id) || null
})

/** 看板对话专用的 Agent ID */
const kanbanAgentId = computed(() => kanbanAgent.value?.id || null)

/** 看板对话专用的 Config ID */
const kanbanConfigId = computed(() => resolveKanbanConfigId(useAgentStore()))

const { getThreadState, resetOnGoingConv } = useAgentThreadState({
  chatState,
  getCurrentThreadId: () => chatState.currentThreadId,
  onStopThread: (threadId) => streamSmoother.flushThread(threadId),
  onBeforeResetThread: (threadId) => streamSmoother.resetThread(threadId),
  onBeforeCleanupThread: (threadId) => streamSmoother.resetThread(threadId)
})

const { handleAgentResponse, handleStreamChunk } = useAgentStreamHandler({
  getThreadState,
  processApprovalInStream: () => false, // 看板版不处理审批
  currentAgentId: computed(() => kanbanAgentId.value),
  supportsFiles: computed(() => true),
  streamSmoother
})

const runsApiEnabled =
  import.meta.env.VITE_USE_RUNS_API === 'true' &&
  localStorage.getItem('force_legacy_stream') !== 'true'

export const createClientRequestId = () => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `req-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export const buildOptimisticHumanMessage = ({ requestId, text, imageContent = null }) => {
  const message = {
    id: requestId,
    role: 'user',
    type: 'human',
    content: text,
    message_type: imageContent ? 'multimodal_image' : 'text',
    extra_metadata: {
      request_id: requestId
    }
  }

  if (imageContent) {
    message.image_content = imageContent
  }

  return message
}

export const insertOptimisticHumanMessage = (threadState, { requestId, text, imageContent = null }) => {
  if (!threadState || !requestId) return
  threadState.pendingRequestId = requestId
  threadState.replyLoadingVisible = false
  threadState.onGoingConv.msgChunks[requestId] = [
    buildOptimisticHumanMessage({ requestId, text, imageContent })
  ]
}

// ==================== 自动滚动管理 ====================
let scrollContainerRef = null

/** 用户是否主动向上滚动了（暂停自动跟滚，直到下次发消息才恢复） */
let userScrolledUp = false

/** 强制滚到底部后的延迟补滚定时器 */
let scrollRetryTimer = null

// ==================== RAF 跟滚循环 ====================
let streamFollowRafId = null

function startStreamFollow() {
  stopStreamFollow()
  function tick() {
    if (scrollContainerRef) {
      scrollContainerRef.scrollTop = scrollContainerRef.scrollHeight
    }
    streamFollowRafId = requestAnimationFrame(tick)
  }
  streamFollowRafId = requestAnimationFrame(tick)
}

function stopStreamFollow() {
  if (streamFollowRafId != null) {
    cancelAnimationFrame(streamFollowRafId)
    streamFollowRafId = null
  }
}

// ==================== 滚动容器管理 ====================

export function setScrollContainer(el) {
  if (scrollContainerRef && scrollContainerRef !== el) {
    scrollContainerRef.removeEventListener('wheel', onWheelUp)
  }
  scrollContainerRef = el
  if (el) {
    // wheel 事件：比 scroll 更早触发，能在 RAF tick 之前捕获用户意图
    el.addEventListener('wheel', onWheelUp, { passive: true })
  }
}

/**
 * wheel 事件处理器：检测向上滚动意图
 * wheel 事件在 scroll 事件之前触发，比 RAF tick 更早
 * 一旦检测到向上滚轮，立即停止 RAF 并标记状态
 * 跟滚不会自动恢复——只有下次发消息时 resetAutoScroll() 才恢复
 */
function onWheelUp(e) {
  if (e.deltaY < 0) {
    userScrolledUp = true
    stopStreamFollow()
  }
}

/**
 * 滚动到底部
 * @param {boolean} force - true 时忽略用户滚动状态（发消息等场景）
 */
function scrollToBottom(force = false) {
  if (!scrollContainerRef) return
  if (!force && userScrolledUp) return

  const doScroll = () => {
    if (!scrollContainerRef) return
    scrollContainerRef.scrollTop = scrollContainerRef.scrollHeight
  }

  requestAnimationFrame(() => {
    doScroll()
    if (force) {
      clearTimeout(scrollRetryTimer)
      scrollRetryTimer = setTimeout(() => {
        if (scrollContainerRef) {
          scrollContainerRef.scrollTop = scrollContainerRef.scrollHeight
        }
      }, 350)
    }
  })
}

/** 重置用户滚动状态（新消息发送时调用，恢复自动跟滚） */
function resetAutoScroll() {
  userScrolledUp = false
}

/** 设置流式活跃状态（由 AISidepanel 的 isProcessing watcher 调用） */
function setStreamActive(active) {
  if (active) {
    if (!userScrolledUp) {
      startStreamFollow()
    }
  } else {
    stopStreamFollow()
  }
}

// ==================== 初始化 ====================
async function initialize() {
  if (chatState.isInitialized) {
    if (runsApiEnabled && chatState.currentThreadId) {
      await resumeActiveRunForThread(chatState.currentThreadId)
    }
    return
  }
  if (chatState.isInitializing) return

  const agentStore = useAgentStore()
  chatState.isInitializing = true
  try {
    if (!agentStore.isInitialized) {
      await agentStore.initialize()
    }
    chatState.isInitialized = true
    if (runsApiEnabled && chatState.currentThreadId) {
      await resumeActiveRunForThread(chatState.currentThreadId)
    }
  } catch (err) {
    console.error('[KanbanChat] Init failed:', err)
    antMessage.error('AI 智能体初始化失败')
  } finally {
    chatState.isInitializing = false
  }
}

// ==================== 线程管理 ====================
async function ensureActiveThread(title = '新的对话') {
  if (chatState.currentThreadId) return chatState.currentThreadId

  const agentId = kanbanAgentId.value
  if (!agentId) {
    antMessage.error('未找到可用的 AI 智能体')
    return null
  }

  try {
    const thread = await threadApi.createThread(agentId, title)
    if (thread) {
      chatState.currentThreadId = thread.id
      threadMessages.value[thread.id] = []
      if (runsApiEnabled) {
        await resumeActiveRunForThread(thread.id)
      }
      return thread.id
    }
  } catch (err) {
    console.error('[KanbanChat] Create thread failed:', err)
    antMessage.error('创建对话失败')
  }
  return null
}

/** 剥离消息中的 <context>...</context> 块，用户不应看到隐藏上下文 */
function stripContextFromContent(content) {
  if (typeof content !== 'string') return content
  return content.replace(/<context>[\s\S]*?<\/context>\s*/g, '').trim()
}

/** 批量剥离历史消息中的隐藏上下文 */
function stripContextFromHistory(history) {
  if (!Array.isArray(history)) return history
  return history.map(msg => {
    if (msg.type === 'human' && typeof msg.content === 'string') {
      return { ...msg, content: stripContextFromContent(msg.content) }
    }
    return msg
  })
}

async function fetchThreadMessages(threadId) {
  if (!threadId) return
  try {
    const response = await agentApi.getAgentHistory(threadId)
    threadMessages.value[threadId] = stripContextFromHistory(response.history || [])
  } catch (err) {
    console.error('[KanbanChat] Fetch messages failed:', err)
  }
}

async function fetchThreadMessagesForRun({ agentId, threadId, delay = 0 }) {
  if (!agentId || !threadId) return

  if (delay > 0) {
    await new Promise((resolve) => setTimeout(resolve, delay))
  }

  await fetchThreadMessages(threadId)
}

async function fetchAgentState(agentId, threadId) {
  if (!agentId || !threadId) return

  try {
    const res = await agentApi.getAgentState(threadId)
    const threadState = getThreadState(threadId)
    if (threadState) {
      threadState.agentState = res.agent_state || null
    }
  } catch {
    // 忽略状态拉取失败，不阻塞消息流结束后的历史刷新。
  }
}

const { startRunStream, resumeActiveRunForThread } = useAgentRunStream({
  getThreadState,
  useRunsApi: runsApiEnabled,
  currentAgentId: computed(() => kanbanAgentId.value),
  handleStreamChunk,
  processApprovalInStream: () => false,
  fetchThreadMessages: fetchThreadMessagesForRun,
  fetchAgentState,
  resetOnGoingConv,
  onScrollToBottom: () => scrollToBottom(true),
  streamSmoother
})

// ==================== 消息发送 ====================
/**
 * 发送消息到 AI 对话
 * @param {string} text - 用户输入的消息文本
 * @param {object} [options] - 可选参数
 * @param {string} [options.context] - 隐藏上下文（数据概览），拼接到 query 前面，用户不可见
 */
async function sendMessage(text, options = {}) {
  if (!text?.trim()) return

  const agentId = kanbanAgentId.value
  const configId = kanbanConfigId.value
  if (!agentId) {
    antMessage.error('AI 智能体未就绪，请稍后再试')
    return
  }

  if (!configId) {
    antMessage.error('智能体配置未就绪')
    return
  }

  // 确保有活跃线程
  let threadId = chatState.currentThreadId
  if (!threadId) {
    threadId = await ensureActiveThread(text)
    if (!threadId) return
  }

  const threadState = getThreadState(threadId)
  if (!threadState) return

  // 构建 query：如果有 context，拼接到前面作为隐藏上下文
  let query = text
  if (options.context) {
    query = `<context>\n${options.context}\n</context>\n\n${text}`
  }

  resetOnGoingConv(threadId)
  const requestId = createClientRequestId()
  insertOptimisticHumanMessage(threadState, {
    requestId,
    text,
    imageContent: null
  })

  if (runsApiEnabled) {
    threadState.isStreaming = true
    try {
      const runResp = await agentApi.createAgentRun({
        query,
        agent_config_id: configId,
        thread_id: threadId,
        meta: {
          request_id: requestId
        },
        image_content: null
      })
      const runId = runResp?.run_id
      if (!runId) {
        throw new Error('创建 run 失败：缺少 run_id')
      }
      await startRunStream(threadId, runId, 0)
    } catch (err) {
      threadState.isStreaming = false
      threadState.replyLoadingVisible = false
      threadState.pendingRequestId = null
      resetOnGoingConv(threadId)
      console.error('[KanbanChat] Send failed:', err)
      antMessage.error('消息发送失败')
    }
    return
  }

  // 开始 legacy 流式处理
  threadState.isStreaming = true
  threadState.streamAbortController = new AbortController()

  try {
    const response = await agentApi.sendAgentMessage(
      {
        query,
        thread_id: threadId,
        agent_config_id: configId
      },
      { signal: threadState.streamAbortController.signal }
    )

    await handleAgentResponse(response, threadId)
  } catch (err) {
    if (err.name !== 'AbortError') {
      console.error('[KanbanChat] Send failed:', err)
      antMessage.error('消息发送失败')
    }
    threadState.isStreaming = false
    threadState.replyLoadingVisible = false
    threadState.pendingRequestId = null
  } finally {
    threadState.streamAbortController = null
    // 异步刷新历史记录
    fetchThreadMessages(threadId).finally(() => {
      resetOnGoingConv(threadId)
    })
  }
}

async function stopGeneration() {
  const threadId = chatState.currentThreadId
  const threadState = getThreadState(threadId)
  if (!threadState || !threadState.isStreaming) return

  if (runsApiEnabled && threadState.activeRunId) {
    try {
      await agentApi.cancelAgentRun(threadState.activeRunId)
      antMessage.info('已发送取消请求')
    } catch (err) {
      console.error('[KanbanChat] Stop run failed:', err)
      antMessage.error('中断生成失败')
    }
    return
  }

  if (threadState.streamAbortController) {
    threadState.streamAbortController.abort()
    threadState.streamAbortController = null
  }

  // 延迟刷新以获取中断后的完整状态
  setTimeout(() => {
    fetchThreadMessages(threadId).finally(() => {
      resetOnGoingConv(threadId)
    })
  }, 500)

  antMessage.info('已中断生成')
}

// ==================== 计算属性 ====================
const isProcessing = computed(() => {
  const threadState = getThreadState(chatState.currentThreadId)
  return threadState ? threadState.isStreaming : false
})

const currentAgentName = computed(() => {
  return kanbanAgent.value?.name || 'AI 助手'
})

const currentAgentId = computed(() => {
  return kanbanAgentId.value
})

const chatActive = computed(() => {
  // 有历史消息或正在进行中，即为对话已激活
  const threadId = chatState.currentThreadId
  if (!threadId) return false
  const msgs = threadMessages.value[threadId]
  return Array.isArray(msgs) && msgs.length > 0
})

const onGoingConvMessages = computed(() => {
  const threadId = chatState.currentThreadId
  const threadState = getThreadState(threadId)
  if (!threadState || !threadState.onGoingConv) return []

  const msgs = Object.values(threadState.onGoingConv.msgChunks).map(
    MessageProcessor.mergeMessageChunk
  )
  return msgs.length > 0
    ? MessageProcessor.convertToolResultToMessages(msgs).filter((msg) => msg.type !== 'tool')
    : []
})

const historyConversations = computed(() => {
  const threadId = chatState.currentThreadId
  return MessageProcessor.convertServerHistoryToMessages(threadMessages.value[threadId] || [])
})

const conversations = computed(() => {
  const history = historyConversations.value

  if (onGoingConvMessages.value.length > 0) {
    return [
      ...history,
      { messages: onGoingConvMessages.value, status: 'streaming' }
    ]
  }
  return history
})

// ==================== Agent 状态 & Mention 配置 ====================
// 看板场景：自动选择"项目管理"Agent（或回退 defaultAgent），用户不可切换。
// @提及应展示全部可用资源（不受 agentConfig/configurableItems 过滤限制）。
// 直接从 store 读取，单层 computed，Vue 模板自动解包 ComputedRef。
const mentionConfig = computed(() => {
  const agentStore = useAgentStore()
  const kb = agentStore.availableKnowledgeBases || []
  const mcps = agentStore.availableMcps || []
  const skills = agentStore.availableSkills || []
  const hasAny = kb.length || mcps.length || skills.length
  const result = hasAny ? { files: [], knowledgeBases: kb, mcps: mcps, skills: skills, subagents: [] } : null
  return result
})

const supportsFileUpload = computed(() => {
  const agent = kanbanAgent.value
  if (!agent) return false
  return (agent.capabilities || []).includes('file_upload')
})

const currentTodos = computed(() => {
  const threadId = chatState.currentThreadId
  const threadState = threadId ? getThreadState(threadId) : null
  const todos = threadState?.agentState?.todos
  return Array.isArray(todos) ? todos : []
})

// 附件上传
async function handleAttachmentUpload(files) {
  const threadId = chatState.currentThreadId
  if (!threadId) {
    antMessage.warning('请先开始对话')
    return
  }
  try {
    antMessage.loading({ content: '正在上传附件...', key: 'kanban-upload', duration: 0 })
    for (const file of files) {
      await threadApi.uploadThreadAttachment(threadId, file)
    }
    antMessage.success({ content: '附件上传成功', key: 'kanban-upload', duration: 2 })
    // 刷新 agent state 以更新 mention 中的文件列表
    try {
      await agentApi.getAgentState(threadId)
    } catch { /* ignore */ }
  } catch (error) {
    antMessage.destroy('kanban-upload')
    antMessage.error('附件上传失败')
    console.error('[KanbanChat] Upload failed:', error)
  }
}

// ==================== 导出 ====================
export function useKanbanChat() {
  return {
    // 状态
    conversations,
    isProcessing,
    chatActive,
    currentAgentName,
    currentAgentId,
    selectedAgentConfigId: kanbanConfigId,
    agentState: computed(() => {
      const threadId = chatState.currentThreadId
      return threadId ? getThreadState(threadId)?.agentState || null : null
    }),
    threadFiles: computed(() => {
      const threadId = chatState.currentThreadId
      const threadState = threadId ? getThreadState(threadId) : null
      return threadState?.agentState?.files ? Object.entries(threadState.agentState.files).map(([path, data]) => ({ path, ...data })) : []
    }),
    isInitialized: computed(() => chatState.isInitialized),
    isInitializing: computed(() => chatState.isInitializing),

    // 输入增强功能
    mentionConfig,
    supportsFileUpload,
    currentTodos,

    // 方法
    initialize,
    sendMessage,
    stopGeneration,
    scrollToBottom,
    resetAutoScroll,
    setStreamActive,
    handleAttachmentUpload,

    // 内部引用（供组件直接使用）
    getThreadState,
    currentThreadId: computed(() => chatState.currentThreadId)
  }
}

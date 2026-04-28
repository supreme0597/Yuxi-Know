/**
 * useKanbanChat - 看板 AI 对话核心 composable
 *
 * 从 AgentChatComponent 提取的核心对话逻辑，用于嵌入 AI 侧边栏。
 * 复用主项目的 agentStore、API、消息处理工具，但不依赖 chatUIStore/sidebar/route 等。
 *
 * 简化点：
 * - 直接使用 defaultAgent，无 agent 选择器
 * - 发送消息时自动创建线程，无手动创建对话流程
 * - 仅使用 legacy stream 模式，不用 Run 模式 SSE
 * - 无人工审批流程
 * - 无 AgentPanel / Artifacts 卡片展示（侧边栏空间有限）
 */
import { ref, reactive, computed, nextTick } from 'vue'
import { message as antMessage } from 'ant-design-vue'
import { useAgentStore } from '@/stores/agent'
import { agentApi, threadApi } from '@/apis'
import { useAgentThreadState } from '@/composables/useAgentThreadState'
import { useAgentStreamHandler } from '@/composables/useAgentStreamHandler'
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

const { getThreadState, resetOnGoingConv, stopThreadStream } = useAgentThreadState({
  chatState,
  getCurrentThreadId: () => chatState.currentThreadId,
  onStopThread: (threadId) => streamSmoother.flushThread(threadId),
  onBeforeResetThread: (threadId) => streamSmoother.resetThread(threadId),
  onBeforeCleanupThread: (threadId) => streamSmoother.resetThread(threadId)
})

const { handleAgentResponse } = useAgentStreamHandler({
  getThreadState,
  processApprovalInStream: () => false, // 看板版不处理审批
  currentAgentId: computed(() => {
    const agentStore = useAgentStore()
    return agentStore.defaultAgentId
  }),
  supportsFiles: computed(() => true),
  streamSmoother
})

// ==================== 自动滚动管理 ====================
let scrollContainerRef = null

export function setScrollContainer(el) {
  scrollContainerRef = el
}

function scrollToBottom(force = false) {
  if (!scrollContainerRef) return
  const el = scrollContainerRef
  const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120
  if (force || isNearBottom) {
    nextTick(() => {
      el.scrollTop = el.scrollHeight
    })
  }
}

// ==================== 初始化 ====================
async function initialize() {
  if (chatState.isInitialized || chatState.isInitializing) return

  const agentStore = useAgentStore()
  chatState.isInitializing = true
  try {
    if (!agentStore.isInitialized) {
      await agentStore.initialize()
    }
    chatState.isInitialized = true
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

  const agentStore = useAgentStore()
  const agentId = agentStore.defaultAgentId
  if (!agentId) {
    antMessage.error('未找到可用的 AI 智能体')
    return null
  }

  try {
    const thread = await threadApi.createThread(agentId, title)
    if (thread) {
      chatState.currentThreadId = thread.id
      threadMessages.value[thread.id] = []
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

// ==================== 消息发送 ====================
/**
 * 发送消息到 AI 对话
 * @param {string} text - 用户输入的消息文本
 * @param {object} [options] - 可选参数
 * @param {string} [options.context] - 隐藏上下文（数据概览），拼接到 query 前面，用户不可见
 */
async function sendMessage(text, options = {}) {
  if (!text?.trim()) return

  const agentStore = useAgentStore()
  const agentId = agentStore.defaultAgentId
  if (!agentId) {
    antMessage.error('AI 智能体未就绪，请稍后再试')
    return
  }

  if (!agentStore.selectedAgentConfigId) {
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

  // 立即将用户消息添加到历史，无需等待后端刷新
  const currentHistory = threadMessages.value[threadId] || []
  threadMessages.value[threadId] = [...currentHistory, { type: 'human', content: text }]

  // 构建 query：如果有 context，拼接到前面作为隐藏上下文
  let query = text
  if (options.context) {
    query = `<context>\n${options.context}\n</context>\n\n${text}`
  }

  // 开始流式处理
  threadState.isStreaming = true
  resetOnGoingConv(threadId)
  threadState.streamAbortController = new AbortController()

  try {
    const response = await agentApi.sendAgentMessage(
      {
        query,
        thread_id: threadId,
        agent_config_id: agentStore.selectedAgentConfigId
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
  } finally {
    threadState.streamAbortController = null
    // 异步刷新历史记录
    fetchThreadMessages(threadId).finally(() => {
      resetOnGoingConv(threadId)
    })
  }
}

function stopGeneration() {
  const threadId = chatState.currentThreadId
  const threadState = getThreadState(threadId)
  if (!threadState || !threadState.isStreaming) return

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
  const agentStore = useAgentStore()
  return agentStore.defaultAgent?.name || 'AI 助手'
})

const currentAgentId = computed(() => {
  const agentStore = useAgentStore()
  return agentStore.defaultAgentId
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
// 看板场景：defaultAgent 固定、用户不可切换，
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
  const agentStore = useAgentStore()
  const agent = agentStore.defaultAgent
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
    } catch (_) { /* ignore */ }
  } catch (error) {
    antMessage.destroy('kanban-upload')
    antMessage.error('附件上传失败')
    console.error('[KanbanChat] Upload failed:', error)
  }
}

// ==================== 导出 ====================
export function useKanbanChat() {
  const agentStore = useAgentStore()

  return {
    // 状态
    conversations,
    isProcessing,
    chatActive,
    currentAgentName,
    currentAgentId,
    selectedAgentConfigId: computed(() => agentStore.selectedAgentConfigId),
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
    handleAttachmentUpload,

    // 内部引用（供组件直接使用）
    getThreadState,
    currentThreadId: computed(() => chatState.currentThreadId)
  }
}

import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  agentStore: {
    isInitialized: true,
    initialize: vi.fn(async () => {}),
    defaultAgentId: 'agent-1',
    agents: [
      {
        id: 'agent-1',
        name: '默认智能体',
        capabilities: ['file_upload']
      }
    ],
    agentConfigs: {
      'agent-1': [
        { id: 'default-config', name: '默认配置', is_default: true },
        { id: 'project-management-config', name: '项目管理' }
      ]
    },
    availableKnowledgeBases: [],
    availableMcps: [],
    availableSkills: []
  },
  agentApi: {
    createAgentRun: vi.fn(),
    sendAgentMessage: vi.fn(),
    cancelAgentRun: vi.fn(),
    getAgentHistory: vi.fn(),
    getAgentState: vi.fn(),
    getThreadActiveRun: vi.fn(),
    getAgentRun: vi.fn(),
    streamAgentRunEvents: vi.fn()
  },
  threadApi: {
    createThread: vi.fn(),
    uploadThreadAttachment: vi.fn()
  },
  startRunStream: vi.fn(),
  resumeActiveRunForThread: vi.fn(),
  stopRunStreamSubscription: vi.fn(),
  handleAgentResponse: vi.fn(),
  handleStreamChunk: vi.fn(),
  message: {
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
    loading: vi.fn(),
    success: vi.fn(),
    destroy: vi.fn()
  }
}))

vi.mock('@/apis', () => ({
  agentApi: mocks.agentApi,
  threadApi: mocks.threadApi
}))

vi.mock('@/stores/agent', () => ({
  useAgentStore: () => mocks.agentStore
}))

vi.mock('@/composables/useAgentRunStream', () => ({
  useAgentRunStream: vi.fn(() => ({
    startRunStream: mocks.startRunStream,
    resumeActiveRunForThread: mocks.resumeActiveRunForThread,
    stopRunStreamSubscription: mocks.stopRunStreamSubscription
  }))
}))

vi.mock('@/composables/useAgentStreamHandler', () => ({
  useAgentStreamHandler: vi.fn(() => ({
    handleAgentResponse: mocks.handleAgentResponse,
    handleStreamChunk: mocks.handleStreamChunk
  }))
}))

vi.mock('@/composables/useStreamSmoother', () => ({
  useStreamSmoother: vi.fn(() => ({
    flushThread: vi.fn(),
    resetThread: vi.fn()
  }))
}))

vi.mock('ant-design-vue', () => ({
  message: mocks.message
}))

const THREAD_ID = 'kanban-thread-1'
const RUN_ID = 'run-123'
const USER_MESSAGE = 'Move task A to Done'
const HIDDEN_CONTEXT = 'Board: Demo Project; Task A status: In Progress'

const resetApiMocks = () => {
  mocks.agentApi.createAgentRun.mockResolvedValue({ run_id: RUN_ID })
  mocks.agentApi.sendAgentMessage.mockResolvedValue({ ok: true })
  mocks.agentApi.cancelAgentRun.mockResolvedValue({ ok: true })
  mocks.agentApi.getAgentHistory.mockResolvedValue({ history: [] })
  mocks.agentApi.getAgentState.mockResolvedValue({ agent_state: null })
  mocks.agentApi.getThreadActiveRun.mockResolvedValue({ run: null })
  mocks.agentApi.getAgentRun.mockResolvedValue({ run: null })
  mocks.agentApi.streamAgentRunEvents.mockResolvedValue({ ok: true })
  mocks.threadApi.createThread.mockResolvedValue({ id: THREAD_ID })
  mocks.threadApi.uploadThreadAttachment.mockResolvedValue({ ok: true })
  mocks.startRunStream.mockResolvedValue(undefined)
  mocks.resumeActiveRunForThread.mockResolvedValue(undefined)
  mocks.handleAgentResponse.mockResolvedValue(undefined)
}

const importKanbanChat = async ({ runsApi = true, forceLegacy = false } = {}) => {
  vi.resetModules()
  vi.stubEnv('VITE_USE_RUNS_API', runsApi ? 'true' : 'false')
  if (forceLegacy) {
    localStorage.setItem('force_legacy_stream', 'true')
  } else {
    localStorage.removeItem('force_legacy_stream')
  }

  const mod = await import('../useKanbanChat.js')
  return mod.useKanbanChat()
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.unstubAllEnvs()
  localStorage.clear()
  mocks.agentStore.isInitialized = true
  mocks.agentStore.initialize.mockResolvedValue(undefined)
  resetApiMocks()
})

describe('useKanbanChat', () => {
  it('creates a Run with hidden context and starts the Run stream when Run mode is enabled', async () => {
    const chat = await importKanbanChat({ runsApi: true })

    await chat.sendMessage(USER_MESSAGE, { context: HIDDEN_CONTEXT })

    expect(mocks.threadApi.createThread).toHaveBeenCalledWith('agent-1', USER_MESSAGE)
    expect(mocks.agentApi.createAgentRun).toHaveBeenCalledWith({
      query: `<context>\n${HIDDEN_CONTEXT}\n</context>\n\n${USER_MESSAGE}`,
      agent_config_id: 'project-management-config',
      thread_id: THREAD_ID,
      meta: {
        request_id: expect.any(String)
      },
      image_content: null
    })
    expect(mocks.agentApi.sendAgentMessage).not.toHaveBeenCalled()
    expect(mocks.startRunStream).toHaveBeenCalledWith(THREAD_ID, RUN_ID, 0)
  })

  it('shows the optimistic human message without exposing hidden context', async () => {
    const chat = await importKanbanChat({ runsApi: true })

    await chat.sendMessage(USER_MESSAGE, { context: HIDDEN_CONTEXT })

    const visibleHumanMessage = chat.conversations.value.at(-1)?.messages?.[0]

    expect(visibleHumanMessage).toMatchObject({
      type: 'human',
      content: USER_MESSAGE
    })
    expect(visibleHumanMessage.content).not.toContain('<context>')
    expect(visibleHumanMessage.content).not.toContain(HIDDEN_CONTEXT)
  })

  it('strips hidden context from ongoing stream-init human messages', async () => {
    const chat = await importKanbanChat({ runsApi: true })

    await chat.sendMessage(USER_MESSAGE, { context: HIDDEN_CONTEXT })

    const requestId = mocks.agentApi.createAgentRun.mock.calls[0][0].meta.request_id
    chat.getThreadState(THREAD_ID).onGoingConv.msgChunks[requestId] = [
      {
        id: requestId,
        role: 'user',
        type: 'human',
        content: `<context>{"cardId":"card-1","title":"测试卡片"}</context>\n\n请总结这个卡片`,
        extra_metadata: {
          request_id: requestId
        }
      }
    ]

    const visibleHumanMessage = chat.conversations.value.at(-1)?.messages?.[0]

    expect(visibleHumanMessage).toMatchObject({
      type: 'human',
      content: '请总结这个卡片'
    })
    expect(visibleHumanMessage.content).not.toContain('<context>')
    expect(visibleHumanMessage.content).not.toContain('</context>')
    expect(visibleHumanMessage.content).not.toContain('card-1')
    expect(visibleHumanMessage.content).not.toContain('测试卡片')
  })

  it('uses the legacy stream when localStorage forces legacy mode', async () => {
    const chat = await importKanbanChat({ runsApi: true, forceLegacy: true })

    await chat.sendMessage(USER_MESSAGE, { context: HIDDEN_CONTEXT })

    expect(mocks.agentApi.sendAgentMessage).toHaveBeenCalledWith(
      {
        query: `<context>\n${HIDDEN_CONTEXT}\n</context>\n\n${USER_MESSAGE}`,
        thread_id: THREAD_ID,
        agent_config_id: 'project-management-config'
      },
      { signal: expect.any(AbortSignal) }
    )
    expect(mocks.agentApi.createAgentRun).not.toHaveBeenCalled()
    expect(mocks.startRunStream).not.toHaveBeenCalled()
  })

  it('strips hidden context from fetched human history', async () => {
    mocks.agentApi.getAgentHistory.mockResolvedValue({
      history: [
        {
          type: 'human',
          content: `<context>\n${HIDDEN_CONTEXT}\n</context>\n\n${USER_MESSAGE}`
        }
      ]
    })
    const chat = await importKanbanChat({ runsApi: true, forceLegacy: true })

    await chat.sendMessage(USER_MESSAGE, { context: HIDDEN_CONTEXT })

    await vi.waitFor(() => {
      const visibleHumanMessage = chat.conversations.value.at(-1)?.messages?.[0]
      expect(visibleHumanMessage?.content).toBe(USER_MESSAGE)
      expect(visibleHumanMessage?.content).not.toContain('<context>')
      expect(visibleHumanMessage?.content).not.toContain(HIDDEN_CONTEXT)
    })
  })

  it('keeps the captured legacy gate when force_legacy_stream changes after import', async () => {
    const chat = await importKanbanChat({ runsApi: true, forceLegacy: true })
    localStorage.removeItem('force_legacy_stream')

    await chat.sendMessage(USER_MESSAGE, { context: HIDDEN_CONTEXT })

    expect(mocks.agentApi.sendAgentMessage).toHaveBeenCalledWith(
      {
        query: `<context>\n${HIDDEN_CONTEXT}\n</context>\n\n${USER_MESSAGE}`,
        thread_id: THREAD_ID,
        agent_config_id: 'project-management-config'
      },
      { signal: expect.any(AbortSignal) }
    )
    expect(mocks.agentApi.createAgentRun).not.toHaveBeenCalled()
    expect(mocks.startRunStream).not.toHaveBeenCalled()
  })

  it('clears processing and optimistic state when Run creation returns no run_id', async () => {
    mocks.agentApi.createAgentRun.mockResolvedValue({})
    const chat = await importKanbanChat({ runsApi: true })

    await chat.sendMessage(USER_MESSAGE, { context: HIDDEN_CONTEXT })

    expect(chat.isProcessing.value).toBe(false)
    expect(chat.getThreadState(THREAD_ID).onGoingConv.msgChunks).toEqual({})
    expect(mocks.message.error).toHaveBeenCalledWith('消息发送失败')
    expect(mocks.startRunStream).not.toHaveBeenCalled()
  })

  it('cancels the active Run exactly once on explicit stop', async () => {
    const chat = await importKanbanChat({ runsApi: true })

    await chat.sendMessage(USER_MESSAGE, { context: HIDDEN_CONTEXT })
    chat.getThreadState(THREAD_ID).activeRunId = RUN_ID

    await chat.stopGeneration()

    expect(mocks.agentApi.cancelAgentRun).toHaveBeenCalledTimes(1)
    expect(mocks.agentApi.cancelAgentRun).toHaveBeenCalledWith(RUN_ID)
  })

  it('resumes an active Run during initialization and does not cancel without explicit stop', async () => {
    const chat = await importKanbanChat({ runsApi: true })

    await chat.sendMessage(USER_MESSAGE, { context: HIDDEN_CONTEXT })
    await chat.initialize()

    expect(mocks.resumeActiveRunForThread).toHaveBeenCalledWith(THREAD_ID)
    expect(mocks.agentApi.cancelAgentRun).not.toHaveBeenCalled()
  })

  it('uses the project-management config id in the Run payload', async () => {
    const chat = await importKanbanChat({ runsApi: true })

    await chat.sendMessage(USER_MESSAGE, { context: HIDDEN_CONTEXT })

    expect(chat.selectedAgentConfigId.value).toBe('project-management-config')
    expect(mocks.agentApi.createAgentRun).toHaveBeenCalledWith(
      expect.objectContaining({
        agent_config_id: 'project-management-config'
      })
    )
  })
})

<template>
  <div class="kanban-chat-messages">
    <!-- 加载中 -->
    <div v-if="!isInitialized && isInitializing" class="kanban-chat-messages__loading">
      <div class="kanban-chat-messages__loading-spinner"></div>
      <span>正在连接 AI 助手...</span>
    </div>

    <!-- 对话内容 -->
    <div class="kanban-chat-messages__list">
      <div v-for="(conv, convIndex) in conversations" :key="convIndex" class="kanban-chat-messages__conv">
        <template v-for="displayItem in getConversationDisplayItems(conv)" :key="displayItem.key">
          <AgentMessageComponent
            v-if="displayItem.type === 'message'"
            :message="displayItem.message"
            :is-processing="isDisplayMessageProcessing(conv, displayItem)"
            :show-refs="getShowRefs(displayItem.message)"
            :hide-tool-calls="true"
          />
          <ToolCallsGroupComponent
            v-else
            :tool-calls="displayItem.toolCalls"
            :is-active="isToolGroupActive(conv, displayItem, getConversationDisplayItems(conv))"
          />
        </template>
      </div>
    </div>

    <!-- 生成中指示器 -->
    <div v-if="isProcessing && conversations.length > 0" class="kanban-chat-messages__generating">
      <div class="kanban-chat-messages__generating-dots">
        <div></div><div></div><div></div>
      </div>
      <span>AI 正在思考...</span>
    </div>
  </div>
</template>

<script setup>
import { watch } from 'vue'
import AgentMessageComponent from '@/components/AgentMessageComponent.vue'
import ToolCallsGroupComponent from '@/components/ToolCallsGroupComponent.vue'
import { useKanbanChat } from '../composables/useKanbanChat'

const {
  conversations,
  isProcessing,
  scrollToBottom
} = useKanbanChat()

// 监听对话变化自动滚动
watch(
  conversations,
  () => {
    if (isProcessing.value) {
      scrollToBottom()
    }
  },
  { deep: true }
)

// ==================== 消息展示工具函数 ====================

function hasVisibleAssistantBody(msg) {
  if (!msg || msg.type !== 'ai') return true
  let content = typeof msg?.content === 'string' ? msg.content.trim() : ''
  let reasoningContent = msg?.additional_kwargs?.reasoning_content || ''
  if (!reasoningContent && content) {
    const thinkRegex = /\<think\>(.*?)\<\/think\>|\<think\>(.*?)$/s
    const thinkMatch = content.match(thinkRegex)
    if (thinkMatch) {
      reasoningContent = (thinkMatch[1] || thinkMatch[2] || '').trim()
      content = content.replace(thinkMatch[0], '').trim()
    }
  }
  return Boolean(content || reasoningContent || msg.error_type || msg.extra_metadata?.error_type || msg.isStoppedByUser)
}

function getMessageToolCalls(msg) {
  if (!Array.isArray(msg?.tool_calls)) return []
  return msg.tool_calls.filter(
    (tc) => tc && (tc.id || tc.name || tc.function?.name) && (tc.args !== undefined || tc.function?.arguments !== undefined || tc.tool_call_result !== undefined)
  )
}

function getConversationDisplayItems(conv) {
  if (!Array.isArray(conv?.messages) || conv.messages.length === 0) return []
  const items = []
  let pendingToolGroup = null

  const flushToolGroup = () => {
    if (pendingToolGroup && pendingToolGroup.toolCalls.length > 0) {
      items.push(pendingToolGroup)
    }
    pendingToolGroup = null
  }

  conv.messages.forEach((msg, index) => {
    if (msg.type !== 'ai') {
      flushToolGroup()
      items.push({ type: 'message', key: msg.id || `msg-${index}`, message: msg, sourceIndex: index })
      return
    }
    if (hasVisibleAssistantBody(msg)) {
      flushToolGroup()
      items.push({ type: 'message', key: msg.id || `msg-${index}`, message: msg, sourceIndex: index })
    }
    const toolCalls = getMessageToolCalls(msg)
    if (toolCalls.length === 0) return
    if (!pendingToolGroup) {
      pendingToolGroup = { type: 'tool-group', key: `tg-${msg.id || index}`, toolCalls: [] }
    }
    pendingToolGroup.toolCalls.push(...toolCalls)
  })

  flushToolGroup()
  return items
}

function isDisplayMessageProcessing(conv, displayItem) {
  return displayItem?.type === 'message' && isProcessing.value && conv?.status === 'streaming' && displayItem.sourceIndex === conv.messages.length - 1
}

function isToolGroupActive(conv, displayItem, displayItems) {
  return isProcessing.value && conv?.status === 'streaming' && displayItem === displayItems[displayItems.length - 1]
}

function getShowRefs(msg) {
  if (msg.isLast && msg.status === 'finished') {
    return ['copy', 'sources']
  }
  return false
}
</script>

<style scoped>
.kanban-chat-messages {
  /* 纯消息渲染，无独立滚动容器，由父组件统一管理滚动 */
}

.kanban-chat-messages__list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kanban-chat-messages__conv {
  display: flex;
  flex-direction: column;
}

/* 加载状态 */
.kanban-chat-messages__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 32px 0;
  color: var(--gray-500, #6b7280);
  font-size: 13px;
}

.kanban-chat-messages__loading-spinner {
  width: 18px;
  height: 18px;
  border: 2px solid var(--gray-200, #e5e7eb);
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: kcm-spin 0.8s linear infinite;
}

/* 生成中指示器 */
.kanban-chat-messages__generating {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  color: var(--gray-500, #6b7280);
  font-size: 13px;
  animation: kcm-fadeInUp 0.3s ease-out;
}

.kanban-chat-messages__generating-dots {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.kanban-chat-messages__generating-dots div {
  width: 5px;
  height: 5px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border-radius: 50%;
  animation: kcm-dotPulse 1.4s infinite ease-in-out both;
}

.kanban-chat-messages__generating-dots div:nth-child(1) { animation-delay: -0.32s; }
.kanban-chat-messages__generating-dots div:nth-child(2) { animation-delay: -0.16s; }

@keyframes kcm-spin {
  to { transform: rotate(360deg); }
}

@keyframes kcm-dotPulse {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

@keyframes kcm-fadeInUp {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>

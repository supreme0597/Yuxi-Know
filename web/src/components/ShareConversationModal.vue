<template>
  <a-modal
    :open="open"
    title="分享对话"
    :footer="null"
    :width="520"
    :mask-closable="true"
    @cancel="emit('close')"
    destroyOnClose
  >
    <div v-if="loading" class="share-modal-state">
      <a-spin />
    </div>

    <div v-else class="share-modal-body">
      <!-- 无分享：选择有效期并创建 -->
      <template v-if="!shareInfo">
        <div class="share-modal-tip">
          生成分享链接后，任何持有链接的人都可以只读查看该对话（包含消息、工具调用、状态与交付件）。
        </div>
        <div class="share-modal-form">
          <div class="share-modal-label">有效期</div>
          <a-radio-group v-model:value="expiresDays" class="share-expiry-options">
            <a-radio-button :value="7">7 天</a-radio-button>
            <a-radio-button :value="30">30 天</a-radio-button>
            <a-radio-button :value="90">90 天</a-radio-button>
          </a-radio-group>
        </div>
        <div class="share-modal-actions">
          <a-button type="primary" :loading="creating" @click="handleCreate">生成分享链接</a-button>
        </div>
      </template>

      <!-- 已有分享：展示链接 + 复制 + 撤销 -->
      <template v-else>
        <div class="share-modal-tip share-modal-tip-success">
          当前对话已开启分享，有效期至 {{ formatExpiry(shareInfo.expires_at) }}。
        </div>
        <div class="share-link-row">
          <a-input :value="shareUrl" read-only class="share-link-input" />
          <a-button type="primary" class="share-copy-btn" @click="handleCopy">复制链接</a-button>
        </div>
        <div class="share-modal-actions">
          <a-button danger :loading="revoking" @click="handleRevoke">撤销分享</a-button>
        </div>
      </template>
    </div>
  </a-modal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { shareApi } from '@/apis/share_api'

const props = defineProps({
  open: { type: Boolean, default: false },
  threadId: { type: String, default: '' }
})
const emit = defineEmits(['close'])

const loading = ref(false)
const creating = ref(false)
const revoking = ref(false)
const shareInfo = ref(null)
const expiresDays = ref(30)

const shareUrl = computed(() => {
  if (!props.threadId || !shareInfo.value?.token) return ''
  const origin = window.location.origin
  return `${origin}/share/${props.threadId}?token=${shareInfo.value.token}`
})

const formatExpiry = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

const loadShare = async () => {
  if (!props.open || !props.threadId) return
  loading.value = true
  shareInfo.value = null
  try {
    const info = await shareApi.getShare(props.threadId)
    shareInfo.value = info || null
  } catch {
    console.error('查询分享状态失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = async () => {
  if (!props.threadId) return
  creating.value = true
  try {
    const result = await shareApi.createShare(props.threadId, expiresDays.value)
    shareInfo.value = result
    message.success('分享链接已生成')
  } catch (e) {
    message.error(e?.message || '生成分享链接失败')
  } finally {
    creating.value = false
  }
}

const handleCopy = async () => {
  try {
    await navigator.clipboard.writeText(shareUrl.value)
    message.success('链接已复制')
  } catch {
    message.error('复制失败，请手动复制')
  }
}

const handleRevoke = async () => {
  if (!props.threadId) return
  revoking.value = true
  try {
    await shareApi.revokeShare(props.threadId)
    shareInfo.value = null
    message.success('分享已撤销')
  } catch (e) {
    message.error(e?.message || '撤销分享失败')
  } finally {
    revoking.value = false
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) loadShare()
  },
  { immediate: true }
)
</script>

<style scoped lang="less">
.share-modal-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
}

.share-modal-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.share-modal-tip {
  font-size: 13px;
  color: var(--gray-600);
  line-height: 1.6;
}

.share-modal-tip-success {
  color: var(--color-success-500);
}

.share-modal-form {
  display: flex;
  align-items: center;
  gap: 12px;
}

.share-modal-label {
  font-size: 13px;
  color: var(--gray-700);
  flex-shrink: 0;
}

.share-modal-actions {
  display: flex;
  justify-content: flex-end;
}

.share-link-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.share-link-input {
  flex: 1;
  font-size: 12px;
}

.share-copy-btn {
  flex-shrink: 0;
}
</style>

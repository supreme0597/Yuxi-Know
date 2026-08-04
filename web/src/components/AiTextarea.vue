<template>
  <div class="ai-textarea-wrapper" :class="`action-${actionPlacement}`">
    <a-textarea
      :value="modelValue"
      @update:value="$emit('update:modelValue', $event)"
      :placeholder="placeholder"
      :rows="rows"
      :auto-size="autoSize"
      :disabled="disabled"
    />
    <a-tooltip v-if="showAiButton" :title="tip">
      <a-button
        class="ai-btn"
        type="text"
        size="small"
        :loading="loading"
        :disabled="disabled"
        @click="runPolish"
      >
        <template #icon>
          <WandSparkles size="14" />
        </template>
        <span v-if="!loading" class="ai-text">{{ modelValue?.trim() ? '润色' : '生成' }}</span>
      </a-button>
    </a-tooltip>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { message } from 'ant-design-vue'
import { databaseApi } from '@/apis/knowledge_api'
import { WandSparkles } from 'lucide-vue-next'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  name: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: ''
  },
  rows: {
    type: Number,
    default: 4
  },
  autoSize: {
    type: [Boolean, Object],
    default: false
  },
  files: {
    type: Array,
    default: () => []
  },
  actionPlacement: {
    type: String,
    default: 'inside'
  },
  /**
   * 可选的通用润色函数 (text) => Promise<string>。
   * 传入时走通用润色路径（如提问"其他"项），否则走默认的知识库描述生成逻辑。
   */
  polish: {
    type: Function,
    default: null
  },
  tip: {
    type: String,
    default: '使用 AI 生成或优化描述'
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const loading = ref(false)

// 是否展示 AI 按钮：通用润色模式始终展示；默认知识库描述模式需提供 name
const showAiButton = computed(() => Boolean(props.polish) || Boolean(props.name?.trim()))

const runPolish = async () => {
  const current = props.modelValue ?? ''
  loading.value = true
  try {
    let polished
    if (props.polish) {
      if (!current.trim()) {
        message.warning('请输入需要润色的内容')
        return
      }
      polished = await props.polish(current)
    } else {
      if (!props.name?.trim()) {
        message.warning('请先输入知识库名称')
        return
      }
      const result = await databaseApi.generateDescription(props.name, current, props.files)
      if (result.status === 'success' && result.description) {
        polished = result.description
      } else {
        message.error(result.message || '生成失败')
        return
      }
    }

    if (polished != null && polished !== '') {
      emit('update:modelValue', polished)
      message.success(current.trim() ? '润色成功' : '生成成功')
    }
  } catch (error) {
    console.error('生成/润色失败:', error)
    message.error(error.message || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style lang="less" scoped>
.ai-textarea-wrapper {
  position: relative;

  .ai-btn {
    position: absolute;
    opacity: 0.9;
    top: 4px;
    right: 4px;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    min-width: 54px;
    padding: 2px 6px;
    height: 24px;
    color: var(--main-color);
    background: var(--gray-50);
    border: 1px solid var(--gray-200);
    border-radius: 4px;
    font-size: 12px;
    transition: all 0.2s ease;

    &:hover {
      background: var(--main-10);
      border-color: var(--main-color);
    }

    .ai-text {
      font-weight: 500;
    }

    :deep(.ant-btn-loading-icon) {
      display: inline-flex;
      margin-inline-end: 0;
    }
  }

  &.action-header {
    .ai-btn {
      top: -31px;
      right: 0;
      height: 26px;
      min-width: 58px;
      padding: 0 9px;
      border-radius: 6px;
      background: var(--gray-0);
      border-color: var(--gray-150);
      color: var(--main-700);
      box-shadow: 0 1px 2px var(--shadow-1);

      &:hover {
        background: var(--gray-50);
        border-color: var(--gray-200);
        color: var(--gray-900);
      }
    }
  }
}
</style>

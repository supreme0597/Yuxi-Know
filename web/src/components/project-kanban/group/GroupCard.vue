<template>
  <div class="pk-group" :style="{ '--group-color': meta.colorHex }">
    <!-- 顶部彩色条纹 -->
    <div class="pk-group__stripe" :style="{ background: meta.colorHex }" />

    <div class="pk-group__content">
      <!-- 头部：图标 + 标题 + 状态徽章 -->
      <div class="pk-group__header">
        <div class="pk-group__icon" :style="{ background: meta.colorHex + '18', color: meta.colorHex }">
          <Building2 :size="16" :stroke-width="2" />
        </div>
        <span class="pk-group__title">{{ meta.name }}</span>
        <StatusBadge :status="meta.status" :text="statusText" class="pk-group__status" />
      </div>

      <!-- AI 一句话总结 -->
      <div v-if="meta.aiSummary" class="pk-group__ai" @click.stop="$emit('ai-click', groupKey)">
        <span class="pk-group__ai-spark">✨</span>
        <Tooltip :title="meta.aiSummary" placement="topLeft" :mouseEnterDelay="0.3">
          <span class="pk-group__ai-text">{{ meta.aiSummary }}</span>
        </Tooltip>
      </div>

      <!-- 子项目网格 -->
      <div class="pk-group__projects">
        <SubProjectCard
          v-for="sub in subProjects"
          :key="sub.id"
          :project="sub"
          @click="$emit('sub-click', sub)"
          @ai-click="$emit('sub-ai-click', $event)"
          @dim-click="$emit('dim-click', $event)"
          @progress-click="$emit('progress-click', $event)"
          @milestone-click="$emit('milestone-click', $event)"
        />
      </div>
    </div>

    <!-- Footer: AI 按钮 -->
    <div class="pk-group__footer">
      <AIButton :title="meta.name" @click="$emit('ai-click', groupKey)" />
    </div>
  </div>
</template>

<script setup>
import { computed, h } from 'vue'
import { Tooltip } from 'ant-design-vue'
import AIButton from '../common/AIButton.vue'
import StatusBadge from '../common/StatusBadge.vue'
import SubProjectCard from './SubProjectCard.vue'
import { groupMeta, getSubProjects } from '../data/groupData'

const props = defineProps({
  groupKey: { type: String, required: true }
})

defineEmits(['ai-click', 'sub-click', 'sub-ai-click', 'dim-click', 'progress-click', 'milestone-click'])

// 用 render function 创建图标组件
const Building2 = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M6 22V4a2 2 0 012-2h8a2 2 0 012 2v18Z' }),
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M6 12H4a2 2 0 00-2 2v6a2 2 0 002 2h2' }),
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M18 9h2a2 2 0 012 2v9a2 2 0 01-2 2h-2' }),
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M10 6h4M10 10h4M10 14h4M10 18h4' })
    ])
  }
}

const meta = computed(() => groupMeta[props.groupKey] || {})

const subProjects = computed(() => getSubProjects(props.groupKey))

const statusText = computed(() => {
  const s = meta.value.status
  if (s === 'normal') return '正常'
  if (s === 'warning') return '关注'
  if (s === 'critical') return '异常'
  return s
})
</script>

<style scoped>
.pk-group {
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.pk-group:hover {
  border-color: var(--group-color, var(--gray-300));
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.pk-group__content {
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Stripe */
.pk-group__stripe {
  height: 3px;
  flex-shrink: 0;
}

/* Header */
.pk-group__header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pk-group__icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.pk-group__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--gray-800);
}
.pk-group__status {
  margin-left: auto;
}

/* AI summary */
.pk-group__ai {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 12px;
  background: linear-gradient(135deg, #faf5ff, #eff6ff);
  border-radius: 8px;
  border: 1px solid rgba(99, 102, 241, 0.1);
  font-size: 12px;
  color: var(--gray-700);
  line-height: 1.6;
  cursor: pointer;
  transition: background 0.2s ease, box-shadow 0.2s ease;
}
.pk-group__ai:hover {
  background: linear-gradient(135deg, #f3e8ff, #dbeafe);
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.2);
}
.pk-group__ai-spark {
  flex-shrink: 0;
  font-size: 12px;
}
.pk-group__ai-text {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Sub-project grid - 纵向排布 */
.pk-group__projects {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Footer */
.pk-group__footer {
  display: flex;
  justify-content: flex-end;
  padding: 8px 16px 14px;
  border-top: 1px solid var(--gray-100);
}

</style>

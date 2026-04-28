<template>
  <div class="pk-group" :style="{ '--group-color': meta.colorHex }">

    <div class="pk-group__content">
      <!-- 头部：图标 + 标题 + 状态徽章 -->
      <div class="pk-group__header">
        <div class="pk-group__icon" :style="{ color: meta.colorHex }">
          <Building2 :size="16" :stroke-width="2" />
        </div>
        <span class="pk-group__title">{{ meta.name }}</span>
        <StatusBadge :status="meta.status" :text="statusText" class="pk-group__status" />
      </div>

      <!-- AI 一句话总结 -->
      <div v-if="meta.aiSummary" class="pk-group__ai" :title="meta.aiSummary" @click.stop="$emit('ai-click', groupKey)">
        <span class="pk-group__ai-spark">✨</span>
        <span class="pk-group__ai-text">{{ meta.aiSummary }}</span>
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
          @id-click="$emit('id-click', $event)"
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
import AIButton from '../common/AIButton.vue'
import StatusBadge from '../common/StatusBadge.vue'
import SubProjectCard from './SubProjectCard.vue'
import { projectData } from '../data/projectData'
import { groupData } from '../data/groupData'

/** 获取某个项目群的子项目详情 */
function getSubProjects(groupKey) {
  const meta = groupData[groupKey]
  if (!meta?.offerings) return []
  return meta.offerings
    .map(id => projectData[id] ? { id, ...projectData[id] } : null)
    .filter(Boolean)
}

const props = defineProps({
  groupKey: { type: String, required: true }
})

defineEmits(['ai-click', 'sub-click', 'sub-ai-click', 'dim-click', 'progress-click', 'milestone-click', 'id-click'])

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

const meta = computed(() => groupData[props.groupKey] || {})

const subProjects = computed(() => getSubProjects(props.groupKey))

const statusText = computed(() => {
  const s = meta.value.status
  if (s === 'normal') return '正常'
  if (s === 'warning') return '关注'
  if (s === 'critical') return '紧急'
  return s
})
</script>

<style scoped>
.pk-group {
  background: var(--gray-0);
  border-radius: 12px;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.10), 0 8px 28px rgba(0, 0, 0, 0.07);
  transition: box-shadow 0.2s ease;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.pk-group:hover {
  box-shadow: 0 5px 16px rgba(0, 0, 0, 0.12), 0 14px 36px rgba(0, 0, 0, 0.09);
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
  font-size: 16px;
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
  font-size: 13px;
  color: var(--gray-700);
  line-height: 1.6;
  cursor: pointer;
  overflow: hidden;
  box-sizing: content-box;
  height: calc(2 * 1.6em);
}
.pk-group__ai-spark {
  flex-shrink: 0;
  font-size: 12px;
}
.pk-group__ai-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.6;
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

@media (max-width: 1024px) {
  .pk-group__content {
    padding: 14px;
    gap: 8px;
  }
  .pk-group__icon {
    width: 28px;
    height: 28px;
  }
  .pk-group__title {
    font-size: 15px;
  }
  .pk-group__ai {
    padding: 7px 10px;
    font-size: 12px;
  }
  .pk-group__projects {
    gap: 8px;
  }
  .pk-group__footer {
    padding: 6px 14px 12px;
  }
}

@media (max-width: 768px) {
  .pk-group__content {
    padding: 12px;
    gap: 6px;
  }
  .pk-group__icon {
    width: 24px;
    height: 24px;
  }
  .pk-group__title {
    font-size: 14px;
  }
  .pk-group__ai {
    padding: 6px 8px;
    font-size: 11px;
  }
  .pk-group__projects {
    gap: 6px;
  }
  .pk-group__footer {
    padding: 4px 12px 10px;
  }
}

@media (min-width: 1600px) {
  .pk-group__content {
    padding: 18px;
    gap: 12px;
  }
  .pk-group__stripe {
    height: 4px;
  }
  .pk-group__icon {
    width: 36px;
    height: 36px;
  }
  .pk-group__title {
    font-size: 17px;
  }
  .pk-group__ai {
    padding: 10px 14px;
    font-size: 14px;
  }
  .pk-group__projects {
    gap: 12px;
  }
  .pk-group__footer {
    padding: 10px 18px 16px;
  }
}

@media (min-width: 1920px) {
  .pk-group__content {
    padding: 20px;
    gap: 14px;
  }
  .pk-group__stripe {
    height: 4px;
  }
  .pk-group__icon {
    width: 38px;
    height: 38px;
  }
  .pk-group__title {
    font-size: 18px;
  }
  .pk-group__ai {
    padding: 10px 14px;
    font-size: 15px;
  }
  .pk-group__projects {
    gap: 14px;
  }
  .pk-group__footer {
    padding: 10px 20px 16px;
  }
}

@media (min-width: 2560px) {
  .pk-group__content {
    padding: 22px;
    gap: 16px;
  }
  .pk-group__stripe {
    height: 5px;
  }
  .pk-group__icon {
    width: 40px;
    height: 40px;
  }
  .pk-group__title {
    font-size: 19px;
  }
  .pk-group__ai {
    padding: 12px 16px;
    font-size: 16px;
  }
  .pk-group__projects {
    gap: 16px;
  }
  .pk-group__footer {
    padding: 12px 22px 18px;
  }
}
</style>

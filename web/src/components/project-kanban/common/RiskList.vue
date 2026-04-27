<template>
  <div class="pk-risk-list">
    <div class="pk-risk-list__title">
      <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      TOP3风险
    </div>
    <div class="pk-risk-list__items">
      <template v-if="topRisks.length">
        <div
          v-for="(risk, index) in topRisks"
          :key="index"
          class="pk-risk-item"
          :class="`pk-risk-item--${risk.level}`"
          @click="$emit('risk-click', risk, index)"
        >
          <span class="pk-risk-item__dot"></span>
          <span class="pk-risk-item__text">{{ risk.text || risk.title }}</span>
          <svg class="pk-risk-item__arrow" width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </template>
      <div v-else class="pk-risk-item pk-risk-item--normal pk-risk-item--empty">
        <span class="pk-risk-item__dot"></span>
        <span class="pk-risk-item__text">暂无风险</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  risks: { type: Array, default: () => [] },
  max: { type: Number, default: 3 }
})

defineEmits(['risk-click'])

const topRisks = computed(() => {
  const levelOrder = { critical: 0, danger: 0, warning: 1, normal: 2 }
  return [...(props.risks || [])]
    .sort((a, b) => (levelOrder[a.level] ?? 3) - (levelOrder[b.level] ?? 3))
    .slice(0, props.max)
})
</script>

<style scoped>
.pk-risk-list {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--gray-200);
}
.pk-risk-list__title {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-600);
  margin-bottom: 6px;
}
.pk-risk-list__items {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.pk-risk-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.4;
  cursor: pointer;
  transition: all 0.15s;
}
.pk-risk-item:hover:not(.pk-risk-item--empty) {
  filter: brightness(0.97);
  transform: translateX(2px);
}
.pk-risk-item--empty {
  cursor: default;
}
.pk-risk-item__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pk-risk-item__text {
  color: var(--gray-700);
  flex: 1;
}
.pk-risk-item__arrow {
  flex-shrink: 0;
  color: var(--gray-400);
  margin-left: auto;
}

.pk-risk-item--critical .pk-risk-item__dot,
.pk-risk-item--danger .pk-risk-item__dot {
  background: var(--pk-danger-dark);
}
.pk-risk-item--warning .pk-risk-item__dot {
  background: var(--pk-warning-dark);
}
.pk-risk-item--normal .pk-risk-item__dot {
  background: var(--pk-success-dark);
}

@media (min-width: 1600px) {
  .pk-risk-list__title {
    font-size: 13px;
  }
  .pk-risk-item {
    font-size: 13px;
    padding: 5px 10px;
  }
}

@media (min-width: 1920px) {
  .pk-risk-list__title {
    font-size: 14px;
  }
  .pk-risk-item {
    font-size: 14px;
    padding: 6px 10px;
  }
}

@media (min-width: 2560px) {
  .pk-risk-list__title {
    font-size: 15px;
  }
  .pk-risk-item {
    font-size: 15px;
    padding: 6px 12px;
  }
}
</style>

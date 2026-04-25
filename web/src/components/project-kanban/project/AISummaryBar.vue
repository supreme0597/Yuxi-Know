<template>
  <div class="pk-ai-bar">
    <!-- 左栏：AI 总结 -->
    <div class="pk-ai-bar__col pk-ai-bar__col--summary">
      <div class="pk-ai-bar__col-head">
        <span class="pk-ai-bar__col-icon">💡</span>
        <span class="pk-ai-bar__col-title">AI 智能评估</span>
      </div>
      <p class="pk-ai-bar__summary" @click="$emit('summary-click')">{{ summary }}</p>
    </div>

    <!-- 中栏：TOP3 风险 -->
    <div v-if="topRisks.length" class="pk-ai-bar__col pk-ai-bar__col--risks">
      <div class="pk-ai-bar__col-head">
        <span class="pk-ai-bar__col-icon">⚡</span>
        <span class="pk-ai-bar__col-title">TOP3风险</span>
      </div>
      <div class="pk-ai-bar__risk-list">
        <div
          v-for="(risk, i) in topRisks"
          :key="i"
          class="pk-ai-bar__risk-item"
          :class="`pk-ai-bar__risk-item--${risk.level}`"
          @click="$emit('risk-click', risk)"
        >
          <span class="pk-ai-bar__risk-dot"></span>
          <div class="pk-ai-bar__risk-body">
            <span class="pk-ai-bar__risk-text">{{ risk.text || risk.title }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 右栏：猜你想问 -->
    <div v-if="questions && questions.length" class="pk-ai-bar__col pk-ai-bar__col--questions">
      <div class="pk-ai-bar__col-head">
        <span class="pk-ai-bar__col-icon">🤔</span>
        <span class="pk-ai-bar__col-title">猜你想问</span>
      </div>
      <div class="pk-ai-bar__question-list">
        <button
          v-for="(q, i) in questions.slice(0, 3)"
          :key="i"
          class="pk-ai-bar__question"
          @click="$emit('question-click', q)"
        >
          {{ q }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  summary: { type: String, default: '' },
  risks: { type: Array, default: () => [] },
  questions: { type: Array, default: () => [] }
})

defineEmits(['question-click', 'risk-click', 'summary-click'])

const topRisks = computed(() => {
  const levelOrder = { critical: 0, danger: 0, warning: 1, normal: 2 }
  return [...(props.risks || [])]
    .sort((a, b) => (levelOrder[a.level] ?? 3) - (levelOrder[b.level] ?? 3))
    .slice(0, 3)
})
</script>

<style scoped>
.pk-ai-bar {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  background: var(--gray-0);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 4px 12px rgba(0, 0, 0, 0.04);
}

/* Column base */
.pk-ai-bar__col {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.pk-ai-bar__col + .pk-ai-bar__col {
  border-left: 1px solid var(--gray-150);
}

.pk-ai-bar__col-head {
  display: flex;
  align-items: center;
  gap: 6px;
}
.pk-ai-bar__col-icon {
  font-size: 13px;
  flex-shrink: 0;
}
.pk-ai-bar__col-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-700);
}

/* Left: Summary */
.pk-ai-bar__summary {
  font-size: 13px;
  color: var(--gray-600);
  line-height: 1.7;
  margin: 0;
  cursor: pointer;
  transition: color 0.15s ease;
}
.pk-ai-bar__summary:hover {
  color: var(--gray-800);
}

/* Middle: Risks */
.pk-ai-bar__risk-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.pk-ai-bar__risk-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  cursor: pointer;
  transition: background 0.15s ease;
  min-height: 30px;
  box-sizing: border-box;
}
.pk-ai-bar__risk-item:hover {
  background: var(--gray-50);
}
.pk-ai-bar__risk-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--gray-300);
}
.pk-ai-bar__risk-item--critical .pk-ai-bar__risk-dot,
.pk-ai-bar__risk-item--danger .pk-ai-bar__risk-dot {
  background: var(--pk-danger-dark);
}
.pk-ai-bar__risk-item--warning .pk-ai-bar__risk-dot {
  background: var(--pk-warning-dark);
}
.pk-ai-bar__risk-item--normal .pk-ai-bar__risk-dot {
  background: var(--pk-success-dark);
}
.pk-ai-bar__risk-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.pk-ai-bar__risk-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--gray-800);
  line-height: 1.4;
}

/* Right: Questions */
.pk-ai-bar__question-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.pk-ai-bar__question {
  width: 100%;
  text-align: left;
  font-size: 12px;
  padding: 6px 10px;
  color: var(--gray-700);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  line-height: 1.4;
  min-height: 30px;
  box-sizing: border-box;
  border: none;
  background: transparent;
}
.pk-ai-bar__question:hover {
  color: var(--pk-accent-dark);
  background: var(--pk-accent-light);
}

/* Responsive */
@media (max-width: 1024px) {
  .pk-ai-bar {
    grid-template-columns: 1fr;
  }
  .pk-ai-bar__col + .pk-ai-bar__col {
    border-left: none;
    border-top: 1px solid var(--gray-150);
  }
}

@media (min-width: 1600px) {
  .pk-ai-bar__col {
    padding: 18px 22px;
    gap: 12px;
  }
  .pk-ai-bar__col-icon {
    font-size: 14px;
  }
  .pk-ai-bar__col-title {
    font-size: 14px;
  }
  .pk-ai-bar__summary {
    font-size: 14px;
  }
  .pk-ai-bar__risk-list {
    gap: 6px;
  }
  .pk-ai-bar__risk-item {
    padding: 7px 12px;
    min-height: 34px;
  }
  .pk-ai-bar__risk-dot {
    width: 5px;
    height: 5px;
  }
  .pk-ai-bar__risk-text {
    font-size: 13px;
  }
  .pk-ai-bar__question-list {
    gap: 6px;
  }
  .pk-ai-bar__question {
    font-size: 13px;
    padding: 7px 12px;
    min-height: 34px;
  }
}

@media (min-width: 1920px) {
  .pk-ai-bar__col {
    padding: 20px 24px;
    gap: 14px;
  }
  .pk-ai-bar__col-icon {
    font-size: 15px;
  }
  .pk-ai-bar__col-title {
    font-size: 15px;
  }
  .pk-ai-bar__summary {
    font-size: 15px;
  }
  .pk-ai-bar__risk-list {
    gap: 7px;
  }
  .pk-ai-bar__risk-item {
    padding: 8px 12px;
    min-height: 36px;
  }
  .pk-ai-bar__risk-dot {
    width: 5px;
    height: 5px;
  }
  .pk-ai-bar__risk-text {
    font-size: 14px;
  }
  .pk-ai-bar__question-list {
    gap: 7px;
  }
  .pk-ai-bar__question {
    font-size: 14px;
    padding: 8px 12px;
    min-height: 36px;
  }
}

@media (min-width: 2560px) {
  .pk-ai-bar__col {
    padding: 22px 28px;
    gap: 16px;
  }
  .pk-ai-bar__col-icon {
    font-size: 16px;
  }
  .pk-ai-bar__col-title {
    font-size: 16px;
  }
  .pk-ai-bar__summary {
    font-size: 16px;
  }
  .pk-ai-bar__risk-list {
    gap: 8px;
  }
  .pk-ai-bar__risk-item {
    padding: 8px 14px;
    min-height: 40px;
  }
  .pk-ai-bar__risk-dot {
    width: 5px;
    height: 5px;
  }
  .pk-ai-bar__risk-text {
    font-size: 15px;
  }
  .pk-ai-bar__question-list {
    gap: 8px;
  }
  .pk-ai-bar__question {
    font-size: 15px;
    padding: 8px 14px;
    min-height: 40px;
  }
}
</style>

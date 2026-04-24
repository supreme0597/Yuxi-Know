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
          <span class="pk-ai-bar__risk-rank">{{ i + 1 }}</span>
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
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  overflow: hidden;
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
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s ease;
  min-height: 30px;
  box-sizing: border-box;
}
.pk-ai-bar__risk-item:hover {
  background: var(--gray-50);
}
.pk-ai-bar__risk-item--critical,
.pk-ai-bar__risk-item--danger {
  background: var(--pk-danger-light);
}
.pk-ai-bar__risk-item--critical:hover,
.pk-ai-bar__risk-item--danger:hover {
  background: var(--pk-danger-lighter);
}
.pk-ai-bar__risk-item--warning {
  background: var(--pk-warning-light);
}
.pk-ai-bar__risk-item--warning:hover {
  background: var(--pk-warning-lighter);
}
.pk-ai-bar__risk-item--normal {
  background: var(--pk-success-light);
}
.pk-ai-bar__risk-item--normal:hover {
  background: var(--pk-success-lighter);
}
.pk-ai-bar__risk-rank {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  background: var(--gray-300);
  color: var(--pk-card-bg);
}
.pk-ai-bar__risk-item--critical .pk-ai-bar__risk-rank,
.pk-ai-bar__risk-item--danger .pk-ai-bar__risk-rank {
  background: var(--pk-danger-dark);
}
.pk-ai-bar__risk-item--warning .pk-ai-bar__risk-rank {
  background: var(--pk-warning-dark);
}
.pk-ai-bar__risk-item--normal .pk-ai-bar__risk-rank {
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
  background: var(--gray-50);
  color: var(--gray-700);
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  line-height: 1.4;
  min-height: 30px;
  box-sizing: border-box;
}
.pk-ai-bar__question:hover {
  background: var(--pk-accent-light);
  border-color: var(--pk-accent);
  color: var(--pk-accent-dark);
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
  .pk-ai-bar__risk-rank {
    width: 20px;
    height: 20px;
    font-size: 12px;
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
  .pk-ai-bar__risk-rank {
    width: 22px;
    height: 22px;
    font-size: 13px;
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
  .pk-ai-bar__risk-rank {
    width: 24px;
    height: 24px;
    font-size: 14px;
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

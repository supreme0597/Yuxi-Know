<template>
  <DataCard
    title="费用执行率"
    :icon="DollarIcon"
    icon-color="var(--pk-warning)"
    :status-text="statusText"
    :status-color="statusColor"
    :ai-summary="data?.aiSummary"
    @ai-click="$emit('ai-click', 'budget-dept')"
    @summary-click="$emit('summary-click', 'budget-dept')"
  >
    <template #stats>
      <StatGrid :items="summaryItems" @item-click="$emit('metric-click', 'budget-dept', $event)" />
    </template>

    <!-- 2x2 正方形项目子卡片 -->
    <div v-if="data?.projects?.length" class="pk-budget-grid">
      <div
        v-for="proj in data.projects"
        :key="proj.name"
        class="pk-budget-sub"
        @click="$emit('project-click', proj)"
      >
        <!-- 项目名 + 状态标签 -->
        <div class="pk-budget-sub__header">
          <span class="pk-budget-sub__name">{{ proj.category }}</span>
          <span class="pk-budget-sub__status" :class="statusClass(proj)">
            <span class="pk-budget-sub__status-dot"></span>
            <span class="pk-budget-sub__status-text">{{ proj.status }}</span>
          </span>
        </div>

        <!-- 中部：圆环图 -->
        <div class="pk-budget-sub__body">
          <div class="pk-budget-sub__ring">
            <DonutChart :percentage="proj.rate" :size="38" :stroke-width="3.5" />
          </div>
        </div>

        <!-- 底部：偏差值/总预算/已执行 统计区（参考 StatGrid 样式） -->
        <div class="pk-budget-sub__footer-stats">
          <div class="pk-budget-sub__stat-item">
            <span class="pk-budget-sub__stat-value" :class="deviationValueClass(proj.deviation)">
              {{ proj.deviation > 0 ? '+' : '' }}{{ proj.deviation }}%
            </span>
            <span class="pk-budget-sub__stat-label">偏差</span>
          </div>
          <div class="pk-budget-sub__stat-divider" />
          <div class="pk-budget-sub__stat-item">
            <span class="pk-budget-sub__stat-value">¥{{ proj.budget }}W</span>
            <span class="pk-budget-sub__stat-label">总预算</span>
          </div>
          <div class="pk-budget-sub__stat-divider" />
          <div class="pk-budget-sub__stat-item">
            <span class="pk-budget-sub__stat-value">¥{{ proj.executed }}W</span>
            <span class="pk-budget-sub__stat-label">已执行</span>
          </div>
        </div>
      </div>
    </div>
  </DataCard>
</template>

<script setup>
import { computed, h } from 'vue'
import DataCard from '../common/DataCard.vue'
import StatGrid from '../common/StatGrid.vue'
import DonutChart from '../common/DonutChart.vue'

const props = defineProps({
  data: { type: Object, default: null }
})

defineEmits(['ai-click', 'summary-click', 'project-click', 'metric-click'])

const DollarIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z' })
    ])
  }
}

const statusText = computed(() => props.data?.status || '正常')
const statusColor = computed(() => {
  const m = { green: 'success', yellow: 'warning', red: 'danger' }
  return m[props.data?.statusType] || 'success'
})

const summaryItems = computed(() => {
  const projs = props.data?.projects || []
  const totalBudget = Math.round(projs.reduce((s, p) => s + (p.budget || 0), 0) * 100) / 100
  const totalExecuted = Math.round(projs.reduce((s, p) => s + (p.executed || 0), 0) * 100) / 100
  const warningCount = projs.filter(p => Math.abs(p.deviation || 0) > 10).length
  return [
    { value: projs.length || '-', label: '项目数' },
    { value: totalBudget ? `¥${totalBudget}W` : '-', label: '总预算(W)' },
    { value: totalExecuted ? `¥${totalExecuted}W` : '-', label: '已执行(W)' },
    { value: warningCount || '-', label: '预警项目', statusClass: warningCount > 0 ? 'warning' : '', clickable: true }
  ]
})

function statusClass(proj) {
  return proj.status === '维护态' ? 'pk-budget-sub__status--maintenance' : 'pk-budget-sub__status--active'
}

/** 偏差 → 指针位置百分比 (0%=最左, 100%=最右, 50%=零点) */
function deviationLeft(deviation) {
  // deviation 范围约 -30 ~ +30, 映射到 0~100%
  const pct = 50 + (deviation / 30) * 50
  return Math.max(5, Math.min(95, pct)) + '%'
}

function deviationPtrClass(deviation) {
  if (Math.abs(deviation) > 20) return 'pk-budget-sub__deviation-ptr--danger'
  if (Math.abs(deviation) > 10) return 'pk-budget-sub__deviation-ptr--warning'
  return 'pk-budget-sub__deviation-ptr--good'
}

function deviationValueClass(deviation) {
  if (Math.abs(deviation) > 20) return 'danger'
  if (Math.abs(deviation) > 10) return 'warning'
  return ''
}
</script>

<style scoped>
/* 2x2 子卡片网格：内容自然撑开，底部留白 */
.pk-budget-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-top: 4px;
  min-width: 0;
}

/* 单个子卡片 — 正方形 */
.pk-budget-sub {
  background: var(--pk-card-bg);
  border-radius: 10px;
  padding: 8px 8px 10px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
  cursor: pointer;
  transition: box-shadow 0.2s ease;
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08), 0 6px 20px rgba(0, 0, 0, 0.05);
  aspect-ratio: 1 / 0.88;
}

.pk-budget-sub:hover {
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.10), 0 8px 28px rgba(0, 0, 0, 0.07);
}

/* 头部 */
.pk-budget-sub__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 4px;
}

.pk-budget-sub__name {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-700);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pk-budget-sub__status {
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.pk-budget-sub__status-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pk-budget-sub__status-text {
  color: var(--gray-500);
}
.pk-budget-sub__status--active .pk-budget-sub__status-dot { background: var(--pk-success); }
.pk-budget-sub__status--maintenance .pk-budget-sub__status-dot { background: var(--pk-warning); }

/* 中部：圆环图 + 偏差指示条 上下排列 */
.pk-budget-sub__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 0;
}

.pk-budget-sub__ring {
  flex-shrink: 0;
}

/* 底部：统计区（参考 StatGrid 样式） */
.pk-budget-sub__footer-stats {
  display: flex;
  align-items: center;
  gap: 0;
  width: 100%;
}

.pk-budget-sub__stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.pk-budget-sub__stat-value {
  font-size: 13px;
  font-weight: 700;
  color: var(--gray-800);
}
.pk-budget-sub__stat-value.danger { color: var(--pk-danger); }
.pk-budget-sub__stat-value.warning { color: var(--pk-warning); }

.pk-budget-sub__stat-label {
  font-size: 11px;
  color: var(--gray-500);
}

.pk-budget-sub__stat-divider {
  width: 1px;
  height: 20px;
  background: var(--gray-200);
  flex-shrink: 0;
}

/* Responsive */
@media (max-width: 600px) {
  .pk-budget-grid {
    grid-template-columns: 1fr;
  }
  .pk-budget-sub {
    aspect-ratio: auto;
  }
}

@media (min-width: 1600px) {
  .pk-budget-sub__name {
    font-size: 14px;
  }
  .pk-budget-sub__status {
    font-size: 13px;
  }
  .pk-budget-sub__stat-value {
    font-size: 14px;
  }
  .pk-budget-sub__stat-label {
    font-size: 12px;
  }
  .pk-budget-sub__stat-divider {
    height: 22px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 46px !important;
  }
}

@media (min-width: 1920px) {
  .pk-budget-sub__name {
    font-size: 15px;
  }
  .pk-budget-sub__status {
    font-size: 14px;
  }
  .pk-budget-sub__stat-value {
    font-size: 15px;
  }
  .pk-budget-sub__stat-label {
    font-size: 13px;
  }
  .pk-budget-sub__stat-divider {
    height: 24px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 54px !important;
  }
}

@media (min-width: 2560px) {
  .pk-budget-sub__name {
    font-size: 16px;
  }
  .pk-budget-sub__status {
    font-size: 14px;
  }
  .pk-budget-sub__stat-value {
    font-size: 16px;
  }
  .pk-budget-sub__stat-label {
    font-size: 14px;
  }
  .pk-budget-sub__stat-divider {
    height: 26px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 78px !important;
  }
}
</style>

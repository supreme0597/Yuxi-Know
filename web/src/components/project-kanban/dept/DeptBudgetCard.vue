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

        <!-- 中部：圆环图 + 偏差指示条 上下排列 -->
        <div class="pk-budget-sub__body">
          <div class="pk-budget-sub__ring">
            <DonutChart :percentage="proj.rate" :size="44" :stroke-width="4" />
          </div>
          <div class="pk-budget-sub__deviation">
            <div class="pk-budget-sub__deviation-bar">
              <div class="pk-budget-sub__deviation-zero" />
              <div
                class="pk-budget-sub__deviation-ptr"
                :class="deviationPtrClass(proj.deviation)"
                :style="{ left: deviationLeft(proj.deviation) }"
              />
            </div>
            <div class="pk-budget-sub__deviation-scale">
              <span>-20%</span>
              <span class="pk-budget-sub__deviation-label" :class="deviationClass(proj.deviation)">
                偏差 {{ proj.deviation > 0 ? '+' : '' }}{{ proj.deviation }}%
              </span>
              <span>+20%</span>
            </div>
          </div>
        </div>

        <!-- 底部：金额 -->
        <div class="pk-budget-sub__amount">
          <span class="pk-budget-sub__executed">¥{{ proj.executed }}M</span>
          <span class="pk-budget-sub__divider">/</span>
          <span class="pk-budget-sub__total">¥{{ proj.budget }}M</span>
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
    { value: totalBudget ? `¥${totalBudget}M` : '-', label: '总预算(M)' },
    { value: totalExecuted ? `¥${totalExecuted}M` : '-', label: '已执行(M)' },
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

function deviationClass(deviation) {
  if (Math.abs(deviation) > 20) return 'pk-budget-sub__deviation-label--danger'
  if (Math.abs(deviation) > 10) return 'pk-budget-sub__deviation-label--warning'
  return 'pk-budget-sub__deviation-label--good'
}
</script>

<style scoped>
/* 2x2 子卡片网格 */
.pk-budget-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: 1fr 1fr;
  gap: 8px;
  margin-top: 4px;
  min-width: 0;
  flex: 1;
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
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 2px 8px rgba(0, 0, 0, 0.03);
}

.pk-budget-sub:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 0, 0, 0.04);
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

/* 底部：金额 */
.pk-budget-sub__amount {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  font-size: 13px;
}

.pk-budget-sub__executed { font-weight: 700; color: var(--gray-800); }
.pk-budget-sub__divider { color: var(--gray-400); }
.pk-budget-sub__total { color: var(--gray-500); }

/* 偏差指示条 */
.pk-budget-sub__deviation {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 80%;
  margin: 0 auto;
}

.pk-budget-sub__deviation-bar {
  height: 6px;
  border-radius: 3px;
  position: relative;
  background: linear-gradient(90deg,
    var(--pk-danger) 0%, var(--pk-danger) 16.67%,
    var(--pk-warning) 16.67%, var(--pk-warning) 33.33%,
    var(--pk-success) 33.33%, var(--pk-success) 66.67%,
    var(--pk-warning) 66.67%, var(--pk-warning) 83.33%,
    var(--pk-danger) 83.33%, var(--pk-danger) 100%
  );
}

.pk-budget-sub__deviation-zero {
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(255, 255, 255, 0.9);
  transform: translateX(-50%);
  z-index: 2;
}

.pk-budget-sub__deviation-scale {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  color: var(--gray-400);
  padding: 0 2px;
}

.pk-budget-sub__deviation-ptr {
  position: absolute;
  top: -4px;
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 9px solid;
  transform: translateX(-50%);
  z-index: 3;
}

.pk-budget-sub__deviation-ptr--danger { border-top-color: var(--pk-danger); }
.pk-budget-sub__deviation-ptr--warning { border-top-color: var(--pk-warning); }
.pk-budget-sub__deviation-ptr--good { border-top-color: var(--pk-success); }

.pk-budget-sub__deviation-label {
  font-size: 11px;
  font-weight: 500;
}

.pk-budget-sub__deviation-label--danger { color: var(--pk-danger); }
.pk-budget-sub__deviation-label--warning { color: var(--pk-warning); }
.pk-budget-sub__deviation-label--good { color: var(--pk-success); }

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
  .pk-budget-sub__amount {
    font-size: 14px;
  }
  .pk-budget-sub__deviation-scale {
    font-size: 12px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 52px !important;
  }
}

@media (min-width: 1920px) {
  .pk-budget-sub__name {
    font-size: 15px;
  }
  .pk-budget-sub__status {
    font-size: 14px;
  }
  .pk-budget-sub__amount {
    font-size: 15px;
  }
  .pk-budget-sub__deviation-scale {
    font-size: 13px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 62px !important;
  }
}

@media (min-width: 2560px) {
  .pk-budget-sub__name {
    font-size: 16px;
  }
  .pk-budget-sub__status {
    font-size: 14px;
  }
  .pk-budget-sub__amount {
    font-size: 16px;
  }
  .pk-budget-sub__deviation-scale {
    font-size: 14px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 72px !important;
  }
}
</style>

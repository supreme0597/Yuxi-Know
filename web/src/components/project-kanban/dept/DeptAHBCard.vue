<template>
  <DataCard
    title="AHB人力"
    :icon="UsersIcon"
    icon-color="#6b7280"
    :status-text="statusText"
    :status-color="statusColor"
    :ai-summary="data?.aiSummary"
    @ai-click="$emit('ai-click', 'ahb')"
    @summary-click="$emit('summary-click', 'ahb')"
  >
    <template #stats>
      <StatGrid :items="summaryItems" @item-click="$emit('metric-click', 'ahb', $event)" />
    </template>

    <!-- 2x2 子卡片网格 -->
    <div v-if="categories.length" class="pk-ahb-grid">
      <div
        v-for="cat in categories"
        :key="cat.label"
        class="pk-ahb-sub"
        @click="$emit('category-click', cat)"
      >
        <!-- 项目名 -->
        <div class="pk-ahb-sub__header">
          <span class="pk-ahb-sub__label">{{ cat.label }}</span>
        </div>

        <!-- 圆环 + 人力数据 -->
        <div class="pk-ahb-sub__body">
          <div class="pk-ahb-sub__ring">
            <DonutChart :percentage="ringPercent(cat)" :size="64" :stroke-width="5" :color="ringColor(cat)" :label="deviationPercentText(cat)" />
          </div>
          <div class="pk-ahb-sub__amount">
            <span class="pk-ahb-sub__executed">{{ cat.total }}</span>
            <span class="pk-ahb-sub__divider">/</span>
            <span class="pk-ahb-sub__total">{{ cat.workload }}人月</span>
          </div>
        </div>

        <!-- 人员构成条 -->
        <div v-if="compositionTotal(cat) > 0" class="pk-ahb-sub__composition">
          <div class="pk-ahb-sub__bar">
            <div
              class="pk-ahb-sub__bar-seg pk-ahb-sub__bar-seg--internal"
              :style="{ width: compositionPercent(cat, 'internal') + '%' }"
            />
            <div
              class="pk-ahb-sub__bar-seg pk-ahb-sub__bar-seg--od"
              :style="{ width: compositionPercent(cat, 'od') + '%' }"
            />
            <div
              class="pk-ahb-sub__bar-seg pk-ahb-sub__bar-seg--outsource"
              :style="{ width: compositionPercent(cat, 'outsource') + '%' }"
            />
          </div>
          <div class="pk-ahb-sub__legend">
            <span class="pk-ahb-sub__legend-item">
              <span class="pk-ahb-sub__legend-dot pk-ahb-sub__legend-dot--internal" />自有{{ compositionValue(cat, 'internal') }}
            </span>
            <span class="pk-ahb-sub__legend-item">
              <span class="pk-ahb-sub__legend-dot pk-ahb-sub__legend-dot--od" />OD{{ compositionValue(cat, 'od') }}
            </span>
            <span class="pk-ahb-sub__legend-item">
              <span class="pk-ahb-sub__legend-dot pk-ahb-sub__legend-dot--outsource" />外包{{ compositionValue(cat, 'outsource') }}
            </span>
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

defineEmits(['ai-click', 'summary-click', 'category-click', 'metric-click'])

const UsersIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z' })
    ])
  }
}

const statusText = computed(() => props.data?.status || '正常')
const statusColor = computed(() => {
  const m = { green: 'success', yellow: 'warning', red: 'danger' }
  return m[props.data?.statusType] || 'success'
})

const categories = computed(() => {
  const cats = props.data?.categories
  if (!cats) return []
  return Object.values(cats)
})

const summaryItems = computed(() => {
  const cats = categories.value
  const totalWorkload = cats.reduce((s, c) => s + (c.workload || 0), 0)
  const totalCapacity = cats.reduce((s, c) => s + (c.total || 0), 0)
  const totalDeviation = cats.reduce((s, c) => s + (c.deviation || 0), 0)
  const utilization = totalCapacity > 0 ? Math.round(totalWorkload / totalCapacity * 100) : 0
  return [
    { value: totalWorkload || '-', label: '总工作量' },
    { value: totalCapacity || '-', label: '总人力' },
    { value: totalDeviation || '-', label: '总偏差', statusClass: totalDeviation < 0 ? 'warning' : '', clickable: true },
    { value: utilization + '%', label: '利用率' }
  ]
})

/** 圆环颜色：根据偏差判断 */
function ringColor(cat) {
  if (cat.workload > cat.total) {
    // 超负荷
    const overloadPct = ((cat.workload - cat.total) / cat.total) * 100
    if (overloadPct > 20) return '#dc2626'
    return '#d97706'
  }
  return '#059669'
}

/** 圆环进度：工作量/人力利用率，超负荷时100%满 */
function ringPercent(cat) {
  if (!cat.total) return 0
  if (cat.workload > cat.total) return 100
  return Math.min(100, Math.round((cat.workload / cat.total) * 100))
}

/** 偏差百分比文字（带%） */
function deviationPercentText(cat) {
  if (!cat.workload) return '0%'
  const pct = Math.round(((cat.total - cat.workload) / cat.workload) * 100)
  return (pct >= 0 ? '+' : '') + pct + '%'
}

/** 人员构成：各类人员总数 */
function compositionTotal(cat) {
  if (!cat.roles) return 0
  return Object.values(cat.roles).reduce((sum, r) => sum + (r.internal || 0) + (r.od || 0) + (r.outsource || 0), 0)
}

/** 人员构成：某类人员总数 */
function compositionValue(cat, type) {
  if (!cat.roles) return 0
  return Object.values(cat.roles).reduce((sum, r) => sum + (r[type] || 0), 0)
}

/** 人员构成：某类人员占比 */
function compositionPercent(cat, type) {
  const total = compositionTotal(cat)
  if (!total) return 0
  return (compositionValue(cat, type) / total * 100).toFixed(1)
}
</script>

<style scoped>
/* 2x2 子卡片网格 */
.pk-ahb-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: 1fr 1fr;
  gap: 8px;
  margin-top: 4px;
  min-width: 0;
  overflow: hidden;
  flex: 1;
}

/* 单个子卡片 */
.pk-ahb-sub {
  background: #fff;
  border: 1px solid #eef0f4;
  border-radius: 10px;
  padding: 8px 8px 10px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
}

.pk-ahb-sub:hover {
  border-color: #dde1e8;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

/* 头部 */
.pk-ahb-sub__header {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.pk-ahb-sub__label {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-700);
}

/* 中部：圆环 + 人力数据 */
.pk-ahb-sub__body {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex: 1;
  min-height: 0;
}

.pk-ahb-sub__ring {
  flex-shrink: 0;
}

.pk-ahb-sub__amount {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 13px;
}

.pk-ahb-sub__executed { font-weight: 700; color: var(--gray-800); }
.pk-ahb-sub__divider { color: var(--gray-400); }
.pk-ahb-sub__total { color: var(--gray-500); }

/* 人员构成条 */
.pk-ahb-sub__composition {
  width: 100%;
  margin-top: auto;
}

.pk-ahb-sub__bar {
  display: flex;
  height: 10px;
  border-radius: 5px;
  overflow: hidden;
  background: #f3f4f6;
  margin-bottom: 4px;
}

.pk-ahb-sub__bar-seg {
  transition: width 0.3s ease;
  min-width: 2px;
}

.pk-ahb-sub__bar-seg--internal { background: #475569; }
.pk-ahb-sub__bar-seg--od { background: #94a3b8; }
.pk-ahb-sub__bar-seg--outsource { background: #cbd5e1; }

.pk-ahb-sub__legend {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--gray-500);
}

.pk-ahb-sub__legend-item {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.pk-ahb-sub__legend-dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  border-radius: 50%;
}

.pk-ahb-sub__legend-dot--internal { background: #475569; }
.pk-ahb-sub__legend-dot--od { background: #94a3b8; }
.pk-ahb-sub__legend-dot--outsource { background: #cbd5e1; }

/* Responsive */
@media (max-width: 600px) {
  .pk-ahb-grid {
    grid-template-columns: 1fr;
  }
  .pk-ahb-sub {
    aspect-ratio: auto;
  }
}

@media (min-width: 1600px) {
  .pk-ahb-sub__label {
    font-size: 14px;
  }
  .pk-ahb-sub__amount {
    font-size: 14px;
  }
  .pk-ahb-sub__legend {
    font-size: 13px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 76px !important;
  }
}

@media (min-width: 1920px) {
  .pk-ahb-sub__label {
    font-size: 15px;
  }
  .pk-ahb-sub__amount {
    font-size: 15px;
  }
  .pk-ahb-sub__legend {
    font-size: 14px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 88px !important;
  }
}

@media (min-width: 2560px) {
  .pk-ahb-sub__label {
    font-size: 16px;
  }
  .pk-ahb-sub__amount {
    font-size: 16px;
  }
  .pk-ahb-sub__legend {
    font-size: 15px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 100px !important;
  }
}
</style>

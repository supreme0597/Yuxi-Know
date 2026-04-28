<template>
  <DataCard
    title="AHB人力（人月）"
    :icon="UsersIcon"
    icon-color="var(--pk-text-secondary)"
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

        <!-- 中部：圆环图（画图用原百分比，中间文字显示偏差值，悬浮显示分数） -->
        <div class="pk-ahb-sub__body">
          <div class="pk-ahb-sub__ring">
            <DonutChart
              :percentage="ringPercent(cat)"
              :size="38"
              :stroke-width="3.5"
              :color="ringColor(cat)"
              :label="deviationPercentText(cat)"
              :tooltip="scoreText(cat)"
            />
          </div>
        </div>

        <!-- 底部：人员构成统计区（参考 StatGrid 样式） -->
        <div class="pk-ahb-sub__footer-stats">
          <div class="pk-ahb-sub__stat-item">
            <span class="pk-ahb-sub__stat-value">{{ compositionValue(cat, 'internal') }}</span>
            <span class="pk-ahb-sub__stat-label">自有</span>
          </div>
          <div class="pk-ahb-sub__stat-divider" />
          <div class="pk-ahb-sub__stat-item">
            <span class="pk-ahb-sub__stat-value">{{ compositionValue(cat, 'od') }}</span>
            <span class="pk-ahb-sub__stat-label">OD</span>
          </div>
          <div class="pk-ahb-sub__stat-divider" />
          <div class="pk-ahb-sub__stat-item">
            <span class="pk-ahb-sub__stat-value">{{ compositionValue(cat, 'outsource') }}</span>
            <span class="pk-ahb-sub__stat-label">合作方</span>
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

/** 格式化数字：有小数最多保留2位并去掉末尾0，整数就显示整数 */
function fmt(n) {
  if (n === 0) return '0'
  const abs = Math.abs(n)
  if (Number.isInteger(abs)) return String(n)
  const rounded = Math.round(n * 100) / 100
  return rounded % 1 === 0 ? String(rounded) : rounded.toString()
}

const summaryItems = computed(() => {
  const cats = categories.value
  const totalWorkload = cats.reduce((s, c) => s + (c.workload || 0), 0)
  const totalCapacity = cats.reduce((s, c) => s + (c.total || 0), 0)
  const totalDeviation = cats.reduce((s, c) => s + (c.deviation || 0), 0)
  const utilization = totalCapacity > 0 ? Math.round(totalWorkload / totalCapacity * 100) : 0
  return [
    { value: totalWorkload ? fmt(totalWorkload) : '-', label: '总工作量' },
    { value: totalCapacity ? fmt(totalCapacity) : '-', label: '总人力' },
    { value: totalDeviation ? fmt(totalDeviation) : '-', label: '总偏差', statusClass: totalDeviation < 0 ? 'warning' : '', clickable: true },
    { value: utilization + '%', label: '利用率' }
  ]
})

/** 圆环颜色：根据偏差判断 */
function ringColor(cat) {
  if (cat.workload > cat.total) {
    // 超负荷
    const overloadPct = ((cat.workload - cat.total) / cat.total) * 100
    if (overloadPct > 20) return 'var(--pk-danger)'
    return 'var(--pk-warning)'
  }
  return 'var(--pk-success)'
}

/** 圆环进度：工作量/人力利用率，超负荷时100%满 */
function ringPercent(cat) {
  if (!cat.total) return 0
  if (cat.workload > cat.total) return 100
  return Math.min(100, Math.round((cat.workload / cat.total) * 100))
}

/** 环形图中间文字：偏差值（带+/-号） */
function deviationPercentText(cat) {
  if (!cat.workload) return '0%'
  const pct = Math.round(((cat.total - cat.workload) / cat.workload) * 100)
  return (pct >= 0 ? '+' : '') + pct + '%'
}

/** 悬浮气泡显示：分数（如 80/80人月） */
function scoreText(cat) {
  return `${fmt(cat.total) || 0}/${fmt(cat.workload) || 0}人月`
}

/** 人员构成：各类人员总数 */
function compositionTotal(cat) {
  if (!cat.roles) return 0
  return Object.values(cat.roles).reduce((sum, r) => sum + (r.internal || 0) + (r.od || 0) + (r.outsource || 0), 0)
}

/** 人员构成：某类人员总数 */
function compositionValue(cat, type) {
  if (!cat.roles) return 0
  const val = Object.values(cat.roles).reduce((sum, r) => sum + (r[type] || 0), 0)
  return val
}

/** 人员构成：某类人员占比 */
function compositionPercent(cat, type) {
  const total = compositionTotal(cat)
  if (!total) return 0
  return (compositionValue(cat, type) / total * 100).toFixed(1)
}
</script>

<style scoped>
/* 2x2 子卡片网格：内容自然撑开，底部留白 */
.pk-ahb-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-top: 4px;
  min-width: 0;
}

/* 单个子卡片 */
.pk-ahb-sub {
  background: var(--pk-card-bg);
  border-radius: 10px;
  padding: 8px 8px 10px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  cursor: pointer;
  transition: box-shadow 0.2s ease;
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08), 0 6px 20px rgba(0, 0, 0, 0.05);
  aspect-ratio: 1 / 0.88;
}

.pk-ahb-sub:hover {
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.10), 0 8px 28px rgba(0, 0, 0, 0.07);
}

/* 头部 */
.pk-ahb-sub__header {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}

.pk-ahb-sub__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-700);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 中部：圆环图 + 人员构成条 上下排列 */
.pk-ahb-sub__body {
  flex: 1;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 0;
}

.pk-ahb-sub__ring {
  flex-shrink: 0;
}

/* 底部：人员构成统计区（参考 StatGrid 样式） */
.pk-ahb-sub__footer-stats {
  display: flex;
  align-items: center;
  gap: 0;
  width: 100%;
}

.pk-ahb-sub__stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
}

.pk-ahb-sub__stat-value {
  font-size: 13px;
  font-weight: 700;
  color: var(--gray-800);
}

.pk-ahb-sub__stat-label {
  font-size: 11px;
  color: var(--gray-500);
}

.pk-ahb-sub__stat-divider {
  width: 1px;
  height: 20px;
  background: var(--gray-200);
  flex-shrink: 0;
}

/* Responsive */
@media (max-width: 1024px) {
  .pk-ahb-sub__label {
    font-size: 11px;
  }
  .pk-ahb-sub__stat-value {
    font-size: 12px;
  }
  .pk-ahb-sub__stat-label {
    font-size: 10px;
  }
  .pk-ahb-sub__stat-divider {
    height: 18px;
  }
}

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
    font-size: 13px;
  }
  .pk-ahb-sub__stat-value {
    font-size: 14px;
  }
  .pk-ahb-sub__stat-label {
    font-size: 12px;
  }
  .pk-ahb-sub__stat-divider {
    height: 22px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 46px !important;
  }
}

@media (min-width: 1920px) {
  .pk-ahb-sub__label {
    font-size: 14px;
  }
  .pk-ahb-sub__stat-value {
    font-size: 14px;
  }
  .pk-ahb-sub__stat-label {
    font-size: 12px;
  }
  .pk-ahb-sub__stat-divider {
    height: 24px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 54px !important;
  }
}

@media (min-width: 2560px) {
  .pk-ahb-sub__label {
    font-size: 15px;
  }
  .pk-ahb-sub__stat-value {
    font-size: 15px;
  }
  .pk-ahb-sub__stat-label {
    font-size: 13px;
  }
  .pk-ahb-sub__stat-divider {
    height: 26px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 78px !important;
  }
}
</style>

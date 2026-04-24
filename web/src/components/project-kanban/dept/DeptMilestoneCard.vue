<template>
  <DataCard
    title="项目里程碑"
    :icon="FlagIcon"
    icon-color="var(--pk-group-v3)"
    :status-text="statusText"
    :status-color="statusColor"
    :ai-summary="data?.aiSummary"
    @ai-click="$emit('ai-click', 'milestone-dept')"
    @summary-click="$emit('summary-click', 'milestone-dept')"
  >
    <template #stats>
      <StatGrid :items="summaryItems" />
    </template>

    <!-- 2x2 子卡片网格 -->
    <div v-if="data?.timeline?.length" class="pk-milestone-grid">
      <div
        v-for="(item, idx) in data.timeline"
        :key="idx"
        class="pk-milestone-sub"
        :class="{ 'pk-milestone-sub--active': activeOffering === idx }"
        @click="$emit('risk-click', item); activeOffering = idx"
      >
        <!-- 头部：项目名 + 状态标签 -->
        <div class="pk-milestone-sub__header">
          <span class="pk-milestone-sub__title">{{ item.category }} {{ item.project }}</span>
          <span v-if="item.deviation > 10" class="pk-milestone-sub__tag">延期</span>
          <span v-else-if="item.deviation > 0" class="pk-milestone-sub__tag pk-milestone-sub__tag--warn">关注</span>
        </div>

        <!-- 圆环图 -->
        <div v-if="nextPhase(item)" class="pk-milestone-sub__donut">
          <DonutChart
            :percentage="arcPercent(nextPhase(item), item)"
            :size="44"
            :stroke-width="4"
            :color="arcColor(nextPhase(item))"
            :label="shortName(nextPhase(item).name)"
          />
        </div>

        <!-- 时间轴 -->
        <div class="pk-milestone-sub__track">
          <div class="pk-milestone-sub__track-line" />
          <template v-for="(phase, pi) in item.phases" :key="pi">
            <div
              class="pk-milestone-sub__node"
              :class="nodeClass(phase, pi, item)"
              :style="{ left: nodeLeft(pi, item.phases.length) + '%' }"
            >
              <span class="pk-milestone-sub__node-date">{{ formatDisplayDate(phase.date) }}</span>
              <span class="pk-milestone-sub__node-dot" @click.stop="$emit('phase-click', { phase, offering: item.category + ' ' + item.project, timelineItem: item })">
                <svg v-if="phase.status === 'completed'" viewBox="0 0 12 12" width="8" height="8">
                  <path d="M2.5 6L5 8.5L9.5 3.5" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              <span class="pk-milestone-sub__node-label">{{ phase.name }}</span>
            </div>
          </template>
        </div>
      </div>
    </div>
  </DataCard>
</template>

<script setup>
import { computed, h, ref } from 'vue'
import DataCard from '../common/DataCard.vue'
import StatGrid from '../common/StatGrid.vue'
import DonutChart from '../common/DonutChart.vue'

const props = defineProps({
  data: { type: Object, default: null }
})

defineEmits(['ai-click', 'summary-click', 'risk-click', 'phase-click'])

const activeOffering = ref(-1)

const FlagIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9' })
    ])
  }
}

const SHORT_NAMES = { '立项': 'RR', '审视': '审视', '结项': 'GA', 'RR准入': 'RR', 'TR5评审': 'TR5', '季度评审': '季度' }
function shortName(name) {
  return SHORT_NAMES[name] || (name ? name.substring(0, 2) : '?')
}

const statusText = computed(() => props.data?.status || '正常')
const statusColor = computed(() => {
  const m = { red: 'danger', yellow: 'warning', green: 'success', none: 'success' }
  return m[props.data?.statusType] || 'success'
})

const summaryItems = computed(() => {
  const timeline = props.data?.timeline || []
  return [
    { value: timeline.length, label: '项目总数' },
    { value: timeline.filter(t => t.deviation > 10).length, label: '高风险项', statusClass: 'danger' },
    { value: timeline.filter(t => t.phases?.some(p => p.status === 'pending')).length, label: '待完成', statusClass: 'warning' },
    { value: timeline.filter(t => t.phases?.every(p => p.status === 'completed')).length, label: '已完成', statusClass: 'success' }
  ]
})

/** 找到下一个里程碑(第一个未完成的) */
function nextPhase(item) {
  if (!item.phases?.length) return null
  return item.phases.find(p => p.status !== 'completed') || item.phases[item.phases.length - 1]
}

/** 日期字符串显示格式化："2028-12-31" → "28/12/31"，"2026/4/1" → "26/4/1"，"4/1" 不变 */
function formatDisplayDate(date) {
  if (!date) return ''
  // 统一按 / 和 - 拆分
  const parts = date.split(/[-/]/)
  if (parts.length === 3) {
    return `${parts[0].slice(-2)}/${parts[1]}/${parts[2]}`
  }
  return date
}

/** 日期字符串 → 线性数值（用于比较和进度计算），兼容 "2028-12-31"、"2026/4/1"、"4/1" 等格式 */
function dateToDecimal(date) {
  const parts = (date || '').split(/[-/]/).map(Number)
  if (parts.length === 3) {
    // "2026/4/1" / "2028-12-31" → year*12 + month + day/31，跨年顺序正确
    return parts[0] * 12 + parts[1] + parts[2] / 31
  }
  // "4/1" → month + day/31（遗留格式，假定为当前年）
  return parts[0] + (parts[1] || 1) / 31
}

/** 弧形仪表进度百分比（按设计稿：根据日期计算时间进度） */
function arcPercent(phase, item) {
  if (phase.status === 'completed') return 100
  const now = new Date()
  const todayVal = now.getFullYear() * 12 + (now.getMonth() + 1) + now.getDate() / 31
  const phaseVal = dateToDecimal(phase.date)
  if (todayVal >= phaseVal) return 100 // 已延期
  // 找前一个节点的日期作为起始
  const idx = item.phases.indexOf(phase)
  const prevVal = idx > 0 ? dateToDecimal(item.phases[idx - 1].date) : dateToDecimal(`${now.getFullYear()}/1/1`)
  const range = phaseVal - prevVal
  if (range <= 0) return 0
  const elapsed = todayVal - prevVal
  return Math.max(0, Math.min(100, Math.round((elapsed / range) * 100)))
}

/** 弧形仪表颜色 */
function arcColor(phase) {
  if (phase.status === 'completed') return 'var(--pk-success)'
  if (phase.risk === 'high') return 'var(--pk-danger)'
  if (phase.risk === 'yellow' || phase.risk === 'medium') return 'var(--pk-warning)'
  return 'var(--pk-success)'
}

/** 弧形仪表状态 */
function arcStatus(phase) {
  if (phase.status === 'completed') return 'done'
  if (phase.risk === 'high') return 'danger'
  if (phase.risk === 'yellow' || phase.risk === 'medium') return 'warn'
  return 'safe'
}

/** 节点水平位置百分比 */
function nodeLeft(idx, total) {
  if (total <= 1) return 50
  return (idx / (total - 1)) * 80 + 10
}

/** 时间轴节点样式 */
function nodeClass(phase, idx, item) {
  if (phase.status === 'completed') return 'pk-milestone-sub__node--done'
  const firstPending = item.phases.findIndex(p => p.status !== 'completed')
  if (idx === firstPending) {
    if (phase.risk === 'high') return 'pk-milestone-sub__node--danger'
    if (phase.risk === 'yellow' || phase.risk === 'medium') return 'pk-milestone-sub__node--warn'
    return ''
  }
  return 'pk-milestone-sub__node--future'
}
</script>

<style scoped>
/* ===== 网格 ===== */
.pk-milestone-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: 1fr 1fr;
  gap: 8px;
  margin-top: 4px;
  min-width: 0;
  flex: 1;
}

/* ===== 子卡片 ===== */
.pk-milestone-sub {
  background: var(--pk-card-bg);
  border: 1px solid var(--pk-border);
  border-radius: 10px;
  padding: 8px 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
  min-width: 0;
}

.pk-milestone-sub:hover {
  border-color: var(--pk-border-hover);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.pk-milestone-sub--active {
  border-color: var(--pk-accent);
  box-shadow: 0 0 0 2px var(--pk-accent-glow);
}

/* ===== 头部 ===== */
.pk-milestone-sub__header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.pk-milestone-sub__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--pk-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.pk-milestone-sub__tag {
  font-size: 12px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
  color: var(--pk-danger-dark);
  background: var(--pk-danger-light);
}
.pk-milestone-sub__tag--warn {
  color: var(--pk-warning-dark);
  background: var(--pk-warning-light);
}

/* ===== 圆环图 ===== */
.pk-milestone-sub__donut {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

/* ===== 时间轴 ===== */
.pk-milestone-sub__track {
  position: relative;
  /* 日期(11px行高) + gap(2px) + 圆点半径(9px) = 22px 为圆点中心 */
  /* 总高度 = 11 + 2 + 18 + 2 + 11 = 44px, 留点余量 */
  height: 48px;
}

/* 连线 — 精确穿过圆点中心 */
.pk-milestone-sub__track-line {
  position: absolute;
  top: 22px;
  left: 10%;
  right: 10%;
  height: 2px;
  background: var(--pk-border);
}

/* 节点 */
.pk-milestone-sub__node {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  z-index: 1;
}

/* 日期 */
.pk-milestone-sub__node-date {
  font-size: 11px;
  color: var(--pk-text-tertiary);
  font-variant-numeric: tabular-nums;
  line-height: 1;
  white-space: nowrap;
}

/* 圆点 */
.pk-milestone-sub__node-dot {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--pk-border-hover);
  background: var(--pk-card-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
  cursor: pointer;
}

/* 已完成 */
.pk-milestone-sub__node--done .pk-milestone-sub__node-dot {
  background: var(--pk-success);
  border-color: var(--pk-success);
}

/* 高风险 */
.pk-milestone-sub__node--danger .pk-milestone-sub__node-dot {
  background: var(--pk-danger);
  border-color: var(--pk-danger);
  box-shadow: 0 0 0 3px var(--pk-danger-glow);
  animation: dot-pulse 2.5s ease-in-out infinite;
}

/* 关注 */
.pk-milestone-sub__node--warn .pk-milestone-sub__node-dot {
  background: var(--pk-warning);
  border-color: var(--pk-warning);
  box-shadow: 0 0 0 3px var(--pk-warning-glow);
}

/* 未来 */
.pk-milestone-sub__node--future .pk-milestone-sub__node-dot {
  border-color: var(--pk-border-hover);
  background: var(--pk-card-bg);
}

/* 阶段名 */
.pk-milestone-sub__node-label {
  font-size: 11px;
  color: var(--pk-text-secondary);
  white-space: nowrap;
  text-align: center;
  max-width: 56px;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

.pk-milestone-sub__node--danger .pk-milestone-sub__node-label {
  color: var(--pk-danger);
  font-weight: 600;
}

@keyframes dot-pulse {
  0%, 100% { box-shadow: 0 0 0 3px var(--pk-danger-glow); }
  50% { box-shadow: 0 0 0 5px var(--pk-danger-glow-weak); }
}

/* Responsive */
@media (max-width: 600px) {
  .pk-milestone-grid {
    grid-template-columns: 1fr;
  }
}

@media (min-width: 1600px) {
  .pk-milestone-sub__title {
    font-size: 15px;
  }
  .pk-milestone-sub__tag {
    font-size: 13px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 52px !important;
  }
  .pk-milestone-sub__node-date {
    font-size: 12px;
  }
  .pk-milestone-sub__node-dot {
    width: 20px;
    height: 20px;
  }
  .pk-milestone-sub__node-label {
    font-size: 12px;
    max-width: 60px;
  }
  .pk-milestone-sub__track {
    height: 50px;
  }
  .pk-milestone-sub__track-line {
    top: 24px;
  }
}

@media (min-width: 1920px) {
  .pk-milestone-sub__title {
    font-size: 16px;
  }
  .pk-milestone-sub__tag {
    font-size: 14px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 62px !important;
  }
  .pk-milestone-sub__node-date {
    font-size: 13px;
  }
  .pk-milestone-sub__node-dot {
    width: 22px;
    height: 22px;
  }
  .pk-milestone-sub__node-label {
    font-size: 13px;
    max-width: 64px;
  }
  .pk-milestone-sub__track {
    height: 54px;
  }
  .pk-milestone-sub__track-line {
    top: 26px;
  }
}

@media (min-width: 2560px) {
  .pk-milestone-sub__title {
    font-size: 17px;
  }
  .pk-milestone-sub__tag {
    font-size: 14px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 72px !important;
  }
  .pk-milestone-sub__node-date {
    font-size: 14px;
  }
  .pk-milestone-sub__node-dot {
    width: 24px;
    height: 24px;
  }
  .pk-milestone-sub__node-label {
    font-size: 14px;
    max-width: 68px;
  }
  .pk-milestone-sub__track {
    height: 58px;
  }
  .pk-milestone-sub__track-line {
    top: 28px;
  }
}
</style>

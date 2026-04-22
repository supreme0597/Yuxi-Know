<template>
  <DataCard
    title="项目里程碑"
    :icon="FlagIcon"
    icon-color="#8b5cf6"
    :status-text="statusText"
    :status-color="statusColor"
    :ai-summary="data?.aiSummary"
    @ai-click="$emit('ai-click', 'milestone-dept')"
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
        @click="$emit('risk-click', item)"
      >
        <!-- 头部：项目名 + 状态标签 -->
        <div class="pk-milestone-sub__header">
          <span class="pk-milestone-sub__title">{{ item.category }} {{ item.project }}</span>
          <span v-if="item.deviation > 10" class="pk-milestone-sub__tag">延期</span>
          <span v-else-if="item.deviation > 0" class="pk-milestone-sub__tag pk-milestone-sub__tag--warn">关注</span>
        </div>

        <!-- 下一里程碑 + 弧形仪表 -->
        <div v-if="nextPhase(item)" class="pk-milestone-sub__next">
          <!-- 弧形半圆仪表 -->
          <div class="pk-milestone-sub__arc" :class="'pk-milestone-sub__arc--' + arcStatus(nextPhase(item))">
            <svg width="40" height="22" viewBox="0 0 40 22">
              <!-- 背景弧 -->
              <path d="M4 20 A16 16 0 0 1 36 20" fill="none" stroke="#e2e8f0" stroke-width="3" stroke-linecap="round" />
              <!-- 进度弧 -->
              <path
                d="M4 20 A16 16 0 0 1 36 20"
                fill="none"
                :stroke="arcColor(nextPhase(item))"
                stroke-width="3"
                stroke-linecap="round"
                :stroke-dasharray="50.27"
                :stroke-dashoffset="50.27 - (arcPercent(nextPhase(item), item) / 100) * 50.27"
              />
            </svg>
            <span class="pk-milestone-sub__arc-label">{{ shortName(nextPhase(item).name) }}</span>
          </div>
          <!-- 文字信息 -->
          <div class="pk-milestone-sub__next-info">
            <span class="pk-milestone-sub__next-name">{{ nextPhase(item).name }}</span>
            <span class="pk-milestone-sub__next-date">{{ nextPhase(item).date }}</span>
          </div>
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
              <span class="pk-milestone-sub__node-date">{{ phase.date }}</span>
              <span class="pk-milestone-sub__node-dot">
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
import { computed, h } from 'vue'
import DataCard from '../common/DataCard.vue'
import StatGrid from '../common/StatGrid.vue'

const props = defineProps({
  data: { type: Object, default: null }
})

defineEmits(['ai-click', 'risk-click'])

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

/** 日期字符串 "4/1" → 小数月份（用于比较） */
function dateToDecimal(date) {
  const parts = (date || '').split('/')
  return parseInt(parts[0]) + parseInt(parts[1] || 1) / 31
}

/** 弧形仪表进度百分比（按设计稿：根据日期计算时间进度） */
function arcPercent(phase, item) {
  if (phase.status === 'completed') return 100
  const now = new Date()
  const todayVal = now.getMonth() + 1 + now.getDate() / 31
  const phaseVal = dateToDecimal(phase.date)
  if (todayVal >= phaseVal) return 100 // 已延期
  // 找前一个节点的日期作为起始
  const idx = item.phases.indexOf(phase)
  const prevVal = idx > 0 ? dateToDecimal(item.phases[idx - 1].date) : dateToDecimal('1/1')
  const range = phaseVal - prevVal
  if (range <= 0) return 0
  const elapsed = todayVal - prevVal
  return Math.max(0, Math.min(100, Math.round((elapsed / range) * 100)))
}

/** 弧形仪表颜色 */
function arcColor(phase) {
  if (phase.status === 'completed') return '#059669'
  if (phase.risk === 'high') return '#dc2626'
  if (phase.risk === 'yellow' || phase.risk === 'medium') return '#d97706'
  return '#059669'
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
  background: #fff;
  border: 1px solid #eef0f4;
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
  border-color: #dde1e8;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

/* ===== 头部 ===== */
.pk-milestone-sub__header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.pk-milestone-sub__title {
  font-size: 11px;
  font-weight: 600;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.pk-milestone-sub__tag {
  font-size: 9px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 4px;
  white-space: nowrap;
  flex-shrink: 0;
  color: #b91c1c;
  background: #fef2f2;
}
.pk-milestone-sub__tag--warn {
  color: #92400e;
  background: #fef3c7;
}

/* ===== 下一里程碑 + 弧形仪表 ===== */
.pk-milestone-sub__next {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 弧形半圆仪表容器 */
.pk-milestone-sub__arc {
  position: relative;
  width: 40px;
  height: 22px;
  flex-shrink: 0;
}

.pk-milestone-sub__arc svg {
  display: block;
}

/* 弧内标签（里程碑缩写） */
.pk-milestone-sub__arc-label {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  font-size: 8px;
  font-weight: 700;
  color: #475569;
}

.pk-milestone-sub__arc--danger .pk-milestone-sub__arc-label { color: #b91c1c; }
.pk-milestone-sub__arc--warn .pk-milestone-sub__arc-label { color: #92400e; }

/* 文字信息 */
.pk-milestone-sub__next-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.pk-milestone-sub__next-name {
  font-size: 11px;
  font-weight: 700;
  color: #334155;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pk-milestone-sub__next-date {
  font-size: 9px;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
}

/* ===== 时间轴 ===== */
.pk-milestone-sub__track {
  position: relative;
  margin-top: auto;
  /* 日期(8px行高) + gap(2px) + 圆点半径(6px) = 16px 为圆点中心 */
  /* 总高度 = 8 + 2 + 12 + 2 + 8 = 32px, 留点余量 */
  height: 36px;
}

/* 连线 — 精确穿过圆点中心 */
.pk-milestone-sub__track-line {
  position: absolute;
  top: 16px;
  left: 10%;
  right: 10%;
  height: 1.5px;
  background: #e2e8f0;
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
  font-size: 8px;
  color: #94a3b8;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  height: 8px;
}

/* 圆点 */
.pk-milestone-sub__node-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #cbd5e1;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

/* 已完成 */
.pk-milestone-sub__node--done .pk-milestone-sub__node-dot {
  background: #059669;
  border-color: #059669;
}

/* 高风险 */
.pk-milestone-sub__node--danger .pk-milestone-sub__node-dot {
  background: #dc2626;
  border-color: #dc2626;
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.2);
  animation: dot-pulse 2.5s ease-in-out infinite;
}

/* 关注 */
.pk-milestone-sub__node--warn .pk-milestone-sub__node-dot {
  background: #d97706;
  border-color: #d97706;
  box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.15);
}

/* 未来 */
.pk-milestone-sub__node--future .pk-milestone-sub__node-dot {
  border-color: #cbd5e1;
  background: #fff;
}

/* 阶段名 */
.pk-milestone-sub__node-label {
  font-size: 8px;
  color: #6b7280;
  white-space: nowrap;
  text-align: center;
  max-width: 40px;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

.pk-milestone-sub__node--danger .pk-milestone-sub__node-label {
  color: #b91c1c;
  font-weight: 600;
}

@keyframes dot-pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.2); }
  50% { box-shadow: 0 0 0 5px rgba(220, 38, 38, 0.1); }
}

/* Responsive */
@media (max-width: 600px) {
  .pk-milestone-grid {
    grid-template-columns: 1fr;
  }
}
</style>

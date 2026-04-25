<template>
  <!-- 原名：任务令进展 修改为 对外承诺KPI&任务令&夺旗进展 -->
  <DataCard
    title="对外承诺KPI&任务令&夺旗进展"
    :icon="ClipboardIcon"
    icon-color="var(--pk-accent)"
    :status-text="statusText"
    :status-color="statusColor"
    :ai-summary="data?.aiSummary"
    @ai-click="$emit('ai-click', 'task-overview')"
    @summary-click="$emit('summary-click', 'task-dept')"
  >
    <template #stats>
      <StatGrid :items="summaryItems" @item-click="$emit('metric-click', 'task-dept', $event)" />
    </template>

    <!-- 子卡片：PMC / RWL / DQ -->
    <div v-if="hasTaskOrders" class="pk-task-subcards">
      <div
        v-for="(tasks, key) in taskOrderGroups"
        :key="key"
        class="pk-task-subcard"
      >
        <div class="pk-task-subcard__header">
          <span class="pk-task-subcard__title">{{ subcardTitles[key] || key }}</span>
          <span class="pk-task-subcard__count">{{ tasks.length }}项</span>
        </div>
        <div class="pk-task-subcard__lanes">
          <div
            v-for="lane in groupLanes(tasks)"
            :key="lane.group"
            class="pk-task-lane"
          >
            <!-- 分组标签（group） -->
            <div class="pk-task-lane__label">
              <span class="pk-task-lane__label-text">{{ lane.group }}</span>
            </div>

            <!-- 泳道节点区域 -->
            <div class="pk-task-lane__content">
              <div
                v-for="node in laneNodes(lane, tasks)"
                :key="node.id"
                class="pk-task-node"
                :class="`pk-task-node--${riskClass(node)}`"
                :style="{ left: node._left + '%' }"
                @click="$emit('task-click', node)"
              >
                <DonutChart
                  :percentage="node.progress"
                  :size="42"
                  :stroke-width="4"
                  :color="ringFgColor(node)"
                  :label="`${node.progress}%`"
                />
                <span class="pk-task-node__name" :title="node.name">{{ node.name }}</span>
                <span class="pk-task-node__date" :class="{ 'pk-task-node__date--overdue': node.status === 'overdue' }">
                  {{ node.deadline }}
                </span>
              </div>
            </div>
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

defineEmits(['ai-click', 'summary-click', 'task-click', 'metric-click', 'group-click'])

const ClipboardIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4' })
    ])
  }
}

const statusText = computed(() => props.data?.status || '正常')
const statusColor = computed(() => {
  const m = { green: 'success', yellow: 'warning', red: 'danger' }
  return m[props.data?.statusType] || 'success'
})

const subcardTitles = {
  PMC: '对外承诺',
  RWL: '任务令',
  DQ: '夺旗'
}

/** 所有任务的扁平数组（兼容对象型/数组型 taskOrders） */
const allTasks = computed(() => {
  const to = props.data?.taskOrders
  if (Array.isArray(to)) return to
  if (to && typeof to === 'object') return Object.values(to).flat()
  return []
})

/** 按子分类分组（PMC/RWL/DQ） */
const taskOrderGroups = computed(() => {
  const to = props.data?.taskOrders
  if (to && typeof to === 'object' && !Array.isArray(to)) return to
  return { all: to || [] }
})

const hasTaskOrders = computed(() => {
  const groups = taskOrderGroups.value
  return Object.values(groups).some(arr => arr.length > 0)
})

const summaryItems = computed(() => {
  const tos = allTasks.value
  return [
    { value: tos.length, label: '任务令总数' },
    { value: tos.filter(t => t.risk === 'high').length, label: '高风险', statusClass: 'danger', clickable: true },
    { value: tos.filter(t => t.progress < 100).length, label: '待完成', statusClass: 'warning' },
    { value: tos.filter(t => t.progress >= 100).length, label: '已完成', statusClass: 'success' }
  ]
})

/** 日期字符串 "4/10" → 可比较数值（月×31+日） */
function dateToValue(date) {
  if (!date) return 0
  const parts = date.split('/')
  return parseInt(parts[0], 10) * 31 + parseInt(parts[1], 10)
}

/** 节点最小间距（%），保证相邻节点不重叠 */
const NODE_MIN_GAP = 18

/** 按 group 分组 */
function groupLanes(tasks) {
  const map = {}
  for (const to of tasks) {
    const g = to.group || '其他'
    if (!map[g]) map[g] = { group: g, tasks: [] }
    map[g].tasks.push(to)
  }
  return Object.values(map)
}

/** 为指定任务列表计算节点位置（每个子卡片独立时间轴） */
function getSubcardPositionMap(tasks) {
  if (!tasks?.length) return new Map()
  const allDates = tasks.map(t => dateToValue(t.deadline)).filter(Boolean)
  if (!allDates.length) return new Map()

  const minDate = Math.min(...allDates)
  const maxDate = Math.max(...allDates)
  const dateRange = maxDate - minDate || 1
  const PADDING = 15
  const USABLE = 100 - 2 * PADDING
  const resultMap = new Map()

  for (const lane of groupLanes(tasks)) {
    const laneTasks = [...lane.tasks].sort((a, b) => dateToValue(a.deadline) - dateToValue(b.deadline))
    if (!laneTasks.length) continue

    const positions = laneTasks.map(t => {
      const dv = dateToValue(t.deadline)
      const ratio = dateRange > 0 ? (dv - minDate) / dateRange : 0.5
      return PADDING + ratio * USABLE
    })

    for (let i = 1; i < positions.length; i++) {
      if (positions[i] - positions[i - 1] < NODE_MIN_GAP) {
        positions[i] = positions[i - 1] + NODE_MIN_GAP
      }
    }

    const maxPos = positions[positions.length - 1]
    if (maxPos > 100 - PADDING) {
      const shift = maxPos - (100 - PADDING)
      for (let i = 0; i < positions.length; i++) positions[i] -= shift
      const minPos = positions[0]
      if (minPos < PADDING) {
        for (let i = 0; i < positions.length; i++) positions[i] += PADDING - minPos
      }
    }

    for (let i = 1; i < positions.length; i++) {
      if (positions[i] - positions[i - 1] < NODE_MIN_GAP) {
        positions[i] = positions[i - 1] + NODE_MIN_GAP
      }
    }

    laneTasks.forEach((t, i) => {
      resultMap.set(t.id, Math.round(Math.max(PADDING, Math.min(100 - PADDING, positions[i])) * 10) / 10)
    })
  }

  return resultMap
}

/** 获取泳道内带位置信息的节点列表 */
function laneNodes(lane, tasks) {
  const posMap = getSubcardPositionMap(tasks)
  return lane.tasks.map(t => ({
    ...t,
    _left: posMap.get(t.id) ?? 50
  }))
}

function riskClass(to) {
  if (to.risk === 'high' || to.status === 'overdue') return 'danger'
  if (to.risk === 'medium') return 'warning'
  return 'normal'
}

function ringFgColor(to) {
  return riskClass(to) === 'danger' ? 'var(--pk-danger)' : riskClass(to) === 'warning' ? 'var(--pk-warning)' : 'var(--pk-success)'
}
</script>

<style scoped>
/* 子卡片容器 */
.pk-task-subcards {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 4px;
  min-height: 0;
}

.pk-task-subcard {
  flex: 1 1 300px;
}

/* 单个子卡片 */
.pk-task-subcard {
  min-width: 0;
  border-radius: 8px;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 4px 12px rgba(0, 0, 0, 0.04);
  background: var(--gray-0);
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.pk-task-subcard:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08), 0 8px 24px rgba(0, 0, 0, 0.06);
  transform: translateY(-1px);
}

.pk-task-subcard__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--gray-100);
  flex-shrink: 0;
}

.pk-task-subcard__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-700);
}

.pk-task-subcard__count {
  font-size: 13px;
  color: var(--gray-400);
  font-variant-numeric: tabular-nums;
}

.pk-task-subcard__lanes {
  display: flex;
  flex-direction: column;
  flex: 1;
}

/* 子卡片内泳道标签：加宽横排 */
.pk-task-subcard .pk-task-lane__label {
  width: 56px;
  padding: 6px 6px;
  color: var(--gray-600);
}

.pk-task-subcard .pk-task-lane__label-text {
  font-size: 12px;
  line-height: 1.3;
  text-align: center;
  word-break: break-all;
}

/* 子卡片内泳道：高度由内容决定，不平分 */
.pk-task-subcard .pk-task-lane {
  flex: 0 0 auto;
}

/* 子卡片内泳道内容：相对定位容器，节点绝对定位 */
.pk-task-subcard .pk-task-lane__content {
  position: relative;
  /* top8 + donut42 + gap3 + name(2行~28) + gap3 + date14 = 98px + 底部留白10px */
  min-height: 108px;
  padding: 8px 10px 10px;
  overflow: visible;
}

/* 子卡片内节点：绝对定位，顶部对齐（不居中，避免溢出） */
.pk-task-subcard .pk-task-node {
  position: absolute;
  top: 8px;
  transform: translateX(-50%);
}

.pk-task-subcard .pk-task-node:hover {
  transform: translateX(-50%) scale(1.08);
}

.pk-task-subcard .pk-task-node__name {
  font-size: 11px;
  max-width: 56px;
  -webkit-line-clamp: 2;
}

.pk-task-subcard .pk-task-node__date {
  font-size: 11px;
}

/* 泳道容器 */
.pk-task-lanes {
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  flex: 1;
  margin-top: 4px;
  overflow: hidden;
}

/* 泳道行 */
.pk-task-lane {
  display: flex;
  align-items: stretch;
  flex: 1;
  border-bottom: 1px dashed var(--gray-150);
}

.pk-task-lane:last-child {
  border-bottom: none;
}

/* 产业标签 */
.pk-task-lane__label {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-400);
  cursor: pointer;
  transition: color 0.15s;
  /* 固定3字宽度，内容自适应换行 */
  width: 3em;
}
.pk-task-lane__label:hover {
  color: var(--pk-accent);
}

.pk-task-lane__label-text {
  word-break: keep-all;
  overflow-wrap: break-word;
  text-align: center;
  line-height: 1.3;
  max-width: 3em; /* 最多3个字宽度，超出换行 */
}

/* 泳道内容：相对定位容器，节点绝对定位 */
.pk-task-lane__content {
  flex: 1;
  position: relative;
  /* 节点高度：donut(54) + gap(3) + name(16) + gap(3) + date(16) + padding(10*2) ≈ 112px */
  min-height: 112px;
  padding: 8px 0;
  overflow: visible;
}

/* 任务令节点（绝对定位） */
.pk-task-node {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  z-index: 2;
  cursor: pointer;
  transition: transform 0.15s;
}

.pk-task-node:hover {
  transform: translate(-50%, -50%) scale(1.08);
  z-index: 3;
}

/* 节点名称 */
.pk-task-node__name {
  font-size: 11px;
  font-weight: 500;
  color: var(--gray-700);
  text-align: center;
  max-width: 56px;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
}

/* 截止日期 */
.pk-task-node__date {
  font-size: 11px;
  color: var(--gray-400);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.pk-task-node__date--overdue {
  color: var(--pk-danger);
  font-weight: 600;
}

/* 节点光晕 */
.pk-task-node--danger .pk-donut {
  filter: drop-shadow(0 0 4px var(--pk-danger-glow-strong));
}

/* Responsive */
@media (max-width: 768px) {
  .pk-task-lane__label {
    min-width: 24px;
    padding: 4px 5px;
    font-size: 10px;
  }
  .pk-task-lane__label-text {
    max-width: 3em;
  }
  .pk-task-node__name {
    font-size: 10px;
    max-width: 48px;
  }
  .pk-task-node__date {
    font-size: 10px;
  }
}

@media (min-width: 1600px) {
  .pk-task-lane__label {
    font-size: 13px;
  }
  .pk-task-lane__label-text {
    max-width: 4em;
  }
  .pk-task-node__name {
    font-size: 12px;
    max-width: 64px;
  }
  .pk-task-node__date {
    font-size: 12px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 52px !important;
  }
  .pk-task-lane__content {
    min-height: 124px;
  }
  /* 子卡片内保持小尺寸 */
  .pk-task-subcard :deep(.pk-donut) {
    --pk-donut-size: 42px !important;
  }
  .pk-task-subcard .pk-task-node__name {
    font-size: 11px;
    max-width: 56px;
  }
  .pk-task-subcard .pk-task-node__date {
    font-size: 11px;
  }
  .pk-task-subcard .pk-task-lane__content {
    min-height: 108px;
  }
}

@media (min-width: 1920px) {
  .pk-task-lane__label {
    font-size: 14px;
  }
  .pk-task-lane__label-text {
    max-width: 4em;
  }
  .pk-task-node__name {
    font-size: 13px;
    max-width: 72px;
  }
  .pk-task-node__date {
    font-size: 13px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 62px !important;
  }
  .pk-task-lane__content {
    min-height: 136px;
  }
  .pk-task-subcard :deep(.pk-donut) {
    --pk-donut-size: 42px !important;
  }
  .pk-task-subcard .pk-task-node__name {
    font-size: 11px;
    max-width: 56px;
  }
  .pk-task-subcard .pk-task-node__date {
    font-size: 11px;
  }
  .pk-task-subcard .pk-task-lane__content {
    min-height: 108px;
  }
}

@media (min-width: 2560px) {
  .pk-task-lane__label {
    font-size: 15px;
  }
  .pk-task-lane__label-text {
    max-width: 5em;
  }
  .pk-task-node__name {
    font-size: 14px;
    max-width: 80px;
  }
  .pk-task-node__date {
    font-size: 14px;
  }
  :deep(.pk-donut) {
    --pk-donut-size: 72px !important;
  }
  .pk-task-lane__content {
    min-height: 148px;
  }
  .pk-task-subcard :deep(.pk-donut) {
    --pk-donut-size: 42px !important;
  }
  .pk-task-subcard .pk-task-node__name {
    font-size: 11px;
    max-width: 56px;
  }
  .pk-task-subcard .pk-task-node__date {
    font-size: 11px;
  }
  .pk-task-subcard .pk-task-lane__content {
    min-height: 108px;
  }
}
</style>

<template>
  <DataCard
    title="任务令进展"
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

    <!-- 产业泳道（共享时间轴） -->
    <div v-if="data?.taskOrders?.length" class="pk-task-lanes">
      <div
        v-for="lane in lanes"
        :key="lane.industry"
        class="pk-task-lane"
      >
        <!-- 产业标签 -->
        <div class="pk-task-lane__label" @click.stop="$emit('industry-click', lane.industry)">
          <span class="pk-task-lane__label-text">{{ lane.industry }}</span>
        </div>

        <!-- 泳道节点区域 -->
        <div class="pk-task-lane__content">
          <div
            v-for="node in laneNodes(lane)"
            :key="node.id"
            class="pk-task-node"
            :class="`pk-task-node--${riskClass(node)}`"
            :style="{ left: node._left + '%' }"
            @click="$emit('task-click', node)"
          >
            <DonutChart
              :percentage="node.progress"
              :size="44"
              :stroke-width="4"
              :color="ringFgColor(node)"
              :label="`${node.progress}%`"
            />
            <span class="pk-task-node__name">{{ node.name }}</span>
            <span class="pk-task-node__date" :class="{ 'pk-task-node__date--overdue': node.status === 'overdue' }">
              {{ node.deadline }}
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

defineEmits(['ai-click', 'summary-click', 'task-click', 'metric-click', 'industry-click'])

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

const summaryItems = computed(() => {
  const tos = props.data?.taskOrders || []
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
const NODE_MIN_GAP = 14

/**
 * 按泳道计算节点位置，带碰撞检测
 * 算法：
 * 1. 每个泳道内，按 deadline 排序
 * 2. 初始位置 = 时间在全局时间范围中的比例映射
 * 3. 从左到右扫描，如果相邻节点间距 < NODE_MIN_GAP，右推到最小间距
 * 4. 如果右推超出右边界，整体左移压缩
 */
const lanePositionMap = computed(() => {
  const tos = props.data?.taskOrders || []
  if (!tos.length) return new Map()

  // 全局时间范围
  const allDates = tos.map(t => dateToValue(t.deadline)).filter(Boolean)
  const minDate = Math.min(...allDates)
  const maxDate = Math.max(...allDates)
  const dateRange = maxDate - minDate || 1

  // 首尾留白：10% ~ 90%
  const PADDING = 10
  const USABLE = 100 - 2 * PADDING

  const resultMap = new Map()

  for (const lane of lanes.value) {
    const tasks = [...lane.tasks].sort((a, b) => dateToValue(a.deadline) - dateToValue(b.deadline))
    if (!tasks.length) continue

    // 步骤1：按时间计算初始位置
    const positions = tasks.map(t => {
      const dv = dateToValue(t.deadline)
      const ratio = dateRange > 0 ? (dv - minDate) / dateRange : 0.5
      return PADDING + ratio * USABLE
    })

    // 步骤2：从左到右碰撞检测，保证最小间距
    for (let i = 1; i < positions.length; i++) {
      if (positions[i] - positions[i - 1] < NODE_MIN_GAP) {
        positions[i] = positions[i - 1] + NODE_MIN_GAP
      }
    }

    // 步骤3：如果超出右边界，整体左移
    const maxPos = positions[positions.length - 1]
    if (maxPos > 100 - PADDING) {
      const shift = maxPos - (100 - PADDING)
      for (let i = 0; i < positions.length; i++) {
        positions[i] -= shift
      }
      // 确保不超出左边界
      const minPos = positions[0]
      if (minPos < PADDING) {
        for (let i = 0; i < positions.length; i++) {
          positions[i] += PADDING - minPos
        }
      }
    }

    // 步骤4：二次碰撞检测（整体偏移后可能再次重叠）
    for (let i = 1; i < positions.length; i++) {
      if (positions[i] - positions[i - 1] < NODE_MIN_GAP) {
        positions[i] = positions[i - 1] + NODE_MIN_GAP
      }
    }

    tasks.forEach((t, i) => {
      resultMap.set(t.id, Math.round(Math.max(PADDING, Math.min(100 - PADDING, positions[i])) * 10) / 10)
    })
  }

  return resultMap
})

/** 获取泳道内带位置信息的节点列表 */
function laneNodes(lane) {
  return lane.tasks.map(t => ({
    ...t,
    _left: lanePositionMap.value.get(t.id) ?? 50
  }))
}

/** 按产业分组（保持原数据顺序） */
const lanes = computed(() => {
  const tos = props.data?.taskOrders || []
  const map = {}
  for (const to of tos) {
    const ind = to.industry || '其他'
    if (!map[ind]) map[ind] = { industry: ind, tasks: [] }
    map[ind].tasks.push(to)
  }
  return Object.values(map)
})

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
/* 泳道容器 */
.pk-task-lanes {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--pk-border);
  border-radius: 8px;
  flex: 1;
  margin-top: 4px;
}

/* 泳道行 */
.pk-task-lane {
  display: flex;
  align-items: stretch;
  flex: 1;
  border-bottom: 1px solid var(--pk-border);
  background: var(--pk-page-bg);
}

.pk-task-lane:first-child {
  border-radius: 7px 7px 0 0;
}

.pk-task-lane:last-child {
  border-bottom: none;
  border-radius: 0 0 7px 7px;
}

.pk-task-lane:only-child {
  border-radius: 7px;
}

/* 产业标签圆角跟随泳道行 */
.pk-task-lane:first-child .pk-task-lane__label {
  border-radius: 7px 0 0 0;
}

.pk-task-lane:last-child .pk-task-lane__label {
  border-radius: 0 0 0 7px;
}

.pk-task-lane:only-child .pk-task-lane__label {
  border-radius: 7px 0 0 7px;
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
  color: var(--gray-500);
  background: var(--pk-neutral-bg);
  border-right: 1px solid var(--pk-border);
  cursor: pointer;
  transition: background 0.15s;
  /* 固定3字宽度，内容自适应换行 */
  width: 3em;
}
.pk-task-lane__label:hover {
  background: var(--pk-accent-light);
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
}
</style>

<template>
  <DataCard
    title="任务令进展"
    :icon="ClipboardIcon"
    icon-color="#6366f1"
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
        <div class="pk-task-lane__label" @click.stop="$emit('industry-click', lane.industry)">{{ lane.industry }}</div>

        <!-- 泳道节点区域 -->
        <div class="pk-task-lane__content">
          <div
            v-for="to in lane.tasks"
            :key="to.id"
            class="pk-task-node"
            :class="`pk-task-node--${riskClass(to)}`"
            :style="{ left: nodePosition(to) + '%' }"
            @click="$emit('task-click', to)"
          >
            <DonutChart
              :percentage="to.progress"
              :size="44"
              :stroke-width="4"
              :color="ringFgColor(to)"
              :label="`${to.progress}%`"
            />
            <span class="pk-task-node__name">{{ to.name }}</span>
            <span class="pk-task-node__date" :class="{ 'pk-task-node__date--overdue': to.status === 'overdue' }">
              {{ to.deadline }}
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

/** 全局排序：所有任务令按截止日期排序，计算每个节点的水平位置百分比 */
const sortedPositions = computed(() => {
  const tos = props.data?.taskOrders || []
  if (!tos.length) return new Map()

  // 按日期排序，记录排序序号
  const sorted = [...tos].sort((a, b) => dateToValue(a.deadline) - dateToValue(b.deadline))
  const total = sorted.length

  const posMap = new Map()
  sorted.forEach((to, idx) => {
    // 均匀分布：14% ~ 86%，首尾留边距避免环形图溢出
    const left = total <= 1 ? 50 : 14 + (idx / (total - 1)) * 72
    posMap.set(to.id, Math.round(left * 10) / 10)
  })
  return posMap
})

/** 获取节点的水平位置百分比 */
function nodePosition(to) {
  return sortedPositions.value.get(to.id) ?? 50
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
  return riskClass(to) === 'danger' ? '#dc2626' : riskClass(to) === 'warning' ? '#d97706' : '#059669'
}
</script>

<style scoped>
/* 泳道容器 */
.pk-task-lanes {
  display: flex;
  flex-direction: column;
  border: 1px solid #eef0f4;
  border-radius: 8px;
  flex: 1;
  margin-top: 4px;
}

/* 泳道行 */
.pk-task-lane {
  display: flex;
  align-items: stretch;
  flex: 1;
  border-bottom: 1px solid #f1f3f6;
  background: #fafbfc;
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
  width: 40px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-500);
  background: #f5f6f8;
  border-right: 1px solid #eef0f4;
  cursor: pointer;
  transition: background 0.15s;
}
.pk-task-lane__label:hover {
  background: #eef2ff;
  color: #6366f1;
}

/* 泳道内容：相对定位容器，节点绝对定位 */
.pk-task-lane__content {
  flex: 1;
  position: relative;
  min-height: 76px;
}

/* 任务令节点（绝对定位，共享全局时间轴位置） */
.pk-task-node {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
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
  max-width: 50px;
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
  color: #dc2626;
  font-weight: 600;
}

/* 节点光晕 */
.pk-task-node--danger .pk-donut {
  filter: drop-shadow(0 0 4px rgba(220, 38, 38, 0.25));
}

/* Responsive */
@media (max-width: 768px) {
  .pk-task-lane__label {
    width: 32px;
    font-size: 9px;
  }
}

@media (min-width: 1600px) {
  .pk-task-lane__label {
    font-size: 13px;
  }
  .pk-task-node__name {
    font-size: 12px;
  }
  .pk-task-node__date {
    font-size: 12px;
  }
}

@media (min-width: 1920px) {
  .pk-task-lane__label {
    font-size: 14px;
  }
  .pk-task-node__name {
    font-size: 13px;
  }
  .pk-task-node__date {
    font-size: 13px;
  }
}

@media (min-width: 2560px) {
  .pk-task-lane__label {
    font-size: 15px;
  }
  .pk-task-node__name {
    font-size: 14px;
  }
  .pk-task-node__date {
    font-size: 14px;
  }
}
</style>

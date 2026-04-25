<template>
  <DataCard
    title="费用执行"
    :icon="BudgetIcon"
    icon-color="var(--pk-success)"
    :status-text="statusText"
    :status-color="data?.status || 'info'"
    :ai-summary="data?.aiSummary"
    ai-lines="1"
    @ai-click="$emit('ai-click', 'budget')"
    @summary-click="$emit('ai-click', 'budget')"
  >
    <StatGrid :items="statItems" />
    <RiskList :risks="data?.risks" @risk-click="$emit('risk-click', $event)" />
  </DataCard>
</template>

<script setup>
import { computed, h } from 'vue'
import DataCard from '../common/DataCard.vue'
import StatGrid from '../common/StatGrid.vue'
import RiskList from '../common/RiskList.vue'

const BudgetIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z' })
    ])
  }
}

const props = defineProps({ data: { type: Object, default: null } })
defineEmits(['ai-click', 'risk-click'])

const statusMap = { green: '正常', normal: '正常', yellow: '关注', warning: '关注', orange: '警告', red: '关键风险', critical: '关键风险' }
const statusText = computed(() => statusMap[props.data?.status] || '正常')

const deviation = computed(() => {
  const rate = props.data?.executionRate ?? 0
  return Math.round(rate - 100)
})

const deviationClass = computed(() => {
  const s = props.data?.status
  if (s === 'red' || s === 'critical') return 'danger'
  if (s === 'yellow' || s === 'warning' || s === 'orange') return 'warning'
  return ''
})

const statItems = computed(() => [
  {
    value: (deviation.value >= 0 ? '+' : '') + deviation.value + '%',
    label: '偏差值',
    statusClass: deviationClass.value
  },
  {
    value: '¥' + (props.data?.total ?? 0) + 'W',
    label: '总预算'
  },
  {
    value: '¥' + (props.data?.executed ?? 0) + 'W',
    label: '已执行'
  },
  {
    value: (props.data?.executionRate ?? 0) + '%',
    label: '执行进度'
  }
])
</script>

<style scoped>
/* 统计区样式由 StatGrid 组件统一管理 */
</style>

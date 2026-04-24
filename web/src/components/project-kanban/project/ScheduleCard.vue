<template>
  <DataCard
    title="进度管理"
    :icon="ScheduleIcon"
    icon-color="var(--pk-success)"
    :status-text="statusText"
    :status-color="data?.status || 'info'"
    :ai-summary="data?.aiSummary"
    ai-lines="1"
    @ai-click="$emit('ai-click', 'schedule')"
    @summary-click="$emit('ai-click', 'schedule')"
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

const ScheduleIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M13 7h8m0 0v8m0-8l-8 8-4-4-6 6' })
    ])
  }
}

const props = defineProps({ data: { type: Object, default: null } })
defineEmits(['ai-click', 'risk-click'])

const statusMap = { green: '正常', normal: '正常', yellow: '关注', warning: '关注', orange: '警告', red: '关键风险', critical: '关键风险' }
const statusText = computed(() => statusMap[props.data?.status] || '正常')

const statItems = computed(() => [
  { value: (props.data?.iterProgress ?? 0) + '%', label: '迭代', statusClass: '' },
  { value: (props.data?.testProgress ?? 0) + '%', label: '用例', statusClass: 'warning' },
  { value: props.data?.failed ?? 0, label: '失败', statusClass: 'danger' },
  { value: (props.data?.passRate ?? 0) + '%', label: '通过率', statusClass: 'success' }
])
</script>

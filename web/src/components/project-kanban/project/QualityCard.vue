<template>
  <DataCard
    title="质量管理"
    :icon="QualityIcon"
    icon-color="var(--pk-success)"
    :status-text="statusText"
    :status-color="data?.status || 'info'"
    :ai-summary="data?.aiSummary"
    ai-lines="1"
    @ai-click="$emit('ai-click', 'quality')"
    @summary-click="$emit('ai-click', 'quality')"
  >
    <StatGrid :items="statItems" />
    <RiskList :risks="data?.risks" @risk-click="$emit('risk-click', $event)" />
  </DataCard>
</template>

<script setup>
import { computed, h } from 'vue'
import DataCard from '../common/DataCard.vue'
import RiskList from '../common/RiskList.vue'
import StatGrid from '../common/StatGrid.vue'

const QualityIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z' })
    ])
  }
}

const props = defineProps({ data: { type: Object, default: null } })
defineEmits(['ai-click', 'risk-click'])

const statusMap = { green: '正常', normal: '正常', yellow: '关注', warning: '关注', orange: '警告', red: '关键风险', critical: '关键风险' }
const statusText = computed(() => statusMap[props.data?.status] || '正常')

const statItems = computed(() => [
  { value: props.data?.di ?? '-', label: 'DI值', statusClass: '' },
  { value: props.data?.defects ?? '-', label: '缺陷', statusClass: 'warning' },
  { value: props.data?.warnings ?? '-', label: '告警', statusClass: 'warning' },
  { value: props.data?.resolveRate != null ? props.data.resolveRate + '%' : '-', label: '解决率', statusClass: 'success' }
])
</script>

<style scoped>
/* StatGrid 组件已处理所有样式 */
</style>

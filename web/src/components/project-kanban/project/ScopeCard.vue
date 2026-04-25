<template>
  <DataCard
    title="范围管理"
    :icon="ScopeIcon"
    icon-color="var(--pk-warning)"
    :status-text="statusText"
    :status-color="data?.status || 'info'"
    :ai-summary="data?.aiSummary"
    ai-lines="1"
    @ai-click="$emit('ai-click', 'scope')"
    @summary-click="$emit('ai-click', 'scope')"
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

const ScopeIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M4 6h16M4 10h16M4 14h16M4 18h16' })
    ])
  }
}

const props = defineProps({ data: { type: Object, default: null } })
defineEmits(['ai-click', 'risk-click'])

const statusMap = { green: '正常', normal: '正常', yellow: '关注', warning: '关注', orange: '警告', red: '关键风险', critical: '关键风险' }
const statusText = computed(() => statusMap[props.data?.status] || '正常')

const statItems = computed(() => [
  { value: props.data?.inProgress || 0, label: '在途需求', statusClass: '' },
  { value: props.data?.pending || 0, label: '待评审', statusClass: 'warning' },
  { value: props.data?.baseline || 0, label: '已基线', statusClass: 'success' }
])
</script>

<style scoped>
/* StatGrid 组件已处理所有样式 */
</style>

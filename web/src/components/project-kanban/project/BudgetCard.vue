<template>
  <DataCard
    title="费用执行"
    :icon="BudgetIcon"
    icon-color="#10b981"
    :status-text="statusText"
    :status-color="data?.status || 'info'"
    :ai-summary="data?.aiSummary"
    @ai-click="$emit('ai-click', 'budget')"
  >
    <div class="pk-budget__chart">
      <DonutChart :percentage="data?.executionRate ?? 0" />
      <div class="pk-budget__detail">
        <span class="pk-budget__detail-label">已执行 / 预算</span>
        <span class="pk-budget__detail-value">
          {{ data?.executed ?? 0 }}M / {{ data?.total ?? 0 }}M
        </span>
      </div>
    </div>
    <RiskList :risks="data?.risks" @risk-click="$emit('risk-click', $event)" />
  </DataCard>
</template>

<script setup>
import { computed, h } from 'vue'
import DataCard from '../common/DataCard.vue'
import DonutChart from '../common/DonutChart.vue'
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
</script>

<style scoped>
.pk-budget__chart {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 4px 0;
}
.pk-budget__detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.pk-budget__detail-label {
  font-size: 11px;
  color: var(--gray-500);
}
.pk-budget__detail-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-800);
}
</style>

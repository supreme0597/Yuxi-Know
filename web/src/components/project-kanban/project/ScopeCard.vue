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
    <div class="pk-scope__grid">
      <div class="pk-scope__item pk-scope__item--purple">
        <span class="pk-scope__value">{{ data?.inProgress || 0 }}</span>
        <span class="pk-scope__label">在途需求</span>
      </div>
      <div class="pk-scope__item pk-scope__item--orange">
        <span class="pk-scope__value">{{ data?.pending || 0 }}</span>
        <span class="pk-scope__label">待评审</span>
      </div>
      <div class="pk-scope__item pk-scope__item--blue">
        <span class="pk-scope__value">{{ data?.baseline || 0 }}</span>
        <span class="pk-scope__label">已基线</span>
      </div>
    </div>
    <RiskList :risks="data?.risks" @risk-click="$emit('risk-click', $event)" />
  </DataCard>
</template>

<script setup>
import { computed, h } from 'vue'
import DataCard from '../common/DataCard.vue'
import RiskList from '../common/RiskList.vue'

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
</script>

<style scoped>
.pk-scope__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.pk-scope__item {
  text-align: center;
  padding: 8px 4px;
  border-radius: 8px;
}
.pk-scope__item--purple { background: var(--pk-group-v3-light); }
.pk-scope__item--orange { background: var(--pk-warning-light); }
.pk-scope__item--blue { background: var(--pk-group-v2-light); }

.pk-scope__value {
  display: block;
  font-size: 18px;
  font-weight: 700;
  color: var(--gray-800);
}
.pk-scope__item--purple .pk-scope__value { color: var(--pk-group-v3); }
.pk-scope__item--orange .pk-scope__value { color: var(--pk-warning-dark); }
.pk-scope__item--blue .pk-scope__value { color: var(--pk-group-v2); }

.pk-scope__label {
  font-size: 12px;
  color: var(--gray-500);
}

@media (min-width: 1600px) {
  .pk-scope__label {
    font-size: 13px;
  }
}

@media (min-width: 1920px) {
  .pk-scope__label {
    font-size: 14px;
  }
}

@media (min-width: 2560px) {
  .pk-scope__label {
    font-size: 15px;
  }
}
</style>

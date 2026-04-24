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
    <div class="pk-quality__grid">
      <div class="pk-quality__item">
        <span class="pk-quality__value">{{ data?.di ?? '-' }}</span>
        <span class="pk-quality__label">DI值</span>
      </div>
      <div class="pk-quality__item pk-quality__item--orange">
        <span class="pk-quality__value">{{ data?.defects ?? '-' }}</span>
        <span class="pk-quality__label">缺陷</span>
      </div>
      <div class="pk-quality__item pk-quality__item--yellow">
        <span class="pk-quality__value">{{ data?.warnings ?? '-' }}</span>
        <span class="pk-quality__label">告警</span>
      </div>
      <div class="pk-quality__item pk-quality__item--green">
        <span class="pk-quality__value">{{ data?.resolveRate != null ? data.resolveRate + '%' : '-' }}</span>
        <span class="pk-quality__label">解决率</span>
      </div>
    </div>
    <RiskList :risks="data?.risks" @risk-click="$emit('risk-click', $event)" />
  </DataCard>
</template>

<script setup>
import { computed, h } from 'vue'
import DataCard from '../common/DataCard.vue'
import RiskList from '../common/RiskList.vue'

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
</script>

<style scoped>
.pk-quality__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
}
.pk-quality__item {
  text-align: center;
  padding: 6px 2px;
  background: var(--gray-50);
  border-radius: 6px;
}
.pk-quality__item--orange { background: var(--pk-warning-light); }
.pk-quality__item--yellow { background: var(--pk-warning-light); }
.pk-quality__item--green { background: var(--pk-success-light); }

.pk-quality__value {
  display: block;
  font-size: 15px;
  font-weight: 700;
  color: var(--gray-700);
}
.pk-quality__item--orange .pk-quality__value { color: var(--pk-warning-dark); }
.pk-quality__item--yellow .pk-quality__value { color: var(--pk-warning-dark); }
.pk-quality__item--green .pk-quality__value { color: var(--pk-success); }

.pk-quality__label {
  font-size: 11px;
  color: var(--gray-400);
}

@media (min-width: 1600px) {
  .pk-quality__value {
    font-size: 16px;
  }
  .pk-quality__label {
    font-size: 12px;
  }
}

@media (min-width: 1920px) {
  .pk-quality__value {
    font-size: 17px;
  }
  .pk-quality__label {
    font-size: 13px;
  }
}

@media (min-width: 2560px) {
  .pk-quality__value {
    font-size: 19px;
  }
  .pk-quality__label {
    font-size: 14px;
  }
}
</style>

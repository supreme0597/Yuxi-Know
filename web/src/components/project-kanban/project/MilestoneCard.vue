<template>
  <DataCard
    title="里程碑进度"
    :icon="CalendarIcon"
    icon-color="var(--pk-success-dark)"
    :status-text="statusText"
    :status-color="data?.statusColor || 'info'"
    :ai-summary="data?.aiSummary"
    ai-lines="1"
    @ai-click="$emit('ai-click', 'milestone')"
    @summary-click="$emit('ai-click', 'milestone')"
  >
    <template #stats>
      <StatGrid :items="statItems" />
    </template>

    <!-- 里程碑信息 -->
    <div class="pk-milestone__info">
      <span class="pk-milestone__name">{{ data?.name }}</span>
      <span class="pk-milestone__date">{{ data?.date }}</span>
    </div>

    <!-- 阶段进度条 -->
    <div class="pk-milestone__phases">
      <div
        v-for="(phase, index) in data?.phases || []"
        :key="index"
        class="pk-milestone__phase"
      >
        <div
          class="pk-milestone__phase-fill"
          :style="{ width: Math.max(phase.progress, 4) + '%', background: phaseColor(phase.status) }"
        ></div>
      </div>
    </div>
    <div class="pk-milestone__labels">
      <span v-for="(phase, index) in data?.phases || []" :key="index" class="pk-milestone__label">
        {{ phase.name }}
      </span>
    </div>

    <!-- TOP3风险 -->
    <RiskList :risks="data?.risks" @risk-click="$emit('risk-click', $event)" />
  </DataCard>
</template>

<script setup>
import { computed, h } from 'vue'
import DataCard from '../common/DataCard.vue'
import StatGrid from '../common/StatGrid.vue'
import RiskList from '../common/RiskList.vue'

// 用 render function 创建简单图标组件，避免额外依赖
const CalendarIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z' })
    ])
  }
}

const props = defineProps({
  data: { type: Object, default: null }
})

defineEmits(['ai-click', 'risk-click'])

const statusMap = { green: '正常', normal: '正常', yellow: '关注', warning: '关注', orange: '警告', red: '关键风险', critical: '关键风险' }
const statusText = computed(() => statusMap[props.data?.statusColor] || '正常')

const statItems = computed(() => {
  const phases = props.data?.phases || []
  return [
    { value: phases.length, label: '阶段总数', statusClass: '' },
    { value: phases.filter(p => p.status === 'completed').length, label: '已完成', statusClass: 'success' },
    { value: phases.filter(p => p.status === 'active').length, label: '进行中', statusClass: 'warning' },
    { value: phases.filter(p => p.status === 'pending').length, label: '待开始', statusClass: '' }
  ]
})

function phaseColor(status) {
  const map = {
    completed: 'var(--pk-chart-green)',
    active: 'var(--pk-success)',
    pending: 'var(--pk-border)'
  }
  return map[status] || 'var(--pk-border)'
}
</script>

<style scoped>
.pk-milestone__info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}
.pk-milestone__name {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-700);
}
.pk-milestone__date {
  font-size: 12px;
  color: var(--gray-400);
}

.pk-milestone__phases {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  gap: 2px;
  margin-top: 8px;
}
.pk-milestone__phase {
  flex: 1;
  height: 100%;
  background: var(--pk-page-bg);
  border-radius: 4px;
  overflow: hidden;
}
.pk-milestone__phase-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
  min-width: 4px;
}

.pk-milestone__labels {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
}
.pk-milestone__label {
  font-size: 11px;
  color: var(--gray-400);
  text-align: center;
  flex: 1;
}

@media (min-width: 1600px) {
  .pk-milestone__name {
    font-size: 14px;
  }
  .pk-milestone__date {
    font-size: 13px;
  }
  .pk-milestone__label {
    font-size: 12px;
  }
}

@media (min-width: 1920px) {
  .pk-milestone__name {
    font-size: 15px;
  }
  .pk-milestone__date {
    font-size: 14px;
  }
  .pk-milestone__label {
    font-size: 13px;
  }
}

@media (min-width: 2560px) {
  .pk-milestone__name {
    font-size: 16px;
  }
  .pk-milestone__date {
    font-size: 15px;
  }
  .pk-milestone__label {
    font-size: 14px;
  }
}
</style>

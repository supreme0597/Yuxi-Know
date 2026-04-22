<template>
  <div class="pk-donut" :style="{ width: size + 'px', height: size + 'px' }">
    <svg :width="size" :height="size" class="pk-donut__svg">
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        stroke="#e5e7eb"
        :stroke-width="strokeWidth"
        fill="none"
      />
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        :stroke="ringColor"
        :stroke-width="strokeWidth"
        fill="none"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
        stroke-linecap="round"
        class="pk-donut__progress"
      />
    </svg>
    <div class="pk-donut__center">
      <span class="pk-donut__value">{{ displayValue }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  percentage: { type: Number, default: 0 },
  size: { type: Number, default: 56 },
  strokeWidth: { type: Number, default: 4 },
  color: { type: String, default: '' },
  label: { type: String, default: '' }
})

const radius = computed(() => (props.size - props.strokeWidth * 2) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const offset = computed(() => circumference.value - (props.percentage / 100) * circumference.value)
const displayValue = computed(() => props.label || `${props.percentage}%`)

const ringColor = computed(() => {
  if (props.color) return props.color
  if (props.percentage >= 80) return '#059669'
  if (props.percentage >= 50) return '#d97706'
  return '#dc2626'
})
</script>

<style scoped>
.pk-donut {
  position: relative;
  flex-shrink: 0;
}
.pk-donut__svg {
  transform: rotate(-90deg);
}
.pk-donut__progress {
  transition: stroke-dashoffset 0.6s ease;
}
.pk-donut__center {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pk-donut__value {
  font-size: 12px;
  font-weight: 700;
  color: var(--gray-700);
}
</style>

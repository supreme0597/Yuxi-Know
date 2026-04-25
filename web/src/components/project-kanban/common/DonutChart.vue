<template>
  <div
    class="pk-donut"
    :style="{ '--pk-donut-size': size + 'px' }"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <svg :viewBox="'0 0 ' + size + ' ' + size" class="pk-donut__svg">
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        stroke="var(--pk-border)"
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
    <!-- 悬浮气泡 -->
    <Transition name="pk-donut-tooltip">
      <div v-if="tooltip && hovered" class="pk-donut__tooltip">
        <span class="pk-donut__tooltip-text">{{ tooltip }}</span>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  percentage: { type: Number, default: 0 },
  size: { type: Number, default: 56 },
  strokeWidth: { type: Number, default: 4 },
  color: { type: String, default: '' },
  label: { type: String, default: '' },
  tooltip: { type: String, default: '' }
})

const hovered = ref(false)

const radius = computed(() => (props.size - props.strokeWidth * 2) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const offset = computed(() => circumference.value - (props.percentage / 100) * circumference.value)
const displayValue = computed(() => props.label || `${props.percentage}%`)

const ringColor = computed(() => {
  if (props.color) return props.color
  if (props.percentage >= 80) return 'var(--pk-chart-green)'
  if (props.percentage >= 50) return 'var(--pk-chart-orange)'
  return 'var(--pk-chart-red)'
})
</script>

<style scoped>
.pk-donut {
  position: relative;
  flex-shrink: 0;
  width: var(--pk-donut-size);
  height: var(--pk-donut-size);
}
.pk-donut__svg {
  width: var(--pk-donut-size);
  height: var(--pk-donut-size);
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
  font-size: 10px;
  font-weight: 700;
  color: var(--pk-text);
}

/* 悬浮气泡 */
.pk-donut__tooltip {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
  pointer-events: none;
}
.pk-donut__tooltip-text {
  display: block;
  white-space: nowrap;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  color: var(--gray-0);
  background: var(--gray-800);
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}
.pk-donut__tooltip-text::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: var(--gray-800);
}

/* tooltip 过渡 */
.pk-donut-tooltip-enter-active,
.pk-donut-tooltip-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.pk-donut-tooltip-enter-from,
.pk-donut-tooltip-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(4px);
}

@media (min-width: 1600px) {
  .pk-donut__value {
    font-size: 11px;
  }
}

@media (min-width: 1920px) {
  .pk-donut__value {
    font-size: 12px;
  }
}

@media (min-width: 2560px) {
  .pk-donut__value {
    font-size: 12px;
  }
}
</style>

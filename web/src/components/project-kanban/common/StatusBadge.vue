<template>
  <span class="pk-badge" :class="`pk-badge--${statusClass}`">
    <span v-if="showDot" class="pk-badge__dot"></span>
    <span class="pk-badge__text">{{ text }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
  text: { type: String, default: '' },
  showDot: { type: Boolean, default: true }
})

const statusClass = computed(() => {
  const map = {
    green: 'success',
    normal: 'success',
    success: 'success',
    yellow: 'warning',
    warning: 'warning',
    orange: 'warning',
    red: 'danger',
    critical: 'danger',
    danger: 'danger',
    info: 'info'
  }
  return map[props.status] || 'info'
})
</script>

<style scoped>
.pk-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}
.pk-badge__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}

.pk-badge--success { background: var(--pk-success-light); color: var(--pk-success-dark); }
.pk-badge--success .pk-badge__dot { background: var(--pk-success-dark); }
.pk-badge--warning { background: var(--pk-warning-light); color: var(--pk-warning-dark); }
.pk-badge--warning .pk-badge__dot { background: var(--pk-warning-dark); }
.pk-badge--danger { background: var(--pk-danger-light); color: var(--pk-danger-dark); }
.pk-badge--danger .pk-badge__dot { background: var(--pk-danger-dark); }
.pk-badge--info { background: var(--pk-success-light); color: var(--pk-success-dark); }
.pk-badge--info .pk-badge__dot { background: var(--pk-success-dark); }
</style>

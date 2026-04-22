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
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}
.pk-badge__dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}

.pk-badge--success { background: #d1fae5; color: #059669; }
.pk-badge--success .pk-badge__dot { background: #059669; }
.pk-badge--warning { background: #fef3c7; color: #d97706; }
.pk-badge--warning .pk-badge__dot { background: #d97706; }
.pk-badge--danger { background: #fef2f2; color: #dc2626; }
.pk-badge--danger .pk-badge__dot { background: #dc2626; }
.pk-badge--info { background: #d1fae5; color: #059669; }
.pk-badge--info .pk-badge__dot { background: #059669; }
</style>

<template>
  <div class="pk-stat-grid">
    <template v-for="(item, index) in items" :key="index">
      <div class="pk-stat-item">
        <span class="pk-stat-item__value" :class="item.statusClass">{{ item.value }}</span>
        <span class="pk-stat-item__label">{{ item.label }}</span>
      </div>
      <div v-if="index < items.length - 1" class="pk-stat-divider"></div>
    </template>
  </div>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    required: true,
    validator(val) {
      return val.every(i => 'value' in i && 'label' in i)
    }
  }
})
</script>

<style scoped>
.pk-stat-grid {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 8px 0;
}
.pk-stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.pk-stat-item__value {
  font-size: 16px;
  font-weight: 700;
  color: var(--gray-800);
}
.pk-stat-item__value.success { color: #059669; }
.pk-stat-item__value.warning { color: #d97706; }
.pk-stat-item__value.danger { color: #dc2626; }

.pk-stat-item__label {
  font-size: 11px;
  color: var(--gray-500);
}
.pk-stat-divider {
  width: 1px;
  height: 24px;
  background: var(--gray-200);
  flex-shrink: 0;
}
</style>

<template>
  <div class="pk-stat-grid">
    <template v-for="(item, index) in items" :key="index">
      <div
        class="pk-stat-item"
        :class="{ 'pk-stat-item--clickable': item.clickable }"
        @click="item.clickable && $emit('item-click', item)"
      >
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

defineEmits(['item-click'])
</script>

<style scoped>
.pk-stat-grid {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 4px 0;
}
.pk-stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.pk-stat-item--clickable {
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
}
.pk-stat-item--clickable:hover {
  background: rgba(99, 102, 241, 0.06);
}
.pk-stat-item__value {
  font-size: 14px;
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

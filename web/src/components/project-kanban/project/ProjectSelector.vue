<template>
  <div class="pk-selector">
    <label class="pk-selector__label">选择子项目：</label>
    <a-select
      :value="modelValue"
      :options="options"
      placeholder="请选择项目"
      class="pk-selector__select"
      @change="$emit('update:modelValue', $event)"
    />
    <span v-if="info" class="pk-selector__info">{{ info }}</span>

    <!-- 甜点工具栏 -->
    <div class="pk-sweet-toolbar">
      <button class="pk-sweet-btn" @click="$emit('tool-action', 'daily')">
        <ClipboardList :size="14" />
        <span>日报</span>
      </button>
      <button class="pk-sweet-btn" @click="$emit('tool-action', 'weekly')">
        <BarChart3 :size="14" />
        <span>周报</span>
      </button>
      <button class="pk-sweet-btn" @click="$emit('tool-action', 'review')">
        <RefreshCw :size="14" />
        <span>复盘</span>
      </button>
      <button class="pk-sweet-btn" @click="$emit('tool-action', 'aar')">
        <FileText :size="14" />
        <span>AAR</span>
      </button>
      <button class="pk-sweet-btn" @click="$emit('tool-action', 'sandbox')">
        <Target :size="14" />
        <span>风险沙盘</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ClipboardList, BarChart3, RefreshCw, FileText, Target } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: String, default: '' },
  projects: { type: Array, default: () => [] },
  info: { type: String, default: '' }
})

defineEmits(['update:modelValue', 'tool-action'])

const options = computed(() =>
  props.projects.map(p => ({ value: p.id, label: p.name }))
)
</script>

<style scoped>
.pk-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--gray-0);
  border-radius: 12px;
  border: 1px solid var(--gray-200);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.pk-selector__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--gray-700);
  white-space: nowrap;
}
.pk-selector__select {
  min-width: 200px;
}
.pk-selector__info {
  font-size: 11px;
  color: var(--gray-400);
}

.pk-sweet-toolbar {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
}
.pk-sweet-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 11px;
  color: var(--gray-600);
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.pk-sweet-btn:hover {
  color: var(--main-color);
  border-color: var(--main-200);
  background: var(--main-50);
}
</style>

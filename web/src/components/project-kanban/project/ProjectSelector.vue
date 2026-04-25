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
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.10), 0 8px 28px rgba(0, 0, 0, 0.07);
}
.pk-selector__label {
  font-size: 14px;
  font-weight: 500;
  color: var(--gray-700);
  white-space: nowrap;
}
.pk-selector__select {
  min-width: 200px;
}
.pk-selector__info {
  font-size: 12px;
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
  font-size: 12px;
  color: var(--gray-600);
  background: var(--gray-50);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  border: none;
}
.pk-sweet-btn:hover {
  color: var(--pk-accent);
  background: var(--pk-accent-light);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
}

@media (min-width: 1600px) {
  .pk-selector {
    padding: 14px 18px;
    gap: 14px;
  }
  .pk-selector__label {
    font-size: 15px;
  }
  .pk-selector__info {
    font-size: 13px;
  }
  .pk-sweet-toolbar {
    gap: 7px;
  }
  .pk-sweet-btn {
    padding: 5px 12px;
    font-size: 13px;
    gap: 5px;
  }
}

@media (min-width: 1920px) {
  .pk-selector {
    padding: 16px 20px;
    gap: 16px;
  }
  .pk-selector__label {
    font-size: 16px;
  }
  .pk-selector__info {
    font-size: 14px;
  }
  .pk-sweet-toolbar {
    gap: 8px;
  }
  .pk-sweet-btn {
    padding: 6px 14px;
    font-size: 14px;
    gap: 5px;
  }
}

@media (min-width: 2560px) {
  .pk-selector {
    padding: 18px 24px;
    gap: 18px;
  }
  .pk-selector__label {
    font-size: 17px;
  }
  .pk-selector__info {
    font-size: 15px;
  }
  .pk-sweet-toolbar {
    gap: 9px;
  }
  .pk-sweet-btn {
    padding: 6px 16px;
    font-size: 15px;
    gap: 6px;
  }
}
</style>

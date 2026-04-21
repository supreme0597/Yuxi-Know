<template>
  <div class="pk-sub" @click="$emit('click', project)">
    <!-- 头部：项目ID + 状态徽章 + 进度 -->
    <div class="pk-sub__header">
      <span class="pk-sub__id">{{ project.id }}</span>
      <StatusBadge :status="milestoneStatus" :text="milestoneText" />
      <span class="pk-sub__progress" @click.stop="$emit('progress-click', project)">{{ project.progress }}%</span>
    </div>

    <!-- 进度条 -->
    <div class="pk-sub__bar">
      <div class="pk-sub__bar-fill" :style="{ width: Math.max(project.progress, 2) + '%' }" />
    </div>

    <!-- AI 一句话总结 -->
    <div v-if="project.aiSummary" class="pk-sub__ai" @click.stop="$emit('ai-click', project)">
      <span class="pk-sub__ai-spark">✨</span>
      <span>{{ project.aiSummary }}</span>
    </div>

    <!-- 5维度风险标签 -->
    <div class="pk-sub__dims">
      <span
        v-for="dim in dimensions"
        :key="dim.key"
        class="pk-sub__dim"
        :class="`pk-sub__dim--${dim.status}`"
        @click.stop="$emit('dim-click', { dim, project })"
      >
        {{ dim.label }}
      </span>
    </div>

    <!-- 里程碑时间轴 -->
    <div v-if="phases.length" class="pk-sub__timeline" @click.stop="$emit('milestone-click', project)">
      <div
        v-for="(phase, i) in phases"
        :key="i"
        class="pk-sub__phase"
        :class="`pk-sub__phase--${phase.status}`"
      >
        <div class="pk-sub__phase-dot" />
        <span class="pk-sub__phase-label">{{ phase.name }}</span>
        <div v-if="i < phases.length - 1" class="pk-sub__phase-line" :class="{ 'pk-sub__phase-line--done': phase.status === 'completed' }" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import StatusBadge from '../common/StatusBadge.vue'
import { getRiskDimensions } from '../data/groupData'

const props = defineProps({
  project: { type: Object, required: true }
})

defineEmits(['click', 'ai-click', 'dim-click', 'progress-click', 'milestone-click'])

const dimensions = computed(() => getRiskDimensions(props.project))

const phases = computed(() => props.project.milestone?.phases || [])

const milestoneStatus = computed(() => {
  const s = props.project.milestone?.statusColor || props.project.milestone?.status || 'green'
  return s
})

const milestoneText = computed(() => props.project.milestone?.status || '')
</script>

<style scoped>
.pk-sub {
  padding: 14px 16px;
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.pk-sub:hover {
  border-color: var(--main-300);
  background: #fafbff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

/* Header */
.pk-sub__header {
  display: flex;
  align-items: center;
  gap: 6px;
}
.pk-sub__id {
  font-size: 13px;
  font-weight: 700;
  color: var(--gray-800);
  font-family: 'SF Mono', 'Fira Code', monospace;
  letter-spacing: -0.3px;
}
.pk-sub__progress {
  margin-left: auto;
  font-size: 12px;
  font-weight: 700;
  color: var(--main-600);
  cursor: pointer;
  transition: color 0.15s ease;
}
.pk-sub__progress:hover {
  color: var(--main-500);
}

/* Progress bar */
.pk-sub__bar {
  height: 5px;
  background: var(--gray-100);
  border-radius: 3px;
  overflow: hidden;
}
.pk-sub__bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--main-400), var(--main-600));
  border-radius: 3px;
  transition: width 0.4s ease;
}

/* AI summary */
.pk-sub__ai {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  font-size: 11px;
  color: var(--gray-600);
  line-height: 1.5;
  padding: 6px 8px;
  background: linear-gradient(135deg, #f8faff, #faf5ff);
  border-radius: 6px;
}
.pk-sub__ai-spark {
  flex-shrink: 0;
  font-size: 11px;
}

/* Dimension tags */
.pk-sub__dims {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.pk-sub__dim {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  transition: transform 0.1s ease, box-shadow 0.1s ease;
  cursor: pointer;
}
.pk-sub__dim:hover {
  transform: scale(1.05);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
.pk-sub__dim--normal {
  background: #d1fae5;
  color: #059669;
}
.pk-sub__dim--warning {
  background: #fef3c7;
  color: #d97706;
}
.pk-sub__dim--danger {
  background: #fef2f2;
  color: #dc2626;
}

/* Milestone timeline */
.pk-sub__timeline {
  display: flex;
  align-items: center;
  gap: 0;
  margin-top: 2px;
  padding-top: 8px;
  border-top: 1px solid var(--gray-100);
  overflow-x: auto;
  cursor: pointer;
  transition: opacity 0.15s ease;
}
.pk-sub__timeline:hover {
  opacity: 0.8;
}
.pk-sub__phase {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  position: relative;
}
.pk-sub__phase-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pk-sub__phase--completed .pk-sub__phase-dot {
  background: #10b981;
}
.pk-sub__phase--active .pk-sub__phase-dot {
  background: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25);
}
.pk-sub__phase--pending .pk-sub__phase-dot {
  background: var(--gray-300);
}
.pk-sub__phase-label {
  font-size: 10px;
  color: var(--gray-500);
  margin-left: 4px;
  white-space: nowrap;
}
.pk-sub__phase-line {
  width: 18px;
  height: 2px;
  background: var(--gray-200);
  margin: 0 3px;
  flex-shrink: 0;
}
.pk-sub__phase-line--done {
  background: #10b981;
}
</style>

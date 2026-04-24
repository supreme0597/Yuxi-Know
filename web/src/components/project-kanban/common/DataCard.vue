<template>
  <div class="pk-card" :class="{ 'pk-card--wide': wide, 'pk-card--clickable': clickable }">
    <div class="pk-card__content">
      <!-- Header: 图标 + 标题 + 状态徽章 -->
      <div v-if="$slots.header || title" class="pk-card__header">
        <slot name="header">
          <span v-if="icon" class="pk-card__icon" :style="{ color: iconColor }">
            <component :is="icon" :size="16" :stroke-width="2" />
          </span>
          <span class="pk-card__title">{{ title }}</span>
          <StatusBadge
            v-if="statusText"
            :status="statusColor"
            :text="statusText"
            class="pk-card__status"
          />
        </slot>
      </div>

      <!-- 统计区 (可选) -->
      <div v-if="$slots.stats" class="pk-card__stats">
        <slot name="stats" />
      </div>

      <!-- 副标题/描述 (可选) -->
      <p v-if="description" class="pk-card__desc">{{ description }}</p>

      <!-- AI 一句话总结 (可选) — 点击打开带焦点的分析，与 AI 按钮区分 -->
      <div
        v-if="aiSummary"
        class="pk-card__ai-summary"
        :class="`pk-card__ai-summary--${aiLines}l`"
        :title="aiSummary"
        @click.stop="$emit('summary-click')"
      >
        <span class="pk-card__ai-spark">✨</span>
        <span class="pk-card__ai-text" :class="`pk-card__ai-text--${aiLines}l`">{{ aiSummary }}</span>
      </div>
      <div v-else-if="$slots.aiSummary" class="pk-card__ai-summary" @click.stop="$emit('summary-click')">
        <slot name="aiSummary" />
      </div>

      <!-- 主要内容区 (可选) -->
      <div v-if="$slots.default" class="pk-card__body">
        <slot />
      </div>
    </div>

    <!-- Footer: AI按钮 或 自定义footer -->
    <div v-if="showAI || $slots.footer" class="pk-card__footer">
      <slot name="footer">
        <AIButton :title="title" @click="$emit('ai-click')" />
      </slot>
    </div>
  </div>
</template>

<script setup>
import AIButton from './AIButton.vue'
import StatusBadge from './StatusBadge.vue'

defineProps({
  title: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
  iconColor: { type: String, default: 'var(--pk-accent)' },
  statusText: { type: String, default: '' },
  statusColor: { type: String, default: 'info' },
  description: { type: String, default: '' },
  aiSummary: { type: String, default: '' },
  aiLines: { type: Number, default: 2 },
  wide: { type: Boolean, default: false },
  clickable: { type: Boolean, default: false },
  showAI: { type: Boolean, default: true }
})

defineEmits(['ai-click', 'summary-click'])
</script>

<style scoped>
.pk-card {
  position: relative;
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
  display: flex;
  flex-direction: column;
}
.pk-card:hover {
  border-color: var(--gray-300);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.pk-card--clickable {
  cursor: pointer;
}
.pk-card--wide {
  grid-column: 1 / -1;
}

.pk-card__content {
  padding: 12px 14px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pk-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 24px;
}
.pk-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.pk-card__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-800);
}
.pk-card__status {
  margin-left: auto;
}

.pk-card__stats {
  padding: 4px 0;
}

.pk-card__desc {
  font-size: 13px;
  color: var(--gray-600);
  margin: 0;
  line-height: 1.5;
}

.pk-card__ai-summary {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 4px 8px;
  background: linear-gradient(135deg, var(--pk-accent-light), var(--pk-group-v2-light));
  border-radius: 6px;
  font-size: 12px;
  color: var(--pk-text);
  line-height: 1.5;
  cursor: pointer;
  transition: background 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
  box-sizing: content-box;
}
.pk-card__ai-summary--1l { height: calc(1 * 1.5em); }
.pk-card__ai-summary--2l { height: calc(2 * 1.5em); }
.pk-card__ai-summary:hover {
  background: linear-gradient(135deg, var(--pk-group-v3-light), var(--pk-group-v2-light));
  box-shadow: 0 0 0 1px var(--pk-accent-glow);
}
.pk-card__ai-spark {
  flex-shrink: 0;
  font-size: 12px;
}
.pk-card__ai-text {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.5;
}
.pk-card__ai-text--1l { -webkit-line-clamp: 1; }
.pk-card__ai-text--2l { -webkit-line-clamp: 2; }

.pk-card__body {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.pk-card__footer {
  display: flex;
  justify-content: flex-end;
  padding: 8px 16px 12px;
}

@media (min-width: 1600px) {
  .pk-card__content {
    padding: 14px 16px;
    gap: 8px;
  }
  .pk-card__title {
    font-size: 15px;
  }
  .pk-card__desc {
    font-size: 14px;
  }
  .pk-card__ai-summary {
    font-size: 13px;
    padding: 6px 10px;
  }
  .pk-card__ai-summary--1l { height: calc(1 * 1.5em); }
  .pk-card__ai-summary--2l { height: calc(2 * 1.5em); }
  .pk-card__footer {
    padding: 10px 18px 14px;
  }
}

@media (min-width: 1920px) {
  .pk-card__content {
    padding: 16px 18px;
    gap: 10px;
  }
  .pk-card__title {
    font-size: 16px;
  }
  .pk-card__desc {
    font-size: 15px;
  }
  .pk-card__ai-summary {
    font-size: 14px;
    padding: 6px 10px;
  }
  .pk-card__ai-summary--1l { height: calc(1 * 1.5em); }
  .pk-card__ai-summary--2l { height: calc(2 * 1.5em); }
  .pk-card__footer {
    padding: 10px 20px 14px;
  }
}

@media (min-width: 2560px) {
  .pk-card__content {
    padding: 18px 20px;
    gap: 12px;
  }
  .pk-card__title {
    font-size: 17px;
  }
  .pk-card__desc {
    font-size: 16px;
  }
  .pk-card__ai-summary {
    font-size: 15px;
    padding: 8px 12px;
  }
  .pk-card__ai-summary--1l { height: calc(1 * 1.5em); }
  .pk-card__ai-summary--2l { height: calc(2 * 1.5em); }
  .pk-card__footer {
    padding: 12px 22px 16px;
  }
}
</style>

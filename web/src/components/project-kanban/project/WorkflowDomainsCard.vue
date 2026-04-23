<template>
  <div class="pk-domains">
    <div
      v-for="(meta, key) in workflowDomainMap"
      :key="key"
      class="pk-domain"
      @click="$emit('domain-click', key)"
    >
      <div class="pk-domain__header">
        <span class="pk-domain__dot" :class="`pk-domain__dot--${domainStatus(key)}`"></span>
        <span class="pk-domain__tag">{{ meta.tag }}</span>
        <span class="pk-domain__title">{{ meta.label }}</span>
        <span
          class="pk-domain__status"
          :class="`pk-domain__status--${domainStatus(key)}`"
        >
          {{ domainLabel(key) }}
        </span>
      </div>
      <p class="pk-domain__summary" v-html="domainSummary(key)"></p>
      <div class="pk-domain__risks">
        <div
          v-for="(risk, i) in topRisks(key)"
          :key="i"
          class="pk-domain__risk"
          :class="`pk-domain__risk--${risk.level}`"
          @click.stop="$emit('risk-click', { domain: key, riskIndex: i })"
        >
          <span class="pk-domain__risk-dot"></span>
          <span>{{ risk.text || risk.title }}</span>
        </div>
      </div>
      <div class="pk-domain__footer">
        <AIButton :title="meta.label" @click.stop="$emit('ai-click', key)" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AIButton from '../common/AIButton.vue'

/** 五领域 workflow key 映射 */
const workflowDomainMap = {
  design: { label: '设计领域', tag: 'SE' },
  dev: { label: '开发领域', tag: 'DEV' },
  build: { label: '构建领域', tag: 'BUILD' },
  test: { label: '测试领域', tag: 'QA' },
  release: { label: '发布领域', tag: 'REL' }
}

const props = defineProps({
  data: { type: Object, default: null }
})

defineEmits(['domain-click', 'ai-click', 'risk-click'])

function domainStatus(key) {
  return props.data?.[key]?.status || 'green'
}

function domainLabel(key) {
  const status = domainStatus(key)
  const map = { green: '正常', warning: '关注', critical: '风险', yellow: '关注', red: '风险' }
  return map[status] || '正常'
}

function domainSummary(key) {
  return props.data?.[key]?.aiSummary || '-'
}

function topRisks(key) {
  const risks = props.data?.[key]?.risks || []
  return risks.slice(0, 3)
}
</script>

<style scoped>
.pk-domains {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.pk-domain {
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pk-domain:hover {
  border-color: var(--main-200);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.pk-domain__header {
  display: flex;
  align-items: center;
  gap: 6px;
}
.pk-domain__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pk-domain__dot--green { background: #10b981; }
.pk-domain__dot--yellow, .pk-domain__dot--warning { background: #f59e0b; }
.pk-domain__dot--red, .pk-domain__dot--critical { background: #ef4444; }

.pk-domain__tag {
  font-size: 11px;
  font-weight: 600;
  color: var(--gray-400);
  padding: 1px 4px;
  background: var(--gray-100);
  border-radius: 3px;
}
.pk-domain__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-800);
}
.pk-domain__status {
  margin-left: auto;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 3px;
  font-weight: 500;
}
.pk-domain__status--green { background: #d1fae5; color: #059669; }
.pk-domain__status--yellow,
.pk-domain__status--warning { background: #fef3c7; color: #d97706; }
.pk-domain__status--red,
.pk-domain__status--critical { background: #fef2f2; color: #dc2626; }

.pk-domain__summary {
  font-size: 13px;
  color: var(--gray-600);
  line-height: 1.5;
  margin: 0;
}

.pk-domain__risks {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.pk-domain__risk {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--gray-600);
  cursor: pointer;
  transition: color 0.15s;
}
.pk-domain__risk:hover {
  color: #6366f1;
}
.pk-domain__risk-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pk-domain__risk--critical .pk-domain__risk-dot,
.pk-domain__risk--danger .pk-domain__risk-dot { background: #dc2626; }
.pk-domain__risk--warning .pk-domain__risk-dot { background: #d97706; }
.pk-domain__risk--normal .pk-domain__risk-dot { background: #059669; }

.pk-domain__footer {
  display: flex;
  justify-content: flex-end;
  margin-top: auto;
}

@media (max-width: 1200px) {
  .pk-domains {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 768px) {
  .pk-domains {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1600px) {
  .pk-domain__tag {
    font-size: 12px;
  }
  .pk-domain__title {
    font-size: 15px;
  }
  .pk-domain__status {
    font-size: 12px;
  }
  .pk-domain__summary {
    font-size: 14px;
  }
  .pk-domain__risk {
    font-size: 12px;
  }
}

@media (min-width: 1920px) {
  .pk-domain__tag {
    font-size: 13px;
  }
  .pk-domain__title {
    font-size: 16px;
  }
  .pk-domain__status {
    font-size: 13px;
  }
  .pk-domain__summary {
    font-size: 15px;
  }
  .pk-domain__risk {
    font-size: 13px;
  }
}

@media (min-width: 2560px) {
  .pk-domain__tag {
    font-size: 13px;
  }
  .pk-domain__title {
    font-size: 17px;
  }
  .pk-domain__status {
    font-size: 13px;
  }
  .pk-domain__summary {
    font-size: 16px;
  }
  .pk-domain__risk {
    font-size: 14px;
  }
}
</style>

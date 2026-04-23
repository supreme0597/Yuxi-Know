<template>
  <DataCard
    title="可信管理"
    :icon="TrustIcon"
    icon-color="#6366f1"
    :status-text="statusText"
    :status-color="trustStatusColor"
    :ai-summary="data?.aiSummary ? `${data.aiSummary}` : ''"
    wide
    @ai-click="$emit('ai-click', 'trust')"
    @summary-click="$emit('ai-click', 'trust')"
  >
    <!-- 9宫格 -->
    <div class="pk-trust__grid">
      <div
        v-for="(item, key) in trustItems"
        :key="key"
        class="pk-trust__subcard"
        @click="$emit('subcard-click', { key, label: item.label })"
      >
        <div class="pk-trust__subcard-header">
          <span class="pk-trust__subcard-title">{{ item.label }}</span>
          <span class="pk-trust__subcard-dot" :class="`pk-trust__subcard-dot--${item.level}`"></span>
        </div>
        <div class="pk-trust__metric">
          <span class="pk-trust__metric-ok">{{ item.ok }}</span>
          <span class="pk-trust__metric-sep">/</span>
          <span class="pk-trust__metric-total">{{ item.total }}</span>
        </div>
        <div class="pk-trust__progress-bar">
          <div
            class="pk-trust__progress-fill"
            :class="`pk-trust__progress-fill--${item.level}`"
            :style="{ width: item.percentage + '%' }"
          ></div>
        </div>
      </div>
    </div>

    <!-- TOP3风险 -->
    <RiskList :risks="data?.risks" @risk-click="$emit('risk-click', $event)" />
  </DataCard>
</template>

<script setup>
import { computed, h } from 'vue'
import DataCard from '../common/DataCard.vue'
import RiskList from '../common/RiskList.vue'

/** 可信管理子卡片 key 映射 */
const trustCategoryMap = {
  productDefinition: { label: '产品定义' },
  design: { label: '设计' },
  coding: { label: '编码' },
  build: { label: '构建' },
  testing: { label: '测试' },
  e2eProtection: { label: 'E2E完整性保护' },
  openSource: { label: '开源及第三方软件' },
  vulnerability: { label: '漏洞管理' },
  lifecycle: { label: '生命周期' }
}

const TrustIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z' })
    ])
  }
}

const props = defineProps({
  data: { type: Object, default: null }
})

defineEmits(['ai-click', 'subcard-click', 'risk-click'])

const trustStatusColor = computed(() => {
  const score = props.data?.overallScore || 0
  if (score >= 80) return 'green'
  if (score >= 60) return 'yellow'
  return 'red'
})

const statusText = computed(() => {
  const score = props.data?.overallScore || 0
  if (score >= 80) return '正常'
  if (score >= 60) return '关注'
  return '关键风险'
})

const trustItems = computed(() => {
  if (!props.data) return {}
  const result = {}
  for (const [key, meta] of Object.entries(trustCategoryMap)) {
    const detail = props.data[key]
    if (detail) {
      const pct = detail.total > 0 ? Math.round((detail.ok / detail.total) * 100) : 0
      result[key] = {
        label: meta.label,
        ok: detail.ok,
        total: detail.total,
        percentage: pct,
        level: pct >= 80 ? 'green' : pct >= 50 ? 'yellow' : 'red'
      }
    }
  }
  return result
})
</script>

<style scoped>
.pk-trust__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.pk-trust__subcard {
  padding: 10px;
  background: var(--gray-25);
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.pk-trust__subcard:hover {
  border-color: var(--main-200);
  background: var(--main-50);
}

.pk-trust__subcard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.pk-trust__subcard-title {
  font-size: 12px;
  font-weight: 500;
  color: var(--gray-700);
}
.pk-trust__subcard-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.pk-trust__subcard-dot--green { background: #10b981; }
.pk-trust__subcard-dot--yellow { background: #f59e0b; }
.pk-trust__subcard-dot--red { background: #ef4444; }

.pk-trust__metric {
  display: flex;
  align-items: baseline;
  gap: 2px;
  margin-bottom: 6px;
}
.pk-trust__metric-ok {
  font-size: 17px;
  font-weight: 700;
  color: var(--gray-800);
}
.pk-trust__metric-sep {
  font-size: 13px;
  color: var(--gray-400);
}
.pk-trust__metric-total {
  font-size: 13px;
  color: var(--gray-500);
}

.pk-trust__progress-bar {
  height: 3px;
  background: var(--gray-200);
  border-radius: 2px;
  overflow: hidden;
}
.pk-trust__progress-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}
.pk-trust__progress-fill--green { background: #10b981; }
.pk-trust__progress-fill--yellow { background: #f59e0b; }
.pk-trust__progress-fill--red { background: #ef4444; }

@media (min-width: 1600px) {
  .pk-trust__grid {
    gap: 10px;
  }
  .pk-trust__subcard {
    padding: 12px;
  }
  .pk-trust__subcard-title {
    font-size: 13px;
  }
  .pk-trust__subcard-header {
    margin-bottom: 8px;
  }
  .pk-trust__metric {
    margin-bottom: 8px;
  }
  .pk-trust__metric-ok {
    font-size: 18px;
  }
  .pk-trust__metric-sep,
  .pk-trust__metric-total {
    font-size: 14px;
  }
}

@media (min-width: 1920px) {
  .pk-trust__grid {
    gap: 12px;
  }
  .pk-trust__subcard {
    padding: 14px;
  }
  .pk-trust__subcard-title {
    font-size: 14px;
  }
  .pk-trust__subcard-header {
    margin-bottom: 10px;
  }
  .pk-trust__metric {
    margin-bottom: 10px;
  }
  .pk-trust__metric-ok {
    font-size: 19px;
  }
  .pk-trust__metric-sep,
  .pk-trust__metric-total {
    font-size: 15px;
  }
}

@media (min-width: 2560px) {
  .pk-trust__grid {
    gap: 14px;
  }
  .pk-trust__subcard {
    padding: 16px;
  }
  .pk-trust__subcard-title {
    font-size: 15px;
  }
  .pk-trust__subcard-header {
    margin-bottom: 12px;
  }
  .pk-trust__metric {
    margin-bottom: 12px;
  }
  .pk-trust__metric-ok {
    font-size: 21px;
  }
  .pk-trust__metric-sep,
  .pk-trust__metric-total {
    font-size: 16px;
  }
}
</style>

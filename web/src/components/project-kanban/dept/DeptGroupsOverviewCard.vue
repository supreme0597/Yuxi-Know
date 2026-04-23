<template>
  <DataCard
    title="项目群综合风险"
    :icon="ShieldIcon"
    icon-color="#6366f1"
    wide
    :status-text="statusText"
    :status-color="statusColor"
    :show-ai="false"
  >
    <!-- 上行：四维度卡片（左边框 + 浅灰背景） -->
    <div v-if="dimensions.length" class="pk-overview-dims">
      <div
        v-for="dim in dimensions"
        :key="dim.key"
        class="pk-dim-card"
        :class="`pk-dim-card--${dim.statusType}`"
        @click="$emit('dim-click', dim)"
      >
        <div class="pk-dim-card__header">
          <span class="pk-dim-card__icon">{{ dim.icon }}</span>
          <span class="pk-dim-card__title">{{ dim.label }}</span>
          <span class="pk-dim-card__dot" :class="`pk-dim-card__dot--${dim.statusType}`" />
        </div>
        <div class="pk-dim-card__stats">
          <div v-for="stat in dim.stats" :key="stat.label" class="pk-dim-card__stat">
            <span class="pk-dim-card__stat-value" :class="stat.class">{{ stat.value }}</span>
            <span class="pk-dim-card__stat-label">{{ stat.label }}</span>
          </div>
        </div>
        <div v-if="dim.sentence" class="pk-dim-card__sentence" :class="`pk-dim-card__sentence--${dim.statusType}`">
          <span class="pk-dim-card__sentence-dot" />
          {{ dim.sentence }}
        </div>
      </div>
    </div>

    <!-- 下行：三个项目群风险卡片（阴影渐变卡片） -->
    <div v-if="groupCards.length" class="pk-overview-groups">
      <div
        v-for="gc in groupCards"
        :key="gc.name"
        class="pk-group-card"
        :class="`pk-group-card--${gc.status}`"
        @click="$emit('group-click', gc)"
      >
        <!-- 头部：项目群名称 -->
        <div class="pk-group-card__header">
          <span class="pk-group-card__tag" :class="`pk-group-card__tag--${gc.status}`">{{ gc.name }}</span>
        </div>

        <!-- 风险列表（部门级：数字序号 + 紧凑描述，无标题无分割线） -->
        <div v-if="gc.risks && gc.risks.length" class="pk-group-risks">
          <div
            v-for="(risk, i) in formatRisks(gc.risks).slice(0, 3)"
            :key="i"
            class="pk-group-risk-item"
            :class="`pk-group-risk-item--${risk.level}`"
            @click.stop="$emit('risk-click', risk, gc)"
          >
            <span class="pk-group-risk-rank">{{ i + 1 }}</span>
            <span class="pk-group-risk-text">{{ risk.text }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：猜你想问 + AI按钮（与设计稿 card-footer 一致） -->
    <template #footer>
      <div class="pk-overview-footer">
        <div class="pk-overview-intent">
          <span
            v-for="(q, i) in quickQuestions"
            :key="i"
            class="pk-overview-intent__tag"
            @click="$emit('question-click', q)"
          >
            {{ q }}
          </span>
        </div>
        <AIButton title="项目群综合风险" @click="$emit('ai-click', 'groups-overview')" />
      </div>
    </template>
  </DataCard>
</template>

<script setup>
import { computed, h } from 'vue'
import DataCard from '../common/DataCard.vue'
import AIButton from '../common/AIButton.vue'

const props = defineProps({
  data: { type: Object, default: null }
})

defineEmits(['ai-click', 'dim-click', 'group-click', 'risk-click', 'question-click'])

/** 综合状态：根据项目风险计算 */
const statusText = computed(() => {
  const d = props.data?.projectRisk
  if (!d) return '正常'
  if (d.criticalCount > 0) return '关键风险'
  if (d.warningCount > 0) return '关注'
  return '正常'
})
const statusColor = computed(() => {
  const d = props.data?.projectRisk
  if (!d) return 'success'
  if (d.criticalCount > 0) return 'danger'
  if (d.warningCount > 0) return 'warning'
  return 'success'
})

const ShieldIcon = {
  render() {
    return h('svg', { fill: 'none', stroke: 'currentColor', viewBox: '0 0 24 24', width: 16, height: 16 }, [
      h('path', { 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'stroke-width': '2', d: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' })
    ])
  }
}

/** 四维度卡片数据 */
const dimensions = computed(() => {
  const d = props.data
  if (!d) return []

  const projectRisk = d.projectRisk
  const online = d.online
  const downstream = d.downstream
  const trustSummary = d.trustSummary

  return [
    {
      key: 'projectRisk',
      label: '项目风险',
      icon: '📊',
      statusType: projectRisk?.criticalCount > 0 ? 'danger' : projectRisk?.warningCount > 0 ? 'warning' : 'success',
      stats: [
        { value: projectRisk?.groupCount ?? '-', label: '群数' },
        { value: projectRisk?.criticalCount ?? '-', label: '高风险', class: (projectRisk?.criticalCount ?? 0) > 0 ? 'pk-dim-card__stat-value--danger' : '' },
        { value: projectRisk?.warningCount ?? '-', label: '中风险', class: (projectRisk?.warningCount ?? 0) > 0 ? 'pk-dim-card__stat-value--warning' : '' },
        { value: projectRisk?.normalCount ?? '-', label: '正常' }
      ],
      sentence: projectRisk?.aiSummary || ''
    },
    {
      key: 'online',
      label: '网上运行',
      icon: '🌐',
      statusType: online?.statusType || 'success',
      stats: (online?.labels || []).map(l => ({
        value: online?.[l.value] ?? '-',
        label: l.label
      })),
      sentence: online?.aiSummary || ''
    },
    {
      key: 'downstream',
      label: '下游问题',
      icon: '🔗',
      statusType: downstream?.statusType || 'success',
      stats: (downstream?.labels || []).map(l => ({
        value: downstream?.[l.value] ?? '-',
        label: l.label,
        class: l.value === 'monthlyNew' && (downstream?.monthlyNew ?? 0) > 0 ? 'pk-dim-card__stat-value--danger' : ''
      })),
      sentence: downstream?.aiSummary || ''
    },
    {
      key: 'trust',
      label: '可信管理',
      icon: '🛡️',
      statusType: trustSummary?.statusType || 'success',
      stats: (trustSummary?.labels || []).map(l => ({
        value: l.value === 'overallRate' ? (trustSummary?.overallRate ?? '-') + '%' : (trustSummary?.[l.value] ?? '-'),
        label: l.label,
        class: l.value === 'overallRate' && (trustSummary?.overallRate ?? 100) < 85 ? 'pk-dim-card__stat-value--warning' : l.value === 'failCount' && (trustSummary?.failCount ?? 0) > 0 ? 'pk-dim-card__stat-value--danger' : ''
      })),
      sentence: trustSummary?.aiSummary || ''
    }
  ]
})

/** 格式化风险为紧凑描述（与设计稿 buildCompactRiskDesc 一致） */
function buildCompactRiskDesc(risk) {
  if (!risk) return '⚠️ 风险待处理'

  const title = risk.title || '风险待处理'
  const rootCause = risk.rootCause || risk.why || ''
  const impact = risk.impact || ''

  let emoji = '📋'
  if (risk.level === 'critical' || risk.level === 'danger') {
    emoji = '🔴'
  } else if (risk.level === 'warning') {
    emoji = '🟡'
  } else if (risk.level === 'normal') {
    emoji = '🟢'
  }

  const parts = []
  if (title) parts.push(title)
  if (rootCause && rootCause !== '待分析') parts.push(rootCause)
  if (impact && impact !== '影响待评估') parts.push(impact)

  if (parts.length > 0) {
    return emoji + ' ' + parts.join('，')
  }

  return emoji + ' ' + title
}

/** 将风险数组格式化为带 text 字段的风险数组 */
function formatRisks(risks) {
  return (risks || []).map(r => ({
    ...r,
    text: buildCompactRiskDesc(r)
  }))
}

/** 三个项目群卡片数据 */
const groupCards = computed(() => {
  const d = props.data
  if (!d) return []
  return [d.V3, d.V2, d.MCU].filter(Boolean)
})

/** 猜你想问 */
const quickQuestions = computed(() => props.data?.projectRisk?.quickQuestions || [])
</script>

<style scoped>
/* ===== 上行：四维度卡片（左边框 + 浅灰背景） ===== */
.pk-overview-dims {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 4px;
}

.pk-dim-card {
  background: #fafafa;
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-left: 4px solid #059669;
}

.pk-dim-card:hover {
  background: #f3f4f6;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.pk-dim-card--danger { border-left-color: #dc2626; }
.pk-dim-card--warning { border-left-color: #d97706; }
.pk-dim-card--success { border-left-color: #059669; }

.pk-dim-card__header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.pk-dim-card__icon { font-size: 14px; flex-shrink: 0; }

.pk-dim-card__title {
  font-size: 11px;
  font-weight: 600;
  color: var(--gray-800);
  flex: 1;
}

.pk-dim-card__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pk-dim-card__dot--danger { background: #dc2626; }
.pk-dim-card__dot--warning { background: #d97706; }
.pk-dim-card__dot--success { background: #059669; }

.pk-dim-card__stats {
  display: flex;
  justify-content: space-between;
  gap: 2px;
}

.pk-dim-card__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1px;
  flex: 1;
}

.pk-dim-card__stat-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--gray-800);
  line-height: 1;
}
.pk-dim-card__stat-value--danger { color: #dc2626; }
.pk-dim-card__stat-value--warning { color: #d97706; }

.pk-dim-card__stat-label {
  font-size: 9px;
  color: var(--gray-400);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 52px;
}

.pk-dim-card__sentence {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  padding: 4px 6px;
  border-radius: 4px;
  line-height: 1.3;
}

.pk-dim-card__sentence-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}

.pk-dim-card__sentence--danger { background: #fef2f2; color: #991b1b; }
.pk-dim-card__sentence--danger .pk-dim-card__sentence-dot { background: #dc2626; }
.pk-dim-card__sentence--warning { background: #fef3c7; color: #92400e; }
.pk-dim-card__sentence--warning .pk-dim-card__sentence-dot { background: #d97706; }
.pk-dim-card__sentence--success { background: #d1fae5; color: #166534; }
.pk-dim-card__sentence--success .pk-dim-card__sentence-dot { background: #059669; }

/* ===== 下行：三个项目群风险卡片（阴影渐变卡片样式） ===== */
.pk-overview-groups {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-top: 12px;
}

.pk-group-card {
  background: linear-gradient(135deg, #fff, #f8fafc);
  border-radius: 12px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06), 0 4px 16px rgba(0, 0, 0, 0.04);
}

.pk-group-card:hover {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12), 0 16px 32px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

/* 头部：标签 + 状态徽章 */
.pk-group-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.pk-group-card__tag {
  font-size: 11px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 6px;
  background: linear-gradient(to bottom, #f9fafb, #f3f4f6);
  color: #374151;
  border: none;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

/* 部门级风险列表（数字序号 + 紧凑描述） */
.pk-group-risks {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.pk-group-risk-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 11px;
  line-height: 1.4;
  cursor: pointer;
  transition: background 0.15s ease;
  min-height: 30px;
  box-sizing: border-box;
}
.pk-group-risk-item:hover {
  background: var(--gray-50);
}
.pk-group-risk-rank {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
  background: var(--gray-300);
  color: #fff;
}
.pk-group-risk-text {
  color: var(--gray-800);
  font-weight: 500;
}

.pk-group-risk-item--critical,
.pk-group-risk-item--danger {
  background: var(--color-error-50);
}
.pk-group-risk-item--critical:hover,
.pk-group-risk-item--danger:hover {
  background: var(--color-error-10);
}
.pk-group-risk-item--critical .pk-group-risk-rank,
.pk-group-risk-item--danger .pk-group-risk-rank {
  background: var(--color-error-500);
}
.pk-group-risk-item--warning {
  background: var(--color-warning-50);
}
.pk-group-risk-item--warning:hover {
  background: var(--color-warning-10);
}
.pk-group-risk-item--warning .pk-group-risk-rank {
  background: var(--color-warning-500);
}
.pk-group-risk-item--normal {
  background: var(--color-success-50);
}
.pk-group-risk-item--normal:hover {
  background: var(--color-success-10);
}
.pk-group-risk-item--normal .pk-group-risk-rank {
  background: var(--color-success-500);
}

/* 底部猜你想问 */
.pk-overview-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  border-top: 1px solid var(--gray-200);
}

.pk-overview-intent {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pk-overview-intent__tag {
  padding: 4px 10px;
  background: linear-gradient(135deg, #faf5ff, #eff6ff);
  border-radius: 6px;
  font-size: 11px;
  color: var(--gray-600);
  cursor: pointer;
  transition: all 0.15s ease;
  border: 1px solid transparent;
}

.pk-overview-intent__tag:hover {
  background: linear-gradient(135deg, #f3e8ff, #dbeafe);
  border-color: rgba(99, 102, 241, 0.2);
  color: var(--gray-800);
}

/* Responsive */
@media (max-width: 1024px) {
  .pk-overview-dims {
    grid-template-columns: repeat(2, 1fr);
  }
  .pk-overview-groups {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .pk-overview-dims {
    grid-template-columns: 1fr 1fr;
  }
  .pk-overview-groups {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .pk-overview-dims {
    grid-template-columns: 1fr;
  }
}
</style>

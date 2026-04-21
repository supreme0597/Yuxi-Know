<template>
  <div class="pk-kanban">
    <!-- Header -->
    <header class="pk-kanban__header">
      <div class="pk-kanban__logo">
        <div class="pk-kanban__logo-icon">
          <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div>
          <h1 class="pk-kanban__title">AI项目管理智能助手</h1>
          <p class="pk-kanban__subtitle">智能决策支持</p>
        </div>
      </div>
      <div class="pk-kanban__header-right">
        <span class="pk-kanban__ai-status">
          <span class="pk-kanban__ai-dot"></span>
          AI就绪
        </span>
      </div>
    </header>

    <!-- 内容容器：最大宽度居中 -->
    <div class="pk-kanban__content">
      <!-- Tab 切换 -->
      <div class="pk-kanban__tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="pk-kanban__tab"
          :class="{ 'pk-kanban__tab--active': activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
        <div class="pk-kanban__tabs-stats">
          <span class="pk-kanban__stat-item">
            <span class="pk-kanban__stat-dot pk-kanban__stat-dot--red"></span>
            {{ criticalCount }}项关键
          </span>
          <span class="pk-kanban__stat-item">
            <span class="pk-kanban__stat-dot pk-kanban__stat-dot--yellow"></span>
            {{ warningCount }}项关注
          </span>
        </div>
      </div>

      <!-- 项目级视图内容 -->
      <div v-if="activeTab === 'project'" class="pk-kanban__body">
        <!-- 子项目选择器 + 甜点工具栏 -->
        <ProjectSelector
          v-model="currentProjectId"
          :projects="projectList"
          :info="selectorInfo"
          @tool-action="handleToolAction"
        />

        <!-- 数据卡片网格 -->
        <div class="pk-kanban__grid">
          <!-- 里程碑 (全宽) -->
          <MilestoneCard
            :data="currentProject?.milestone"
            @ai-click="handleAIClick"
            @risk-click="handleRiskClick"
          />

          <!-- 可信管理 (全宽 9宫格) -->
          <TrustCard
            :data="currentProject?.trustDetails"
            @ai-click="handleAIClick"
            @subcard-click="handleTrustSubcardClick"
            @risk-click="handleRiskClick"
          />

          <!-- 范围 + 质量 (并排) -->
          <ScopeCard :data="currentProject?.scope" @ai-click="handleAIClick" @risk-click="handleRiskClick" />
          <QualityCard :data="currentProject?.quality" @ai-click="handleAIClick" @risk-click="handleRiskClick" />

          <!-- 进度 + 费用 (并排) -->
          <ScheduleCard :data="currentProject?.schedule" @ai-click="handleAIClick" @risk-click="handleRiskClick" />
          <BudgetCard :data="currentProject?.budget" @ai-click="handleAIClick" @risk-click="handleRiskClick" />
        </div>

        <!-- 五领域卡片 -->
        <WorkflowDomainsCard
          :data="currentProject?.workflow"
          @domain-click="handleDomainClick"
          @ai-click="handleAIClick"
        />

        <!-- AI 分析总结条 -->
        <AISummaryBar
          :summary="currentProject?.aiSummary || ''"
          :risks="allRisks"
          :questions="allQuestions"
          @question-click="handleQuestionClick"
          @risk-click="handleRiskClick"
          @summary-click="handleSummaryClick"
        />
      </div>

      <!-- 项目群级视图内容 -->
      <div v-else-if="activeTab === 'group'" class="pk-kanban__body">
        <!-- 项目群卡片网格 -->
        <div class="pk-kanban__groups">
          <GroupCard
            v-for="gk in groupKeys"
            :key="gk"
            :group-key="gk"
            @ai-click="handleGroupAIClick"
            @sub-click="handleSubProjectClick"
            @sub-ai-click="handleSubProjectAIClick"
            @dim-click="handleDimClick"
            @progress-click="handleSubProjectProgressClick"
            @milestone-click="handleSubProjectMilestoneClick"
          />
        </div>

        <!-- AI 分析总结条 -->
        <AISummaryBar
          :summary="groupSummaryData.aiSummary"
          :risks="groupSummaryData.risks"
          :questions="groupSummaryData.quickQuestions"
          @question-click="handleGroupQuestionClick"
          @risk-click="handleGroupRiskClick"
          @summary-click="handleGroupSummaryClick"
        />
      </div>

      <!-- 部门级 占位 -->
      <div v-else class="pk-kanban__placeholder">
        <div class="pk-kanban__placeholder-icon">🚧</div>
        <p class="pk-kanban__placeholder-text">{{ activeTabLabel }}视图开发中</p>
        <p class="pk-kanban__placeholder-desc">敬请期待</p>
      </div>
    </div>

    <!-- AI 分析侧边栏 -->
    <AISidepanel
      :visible="sidepanel.visible.value"
      :data="sidepanel.panelData.value"
      @update:visible="sidepanel.visible.value = $event"
      @question-click="handleSidepanelQuestion"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { projectData, projectList } from '@/components/project-kanban/data/projectData'
import { groupSummary, groupMeta, groupKeys } from '@/components/project-kanban/data/groupData'
import { useAISidepanel } from '@/components/project-kanban/composables/useAISidepanel'
import ProjectSelector from '@/components/project-kanban/project/ProjectSelector.vue'
import MilestoneCard from '@/components/project-kanban/project/MilestoneCard.vue'
import TrustCard from '@/components/project-kanban/project/TrustCard.vue'
import ScopeCard from '@/components/project-kanban/project/ScopeCard.vue'
import QualityCard from '@/components/project-kanban/project/QualityCard.vue'
import ScheduleCard from '@/components/project-kanban/project/ScheduleCard.vue'
import BudgetCard from '@/components/project-kanban/project/BudgetCard.vue'
import WorkflowDomainsCard from '@/components/project-kanban/project/WorkflowDomainsCard.vue'
import AISummaryBar from '@/components/project-kanban/project/AISummaryBar.vue'
import GroupCard from '@/components/project-kanban/group/GroupCard.vue'
import AISidepanel from '@/components/project-kanban/common/AISidepanel.vue'

const tabs = [
  { key: 'dept', label: '部门级' },
  { key: 'group', label: '项目群级' },
  { key: 'project', label: '项目级' }
]

const activeTab = ref('project')
const currentProjectId = ref(projectList[0]?.id || '')
const sidepanel = useAISidepanel()

const currentProject = computed(() => projectData[currentProjectId.value] || null)

const selectorInfo = computed(() => {
  const p = currentProject.value
  if (!p) return ''
  return `${p.group}项目群 | 进度: ${p.progress}%`
})

const activeTabLabel = computed(() => tabs.find(t => t.key === activeTab.value)?.label || '')

// 汇总当前项目的全维度风险，按等级排序取 TOP3
const allRisks = computed(() => {
  if (!currentProject.value) return []
  const p = currentProject.value
  const all = []
  const sources = [
    p.milestone?.risks,
    p.trustDetails?.risks,
    p.scope?.risks,
    p.schedule?.risks,
    p.resource?.risks,
    p.budget?.risks,
    p.quality?.risks
  ]
  for (const risks of sources) {
    if (Array.isArray(risks)) all.push(...risks)
  }
  return all
})

// 猜你想问：使用 intentQuestions（risk + decision），与设计稿一致
const allQuestions = computed(() => {
  if (!currentProject.value) return []
  const p = currentProject.value
  const intent = p.intentQuestions || {}
  return [...(intent.risk || []), ...(intent.decision || [])].slice(0, 3)
})

const criticalCount = computed(() => {
  if (activeTab.value === 'group') {
    return groupSummary.risks.filter(r => r.level === 'critical' || r.level === 'danger').length
  }
  return allRisks.value.filter(r => r.level === 'critical' || r.level === 'danger').length
})
const warningCount = computed(() => {
  if (activeTab.value === 'group') {
    return groupSummary.risks.filter(r => r.level === 'warning').length
  }
  return allRisks.value.filter(r => r.level === 'warning').length
})

// 项目群级 computed
const groupSummaryData = computed(() => groupSummary)

function handleAIClick(section) {
  sidepanel.open(section, currentProject.value)
}

function handleTrustSubcardClick(category) {
  sidepanel.open('trustSubcard', currentProject.value, category)
}

function handleDomainClick(domain) {
  sidepanel.open('workflow', currentProject.value, { domain })
}

function handleToolAction(action) {
  console.log('[Tool Action]', action)
}

function handleRiskClick(risk) {
  const intent = currentProject.value?.intentQuestions || {}
  const questions = [...(intent.risk || []), ...(intent.decision || [])]
  sidepanel.open('aiSummary', currentProject.value, { risk, questions })
}

function handleQuestionClick(question) {
  // 猜你想问：打开侧边栏 + 隐藏概览 + 自动发送
  sidepanel.open('subProject', currentProject.value, { hideData: true, autoSend: question })
}

function handleSummaryClick() {
  sidepanel.open('subProject', currentProject.value)
}

function handleSidepanelQuestion(question) {
  console.log('[AI Question]', question)
}

// 项目群级事件
function handleGroupAIClick(groupKey) {
  const meta = groupMeta[groupKey]
  if (!meta) return
  sidepanel.open('group', meta, { summary: groupSummary, groupCount: groupKeys.length })
}

function handleSubProjectClick(subProject) {
  sidepanel.open('subProject', subProject)
}

function handleSubProjectAIClick(subProject) {
  sidepanel.open('subProject', subProject)
}

function handleDimClick({ dim, project }) {
  sidepanel.open('subProjectDimension', project, { dim })
}

function handleSubProjectProgressClick(subProject) {
  sidepanel.open('schedule', subProject)
}

function handleSubProjectMilestoneClick(subProject) {
  sidepanel.open('milestone', subProject)
}

function handleGroupRiskClick(risk) {
  // 项目群级风险点击 — 用项目群的 quickQuestions
  const source = risk.source
  const project = source ? projectData[source] : null
  if (project) {
    sidepanel.open('aiSummary', project, { risk, questions: groupSummary.quickQuestions })
  }
}

function handleGroupQuestionClick(question) {
  // 项目群级猜你想问：打开侧边栏 + 隐藏概览 + 自动发送
  sidepanel.open('groupSummary', groupSummary, { groupCount: groupKeys.length, hideData: true, autoSend: question })
}

function handleGroupSummaryClick() {
  sidepanel.open('groupSummary', groupSummary, { groupCount: groupKeys.length })
}
</script>

<style scoped>
.pk-kanban {
  min-height: 100vh;
  background: var(--gray-25);
  padding-bottom: 32px;
}

/* Header */
.pk-kanban__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: var(--gray-0);
  border-bottom: 1px solid var(--gray-200);
  position: sticky;
  top: 0;
  z-index: 50;
}
.pk-kanban__logo {
  display: flex;
  align-items: center;
  gap: 12px;
}
.pk-kanban__logo-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.pk-kanban__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--gray-900);
  margin: 0;
}
.pk-kanban__subtitle {
  font-size: 11px;
  color: var(--gray-400);
  margin: 0;
}
.pk-kanban__header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.pk-kanban__ai-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--gray-400);
}
.pk-kanban__ai-dot {
  width: 6px;
  height: 6px;
  background: #10b981;
  border-radius: 50%;
  animation: pk-pulse 2s ease-in-out infinite;
}
@keyframes pk-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* Content wrapper - centered with max-width */
.pk-kanban__content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 32px;
}

/* Tabs */
.pk-kanban__tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px;
  margin-top: 24px;
  background: var(--gray-0);
  border-radius: 12px;
  border: 1px solid var(--gray-200);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.pk-kanban__tab {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 500;
  color: var(--gray-500);
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.pk-kanban__tab:hover {
  color: var(--gray-700);
  background: var(--gray-50);
}
.pk-kanban__tab--active {
  color: var(--gray-800);
  background: var(--gray-0);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  font-weight: 600;
}
.pk-kanban__tabs-stats {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: var(--gray-400);
  padding-right: 8px;
}
.pk-kanban__stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.pk-kanban__stat-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.pk-kanban__stat-dot--red { background: #ef4444; }
.pk-kanban__stat-dot--yellow { background: #f59e0b; }

/* Body */
.pk-kanban__body {
  padding: 24px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Grid */
.pk-kanban__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

/* Groups grid */
.pk-kanban__groups {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

/* Placeholder */
.pk-kanban__placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 24px 32px;
}
.pk-kanban__placeholder-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.pk-kanban__placeholder-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--gray-700);
  margin: 0;
}
.pk-kanban__placeholder-desc {
  font-size: 13px;
  color: var(--gray-400);
  margin: 4px 0 0;
}

/* Responsive */
@media (max-width: 1024px) {
  .pk-kanban__grid {
    grid-template-columns: 1fr;
  }
  .pk-kanban__groups {
    grid-template-columns: 1fr;
  }
}
</style>

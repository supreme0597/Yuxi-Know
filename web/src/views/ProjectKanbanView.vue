<template>
  <div class="pk-kanban project-kanban-view">
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
          <BudgetCard :data="currentBudgetFromDept" @ai-click="handleBudgetAIClick" @risk-click="handleRiskClick" />
        </div>

        <!-- 五领域卡片 -->
        <WorkflowDomainsCard
          :data="currentProject?.workflow"
          @domain-click="handleDomainClick"
          @ai-click="handleAIClick"
          @risk-click="handleWorkflowRiskClick"
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
            @id-click="handleSubProjectIdClick"
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

      <!-- 部门级视图内容 -->
      <div v-else class="pk-kanban__body">
        <!-- 第1行：3张卡片 -->
        <div class="pk-kanban__dept-grid">
          <DeptMilestoneCard
            :data="deptData.department.milestone"
            @ai-click="handleDeptAIClick"
            @summary-click="handleDeptSummaryClick"
            @risk-click="handleDeptMilestoneItemClick"
            @phase-click="handleMilestonePhaseClick"
          />
          <DeptAHBCard
            :data="deptData.department.ahb"
            @ai-click="handleDeptAIClick"
            @summary-click="handleDeptSummaryClick"
            @category-click="handleDeptAHBCategoryClick"
            @metric-click="handleMetricClick"
          />
          <DeptBudgetCard
            :data="deptData.department.budget"
            @ai-click="handleDeptAIClick"
            @summary-click="handleDeptSummaryClick"
            @project-click="handleDeptBudgetProjectClick"
            @metric-click="handleMetricClick"
          />
        </div>

        <!-- 第2行：任务卡片全宽 -->
        <DeptTaskCard
          :data="deptData.department.task"
          @ai-click="handleDeptAIClick"
          @summary-click="handleDeptSummaryClick"
          @task-click="handleDeptTaskClick"
          @metric-click="handleMetricClick"
          @group-click="handleGroupHighlight"
        />

        <!-- 第3行：综合风险卡片全宽 -->
        <DeptGroupsOverviewCard
          :data="deptData.department.groupsOverview"
          @ai-click="handleDeptAIClick"
          @dim-click="handleDeptDimClick"
          @group-click="handleDeptGroupClick"
          @risk-click="handleDeptRiskClick"
          @question-click="handleDeptQuestionClick"
        />
      </div>
    </div>

    <!-- AI 分析侧边栏 -->
    <AISidepanel
      :visible="sidepanel.visible.value"
      :data="sidepanel.panelData.value"
      @update:visible="sidepanel.visible.value = $event"
      @question-click="handleSidepanelQuestion"
    />

    <!-- Markdown 文档侧边栏（甜点工具栏） -->
    <MdSidepanel
      :visible="mdSidepanel.visible.value"
      :title="mdSidepanel.title.value"
      :subtitle="mdSidepanel.subtitle.value"
      :tool-type="mdSidepanel.toolType.value"
      :fetch-content="fetchMdContent"
      :current-project-id="currentProjectId"
      @update:visible="mdSidepanel.visible.value = $event"
      @close="mdSidepanel.close"
    />
  </div>
</template>

<script setup>
import '@/components/project-kanban/styles/variables.css'
import { ref, computed } from 'vue'
import { projectData } from '@/components/project-kanban/data/projectData'
import { groupData } from '@/components/project-kanban/data/groupData'
import { useAISidepanel } from '@/components/project-kanban/composables/useAISidepanel'
import { useMdSidepanel, fetchMdContent } from '@/components/project-kanban/composables/useMdSidepanel'
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
import { deptData } from '@/components/project-kanban/data/deptData'
import DeptMilestoneCard from '@/components/project-kanban/dept/DeptMilestoneCard.vue'
import DeptAHBCard from '@/components/project-kanban/dept/DeptAHBCard.vue'
import DeptBudgetCard from '@/components/project-kanban/dept/DeptBudgetCard.vue'
import DeptTaskCard from '@/components/project-kanban/dept/DeptTaskCard.vue'
import DeptGroupsOverviewCard from '@/components/project-kanban/dept/DeptGroupsOverviewCard.vue'
import MdSidepanel from '@/components/project-kanban/common/MdSidepanel.vue'

const tabs = [
  { key: 'dept', label: '部门级' },
  { key: 'group', label: '项目群级' },
  { key: 'project', label: '项目级' }
]

const activeTab = ref('dept')
const sidepanel = useAISidepanel()
const mdSidepanel = useMdSidepanel()

// 派生数据
const projectList = computed(() => Object.keys(projectData).map(key => ({
  id: key,
  name: projectData[key].name,
  group: projectData[key].group,
  progress: projectData[key].progress
})))

const groupKeys = computed(() => Object.keys(groupData).filter(k => k !== 'summary'))
const groupSummaryData = computed(() => groupData.summary || {})

const currentProjectId = ref(projectList.value[0]?.id || '')

const currentProject = computed(() => projectData[currentProjectId.value] || null)

// 费用执行卡片：从部门级 budget.projects 中查找当前版本所属项目，使用其数据
const currentDeptBudgetProject = computed(() => {
  const versionId = currentProjectId.value
  if (!versionId) return null
  const projects = deptData.department?.budget?.projects || []
  return projects.find(p => Array.isArray(p.relations) && p.relations.includes(versionId)) || null
})

const currentBudgetFromDept = computed(() => {
  const match = currentDeptBudgetProject.value
  if (!match) return null
  // 将部门级项目预算数据映射为 BudgetCard 所需格式
  // status 基于偏差值，与部门级子卡片偏差颜色逻辑一致
  const absDeviation = Math.abs(match.deviation || 0)
  let status = 'green'
  if (absDeviation > 20) status = 'red'
  else if (absDeviation > 10) status = 'yellow'
  return {
    status,
    aiSummary: match.aiSummary || '',
    executionRate: match.rate ?? 0,
    total: match.budget ?? 0,
    executed: match.executed ?? 0,
    deviation: match.deviation,
    risks: match.risks || []
  }
})

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

// 从当前 tab 卡片的标签状态动态统计关键/关注数量
const CRITICAL_STATUS = new Set(['red', 'critical', 'danger'])
const WARNING_STATUS = new Set(['yellow', 'warning'])

const criticalCount = computed(() => {
  const statuses = getCardStatuses()
  return statuses.filter(s => CRITICAL_STATUS.has(s)).length
})
const warningCount = computed(() => {
  const statuses = getCardStatuses()
  return statuses.filter(s => WARNING_STATUS.has(s)).length
})

/** 获取当前 tab 中所有卡片的 status 标签值 */
function getCardStatuses() {
  if (activeTab.value === 'project') return getProjectCardStatuses()
  if (activeTab.value === 'group') return getGroupCardStatuses()
  return getDeptCardStatuses()
}

/** 项目级：6张数据卡片 + 5个领域状态 */
function getProjectCardStatuses() {
  const p = currentProject.value
  if (!p) return []
  const statuses = []
  // 6张数据卡片的 status
  statuses.push(p.milestone?.statusColor || 'green')
  const trustScore = p.trustDetails?.overallScore || 0
  statuses.push(trustScore >= 80 ? 'green' : trustScore >= 60 ? 'yellow' : 'red')
  statuses.push(p.scope?.status || 'green')
  statuses.push(p.quality?.status || 'green')
  statuses.push(p.schedule?.status || 'green')
  statuses.push(p.budget?.status || 'green')
  // 5个领域
  const wf = p.workflow || {}
  for (const key of ['design', 'dev', 'build', 'test', 'release']) {
    statuses.push(wf[key]?.status || 'green')
  }
  return statuses
}

/** 项目群级：各项目群 GroupCard 的 status */
function getGroupCardStatuses() {
  return groupKeys.value.map(k => groupData[k]?.status || 'normal')
}

/** 部门级：5张数据卡片的 statusType */
function getDeptCardStatuses() {
  const d = deptData.department
  return [
    d.milestone?.statusType || 'green',
    d.ahb?.statusType || 'green',
    d.budget?.statusType || 'green',
    d.task?.statusType || 'green',
    d.groupsOverview?.projectRisk
      ? (d.groupsOverview.projectRisk.criticalCount > 0 ? 'red' : d.groupsOverview.projectRisk.warningCount > 0 ? 'yellow' : 'green')
      : 'green'
  ]
}

// 项目群级 computed

// 费用执行卡片 AI 点击 — 使用部门级 budget-dept builder，与部门级子卡片侧边栏一致
function handleBudgetAIClick() {
  const match = currentDeptBudgetProject.value
  if (match) {
    sidepanel.open('budget-dept', deptData, { project: match })
  } else {
    sidepanel.open('budget-dept', deptData)
  }
}

function handleAIClick(section) {
  sidepanel.open(section, currentProject.value)
}

function handleTrustSubcardClick(category) {
  sidepanel.open('trustSubcard', currentProject.value, category)
}

function handleDomainClick(domain, riskIndex) {
  sidepanel.open('workflow', currentProject.value, { domain, riskIndex })
}

function handleWorkflowRiskClick({ domain, riskIndex }) {
  sidepanel.open('workflow', currentProject.value, { domain, riskIndex })
}

function handleToolAction(action) {
  mdSidepanel.open(action)
}

function handleRiskClick(risk) {
  const typeToField = { '里程碑': 'milestone', '可信': 'trustDetails', '范围': 'scope', '质量': 'quality', '进度': 'schedule', '费用': 'budget' }
  const field = typeToField[risk.type]
  const fieldQuestions = field ? currentProject.value?.[field]?.quickQuestions : []
  const intent = currentProject.value?.intentQuestions || {}
  const questions = fieldQuestions?.length ? fieldQuestions : [...(intent.risk || []), ...(intent.decision || [])]
  sidepanel.open('aiSummary', currentProject.value, { risk, questions })
}

function handleQuestionClick(question) {
  // 猜你想问：打开侧边栏 + 显示完整数据概览 + 自动发送
  sidepanel.open('subProject', currentProject.value, { autoSend: question })
}

function handleSummaryClick() {
  sidepanel.open('summary-project', currentProject.value)
}

function handleSidepanelQuestion(question) {
  // 侧边栏内猜你想问：AISidepanel.handleQuickQuestion 已自行发送到聊天
  // 此处仅做日志记录
  console.log('[AI Question]', question)
}

// 项目群级事件
function handleGroupAIClick(groupKey) {
  const meta = groupData[groupKey]
  if (!meta) return
  sidepanel.open('group', meta, { summary: groupSummaryData.value, groupCount: groupKeys.value.length })
}

function handleSubProjectClick(subProject) {
  sidepanel.open('subProject', subProject)
}

function handleSubProjectIdClick(subProject) {
  // 切换到项目级页签 + 选择对应子项目
  currentProjectId.value = subProject.id
  activeTab.value = 'project'
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function handleSubProjectAIClick(subProject) {
  // 项目群子项目使用专用 builder
  if (subProject.subProjects?.length || subProject.projectCount) {
    sidepanel.open('project-group', subProject)
  } else {
    sidepanel.open('subProject', subProject)
  }
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
    sidepanel.open('aiSummary', project, { risk, questions: groupData.summary.quickQuestions })
  }
}

function handleGroupQuestionClick(question) {
  // 项目群级猜你想问：打开侧边栏 + 显示完整数据概览 + 自动发送
  sidepanel.open('groupSummary', groupSummaryData.value, { groupCount: groupKeys.value.length, autoSend: question })
}

function handleGroupSummaryClick() {
  sidepanel.open('groupSummary', groupSummaryData.value, { groupCount: groupKeys.value.length })
}

// 部门级事件
function handleDeptAIClick(section) {
  sidepanel.open(section, deptData)
}

// 一句话总结点击 — 打开带焦点上下文的侧边栏（与 AI 按钮区分）
function handleDeptSummaryClick(section) {
  // 从 deptData 中获取该卡片的 aiSummary 作为焦点
  const dept = deptData?.department || {}
  const summaryMap = {
    'milestone-dept': dept.milestone?.aiSummary || '',
    'ahb': dept.ahb?.aiSummary || '',
    'budget-dept': dept.budget?.aiSummary || '',
    'task-dept': dept.task?.aiSummary || ''
  }
  const sentence = summaryMap[section] || ''
  sidepanel.open(section, deptData, { sentence })
}

// 里程碑子卡片点击 — 传入 timeline item
function handleDeptMilestoneItemClick(item) {
  sidepanel.open('milestone-dept', deptData, { timelineItem: item })
}

// 项目群综合风险中的风险点击 — 展示单条风险的 5W2H 详情
function handleDeptRiskClick(risk, groupCard) {
  sidepanel.open('group-risk-detail', deptData, { risk, groupCard })
}

function handleDeptAHBCategoryClick(category) {
  sidepanel.open('ahb', deptData, { category })
}

function handleDeptBudgetProjectClick(project) {
  sidepanel.open('budget-dept', deptData, { project })
}

function handleDeptTaskClick(taskOrder) {
  console.log(taskOrder)
  sidepanel.open('task-dept', deptData, { taskOrder })
}

function handleDeptDimClick(dimension) {
  // 维度子卡片点击：用 groups-overview builder 的 dimension 分支
  sidepanel.open('groups-overview', deptData, { dimension })
}

function handleDeptGroupClick(groupCard) {
  activeTab.value = 'group'
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function handleDeptQuestionClick(question) {
  sidepanel.open('groups-overview', deptData, { autoSend: question })
}

// 指标点击（I任务）
function handleMetricClick(cardType, metric) {
  sidepanel.open('metric-detail', deptData, { cardType, metric })
}

// 里程碑阶段点击（K任务）
function handleMilestonePhaseClick({ phase, offering, timelineItem }) {
  sidepanel.open('milestone-phase', deptData, { phase, offering, timelineItem })
}

// 分组高亮
function handleGroupHighlight(group) {
  const task = deptData.department.task
  const allOrders = task.taskOrders && typeof task.taskOrders === 'object' && !Array.isArray(task.taskOrders)
    ? Object.values(task.taskOrders).flat()
    : task.taskOrders || []
  const matchingOrders = allOrders.filter(t => t.group === group)
  if (matchingOrders.length > 0) {
    sidepanel.open('task-dept', deptData, { taskOrder: matchingOrders[0] })
  }
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
  padding: 16px clamp(80px, 8vw, 320px);
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
  background: linear-gradient(135deg, var(--pk-group-v2), var(--pk-group-v3));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--pk-card-bg);
}
.pk-kanban__title {
  font-size: 15px;
  font-weight: 600;
  color: var(--gray-900);
  margin: 0;
}
.pk-kanban__subtitle {
  font-size: 12px;
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
  font-size: 12px;
  color: var(--gray-400);
}
.pk-kanban__ai-dot {
  width: 6px;
  height: 6px;
  background: var(--pk-success);
  border-radius: 50%;
  animation: pk-pulse 2s ease-in-out infinite;
}
@keyframes pk-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* Content wrapper - centered with max-width, fluid padding */
.pk-kanban__content {
  max-width: clamp(1440px, 92vw, 2800px);
  margin: 0 auto;
  padding: 0 clamp(80px, 8vw, 320px);
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
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 4px 12px rgba(0, 0, 0, 0.04);
}
.pk-kanban__tab {
  padding: 8px 20px;
  font-size: 14px;
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
  font-size: 12px;
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
.pk-kanban__stat-dot--red { background: var(--pk-danger); }
.pk-kanban__stat-dot--yellow { background: var(--pk-warning); }

/* Body */
.pk-kanban__body {
  padding: 16px 0;
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

/* Dept grid - 第1行3列 */
.pk-kanban__dept-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  min-width: 0;
}

/* 防止子卡片内容溢出 grid */
.pk-kanban__dept-grid > * {
  min-width: 0;
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
@media (max-width: 1440px) {
  .pk-kanban__grid {
    gap: 14px;
  }
}

@media (max-width: 1280px) {
  .pk-kanban__groups {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 1024px) {
  .pk-kanban__grid {
    grid-template-columns: 1fr;
  }
  .pk-kanban__dept-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .pk-kanban__groups {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .pk-kanban__dept-grid {
    grid-template-columns: 1fr;
  }
  .pk-kanban__groups {
    grid-template-columns: 1fr;
  }
}

/* 宽屏自适应放大 */
@media (min-width: 1600px) {
  .pk-kanban__header {
    padding-top: 18px;
    padding-bottom: 18px;
  }
  .pk-kanban__title {
    font-size: 17px;
  }
  .pk-kanban__subtitle {
    font-size: 13px;
  }
  .pk-kanban__ai-status {
    font-size: 13px;
  }
  .pk-kanban__tabs {
    padding: 8px;
    margin-top: 28px;
  }
  .pk-kanban__tab {
    padding: 9px 22px;
    font-size: 15px;
  }
  .pk-kanban__tabs-stats {
    font-size: 13px;
  }
  .pk-kanban__body {
    padding: 18px 0;
    gap: 18px;
  }
  .pk-kanban__grid {
    gap: 18px;
  }
  .pk-kanban__dept-grid {
    gap: 14px;
  }
  .pk-kanban__groups {
    gap: 22px;
  }
}

@media (min-width: 1920px) {
  .pk-kanban__header {
    padding-top: 20px;
    padding-bottom: 20px;
  }
  .pk-kanban__title {
    font-size: 18px;
  }
  .pk-kanban__subtitle {
    font-size: 14px;
  }
  .pk-kanban__ai-status {
    font-size: 14px;
  }
  .pk-kanban__tabs {
    padding: 8px;
    margin-top: 32px;
  }
  .pk-kanban__tab {
    padding: 10px 24px;
    font-size: 16px;
  }
  .pk-kanban__tabs-stats {
    font-size: 14px;
  }
  .pk-kanban__body {
    padding: 20px 0;
    gap: 20px;
  }
  .pk-kanban__grid {
    gap: 20px;
  }
  .pk-kanban__dept-grid {
    gap: 16px;
  }
  .pk-kanban__groups {
    gap: 24px;
  }
}

@media (min-width: 2560px) {
  .pk-kanban__header {
    padding-top: 24px;
    padding-bottom: 24px;
  }
  .pk-kanban__title {
    font-size: 19px;
  }
  .pk-kanban__subtitle {
    font-size: 15px;
  }
  .pk-kanban__ai-status {
    font-size: 15px;
  }
  .pk-kanban__tabs {
    padding: 10px;
    margin-top: 36px;
  }
  .pk-kanban__tab {
    padding: 10px 28px;
    font-size: 17px;
  }
  .pk-kanban__tabs-stats {
    font-size: 15px;
  }
  .pk-kanban__body {
    padding: 24px 0;
    gap: 24px;
  }
  .pk-kanban__grid {
    gap: 24px;
  }
  .pk-kanban__dept-grid {
    gap: 20px;
  }
  .pk-kanban__groups {
    gap: 28px;
  }
}
</style>

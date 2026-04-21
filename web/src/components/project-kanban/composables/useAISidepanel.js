/**
 * useAISidepanel - AI 侧边栏数据映射
 * 根据卡片类型和项目数据，生成侧边栏所需的结构化数据
 */
import { ref, computed } from 'vue'

const visible = ref(false)
const panelData = ref({})

export function useAISidepanel() {
  /**
   * 根据卡片类型和项目数据构建侧边栏数据
   * @param {string} section - 卡片区域标识
   * @param {object} projectData - 当前项目的完整数据
   * @param {object} [extra] - 额外上下文（如 trustSubcard 等）
   */
  function open(section, projectData, extra = {}) {
    // 五领域 key (design/dev/build/test/release) → workflow
    const workflowKeys = ['design', 'dev', 'build', 'test', 'release']
    if (workflowKeys.includes(section)) {
      extra = { ...extra, domain: section }
      section = 'workflow'
    }
    // 子项目维度 → subProjectDimension
    if (section === 'subProjectDimension') {
      section = 'subProjectDimension'
    }
    const builder = sectionBuilders[section]
    if (builder && projectData) {
      panelData.value = builder(projectData, extra)
    } else {
      panelData.value = { title: 'AI 分析', reasoning: '暂无数据' }
    }
    // 如果指定了自动发送的消息，附加到 panelData
    if (extra.autoSend) {
      panelData.value = { ...panelData.value, autoSend: extra.autoSend }
    }
    // 如果指定隐藏数据概览
    if (extra.hideData) {
      panelData.value = { ...panelData.value, hideData: true }
    }
    visible.value = true
  }

  function close() {
    visible.value = false
  }

  return { visible, panelData, open, close }
}

// ========== 卡片类型 → 侧边栏数据映射 ==========

const sectionBuilders = {
  // 里程碑
  milestone(project) {
    const ms = project.milestone || {}
    const phases = ms.phases || []
    const completed = phases.filter(p => p.status === 'completed').length
    const active = phases.filter(p => p.status === 'active').length
    const risks = ms.risks || []

    return {
      title: '里程碑分析',
      subtitle: project.name || '',
      progress: [
        { label: '总阶段', value: `${phases.length}个`, status: 'normal' },
        { label: '已完成', value: `${completed}个`, status: completed > 0 ? 'normal' : 'warning' },
        { label: '进行中', value: `${active}个`, status: active > 0 ? 'warning' : 'normal' }
      ],
      reasoning: ms.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: ms.quickQuestions || []
    }
  },

  // 可信管理
  trust(project) {
    const td = project.trustDetails || {}
    const dimensions = [
      { label: '产品定义', data: td.productDefinition },
      { label: '设计', data: td.design },
      { label: '编码', data: td.coding },
      { label: '构建', data: td.build },
      { label: '测试', data: td.testing },
      { label: 'E2E保护', data: td.e2eProtection },
      { label: '开源', data: td.openSource },
      { label: '漏洞管理', data: td.vulnerability },
      { label: '生命周期', data: td.lifecycle }
    ].filter(d => d.data)

    const totalOk = dimensions.reduce((s, d) => s + (d.data.ok || 0), 0)
    const totalAll = dimensions.reduce((s, d) => s + (d.data.total || 0), 0)
    const rate = totalAll > 0 ? Math.round(totalOk / totalAll * 100) : 0

    const risks = td.risks || []
    // 找达标率最低的维度
    const worstDim = [...dimensions].sort((a, b) => {
      const ra = a.data.total > 0 ? (a.data.ok || 0) / a.data.total : 1
      const rb = b.data.total > 0 ? (b.data.ok || 0) / b.data.total : 1
      return ra - rb
    })[0]

    return {
      title: '可信管理分析',
      subtitle: project.name || '',
      progress: [
        { label: '整体达标率', value: `${rate}%`, status: rate < 30 ? 'danger' : (rate < 70 ? 'warning' : 'normal') },
        { label: '通过/总数', value: `${totalOk}/${totalAll}`, status: 'normal' },
        ...(worstDim ? [{ label: '最弱维度', value: worstDim.label, status: 'warning' }] : [])
      ],
      reasoning: td.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: td.quickQuestions || []
    }
  },

  // 可信子卡片（9宫格单项）
  trustSubcard(project, extra) {
    const td = project.trustDetails || {}
    const key = extra.key
    const dim = td[key]
    if (!dim) return { title: '可信分析', reasoning: '暂无数据' }

    const rate = dim.total > 0 ? Math.round((dim.ok || 0) / dim.total * 100) : 0

    // 从全局 risks 中筛出与该维度相关的风险
    const dimLabel = extra.label || key
    const allRisks = td.risks || []
    const relatedRisks = allRisks.filter(r => {
      const text = (r.text || r.title || '').toLowerCase()
      return text.includes(dimLabel) || text.includes(key.toLowerCase())
    })

    // 如果没有直接匹配的风险，构造一个达标率风险
    const risks = relatedRisks.length > 0
      ? formatRisks(relatedRisks)
      : rate < 70
        ? [{
            level: rate < 30 ? 'danger' : 'warning',
            title: `${dimLabel}达标率${rate}%`,
            detail: `当前${dimLabel}维度共${dim.total}项指标，已通过${dim.ok || 0}项，达标率${rate}%`,
            impact: rate < 30 ? '达标率极低，可能影响TR准入和发布安全' : '达标率偏低，需关注可能影响后续节点',
            suggestion: `建议针对未通过的${dim.total - (dim.ok || 0)}项指标制定改进计划`
          }]
        : [{
            level: 'normal',
            title: `${dimLabel}达标率正常`,
            detail: `当前${dimLabel}维度达标率${rate}%，运行正常`,
            impact: '暂无影响',
            suggestion: '继续保持'
          }]

    return {
      title: `可信分析 · ${dimLabel}`,
      subtitle: project.name || '',
      progress: [
        { label: '达标率', value: `${rate}%`, status: rate < 30 ? 'danger' : (rate < 70 ? 'warning' : 'normal') },
        { label: '通过/总数', value: `${dim.ok || 0}/${dim.total || 0}`, status: 'normal' }
      ],
      reasoning: dim.aiSummary || '',
      risks,
      quickQuestions: [
        `${dimLabel}维度的改进重点是什么？`,
        `如何快速提升${dimLabel}达标率？`,
        `${dimLabel}维度的风险对整体项目有何影响？`
      ]
    }
  },

  // 范围管理
  scope(project) {
    const scope = project.scope || {}
    const total = (scope.baseline || 0) + (scope.pending || 0) + (scope.inProgress || 0)
    const risks = scope.risks || []

    return {
      title: '范围管理分析',
      subtitle: project.name || '',
      progress: [
        { label: '需求总数', value: `${total}项`, status: 'normal' },
        { label: '已基线', value: `${scope.baseline || 0}项`, status: (scope.baseline || 0) > 0 ? 'normal' : 'warning' },
        { label: '进行中', value: `${scope.inProgress || 0}项`, status: 'normal' },
        { label: '待处理', value: `${scope.pending || 0}项`, status: (scope.pending || 0) > 0 ? 'warning' : 'normal' }
      ],
      reasoning: scope.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: scope.quickQuestions || []
    }
  },

  // 质量管理
  quality(project) {
    const q = project.quality || {}
    const risks = q.risks || []
    const di = q.di || 0

    return {
      title: '质量管理分析',
      subtitle: project.name || '',
      progress: [
        { label: 'DI值', value: di, status: di > 100 ? 'danger' : (di > 50 ? 'warning' : 'normal') },
        { label: '缺陷数', value: `${q.defects || 0}个`, status: (q.defects || 0) > 10 ? 'danger' : 'normal' },
        { label: '告警数', value: `${q.warnings || 0}个`, status: (q.warnings || 0) > 0 ? 'warning' : 'normal' },
        { label: '解决率', value: `${q.resolveRate || 0}%`, status: (q.resolveRate || 0) < 80 ? 'warning' : 'normal' }
      ],
      reasoning: q.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: q.quickQuestions || []
    }
  },

  // 进度管理
  schedule(project) {
    const s = project.schedule || {}
    const risks = s.risks || []

    return {
      title: '进度管理分析',
      subtitle: project.name || '',
      progress: [
        { label: '迭代进度', value: `${s.iterProgress || 0}%`, status: (s.iterProgress || 0) >= 60 ? 'normal' : 'warning' },
        { label: '测试进度', value: `${s.testProgress || 0}%`, status: (s.testProgress || 0) >= 50 ? 'normal' : 'warning' },
        { label: '通过率', value: `${s.passRate || 0}%`, status: (s.passRate || 0) >= 90 ? 'normal' : 'danger' },
        { label: '失败数', value: `${s.failed || 0}个`, status: (s.failed || 0) > 0 ? 'danger' : 'normal' }
      ],
      reasoning: s.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: s.quickQuestions || []
    }
  },

  // 费用执行
  budget(project) {
    const b = project.budget || {}
    const risks = b.risks || []

    return {
      title: '费用执行分析',
      subtitle: project.name || '',
      progress: [
        { label: '总预算', value: `${b.total || 0}M`, status: 'normal' },
        { label: '已执行', value: `${b.executed || 0}M`, status: 'normal' },
        { label: '执行率', value: `${b.executionRate || 0}%`, status: (b.executionRate || 0) > 90 ? 'warning' : 'normal' }
      ],
      reasoning: b.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: b.quickQuestions || []
    }
  },

  // 五领域（通用）
  workflow(project, extra) {
    const wf = project.workflow || {}
    const domain = extra.domain || 'dev'
    const data = wf[domain]
    if (!data) return { title: '作业流分析', reasoning: '暂无数据' }

    const risks = data.risks || []

    const domainLabels = {
      design: '设计领域', dev: '开发领域', build: '构建领域',
      test: '测试领域', release: '发布领域'
    }

    return {
      title: `${domainLabels[domain] || domain}分析`,
      subtitle: project.name || '',
      progress: [
        { label: '状态', value: statusText(data.status), status: data.status === 'green' ? 'normal' : (data.status === 'warning' ? 'warning' : 'danger') }
      ],
      reasoning: data.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: data.quickQuestions || []
    }
  },

  // 项目群总览
  groupSummary(groupMeta, extra) {
    const summary = extra.summary || {}
    const risks = summary.risks || []
    return {
      title: '项目群智能评估',
      subtitle: summary.name || '',
      progress: [
        { label: '项目群数', value: `${extra.groupCount || 3}个`, status: 'normal' },
        { label: '关键风险', value: `${risks.filter(r => r.level === 'critical').length}项`, status: risks.some(r => r.level === 'critical') ? 'danger' : 'normal' },
        { label: '关注风险', value: `${risks.filter(r => r.level === 'warning').length}项`, status: risks.some(r => r.level === 'warning') ? 'warning' : 'normal' }
      ],
      reasoning: summary.aiSummary || '',
      risks: formatRisks(risks.slice(0, 5)),
      quickQuestions: summary.quickQuestions || []
    }
  },

  // 单个项目群
  group(groupMeta, extra) {
    const risks = groupMeta.risks || []
    return {
      title: `${groupMeta.name || '项目群'}分析`,
      subtitle: groupMeta.name || '',
      progress: [
        { label: '子项目数', value: `${groupMeta.projectCount || 0}个`, status: 'normal' },
        { label: '整体进度', value: `${groupMeta.overallProgress || 0}%`, status: (groupMeta.overallProgress || 0) >= 60 ? 'normal' : 'warning' },
        { label: '风险数', value: `${risks.length}项`, status: risks.some(r => r.level === 'critical') ? 'danger' : 'normal' }
      ],
      reasoning: groupMeta.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: groupMeta.quickQuestions || []
    }
  },

  // 子项目全维度汇总（点击子项目卡片 / AI 按钮触发）
  subProject(project) {
    const name = project.name || project.id || ''
    const progress = project.progress || 0
    const milestoneStatus = project.milestone?.status || ''

    // 汇聚全维度风险（不含可信9宫格子维度，避免与顶层可信风险重叠）
    const allRisks = []

    // 里程碑风险
    if (project.milestone?.risks?.length) {
      allRisks.push(...project.milestone.risks)
    }
    // 可信风险
    if (project.trustDetails?.risks?.length) {
      allRisks.push(...project.trustDetails.risks)
    }
    // 范围风险
    if (project.scope?.risks?.length) {
      allRisks.push(...project.scope.risks)
    }
    // 进度风险
    if (project.schedule?.risks?.length) {
      allRisks.push(...project.schedule.risks)
    }
    // 质量风险
    if (project.quality?.risks?.length) {
      allRisks.push(...project.quality.risks)
    }
    // 资源风险
    if (project.resource?.risks?.length) {
      allRisks.push(...project.resource.risks)
    }
    // 费用风险
    if (project.budget?.risks?.length) {
      allRisks.push(...project.budget.risks)
    }
    // 不含作业流风险：作业流是从流程阶段视角展示同一批风险，与维度风险大量重叠，
    // 点击作业流 tab 时有自己的专属分析视图，全维度汇总不应重复展示

    // 统计
    const criticalCount = allRisks.filter(r => normalizeLevel(r.level) === 'danger').length
    const warningCount = allRisks.filter(r => normalizeLevel(r.level) === 'warning').length

    // 猜你想问：汇聚各维度
    const allQuestions = []
    if (project.milestone?.quickQuestions) allQuestions.push(...project.milestone.quickQuestions)
    if (project.trustDetails?.quickQuestions) allQuestions.push(...project.trustDetails.quickQuestions)
    if (project.scope?.quickQuestions) allQuestions.push(...project.scope.quickQuestions)
    if (project.schedule?.quickQuestions) allQuestions.push(...project.schedule.quickQuestions)
    if (project.quality?.quickQuestions) allQuestions.push(...project.quality.quickQuestions)

    return {
      title: `${name} 全维度分析`,
      subtitle: name,
      progress: [
        { label: '整体进度', value: `${progress}%`, status: progress >= 60 ? 'normal' : 'warning' },
        { label: '里程碑', value: milestoneStatus || '-', status: project.milestone?.statusColor === 'red' ? 'danger' : (project.milestone?.statusColor === 'yellow' ? 'warning' : 'normal') },
        { label: '关键风险', value: `${criticalCount}项`, status: criticalCount > 0 ? 'danger' : 'normal' },
        { label: '关注风险', value: `${warningCount}项`, status: warningCount > 0 ? 'warning' : 'normal' }
      ],
      reasoning: project.aiSummary || project.trustDetails?.aiSummary || '',
      risks: formatRisks(allRisks),
      quickQuestions: [...new Set(allQuestions)].slice(0, 5)
    }
  },

  // 子项目维度（可信/范围/进度/质量/资源）
  subProjectDimension(project, extra) {
    const dim = extra.dim
    if (!dim) return { title: '维度分析', reasoning: '暂无数据' }

    const dimKey = dim.key
    let risks = []
    let aiSummary = ''
    let questions = []
    let progressItems = []

    if (dimKey === 'trust') {
      const data = project.trustDetails || {}
      risks = data.risks || []
      aiSummary = data.aiSummary || ''
      questions = data.quickQuestions || []
      const score = data.overallScore || 0
      progressItems = [
        { label: '可信评分', value: `${score}分`, status: score >= 80 ? 'normal' : (score >= 60 ? 'warning' : 'danger') },
        { label: '状态', value: data.status || '-', status: score >= 80 ? 'normal' : 'warning' }
      ]
    } else if (dimKey === 'scope') {
      const data = project.scope || {}
      risks = data.risks || []
      aiSummary = data.aiSummary || ''
      questions = data.quickQuestions || []
      const total = (data.baseline || 0) + (data.pending || 0) + (data.inProgress || 0)
      progressItems = [
        { label: '需求总数', value: `${total}项`, status: 'normal' },
        { label: '已基线', value: `${data.baseline || 0}项`, status: (data.baseline || 0) > 0 ? 'normal' : 'warning' },
        { label: '状态', value: data.text || '-', status: data.status === 'green' ? 'normal' : 'warning' }
      ]
    } else if (dimKey === 'schedule') {
      const data = project.schedule || {}
      risks = data.risks || []
      aiSummary = data.aiSummary || ''
      questions = data.quickQuestions || []
      progressItems = [
        { label: '迭代进度', value: `${data.iterProgress || 0}%`, status: (data.iterProgress || 0) >= 60 ? 'normal' : 'warning' },
        { label: '测试进度', value: `${data.testProgress || 0}%`, status: (data.testProgress || 0) >= 50 ? 'normal' : 'warning' },
        { label: '通过率', value: `${data.passRate || 0}%`, status: (data.passRate || 0) >= 90 ? 'normal' : 'danger' }
      ]
    } else if (dimKey === 'quality') {
      const data = project.quality || {}
      risks = data.risks || []
      aiSummary = data.aiSummary || ''
      questions = data.quickQuestions || []
      const di = data.di || 0
      progressItems = [
        { label: 'DI值', value: di, status: di > 100 ? 'danger' : (di > 50 ? 'warning' : 'normal') },
        { label: '缺陷数', value: `${data.defects || 0}个`, status: (data.defects || 0) > 10 ? 'danger' : 'normal' },
        { label: '解决率', value: `${data.resolveRate || 0}%`, status: (data.resolveRate || 0) < 80 ? 'warning' : 'normal' }
      ]
    } else if (dimKey === 'resource') {
      const data = project.resource || {}
      risks = data.risks || []
      aiSummary = data.text ? `${data.text}，开发${data.dev || 0}人/测试${data.test || 0}人` : ''
      questions = data.quickQuestions || ['资源到位情况如何？', '人力缺口如何补齐？', '资源复用规划？']
      progressItems = [
        { label: '开发人力', value: `${data.dev || 0}人`, status: 'normal' },
        { label: '测试人力', value: `${data.test || 0}人`, status: 'normal' },
        { label: '状态', value: data.text || '-', status: data.status === 'green' ? 'normal' : 'warning' }
      ]
    }

    return {
      title: `${dim.label}维度分析`,
      subtitle: project.name || project.id || '',
      progress: progressItems,
      reasoning: aiSummary,
      risks: formatRisks(risks),
      quickQuestions: questions
    }
  },

  // AI 总结条（风险项点击）
  aiSummary(project, extra) {
    const risk = extra.risk
    if (!risk) return { title: 'AI 分析', reasoning: '暂无数据' }

    const riskType = risk.type || ''
    const typeQuestions = {
      '里程碑': ['该风险对后续节点有何影响？', '有哪些具体的应对方案？', '需要协调哪些资源？'],
      '可信': ['可信问题的根本原因是什么？', '如何提升代码可信度？', '安全加固的优先级排序？'],
      '范围': ['需求变更的频率如何？', '需求冻结的时间节点？', '范围蔓延如何控制？'],
      '质量': ['缺陷集中的模块有哪些？', '代码质量如何提升？', '测试覆盖率是否达标？'],
      '进度': ['进度延迟的根因是什么？', '关键路径上的阻塞因素？', '资源瓶颈在哪里？'],
      '费用': ['费用超支的主要原因？', '预算调整的空间有多大？', '成本控制的关键措施？']
    }

    // 优先使用外部传入的问题（如项目群级的专属问题）
    const questions = extra.questions || typeQuestions[riskType] || [
      '该问题的主要风险点是什么？',
      '有哪些具体的应对建议？',
      '对其他领域有什么影响？'
    ]

    return {
      title: risk.title || '风险详情',
      subtitle: project.name || '',
      progress: [
        { label: '风险级别', value: riskLevelText(risk.level), status: risk.level === 'critical' || risk.level === 'danger' ? 'danger' : (risk.level === 'warning' ? 'warning' : 'normal') },
        { label: '来源', value: risk.type || '-', status: 'normal' }
      ],
      reasoning: '',
      risks: [formatSingleRisk(risk)],
      quickQuestions: questions
    }
  }
}

// ========== 工具函数 ==========

/**
 * 格式化风险列表 — 将原始风险数据转为侧边栏展示格式
 * 确保每个风险都有 detail/impact/suggestion 三个完整字段
 */
function formatRisks(risks) {
  if (!risks || !risks.length) return []
  // 按风险等级排序：danger > warning > normal
  const levelOrder = { danger: 0, warning: 1, normal: 2 }
  const sorted = [...risks].sort((a, b) =>
    (levelOrder[normalizeLevel(a.level)] ?? 3) - (levelOrder[normalizeLevel(b.level)] ?? 3)
  )
  return sorted.map(r => formatSingleRisk(r))
}

/**
 * 格式化单个风险 — 严格输出 detail(风险详情) + impact(影响范围) + suggestion(应对建议)
 */
function formatSingleRisk(r) {
  const level = normalizeLevel(r.level)
  return {
    level,
    title: r.title || r.text || '',
    detail: r.rootCause || r.why || r.text || r.desc || '暂无详情',
    impact: r.impact || inferImpact(r),
    suggestion: r.suggestion || r.how || inferSuggestion(r)
  }
}

function normalizeLevel(level) {
  if (level === 'critical' || level === 'danger' || level === 'high' || level === '红') return 'danger'
  if (level === 'warning' || level === 'medium' || level === '黄') return 'warning'
  return 'normal'
}

function inferImpact(r) {
  const level = normalizeLevel(r.level)
  if (level === 'danger') return '需立即关注和处理，可能影响项目交付节点'
  if (level === 'warning') return '建议持续跟踪，可能影响后续推进'
  return '暂无影响'
}

function inferSuggestion(r) {
  const level = normalizeLevel(r.level)
  if (level === 'danger') return '建议立即组织专项会议，制定应对计划'
  if (level === 'warning') return '建议重点跟进，确认资源充足'
  return '继续保持'
}

function getMaxRiskLevel(risks) {
  if (!risks?.length) return 'normal'
  if (risks.some(r => normalizeLevel(r.level) === 'danger')) return 'danger'
  if (risks.some(r => normalizeLevel(r.level) === 'warning')) return 'warning'
  return 'normal'
}

function statusText(status) {
  const map = { green: '正常', yellow: '关注', red: '异常', warning: '关注', critical: '异常', normal: '正常' }
  return map[status] || status || '未知'
}

function riskLevelText(level) {
  const map = { critical: '关键', danger: '危险', warning: '一般', normal: '低', info: '信息' }
  return map[level] || level || '未知'
}

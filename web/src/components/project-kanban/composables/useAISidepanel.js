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
  },

  // ===== 部门级 builder =====
  // 传入的 projectData 是整个 deptData 对象，数据在 projectData.department 下

  'milestone-dept'(deptData, extra) {
    const ms = deptData?.department?.milestone || {}
    const timeline = ms.timeline || []

    // 点击单个 timeline 子卡片：展示该 offering 的详细分析
    if (extra?.timelineItem) {
      const item = extra.timelineItem
      const phases = item.phases || []
      // 从 phases[].risks 汇总风险
      const risks = phases.flatMap(p => p.risks || [])
      // 关键进度：当前/下一个阶段的 objectives
      const activePhase = phases.find(p => p.status === 'pending' || p.status === 'active') || phases[phases.length - 1]
      const keyPoints = activePhase?.objectives || []

      return {
        title: `里程碑 · ${item.category} ${item.project}`,
        subtitle: item.group || '部门级',
        progress: [
          { label: '下一节点', value: item.nextMilestone || '-', status: item.deviation > 10 ? 'danger' : (item.deviation > 0 ? 'warning' : 'normal') },
          { label: '偏差', value: `${item.deviation > 0 ? '+' : ''}${item.deviation}%`, status: item.deviation > 10 ? 'danger' : (item.deviation > 0 ? 'warning' : 'normal') },
          { label: '状态', value: item.status || '-', status: item.deviation > 10 ? 'danger' : (item.deviation > 0 ? 'warning' : 'normal') }
        ],
        keyPoints,
        reasoning: item.aiSummary || ms.aiSummary || '',
        risks: formatRisks(risks),
        quickQuestions: item.quickQuestions || ms.quickQuestions || []
      }
    }

    // 默认：整体里程碑分析 — 与设计稿一致的关键进度展示
    const allPhaseRisks = []
    timeline.forEach(item => {
      (item.phases || []).forEach(p => {
        (p.risks || []).forEach(r => {
          allPhaseRisks.push({ ...r, _project: item.project, _phaseName: p.name })
        })
      })
    })
    // 给风险 title 加上项目名前缀（与设计稿一致：项目名 · 风险标题）
    const risks = allPhaseRisks.slice(0, 5).map(r => ({
      ...r,
      title: r._project ? `${r._project} · ${r.title || r.text || ''}` : (r.title || r.text || '')
    }))
    const totalCount = timeline.length
    // 有风险的项目数（某个 offering 的某个 phase 有非 normal 风险）
    const riskProjectNames = [...new Set(
      allPhaseRisks
        .filter(r => normalizeLevel(r.level) !== 'normal')
        .map(r => r._project)
    )]
    const normalCount = totalCount - riskProjectNames.length

    // 焦点风险：风险最高的项目+阶段名（与设计稿一致：clickProject.project + ' ' + clickProject.phaseName）
    const topRisk = allPhaseRisks.find(r => normalizeLevel(r.level) === 'danger')
      || allPhaseRisks.find(r => normalizeLevel(r.level) === 'warning')
    const focusText = topRisk ? `${topRisk._project} ${topRisk._phaseName}` : ''
    const focusLevel = ms.statusType === 'red' ? 'danger' : (ms.statusType === 'yellow' ? 'warning' : 'normal')

    const progressItems = []
    if (focusText) {
      progressItems.push({ label: '焦点风险', value: focusText, status: focusLevel === 'danger' ? 'danger' : (focusLevel === 'warning' ? 'warning' : 'normal') })
    }
    progressItems.push({ label: 'Offering总数', value: `${totalCount}个`, status: 'normal' })
    if (riskProjectNames.length > 0) {
      progressItems.push({ label: '有风险项目', value: `${riskProjectNames.length}个`, status: 'danger' })
      progressItems.push({ label: '正常推进', value: `${normalCount}个`, status: 'normal' })
    } else {
      progressItems.push({ label: '整体状态', value: '正常', status: 'normal' })
    }

    return {
      title: '里程碑详情分析',
      subtitle: '部门级',
      progress: progressItems,
      reasoning: ms.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: ms.quickQuestions || []
    }
  },

  ahb(deptData, extra) {
    const ahb = deptData?.department?.ahb || {}
    const categories = ahb.categories || {}
    const catList = Object.values(categories)

    // 汇总人力数据
    const totalCapacity = catList.reduce((s, c) => s + (c.total || 0), 0)
    const totalWorkload = catList.reduce((s, c) => s + (c.workload || 0), 0)
    const utilRate = totalCapacity > 0 ? Math.round(totalWorkload / totalCapacity * 100) : 0

    // 从 categories[].risks 汇总风险（带分类名前缀，与设计稿一致：catName · r.title）
    const risks = []
    Object.entries(categories).forEach(([catName, catData]) => {
      (catData.risks || []).forEach(r => {
        risks.push({ ...r, title: `${catData.label || catName} · ${r.title || ''}` })
      })
    })

    // 如果有子分类点击的上下文，优先展示子分类数据
    if (extra?.category) {
      const cat = extra.category
      const catUtil = cat.total > 0 ? Math.round((cat.workload || 0) / cat.total * 100) : 0
      const catRisks = cat.risks || []
      // 关键进度：角色分布
      const keyPoints = []
      if (cat.roles) {
        Object.entries(cat.roles).forEach(([role, data]) => {
          keyPoints.push(`${role === 'dev' ? '开发' : role === 'test' ? '测试' : 'PM'}: 自有${data.internal}人、OD${data.od}人、外包${data.outsource}人`)
        })
      }

      return {
        title: `AHB人力 · ${cat.label || ''}`,
        subtitle: '部门级',
        progress: [
          { label: '工作量', value: `${cat.workload || 0}人月`, status: 'normal' },
          { label: '人力', value: `${cat.total || 0}人月`, status: 'normal' },
          { label: '利用率', value: `${catUtil}%`, status: catUtil > 100 ? 'danger' : (catUtil > 90 ? 'warning' : 'normal') },
          { label: '偏差', value: `${cat.deviation > 0 ? '+' : ''}${cat.deviation || 0}人月`, status: Math.abs(cat.deviation || 0) > 10 ? 'danger' : (Math.abs(cat.deviation || 0) > 5 ? 'warning' : 'normal') }
        ],
        keyPoints,
        reasoning: cat.aiSummary || ahb.aiSummary || '',
        risks: formatRisks(catRisks),
        quickQuestions: cat.quickQuestions || ahb.quickQuestions || []
      }
    }

    // 默认：整体AHB分析 — 与设计稿一致的关键进度展示
    const totalDeviation = catList.reduce((s, c) => s + (c.deviation || 0), 0)

    const progressItems = []
    // 焦点问题：直接使用一句话总结文本（与设计稿一致，focus = aiSummary 全文）
    const focusText = ahb.aiSummary || ''
    if (focusText) {
      const focusStatus = ahb.statusType === 'red' ? 'danger' : (ahb.statusType === 'yellow' ? 'warning' : 'normal')
      progressItems.push({ label: '焦点问题', value: focusText, status: focusStatus })
    }
    progressItems.push({ label: '总人力容量', value: `${totalCapacity}人月`, status: 'normal' })
    progressItems.push({ label: '已分配工作量', value: `${totalWorkload}人月`, status: utilRate > 100 ? 'danger' : 'normal' })
    progressItems.push({ label: '利用率', value: `${utilRate}%`, status: utilRate > 100 ? 'danger' : (utilRate > 90 ? 'warning' : 'normal') })
    progressItems.push({ label: '偏差', value: `${totalDeviation > 0 ? '+' : ''}${totalDeviation}人月`, status: totalDeviation < 0 ? 'danger' : (totalDeviation > 10 ? 'warning' : 'normal') })

    // 各分类详情（与设计稿一致）
    Object.entries(categories).forEach(([, catData]) => {
      const catLabel = catData.label || ''
      const catDev = catData.deviation || 0
      progressItems.push({
        label: catLabel,
        value: `工作量${catData.workload}/容量${catData.total}（偏差${catDev > 0 ? '+' : ''}${catDev}）`,
        status: catDev < 0 ? 'danger' : 'normal'
      })
    })

    return {
      title: 'AHB人力分析',
      subtitle: '部门级',
      progress: progressItems,
      reasoning: ahb.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: ahb.quickQuestions || []
    }
  },

  'budget-dept'(deptData, extra) {
    const budget = deptData?.department?.budget || {}
    const projects = budget.projects || []

    // 从 projects[].risks 汇总风险（带项目类别前缀，与设计稿一致：proj.category · r.title）
    const risks = []
    projects.forEach(proj => {
      (proj.risks || []).forEach(r => {
        risks.push({ ...r, title: `${proj.category || proj.name || ''} · ${r.title || ''}` })
      })
    })

    // 如果有项目点击的上下文
    if (extra?.project) {
      const proj = extra.project
      const rate = proj.budget > 0 ? Math.round((proj.executed || 0) / proj.budget * 100) : 0
      const projRisks = proj.risks || []
      return {
        title: `费用执行 · ${proj.name || ''}`,
        subtitle: '部门级',
        progress: [
          { label: '预算', value: `${proj.budget || 0}M`, status: 'normal' },
          { label: '已执行', value: `${proj.executed || 0}M`, status: 'normal' },
          { label: '执行率', value: `${rate}%`, status: rate < 70 ? 'warning' : 'normal' }
        ],
        reasoning: proj.aiSummary || budget.aiSummary || '',
        risks: formatRisks(projRisks),
        quickQuestions: proj.quickQuestions || budget.quickQuestions || []
      }
    }

    const totalBudget = projects.reduce((s, p) => s + (p.budget || 0), 0)
    const totalExecuted = projects.reduce((s, p) => s + (p.executed || 0), 0)
    const execRate = budget.executionRate || (totalBudget > 0 ? Math.round(totalExecuted / totalBudget * 100) : 0)

    // 关键进度：与设计稿一致 — 焦点问题 + 预算总额 + 已执行 + 执行率
    const progressItems = []
    // 焦点问题：直接使用一句话总结文本（与设计稿一致，focus = aiSummary 全文）
    const focusText = budget.aiSummary || ''
    if (focusText) {
      const focusStatus = budget.statusType === 'red' ? 'danger' : (budget.statusType === 'yellow' ? 'warning' : 'normal')
      progressItems.push({ label: '焦点问题', value: focusText, status: focusStatus })
    }
    progressItems.push({ label: '预算总额', value: `${budget.total || totalBudget}M`, status: 'normal' })
    progressItems.push({ label: '已执行', value: `${budget.executed || totalExecuted}M`, status: 'normal' })
    progressItems.push({ label: '执行率', value: `${execRate}%`, status: execRate >= 80 ? 'normal' : (execRate >= 60 ? 'warning' : 'danger') })

    return {
      title: '费用执行详情分析',
      subtitle: '部门级',
      progress: progressItems,
      reasoning: budget.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: budget.quickQuestions || []
    }
  },

  'task-dept'(deptData, extra) {
    const task = deptData?.department?.task || {}
    const taskOrders = task.taskOrders || []

    // 从 taskOrders[].risks 汇总风险（带分组前缀，与设计稿一致：order.group · r.title）
    const risks = []
    taskOrders.forEach(order => {
      (order.risks || []).forEach(r => {
        risks.push({ ...r, title: `${order.group || order.industry || ''} · ${r.title || ''}` })
      })
    })

    // 如果有任务令点击的上下文
    if (extra?.taskOrder) {
      const to = extra.taskOrder
      const toRisks = to.risks || []
      // 关键进度：phases
      const keyPoints = (to.phases || []).map(p => `${p.name}(${p.date}): ${p.status === 'completed' ? '已完成' : p.status === 'active' ? '进行中' : '待启动'}`)

      return {
        title: `任务令 · ${to.name || ''}`,
        subtitle: to.project || '部门级',
        progress: [
          { label: '进度', value: `${to.progress || 0}%`, status: (to.progress || 0) >= 60 ? 'normal' : 'warning' },
          { label: '行业', value: to.industry || '-', status: 'normal' },
          { label: '负责人', value: to.owner || '-', status: 'normal' },
          { label: '截止', value: to.deadline || '-', status: to.status === 'overdue' ? 'danger' : 'normal' }
        ],
        keyPoints,
        reasoning: task.aiSummary || '',
        risks: formatRisks(toRisks),
        quickQuestions: to.quickQuestions || task.quickQuestions || []
      }
    }

    const completed = taskOrders.filter(o => o.progress >= 100 || o.status === 'completed').length
    const avgProgress = taskOrders.length > 0 ? Math.round(taskOrders.reduce((s, o) => s + (o.progress || 0), 0) / taskOrders.length) : 0

    // 关键进度：与设计稿一致 — 焦点风险 + 总数 + 高/中风险 + 已完成
    const criticalOrders = taskOrders.filter(o => o.risk === 'high' || o.status === 'overdue')
    const warningOrders = taskOrders.filter(o => o.risk === 'medium')
    const totalCount = taskOrders.length

    const progressItems = []
    // 焦点风险：最高风险任务令名称（与设计稿一致：topRiskOrder.name）
    const topRiskOrder = criticalOrders[0] || warningOrders[0]
    if (topRiskOrder) {
      progressItems.push({ label: '焦点风险', value: topRiskOrder.name, status: criticalOrders.length > 0 ? 'danger' : 'warning' })
    }
    progressItems.push({ label: '任务令总数', value: `${totalCount}个`, status: 'normal' })
    if (criticalOrders.length > 0) {
      progressItems.push({ label: '高风险任务', value: `${criticalOrders.length}个`, status: 'danger' })
    }
    if (warningOrders.length > 0) {
      progressItems.push({ label: '中风险任务', value: `${warningOrders.length}个`, status: 'warning' })
    }
    progressItems.push({ label: '已完成', value: `${completed}个`, status: 'normal' })

    return {
      title: '任务令详情分析',
      subtitle: '部门级',
      progress: progressItems,
      reasoning: task.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: task.quickQuestions || []
    }
  },

  'groups-overview'(deptData, extra) {
    const go = deptData?.department?.groupsOverview || {}

    // 点击单个维度卡片
    if (extra?.dimension) {
      const dim = extra.dimension
      const dimKey = dim.key
      let dimData = null
      let risks = []

      if (dimKey === 'projectRisk') {
        dimData = go.projectRisk || {}
        risks = dimData.risks || []
      } else if (dimKey === 'online') {
        dimData = go.online || {}
        risks = dimData.risks || []
      } else if (dimKey === 'downstream') {
        dimData = go.downstream || {}
        risks = dimData.risks || []
      } else if (dimKey === 'trust') {
        dimData = go.trustSummary || {}
        risks = dimData.risks || []
      }

      return {
        title: `${dim.label || dimKey}分析`,
        subtitle: '部门级',
        progress: (dim.stats || []).map(s => ({
          label: s.label,
          value: s.value,
          status: s.class?.includes('danger') ? 'danger' : (s.class?.includes('warning') ? 'warning' : 'normal')
        })),
        reasoning: dimData?.aiSummary || dim.sentence || '',
        risks: formatRisks(risks),
        quickQuestions: dimData?.quickQuestions || []
      }
    }

    // 点击单个项目群卡片中的风险
    if (extra?.risk && extra?.groupCard) {
      const gc = extra.groupCard
      const risk = extra.risk
      return {
        title: `${gc.name || '项目群'}风险分析`,
        subtitle: gc.targetProject || '部门级',
        progress: [
          { label: '项目数', value: `${gc.projectCount || 0}个`, status: 'normal' },
          { label: '整体进度', value: `${gc.overallProgress || 0}%`, status: (gc.overallProgress || 0) >= 60 ? 'normal' : 'warning' },
          { label: '风险数', value: `${(gc.risks || []).length}项`, status: (gc.risks || []).some(r => r.level === 'critical') ? 'danger' : 'normal' }
        ],
        reasoning: gc.aiSummary || '',
        risks: formatRisks(gc.risks || []),
        quickQuestions: gc.quickQuestions || []
      }
    }

    // 默认：整体综合风险分析
    const pr = go.projectRisk || {}
    const risks = pr.risks || []

    return {
      title: '项目群综合风险分析',
      subtitle: '部门级',
      progress: [
        { label: '项目群数', value: `${pr.groupCount || 0}个`, status: 'normal' },
        { label: '高风险', value: `${pr.criticalCount || 0}项`, status: (pr.criticalCount || 0) > 0 ? 'danger' : 'normal' },
        { label: '中风险', value: `${pr.warningCount || 0}项`, status: (pr.warningCount || 0) > 0 ? 'warning' : 'normal' },
        { label: '正常', value: `${pr.normalCount || 0}项`, status: 'normal' }
      ],
      reasoning: pr.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: pr.quickQuestions || []
    }
  },

  dim(deptData, extra) {
    const dim = extra.dimension
    if (!dim) return { title: '维度分析', reasoning: '暂无数据' }

    return {
      title: `${dim.label || ''}分析`,
      subtitle: '部门级',
      progress: (dim.stats || []).map(s => ({
        label: s.label,
        value: s.value,
        status: 'normal'
      })),
      reasoning: dim.sentence || '',
      risks: [],
      quickQuestions: []
    }
  },

  groupRisk(deptData, extra) {
    const gc = extra?.groupCard
    if (!gc) return { title: '项目群风险分析', reasoning: '暂无数据' }

    const risks = gc.risks || []
    return {
      title: `${gc.name || '项目群'}风险分析`,
      subtitle: gc.targetProject || '部门级',
      progress: [
        { label: '项目数', value: `${gc.projectCount || 0}个`, status: 'normal' },
        { label: '整体进度', value: `${gc.overallProgress || 0}%`, status: (gc.overallProgress || 0) >= 60 ? 'normal' : 'warning' },
        { label: '风险数', value: `${risks.length}项`, status: risks.some(r => r.level === 'critical') ? 'danger' : 'normal' }
      ],
      reasoning: gc.aiSummary || '',
      risks: formatRisks(risks),
      quickQuestions: gc.quickQuestions || []
    }
  },

  deptQuestion(deptData) {
    const questions = deptData?.quickQuestions || []
    const dept = deptData?.department || {}
    return {
      title: 'AI 问答',
      subtitle: '部门级',
      progress: [
        { label: '里程碑', value: dept.milestone?.status || '-', status: dept.milestone?.statusType === 'red' ? 'danger' : (dept.milestone?.statusType === 'yellow' ? 'warning' : 'normal') },
        { label: '任务令', value: dept.task?.status || '-', status: dept.task?.statusType === 'red' ? 'danger' : (dept.task?.statusType === 'yellow' ? 'warning' : 'normal') },
        { label: '费用', value: dept.budget?.status || '-', status: dept.budget?.statusType === 'red' ? 'danger' : (dept.budget?.statusType === 'yellow' ? 'warning' : 'normal') }
      ],
      reasoning: '',
      risks: [],
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

/**
 * 项目群级看板 Mock 数据
 * 从 project-manager2/js/data/group-data.js 完整同步，转为 ES Module
 *
 * ⚠️ 此文件为设计稿数据的 1:1 映射，仅导出与设计稿一致的 groupData 对象
 *    如需派生数据（groupKeys/getSubProjects/getRiskDimensions），请在组件中计算
 *    如需修改数据结构，请先修改设计稿源文件，再同步到此
 */

export const groupData = {
  "summary": {
    "name": "项目群总览",
    "aiSummary": "部门整体风险可控。\nV3项目面临最大压力，301.1.0 TR5节点延误概率>80%，建议重点关注；V2和MCU整体平稳，无重大阻塞风险。",
    "risks": [
      { "level": "critical", "title": "301.1.0 TR5节点延误概率>80%", "source": "301.1.0", "rootCause": "迭代1延期5天，编码进度滞后导致测试时间被压缩", "impact": "下游集成计划延后，影响客户交付承诺", "suggestion": "建议PM立即召集核心开发评审，目标3天内追回3天进度" },
      { "level": "warning", "title": "208.10.0安全加固滞后2周", "source": "208.10.0", "rootCause": "安全模块开发人员被抽调至301.1.0应急", "impact": "影响TR4审视节点达成", "suggestion": "建议申请安全专家支援" },
      { "level": "warning", "title": "208.10.0测试人力缺口2人", "source": "208.10.0", "rootCause": "测试团队被301.1.0借调2人", "impact": "测试进度42%，存在覆盖不足风险", "suggestion": "建议申请2名合作方测试人员支撑" },
      { "level": "warning", "title": "301.1.0测试人力缺口4人", "source": "301.1.0", "rootCause": "计划12人，实际到位8人", "impact": "测试进度仅37%，无法支撑TR5节点", "suggestion": "建议从208.10.0借调2名测试工程师临时支撑" },
      { "level": "warning", "title": "301.1.0 DI值45分超标", "source": "301.1.0", "rootCause": "静态检查告警680条，代码评审覆盖不足", "impact": "TR5准入门槛未达，可能触发质量门禁拦截", "suggestion": "启动DI专项整改，目标TR5前将DI降至30以下" },
      { "level": "normal", "title": "1.1.0遗留2个低优先级缺陷", "source": "1.1.0", "rootCause": "2个低优先级缺陷计划在下一版本修复", "impact": "暂不影响线上运行和结项评审", "suggestion": "在1.2.0版本规划中安排修复" }
    ],
    "quickQuestions": [
      "V2各版本的进度如何？",
      "208.10.0 TR4节点能如期达成吗？",
      "如何调配资源加速安全加固？",
      "V3各版本的进度如何？",
      "301.1.0 TR5节点能如期达成吗？",
      "如何解决测试人力缺口问题？",
      "MCU各版本的进度如何？",
      "1.1.0 ER评审准备情况？",
      "遗留缺陷如何处理？"
    ]
  },
  "V2": {
    "name": "RTOS V2",
    "color": "blue",
    "colorHex": "#3b82f6",
    "offerings": ["208.11.0", "208.10.0"],
    "projectCount": 2,
    "overallProgress": 65,
    "status": "normal",
    "aiSummary": "V2项目整体风险可控，208.11.0刚启动暂无明显风险，208.10.0存在安全加固进度滞后和测试人力缺口。",
    "risks": [
      { "level": "warning", "title": "208.10.0安全加固滞后2周", "source": "208.10.0", "rootCause": "安全模块开发人员被抽调至301.1.0应急", "impact": "影响TR4审视节点达成", "suggestion": "建议申请安全专家支援" },
      { "level": "warning", "title": "208.10.0测试人力缺口2人", "source": "208.10.0", "rootCause": "测试团队被301.1.0借调2人", "impact": "测试进度42%，存在覆盖不足风险", "suggestion": "建议申请2名合作方测试人员支撑" }
    ],
    "quickQuestions": [
      "V2各版本的进度如何？",
      "208.10.0 TR4节点能如期达成吗？",
      "如何调配资源加速安全加固？"
    ]
  },
  "V3": {
    "name": "RTOS V3",
    "color": "purple",
    "colorHex": "#8b5cf6",
    "offerings": ["301.1.0", "301.0.0"],
    "projectCount": 2,
    "overallProgress": 45,
    "status": "warning",
    "aiSummary": "RTOS V3项目风险较高，301.1.0面临TR5节点延误（>80%概率），主要受编码延期和测试人力缺口影响。301.0.0已完成TR5，整体风险可控。",
    "risks": [
      { "level": "critical", "title": "301.1.0 TR5节点延误概率>80%", "source": "301.1.0", "rootCause": "迭代1延期5天，编码进度滞后导致测试时间被压缩", "impact": "下游集成计划延后，影响客户交付承诺", "suggestion": "建议PM立即召集核心开发评审，目标3天内追回3天进度" },
      { "level": "warning", "title": "301.1.0测试人力缺口4人", "source": "301.1.0", "rootCause": "计划12人，实际到位8人", "impact": "测试进度仅37%，无法支撑TR5节点", "suggestion": "建议从208.10.0借调2名测试工程师临时支撑" },
      { "level": "warning", "title": "301.1.0 DI值45分超标", "source": "301.1.0", "rootCause": "静态检查告警680条，代码评审覆盖不足", "impact": "TR5准入门槛未达，可能触发质量门禁拦截", "suggestion": "启动DI专项整改，目标TR5前将DI降至30以下" }
    ],
    "quickQuestions": [
      "V3各版本的进度如何？",
      "301.1.0 TR5节点能如期达成吗？",
      "如何解决测试人力缺口问题？"
    ]
  },
  "MCU": {
    "name": "RTOS MCU",
    "color": "cyan",
    "colorHex": "#06b6d4",
    "offerings": ["1.1.0", "1.0.0"],
    "projectCount": 2,
    "overallProgress": 90,
    "status": "normal",
    "aiSummary": "MCU项目整体运行正常。1.1.0即将结项，ER评审（4/5）正常推进，遗留2个低优先级缺陷不影响结项。1.0.0已完成结项归档。",
    "risks": [
      { "level": "normal", "title": "1.1.0遗留2个低优先级缺陷", "source": "1.1.0", "rootCause": "2个低优先级缺陷计划在下一版本修复", "impact": "暂不影响线上运行和结项评审", "suggestion": "在1.2.0版本规划中安排修复" }
    ],
    "quickQuestions": [
      "MCU各版本的进度如何？",
      "1.1.0 ER评审准备情况？",
      "遗留缺陷如何处理？"
    ]
  }
};

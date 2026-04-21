/**
 * 项目级看板 Mock 数据
 * 从 project-manager/js/data/project-data.js 完整同步，转为 ES Module
 * 
 * ⚠️ 此文件为设计稿数据的 1:1 映射，请勿手动修改字段
 *    如需修改数据结构，请先修改设计稿源文件，再同步到此
 */
export const projectData = {
  "208.11.0": {
    "name": "208.11.0版本",
    "group": "V2",
    "progress": 0,
    "trustDetails": {
      "overallScore": 45,
      "status": "可信评估准备中",
      "aiSummary": "项目刚启动，可信评估工作尚未开展，各项指标待建立基线",
      "quickQuestions": [
        "可信评估准备情况如何？",
        "哪些可信指标需要优先建立基线？",
        "安全需求评审计划何时启动？"
      ],
      "productDefinition": {
        "ok": 0,
        "total": 6,
        "aiSummary": "产品定义维度共6项指标，已通过0项，整体达标率0%，需全面建立产品定义基线",
        "risks": [
          {
            "type": "可信-产品定义",
            "text": "产品定义达标率0%",
            "level": "critical",
            "title": "产品定义可信度严重不足",
            "rootCause": "6项产品定义指标均未完成，产品定义基线尚未建立",
            "impact": "产品定义不完整将影响后续设计和开发方向",
            "suggestion": "立即组织产品定义基线建立会议，协调各方完成6项指标"
          }
        ],
        "quickQuestions": [
          "产品定义当前有哪些未达标项？",
          "如何建立产品定义基线？",
          "产品定义评审预计何时启动？"
        ]
      },
      "design": {
        "ok": 1,
        "total": 8,
        "aiSummary": "设计维度共8项指标，已通过1项，整体达标率12.5%，需大力推进设计基线建设",
        "risks": [
          {
            "type": "可信-设计",
            "text": "设计达标率12.5%",
            "level": "critical",
            "title": "设计可信度严重不足",
            "rootCause": "7项设计指标未完成，设计评审和验证流程尚未建立",
            "impact": "设计流程不完善可能影响后续开发质量",
            "suggestion": "建立设计评审机制，推进设计基线建设"
          }
        ],
        "quickQuestions": [
          "设计评审流程建立进展如何？",
          "设计验证计划是什么？",
          "架构设计何时完成？"
        ]
      },
      "coding": {
        "ok": 0,
        "total": 12,
        "aiSummary": "编码维度共12项指标，已通过0项，整体达标率0%，需立即建立编码规范和质量门禁",
        "risks": [
          {
            "type": "可信-编码",
            "text": "编码达标率0%",
            "level": "critical",
            "title": "编码可信度严重不足",
            "rootCause": "项目刚启动，编码规范和CI质量门禁尚未建立",
            "impact": "编码质量无法保证，可能引入大量技术债务",
            "suggestion": "立即建立编码规范和CI质量门禁"
          }
        ],
        "quickQuestions": [
          "编码规范建立进展如何？",
          "代码质量门禁配置了吗？",
          "代码评审流程何时启动？"
        ]
      },
      "build": {
        "ok": 2,
        "total": 3,
        "aiSummary": "构建维度共3项指标，已通过2项，整体达标率66.7%，需完成构建验证流程建立",
        "risks": [
          {
            "type": "可信-构建",
            "text": "构建达标率66.7%",
            "level": "warning",
            "title": "构建验证流程待完善",
            "rootCause": "构建验证流程尚未完全建立，CI配置待完善",
            "impact": "构建流程不完善可能影响交付效率",
            "suggestion": "完成构建验证流程建立，确保CI流水线稳定"
          }
        ],
        "quickQuestions": [
          "构建验证流程完成了吗？",
          "CI流水线配置进展如何？",
          "构建环境是否就绪？"
        ]
      },
      "testing": {
        "ok": 0,
        "total": 8,
        "aiSummary": "测试维度共8项指标，已通过0项，整体达标率0%，需建立测试策略和质量门禁",
        "risks": [
          {
            "type": "可信-测试",
            "text": "测试达标率0%",
            "level": "critical",
            "title": "测试可信度严重不足",
            "rootCause": "测试策略和用例体系尚未建立，质量门禁未配置",
            "impact": "测试覆盖不足可能导致质量风险",
            "suggestion": "立即建立测试策略，完善测试用例体系"
          }
        ],
        "quickQuestions": [
          "测试策略制定进展如何？",
          "测试用例编写计划是什么？",
          "质量门禁何时配置？"
        ]
      },
      "e2eProtection": {
        "ok": 0,
        "total": 5,
        "aiSummary": "E2E保护维度共5项指标，已通过0项，整体达标率0%，需建立E2E完整性保护机制",
        "risks": [
          {
            "type": "可信-E2E保护",
            "text": "E2E保护达标率0%",
            "level": "critical",
            "title": "E2E完整性保护未建立",
            "rootCause": "E2E保护机制尚未建立，完整性验证流程缺失",
            "impact": "系统完整性无法保证，可能存在安全隐患",
            "suggestion": "建立E2E完整性保护机制和验证流程"
          }
        ],
        "quickQuestions": [
          "E2E保护机制建立进展如何？",
          "完整性验证流程何时配置？",
          "安全门禁是否已设置？"
        ]
      },
      "openSource": {
        "ok": 1,
        "total": 3,
        "aiSummary": "开源维度共3项指标，已通过1项，整体达标率33.3%，需完善开源合规和安全管理",
        "risks": [
          {
            "type": "可信-开源",
            "text": "开源达标率33.3%",
            "level": "critical",
            "title": "开源合规管理不足",
            "rootCause": "开源许可证合规未完成，开源安全扫描未建立",
            "impact": "开源合规风险可能影响产品发布",
            "suggestion": "完成开源许可证合规审查，建立安全扫描机制"
          }
        ],
        "quickQuestions": [
          "开源许可证合规完成了吗？",
          "开源安全扫描建立进展如何？",
          "第三方组件清单是否已整理？"
        ]
      },
      "vulnerability": {
        "ok": 0,
        "total": 3,
        "aiSummary": "漏洞管理维度共3项指标，已通过0项，整体达标率0%，需建立安全漏洞管理机制",
        "risks": [
          {
            "type": "可信-漏洞管理",
            "text": "漏洞管理达标率0%",
            "level": "critical",
            "title": "漏洞管理机制未建立",
            "rootCause": "安全扫描、补丁管理和CVE跟踪机制均未建立",
            "impact": "安全漏洞无法及时发现和修复，存在高危风险",
            "suggestion": "立即建立安全扫描和漏洞管理流程"
          }
        ],
        "quickQuestions": [
          "安全扫描机制建立进展如何？",
          "补丁管理流程配置了吗？",
          "CVE跟踪系统是否已接入？"
        ]
      },
      "lifecycle": {
        "ok": 0,
        "total": 6,
        "aiSummary": "生命周期维度共6项指标，已通过0项，整体达标率0%，需建立全生命周期管理流程",
        "risks": [
          {
            "type": "可信-生命周期",
            "text": "生命周期达标率0%",
            "level": "critical",
            "title": "生命周期管理流程未建立",
            "rootCause": "维护计划、升级策略、退役流程均未建立",
            "impact": "产品生命周期管理不完善，影响长期运维",
            "suggestion": "建立完整的生命周期管理流程和文档"
          }
        ],
        "quickQuestions": [
          "生命周期管理流程建立进展如何？",
          "维护计划制定了吗？",
          "退役流程是否已规划？"
        ]
      },
      "risks": [
        {
          "type": "可信",
          "text": "安全需求待评审",
          "level": "warning",
          "title": "安全需求评审排期中",
          "rootCause": "安全需求已提交，待安全专家评审",
          "impact": "安全需求未评审可能影响后续架构设计",
          "suggestion": "协调安全专家尽快安排评审"
        },
        {
          "type": "可信",
          "text": "性能基线待建立",
          "level": "normal",
          "title": "性能基线建立中",
          "rootCause": "性能测试环境正在搭建",
          "impact": "暂无影响",
          "suggestion": "按计划推进性能基线建立"
        }
      ]
    },
    "aiSummary": "208.11.0版本刚启动，暂无明显风险",
    "intentQuestions": {
      "risk": [
        "需求未冻结会影响项目基线吗？",
        "人员到位延迟会影响启动计划吗？"
      ],
      "decision": [
        "如何加速需求冻结流程？"
      ]
    },
    "milestone": {
      "status": "正常",
      "text": "需求收集阶段",
      "statusColor": "green",
      "name": "208.11.0版本",
      "date": "需求收集阶段",
      "aiSummary": "4个阶段0个已完成，里程碑定义待完成，建议关注节点达成",
      "quickQuestions": [
        "里程碑节点的主要风险是什么？",
        "如何确保节点按时达成？",
        "有哪些可并行的任务？"
      ],
      "phases": [
        {
          "name": "需求收集",
          "progress": 10,
          "status": "active"
        },
        {
          "name": "迭代1",
          "progress": 0,
          "status": "pending"
        },
        {
          "name": "迭代2",
          "progress": 0,
          "status": "pending"
        },
        {
          "name": "TR4",
          "progress": 0,
          "status": "pending"
        }
      ],
      "risks": [
        {
          "type": "里程碑",
          "text": "里程碑定义待完成",
          "level": "normal",
          "title": "里程碑定义待完成",
          "rootCause": "项目刚启动，需求尚未冻结，里程碑节点无法精确定义",
          "impact": "里程碑定义不清晰可能影响后续进度跟踪和资源规划",
          "suggestion": "需求冻结后及时组织里程碑评审，明确各阶段时间和交付物"
        },
        {
          "type": "里程碑",
          "text": "需求冻结影响后续节点",
          "level": "warning",
          "title": "需求冻结延迟风险",
          "rootCause": "客户侧需求评审排期在4月中旬",
          "impact": "需求冻结延迟将影响迭代1和TR4节点计划",
          "suggestion": "建议PM协调客户提前进行需求评审，目标4月15日前完成冻结"
        }
      ]
    },
    "scope": {
      "inProgress": 5,
      "baseline": 0,
      "pending": 0,
      "status": "green",
      "text": "尚未开始",
      "aiSummary": "5项需求中，需求尚未冻结，建议尽快冻结需求",
      "quickQuestions": [
        "范围变更的影响是什么？",
        "在途需求的优先级如何？",
        "如何控制范围蔓延？"
      ],
      "risks": [
        {
          "type": "范围",
          "text": "需求尚未冻结",
          "level": "warning",
          "title": "需求冻结延迟",
          "rootCause": "客户侧需求评审排期在4月中旬",
          "impact": "需求未冻结将影响后续设计和开发基线建立",
          "suggestion": "建议PM协调客户提前进行需求评审"
        }
      ]
    },
    "schedule": {
      "status": "green",
      "text": "进度正常",
      "iterProgress": 0,
      "testProgress": 0,
      "passRate": 0,
      "failed": 0,
      "aiSummary": "迭代0%，通过率0%，项目刚启动暂无进度风险，建议保持现状监控",
      "quickQuestions": [
        "进度延误的根本原因是什么？",
        "如何追赶进度？",
        "关键路径上的任务有哪些？"
      ],
      "risks": [
        {
          "type": "进度",
          "text": "项目刚启动，暂无进度风险",
          "level": "normal",
          "title": "进度正常",
          "rootCause": "需求收集阶段刚开始",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "进度",
          "text": "关键里程碑待定义",
          "level": "normal",
          "title": "里程碑待确定",
          "rootCause": "需求未冻结导致里程碑无法精确定义",
          "impact": "暂无影响",
          "suggestion": "需求冻结后及时更新里程碑计划"
        }
      ]
    },
    "resource": {
      "dev": 4,
      "test": 0,
      "env": "yellow",
      "status": "yellow",
      "text": "SE团队组建中",
      "risks": [
        {
          "type": "资源",
          "text": "SE团队组建中",
          "level": "warning",
          "title": "资源到位延迟",
          "rootCause": "团队组建尚未完成",
          "impact": "可能影响后续开发启动",
          "suggestion": "加快团队组建进度"
        },
        {
          "type": "资源",
          "text": "开发人力缺口2人",
          "level": "warning",
          "title": "开发人力不足",
          "rootCause": "计划8人，实际到位6人",
          "impact": "可能影响开发启动进度",
          "suggestion": "加快招聘流程或协调内部资源"
        }
      ]
    },
    "budget": {
      "executionRate": 0,
      "executed": 0,
      "total": 2.5,
      "status": "green",
      "text": "项目刚启动，尚未产生费用",
      "aiSummary": "预算2.5M执行率0%，项目刚启动暂无费用发生，执行节奏正常",
      "quickQuestions": [
        "费用偏差的原因是什么？",
        "如何控制费用超支？",
        "预算调整的建议？"
      ],
      "risks": [
        {
          "type": "费用",
          "text": "项目刚启动暂无费用发生",
          "level": "normal",
          "title": "预算执行正常",
          "rootCause": "项目处于需求收集阶段，尚未进入开发",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        }
      ]
    },
    "quality": {
      "di": 0,
      "defects": 0,
      "warnings": 0,
      "resolveRate": 0,
      "status": "green",
      "text": "暂无数据",
      "aiSummary": "DI值0，缺陷0个，项目刚启动暂无数据，质量状态正常",
      "quickQuestions": [
        "质量问题的根本原因是什么？",
        "如何提升代码质量？",
        "测试覆盖率如何提升？"
      ],
      "risks": [
        {
          "type": "质量",
          "text": "暂无数据",
          "level": "normal",
          "title": "质量状态正常",
          "rootCause": "项目刚启动，无代码产出",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        }
      ]
    },
    "workflow": {
      "design": {
        "status": "warning",
        "aiSummary": "需求收集阶段，<br>尚未冻结",
        "risks": [
          {
            "type": "作业流-需求",
            "text": "需求尚未冻结",
            "level": "warning",
            "title": "需求尚未冻结",
            "rootCause": "客户侧需求评审排期在4月中旬，当前处于需求收集阶段",
            "impact": "需求未冻结将影响后续架构设计和开发基线建立",
            "suggestion": "建议PM协调客户提前进行需求评审，目标4月15日前完成冻结"
          },
          {
            "type": "作业流-需求",
            "text": "客户评审排期中",
            "level": "normal",
            "title": "客户评审排期中",
            "rootCause": "客户内部评审流程需要时间协调各方资源",
            "impact": "评审排期可能影响需求冻结时间点",
            "suggestion": "提前准备评审材料，缩短评审周期"
          },
          {
            "type": "作业流-需求",
            "text": "SE团队组建中",
            "level": "normal",
            "title": "SE团队组建中",
            "rootCause": "项目刚启动，系统工程师正在陆续到位",
            "impact": "SE人员未全部到位可能影响设计文档产出效率",
            "suggestion": "加快SE人员招聘和入职流程，确保关键设计角色优先到位"
          }
        ],
        "quickQuestions": [
          "需求评审何时完成冻结？",
          "客户评审排期能否提前？",
          "SE团队组建进展如何？"
        ]
      },
      "dev": {
        "status": "green",
        "aiSummary": "开发团队组建中，<br>尚未开始编码",
        "risks": [
          {
            "type": "作业流-开发",
            "text": "团队组建中",
            "level": "normal",
            "title": "团队组建中",
            "rootCause": "计划8人，实际到位6人，缺口2人正在招聘",
            "impact": "开发人力不足可能影响后续迭代启动时间",
            "suggestion": "加快招聘进度或从其他项目协调临时支援"
          }
        ],
        "quickQuestions": [
          "团队组建进展如何？",
          "开发人员缺口如何快速补齐？",
          "开发环境何时准备就绪？"
        ]
      },
      "build": {
        "status": "green",
        "aiSummary": "构建环境准备中，<br>流水线就绪",
        "risks": [],
        "quickQuestions": [
          "构建流水线准备情况如何？",
          "构建环境何时就绪？",
          "CI/CD流程是否已配置？"
        ]
      },
      "test": {
        "status": "green",
        "aiSummary": "测试团队待组建，<br>测试策略制定中",
        "risks": [],
        "quickQuestions": [
          "测试团队组建计划是什么？",
          "测试策略何时完成制定？",
          "测试环境准备情况如何？"
        ]
      },
      "release": {
        "status": "green",
        "aiSummary": "发布计划制定中，<br>距发布较远",
        "risks": [],
        "quickQuestions": [
          "发布计划制定进展如何？",
          "发布窗口是否已确认？",
          "发布流程是否已规划？"
        ]
      }
    }
  },
  "208.10.0": {
    "name": "208.10.0版本",
    "group": "V2",
    "progress": 55,
    "trustDetails": {
      "overallScore": 68,
      "status": "可信待加强",
      "aiSummary": "安全扫描发现高危漏洞需紧急修复，渗透测试和隐私合规评估尚未完成，可信验证进度滞后影响TR4审视节点",
      "quickQuestions": [
        "可信问题的根本原因是什么？",
        "如何提升代码可信度？",
        "安全漏洞如何修复？"
      ],
      "productDefinition": {
        "ok": 5,
        "total": 6,
        "aiSummary": "产品定义维度共6项指标，已通过5项，整体达标率83.3%，状态良好",
        "risks": [
          {
            "type": "可信-产品定义",
            "text": "产品定义达标率83.3%",
            "level": "normal",
            "title": "产品定义可信度良好",
            "rootCause": "5项产品定义指标已通过，1项待验证",
            "impact": "暂无影响",
            "suggestion": "完成剩余1项指标的验证工作"
          }
        ],
        "quickQuestions": [
          "产品定义达标情况如何？",
          "剩余1项指标何时完成验证？",
          "产品定义变更管理流程是否完善？"
        ]
      },
      "design": {
        "ok": 7,
        "total": 10,
        "aiSummary": "设计维度共10项指标，已通过7项，整体达标率70%，需加强设计验证",
        "risks": [
          {
            "type": "可信-设计",
            "text": "设计达标率70%",
            "level": "warning",
            "title": "设计验证待加强",
            "rootCause": "3项设计指标未完成，设计验证流程部分缺失",
            "impact": "设计质量风险可能影响后续开发",
            "suggestion": "完成剩余3项设计指标验证"
          }
        ],
        "quickQuestions": [
          "设计验证进展如何？",
          "剩余3项设计指标完成计划？",
          "设计变更管理是否规范？"
        ]
      },
      "coding": {
        "ok": 9,
        "total": 15,
        "aiSummary": "编码维度共15项指标，已通过9项，整体达标率60%，需提升代码质量",
        "risks": [
          {
            "type": "可信-编码",
            "text": "编码达标率60%",
            "level": "warning",
            "title": "编码质量需提升",
            "rootCause": "6项编码指标未完成，代码规范执行不彻底",
            "impact": "代码质量风险可能影响TR4评审",
            "suggestion": "加强代码规范执行和评审覆盖"
          }
        ],
        "quickQuestions": [
          "代码质量现状如何？",
          "剩余6项指标完成计划？",
          "代码评审覆盖是否足够？"
        ]
      },
      "build": {
        "ok": 3,
        "total": 3,
        "aiSummary": "构建维度共3项指标，已通过3项，整体达标率100%，状态优秀",
        "risks": [],
        "quickQuestions": [
          "构建流水线稳定性如何？",
          "构建产物管理规范吗？",
          "构建性能是否需要优化？"
        ]
      },
      "testing": {
        "ok": 6,
        "total": 9,
        "aiSummary": "测试维度共9项指标，已通过6项，整体达标率66.7%，需提升测试覆盖",
        "risks": [
          {
            "type": "可信-测试",
            "text": "测试达标率66.7%",
            "level": "warning",
            "title": "测试覆盖待提升",
            "rootCause": "3项测试指标未完成，用例覆盖存在盲区",
            "impact": "测试覆盖不足可能遗漏缺陷",
            "suggestion": "补充测试用例，提升覆盖率"
          }
        ],
        "quickQuestions": [
          "测试覆盖现状如何？",
          "剩余3项指标完成计划？",
          "测试自动化推进情况？"
        ]
      },
      "e2eProtection": {
        "ok": 3,
        "total": 5,
        "aiSummary": "E2E保护维度共5项指标，已通过3项，整体达标率60%，需完善保护机制",
        "risks": [
          {
            "type": "可信-E2E保护",
            "text": "E2E保护达标率60%",
            "level": "warning",
            "title": "E2E保护机制待完善",
            "rootCause": "2项E2E保护指标未完成，完整性验证不完整",
            "impact": "系统完整性保护不足，存在安全风险",
            "suggestion": "完善E2E完整性保护机制"
          }
        ],
        "quickQuestions": [
          "E2E保护机制完善计划？",
          "完整性验证进展如何？",
          "安全门禁配置是否完整？"
        ]
      },
      "openSource": {
        "ok": 1,
        "total": 3,
        "aiSummary": "开源维度共3项指标，已通过1项，整体达标率33.3%，需加强合规管理",
        "risks": [
          {
            "type": "可信-开源",
            "text": "开源达标率33.3%",
            "level": "critical",
            "title": "开源合规风险较高",
            "rootCause": "开源许可证合规未完成，第三方组件安全扫描缺失",
            "impact": "开源合规问题可能影响产品发布",
            "suggestion": "立即完成开源合规审查"
          }
        ],
        "quickQuestions": [
          "开源合规审查进展？",
          "第三方组件安全扫描配置了吗？",
          "许可证清单是否已整理？"
        ]
      },
      "vulnerability": {
        "ok": 1,
        "total": 3,
        "aiSummary": "漏洞管理维度共3项指标，已通过1项，整体达标率33.3%，需建立漏洞管理机制",
        "risks": [
          {
            "type": "可信-漏洞管理",
            "text": "漏洞管理达标率33.3%",
            "level": "critical",
            "title": "漏洞管理机制不完善",
            "rootCause": "安全扫描和CVE跟踪机制缺失，2项漏洞指标未完成",
            "impact": "安全漏洞无法及时发现和修复",
            "suggestion": "建立安全扫描和漏洞管理流程"
          }
        ],
        "quickQuestions": [
          "安全扫描机制建立进展？",
          "CVE跟踪系统接入了吗？",
          "漏洞修复流程是否规范？"
        ]
      },
      "lifecycle": {
        "ok": 4,
        "total": 6,
        "aiSummary": "生命周期维度共6项指标，已通过4项，整体达标率66.7%，需完善管理流程",
        "risks": [
          {
            "type": "可信-生命周期",
            "text": "生命周期达标率66.7%",
            "level": "warning",
            "title": "生命周期管理待完善",
            "rootCause": "2项生命周期指标未完成，维护计划部分缺失",
            "impact": "生命周期管理不完善可能影响长期运维",
            "suggestion": "完善维护计划和升级策略"
          }
        ],
        "quickQuestions": [
          "生命周期管理流程完善计划？",
          "维护计划制定进展？",
          "退役流程是否已规划？"
        ]
      },
      "risks": [
        {
          "type": "可信",
          "text": "可信待加强",
          "level": "warning",
          "title": "可信验证待加强",
          "rootCause": "安全加固滞后影响可信验证进度",
          "impact": "TR4审视可能受影响",
          "suggestion": "加快安全加固进度"
        },
        {
          "type": "可信",
          "text": "安全扫描未通过",
          "level": "critical",
          "title": "安全扫描发现高危漏洞",
          "rootCause": "安全扫描发现2个高危漏洞未修复",
          "impact": "高危漏洞可能导致TR4被拦截",
          "suggestion": "立即修复高危漏洞"
        },
        {
          "type": "可信",
          "text": "隐私合规待确认",
          "level": "warning",
          "title": "隐私合规评估中",
          "rootCause": "隐私合规评估文档待法务确认",
          "impact": "可能影响TR4可信评审",
          "suggestion": "协调法务尽快完成隐私合规确认"
        },
        {
          "type": "可信",
          "text": "渗透测试未完成",
          "level": "warning",
          "title": "渗透测试进度滞后",
          "rootCause": "渗透测试人员被抽调",
          "impact": "可信验证不完整",
          "suggestion": "安排渗透测试"
        }
      ]
    },
    "aiSummary": "208.10.0版本进度滞后，安全加固风险需关注",
    "intentQuestions": {
      "risk": [
        "安全加固滞后会影响发布时间吗？",
        "测试人力缺口如何影响质量目标？"
      ],
      "decision": [
        "如何调配资源加速安全加固？",
        "哪些非核心功能应该裁剪？"
      ]
    },
    "milestone": {
      "status": "关注",
      "text": "TR4审视（4/15）",
      "statusColor": "yellow",
      "name": "208.10.0版本",
      "date": "TR4审视（4/15）",
      "aiSummary": "4个阶段2个已完成，安全加固滞后影响TR4，建议关注节点达成",
      "quickQuestions": [
        "里程碑节点的主要风险是什么？",
        "如何确保节点按时达成？",
        "有哪些可并行的任务？"
      ],
      "phases": [
        {
          "name": "需求收集",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "迭代1",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "迭代2",
          "progress": 65,
          "status": "active"
        },
        {
          "name": "TR4",
          "progress": 0,
          "status": "pending"
        }
      ],
      "risks": [
        {
          "type": "里程碑",
          "text": "TR4节点临近",
          "level": "critical",
          "title": "TR4审视节点压力",
          "rootCause": "TR4审视定在4/15，当前迭代2进度65%",
          "impact": "TR4节点时间紧迫，存在较大延误风险",
          "suggestion": "全力保障TR4节点，建议每日跟踪迭代2关键路径"
        },
        {
          "type": "里程碑",
          "text": "安全加固滞后影响TR4",
          "level": "critical",
          "title": "安全加固进度滞后",
          "rootCause": "安全模块开发人员被抽调至301.1.0，导致安全加固滞后2周",
          "impact": "安全加固是TR4的必要条件，滞后将导致TR4被拦截",
          "suggestion": "建议申请安全专家支援，目标1周内追回进度"
        }
      ]
    },
    "scope": {
      "inProgress": 8,
      "baseline": 28,
      "pending": 3,
      "status": "green",
      "text": "需求基本稳定",
      "aiSummary": "39项需求中，需求基本稳定，建议加强范围控制",
      "quickQuestions": [
        "范围变更的影响是什么？",
        "在途需求的优先级如何？",
        "如何控制范围蔓延？"
      ],
      "risks": [
        {
          "type": "范围",
          "text": "需求基本稳定",
          "level": "normal",
          "title": "范围可控",
          "rootCause": "需求冻结率较高",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "范围",
          "text": "遗留需求变更2项",
          "level": "normal",
          "title": "遗留需求处理中",
          "rootCause": "2项遗留需求变更评估中",
          "impact": "对整体范围影响可控",
          "suggestion": "按优先级处理遗留需求"
        },
        {
          "type": "范围",
          "text": "接口兼容性待验证",
          "level": "warning",
          "title": "接口兼容性风险",
          "rootCause": "与旧版本接口兼容性需进一步验证",
          "impact": "可能影响集成测试",
          "suggestion": "尽快安排接口兼容性测试"
        },
        {
          "type": "范围",
          "text": "需求蔓延风险",
          "level": "warning",
          "title": "需求蔓延监控",
          "rootCause": "部分需求边界模糊",
          "impact": "可能影响范围控制",
          "suggestion": "加强需求边界管理"
        }
      ]
    },
    "schedule": {
      "status": "yellow",
      "text": "安全加固滞后",
      "iterProgress": 55,
      "testProgress": 42,
      "failed": 4,
      "passRate": 88,
      "aiSummary": "迭代55%，通过率88%，安全加固滞后2周影响TR4，建议申请安全专家支援",
      "quickQuestions": [
        "进度延误的根本原因是什么？",
        "如何追赶进度？",
        "关键路径上的任务有哪些？"
      ],
      "risks": [
        {
          "type": "进度",
          "text": "安全加固滞后2周",
          "level": "critical",
          "title": "安全加固进度滞后",
          "rootCause": "安全模块开发人员被抽调至301.1.0应急",
          "impact": "安全加固是TR4的必要条件，滞后2周将影响TR4审视节点",
          "suggestion": "建议申请安全专家支援"
        },
        {
          "type": "进度",
          "text": "集成测试启动晚",
          "level": "warning",
          "title": "集成测试延期风险",
          "rootCause": "依赖安全加固完成",
          "impact": "集成测试时间被压缩",
          "suggestion": "优化集成测试计划"
        },
        {
          "type": "进度",
          "text": "TR4节点临近",
          "level": "critical",
          "title": "TR4审视节点压力",
          "rootCause": "TR4审视定在4/15",
          "impact": "时间紧迫，风险较高",
          "suggestion": "全力保障TR4节点"
        },
        {
          "type": "进度",
          "text": "联调环境不稳定",
          "level": "warning",
          "title": "环境问题",
          "rootCause": "联调环境频繁出现问题",
          "impact": "影响联调效率",
          "suggestion": "加强环境维护"
        }
      ]
    },
    "resource": {
      "dev": 10,
      "test": 6,
      "env": "green",
      "status": "yellow",
      "text": "测试人力缺口2人",
      "risks": [
        {
          "type": "资源",
          "text": "测试人力紧张",
          "level": "warning",
          "title": "测试人力缺口",
          "rootCause": "测试团队被301.1.0借调2人",
          "impact": "测试进度42%，存在测试覆盖不足风险",
          "suggestion": "建议申请2名外包测试人员支撑"
        },
        {
          "type": "资源",
          "text": "安全专家资源争抢",
          "level": "critical",
          "title": "安全专家资源紧张",
          "rootCause": "301.1.0和208.10.0同时需要安全专家",
          "impact": "安全专家精力分散，影响两端进度",
          "suggestion": "建议错峰使用安全专家"
        },
        {
          "type": "资源",
          "text": "环境维护人力不足",
          "level": "warning",
          "title": "环境稳定性风险",
          "rootCause": "环境运维人员仅1人",
          "impact": "环境问题响应可能不及时",
          "suggestion": "增加环境运维支持"
        }
      ]
    },
    "budget": {
      "executionRate": 72,
      "executed": 1.8,
      "total": 2.5,
      "status": "green",
      "text": "执行率72%，进度正常",
      "aiSummary": "预算2.5M执行率72%，进度正常，需关注后续费用使用节奏",
      "quickQuestions": [
        "费用偏差的原因是什么？",
        "如何控制费用超支？",
        "预算调整的建议？"
      ],
      "risks": [
        {
          "type": "费用",
          "text": "预算执行进度正常",
          "level": "normal",
          "title": "费用状态正常",
          "rootCause": "执行率72%符合预期进度",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "费用",
          "text": "需关注后续费用使用节奏",
          "level": "warning",
          "title": "费用使用节奏风险",
          "rootCause": "剩余28%预算需在后期合理使用",
          "impact": "可能出现前期节流后期突击花钱",
          "suggestion": "提前规划后期预算使用计划"
        }
      ]
    },
    "quality": {
      "di": 38,
      "defects": 12,
      "warnings": 320,
      "resolveRate": 78,
      "status": "yellow",
      "text": "DI值偏高",
      "aiSummary": "DI值38，缺陷12个，DI值偏高接近阈值，建议每日站会增加DI值清理环节",
      "quickQuestions": [
        "质量问题的根本原因是什么？",
        "如何提升代码质量？",
        "测试覆盖率如何提升？"
      ],
      "risks": [
        {
          "type": "质量",
          "text": "DI值偏高",
          "level": "warning",
          "title": "DI值超标",
          "rootCause": "静态检查告警320条未及时清理",
          "impact": "DI值38分接近阈值，质量门禁存在触发风险",
          "suggestion": "建议每日站会增加DI值清理环节"
        },
        {
          "type": "质量",
          "text": "代码评审积压15项",
          "level": "warning",
          "title": "评审积压风险",
          "rootCause": "评审专家被抽调",
          "impact": "代码质量问题可能遗漏",
          "suggestion": "增加评审资源"
        },
        {
          "type": "质量",
          "text": "缺陷修复周期长",
          "level": "normal",
          "title": "缺陷处理效率待提升",
          "rootCause": "平均缺陷修复周期5天",
          "impact": "影响测试进度",
          "suggestion": "优化缺陷处理流程"
        },
        {
          "type": "质量",
          "text": "冒烟测试通过率低",
          "level": "warning",
          "title": "冒烟测试失败率高",
          "rootCause": "冒烟测试通过率仅75%",
          "impact": "构建质量不稳定",
          "suggestion": "加强冒烟测试覆盖"
        }
      ]
    },
    "workflow": {
      "design": {
        "status": "green",
        "aiSummary": "需求已冻结，<br>架构设计完成",
        "risks": [
          {
            "type": "作业流-需求",
            "text": "无阻塞问题",
            "level": "normal",
            "title": "无阻塞问题",
            "rootCause": "需求冻结率100%，架构设计评审已通过",
            "impact": "设计阶段无风险，支持后续开发",
            "suggestion": "继续保持设计文档的完善和更新"
          },
          {
            "type": "作业流-需求",
            "text": "设计评审通过",
            "level": "normal",
            "title": "设计评审通过",
            "rootCause": "架构设计满足功能性和非功能性需求",
            "impact": "设计评审通过，可以进入开发阶段",
            "suggestion": "定期回顾设计文档，确保与实现一致"
          },
          {
            "type": "作业流-需求",
            "text": "接口已冻结",
            "level": "normal",
            "title": "接口已冻结",
            "rootCause": "跨团队接口协商完成，接口文档已归档",
            "impact": "接口冻结支持下游模块并行开发",
            "suggestion": "持续监控接口变更请求，评估影响范围"
          }
        ],
        "quickQuestions": [
          "设计阶段还有哪些遗留问题？",
          "架构设计是否满足性能要求？",
          "接口文档是否已同步给下游团队？"
        ]
      },
      "dev": {
        "status": "warning",
        "aiSummary": "安全加固滞后2周，<br>测试人力紧张",
        "risks": [
          {
            "type": "作业流-开发",
            "text": "安全加固滞后2周",
            "level": "critical",
            "title": "安全加固滞后2周",
            "rootCause": "安全模块开发人员被抽调至301.1.0应急，导致安全加固进度滞后",
            "impact": "安全加固是TR4的必要条件，滞后2周将影响TR4审视节点",
            "suggestion": "建议申请安全专家支援，目标1周内追回进度"
          },
          {
            "type": "作业流-开发",
            "text": "测试人力缺口2人",
            "level": "warning",
            "title": "测试人力缺口2人",
            "rootCause": "测试团队被301.1.0借调2人，实际测试人员仅6人",
            "impact": "测试进度42%，存在测试覆盖不足风险",
            "suggestion": "建议申请2名外包测试人员临时支撑"
          },
          {
            "type": "作业流-开发",
            "text": "DI值偏高",
            "level": "warning",
            "title": "DI值偏高",
            "rootCause": "静态检查告警320条未及时清理，代码评审覆盖不足",
            "impact": "DI值38分接近阈值，质量门禁存在触发风险",
            "suggestion": "建议每日站会增加DI值清理环节，目标降至30以下"
          }
        ],
        "quickQuestions": [
          "安全加固滞后的根本原因是什么？",
          "测试人力缺口如何快速补齐？",
          "DI值清理计划何时启动？"
        ]
      },
      "build": {
        "status": "green",
        "aiSummary": "构建成功率99%，<br>CI流水线正常",
        "risks": [
          {
            "type": "作业流-构建",
            "text": "构建正常",
            "level": "normal",
            "title": "构建正常",
            "rootCause": "构建环境稳定，构建成功率99%",
            "impact": "构建环节无风险，支撑开发进度",
            "suggestion": "继续保持构建环境稳定性"
          },
          {
            "type": "作业流-构建",
            "text": "无阻塞问题",
            "level": "normal",
            "title": "无阻塞问题",
            "rootCause": "CI流水线运行正常，无构建阻塞问题",
            "impact": "构建流程顺畅，开发效率不受影响",
            "suggestion": "持续监控构建时长，优化构建性能"
          }
        ],
        "quickQuestions": [
          "构建流水线是否需要优化？",
          "构建环境如何保持稳定性？",
          "是否有新的构建工具可以引入？"
        ]
      },
      "test": {
        "status": "warning",
        "aiSummary": "用例执行率75%，<br>覆盖度达标",
        "risks": [
          {
            "type": "作业流-测试",
            "text": "测试人力缺口2人",
            "level": "warning",
            "title": "测试人力缺口2人",
            "rootCause": "测试团队被301.1.0借调2人，实际测试人员仅6人",
            "impact": "测试进度42%，存在测试覆盖不足风险",
            "suggestion": "建议申请2名外包测试人员临时支撑"
          },
          {
            "type": "作业流-测试",
            "text": "DI值38分偏高",
            "level": "warning",
            "title": "DI值38分偏高",
            "rootCause": "静态检查告警320条未及时清理，代码评审覆盖不足",
            "impact": "DI值38分接近阈值，质量门禁存在触发风险",
            "suggestion": "建议每日站会增加DI值清理环节，目标降至30以下"
          }
        ],
        "quickQuestions": [
          "测试人力缺口如何快速补齐？",
          "DI值清理计划何时启动？",
          "测试覆盖率是否达标？"
        ]
      },
      "release": {
        "status": "green",
        "aiSummary": "TR4审视在即，<br>发布准备就绪",
        "risks": [
          {
            "type": "作业流-发布",
            "text": "发布准备就绪",
            "level": "normal",
            "title": "发布准备就绪",
            "rootCause": "发布材料已准备，发布窗口已确认",
            "impact": "发布准备工作完成，支持TR4审视",
            "suggestion": "提前检查发布清单，确保无遗漏"
          },
          {
            "type": "作业流-发布",
            "text": "无风险问题",
            "level": "normal",
            "title": "无风险问题",
            "rootCause": "发布计划已评审，无阻塞发布的问题",
            "impact": "发布环节无风险，支持按计划发布",
            "suggestion": "继续保持发布准备工作"
          }
        ],
        "quickQuestions": [
          "TR4审视准备情况如何？",
          "发布材料是否已完整准备？",
          "发布窗口是否已确认？"
        ]
      }
    }
  },
  "301.1.0": {
    "name": "301.1.0版本",
    "group": "V3",
    "progress": 35,
    "trustDetails": {
      "overallScore": 58,
      "status": "可信验证进行中",
      "aiSummary": "性能测试发现瓶颈需立即优化，安全测试发现3个中危漏洞待修复，代码审计和合规检查尚未完成，可信验证进度78%影响TR5准入",
      "quickQuestions": [
        "可信问题的根本原因是什么？",
        "如何提升代码可信度？",
        "安全漏洞如何修复？"
      ],
      "productDefinition": {
        "ok": 4,
        "total": 6,
        "aiSummary": "产品定义维度共6项指标，已通过4项，整体达标率66.7%，需完善产品定义评审",
        "risks": [
          {
            "type": "可信-产品定义",
            "text": "产品定义达标率66.7%",
            "level": "warning",
            "title": "产品定义需完善",
            "rootCause": "2项产品定义指标未完成，产品定义评审流程部分缺失",
            "impact": "产品定义不完整可能影响需求稳定性",
            "suggestion": "完成剩余2项指标，建立产品定义评审机制"
          }
        ],
        "quickQuestions": [
          "产品定义完善计划？",
          "产品定义评审流程建立进展？",
          "需求变更控制是否规范？"
        ]
      },
      "design": {
        "ok": 6,
        "total": 10,
        "aiSummary": "设计维度共10项指标，已通过6项，整体达标率60%，需加强设计评审",
        "risks": [
          {
            "type": "可信-设计",
            "text": "设计达标率60%",
            "level": "warning",
            "title": "设计评审需加强",
            "rootCause": "4项设计指标未完成，架构评审和安全设计验证缺失",
            "impact": "设计质量风险可能影响开发进度",
            "suggestion": "完成剩余4项设计指标，加强架构评审"
          }
        ],
        "quickQuestions": [
          "设计评审进展如何？",
          "架构评审完成了吗？",
          "安全设计验证计划？"
        ]
      },
      "coding": {
        "ok": 8,
        "total": 15,
        "aiSummary": "编码维度共15项指标，已通过8项，整体达标率53.3%，需提升代码质量",
        "risks": [
          {
            "type": "可信-编码",
            "text": "编码达标率53.3%",
            "level": "warning",
            "title": "代码质量需提升",
            "rootCause": "7项编码指标未完成，代码规范执行不彻底，DI值45分超标",
            "impact": "代码质量问题影响TR5准入评审",
            "suggestion": "加强代码规范执行，目标TR5前DI值降至30以下"
          }
        ],
        "quickQuestions": [
          "代码质量现状？",
          "DI值优化计划？",
          "代码评审覆盖是否足够？"
        ]
      },
      "build": {
        "ok": 2,
        "total": 3,
        "aiSummary": "构建维度共3项指标，已通过2项，整体达标率66.7%，需完善构建验证",
        "risks": [
          {
            "type": "可信-构建",
            "text": "构建达标率66.7%",
            "level": "warning",
            "title": "构建验证待完善",
            "rootCause": "1项构建指标未完成，构建验证流程部分缺失",
            "impact": "构建流程不完善可能影响交付效率",
            "suggestion": "完成剩余1项构建指标验证"
          }
        ],
        "quickQuestions": [
          "构建验证完成进展？",
          "构建流水线稳定性？",
          "构建产物管理规范吗？"
        ]
      },
      "testing": {
        "ok": 5,
        "total": 9,
        "aiSummary": "测试维度共9项指标，已通过5项，整体达标率55.6%，需提升测试覆盖",
        "risks": [
          {
            "type": "可信-测试",
            "text": "测试达标率55.6%",
            "level": "warning",
            "title": "测试覆盖需提升",
            "rootCause": "4项测试指标未完成，用例覆盖存在盲区，测试人力缺口4人",
            "impact": "测试覆盖不足可能遗漏缺陷，影响TR5评审",
            "suggestion": "补充测试用例，从208.10.0借调测试人员支援"
          }
        ],
        "quickQuestions": [
          "测试覆盖现状？",
          "测试人力缺口如何补齐？",
          "测试用例补充计划？"
        ]
      },
      "e2eProtection": {
        "ok": 3,
        "total": 5,
        "aiSummary": "E2E保护维度共5项指标，已通过3项，整体达标率60%，需完善完整性保护",
        "risks": [
          {
            "type": "可信-E2E保护",
            "text": "E2E保护达标率60%",
            "level": "warning",
            "title": "E2E保护机制待完善",
            "rootCause": "2项E2E保护指标未完成，完整性验证不完整",
            "impact": "系统完整性保护不足，存在安全风险",
            "suggestion": "完善E2E完整性保护机制"
          }
        ],
        "quickQuestions": [
          "E2E保护机制完善计划？",
          "完整性验证进展如何？",
          "安全门禁配置完整吗？"
        ]
      },
      "openSource": {
        "ok": 1,
        "total": 3,
        "aiSummary": "开源维度共3项指标，已通过1项，整体达标率33.3%，需加强开源合规管理",
        "risks": [
          {
            "type": "可信-开源",
            "text": "开源达标率33.3%",
            "level": "critical",
            "title": "开源合规风险较高",
            "rootCause": "开源许可证合规未完成，第三方组件安全扫描缺失",
            "impact": "开源合规问题可能影响TR5评审和产品发布",
            "suggestion": "立即完成开源合规审查，建立安全扫描机制"
          }
        ],
        "quickQuestions": [
          "开源合规审查进展？",
          "第三方组件安全扫描配置了吗？",
          "许可证清单是否已整理？"
        ]
      },
      "vulnerability": {
        "ok": 0,
        "total": 3,
        "aiSummary": "漏洞管理维度共3项指标，已通过0项，整体达标率0%，需立即建立漏洞管理机制",
        "risks": [
          {
            "type": "可信-漏洞管理",
            "text": "漏洞管理达标率0%",
            "level": "critical",
            "title": "漏洞管理机制严重缺失",
            "rootCause": "安全扫描、CVE跟踪和补丁管理机制均未建立",
            "impact": "安全漏洞无法及时发现和修复，存在高危风险",
            "suggestion": "立即建立安全扫描和漏洞管理流程"
          }
        ],
        "quickQuestions": [
          "安全扫描机制建立进展？",
          "CVE跟踪系统接入了吗？",
          "漏洞修复流程是否规范？"
        ]
      },
      "lifecycle": {
        "ok": 3,
        "total": 6,
        "aiSummary": "生命周期维度共6项指标，已通过3项，整体达标率50%，需完善生命周期管理",
        "risks": [
          {
            "type": "可信-生命周期",
            "text": "生命周期达标率50%",
            "level": "warning",
            "title": "生命周期管理待完善",
            "rootCause": "3项生命周期指标未完成，维护计划和升级策略部分缺失",
            "impact": "生命周期管理不完善影响长期运维",
            "suggestion": "完善维护计划和升级策略"
          }
        ],
        "quickQuestions": [
          "生命周期管理流程完善计划？",
          "维护计划制定进展？",
          "升级策略是否已规划？"
        ]
      },
      "risks": [
        {
          "type": "可信",
          "text": "可信验证78%",
          "level": "warning",
          "title": "可信验证进度滞后",
          "rootCause": "剩余安全测试和性能测试未完成",
          "impact": "影响TR5准入评审",
          "suggestion": "建议安全团队和性能团队并行推进，目标2天内完成可信验证"
        },
        {
          "type": "可信",
          "text": "性能测试未通过",
          "level": "critical",
          "title": "性能测试发现瓶颈",
          "rootCause": "高并发场景下响应时间超标",
          "impact": "可能导致TR5被拦截",
          "suggestion": "立即进行性能优化"
        },
        {
          "type": "可信",
          "text": "安全测试发现漏洞",
          "level": "warning",
          "title": "安全漏洞待修复",
          "rootCause": "安全测试发现3个中危漏洞",
          "impact": "需修复后才能通过可信评审",
          "suggestion": "按优先级修复安全漏洞"
        },
        {
          "type": "可信",
          "text": "代码审计未完成",
          "level": "warning",
          "title": "代码审计进度滞后",
          "rootCause": "代码审计人员被借调",
          "impact": "可信验证不完整",
          "suggestion": "安排代码审计"
        },
        {
          "type": "可信",
          "text": "合规检查待通过",
          "level": "warning",
          "title": "合规检查风险",
          "rootCause": "合规文档待审核",
          "impact": "可能影响上线",
          "suggestion": "加快合规检查"
        }
      ]
    },
    "aiSummary": "301.1.0版本进度滞后，TR5节点风险高",
    "intentQuestions": {
      "risk": [
        "编码进度延期会影响TR5验收吗？",
        "测试人力缺口如何影响质量目标？",
        "当前代码质量能否达到TR5准入标准？"
      ],
      "decision": [
        "如何调配资源保证TR5节点？",
        "哪些需求变更应该裁剪以保交期？",
        "TR5后剩余缺陷如何排期清理？"
      ]
    },
    "milestone": {
      "status": "关键风险",
      "text": "TR5（3/28）距节点4天",
      "statusColor": "red",
      "name": "301.1.0版本",
      "date": "TR5（3/28）距节点4天",
      "aiSummary": "4个阶段2个已完成，TR5节点延误风险>80%，建议关注节点达成",
      "quickQuestions": [
        "里程碑节点的主要风险是什么？",
        "如何确保节点按时达成？",
        "有哪些可并行的任务？"
      ],
      "phases": [
        {
          "name": "需求收集",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "迭代1",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "迭代2",
          "progress": 65,
          "status": "active"
        },
        {
          "name": "TR5",
          "progress": 0,
          "status": "pending"
        }
      ],
      "risks": [
        {
          "type": "里程碑",
          "text": "TR5节点延误风险>80%",
          "level": "critical",
          "title": "TR5节点延误风险",
          "rootCause": "迭代2进度仅65%，编码延期5天导致测试时间被严重压缩",
          "impact": "TR5节点延误将导致下游集成计划延后，影响客户交付承诺",
          "suggestion": "建议PM立即召集核心开发评审，识别可并行任务，目标3天内追回进度"
        },
        {
          "type": "里程碑",
          "text": "TR5窗口仅剩4天",
          "level": "critical",
          "title": "TR5窗口紧张",
          "rootCause": "TR5窗口仅剩4天，测试进度仅37%，可信验证进度78%",
          "impact": "TR5窗口紧张可能导致发布延期",
          "suggestion": "建议提前准备发布材料，并行推进发布准备工作"
        }
      ]
    },
    "scope": {
      "inProgress": 12,
      "baseline": 35,
      "pending": 5,
      "status": "yellow",
      "text": "需求变更2次影响核心路径",
      "aiSummary": "52项需求中，需求变更2次影响核心路径，建议立即组织变更评审会",
      "quickQuestions": [
        "范围变更的影响是什么？",
        "在途需求的优先级如何？",
        "如何控制范围蔓延？"
      ],
      "risks": [
        {
          "type": "范围",
          "text": "需求变更2次影响核心路径",
          "level": "warning",
          "title": "范围变更风险",
          "rootCause": "客户在迭代1后期提出3项重大需求变更",
          "impact": "架构需要重新评审，影响开发进度约5天",
          "suggestion": "建议立即组织变更评审会，评估影响范围并调整迭代计划"
        },
        {
          "type": "范围",
          "text": "接口定义变更3次",
          "level": "warning",
          "title": "接口变更风险",
          "rootCause": "接口定义频繁变更",
          "impact": "增加集成测试复杂度",
          "suggestion": "冻结接口定义，控制变更"
        }
      ]
    },
    "schedule": {
      "status": "critical",
      "text": "迭代1延期5天",
      "iterProgress": 65,
      "testProgress": 37,
      "failed": 6,
      "passRate": 92,
      "aiSummary": "迭代65%，通过率92%，TR5节点延误概率>80%，建议立即召集核心开发评审",
      "quickQuestions": [
        "进度延误的根本原因是什么？",
        "如何追赶进度？",
        "关键路径上的任务有哪些？"
      ],
      "risks": [
        {
          "type": "进度",
          "text": "TR5节点延误概率>80%",
          "level": "critical",
          "title": "TR5节点延误风险",
          "rootCause": "迭代1延期5天，编码进度滞后导致测试时间被压缩",
          "impact": "TR5节点延误将导致下游集成计划延后",
          "suggestion": "建议PM立即召集核心开发评审，识别可并行任务"
        },
        {
          "type": "进度",
          "text": "编码延期严重",
          "level": "critical",
          "title": "编码进度严重滞后",
          "rootCause": "核心模块技术难度超出预期",
          "impact": "影响整体项目进度",
          "suggestion": "增加开发资源或调整范围"
        },
        {
          "type": "进度",
          "text": "阻塞问题3个",
          "level": "critical",
          "title": "阻塞问题待解决",
          "rootCause": "存在3个技术难题未突破",
          "impact": "阻塞后续开发和测试",
          "suggestion": "组织专项攻关"
        },
        {
          "type": "进度",
          "text": "联调进度滞后",
          "level": "warning",
          "title": "联调进度风险",
          "rootCause": "联调环境不稳定",
          "impact": "影响集成测试",
          "suggestion": "加强联调管理"
        }
      ]
    },
    "resource": {
      "dev": 12,
      "test": 8,
      "env": "green",
      "status": "yellow",
      "text": "测试人力缺口4人",
      "risks": [
        {
          "type": "资源",
          "text": "测试人力缺口4人",
          "level": "warning",
          "title": "测试人力缺口",
          "rootCause": "计划测试人员12人，实际到位仅8人，缺口4人",
          "impact": "测试进度仅37%，无法支撑TR5节点",
          "suggestion": "建议从208.10.0借调2名测试工程师"
        },
        {
          "type": "资源",
          "text": "资深开发不足",
          "level": "warning",
          "title": "技术骨干缺口",
          "rootCause": "核心技术评审能力不足",
          "impact": "代码质量风险增加",
          "suggestion": "申请高级开发支援"
        },
        {
          "type": "资源",
          "text": "外包人员效率低",
          "level": "normal",
          "title": "外包人员培训需求",
          "rootCause": "外包人员对系统不熟悉",
          "impact": "初期产出效率较低",
          "suggestion": "加强外包人员培训"
        },
        {
          "type": "资源",
          "text": "设备资源不足",
          "level": "warning",
          "title": "测试设备缺口",
          "rootCause": "测试设备数量不足",
          "impact": "影响测试效率",
          "suggestion": "申请测试设备"
        }
      ]
    },
    "budget": {
      "executionRate": 38,
      "executed": 1.52,
      "total": 4,
      "status": "yellow",
      "text": "执行率38%，低于预期",
      "aiSummary": "预算4.0M执行率38%，低于预期28%，建议加快开发进度追回预算执行率",
      "quickQuestions": [
        "费用偏差的原因是什么？",
        "如何控制费用超支？",
        "预算调整的建议？"
      ],
      "risks": [
        {
          "type": "费用",
          "text": "预算执行滞后28%",
          "level": "warning",
          "title": "执行率偏低风险",
          "rootCause": "编码延期导致开发人力投入不足",
          "impact": "执行率38%低于预期，进度滞后可能影响预算分配",
          "suggestion": "加快开发进度，追回预算执行率"
        },
        {
          "type": "费用",
          "text": "警惕后期突击花钱",
          "level": "warning",
          "title": "预算使用节奏风险",
          "rootCause": "当前执行率偏低，若后续加速可能导致费用使用不均衡",
          "impact": "费用使用不均衡可能影响财务核算",
          "suggestion": "制定合理的预算使用计划"
        }
      ]
    },
    "quality": {
      "di": 45,
      "defects": 17,
      "warnings": 680,
      "resolveRate": 82,
      "status": "yellow",
      "text": "DI值45分超标",
      "aiSummary": "DI值45，缺陷17个，DI值超标接近门禁，建议启动DI专项整改",
      "quickQuestions": [
        "质量问题的根本原因是什么？",
        "如何提升代码质量？",
        "测试覆盖率如何提升？"
      ],
      "risks": [
        {
          "type": "质量",
          "text": "DI值45分超标",
          "level": "warning",
          "title": "DI值超标",
          "rootCause": "静态检查告警680条，代码评审覆盖不足",
          "impact": "TR5准入门槛未达，可能触发质量门禁拦截",
          "suggestion": "建议启动DI专项整改，目标TR5前将DI降至30以下"
        },
        {
          "type": "质量",
          "text": "缺陷逃逸2个",
          "level": "warning",
          "title": "缺陷逃逸风险",
          "rootCause": "测试用例覆盖不足",
          "impact": "线上可能暴露缺陷",
          "suggestion": "补充测试用例"
        },
        {
          "type": "质量",
          "text": "技术债务累积",
          "level": "warning",
          "title": "技术债务风险",
          "rootCause": "为赶进度采用临时方案",
          "impact": "影响后续维护",
          "suggestion": "TR5后安排技术债务清理"
        },
        {
          "type": "质量",
          "text": "代码重复率高",
          "level": "warning",
          "title": "代码重复风险",
          "rootCause": "代码重复率15%",
          "impact": "维护成本增加",
          "suggestion": "重构重复代码"
        }
      ]
    },
    "workflow": {
      "design": {
        "status": "warning",
        "aiSummary": "需求冻结率65%，<br>存在3项重大变更风险",
        "risks": [
          {
            "type": "作业流-需求",
            "text": "需求变更影响核心设计",
            "level": "warning",
            "title": "需求变更影响核心设计",
            "rootCause": "客户在迭代1后期提出3项重大需求变更，涉及核心架构调整",
            "impact": "架构需要重新评审，影响开发进度约5天",
            "suggestion": "建议立即组织变更评审会，评估影响范围并调整迭代计划"
          },
          {
            "type": "作业流-需求",
            "text": "架构评审未通过",
            "level": "warning",
            "title": "架构评审未通过",
            "rootCause": "架构方案未满足安全性要求，存在2个高危风险项",
            "impact": "架构评审未通过导致设计无法进入开发阶段",
            "suggestion": "建议安全专家介入，重新设计安全模块架构"
          },
          {
            "type": "作业流-需求",
            "text": "接口定义未冻结",
            "level": "warning",
            "title": "接口定义未冻结",
            "rootCause": "跨团队接口协商进度滞后，存在5个接口待确认",
            "impact": "接口未冻结影响下游模块开发启动",
            "suggestion": "建议组织跨团队接口评审会，目标3天内完成所有接口确认"
          }
        ],
        "quickQuestions": [
          "需求变更对架构的影响范围有多大？",
          "架构评审未通过的具体风险项是什么？",
          "跨团队接口协商需要哪些资源支持？"
        ]
      },
      "dev": {
        "status": "critical",
        "aiSummary": "编码进度延期5天，<br>TR5准入存在风险",
        "risks": [
          {
            "type": "作业流-开发",
            "text": "核心模块编码延期",
            "level": "critical",
            "title": "核心模块编码延期",
            "rootCause": "核心模块开发难度超出预期，技术攻关耗时3天",
            "impact": "核心模块延期导致整体编码进度滞后，影响TR5准入",
            "suggestion": "建议从其他项目借调2名资深开发工程师支援，目标5天内追回进度"
          },
          {
            "type": "作业流-开发",
            "text": "代码评审积压12项",
            "level": "warning",
            "title": "代码评审积压12项",
            "rootCause": "评审专家被抽调至其他项目，评审资源不足",
            "impact": "代码评审积压影响代码质量把控，存在潜在缺陷风险",
            "suggestion": "建议安排高级工程师轮流承担评审职责，每周至少完成4项评审"
          },
          {
            "type": "作业流-开发",
            "text": "技术债务累积",
            "level": "warning",
            "title": "技术债务累积",
            "rootCause": "为赶进度采用临时方案，技术债务累积约15项",
            "impact": "技术债务累积影响后续维护和迭代效率",
            "suggestion": "建议在TR5后安排技术债务清理专项，目标2周内清理50%"
          }
        ],
        "quickQuestions": [
          "核心模块延期的根本原因是什么？",
          "代码评审积压如何快速消化？",
          "技术债务清理计划何时启动？"
        ]
      },
      "build": {
        "status": "green",
        "aiSummary": "构建成功率98%，<br>依赖管理正常",
        "risks": [
          {
            "type": "作业流-构建",
            "text": "构建时长优化10%",
            "level": "normal",
            "title": "构建时长优化10%",
            "rootCause": "优化了构建流水线并行度，构建时长从45分钟降至40分钟",
            "impact": "构建效率提升，开发人员等待时间缩短",
            "suggestion": "建议持续监控构建时长，目标优化至35分钟以内"
          },
          {
            "type": "作业流-构建",
            "text": "依赖版本一致",
            "level": "normal",
            "title": "依赖版本一致",
            "rootCause": "统一了依赖版本管理，无版本冲突问题",
            "impact": "依赖管理稳定，无阻塞风险",
            "suggestion": "建议定期检查依赖安全告警，及时更新有漏洞的依赖"
          },
          {
            "type": "作业流-构建",
            "text": "无阻塞问题",
            "level": "normal",
            "title": "无阻塞问题",
            "rootCause": "构建环境稳定，构建成功率98%",
            "impact": "构建环节无风险，支撑开发进度",
            "suggestion": "继续保持构建环境稳定性"
          }
        ],
        "quickQuestions": [
          "构建流水线还有哪些优化空间？",
          "依赖版本是否存在安全漏洞？",
          "构建环境如何保持稳定性？"
        ]
      },
      "test": {
        "status": "warning",
        "aiSummary": "用例执行率72%，<br>缺陷修复率需提升",
        "risks": [
          {
            "type": "作业流-测试",
            "text": "测试人力缺口4人",
            "level": "warning",
            "title": "测试人力缺口4人",
            "rootCause": "计划测试人员12人，实际到位仅8人，缺口4人",
            "impact": "测试进度仅37%，无法支撑TR5节点",
            "suggestion": "建议从208.10.0借调2名测试工程师临时支援"
          },
          {
            "type": "作业流-测试",
            "text": "DI值超标(45分)",
            "level": "warning",
            "title": "DI值超标(45分)",
            "rootCause": "静态检查告警680条，代码评审覆盖不足",
            "impact": "TR5准入门槛未达，可能触发质量门禁拦截",
            "suggestion": "建议启动DI专项整改，目标TR5前将DI降至30以下"
          },
          {
            "type": "作业流-测试",
            "text": "阻塞问题3个",
            "level": "warning",
            "title": "阻塞问题3个",
            "rootCause": "存在3个严重缺陷阻塞测试进度，已定位根因但修复中",
            "impact": "阻塞问题导致测试无法继续，影响TR5准入",
            "suggestion": "建议组织专项攻关会，优先解决3个阻塞问题"
          }
        ],
        "quickQuestions": [
          "测试人力缺口如何快速补齐？",
          "DI值专项整改进度如何？",
          "3个阻塞问题的修复进展？"
        ]
      },
      "release": {
        "status": "warning",
        "aiSummary": "TR5窗口4天，<br>可信验证进度78%",
        "risks": [
          {
            "type": "作业流-发布",
            "text": "TR5延期风险",
            "level": "warning",
            "title": "TR5延期风险",
            "rootCause": "编码进度滞后5天，测试进度仅37%，TR5延期概率>80%",
            "impact": "TR5延期将导致下游集成计划延后，影响客户交付承诺",
            "suggestion": "建议PM立即召集核心开发评审，识别可并行任务，目标3天内追回进度"
          },
          {
            "type": "作业流-发布",
            "text": "可信验证未完成",
            "level": "warning",
            "title": "可信验证未完成",
            "rootCause": "可信验证进度78%，剩余安全测试和性能测试未完成",
            "impact": "可信验证未完成将影响TR5准入评审",
            "suggestion": "建议安全团队和性能团队并行推进，目标2天内完成可信验证"
          },
          {
            "type": "作业流-发布",
            "text": "发布窗口紧张",
            "level": "warning",
            "title": "发布窗口紧张",
            "rootCause": "TR5窗口仅剩4天，发布准备时间不足",
            "impact": "发布窗口紧张可能导致发布延期，影响客户交付",
            "suggestion": "建议提前准备发布材料，并行推进发布准备工作"
          }
        ],
        "quickQuestions": [
          "TR5延期风险如何消减？",
          "可信验证剩余工作何时完成？",
          "发布准备工作的优先级排序？"
        ]
      }
    }
  },
  "301.0.0": {
    "name": "301.0.0版本",
    "group": "V3",
    "progress": 72,
    "trustDetails": {
      "overallScore": 88,
      "status": "可信验证完成",
      "aiSummary": "已通过TR5可信评审，各项可信指标达标，安全合规无问题，架构升级后质量可控",
      "quickQuestions": [
        "可信问题的根本原因是什么？",
        "如何提升代码可信度？",
        "安全漏洞如何修复？"
      ],
      "productDefinition": {
        "ok": 6,
        "total": 6,
        "aiSummary": "产品定义维度共6项指标，已通过6项，整体达标率100%，状态优秀",
        "risks": [],
        "quickQuestions": [
          "产品定义状态如何？",
          "产品定义变更管理是否规范？",
          "需求稳定性评估？"
        ]
      },
      "design": {
        "ok": 9,
        "total": 10,
        "aiSummary": "设计维度共10项指标，已通过9项，整体达标率90%，状态良好",
        "risks": [
          {
            "type": "可信-设计",
            "text": "设计达标率90%",
            "level": "normal",
            "title": "设计验证接近完成",
            "rootCause": "1项设计指标待验证",
            "impact": "暂无影响",
            "suggestion": "完成剩余1项指标验证"
          }
        ],
        "quickQuestions": [
          "设计验证进展？",
          "剩余1项指标完成计划？",
          "设计变更管理是否规范？"
        ]
      },
      "coding": {
        "ok": 14,
        "total": 15,
        "aiSummary": "编码维度共15项指标，已通过14项，整体达标率93.3%，状态优秀",
        "risks": [
          {
            "type": "可信-编码",
            "text": "编码达标率93.3%",
            "level": "normal",
            "title": "代码质量良好",
            "rootCause": "1项编码指标待完成",
            "impact": "暂无影响",
            "suggestion": "完成剩余1项指标"
          }
        ],
        "quickQuestions": [
          "代码质量现状？",
          "剩余1项指标完成计划？",
          "代码评审覆盖情况？"
        ]
      },
      "build": {
        "ok": 3,
        "total": 3,
        "aiSummary": "构建维度共3项指标，已通过3项，整体达标率100%，状态优秀",
        "risks": [],
        "quickQuestions": [
          "构建流水线稳定性？",
          "构建产物管理规范？",
          "构建性能需要优化吗？"
        ]
      },
      "testing": {
        "ok": 8,
        "total": 9,
        "aiSummary": "测试维度共9项指标，已通过8项，整体达标率88.9%，状态良好",
        "risks": [
          {
            "type": "可信-测试",
            "text": "测试达标率88.9%",
            "level": "normal",
            "title": "测试覆盖良好",
            "rootCause": "1项测试指标待完成",
            "impact": "暂无影响",
            "suggestion": "完成剩余1项指标"
          }
        ],
        "quickQuestions": [
          "测试覆盖现状？",
          "剩余1项指标完成计划？",
          "测试用例是否已归档？"
        ]
      },
      "e2eProtection": {
        "ok": 4,
        "total": 5,
        "aiSummary": "E2E保护维度共5项指标，已通过4项，整体达标率80%，状态良好",
        "risks": [
          {
            "type": "可信-E2E保护",
            "text": "E2E保护达标率80%",
            "level": "normal",
            "title": "E2E保护接近完善",
            "rootCause": "1项E2E保护指标待完成",
            "impact": "暂无影响",
            "suggestion": "完成剩余1项指标"
          }
        ],
        "quickQuestions": [
          "E2E保护机制完善计划？",
          "完整性验证进展？",
          "安全门禁配置情况？"
        ]
      },
      "openSource": {
        "ok": 3,
        "total": 3,
        "aiSummary": "开源维度共3项指标，已通过3项，整体达标率100%，状态优秀",
        "risks": [],
        "quickQuestions": [
          "开源合规状态如何？",
          "第三方组件管理规范？",
          "许可证清单是否已归档？"
        ]
      },
      "vulnerability": {
        "ok": 2,
        "total": 3,
        "aiSummary": "漏洞管理维度共3项指标，已通过2项，整体达标率66.7%，需完善漏洞管理",
        "risks": [
          {
            "type": "可信-漏洞管理",
            "text": "漏洞管理达标率66.7%",
            "level": "warning",
            "title": "漏洞管理待完善",
            "rootCause": "1项漏洞管理指标未完成，CVE跟踪待完善",
            "impact": "漏洞管理不完整可能存在安全风险",
            "suggestion": "完善CVE跟踪机制"
          }
        ],
        "quickQuestions": [
          "CVE跟踪机制完善计划？",
          "漏洞修复流程是否规范？",
          "安全扫描结果如何处理？"
        ]
      },
      "lifecycle": {
        "ok": 5,
        "total": 6,
        "aiSummary": "生命周期维度共6项指标，已通过5项，整体达标率83.3%，状态良好",
        "risks": [
          {
            "type": "可信-生命周期",
            "text": "生命周期达标率83.3%",
            "level": "normal",
            "title": "生命周期管理良好",
            "rootCause": "1项生命周期指标待完成",
            "impact": "暂无影响",
            "suggestion": "完成剩余1项指标"
          }
        ],
        "quickQuestions": [
          "生命周期管理现状？",
          "维护计划制定进展？",
          "退役流程是否已规划？"
        ]
      },
      "risks": [
        {
          "type": "可信",
          "text": "可信验证完成",
          "level": "normal",
          "title": "可信状态正常",
          "rootCause": "已完成可信验证",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "可信",
          "text": "TR6可信待规划",
          "level": "normal",
          "title": "TR6准备中",
          "rootCause": "TR6评审计划尚未制定",
          "impact": "暂无影响",
          "suggestion": "按计划推进TR6准备工作"
        },
        {
          "type": "可信",
          "text": "安全合规无问题",
          "level": "normal",
          "title": "合规状态良好",
          "rootCause": "安全合规检查已通过",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        },
        {
          "type": "可信",
          "text": "渗透测试通过",
          "level": "normal",
          "title": "渗透测试正常",
          "rootCause": "渗透测试已通过",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        }
      ]
    },
    "aiSummary": "301.0.0架构升级完成，执行率偏低",
    "intentQuestions": {
      "risk": [
        "执行率偏低会影响预算分配吗？",
        "架构复杂度会影响后续维护吗？"
      ],
      "decision": [
        "如何追回执行率差距？",
        "架构优化优先级如何排定？"
      ]
    },
    "milestone": {
      "status": "正常",
      "text": "已通过TR5",
      "statusColor": "green",
      "name": "301.0.0版本",
      "date": "已通过TR5",
      "aiSummary": "4个阶段4个已完成，当前「已通过TR5」进展正常",
      "quickQuestions": [
        "里程碑节点的主要风险是什么？",
        "如何确保节点按时达成？",
        "有哪些可并行的任务？"
      ],
      "phases": [
        {
          "name": "需求收集",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "迭代1",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "迭代2",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "TR5",
          "progress": 100,
          "status": "completed"
        }
      ],
      "risks": [
        {
          "type": "里程碑",
          "text": "TR6待规划",
          "level": "normal",
          "title": "TR6节点规划中",
          "rootCause": "TR6评审计划尚未制定",
          "impact": "暂无影响，需提前规划TR6节点",
          "suggestion": "按计划推进TR6准备工作，及时确认TR6评审时间"
        },
        {
          "type": "里程碑",
          "text": "架构升级收尾中",
          "level": "normal",
          "title": "架构升级收尾",
          "rootCause": "架构升级已完成，进入收尾阶段",
          "impact": "暂无影响，关注收尾进度即可",
          "suggestion": "保持现状，完成架构升级收尾工作"
        }
      ]
    },
    "scope": {
      "inProgress": 3,
      "baseline": 42,
      "pending": 1,
      "status": "green",
      "text": "需求已冻结",
      "aiSummary": "46项需求中，架构复杂度高增加维护难度，建议完善架构设计文档",
      "quickQuestions": [
        "范围变更的影响是什么？",
        "在途需求的优先级如何？",
        "如何控制范围蔓延？"
      ],
      "risks": [
        {
          "type": "范围",
          "text": "架构复杂度高",
          "level": "warning",
          "title": "架构复杂度风险",
          "rootCause": "本次架构升级涉及3个核心模块，复杂度较高",
          "impact": "架构复杂度高将增加后续维护难度",
          "suggestion": "建议完善架构设计文档，增加代码评审频次"
        },
        {
          "type": "范围",
          "text": "遗留需求待关闭",
          "level": "normal",
          "title": "遗留项处理中",
          "rootCause": "5项遗留需求变更待评审",
          "impact": "影响整体交付",
          "suggestion": "尽快完成遗留需求评审"
        },
        {
          "type": "范围",
          "text": "文档更新滞后",
          "level": "normal",
          "title": "文档维护风险",
          "rootCause": "架构变更文档未及时更新",
          "impact": "影响后续维护",
          "suggestion": "加强文档更新管理"
        },
        {
          "type": "范围",
          "text": "接口文档待更新",
          "level": "normal",
          "title": "接口文档风险",
          "rootCause": "接口变更后文档未更新",
          "impact": "影响团队协作",
          "suggestion": "更新接口文档"
        }
      ]
    },
    "schedule": {
      "status": "green",
      "text": "进度正常",
      "iterProgress": 72,
      "testProgress": 65,
      "failed": 3,
      "passRate": 95,
      "aiSummary": "迭代72%，通过率95%，进度正常无风险点，建议保持现状监控",
      "quickQuestions": [
        "进度延误的根本原因是什么？",
        "如何追赶进度？",
        "关键路径上的任务有哪些？"
      ],
      "risks": [
        {
          "type": "进度",
          "text": "进度正常",
          "level": "normal",
          "title": "进度可控",
          "rootCause": "已通过TR5",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "进度",
          "text": "迭代2收尾中",
          "level": "normal",
          "title": "迭代收尾阶段",
          "rootCause": "迭代2接近完成",
          "impact": "暂无影响",
          "suggestion": "按计划完成迭代收尾"
        },
        {
          "type": "进度",
          "text": "TR6节点待确认",
          "level": "normal",
          "title": "TR6节点规划中",
          "rootCause": "TR6评审时间待确认",
          "impact": "暂无影响",
          "suggestion": "及时确认TR6节点"
        },
        {
          "type": "进度",
          "text": "回归测试进行中",
          "level": "normal",
          "title": "回归测试正常",
          "rootCause": "回归测试正常进行",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        }
      ]
    },
    "resource": {
      "dev": 8,
      "test": 6,
      "env": "green",
      "status": "green",
      "text": "资源满足",
      "risks": [
        {
          "type": "资源",
          "text": "资源满足",
          "level": "normal",
          "title": "资源状态正常",
          "rootCause": "人力配置合理",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "资源",
          "text": "人员复用规划中",
          "level": "normal",
          "title": "资源复用计划",
          "rootCause": "项目收尾阶段人员复用规划中",
          "impact": "暂无影响",
          "suggestion": "按计划推进人员复用"
        },
        {
          "type": "资源",
          "text": "培训资源充足",
          "level": "normal",
          "title": "培训支持到位",
          "rootCause": "培训资源已准备",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        },
        {
          "type": "资源",
          "text": "设备资源充足",
          "level": "normal",
          "title": "设备状态正常",
          "rootCause": "设备配置合理",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        }
      ]
    },
    "budget": {
      "executionRate": 68,
      "executed": 2.04,
      "total": 3,
      "status": "yellow",
      "text": "执行率68%，略低于预期",
      "aiSummary": "预算3.0M执行率68%，略低于预期12%，建议合理规划后续预算使用",
      "quickQuestions": [
        "费用偏差的原因是什么？",
        "如何控制费用超支？",
        "预算调整的建议？"
      ],
      "risks": [
        {
          "type": "费用",
          "text": "预算执行率低于预期12%",
          "level": "warning",
          "title": "执行率偏差风险",
          "rootCause": "架构升级复杂度高，部分人力投入延后",
          "impact": "执行率68%略低于预期进度72%",
          "suggestion": "合理规划后续预算使用，加快执行进度"
        }
      ]
    },
    "quality": {
      "di": 32,
      "defects": 8,
      "warnings": 150,
      "resolveRate": 88,
      "status": "green",
      "text": "质量可控",
      "aiSummary": "DI值32，缺陷8个，DI值偏高处于边缘，建议建立代码质量门禁",
      "quickQuestions": [
        "质量问题的根本原因是什么？",
        "如何提升代码质量？",
        "测试覆盖率如何提升？"
      ],
      "risks": [
        {
          "type": "质量",
          "text": "DI值偏高",
          "level": "warning",
          "title": "DI值需优化",
          "rootCause": "代码变更150条，静态检查告警150条",
          "impact": "DI值32分处于边缘，需持续优化避免触发门禁",
          "suggestion": "建议建立代码质量门禁"
        },
        {
          "type": "质量",
          "text": "遗留缺陷8个",
          "level": "normal",
          "title": "遗留缺陷可控",
          "rootCause": "8个遗留缺陷均为低优先级",
          "impact": "暂不影响上线",
          "suggestion": "在后续版本中安排修复"
        },
        {
          "type": "质量",
          "text": "回归测试通过",
          "level": "normal",
          "title": "回归测试状态良好",
          "rootCause": "回归测试用例100%通过",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        },
        {
          "type": "质量",
          "text": "单元测试覆盖率85%",
          "level": "normal",
          "title": "测试覆盖良好",
          "rootCause": "单元测试覆盖率高",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        }
      ]
    },
    "workflow": {
      "design": {
        "status": "green",
        "aiSummary": "架构升级完成，<br>设计文档完善",
        "risks": [
          {
            "type": "作业流-需求",
            "text": "架构评审通过",
            "level": "normal",
            "title": "架构评审通过",
            "rootCause": "架构设计方案经过多轮评审，满足功能性和非功能性需求",
            "impact": "架构稳定支撑后续开发和维护工作",
            "suggestion": "持续完善架构设计文档，保持文档与实现同步"
          },
          {
            "type": "作业流-需求",
            "text": "设计文档完善",
            "level": "normal",
            "title": "设计文档完善",
            "rootCause": "设计阶段产出的接口文档、时序图等资料齐全",
            "impact": "完善的文档支持团队快速理解和后续新人上手",
            "suggestion": "定期回顾和更新设计文档，确保与代码一致"
          }
        ],
        "quickQuestions": [
          "架构升级还有什么遗留问题？",
          "设计文档是否与代码保持同步？",
          "TR6架构设计何时启动？"
        ]
      },
      "dev": {
        "status": "green",
        "aiSummary": "编码已完成，<br>代码评审通过",
        "risks": [
          {
            "type": "作业流-开发",
            "text": "编码完成",
            "level": "normal",
            "title": "编码完成",
            "rootCause": "所有开发任务已完成并通过单元测试验证",
            "impact": "编码完成标志项目进入测试收尾阶段",
            "suggestion": "关注回归测试结果，及时修复发现的问题"
          },
          {
            "type": "作业流-开发",
            "text": "代码评审通过",
            "level": "normal",
            "title": "代码评审通过",
            "rootCause": "所有代码变更已完成评审并合并到主分支",
            "impact": "代码评审通过确保代码质量和可维护性",
            "suggestion": "保持代码规范，为后续版本奠定良好基础"
          }
        ],
        "quickQuestions": [
          "代码质量整体评估如何？",
          "技术债务清理计划是什么？",
          "代码资产移交进展如何？"
        ]
      },
      "build": {
        "status": "green",
        "aiSummary": "构建成功率100%，<br>流水线稳定",
        "risks": [
          {
            "type": "作业流-构建",
            "text": "构建正常",
            "level": "normal",
            "title": "构建正常",
            "rootCause": "构建环境稳定，CI/CD流水线运行正常，构建成功率100%",
            "impact": "构建环节无阻塞，支撑正常的迭代发布节奏",
            "suggestion": "继续保持构建环境稳定性，关注依赖安全告警"
          }
        ],
        "quickQuestions": [
          "构建环境是否稳定？",
          "依赖安全告警是否已处理？",
          "构建流水线还需要优化吗？"
        ]
      },
      "test": {
        "status": "green",
        "aiSummary": "测试通过，<br>质量门禁达标",
        "risks": [
          {
            "type": "作业流-测试",
            "text": "测试通过",
            "level": "normal",
            "title": "测试通过",
            "rootCause": "全部测试用例执行通过，覆盖率达到预期目标",
            "impact": "测试通过是TR5准入的必要条件，当前状态满足要求",
            "suggestion": "保持测试用例更新，关注线上运行反馈"
          },
          {
            "type": "作业流-测试",
            "text": "DI值32分可控",
            "level": "normal",
            "title": "DI值32分可控",
            "rootCause": "代码变更150条，静态检查告警150条，DI值32分处于边缘",
            "impact": "DI值接近阈值30，需持续优化避免触发质量门禁",
            "suggestion": "建议建立代码质量门禁，每次提交前自动检测DI值"
          }
        ],
        "quickQuestions": [
          "回归测试还有哪些遗留问题？",
          "DI值优化计划是什么？",
          "测试覆盖率是否达标？"
        ]
      },
      "release": {
        "status": "green",
        "aiSummary": "已通过TR5，<br>发布准备就绪",
        "risks": [
          {
            "type": "作业流-发布",
            "text": "TR5已通过",
            "level": "normal",
            "title": "TR5已通过",
            "rootCause": "TR5评审顺利通过，所有准入条件均已满足",
            "impact": "TR5通过标志着项目进入最终发布准备阶段",
            "suggestion": "按计划推进ER评审准备工作"
          }
        ],
        "quickQuestions": [
          "TR6评审准备情况如何？",
          "发布清单是否已检查？",
          "ER评审材料准备进展如何？"
        ]
      }
    }
  },
  "1.1.0": {
    "name": "1.1.0版本",
    "group": "MCU",
    "progress": 90,
    "trustDetails": {
      "overallScore": 94,
      "status": "可信验证完成",
      "aiSummary": "可信验证已全部通过，安全合规无问题，零高危漏洞，ER评审准备就绪",
      "quickQuestions": [
        "可信问题的根本原因是什么？",
        "如何提升代码可信度？",
        "安全漏洞如何修复？"
      ],
      "productDefinition": {
        "ok": 6,
        "total": 6,
        "aiSummary": "产品定义维度共6项指标，已通过6项，整体达标率100%，状态优秀，即将结项",
        "risks": [],
        "quickQuestions": [
          "产品定义最终状态确认？",
          "产品定义文档归档完成？",
          "需求移交清单是否完整？"
        ]
      },
      "design": {
        "ok": 10,
        "total": 10,
        "aiSummary": "设计维度共10项指标，已通过10项，整体达标率100%，状态优秀",
        "risks": [],
        "quickQuestions": [
          "设计文档最终归档完成？",
          "设计经验如何总结？",
          "设计资产移交清单是否完整？"
        ]
      },
      "coding": {
        "ok": 15,
        "total": 15,
        "aiSummary": "编码维度共15项指标，已通过15项，整体达标率100%，零缺陷交付状态优秀",
        "risks": [],
        "quickQuestions": [
          "代码资产最终归档完成？",
          "代码规范经验如何总结？",
          "代码移交清单是否完整？"
        ]
      },
      "build": {
        "ok": 3,
        "total": 3,
        "aiSummary": "构建维度共3项指标，已通过3项，整体达标率100%，状态优秀",
        "risks": [],
        "quickQuestions": [
          "构建产物最终归档完成？",
          "构建流水线何时下线？",
          "构建环境资源释放计划？"
        ]
      },
      "testing": {
        "ok": 9,
        "total": 9,
        "aiSummary": "测试维度共9项指标，已通过9项，整体达标率100%，用例执行率96%，状态优秀",
        "risks": [],
        "quickQuestions": [
          "测试用例最终归档完成？",
          "测试经验如何总结？",
          "测试数据清理计划？"
        ]
      },
      "e2eProtection": {
        "ok": 5,
        "total": 5,
        "aiSummary": "E2E保护维度共5项指标，已通过5项，整体达标率100%，状态优秀",
        "risks": [],
        "quickQuestions": [
          "E2E保护最终验证完成？",
          "安全门禁配置归档？",
          "完整性保护文档移交？"
        ]
      },
      "openSource": {
        "ok": 3,
        "total": 3,
        "aiSummary": "开源维度共3项指标，已通过3项，整体达标率100%，合规无问题",
        "risks": [],
        "quickQuestions": [
          "开源合规最终确认？",
          "许可证清单归档完成？",
          "第三方组件清单移交？"
        ]
      },
      "vulnerability": {
        "ok": 3,
        "total": 3,
        "aiSummary": "漏洞管理维度共3项指标，已通过3项，整体达标率100%，零漏洞状态优秀",
        "risks": [],
        "quickQuestions": [
          "漏洞管理最终确认？",
          "CVE跟踪记录归档？",
          "安全扫描报告移交？"
        ]
      },
      "lifecycle": {
        "ok": 6,
        "total": 6,
        "aiSummary": "生命周期维度共6项指标，已通过6项，整体达标率100%，状态优秀",
        "risks": [],
        "quickQuestions": [
          "生命周期管理最终确认？",
          "维护计划文档归档？",
          "退役流程是否已规划？"
        ]
      },
      "risks": [
        {
          "type": "可信",
          "text": "可信验证完成",
          "level": "normal",
          "title": "可信状态正常",
          "rootCause": "已完成可信验证",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "可信",
          "text": "安全合规通过",
          "level": "normal",
          "title": "合规状态良好",
          "rootCause": "安全合规检查已通过",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        }
      ]
    },
    "aiSummary": "1.1.0版本运行正常，即将结项",
    "intentQuestions": {
      "risk": [
        "遗留缺陷会影响结项评审吗？",
        "还有哪些收尾工作需要关注？"
      ],
      "decision": [
        "遗留缺陷如何处理？",
        "结项评审材料如何准备？"
      ]
    },
    "milestone": {
      "status": "正常",
      "text": "ER评审（4/5）",
      "statusColor": "green",
      "name": "1.1.0版本",
      "date": "ER评审（4/5）",
      "aiSummary": "4个阶段3个已完成，当前「ER评审（4/5）」进展正常",
      "quickQuestions": [
        "里程碑节点的主要风险是什么？",
        "如何确保节点按时达成？",
        "有哪些可并行的任务？"
      ],
      "phases": [
        {
          "name": "需求收集",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "迭代1",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "迭代2",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "ER",
          "progress": 90,
          "status": "active"
        }
      ],
      "risks": [
        {
          "type": "里程碑",
          "text": "ER评审准备中",
          "level": "normal",
          "title": "ER评审材料准备",
          "rootCause": "ER评审（4/5）进度90%，评审材料准备中",
          "impact": "暂无影响，保持正常推进",
          "suggestion": "按计划完成ER评审材料准备"
        },
        {
          "type": "里程碑",
          "text": "结项倒计时",
          "level": "normal",
          "title": "结项工作收尾",
          "rootCause": "项目进入最终结项阶段",
          "impact": "暂无影响，关注结项清单完成情况",
          "suggestion": "提前检查结项清单，确保无遗漏项"
        }
      ]
    },
    "scope": {
      "inProgress": 0,
      "baseline": 25,
      "pending": 0,
      "status": "green",
      "text": "需求完全冻结",
      "aiSummary": "25项需求已完全冻结，范围可控无风险，建议保持现状监控",
      "quickQuestions": [
        "范围变更的影响是什么？",
        "在途需求的优先级如何？",
        "如何控制范围蔓延？"
      ],
      "risks": [
        {
          "type": "范围",
          "text": "需求完全冻结",
          "level": "normal",
          "title": "范围可控",
          "rootCause": "需求已完全交付",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "范围",
          "text": "遗留需求已关闭",
          "level": "normal",
          "title": "遗留项关闭",
          "rootCause": "遗留需求已全部处理",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        }
      ]
    },
    "schedule": {
      "status": "green",
      "text": "进度超前",
      "iterProgress": 90,
      "testProgress": 88,
      "failed": 1,
      "passRate": 96,
      "aiSummary": "迭代90%，通过率96%，进度超前无风险，建议继续保持日常监控",
      "quickQuestions": [
        "进度延误的根本原因是什么？",
        "如何追赶进度？",
        "关键路径上的任务有哪些？"
      ],
      "risks": [
        {
          "type": "进度",
          "text": "进度超前",
          "level": "normal",
          "title": "进度正常",
          "rootCause": "进度90%，ER评审（4/5）节点正常",
          "impact": "当前无明显风险点",
          "suggestion": "继续保持日常监控即可"
        },
        {
          "type": "进度",
          "text": "结项工作收尾中",
          "level": "normal",
          "title": "结项收尾",
          "rootCause": "结项材料准备中",
          "impact": "暂无影响",
          "suggestion": "按计划完成结项"
        }
      ]
    },
    "resource": {
      "dev": 6,
      "test": 4,
      "env": "green",
      "status": "green",
      "text": "资源充足",
      "risks": [
        {
          "type": "资源",
          "text": "资源充足",
          "level": "normal",
          "title": "资源状态正常",
          "rootCause": "人力配置合理",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "资源",
          "text": "人员释放规划中",
          "level": "normal",
          "title": "资源释放",
          "rootCause": "项目收尾人员释放规划中",
          "impact": "暂无影响",
          "suggestion": "按计划执行"
        }
      ]
    },
    "budget": {
      "executionRate": 92,
      "executed": 1.84,
      "total": 2,
      "status": "green",
      "text": "执行率92%，即将完成",
      "aiSummary": "预算2.0M执行率92%，即将完成，执行节奏良好",
      "quickQuestions": [
        "费用偏差的原因是什么？",
        "如何控制费用超支？",
        "预算调整的建议？"
      ],
      "risks": [
        {
          "type": "费用",
          "text": "预算执行进度良好",
          "level": "normal",
          "title": "费用状态正常",
          "rootCause": "执行率92%符合项目收尾节奏",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "费用",
          "text": "注意预算节余管理",
          "level": "normal",
          "title": "预算节余风险",
          "rootCause": "执行率92%预计有少量节余",
          "impact": "预算节余需按规定处理",
          "suggestion": "按财务规定处理节余资金"
        }
      ]
    },
    "quality": {
      "di": 28,
      "defects": 2,
      "warnings": 45,
      "resolveRate": 95,
      "status": "green",
      "text": "质量优良",
      "aiSummary": "DI值28，缺陷2个，质量优良零高危，建议保持现状",
      "quickQuestions": [
        "质量问题的根本原因是什么？",
        "如何提升代码质量？",
        "测试覆盖率如何提升？"
      ],
      "risks": [
        {
          "type": "质量",
          "text": "遗留2个低优先级缺陷",
          "level": "normal",
          "title": "遗留缺陷",
          "rootCause": "2个低优先级缺陷计划在下一版本修复",
          "impact": "遗留缺陷暂不影响线上运行",
          "suggestion": "建议在1.2.0版本规划中安排2个缺陷的修复"
        },
        {
          "type": "质量",
          "text": "代码质量良好",
          "level": "normal",
          "title": "质量状态良好",
          "rootCause": "代码质量稳定",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        }
      ]
    },
    "workflow": {
      "design": {
        "status": "green",
        "aiSummary": "设计已完成，<br>无遗留问题",
        "risks": [
          {
            "type": "作业流-需求",
            "text": "无阻塞问题",
            "level": "normal",
            "title": "无阻塞问题",
            "rootCause": "设计阶段所有交付物已完成并通过评审归档",
            "impact": "设计阶段无遗留问题，支持项目正常推进到结项",
            "suggestion": "保持现状，关注结项评审中的设计相关反馈"
          }
        ],
        "quickQuestions": [
          "设计文档是否已全部归档？",
          "还有哪些设计遗留问题需要处理？",
          "设计经验如何总结？"
        ]
      },
      "dev": {
        "status": "green",
        "aiSummary": "编码已完成，<br>代码质量良好",
        "risks": [
          {
            "type": "作业流-开发",
            "text": "无阻塞问题",
            "level": "normal",
            "title": "无阻塞问题",
            "rootCause": "所有开发任务完成，代码已通过评审并归档",
            "impact": "开发环节无阻塞，支撑项目按计划结项",
            "suggestion": "做好代码资产移交和文档归档"
          }
        ],
        "quickQuestions": [
          "代码资产移交是否完成？",
          "还有哪些开发遗留工作？",
          "开发经验如何总结？"
        ]
      },
      "build": {
        "status": "green",
        "aiSummary": "构建成功率100%，<br>流水线正常",
        "risks": [
          {
            "type": "作业流-构建",
            "text": "构建正常",
            "level": "normal",
            "title": "构建正常",
            "rootCause": "构建环境稳定运行，构建流水线无异常",
            "impact": "构建环节稳定可靠，支撑版本发布工作",
            "suggestion": "保持构建环境维护直至项目正式结项"
          }
        ],
        "quickQuestions": [
          "构建流水线何时下线？",
          "构建产物是否已归档？",
          "构建环境维护计划是什么？"
        ]
      },
      "test": {
        "status": "green",
        "aiSummary": "测试通过，<br>用例执行率96%",
        "risks": [
          {
            "type": "作业流-测试",
            "text": "遗留2个低优先级缺陷",
            "level": "normal",
            "title": "遗留2个低优先级缺陷",
            "rootCause": "2个缺陷为UI体验类问题，不影响核心功能",
            "impact": "低优先级缺陷暂不影响上线运行，计划在下一版本修复",
            "suggestion": "在1.2.0版本规划中安排2个缺陷的修复"
          }
        ],
        "quickQuestions": [
          "测试用例是否已全部归档？",
          "遗留缺陷处理计划是什么？",
          "测试经验如何总结？"
        ]
      },
      "release": {
        "status": "green",
        "aiSummary": "ER评审（4/5），<br>即将结项",
        "risks": [
          {
            "type": "作业流-发布",
            "text": "无阻塞问题",
            "level": "normal",
            "title": "无阻塞问题",
            "rootCause": "发布材料已准备完毕，ER评审排期已确认",
            "impact": "发布准备工作就绪，支持按计划完成ER评审和结项",
            "suggestion": "提前检查发布清单，确保无遗漏项"
          }
        ],
        "quickQuestions": [
          "ER评审准备情况如何？",
          "发布清单是否已检查完毕？",
          "结项材料准备进展如何？"
        ]
      }
    }
  },
  "1.0.0": {
    "name": "1.0.0版本",
    "group": "MCU",
    "progress": 100,
    "trustDetails": {
      "overallScore": 100,
      "status": "已结项",
      "aiSummary": "项目已完成结项，所有可信指标100%达标，零缺陷交付，经验总结归档完成",
      "quickQuestions": [
        "可信问题的根本原因是什么？",
        "如何提升代码可信度？",
        "安全漏洞如何修复？"
      ],
      "productDefinition": {
        "ok": 6,
        "total": 6,
        "aiSummary": "产品定义维度共6项指标，已通过6项，整体达标率100%，项目已结项",
        "risks": [],
        "quickQuestions": [
          "产品定义经验如何总结？",
          "产品定义文档归档情况？",
          "需求移交清单是否完整？"
        ]
      },
      "design": {
        "ok": 10,
        "total": 10,
        "aiSummary": "设计维度共10项指标，已通过10项，整体达标率100%，项目已结项",
        "risks": [],
        "quickQuestions": [
          "设计经验如何总结沉淀？",
          "设计文档归档是否完整？",
          "有哪些可复用的设计模式？"
        ]
      },
      "coding": {
        "ok": 15,
        "total": 15,
        "aiSummary": "编码维度共15项指标，已通过15项，整体达标率100%，零缺陷交付，项目已结项",
        "risks": [],
        "quickQuestions": [
          "代码资产移交是否完成？",
          "代码规范经验如何沉淀？",
          "有哪些可复用的组件？"
        ]
      },
      "build": {
        "ok": 3,
        "total": 3,
        "aiSummary": "构建维度共3项指标，已通过3项，整体达标率100%，项目已结项",
        "risks": [],
        "quickQuestions": [
          "构建产物归档是否完成？",
          "构建流水线是否已下线？",
          "构建环境资源是否已释放？"
        ]
      },
      "testing": {
        "ok": 9,
        "total": 9,
        "aiSummary": "测试维度共9项指标，已通过9项，整体达标率100%，用例执行率98%，项目已结项",
        "risks": [],
        "quickQuestions": [
          "测试用例归档是否完成？",
          "测试经验如何总结？",
          "测试数据是否已清理？"
        ]
      },
      "e2eProtection": {
        "ok": 5,
        "total": 5,
        "aiSummary": "E2E保护维度共5项指标，已通过5项，整体达标率100%，项目已结项",
        "risks": [],
        "quickQuestions": [
          "E2E保护验证归档？",
          "安全门禁配置归档？",
          "完整性保护文档移交？"
        ]
      },
      "openSource": {
        "ok": 3,
        "total": 3,
        "aiSummary": "开源维度共3项指标，已通过3项，整体达标率100%，合规无问题，项目已结项",
        "risks": [],
        "quickQuestions": [
          "开源合规归档完成？",
          "许可证清单归档情况？",
          "第三方组件清单移交？"
        ]
      },
      "vulnerability": {
        "ok": 3,
        "total": 3,
        "aiSummary": "漏洞管理维度共3项指标，已通过3项，整体达标率100%，零漏洞，项目已结项",
        "risks": [],
        "quickQuestions": [
          "漏洞管理归档完成？",
          "CVE跟踪记录归档？",
          "安全扫描报告移交？"
        ]
      },
      "lifecycle": {
        "ok": 6,
        "total": 6,
        "aiSummary": "生命周期维度共6项指标，已通过6项，整体达标率100%，项目已结项",
        "risks": [],
        "quickQuestions": [
          "生命周期管理归档完成？",
          "维护计划文档归档？",
          "退役流程是否已规划？"
        ]
      },
      "risks": [
        {
          "type": "可信",
          "text": "可信验证完成",
          "level": "normal",
          "title": "可信状态正常",
          "rootCause": "已完成可信验证",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "可信",
          "text": "安全合规已通过",
          "level": "normal",
          "title": "合规状态正常",
          "rootCause": "安全合规已通过",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        }
      ]
    },
    "aiSummary": "1.0.0版本已完成结项",
    "intentQuestions": {
      "risk": [],
      "decision": [
        "项目经验如何总结沉淀？",
        "团队知识如何有效传承？"
      ]
    },
    "milestone": {
      "status": "完成",
      "text": "已结项",
      "statusColor": "green",
      "name": "1.0.0版本",
      "date": "已结项",
      "aiSummary": "4个阶段4个已完成，当前「已结项」进展正常",
      "quickQuestions": [
        "里程碑节点的主要风险是什么？",
        "如何确保节点按时达成？",
        "有哪些可并行的任务？"
      ],
      "phases": [
        {
          "name": "需求收集",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "迭代1",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "迭代2",
          "progress": 100,
          "status": "completed"
        },
        {
          "name": "ER",
          "progress": 100,
          "status": "completed"
        }
      ],
      "risks": [
        {
          "type": "里程碑",
          "text": "已结项无风险",
          "level": "normal",
          "title": "项目已结项",
          "rootCause": "项目已完成结项，所有里程碑已达成",
          "impact": "暂无影响",
          "suggestion": "项目已完成，保持归档即可"
        }
      ]
    },
    "scope": {
      "inProgress": 0,
      "baseline": 20,
      "pending": 0,
      "status": "green",
      "text": "需求完全交付",
      "aiSummary": "20项需求已完全交付，范围可控无风险，项目已完成",
      "quickQuestions": [
        "范围变更的影响是什么？",
        "在途需求的优先级如何？",
        "如何控制范围蔓延？"
      ],
      "risks": [
        {
          "type": "范围",
          "text": "需求完全交付",
          "level": "normal",
          "title": "范围可控",
          "rootCause": "需求已完全交付",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "范围",
          "text": "所有需求已关闭",
          "level": "normal",
          "title": "范围已关闭",
          "rootCause": "所有需求项已处理完成",
          "impact": "暂无影响",
          "suggestion": "保持现状"
        }
      ]
    },
    "schedule": {
      "status": "green",
      "text": "已结项",
      "iterProgress": 100,
      "testProgress": 100,
      "failed": 0,
      "passRate": 98,
      "aiSummary": "迭代100%，通过率98%，项目已完成结项，建议做好经验归档",
      "quickQuestions": [
        "进度延误的根本原因是什么？",
        "如何追赶进度？",
        "关键路径上的任务有哪些？"
      ],
      "risks": [
        {
          "type": "进度",
          "text": "已结项",
          "level": "normal",
          "title": "进度完成",
          "rootCause": "项目已结项",
          "impact": "暂无影响",
          "suggestion": "项目已完成结项"
        }
      ]
    },
    "resource": {
      "dev": 0,
      "test": 0,
      "env": "yellow",
      "status": "yellow",
      "text": "释放协调中",
      "risks": [
        {
          "type": "资源",
          "text": "释放协调中",
          "level": "normal",
          "title": "资源释放",
          "rootCause": "项目结项中",
          "impact": "暂无影响",
          "suggestion": "完成资源释放协调"
        }
      ]
    },
    "budget": {
      "executionRate": 100,
      "executed": 2,
      "total": 2,
      "status": "green",
      "text": "执行率100%，已完成",
      "aiSummary": "预算2.0M执行率100%，已全部完成，无超支情况，建议按流程完成预算结算",
      "quickQuestions": [
        "费用偏差的原因是什么？",
        "如何控制费用超支？",
        "预算调整的建议？"
      ],
      "risks": [
        {
          "type": "费用",
          "text": "预算执行完成",
          "level": "normal",
          "title": "预算结项正常",
          "rootCause": "执行率100%，预算已全部使用",
          "impact": "暂无影响",
          "suggestion": "按流程完成预算结算"
        },
        {
          "type": "费用",
          "text": "无超支情况",
          "level": "normal",
          "title": "费用合规正常",
          "rootCause": "预算执行精准，无超支",
          "impact": "暂无影响",
          "suggestion": "项目经验归档"
        }
      ]
    },
    "quality": {
      "di": 25,
      "defects": 0,
      "warnings": 20,
      "resolveRate": 100,
      "status": "green",
      "text": "零缺陷交付",
      "aiSummary": "DI值25，缺陷0个，零缺陷交付质量优良，建议做好知识传承",
      "quickQuestions": [
        "质量问题的根本原因是什么？",
        "如何提升代码质量？",
        "测试覆盖率如何提升？"
      ],
      "risks": [
        {
          "type": "质量",
          "text": "零缺陷交付",
          "level": "normal",
          "title": "质量优良",
          "rootCause": "零缺陷交付",
          "impact": "暂无影响",
          "suggestion": "保持现状监控即可"
        },
        {
          "type": "质量",
          "text": "项目经验已总结",
          "level": "normal",
          "title": "知识沉淀",
          "rootCause": "项目经验已归档",
          "impact": "暂无影响",
          "suggestion": "知识传承"
        }
      ]
    },
    "workflow": {
      "design": {
        "status": "green",
        "aiSummary": "已完成，<br>零缺陷交付",
        "risks": [],
        "quickQuestions": [
          "设计经验总结是否完成？",
          "设计文档是否已归档？",
          "有哪些可复用的设计模式？"
        ]
      },
      "dev": {
        "status": "green",
        "aiSummary": "已完成，<br>代码归档",
        "risks": [],
        "quickQuestions": [
          "代码资产是否已移交？",
          "代码规范经验如何沉淀？",
          "有哪些可复用的组件？"
        ]
      },
      "build": {
        "status": "green",
        "aiSummary": "已完成，<br>构建归档",
        "risks": [],
        "quickQuestions": [
          "构建产物是否已归档？",
          "构建流水线是否已下线？",
          "构建环境资源是否已释放？"
        ]
      },
      "test": {
        "status": "green",
        "aiSummary": "已完成，<br>测试归档",
        "risks": [],
        "quickQuestions": [
          "测试用例是否已归档？",
          "测试经验如何总结？",
          "测试数据是否已清理？"
        ]
      },
      "release": {
        "status": "green",
        "aiSummary": "已结项，<br>版本发布完成",
        "risks": [],
        "quickQuestions": [
          "结项材料是否已归档？",
          "项目经验总结完成了吗？",
          "资源释放协调进展如何？"
        ]
      }
    }
  }
}

/** 项目列表（用于选择器） */
export const projectList = Object.keys(projectData).map(key => ({
  id: key,
  name: projectData[key].name,
  group: projectData[key].group,
  progress: projectData[key].progress
}))

/** 可信管理子卡片 key 映射 */
export const trustCategoryMap = {
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

/** 五领域 workflow key 映射 */
export const workflowDomainMap = {
  design: { label: '设计领域', tag: 'SE' },
  dev: { label: '开发领域', tag: 'DEV' },
  build: { label: '构建领域', tag: 'BUILD' },
  test: { label: '测试领域', tag: 'QA' },
  release: { label: '发布领域', tag: 'REL' }
}

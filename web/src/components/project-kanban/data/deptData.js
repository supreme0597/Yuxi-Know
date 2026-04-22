/**
 * 部门级看板 Mock 数据
 * 从 project-manager2/js/data/dept-data.js 完整同步，转为 ES Module
 *
 * ⚠️ 此文件为设计稿数据的 1:1 映射，仅导出与设计稿一致的 deptData 对象
 *    如需修改数据结构，请先修改设计稿源文件，再同步到此
 */

export const deptData = {
    "department": {
        "milestone": {
            "status": "预警",
            "statusType": "red",
            "hasAlert": true,
            "text": "301.0-301.1开发项目的审视节点需重点关注",
            "aiSummary": "4个offering推进中，1个高风险、1个中风险。V3项目301.0-301.1的RR准入节点已延期15%，需立即介入；V2项目208.11-208.12审视节点有8%延期风险，需重点跟进；MCU和维护项目整体正常。",
            "timeline": [
                {
                    "project": "208.11-208.12开发项目",
                    "group": "V2",
                    "category": "RTOS V2",
                    "status": "在研",
                    "nextMilestone": "审视",
                    "nextDate": "4/1",
                    "deviation": -8.3,
                    "phases": [
                        {
                            "name": "立项", "date": "2/15", "status": "completed", "risk": "none",
                            "objectives": ["完成产品需求规格书v1.0", "通过立项评审", "确认资源预算"],
                            "aiSummary": "立项节点已正常完成，产品需求规格书v1.0已通过评审，资源预算已确认。",
                            "risks": [
                                { "level": "normal", "title": "立项节点已正常完成", "rootCause": "产品需求规格书v1.0已通过立项评审，资源预算已确认", "impact": "暂无影响", "suggestion": "继续按计划推进审视阶段" }
                            ]
                        },
                        {
                            "name": "审视", "date": "4/1", "status": "pending", "risk": "yellow",
                            "overduePercent": 8,
                            "objectives": ["需求基线冻结", "架构评审通过", "关键风险闭环"],
                            "riskReason": "需求变更频繁，架构方案仍在评审中",
                            "aiSummary": "审视节点有8%延期风险，需求变更频繁，架构方案仍在评审中，需尽快完成架构评审锁定需求基线。",
                            "risks": [
                                { "level": "warning", "title": "审视节点延期风险", "rootCause": "需求变更频繁，架构方案仍在评审中，延期约8%", "impact": "可能影响后续审视节点达成，需关注架构评审进度", "suggestion": "建议本周内完成架构评审，锁定需求基线" }
                            ]
                        },
                        {
                            "name": "结项", "date": "12/31", "status": "pending", "risk": "none",
                            "objectives": ["所有特性开发完成", "集成测试通过率≥95%", "发布文档齐套"],
                            "aiSummary": "结项节点尚远，当前关键是审视阶段的推进情况将直接影响结项节奏。",
                            "risks": []
                        }
                    ],
                    "currentPhase": "审视中",
                    "aiSummary": "208.11-208.12开发项目审视节点有8%延期风险，需求变更频繁，架构方案仍在评审中。立项已正常完成，结项节点尚远，当前关键是尽快完成架构评审锁定需求基线。",
                    "quickQuestions": [
                        "审视节点延期8%如何补救？",
                        "架构评审预计何时完成？",
                        "需求变更对结项有何影响？",
                        "是否需要调整里程碑计划？"
                    ]
                },
                {
                    "project": "301.0-301.1开发项目",
                    "group": "V3",
                    "category": "RTOS V3",
                    "status": "在研",
                    "nextMilestone": "RR准入",
                    "nextDate": "3/28",
                    "deviation": 12.5,
                    "phases": [
                        {
                            "name": "立项", "date": "2/10", "status": "completed", "risk": "none",
                            "objectives": ["完成V3平台立项评审", "关键技术路线确认", "人力资源锁定"],
                            "aiSummary": "立项节点已正常完成，V3平台立项评审通过，技术路线和人力资源已确认。",
                            "risks": []
                        },
                        {
                            "name": "RR准入", "date": "3/28", "status": "pending", "risk": "high",
                            "overduePercent": 15,
                            "objectives": ["RR准入条件定义", "架构评审通过", "测试策略发布"],
                            "riskReason": "编码进度滞后导致RR准入条件未达成",
                            "aiSummary": "RR准入节点已严重延期15%，编码进度滞后是主因，准入条件未达成，需立即介入追赶。",
                            "risks": [
                                { "level": "critical", "title": "RR准入节点严重延期", "rootCause": "编码进度滞后，RR准入条件未达成，延期约15%", "impact": "影响版本发布计划，下游项目依赖受阻，可能导致客户交付延期", "suggestion": "建议申请资源加速追赶，评估里程碑节点调整可能性" }
                            ]
                        },
                        {
                            "name": "结项", "date": "12/31", "status": "pending", "risk": "yellow",
                            "objectives": ["RR准入条件100%达成", "遗留缺陷清零（P1/P2）", "版本发布包就绪"],
                            "riskReason": "301.1.0版本当前进度滞后，需加速追赶",
                            "aiSummary": "结项节点存在中风险，301.1.0版本进度滞后，需加速追赶以确保按期发布。",
                            "risks": [
                                { "level": "warning", "title": "结项节点存在滞后风险", "rootCause": "301.1.0版本当前进度滞后，需加速追赶", "impact": "可能影响最终版本发布和客户交付", "suggestion": "建议制定追赶计划，增加关键路径资源投入" }
                            ]
                        }
                    ],
                    "currentPhase": "RR准入中，已延期",
                    "aiSummary": "301.0-301.1开发项目RR准入节点已严重延期15%，编码进度滞后是主因。结项节点也存在中风险，301.1.0版本进度滞后需加速追赶。整体风险最高，需立即介入。",
                    "quickQuestions": [
                        "RR准入延期15%如何补救？",
                        "是否需要调整里程碑节点？",
                        "301.1.0版本追赶计划是什么？",
                        "下游项目受何影响？"
                    ]
                },
                {
                    "project": "1.0-1.1开发项目",
                    "group": "MCU",
                    "category": "RTOS MCU",
                    "status": "在研",
                    "nextMilestone": "TR5评审",
                    "nextDate": "5/30",
                    "deviation": -5.0,
                    "phases": [
                        {
                            "name": "立项", "date": "2/01", "status": "completed", "risk": "none",
                            "objectives": ["MCU固件需求冻结", "硬件接口规格确认", "供应链评估完成"],
                            "aiSummary": "立项节点已正常完成，MCU固件需求已冻结，硬件接口规格和供应链评估已确认。",
                            "risks": []
                        },
                        {
                            "name": "审视", "date": "3/15", "status": "completed", "risk": "none",
                            "objectives": ["固件开发完成率≥70%", "单元测试覆盖率≥85%", "硬件联调通过"],
                            "aiSummary": "审视节点已正常完成，固件开发完成率达标，单元测试覆盖率和硬件联调均通过。",
                            "risks": []
                        },
                        {
                            "name": "结项", "date": "12/31", "status": "pending", "risk": "none",
                            "objectives": ["全功能测试通过", "EMC/安规测试完成", "量产包发布"],
                            "aiSummary": "结项节点尚远，当前开发推进正常，需关注TR5评审节点准备情况。",
                            "risks": [
                                { "level": "normal", "title": "整体正常推进", "rootCause": "立项和审视节点均已完成，开发按计划推进", "impact": "暂无影响", "suggestion": "关注TR5评审节点准备情况" }
                            ]
                        }
                    ],
                    "currentPhase": "审视完成，开发中",
                    "aiSummary": "1.0-1.1开发项目整体正常，立项和审视节点均已完成。MCU固件开发推进中，下一个关键节点为TR5评审（5/30），当前无风险信号。",
                    "quickQuestions": [
                        "TR5评审准备情况如何？",
                        "硬件联调进展如何？",
                        "MCU盈余人力可否调配到其他项目？",
                        "量产包发布计划有无调整？"
                    ]
                },
                {
                    "project": "2026年维护项目",
                    "group": "V2",
                    "category": "RTOS维护",
                    "status": "维护态",
                    "nextMilestone": "季度评审",
                    "nextDate": "6/30",
                    "deviation": 0,
                    "phases": [
                        {
                            "name": "立项", "date": "1/15", "status": "completed", "risk": "none",
                            "objectives": ["维护项目启动", "资源确认", "维护范围界定"],
                            "aiSummary": "立项节点已正常完成，维护项目已启动，资源和范围已确认。",
                            "risks": []
                        },
                        {
                            "name": "结项", "date": "12/31", "status": "pending", "risk": "none",
                            "objectives": ["遗留问题清零", "维护文档完整", "客户满意度达标"],
                            "aiSummary": "维护项目按季度评审节奏正常推进，需持续关注遗留问题清零进度。",
                            "risks": [
                                { "level": "normal", "title": "维护项目正常推进", "rootCause": "立项已完成，按季度评审节奏正常推进", "impact": "暂无影响", "suggestion": "持续关注遗留问题清零进度" }
                            ]
                        }
                    ],
                    "currentPhase": "维护期",
                    "aiSummary": "2026年维护项目整体正常，立项已完成，按季度评审节奏推进。当前处于维护期，无风险信号，按计划推进即可。",
                    "quickQuestions": [
                        "遗留问题清零进展如何？",
                        "季度评审有什么重点？",
                        "维护资源是否充足？",
                        "客户满意度达标情况？"
                    ]
                }
            ],
            "quickQuestions": [
                "V3项目RR准入延期如何补救？",
                "V2项目架构评审何时完成？",
                "MCU盈余人力可否调配到V3项目？",
                "各offering后续关键节点是什么？"
            ]
        },
        "task": {
            "status": "2项滞后",
            "statusType": "yellow",
            "hasAlert": false,
            "text": "任务令达成有风险",
            "aiSummary": "6个任务推进中，2个严重滞后。芯片空闲功耗优化和小区数据提升均延期，建议本周内拉通责任人推进",
            "taskOrders": [
                {
                    "id": "TO-2026-001",
                    "name": "芯片空闲功耗优化",
                    "industry": "无线",
                    "owner": "陈xx",
                    "deadline": "4/10",
                    "progress": 85,
                    "status": "overdue",
                    "risk": "high",
                    "project": "301.0-301.1开发项目",
                    "group": "V3",
                    "phases": [
                        { "name": "方案设计", "status": "completed", "date": "3/15" },
                        { "name": "开发实施", "status": "active", "date": "4/5" },
                        { "name": "验收测试", "status": "pending", "date": "4/10" }
                    ],
                    "risks": [
                        {
                            "level": "high",
                            "title": "开发实施阶段已逾期",
                            "rootCause": "开发实施进度85%，截止4/5已逾期，验收测试尚未启动",
                            "impact": "影响V3项目RR准入节点，可能导致版本发布延期",
                            "suggestion": "建议本周内拉通责任人陈xx，制定追赶计划，评估是否需要增调开发资源"
                        },
                        {
                            "level": "warning",
                            "title": "验收测试资源未确认",
                            "rootCause": "开发延期导致验收测试排期不确定，测试人力可能冲突",
                            "impact": "验收延迟可能影响301.0-301.1项目的整体交付节奏",
                            "suggestion": "建议提前与测试团队沟通，预留验收窗口"
                        }
                    ],
                    "quickQuestions": [
                        "芯片空闲功耗优化逾期的主要原因是什么？",
                        "能否增调开发资源加速追赶？",
                        "验收测试预计何时可以启动？"
                    ]
                },
                {
                    "id": "TO-2026-002",
                    "name": "小区数据提升1.5倍",
                    "industry": "无线",
                    "owner": "王xx",
                    "deadline": "6/30",
                    "progress": 60,
                    "status": "normal",
                    "risk": "medium",
                    "project": "301.0-301.1开发项目",
                    "group": "V3",
                    "phases": [
                        { "name": "需求分析", "status": "completed", "date": "4/15" },
                        { "name": "算法优化", "status": "active", "date": "5/31" },
                        { "name": "集成验证", "status": "pending", "date": "6/30" }
                    ],
                    "risks": [
                        {
                            "level": "warning",
                            "title": "算法优化阶段进展偏慢",
                            "rootCause": "当前进度60%，算法优化仍在进行中，技术方案需反复验证",
                            "impact": "若5月底未完成算法优化，将影响6月集成验证和最终交付",
                            "suggestion": "建议定期跟进王xx的算法验证进展，必要时组织技术评审"
                        }
                    ],
                    "quickQuestions": [
                        "小区数据提升1.5倍的算法方案是否可行？",
                        "算法优化阶段有哪些技术难点？",
                        "集成验证是否需要额外的环境支持？"
                    ]
                },
                {
                    "id": "TO-2026-003",
                    "name": "SIG转发性能优化",
                    "industry": "数通",
                    "owner": "李xx",
                    "deadline": "5/30",
                    "progress": 0,
                    "status": "normal",
                    "risk": "none",
                    "project": "208.11-208.12开发项目",
                    "group": "V2",
                    "phases": [
                        { "name": "性能分析", "status": "pending", "date": "8/15" },
                        { "name": "优化开发", "status": "pending", "date": "10/31" },
                        { "name": "效果验证", "status": "pending", "date": "11/30" }
                    ],
                    "risks": [
                        {
                            "level": "normal",
                            "title": "任务令尚未启动",
                            "rootCause": "当前进度0%，性能分析阶段计划8月启动",
                            "impact": "暂无影响，远期任务按计划推进",
                            "suggestion": "建议提前完成性能基线评估，为8月启动做好准备"
                        }
                    ],
                    "quickQuestions": [
                        "SIG转发性能优化的技术方案是什么？",
                        "性能基线数据是否已收集？",
                        "该任务令与V2项目其他任务的依赖关系？"
                    ]
                },
                {
                    "id": "TO-2026-004",
                    "name": "主力设备商用",
                    "industry": "数通",
                    "owner": "杨xx",
                    "deadline": "7/30",
                    "progress": 0,
                    "status": "normal",
                    "risk": "none",
                    "project": "208.11-208.12开发项目",
                    "group": "V2",
                    "phases": [
                        { "name": "兼容性测试", "status": "pending", "date": "9/30" },
                        { "name": "现场试点", "status": "pending", "date": "11/15" },
                        { "name": "正式商用", "status": "pending", "date": "12/31" }
                    ],
                    "risks": [
                        {
                            "level": "normal",
                            "title": "任务令尚未启动",
                            "rootCause": "当前进度0%，兼容性测试计划9月启动",
                            "impact": "暂无影响，远期任务按计划推进",
                            "suggestion": "建议提前确认测试设备和环境就绪情况"
                        }
                    ],
                    "quickQuestions": [
                        "主力设备商用的兼容性测试范围？",
                        "现场试点的客户和场景是否已确定？",
                        "正式商用的时间节点是否可提前？"
                    ]
                },
                {
                    "id": "TO-2026-005",
                    "name": "启动时间优化",
                    "industry": "MCU",
                    "owner": "张xx",
                    "deadline": "6/15",
                    "progress": 90,
                    "status": "normal",
                    "risk": "none",
                    "project": "1.0-1.1开发项目",
                    "group": "MCU",
                    "phases": [
                        { "name": "启动流程分析", "status": "completed", "date": "4/15" },
                        { "name": "优化实现", "status": "active", "date": "5/31" },
                        { "name": "验证测试", "status": "pending", "date": "6/15" }
                    ],
                    "risks": [
                        {
                            "level": "normal",
                            "title": "推进正常，即将完成",
                            "rootCause": "当前进度90%，优化实现阶段接近完成",
                            "impact": "暂无影响",
                            "suggestion": "保持当前节奏，关注验证测试的启动准备"
                        }
                    ],
                    "quickQuestions": [
                        "启动时间优化的具体效果如何？",
                        "验证测试的计划和用例是否已就绪？",
                        "优化成果如何推广到其他MCU项目？"
                    ]
                },
                {
                    "id": "TO-2026-006",
                    "name": "端到端优化",
                    "industry": "MCU",
                    "owner": "赵xx",
                    "deadline": "9/30",
                    "progress": 25,
                    "status": "normal",
                    "risk": "high",
                    "project": "1.0-1.1开发项目",
                    "group": "MCU",
                    "phases": [
                        { "name": "架构设计", "status": "completed", "date": "5/15" },
                        { "name": "模块开发", "status": "active", "date": "8/31" },
                        { "name": "联调测试", "status": "pending", "date": "9/30" }
                    ],
                    "risks": [
                        {
                            "level": "high",
                            "title": "模块开发进度严重滞后",
                            "rootCause": "当前进度仅25%，架构设计刚完成，模块开发进展缓慢，截止8/31时间紧迫",
                            "impact": "可能影响MCU项目9/30的联调测试和整体交付计划",
                            "suggestion": "建议评估模块开发的人力投入，考虑拆分并行开发以追赶进度"
                        },
                        {
                            "level": "warning",
                            "title": "联调测试时间窗口偏紧",
                            "rootCause": "模块开发延期将压缩联调测试时间，9/30截止日期压力较大",
                            "impact": "若模块开发未能8月底完成，联调测试将延期",
                            "suggestion": "建议提前准备联调环境和测试用例，确保开发完成后可立即进入联调"
                        }
                    ],
                    "quickQuestions": [
                        "端到端优化模块开发进展缓慢的原因？",
                        "能否增加开发人力加速推进？",
                        "联调测试的依赖项有哪些？",
                        "对MCU项目整体里程碑有什么影响？"
                    ]
                }
            ],
            "quickQuestions": [
                "哪些任务令滞后？原因是什么？",
                "需要哪些部门协调？",
                "对项目里程碑有什么影响？"
            ]
        },
        "budget": {
            "status": "偏低",
            "statusType": "yellow",
            "hasAlert": false,
            "text": "部门整体执行率68%（¥5.75M/¥8.5M），低于预期",
            "aiSummary": "4个项目执行率68%，偏差17%。V2和维护项目执行率偏低，需重点关注并催促加快执行",
            "executionRate": 68,
            "executed": 5.75,
            "total": 8.5,
            "warningCount": 2,  // 预警项目数（偏差>10%）
            "projects": [
                {
                    "name": "208.11-208.12开发项目",
                    "group": "V2",
                    "category": "RTOS V2",
                    "budget": 2.5,
                    "executed": 1.7,
                    "rate": 68,
                    "deviation": -15,
                    "status": "在研",
                    "risks": [
                        {
                            "level": "warning",
                            "title": "执行率偏差-15%",
                            "rootCause": "开发人力到位延迟，部分预算未及时使用",
                            "impact": "执行率偏低可能导致年底预算回收",
                            "suggestion": "加快开发进度，追回执行率"
                        }
                    ],
                    "quickQuestions": [
                        "V2项目执行率偏差-15%的根因是什么？",
                        "后续如何追回执行进度？",
                        "年底预算回收风险有多大？"
                    ],
                    "aiSummary": "V2开发项目执行率68%（¥1.7M/¥2.5M），偏差-15%。开发人力到位延迟导致预算使用滞后，存在年底预算回收风险，需加快开发进度追回执行率。"
                },
                {
                    "name": "301.0-301.1开发项目",
                    "group": "V3",
                    "category": "RTOS V3",
                    "budget": 3.0,
                    "executed": 2.55,
                    "rate": 85,
                    "deviation": 5,
                    "status": "在研",
                    "risks": [
                        {
                            "level": "normal",
                            "title": "执行率正常",
                            "rootCause": "项目进度符合预期",
                            "impact": "暂无影响",
                            "suggestion": "保持现状监控"
                        }
                    ],
                    "quickQuestions": [
                        "V3项目费用执行情况如何？",
                        "剩余预算预计何时用完？",
                        "后续有哪些大额支出计划？"
                    ],
                    "aiSummary": "V3开发项目执行率85%（¥2.55M/¥3.0M），偏差+5%。项目进度符合预期，费用执行节奏正常，剩余预算¥0.45M需关注后续大额支出计划。"
                },
                {
                    "name": "1.0-1.1开发项目",
                    "group": "MCU",
                    "category": "RTOS MCU",
                    "budget": 2.0,
                    "executed": 1.9,
                    "rate": 95,
                    "deviation": -3,
                    "status": "在研",
                    "risks": [
                        {
                            "level": "normal",
                            "title": "执行率良好",
                            "rootCause": "项目收尾阶段，执行率符合预期",
                            "impact": "暂无影响",
                            "suggestion": "按计划完成收尾"
                        }
                    ],
                    "quickQuestions": [
                        "MCU项目收尾阶段还有哪些费用支出？",
                        "剩余预算¥0.1M如何规划使用？",
                        "项目结项后预算结余如何处理？"
                    ],
                    "aiSummary": "MCU开发项目执行率95%（¥1.9M/¥2.0M），偏差-3%。项目处于收尾阶段，执行率良好，剩余预算¥0.1M需规划收尾支出。"
                },
                {
                    "name": "2026年维护项目",
                    "group": "V2",
                    "category": "RTOS维护",
                    "budget": 1.0,
                    "executed": 0.65,
                    "rate": 65,
                    "deviation": -12,
                    "status": "维护态",
                    "risks": [
                        {
                            "level": "warning",
                            "title": "执行率偏差-12%",
                            "rootCause": "维护工作需求不饱满，预算使用节奏偏慢",
                            "impact": "执行率偏低可能影响年度预算执行",
                            "suggestion": "评估维护需求，调整预算使用计划"
                        }
                    ],
                    "quickQuestions": [
                        "维护项目预算执行偏慢的原因？",
                        "下半年维护需求预计有多少？",
                        "是否需要调整年度预算计划？"
                    ],
                    "aiSummary": "维护项目执行率65%（¥0.65M/¥1.0M），偏差-12%。维护需求不饱满导致预算使用偏慢，建议评估下半年需求并调整预算使用计划。"
                }
            ],
            "monthlyData": [
                { "month": "1月", "planned": 1.5, "actual": 1.45 },
                { "month": "2月", "planned": 2.0, "actual": 2.1 },
                { "month": "3月", "planned": 2.5, "actual": 1.55 },
                { "month": "4月", "planned": 1.5, "actual": 0 }
            ],
            "quickQuestions": [
                "费用执行率低的主要原因？",
                "哪些项目预算执行滞后？",
                "如何加快执行？",
                "各项目群的费用执行明细？"
            ]
        },
        "ahb": {
            "status": "平衡",
            "statusType": "green",
            "hasAlert": false,
            "text": "部门整体人力与工作量基本持平",
            "aiSummary": "261人月容量，利用率100%，总体分配合理。V3项目存在2人月缺口需关注",

            // 新增：按项目分类聚合（RTOS V2/V3/MCU）
            "categories": {
                "RTOS V2": {
                    "label": "RTOS V2",
                    "workload": 80,
                    "dev": 14,
                    "test": 6,
                    "total": 80,
                    "deviation": 0,
                    "status": "green",
                    "groupCount": 1,
                    "projectCount": 2,
                    "roles": {
                        "dev": { total: 14, internal: 8, od: 2, outsource: 4 },
                        "test": { total: 6, internal: 3, od: 1, outsource: 2 },
                        "pm": { total: 3, internal: 2, od: 1, outsource: 0 }
                    },
                    "risks": [
                        {
                            "level": "normal",
                            "title": "人力与工作量基本持平",
                            "rootCause": "V2项目人力配置与工作量匹配",
                            "impact": "暂无影响",
                            "suggestion": "保持当前人力配置"
                        }
                    ],
                    "aiSummary": "V2项目人力80人月，工作量80人月，人力与工作量基本持平。自有13人、OD4人、外包6人，人员构成合理，当前无需调整。",
                    "quickQuestions": [
                        "V2项目各角色人力分布如何？",
                        "下半年人力需求是否有变化？",
                        "OD和外包人员占比是否合理？"
                    ]
                },
                "RTOS V3": {
                    "label": "RTOS V3",
                    "workload": 120,
                    "dev": 20,
                    "test": 8,
                    "total": 118,
                    "deviation": -2,
                    "status": "green",
                    "groupCount": 1,
                    "projectCount": 2,
                    "roles": {
                        "dev": { total: 20, internal: 12, od: 3, outsource: 5 },
                        "test": { total: 8, internal: 4, od: 2, outsource: 2 },
                        "pm": { total: 4, internal: 3, od: 1, outsource: 0 }
                    },
                    "risks": [
                        {
                            "level": "warning",
                            "title": "人力缺口2人月",
                            "rootCause": "V3项目工作量120人月超过人力配置118人月",
                            "impact": "持续缺口可能导致迭代延期",
                            "suggestion": "建议评估是否需要补充测试或开发人力"
                        }
                    ],
                    "aiSummary": "V3项目人力118人月，工作量120人月，存在2人月缺口。自有19人、OD6人、外包7人，开发人力相对充裕但测试人力偏紧，需关注。",
                    "quickQuestions": [
                        "V3项目人力缺口主要在哪个角色？",
                        "是否有计划补充测试人力？",
                        "当前缺口对迭代进度的影响？"
                    ]
                },
                "RTOS MCU": {
                    "label": "RTOS MCU",
                    "workload": 40,
                    "dev": 6,
                    "test": 4,
                    "total": 42,
                    "deviation": 2,
                    "status": "green",
                    "groupCount": 1,
                    "projectCount": 2,
                    "roles": {
                        "dev": { total: 6, internal: 4, od: 1, outsource: 1 },
                        "test": { total: 4, internal: 2, od: 1, outsource: 1 },
                        "pm": { total: 2, internal: 1, od: 1, outsource: 0 }
                    },
                    "risks": [
                        {
                            "level": "normal",
                            "title": "人力盈余2人月",
                            "rootCause": "MCU项目收尾阶段工作量下降",
                            "impact": "暂无影响",
                            "suggestion": "可考虑将盈余人力调配至V3项目"
                        }
                    ],
                    "aiSummary": "MCU项目人力42人月，工作量40人月，盈余2人月。自有7人、OD3人、外包2人，项目收尾阶段人力有富余，可考虑调配。",
                    "quickQuestions": [
                        "MCU项目盈余人力可否调配到其他项目？",
                        "收尾阶段预计还需多少人力？",
                        "外包人员何时可以释放？"
                    ]
                },
                "维护项目": {
                    "label": "维护项目",
                    "workload": 20,
                    "dev": 4,
                    "test": 2,
                    "total": 21,
                    "deviation": -1,
                    "status": "yellow",
                    "groupCount": 1,
                    "projectCount": 1,
                    "isMaintenance": true,
                    "roles": {
                        "dev": { total: 4, internal: 2, od: 1, outsource: 1 },
                        "test": { total: 2, internal: 1, od: 0, outsource: 1 },
                        "pm": { total: 1, internal: 1, od: 0, outsource: 0 }
                    },
                    "risks": [
                        {
                            "level": "warning",
                            "title": "维护人力缺口1人月",
                            "rootCause": "维护需求波动大，偶发性任务导致工作量超出预期",
                            "impact": "紧急维护任务可能响应不及时",
                            "suggestion": "建议预留弹性人力应对突发维护需求"
                        }
                    ],
                    "aiSummary": "维护项目人力21人月，工作量20人月，基本持平但有1人月缺口。自有4人、OD1人、外包2人，人员偏少，紧急维护响应能力需关注。",
                    "quickQuestions": [
                        "维护项目人力缺口如何补齐？",
                        "突发维护需求的响应机制？",
                        "下半年维护工作量预计变化？"
                    ]
                }
            },
            "quickQuestions": [
                "各项目群的人力分配是否合理？",
                "维护项目突发需求如何应对？",
                "MCU盈余人力可否调配到V3项目？",
                "下季度人力规划如何安排？"
            ]
        },
        "groupsOverview": {
            "projectRisk": {
                // AI一句话总结
                "aiSummary": "V3项目关键风险、TR5节点延误概率>80%；V2项目关注、安全加固进度滞后；MCU项目正常推进",
                // 关键指标（数据驱动）
                "labels": [
                    { "value": "groupCount", "label": "项目群数" },
                    { "value": "criticalCount", "label": "高风险" },
                    { "value": "warningCount", "label": "中风险" },
                    { "value": "normalCount", "label": "正常" }
                ],
                // 关键数据
                "groupCount": 3,
                "criticalCount": 1,
                "warningCount": 1,
                "normalCount": 1,
                // TOP3风险列表
                "risks": [
                    {
                        "level": "critical",
                        "title": "V3项目TR5节点延误",
                        "rootCause": "TR5节点受上游设计变更影响，关键路径延长",
                        "impact": "节点延误概率>80%，影响版本按时发布",
                        "suggestion": "建议尽快协调上游确认设计冻结，评估TR5节点能否分批交付"
                    },
                    {
                        "level": "warning",
                        "title": "V2项目安全加固滞后",
                        "rootCause": "安全加固任务依赖外部资源，进度晚于计划",
                        "impact": "可能导致可信认证延期",
                        "suggestion": "建议增加资源投入，优先保障关键路径任务"
                    },
                    {
                        "level": "normal",
                        "title": "MCU项目正常推进",
                        "rootCause": "MCU版本按计划执行，无重大阻塞",
                        "impact": "暂无风险",
                        "suggestion": "继续保持当前节奏"
                    }
                ],
                "quickQuestions": [
                    "V3项目TR5节点延误概率>80%如何补救？",
                    "V2安全加固进度滞后怎么办？",
                    "当前有哪些高风险项目需要重点关注？",
                    "项目群整体健康状况如何？"
                ]
            },
            "V3": {
                "name": "V3",
                "status": "critical",
                "statusText": "关键",
                "hasAlert": true,
                "targetProject": "301.0-301.1开发项目",
                "projectCount": 2,
                "overallProgress": 53,
                "risks": [
                    {
                        "level": "critical",
                        "title": "TR5节点延误概率>80%",
                        "rootCause": "关键路径滞后2周，影响下游集成",
                        "impact": "可能导致版本延期1个月",
                        "suggestion": "立即协调架构资源，每日跟踪关键任务"
                    },
                    {
                        "level": "warning",
                        "title": "架构人力缺口30%",
                        "rootCause": "核心架构设计任务积压，当前人力无法按期完成",
                        "impact": "影响核心模块设计和评审",
                        "suggestion": "从V2项目组借调2名资深架构师"
                    },
                    {
                        "level": "warning",
                        "title": "可信认证方案未定",
                        "rootCause": "安全审计要求与当前设计冲突，方案评审2次未通过",
                        "impact": "阻塞可信特性交付",
                        "suggestion": "本周内召开技术决策会，明确方案方向"
                    }
                ],
                "quickQuestions": [
                    "V3项目TR5节点延误如何补救？",
                    "架构人力缺口30%如何补充？",
                    "可信认证方案何时能定稿？",
                    "对下游项目的影响有多大？"
                ]
            },
            "V2": {
                "name": "V2",
                "status": "warning",
                "statusText": "关注",
                "hasAlert": false,
                "targetProject": "208.11-208.12开发项目",
                "projectCount": 2,
                "overallProgress": 45,
                "risks": [
                    {
                        "level": "warning",
                        "title": "安全加固进度滞后",
                        "rootCause": "仅完成40%，距节点仅2周",
                        "impact": "可能无法通过安全评审",
                        "suggestion": "加班赶工或申请延期评审"
                    },
                    {
                        "level": "warning",
                        "title": "人力紧张",
                        "rootCause": "3名核心开发人员被抽调支援V3项目",
                        "impact": "影响特性开发进度",
                        "suggestion": "协调人力补充或调整优先级"
                    },
                    {
                        "level": "warning",
                        "title": "需求变更频繁",
                        "rootCause": "新增5个需求变更，2个涉及核心模块",
                        "impact": "影响已完成的测试用例",
                        "suggestion": "本周五召开需求冻结评审会"
                    }
                ],
                "quickQuestions": [
                    "V2安全加固进度滞后如何补救？",
                    "被抽调的人力何时能归还？",
                    "需求变更频繁如何控制？",
                    "对安全评审通过有何影响？"
                ]
            },
            "MCU": {
                "name": "MCU",
                "status": "green",
                "statusText": "正常",
                "hasAlert": false,
                "targetProject": "1.0-1.1开发项目",
                "projectCount": 2,
                "overallProgress": 32,
                "risks": [
                    {
                        "level": "normal",
                        "title": "遗留2个低优先级缺陷",
                        "rootCause": "计划在1.2.0中修复",
                        "impact": "不影响结项评审",
                        "suggestion": "在1.2.0版本规划中安排修复"
                    },
                    {
                        "level": "normal",
                        "title": "ER评审节点临近",
                        "rootCause": "准备工作正常推进",
                        "impact": "当前进度符合预期",
                        "suggestion": "继续跟踪评审材料准备情况"
                    },
                    {
                        "level": "normal",
                        "title": "多版本维护成本",
                        "rootCause": "1.0.0已结项，需持续维护",
                        "impact": "占用维护资源",
                        "suggestion": "评估是否可提前终止维护"
                    }
                ],
                "quickQuestions": [
                    "MCU项目遗留缺陷如何安排修复？",
                    "ER评审节点准备情况如何？",
                    "多版本维护成本如何优化？",
                    "盈余人力是否可调配到其他项目群？"
                ]
            },
            "online": {
                "status": "稳定",
                "statusType": "green",
                "hasAlert": false,
                "aiSummary": "无新增网上问题，运行正常",
                "resolved": 0,
                // 关键指标（数据驱动：labels 定义显示什么，values 取对应的数据字段）
                "labels": [
                    { "value": "yearlyBase", "label": "(2026)" }
                ],
                "yearlyBase": 5,    // 去年累计基线
                "yearlyNew": 1,     // 今年新增
                "monthlyNew": 0,    // 本月新增
                "risks": [
                    {
                        "level": "normal",
                        "title": "网上运行正常",
                        "rootCause": "无新增重大问题",
                        "impact": "各版本运行稳定",
                        "suggestion": "继续保持监控"
                    }
                ],
                "quickQuestions": [
                    "当前网上运行状态如何？",
                    "有无潜在风险？",
                    "近期有哪些变更？"
                ]
            },
            "downstream": {
                "status": "新增2个",
                "statusType": "red",
                "hasAlert": true,
                "aiSummary": "存在2个新增下游问题，集成测试阻塞影响3个项目，需紧急协调",
                "resolved": 0,
                // 关键指标（数据驱动）
                "labels": [
                    { "value": "yearlyBase", "label": "(2026)" },
                    { "value": "monthlyNew", "label": "4月新增" }
                ],
                "yearlyBase": 23,   // 去年累计基线
                "yearlyNew": 5,     // 今年新增
                "monthlyNew": 2,    // 本月新增
                "risks": [
                    {
                        "level": "critical",
                        "title": "下游问题新增",
                        "rootCause": "下游客户反馈接口兼容性问题，影响2个对接项目",
                        "impact": "可能导致客户投诉，影响客户满意度",
                        "suggestion": "建议紧急修复接口兼容性问题，主动沟通客户"
                    }
                ],
                "quickQuestions": [
                    "关键阻塞问题的解决进展如何？",
                    "有哪些依赖需要提前协调？",
                    "是否需要升级到更高层协调？"
                ]
            },
            "trustSummary": {
                "status": "关注",
                "statusType": "yellow",
                "hasAlert": false,
                // 关键指标（数据驱动）
                "labels": [
                    { "value": "overallRate", "label": "达标率" },
                    { "value": "warningCount", "label": "预警项" },
                    { "value": "failCount", "label": "未通过" },
                    { "value": "totalItems", "label": "总项数" }
                ],
                "overallRate": 82,      // 总体达标率
                "warningCount": 3,      // 预警项数（达标率70-85%）
                "failCount": 12,        // 未通过项数
                "totalItems": 45,       // 总评估项数
                // AI一句话总结
                "aiSummary": "V3版本可信达标率85%，V2版本78%需关注，MCU版本92%正常",
                "risks": [
                    {
                        "level": "warning",
                        "title": "V2版本可信达标率偏低",
                        "rootCause": "208.10.0版本设计阶段可信评估未达标，主要涉及安全设计和架构设计",
                        "impact": "可能影响TR4评审通过",
                        "suggestion": "建议本周内完成安全设计评审，补充架构设计文档"
                    }
                ],
                "quickQuestions": [
                    "V2版本可信达标率78%如何提升？",
                    "哪些可信维度未达标？",
                    "V3/MCU版本可信情况如何？",
                    "可信认证对版本发布有何影响？"
                ]
            }
        },
        "quickQuestions": [
            "里程碑节点能如期验收吗？",
            "测试人力如何补充？",
            "下游问题影响多大？",
            "费用执行如何追回？"
        ]
    },
};

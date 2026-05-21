# 开发路线图

路线图可能会经常变更，如果有强烈的建议，可以在 [issue](https://github.com/xerrors/Yuxi/issues) 中提。

日志添加规范（For Agent）:

- 同一版本的多次功能更新时，应以功能为单位进行更新，比如之前添加了 A 功能的更新，在后续的更新中修复了因 A 功能引入的 bug，那么这个修复说明应该和 A 功能描述放在一起，而不是新增一条修复记录，功能更新同理。


### 看板

- Langfuse 增加 self-host 模式支持，补齐私有化部署与配置说明（已支持 cloud，待调试）
- 检索测试中，添加问答
- 集成 Memory，基于 deepagents 的文件后端实现，需要考虑定位
- Yuxi-cli 相关的功能，放在后续版本中实现（不是类似于编程助手，而是管理平台的工，等各个 router 接口优化之后）
- 完善测试基准自动生成功能，目前的实现过于简单，无法覆盖实际需求
- 完善 Skills 的环境变量注入
- 拓宽检索的知识源，统一多知识源（channel），目前已知知识库/知识图谱/网页，可拓展：个人知识库、数据库、历史对话等
    - 前置任务，多知识库并行检索（扩展 query_kb）
    - 新增 query_keywords 工具，专门用于基于关键词命中的排序，也结合词频（和 BM25 的区别？）
- 参考 AgenticRAG 方案扩展当前 Search 工具：基于知识库工具返回的 resource_id/file_id 改进 Search 返回递增文件序列 ID，完善 Find 与 Open 能力；Summary 暂缓
- 评估，基于 Agent 的评估，这里应该是结合 Langfuse 实现

### Bugs
- 目前的知识库的图片存在公开访问风险

### BREAKING CHANGE（不兼容变更，0.7 版本再实现）
- 将自定义provider 的实现逻辑，从文件移动到数据库中，并将相关处理代码，移出 config 文件，放到 provider 模块中
- 已补充方案文档：`docs/vibe/2026-04-18-custom-provider-db-refactor-plan.md`，明确采用“provider 一行、models 放 JSON、移除 provider 默认模型”的落地方案
- 优化知识库的 API 接口设计，使用 /{db_id}/xxx 的形式，整合 mindmap / eval 接口
- 移除 v1 版本的 provider 统一接口，改为 v2 版本的 provider 模块接口



## 版本记录

### 0.6.2 开发记录

<!-- 0.6.2 的内容请放在这里 -->
- 下放扩展管理权限：普通管理员现在可进入扩展管理并完整管理 Tools、MCP、SubAgent、Skills；同步放开 Skill 管理接口权限并补充权限测试。
- 调整 Agent 知识库默认选择：未显式配置知识库时默认启用当前用户可访问的全部知识库，显式保存空列表仍表示不启用知识库。
- 移除知识库沙盒文件系统映射：不再通过 `/home/gem/kbs` 暴露知识库文件树，Agent 继续使用 `query_kb` 与 `open_kb_document` 访问知识库内容。
- 优化评估基准自动生成：仅支持 commonrag/Milvus 知识库，默认参考 chunks 数量改为 1；多 chunk 场景复用知识库向量检索选择相似 chunks，不再对全量 chunks 重新计算 embedding，并移除前端 Embedding 模型选择。
- 修复知识库文档入库状态回退：当已解析文件缺失 `markdown_file` 解析产物时，索引流程会将文件状态恢复为未解析，便于重新解析而不是停留在索引失败。
- 优化 Agent 输入框文件 mention 候选性能并重构为后端异步搜索与二进制极速缓存体系：后端引入 Redis + Rust 驱动的 `ormsgpack` 二进制序列化紧凑 Tuple 缓存，使用 `latin1` 单字节极速字符转换，以规避 BigKey 隐患及 `decode_responses` 解码冲突，实现基于宽度熔断 (500个/目录)、深度保护 (15层) 和黑名单剪枝的异步多线程磁盘安全扫描；提供 `/api/mention/search` 检索接口，实现微秒级内存匹配与防抖/防竞态物理截断；突破性地将 Redis 缓存元组容纳限额从 5,000 条大幅提高到 100,000 条，保证全量物理文件无遗漏扫描装载；同时引入基于匹配位置偏好、前缀/后缀特征加权和长度扣分的 IDE 级模糊匹配平滑打分算法，实现智能降序 of 混合展示，将搜索结果最大上限提至 50，彻底解决同名短文件（如 CSV）、非开头匹配但高相关核心文件被海量测试脚本粗暴截断和挤出名额的痛点。前端删除对巨型 workspace 和 thread 文件数组的全量遍历与合并计算，废弃初始化阶段对整个工作区的深度递归（O(N) -> O(1) 浅探测），解决在超大项目下前端 CPU 冻结与卡顿；采用防抖 (250ms) + `AbortController` 抗竞态多重物理截断请求，配合 6 大核心单元测试 100% 覆盖通过；前端完美接入 100% 防 XSS 且高性能的切片式文本高亮渲染，同时重构 CSS 排版布局，去除两端对齐与右对齐拉伸，令路径信息紧跟在文件名右侧，带来极致、温润的现代微视觉感知交互；**突破性地打通提及列表项“双重安全防护”极客交互优化**：1. **黄金 Range 锁机制**：解决用户在回归聚焦输入框时由于 `ELEMENT_NODE` 索引偏移导致的 `@query` 过滤词清空 Bug，改为基于 DOM 克隆 Range 全局感知字词；同时在打字匹配成功的当下，利用 `TreeWalker` 的全局字符匹配算法 `findNodeAndOffsetAt` 瞬间锁定包含 `@` 符号的具体文本节点与全局 Range 并存入 `mentionTriggerRange` 缓存。2. **零失焦强力捕获与防光标劫持**：将下拉列表项上所有的 `@click` 升级为 `@mousedown.prevent.stop`，在鼠标落下的电光火石之间瞬间截获事件并调用 `deleteContents()` 原地擦除与药丸追加，彻底根绝由于点击弹框导致的任何宿主 Selection 偏转或失焦；在顶层 `focusInput(e)` 中融入对已聚焦状态和输入框内部点击的双重判定，拦截并释放浏览器原生的中间文字定位权利，从根本上解决“想在长句中间点击聚焦以插入补充文字时、光标被粗暴强制劫持拉回至富文本最末尾”的过度设计缺陷，真正兼顾了“空白一键聚焦”与“文字中间精准录入”的双重优良交互品质。3. **点击药丸联动工作台预览**：双向代理检测文件药丸点击动作，配合 Pinia 全局状态信使与 immediate 挂载监听，完美实现了“点击输入框内提及的文件小药丸，即使工作台文件系统正处于关闭状态也能自动联动唤起并直接在右侧工作区加载该文件实时预览”的震撼功能。
- 调整知识库思维导图后端结构：将思维导图路由文件重命名为知识库语义更明确的 router，并把文件列表整理、提示词构建、AI JSON 解析等纯逻辑下沉到知识库 utils。
- 收敛知识库评估后端结构：将评估指标、单题评估、答案生成提示词和自动基准生成算法下沉到 `knowledge/eval`，`EvaluationService` 保留任务、文件和持久化编排职责。
- 新增个人工作区预览与管理：提供独立于对话 thread 的用户级 workspace API，并增加“工作区”页面，用于浏览个人 workspace 文件、预览 Markdown/文本/代码/图片/PDF；支持新建文件夹、上传文件、下载文件、删除文件/文件夹和多选删除；工作区预览支持 Markdown/TXT 在右侧预览框内切换编辑并保存，其他格式和非工作区预览默认只读；知识库与团队空间入口先展示到占位层级；默认创建 `agents/AGENTS.md`，并在 Agent 执行时将其内容追加到系统提示词。
- 加固 JWT 鉴权安全：移除历史默认密钥回退，初始化脚本支持生成并持久化 `JWT_SECRET_KEY` 与 `YUXI_INSTANCE_ID`，签发和验证令牌时校验 `iss/aud`，并在鉴权阶段拒绝已删除或登录锁定用户继续使用旧令牌访问系统。
- 扩展管理界面交互逻辑重构：将 MCP / Subagents / Skills 三个标签页从「左侧边栏 + 右侧详情面板」布局重构为「卡片式网格布局 + 路由跳转二级页面」布局，工具标签页改为卡片网格布局 + 弹窗详情（保持弹窗内容不变）。新增共享组件 `ExtensionCard`、`ExtensionCardGrid`、`ExtensionToolbar`、`ExtensionDetailLayout`，详情页（`McpDetailView`、`SubagentDetailView`、`SkillDetailView`）使用居中宽度限制，路由规划为 `/extensions/mcp/:name`、`/extensions/subagent/:name`、`/extensions/skill/:slug`。
- 统一卡片样式：`ExtensionCard` 新增 `tags` prop 支持传入 `[{label, color}]` 数组，内部使用 `<a-tag bordered=false size=small>` 渲染，与知识库卡片标签风格统一；知识库列表页 `DataBaseView` 改用 `ExtensionCard` + `ExtensionCardGrid` 替代原有自定义卡片，移除冗余 card 样式。
- 调整应用主导航：`AppLayout` 从默认窄栏升级为默认展开的侧边栏，保留折叠态图标导航；侧边栏样式收敛为 14px 文本 + 18px 图标的标准紧凑密度，并统一导航项、任务中心、GitHub、用户信息的图标与文字对齐。折叠态改为仅通过显式按钮展开，避免空白区域误触发。
- 合并智能体对话导航：移除 `AgentChatComponent` 内部聊天侧边栏，将新建对话入口和对话历史移动到 `AppLayout` 主侧边栏，并通过共享线程 store 统一管理历史列表、当前线程、重命名、删除、置顶和分页加载。
- 新增独立模型配置模块：增加 `model_providers` 表、独立管理接口和”模型配置”页面，支持 provider 基础信息、可配置模型列表端点、远端候选模型、`enabled_models` 的早期配置验证；启动时会补齐内置 provider 模板，`provider_type` 暂统一默认为 `openai`，该模块暂不接入现有运行时模型选择逻辑。远端模型加载默认使用 `/models` 获取 chat/通用模型，provider 声明 `embedding` 能力时使用 `/embeddings/models` 获取 embedding 候选，rerank 模型列表端点按供应商文档显式配置后加载；修复路由请求模型未接收 `embedding_base_url`/`rerank_base_url` 导致前端已填写仍被后端校验拦截的问题。补充手动添加模型能力：`enabled_models[i]` 新增可选 `source: "manual"|"remote"` 字段（默认 `remote`），管理员可通过”+ 手动添加”入口录入远端清单未覆盖的模型（典型：自部署 embedding/rerank），手动模型在前端跳过”远端不存在”的 stale 警告并显示「手动」标签；type 选项受 `provider.capabilities` 约束，后端在 `_normalize_payload` 与 `update_provider_config` 双层一致性校验中拦截越权写入。
- 统一前端 Markdown 预览渲染：新增共享 `MarkdownPreview` 组件与 `markdown_preview` 渲染工具，替换 Agent 消息、文件预览、知识库 chunk、任务工具结果、聊天导出等场景中的旧 `md-editor-v3/marked` 预览；支持 KaTeX、任务列表、frontmatter 卡片、Shiki 代码高亮、DOMPurify 清洗和浅层渲染缓存，并抽取 HTML 转义与代码语言归一化工具。Skill 详情页复用 `AgentFilePreview`，统一文件预览、编辑、保存和全屏交互。
- 优化远程 Skill 批量安装：`remote_skill_install_service.py` 新增 `install_remote_skills_batch()`，利用 `npx skills add --skill A --skill B --skill C` 原生多 skill 支持，将安装 N 个 skill 的仓库克隆次数从 2N 降至 1；配套新增路由 `POST /remote/install-batch`、前端 `installRemoteSkillsBatch()` API 方法和批处理 UI 逻辑

---

历史版本发布记录已迁移到 [版本变更记录](./changelog.md)。

维护说明：
- roadmap 仅保留未来规划（看板/Bugs/里程碑方向）。
- 具体版本发布内容统一维护在 changelog。

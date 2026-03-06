# Skills 管理

Skills 管理模块用于集中维护可供 Agent 只读引用的技能包。  
本期采用“文件系统存内容，数据库存索引”模式：

1. 技能目录存储在 `/app/saves/skills`（本地 `save_dir/skills`）。
2. 技能元数据（slug/name/description/dir_path）存储在 `skills` 表。
3. Agent 配置通过 `context.skills` 选择技能，运行时挂载到 `/skills` 且只读。

## 权限与入口

1. 系统设置中新增 `Skills 管理` 页签（仅 `superadmin` 可见）。
2. `admin` 仅可调用列表接口（用于 Agent 配置选择 skills）。
3. `user` 无 skills 管理权限。

## 导入规范（ZIP）

1. 单包单技能，且必须包含一个 `SKILL.md`。
2. `SKILL.md` 必须包含 frontmatter，且 `name`、`description` 必填。
3. `name` 需满足 slug 规则：小写字母/数字/短横线。
4. 导入时执行路径安全校验，拒绝绝对路径与 `..` 路径穿越。
5. slug 冲突时自动追加 `-v2/-v3...`，并自动改写 `SKILL.md` 中 `name` 为最终 slug。
6. 导入采用临时目录 + 原子替换，避免半成品落盘。

## 在线管理能力

1. Skills 列表：来自数据库，避免全量目录扫描。
2. 目录树：按原生目录结构展示。
3. 文件级 CRUD：支持新建文件/目录、编辑文本文件、删除文件/目录。
4. 文件编辑仅允许文本类型（如 md/py/js/ts/json/yaml/toml/txt 等）。
5. `SKILL.md` 保存后会重新解析，并同步更新数据库中的 `name/description`。
6. 支持导出单个 skill 为 ZIP。
7. 删除 skill 时会同时删除目录与数据库记录（硬删除）。

## Agent 运行时行为

1. `context.skills` 用于配置技能 slug 列表。
2. 运行时按会话构建 `SkillResolver` 快照（同一会话首次构建，后续复用）。
3. 运行时仅暴露快照中的可见 skills 到 `/skills/<slug>/...`。
4. `/skills` 路径只读，不允许写入、编辑、上传。
5. 同会话内若 `context.skills` 变化会触发快照重建。
6. 后台修改 skills 内容后，已有会话不会自动刷新，需新会话或调整 `context.skills` 才生效。

## 依赖类型说明

每个 skill 支持三类依赖，均在 Skills 管理页维护：

1. `tool_dependencies`：该 skill 需要的内置工具名列表。
2. `mcp_dependencies`：该 skill 需要的 MCP 服务器名列表。
3. `skill_dependencies`：该 skill 依赖的其他 skill slug 列表。

约束与语义：

1. 依赖在保存时做合法性校验，不允许引用不存在的工具/MCP/skill。
2. `skill_dependencies` 不允许包含自身。
3. `skill_dependencies` 按递归闭包生效，自动去重、去环、保序。

## 渐进式加载流程

系统不会在会话开始时一次性加载全部依赖，而是按阶段渐进加载：

### 阶段 1：会话启动前（构建 skill 可见集）

1. 读取 `context.skills` 作为用户显式选择的 skills（selected）。
2. `SkillResolver` 递归展开 `skill_dependencies`，得到 `visible_skills`（selected + 依赖闭包）。
3. 把快照写入 `runtime.context.skill_session_snapshot`。
4. 基于 `visible_skills` 构建 skills prompt 段，并在 `abefore_agent` 预拼接到 `system_prompt`。
5. `/skills` 只挂载 `visible_skills`，所以被依赖 skill 从会话首轮起即可被读取。

结论：`skill_dependencies` 是“会话启动即生效”的。

### 阶段 2：技能激活时（按需激活）

1. Agent 通过 `read_file` 读取 `/skills/<slug>/SKILL.md` 时，视为激活该 skill。
2. 仅当 `<slug>` 在 `skill_session_snapshot.visible_skills` 内，激活才被接受。
3. 激活结果写入 `activated_skills`（去重保序）。

结论：只有“真正被读取并使用”的 skill 才会进入后续依赖注入计算。

### 阶段 3：后续模型轮次（注入工具与 MCP 依赖）

1. 在 `awrap_model_call` 中，基于 `activated_skills` 计算依赖闭包。
2. 聚合闭包内 skill 的 `tool_dependencies` 与 `mcp_dependencies`。
3. 仅把这些依赖工具/MCP 合并进本轮可用工具集。

结论：`tool_dependencies` 与 `mcp_dependencies` 是“激活后按需加载”的，不会在会话首轮全量注入。

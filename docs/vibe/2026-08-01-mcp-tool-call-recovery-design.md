# MCP 工具调用断线恢复设计

> 日期：2026-08-01
> 状态：评审修订稿
> 主题：修复 MCP Server 重启或连接中断时，在途工具调用异常穿透并终止整个聊天流的问题

## 1. 结论摘要

当前 Yuxi 已经具备 MCP Session 后台重连框架，但连续重连存在缺陷，并且没有对已经失败的 `call_tool` 做恢复处理。

当 MCP Server 在工具调用过程中重启时：

1. 已经发出的工具调用仍等待旧 Session 的 response stream。
2. MCP Server 重启或传输中断后，旧 stream 关闭，调用可能先收到 `EndOfStream`、`ClosedResourceError` 或 `BrokenResourceError`。
3. 当前工具调用不会据此通知 `LongLivedSession`；后台循环只能等待传输上下文自行退出或下一次 ping 失败，最迟可能等待 30 秒。
4. 异常未经 MCP 工具边界转换，穿透 LangChain Tool 和 LangGraph ToolNode，最终终止聊天流。
5. `LongLivedSession` 即使随后检测到断线并建立新 Session，也只能提供新的调用通道，不能恢复已经失败的旧 request；安全工具必须在新 Session 上重新发送一次。

推荐方案是在 `langchain-mcp-adapters` 提供的 `tool_interceptors` 扩展点实现 MCP 专用调用恢复拦截器，修复 `LongLivedSession` 的连续重连循环，并让 `_SessionProxy` 同时提供代次感知的连接等待和主动重连请求能力。

确定的恢复策略为：

- 调用前 Session 已不可用：请求尚未发送，恢复拦截器请求当前 `LongLivedSession` 重连并等待下一代 Session，随后正常发送一次。
- 调用过程中断线：恢复拦截器先对发生错误的 generation 发出幂等 `request_reconnect()`，确保后台循环立即离开旧 Session，而不是等待最长 30 秒的下一次 ping。
- 工具声明 `readOnlyHint=true` 或 `idempotentHint=true`：等待当前连接条目的 generation 增加，随后只重试 MCP Adapter 内层 handler 一次。
- 工具未声明只读或幂等：不自动重试，但仍请求后台重建已损坏 Session，然后返回“执行结果未知”的 Tool 错误。
- `LongLivedSession` 是创建和重建 ClientSession 的唯一所有者；恢复拦截器只发出重连请求并等待状态变化，不并行创建第二条连接。
- `RuntimeConfigMiddleware.awrap_tool_call()` 继续只负责动态 Tool 注入和 `AuthContext` 生命周期；它不创建 Session，也不重复调用外层 LangChain handler。
- 工具调用最多等待重连 5 秒，可通过环境变量调整；等待超时只结束本次工具恢复，不停止后台重连。
- 预期连接错误必须转换为 Tool 错误，让聊天继续，不再直接终止消息流。
- 不修改 MCP SDK、LangChain MCP Adapter、数据库或前端。

## 2. 目标与验收标准

### 2.1 目标

- MCP Server 短暂重启后，连接池继续自动恢复 Session。
- 初次连接成功后，即使连续多次重连失败，后台循环也持续运行，直到成功或收到停止指令。
- 临时断线期间，同一配置的连接池条目和 `_SessionProxy` 保持不变，不产生并行重连任务。
- 工具调用发现连接关闭时，能够立即唤醒同一 `LongLivedSession` 的重连循环，不依赖 30 秒 ping 周期。
- 下一轮 Agent 重新加载工具时，不会因为 Session 正在重连或等待超时而停止并淘汰该 `LongLivedSession`。
- 连接恢复重试发生在 MCP Adapter 内层，不重复执行 Agent 的其他 `awrap_tool_call` 中间件。
- 安全工具在连接恢复后自动重试一次。
- 未声明安全语义的工具不被自动重放。
- 预期的 MCP 连接关闭不再中止整个聊天流。
- 错误信息明确说明请求是否可能已经执行。
- Token 提前刷新、401 刷新和权限隔离行为保持不变。
- HTTP、SSE、Streamable HTTP 和 Stdio MCP 的正常调用不受影响。

### 2.2 验收清单

- [ ] 调用前 Session 已断开时，系统等待重连并且只发送一次请求。
- [ ] 初次连接失败时启动明确失败，不发布无效连接池条目。
- [ ] 初次连接曾成功后，连续重连失败不会使 `_run_loop` 退出。
- [ ] 临时断线期间再次获取相同连接时，不淘汰正在重连的 `LongLivedSession`。
- [ ] 工具加载等待重连超时或 `list_tools` 遇到连接关闭时，不停止仍在运行的 Session 所有者。
- [ ] 5 秒工具等待超时后，后台重连仍然继续。
- [ ] `ClosedResourceError` 到达 MCP Adapter interceptor 后，对旧 generation 发出一次幂等重连请求。
- [ ] 重连请求能立即唤醒 `_run_loop`，不等待下一次 Session ping。
- [ ] 同一 generation 的并发错误只触发一次重连过程。
- [ ] 一次 Agent 工具调用中，外层 `awrap_tool_call` handler 只执行一次，MCP Adapter handler 最多执行两次。
- [ ] 预期连接关闭异常被 Adapter interceptor 消化，不再冒泡到 `RuntimeConfigMiddleware.awrap_tool_call()`。
- [ ] `readOnlyHint=true` 的工具断线后最多自动重试一次。
- [ ] `idempotentHint=true` 的工具断线后最多自动重试一次。
- [ ] 未标注工具断线后不自动重试。
- [ ] 未标注工具返回“执行结果未知”的 Tool 错误，聊天流继续。
- [ ] 5 秒内未重连时返回明确 Tool 错误，聊天流继续。
- [ ] 重连后的第二次调用仍失败时不进行第三次调用。
- [ ] `EndOfStream`、`ClosedResourceError` 和 `BrokenResourceError` 得到一致处理。
- [ ] 普通业务错误、参数错误和代码错误不会被错误归类为连接中断。
- [ ] Token、请求头和工具参数不会写入恢复日志。
- [ ] `manual_mcp_13_token_pre_refresh` 行为保持不变。
- [ ] 401 Token 刷新重试行为保持不变。
- [ ] 真实 Demo Server 重启场景通过集成测试和 E2E。

## 3. 当前实现与根因

### 3.1 已有后台重连框架

`backend/package/yuxi/agents/mcp/client_pool.py` 中的 `LongLivedSession` 已经负责：

- 长期维护 MCP ClientSession。
- 使用 `_SessionProxy` 将工具闭包指向当前 Session。
- 设计上在连接断开后按 1 秒起始、最大 30 秒的指数退避重连。
- 重连后将代理切换到新 Session。
- 通过 ping 检测空闲连接是否仍然有效。

`MultiServerMCPClient.session(server_name)` 会主动创建连接并执行 `initialize()`；成功返回后，`LongLivedSession` 才通过 `_SessionProxy.set_session()` 发布该 Session。因此，主动创建新 Session 的职责属于 `LongLivedSession._run_loop()`，不是等待中的工具调用。

现有重连框架可以保留，但必须修复下面的连续重连缺陷。

### 3.2 首次重连失败后循环退出的缺陷

当前 `_run_loop()` 在异常分支使用 `_SessionProxy.is_connected` 判断是否属于首次连接失败：

```python
if not self._session_proxy.is_connected:
    logger.warning("Failed to start MCP session ...")
    break
```

旧 Session 断开后，代理会被设置为不可用。若第一次重连尝试在新 Session 发布前失败，`is_connected` 仍为 `False`，上述判断会把它误认为“首次启动失败”并退出后台循环。

此时连接池中仍可能保留这个已经停止的 `LongLivedSession`。未来一次 `get_session()` 可能将其淘汰并创建新条目，但当前工具恢复拦截器等待的是旧 `_SessionProxy`，不会被新条目唤醒。因此单纯增加 `wait_for_session()` 不足以保证恢复。

必须同时保证：

- 使用现有 `first_connect` 状态区分“从未成功连接”和“已连接过、正在重连”。
- 从未成功连接时，连接失败继续按当前行为使 `start()` 失败，连接池不发布条目。
- 只要至少成功连接过一次，后续连接尝试失败就继续退避重试，不能因为代理暂时不可用而退出。
- 同一 cache key 和配置 hash 的 `LongLivedSession` 正在重连时，连接池不得仅因 `is_connected=False` 将其淘汰。
- 重连任务只在收到 `stop`、配置被替换、连接被明确移除或连接池关闭时结束。

此外，当前 `tool_registry_service.get_mcp_tools()` 的异常分支会调用 `mcp_client_pool.remove_session()`，连接类异常还会继续执行 `remove_sessions_by_server()`。如果下一轮 `awrap_model_call()` 恰好在后台重连窗口重新加载工具，这个清理逻辑会停止唯一的 `LongLivedSession`，使旧 Tool 捕获的 `_SessionProxy` 永远等不到新 generation。实现必须把“仍在后台恢复”与“条目已经失效”分开处理。

### 3.3 LangChain 与 Agent 的真实工具调用链

MCP Tool 不是由 `RuntimeConfigMiddleware.awrap_tool_call()` 直接调用 ClientSession。当前 LangChain 1.x 的实际链路分为工具加载和工具执行两个阶段。

工具加载阶段：

```text
ChatbotAgent / DeepAgent 构建或执行模型调用
    ↓
RuntimeConfigMiddleware.awrap_model_call()
    ↓
get_tools_from_context()
    ↓
get_enabled_mcp_tools()
    ↓
get_mcp_tools()
    ↓
MCPClientPool.get_session()
    ↓
LongLivedSession.start() / _run_loop()
    ↓
MultiServerMCPClient.session() 创建连接并 initialize()
    ↓
load_mcp_tools(_SessionProxy, tool_interceptors=[...])
    ↓
生成捕获该 _SessionProxy 的 LangChain StructuredTool
```

工具执行阶段：

```text
Agent 模型输出 tool_call
    ↓
LangGraph ToolNode._arun_one()
    ↓
组合后的 AgentMiddleware.awrap_tool_call 链
    ↓
RuntimeConfigMiddleware.awrap_tool_call()
    ↓
SkillsMiddleware.awrap_tool_call() 等后续中间件
    ↓
ToolNode._execute_tool_async()
    ↓
StructuredTool.ainvoke() / BaseTool.arun()
    ↓
langchain-mcp-adapters 生成的 call_tool coroutine
    ↓
MCPToolCallRecoveryInterceptor
    ↓
_SessionProxy.call_tool
    ↓
当前 ClientSession.call_tool
```

`RuntimeConfigMiddleware.awrap_tool_call()` 当前只负责：

- 当 ToolNode 未注册运行时 MCP Tool 时，从上一轮 `awrap_model_call()` 保存的动态工具映射中注入正确 Tool。
- 在 `await handler(request)` 整个期间设置当前用户的 `AuthContext`。

它不捕获连接异常，也没有当前连接 partition、generation 或 `LongLivedSession` 的完整控制信息。现在 `ClosedResourceError` 会从 `await handler(request)` 向外冒泡；ToolNode 默认错误处理只将参数调用错误转成 ToolMessage，普通工具执行异常仍会重新抛出，因此聊天流终止。

这里存在两个名称相同但边界不同的 handler：

- Agent Middleware handler：继续执行后续中间件和完整 `StructuredTool.ainvoke()`；重复调用会重复整个 LangChain 工具执行链。
- MCP Adapter interceptor handler：只执行一次底层 MCP `ClientSession.call_tool()`；重复调用只重放远端 MCP 请求。

恢复逻辑必须只重试 MCP Adapter handler。外层 `RuntimeConfigMiddleware.awrap_tool_call()` handler 在一次 Agent 工具调用中只执行一次，并持续保持 `AuthContext`，直到内部恢复、重试或错误 ToolMessage 返回。

这里能在新 Session 上重试的关键，是 `load_mcp_tools(session=_SessionProxy, ...)` 生成 `StructuredTool` 时，Adapter 的 `execute_tool` 闭包捕获的是 `_SessionProxy`，不是当时那一个具体 `ClientSession`。第一次 Adapter handler 调用通过代理访问旧 Session；`LongLivedSession` 发布新 Session 后，第二次调用同一个 Adapter handler 会再次执行 `await session.call_tool(...)`，此时代理自然转发到新 Session。因此不需要重建 Tool，也不需要重新进入 ToolNode 或 Agent Middleware。

### 3.4 在途调用无法迁移

MCP `tools/call` 是带 request ID 的请求响应过程。已经发送的请求与 response stream 属于旧 Session。旧连接退出后，该请求不能迁移到新 Session，也不能从新 Session 继续等待旧响应。

因此，“在途调用仍绑定旧 Session”属于协议和连接生命周期的固有限制，不是代码缺陷。

### 3.5 聊天流被终止的根因

Yuxi 当前把 MCP 工具设置为 `handle_tool_error=True`，但 LangChain 只会据此处理 `ToolException`，不会处理任意传输异常。

当前异常传播路径为：

```text
MCP Server 重启
    ↓
旧 response stream 关闭
    ↓
MCP SDK send_request 抛出流关闭异常
    ↓
langchain-mcp-adapters 重新抛出异常
    ↓
StructuredTool 重新抛出普通 Exception
    ↓
SkillsMiddleware.awrap_tool_call 等内层 Agent Middleware 重新抛出
    ↓
RuntimeConfigMiddleware.awrap_tool_call 在 finally 中重置 AuthContext 后重新抛出
    ↓
ToolNode 默认处理器重新抛出
    ↓
LangGraph stream 终止
    ↓
chat_service 记录 Error streaming messages
```

因此真正需要修复的是：MCP 工具边界没有将预期的连接关闭异常转换成可由 Agent 消费的 Tool 错误。

### 3.6 `ClosedResourceError` 的两种来源

第一种是调用前错误：

- `_SessionProxy` 已经没有 Session。
- 新工具调用访问代理方法。
- `_SessionProxy.__getattr__()` 直接抛出 `ClosedResourceError`。
- 请求确定没有发送到 MCP Server。

第二种是在途调用错误：

- 请求已经发送并等待 response stream。
- MCP Server 或传输层先关闭 response stream，工具调用直接收到连接异常；或者恢复拦截器请求重连后，`LongLivedSession` 主动关闭旧 Session 的 pending streams。
- 根据关闭时机，AnyIO 可能抛出 `EndOfStream`、`ClosedResourceError` 或 `BrokenResourceError`。
- 请求是否已经在服务端产生副作用无法确定。

现有代码注释把关闭 pending streams 的结果写死为 `ClosedResourceError`，并不准确。实现时应改为“快速收到流关闭异常”。

## 4. 方案比较

### 4.1 方案 A：MCP Tool Interceptor + Session 代次 + 单一重连所有者

这是推荐方案。

通过 `langchain-mcp-adapters` 的公开 `tool_interceptors` 扩展点包围每次 MCP 工具调用。拦截器负责：

- 判断调用前是否已有可用 Session。
- 记录调用开始时的 Session generation。
- 捕获明确的连接关闭异常。
- 对发生错误的 generation 调用幂等 `request_reconnect()`，主动唤醒 Session 所有者。
- 依据 MCP ToolAnnotations 判断是否允许重试。
- 等待 generation 增加后，只调用 MCP Adapter handler 重试一次。
- 将无法恢复的连接错误转换为标准 MCP `CallToolResult(isError=True)`。

优点：

- 恢复逻辑只作用于 MCP 工具。
- 使用第三方包的正式扩展点，不需要 fork 或 monkey patch。
- 可以直接调用 Adapter 内层 handler 完成重试，不重复执行 LangChain Agent 中间件。
- 返回标准 MCP 错误后，可复用现有 `handle_tool_error=True` 行为。
- 不把 MCP 传输细节扩散到通用 Agent 中间件。

缺点：

- `LongLivedSession` 需要修复首次重连失败后退出的问题。
- `LongLivedSession` 需要新增可唤醒 keepalive 的重连事件。
- `MCPClientPool` 需要在临时断线期间保留正在重连的连接条目。
- `_SessionProxy` 需要新增 generation、重连请求和重连等待接口。
- 拦截器需要在工具加载后获得工具注解策略。

### 4.2 方案 B：在 RuntimeConfigMiddleware 捕获并重试

`RuntimeConfigMiddleware.awrap_tool_call()` 可以读取 LangChain Tool metadata，也能捕获工具异常。

优点：

- 可以直接判断工具注解。
- LangChain 明确允许 `awrap_tool_call` handler 被调用多次，可以实现整个 Tool 的重试。

缺点：

- Middleware 无法自然获得当前 Tool 捕获的具体 `_SessionProxy`、partition、generation 和 `LongLivedSession` 所有者。
- 通过 `get_enabled_mcp_tools()` 重新加载可能命中 Tool 缓存，或者创建绑定新代理的新 Tool；当前 ToolNode 仍可能持有旧 Tool 和旧代理。
- 再次调用 Agent handler 会重复执行后续 `awrap_tool_call` 中间件和完整 `StructuredTool.ainvoke()`，恢复边界大于实际需要。
- 容易把通用运行时配置职责和 MCP 传输恢复混在一起。
- 即使固定 sleep 后再次调用，也可能再次命中旧 Session，无法证明已经切换 generation。

不采用该方案。

### 4.3 方案 C：全局捕获 ToolNode 异常

通过 LangGraph ToolNode 的通用异常处理，把所有工具异常转换成 ToolMessage。

优点：

- 可以快速避免聊天流终止。

缺点：

- 会影响内置工具、知识库工具、Skills 等非 MCP 工具。
- 可能掩盖真实程序错误。
- 无法可靠等待 MCP Session 重连。
- 无法安全判断是否允许重试。

不采用该方案。

### 4.4 不修改第三方包

当前运行容器已经确认以下版本与行为：

- LangChain `1.2.14`。
- LangGraph `1.1.4`。
- `langchain-mcp-adapters 0.2.2`。
- MCP SDK `1.27.0`。

- MCP SDK 的 `ClientSession.call_tool()` 只调用一次 `send_request()`，没有调用级重试。
- `langchain-mcp-adapters` 直接调用 `session.call_tool()`，异常会向上抛出。
- Adapter 已明确提供 `tool_interceptors` 用于重试和错误处理。
- Adapter interceptor handler 可以被调用多次，而 LangChain Agent Middleware handler 位于它的外层。
- `BaseTool.handle_tool_error=True` 只处理 `ToolException`；普通 `ClosedResourceError` 不会被该配置转换。
- ToolNode 默认错误处理只消费工具参数调用错误，普通工具执行异常仍会重新抛出。

重试策略需要知道服务是否可信、工具是否允许重复执行，属于 Yuxi 应用侧责任，不应修改或 fork 第三方包。

## 5. 推荐架构

```mermaid
sequenceDiagram
    autonumber
    participant Agent
    participant ToolNode
    participant AWrap as RuntimeConfigMiddleware.awrap_tool_call
    participant Tool as StructuredTool / BaseTool
    participant Interceptor as MCPToolCallRecoveryInterceptor
    participant Proxy as _SessionProxy
    participant Owner as LongLivedSession._run_loop
    participant Session as ClientSession / MCP transport

    Agent->>ToolNode: 模型输出 tool_call
    ToolNode->>AWrap: 进入 Agent Middleware handler
    AWrap->>Tool: handler(request)，外层只调用一次
    Tool->>Interceptor: Adapter handler
    Interceptor->>Proxy: 记录 generation 并调用 call_tool
    Proxy->>Session: 使用旧 ClientSession
    Session--x Interceptor: ClosedResourceError 等连接异常
    Interceptor->>Proxy: request_reconnect(expected_generation)
    Proxy->>Owner: 幂等设置 reconnect event

    alt readOnlyHint 或 idempotentHint
        Owner->>Owner: 立即唤醒 keepalive，记录重连原因
        Owner->>Session: 关闭旧 Session 和 pending streams
        Owner->>Owner: 等待可被 stop 中断的首次退避 1 秒
        Owner->>Session: client.session(auto_initialize=True)
        Session-->>Owner: 新 ClientSession
        Owner->>Proxy: set_session()，generation 加一
        Proxy-->>Interceptor: 唤醒 generation 等待者
        Interceptor->>Proxy: Adapter handler 只重试一次
        Proxy->>Session: 使用新 ClientSession.call_tool
        Session-->>Interceptor: 工具结果
    else 未声明安全语义
        Interceptor-->>Tool: CallToolResult(isError=True)，不重试
        Note over Owner,Session: 后台仍由同一 reconnect event 驱动重建，不阻塞本次 Tool 返回
    end

    Tool-->>AWrap: ToolMessage 或正常结果
    AWrap-->>ToolNode: 重置 AuthContext 后返回
```

`ClosedResourceError` 的捕获点位于 LangChain `StructuredTool` 内部，因此仍处于 `RuntimeConfigMiddleware.awrap_tool_call()` 的 `await handler(request)` 之内。恢复成功时，异常不会到达外层 Middleware；无法恢复时，Adapter 将标准 MCP 错误转换为 `ToolException`，再由 `BaseTool.handle_tool_error=True` 生成错误 ToolMessage。

恢复拦截器不直接调用 `client.session()`。它通过 `_SessionProxy.request_reconnect(expected_generation)` 主动唤醒唯一的 Session 所有者；只有 `LongLivedSession._run_loop()` 可以关闭旧 Session，并重新进入 `MultiServerMCPClient.session(server_name)`。该上下文管理器默认使用 `auto_initialize=True`，内部创建传输与 `ClientSession` 后自动执行 `initialize()`。这样既不是纯被动等待，也不会从工具调用任务并行创建第二条连接。

### 5.1 组件职责

#### `_SessionProxy`

继续负责将工具闭包委托到当前 Session，并新增：

- `generation`：成功绑定新 Session 时递增。
- 连接可用事件：有 Session 时置位，无 Session 时清除。
- `request_reconnect(expected_generation)`：将重连请求委托给所属 `LongLivedSession`；返回 `accepted`、`merged`、`stale_generation` 或 `stopped`。
- `wait_for_session()`：调用前没有 Session 时，等待当前连接条目重新绑定可用 Session。
- `wait_for_new_session(after_generation)`：在途调用断线后，只等待当前连接条目绑定 generation 更大的 Session。

`_SessionProxy` 不创建 ClientSession、不调用连接池，也不启动第二个重连任务。`request_reconnect()` 只通过绑定回调唤醒唯一所有者：

- `accepted`：当前 generation 匹配，首次设置重连事件。
- `merged`：同一 generation 已有重连请求，当前请求合并等待。
- `stale_generation`：generation 已变化，说明其他调用已经完成重连，不再断开新 Session。
- `stopped`：后台所有者已停止，当前 Tool 不再无意义等待；返回连接不可用错误，由后续工具加载重新创建连接池条目。

幂等判断不能只依赖 `_reconnect_event.is_set()`。`_run_loop()` 消费事件后会清除 Event，但新 Session 尚未发布前，后到的同 generation 错误仍必须返回 `merged`。因此 `LongLivedSession` 还需保存 `_reconnect_generation`，表示当前正在恢复哪一代 Session：

- 首次接受 generation N 的主动请求时记录 N 并设置 Event。
- ping 失败或传输上下文自然退出时，也记录正在恢复 generation N。
- `_run_loop()` 消费 Event 后可以清除 Event，但在新 Session 发布前继续保留 N。
- generation N+1 发布后清除旧请求记录。
- 此后迟到的 generation N 请求通过 generation 比较返回 `stale_generation`，不会让刚建立的新 Session 再次断开。

断开顺序调整为：

1. 保存旧 Session 引用。
2. 立即把代理标记为不可用并清除连接事件。
3. 关闭旧 Session 的 pending response streams。

这样可以避免旧流关闭期间的新调用继续进入旧 Session。

#### `LongLivedSession`

作为 ClientSession 创建和重建的唯一所有者，修复现有重连循环并保留退避策略：

- 新增 `_reconnect_event`，由 `_SessionProxy.request_reconnect()` 幂等触发。
- 新增 `_reconnect_generation`，统一标识主动请求、ping 失败或传输退出正在恢复的 generation；在 Event 已被消费但新 Session 尚未发布的窗口内继续合并同 generation 请求。
- `request_reconnect()` 在同一事件循环内完成 generation、运行状态、已请求 generation 和 event 状态判断，中间不执行 await，保证检查与置位之间没有任务切换。
- 扩展现有 keepalive 等待，使其同时响应 stop、主动 reconnect 和定时 ping，而不是只等待 stop 或最长 30 秒的 ping 周期。
- 收到主动 reconnect 后，立即将代理标记为不可用、关闭旧 pending streams、退出旧 Session 上下文，然后进入统一退避重连路径。
- 使用 `first_connect` 判断是否从未成功建立 Session。
- 首次启动连接失败时终止 `start()`，保持当前快速暴露配置或鉴权错误的行为。
- 首次连接成功后，即使后续多次连接失败，也持续按指数退避重试，直到连接成功或收到停止指令。
- 重连尝试失败时不得因为 `_SessionProxy.is_connected=False` 退出循环。
- 任意时刻同一个 `LongLivedSession` 最多只有一个 `_run_loop` 和一个连接尝试。
- 传输层自然退出、ping 失败和主动 reconnect 请求最终进入同一重连分支，避免维护三套 Session 创建逻辑。

“立即唤醒”指立即开始恢复流程，不是绕过既有退避并同步创建连接。主动请求被消费后先关闭旧 Session，再执行当前 1 秒起始的退避；若建立失败，继续按 2、4、8 秒增长，最大 30 秒。退避等待可被 `stop` 中断。

每次新 ClientSession 完成 initialize 后，通过 `_SessionProxy.set_session()`：

- 绑定新 Session。
- generation 加一。
- 唤醒全部重连等待者。

不修改当前 1 秒起始、最大 30 秒的指数退避参数。工具调用的 5 秒等待不会取消或停止这个后台循环。

#### `MCPClientPool`

临时断线期间必须保持连接条目稳定：

- cache key 和配置 hash 相同，且 `LongLivedSession` 的后台循环仍在运行时，不因代理暂时不可用而淘汰该条目。
- 需要获取 Session 的并发调用等待同一个 `_SessionProxy` 恢复，而不是创建新的 `LongLivedSession`；该等待复用 `YUXI_MCP_TOOL_RECONNECT_WAIT_SECONDS`，不新增第二个超时配置。
- `_dict_lock` 只用于确认和保留连接池条目，实际等待必须在锁外进行，避免一个 MCP Server 的重连阻塞其他连接池操作。
- 等待超时可以让当前获取操作失败，但不能停止或替换仍在后台重连的条目。
- 只有配置变化、显式 remove、后台任务已经退出或连接池关闭时才淘汰条目。

`get_session()` 需要区分“所有者已经停止”和“所有者仍在重连”：

- 已连接：立即返回原 `_SessionProxy`。
- 未连接但后台仍运行：在 `_dict_lock` 外等待原代理恢复。
- 等待超时：抛出专用的 `MCPConnectionRecoveringError`，表示本次获取失败但后台所有者仍有效。
- 后台已经退出：才淘汰旧条目并按现有流程创建新的 `LongLivedSession`。

该约束是 generation 等待能够可靠唤醒的必要条件：如果连接池在断线窗口创建新条目，旧工具闭包仍绑定旧代理，永远看不到新条目的 generation。

#### `MCPToolCallRecoveryInterceptor`

放在 MCP 连接池模块内，与 Session 生命周期和传输异常保持同一职责边界。

拦截器持有：

- 绑定了所属 `LongLivedSession` 重连回调的 `_SessionProxy`。
- 工具名称到安全重试标记的映射。
- 最大重连等待秒数。

执行流程：

1. 调用 Adapter handler 前读取连接状态和 generation。
2. 如果调用前已经没有 Session，请求确定尚未发送：调用 `request_reconnect(generation)`；`accepted` 或 `merged` 时等待可用 Session，`stale_generation` 表示新 Session 已经发布，`stopped` 立即返回错误。
3. Session 可用后重新读取并记录 `call_generation`，然后调用 Adapter handler。这是本次请求第一次真正发送，不受工具注解限制。
4. 第一次真正发送若捕获明确连接异常，无论工具是否允许重试，都先调用 `request_reconnect(call_generation)` 修复连接状态。
5. 未标注工具直接返回“执行结果未知”的标准 MCP 错误，不等待、不重放。
6. 只读或幂等工具在 `accepted` 或 `merged` 时等待 `generation > call_generation`；`stale_generation` 不再等待；随后调用 Adapter handler 重试一次。
7. 第二次 Adapter handler 若再次发生连接异常，先对新的 generation 请求后台重连，再转换为 Tool 错误；不发起第三次工具调用。

`stale_generation` 只表示“不需要再次触发或等待重连”。它不改变重试资格：未标注工具仍然不重放；只有调用前确定尚未发送，或第一次真正发送失败且工具声明只读/幂等时，才会继续调用 Adapter handler。

如果预检查时 Session 可用，但在进入 `ClientSession.call_tool()` 前发生竞态断线，仍按“请求可能已经发送”保守处理，不根据空字符串异常或时序猜测请求未发送。

拦截器不调用 `client.session()`，不重新调用 Agent Middleware handler，不创建或替换连接池条目，也不保存用户身份、Token、请求头或工具参数。

#### `RuntimeConfigMiddleware.awrap_tool_call`

生产逻辑保持不变：

- 继续注入上一轮 `awrap_model_call()` 选择的运行时 MCP Tool。
- 继续在一次外层 `handler(request)` 执行期间设置并最终重置 `AuthContext`。
- 不捕获 MCP 传输异常，不调用连接池，不负责 Session 重建。

Adapter interceptor 的原始调用和一次安全重试都发生在同一个外层 `await handler(request)` 内，因此不会重复执行 Skills 等 Agent Middleware，也不会提前重置 `AuthContext`。

#### `tool_registry_service`

加载工具时：

1. 创建共享的工具安全策略映射。
2. 创建绑定当前 `_SessionProxy` 的恢复拦截器；该代理已经持有所属 `LongLivedSession` 的重连回调。
3. 调用 `load_mcp_tools(..., tool_interceptors=[interceptor])`。
4. 根据返回 LangChain Tool 的 metadata 填充安全策略映射。
5. 继续添加现有 `id`、`mcp_server_name` 和 `handle_tool_error=True`。

工具只会在加载完成并返回 Agent 后执行，因此在工具调用发生前，安全策略映射已经完整。

工具加载异常处理也必须服从“单一 Session 所有者”原则：

- 捕获 `MCPConnectionRecoveringError` 时，本轮返回空工具列表，但不进入故障冷却、不调用 `remove_session()`，后台重连继续。
- `load_mcp_tools()` 的 `list_tools` 遇到明确连接关闭时，通过当前 `_SessionProxy.request_reconnect()` 唤醒所有者。返回 `accepted`、`merged` 或 `stale_generation` 时只清理当前 Tool 对象缓存，不停止 `LongLivedSession`；只有返回 `stopped` 时才允许移除失效条目。
- 普通配置、鉴权、协议或程序错误保持现有失败冷却和清理行为。
- 只有连接池确认所有者已停止、配置已变化或条目已失效时，才允许移除 Session。

这一步不是额外的工具加载重试。当前模型调用最多等待一次已有后台重连；超时后本轮不加载该 MCP Tool，下一轮模型调用再按正常流程获取。这样可以避免 Agent 返回错误 ToolMessage 后的下一次 `awrap_model_call()` 反过来杀死正在恢复的 Session。

### 5.2 精确控制流

下面的伪代码明确两个 handler 的调用位置：

```python
async def awrap_tool_call(request, agent_handler):
    token = mcp_auth_context_var.set(current_auth_context)
    try:
        return await agent_handler(request)  # 一次 Agent 工具调用只执行一次
    finally:
        mcp_auth_context_var.reset(token)


async def recovery_interceptor(request, mcp_handler):
    observed_generation = proxy.generation

    if not proxy.is_connected:
        status = proxy.request_reconnect(observed_generation)
        if status == "stopped":
            return unavailable_before_send_result()
        if status != "stale_generation":
            restored = await proxy.wait_for_new_session(observed_generation, timeout=5)
            if not restored:
                return unavailable_before_send_result()

    call_generation = proxy.generation
    try:
        return await mcp_handler(request)  # 本次请求第一次真正发送
    except SUPPORTED_CONNECTION_ERRORS as exc:
        status = proxy.request_reconnect(call_generation)
        if status == "stopped":
            return connection_error_result(exc)
        if not tool_is_read_only_or_idempotent(request.name):
            return unknown_result_error(exc)  # 不重放
        if status != "stale_generation":
            await proxy.wait_for_new_session(call_generation, timeout=5)

        retry_generation = proxy.generation
        try:
            return await mcp_handler(request)  # 同一闭包经代理访问新 Session
        except SUPPORTED_CONNECTION_ERRORS as retry_exc:
            proxy.request_reconnect(retry_generation)
            return retry_failed_result(retry_exc)  # 不进行第三次调用
```

`mcp_handler` 是 Adapter `_build_interceptor_chain()` 传入的内层 handler，最终执行其 `execute_tool()`；其中闭包变量 `session` 就是 `_SessionProxy`。所以第二次 `mcp_handler(request)` 不会重新进入 `RuntimeConfigMiddleware.awrap_tool_call()`，却会重新解析代理当前持有的 `ClientSession`。

`LongLivedSession` 的唯一建连循环如下：

```python
while not stop_requested:
    try:
        async with client.session(server_name) as new_session:  # 内部 initialize
            proxy.publish(new_session)  # generation += 1
            clear_completed_reconnect_generation()
            reason = await keep_alive_until_stop_or_reconnect(new_session)
            if reason == "stop":
                break
            await proxy.disconnect()  # 先禁止新调用，再关闭旧 pending streams
    except SUPPORTED_SESSION_ERRORS as exc:
        mark_reconnect_generation(proxy.generation)
        await proxy.disconnect()
        if never_connected_successfully:
            fail_start(exc)
            break

    await wait_reconnect_backoff_or_stop()
```

不论触发源是 Adapter 连接异常、ping 失败还是传输上下文退出，最终都只让这个循环进入下一次 `client.session()`；其他组件只能发请求或等待 generation，不能自行建连。

### 5.3 工具安全重试资格

只使用 MCP 标准 ToolAnnotations：

- `readOnlyHint is True`
- `idempotentHint is True`

满足任意一个即允许在“请求已开始后断线”的情况下自动重试一次。

以下方式明确禁止：

- 不根据工具名称猜测。
- 不根据 description 文案猜测。
- 不让 LLM 判断是否幂等。
- 不默认把未标注工具视为安全。
- 不新增数据库或前端逐工具重试配置。

MCP ToolAnnotations 是提示信息，管理员应只接入可信 MCP Server。Yuxi 的保守默认值是：没有明确 `True` 就不重试。

### 5.4 等待时间与重试次数

新增环境变量：

```text
YUXI_MCP_TOOL_RECONNECT_WAIT_SECONDS=5
```

语义：

- 默认等待 5 秒。
- 允许使用非负浮点数。
- `0` 表示不等待重连。
- 等待对象是当前 server、当前 partition、当前配置 hash 对应的同一个 `_SessionProxy`，不是连接池中的任意 Session。
- 连接异常发生后先调用 `request_reconnect()`，再开始计算等待时间；等待动作本身不创建连接。
- `_reconnect_event` 会立即唤醒 `LongLivedSession._run_loop()`，恢复不依赖下一次 30 秒 ping。
- 仅限制单次工具调用或工具加载对临时重连的等待，不修改或取消连接池后台重连策略。
- 5 秒内没有出现新 generation 时，本次工具调用返回 Tool 错误；后台循环继续按 1、2、4、8 秒等退避节奏重连，后续调用仍可恢复。
- 5 秒是等待上限，不承诺 MCP Server 在该时间内一定恢复，也不要求后台循环为单次工具调用额外创建并行连接。

重试次数固定为一次，不增加额外配置项。

## 6. 异常分类

### 6.1 连接关闭异常

恢复拦截器只识别：

- `anyio.EndOfStream`
- `anyio.ClosedResourceError`
- `anyio.BrokenResourceError`
- `httpx.ConnectError`
- `httpx.ReadError`
- `httpx.RemoteProtocolError`
- `ConnectionResetError`
- `BrokenPipeError`
- 所有叶子异常均属于上述连接异常的 `BaseExceptionGroup`

异常组按子异常递归检查。只有至少包含一个叶子异常，且所有叶子异常都属于上述明确连接异常时，才进入恢复分支。只要混有取消异常、程序错误或其他未知异常，就保持原异常传播，避免误吞真实缺陷或破坏取消语义。

命中连接关闭异常后首先请求重连。是否等待并重试由“调用前是否已有 Session”和 ToolAnnotations 决定；连接是否需要修复不取决于工具是否幂等。

### 6.2 请求超时

请求超时不自动重试。

原因：

- 超时不等同于 Session 已断开。
- 服务端可能仍在执行长任务。
- 立即重试可能重复消耗资源或放大负载。

MCP 请求超时应转换成 Tool 错误，让聊天继续，并提示调用结果未知。

请求超时不调用 `request_reconnect()`，避免仅因某个长任务执行缓慢就销毁仍然健康的共享 Session。

### 6.3 不由恢复拦截器处理的错误

- MCP 正常返回的 `CallToolResult(isError=True)`。
- `ToolException`。
- 参数校验错误。
- MCP 业务错误。
- 普通 `ValueError`、`TypeError` 等程序错误。
- 401 鉴权错误。
- `CancelledError`、`KeyboardInterrupt`、`SystemExit`。

这些错误继续由现有层处理，避免吞掉真实缺陷或破坏取消语义。

### 6.4 401 与 Token 刷新边界

动态 Token 的 401 重试继续由 `DynamicMCPTokenAuth` 负责：

1. 清除请求头缓存和 Redis access token。
2. 重新解析并获取 Token。
3. 通过 HTTPX Auth 的第二次 yield 重发 HTTP 请求。

恢复拦截器不接管 401，不清理 Token，不修改连接状态。

Session 重连后，新的 HTTP 请求仍会通过 `DynamicMCPTokenAuth` 注入当前有效 Token。

## 7. 错误返回与聊天行为

预期的连接恢复失败统一返回：

```python
CallToolResult(
    isError=True,
    content=[TextContent(type="text", text="...")],
)
```

`langchain-mcp-adapters` 会将 `isError=True` 转成 `ToolException`，现有 `handle_tool_error=True` 再将其转换成 ToolMessage。因此 LangGraph 会继续运行，模型可以解释错误或继续执行其他步骤。

### 7.1 调用前未连接

```text
MCP 服务「{server_name}」当前不可用，5 秒内未恢复。本次工具请求尚未发送。
```

### 7.2 未标注工具在途断线

```text
MCP 服务「{server_name}」在工具「{tool_name}」执行期间连接中断。该工具未声明为只读或幂等，系统未自动重试；执行结果可能已经生效，请确认后再试。
```

### 7.3 安全工具重连超时

```text
MCP 服务「{server_name}」连接中断，5 秒内未恢复，工具「{tool_name}」的自动重试未执行。
```

### 7.4 重试再次失败

```text
MCP 服务「{server_name}」已重连，但工具「{tool_name}」自动重试仍然失败。
```

错误内容面向模型和用户，必须同时说明：

- 是否发生自动重试。
- 请求是否可能已经生效。
- 是否可以安全再次尝试。

## 8. 日志设计

连接恢复日志记录：

- MCP Server 名称。
- 工具名称。
- 异常类型。
- 异常发生在调用前无 Session，还是在途调用阶段。
- 调用开始时的 generation。
- `request_reconnect()` 是被接受、合并，还是因 generation 已变化而 no-op。
- 重连后的 generation。
- 工具是否符合安全重试条件。
- 等待是否超时。
- 是否执行了自动重试。
- 自动重试是否成功。

不记录：

- 工具参数。
- Tool result 原文。
- Authorization header。
- access token、refresh token。
- connection credential。

空字符串异常必须通过异常类型补全日志，例如：

```text
MCP tool call interrupted: server=..., tool=..., error=EndOfStream
```

不再只记录空白的 `Error streaming messages:`。

## 9. Demo MCP Server 测试能力

### 9.1 工具注解

给现有回显工具添加符合其真实语义的注解：

- `echo_global`
- `echo_dept_data`
- `echo_user_profile`

统一声明：

```text
readOnlyHint=true
idempotentHint=true
destructiveHint=false
```

### 9.2 延迟工具

新增 `echo_delayed_safe`：

- 参数：`message`、`delay_seconds`。
- 延迟后返回回显。
- 声明只读、幂等、非破坏性。
- 用于验证自动重试成功。

新增 `echo_delayed_unannotated`：

- 参数和行为与安全延迟工具相同。
- 不声明 ToolAnnotations。
- 用于验证保守默认策略。

### 9.3 故障控制接口

Demo Server 增加测试专用接口：

- `GET /test/faults/state`
  - 返回当前正在执行的延迟工具名称和数量。
  - 不返回请求参数。
- `POST /test/faults/restart`
  - 先返回 HTTP 响应。
  - 随后向当前 Demo Server 主进程发送退出信号。

Compose 已为 `mcp-demo-server` 配置 `restart: unless-stopped`。进程退出后容器会真实重启，从而覆盖 Docker DNS 短暂不可用、HTTP 连接关闭和 MCP Session 重建。

这些接口只存在于 `backend/test/mcp_demo_server.py`，不进入生产 API。

## 10. 测试设计

### 10.1 单元测试

扩充 `backend/test/unit/services/test_mcp_client_pool.py`，覆盖以下职责。

`LongLivedSession` 和连接池生命周期：

1. 真正的首次连接失败时 `start()` 失败，连接池不发布条目。
2. 首次连接成功后，第一次重连尝试失败不会使 `_run_loop` 退出。
3. 连续多次重连失败后仍继续退避，并在后续成功时重新绑定同一 `_SessionProxy`。
4. 重连成功后 generation 只增加一次，不为失败的连接尝试增加。
5. `request_reconnect(expected_generation)` 首次请求返回 `accepted` 并立即唤醒 keepalive，不等待 30 秒 ping。
6. generation 已变化时返回 `stale_generation`，不关闭新 Session。
7. 同一 generation 的后续请求返回 `merged`，只执行一次 Session 重建。
8. Event 被 `_run_loop()` 消费后、新 Session 发布前，同 generation 请求仍因 `_reconnect_generation` 返回 `merged`。
9. ping 失败或传输退出进入退避后，同 generation 的工具调用请求返回 `merged`，不会留下导致新 Session 再次断开的 Event。
10. 后台任务已停止时返回 `stopped`，不设置永远无人消费的重连事件。
11. 主动重连、ping 失败和传输上下文退出进入同一个退避重连分支。
12. 收到 `stop` 时可以从 keepalive 或重连退避中立即退出。
13. 同一个 `LongLivedSession` 不会并行启动两个 `_run_loop`。
14. cache key 和配置 hash 相同且后台循环仍在重连时，`get_session()` 不淘汰原条目。
15. 并发 `get_session()` 等待并返回同一个代理，不创建第二个 `LongLivedSession`。
16. `get_session()` 在 `_dict_lock` 外等待，其他 server 或 partition 的池操作不被阻塞。
17. 当前获取操作等待超时后抛出 `MCPConnectionRecoveringError`，后台重连任务和池条目仍然保留。
18. 配置 hash 改变、显式 remove 或连接池关闭时，原条目仍按现有行为停止并淘汰。

`_SessionProxy` 和恢复拦截器：

1. `_SessionProxy` 初始 generation 为 0。
2. 首次绑定 Session 后 generation 为 1。
3. 断开时 generation 不增加，连接事件清除。
4. 绑定新 Session 后 generation 增加并唤醒等待者。
5. 多个等待者能被同一次重连同时唤醒。
6. `wait_for_new_session()` 不会被同一 generation 或其他连接条目唤醒。
7. `request_reconnect()` 正确委托给所属 `LongLivedSession`，自身不创建 Session。
8. 等待超时返回明确失败结果，但不触发第二个连接任务。
9. 调用前未连接时，无论工具是否有注解，都先请求重连，等待成功后 Adapter handler 只执行一次。
10. 调用前未连接且等待超时时，Adapter handler 不执行。
11. `readOnlyHint` 工具收到 `EndOfStream` 后请求重连并重试一次。
12. `idempotentHint` 工具收到 `ClosedResourceError` 后请求重连并重试一次。
13. 安全工具收到 `BrokenResourceError` 后请求重连并重试一次。
14. 未标注工具收到在途连接关闭异常时请求重连，但不等待、不重试。
15. generation 已经变化时，安全工具直接使用新 Session，未标注工具仍不重放。
16. 后台所有者返回 `stopped` 时立即返回 Tool 错误，不等待 5 秒。
17. 重连超时时不进行第二次 Adapter handler 调用。
18. 第二次调用再次出现连接错误时，对新 generation 请求重连，但不进行第三次工具调用。
19. 一次 Agent Middleware handler 调用内，Adapter handler 原始调用和安全重试合计最多两次。
20. 仅由连接异常组成的 `BaseExceptionGroup` 可以识别。
21. 混有 `ValueError` 或取消异常的异常组继续传播。
22. 请求超时转换成 Tool 错误但不请求重连、不重试。
23. 普通 `ValueError` 继续抛出。
24. 取消异常继续传播。
25. 日志不包含工具参数、Token 或请求头。

扩充 `backend/test/unit/services/test_mcp_tool_registry_service.py`，覆盖：

1. `load_mcp_tools()` 收到恢复拦截器。
2. `readOnlyHint=true` 进入安全重试集合。
3. `idempotentHint=true` 进入安全重试集合。
4. 未标注工具不进入安全重试集合。
5. 原有 `id`、`mcp_server_name` 和 `handle_tool_error` 保持不变。
6. 非 MCP 工具不受影响。
7. `MCPConnectionRecoveringError` 不进入失败冷却，也不调用 `remove_session()`。
8. `list_tools` 遇到支持的连接关闭异常时请求原代理重连，只清 Tool 对象缓存，不停止仍在运行的所有者。
9. 配置、鉴权或普通程序错误仍按现有规则进入冷却和清理。

扩充 `backend/test/unit/middlewares/test_runtime_config_middleware.py`，验证 LangChain 外层边界：

1. `RuntimeConfigMiddleware.awrap_tool_call()` 只调用一次外层 handler。
2. Adapter 内部发生一次安全重试时，不会重新进入 RuntimeConfig 或 Skills Middleware。
3. 原始 MCP 调用和内部重试期间 `mcp_auth_context_var` 都保持当前用户的 `AuthContext`。
4. Adapter 返回错误 ToolMessage 后，`AuthContext` 在 `finally` 中正常重置。
5. 预期连接异常安装恢复拦截器后不再冒泡到 `awrap_tool_call()`。

### 10.2 真实集成测试

新增 MCP 重连集成测试，使用真实：

- MCP CRUD API。
- Postgres MCPServer/MCPConnection 配置。
- Runtime MCP 配置解析。
- `mcp-demo-server` 容器。
- MCP SDK。
- LangChain MCP Adapter。
- Yuxi MCPClientPool。

安全工具场景：

1. 通过 API 创建测试 MCP Server 和连接配置。
2. 加载 `echo_delayed_safe`。
3. 异步启动工具调用。
4. 轮询 `/test/faults/state`，确认工具已经开始执行。
5. 调用 `/test/faults/restart`。
6. 断线窗口内再次请求相同 cache key，验证连接池没有创建第二个 `LongLivedSession` 或替换原代理。
7. 在重连窗口触发下一次工具加载，验证其等待超时或 `list_tools` 断线不会停止原 `LongLivedSession`。
8. 等待容器自动恢复和原 `_SessionProxy` 的 Session generation 增加。
9. 验证工具自动重试一次并成功返回。
10. 验证同一次 Agent 工具调用只产生一个 ToolNode/外层 Middleware 调用，但 Demo Server 最多收到原始调用和一次安全重试。
11. 验证下一次普通 MCP 调用继续成功。

未标注工具场景：

1. 加载 `echo_delayed_unannotated`。
2. 工具执行过程中重启 Demo Server。
3. 验证调用返回 Tool 错误而不是向上抛出流异常。
4. 验证错误包含“未自动重试”和“执行结果可能已经生效”。
5. 验证恢复后的下一次普通 MCP 调用成功。

测试必须在 `finally` 中清理创建的 MCP Server 和 connection。

### 10.3 E2E 聊天测试

新增 `backend/test/e2e/test_mcp_reconnect_e2e.py`。

安全工具场景：

1. 创建专用 MCP Server、连接、Agent Config 和 Chat Thread。
2. Agent Config 只启用目标 MCP，降低工具选择不确定性。
3. 通过 `/api/chat/agent` 发起真实流式聊天，明确要求调用 `echo_delayed_safe`。
4. 工具开始后通过 Demo fault API 重启 Server。
5. 断言流式响应没有出现 `Error streaming messages`。
6. 断言最终 Assistant 消息正常生成。
7. 断言工具结果来自重连后的成功调用。
8. 再发送一条消息，验证后续 MCP 调用继续正常。

未标注工具场景：

1. 明确要求调用 `echo_delayed_unannotated`。
2. 工具开始后重启 Demo Server。
3. 断言聊天流没有中止。
4. 断言 Tool 错误说明未自动重试和执行结果未知。
5. 测试 Agent 的 system prompt 明确要求发生工具错误时不要自行再次调用，避免模型层重试干扰底层断言。
6. 断言后续聊天仍可继续。

E2E 不断言底层必须抛出某一个具体 AnyIO 异常，只断言支持的连接关闭异常最终得到一致的用户行为。

### 10.4 回归验证

实现完成后至少运行：

```bash
docker exec api-dev uv run --group test pytest \
  test/unit/services/test_mcp_client_pool.py \
  test/unit/services/test_mcp_tool_registry_service.py \
  test/unit/middlewares/test_runtime_config_middleware.py -q
```

```bash
docker exec api-dev uv run --group test pytest \
  test/integration -k "mcp and reconnect" -q
```

```bash
docker exec api-dev uv run --group test pytest \
  test/e2e/test_mcp_reconnect_e2e.py -m e2e -q
```

```bash
docker exec api-dev uv run --group dev ruff check \
  package/yuxi/agents/mcp/client_pool.py \
  package/yuxi/agents/mcp/tool_registry_service.py \
  test/mcp_demo_server.py \
  test/unit/services/test_mcp_client_pool.py \
  test/unit/services/test_mcp_tool_registry_service.py \
  test/unit/middlewares/test_runtime_config_middleware.py \
  test/e2e/test_mcp_reconnect_e2e.py
```

还需手工确认：

- `manual_mcp_13_token_pre_refresh` 的 15 秒 Token 和提前刷新测试行为不变。
- 重启发生在安全工具调用期间时，聊天能够继续并完成。
- 重启发生在未标注工具调用期间时，聊天继续但不自动重试。
- MCP Server 持续不可用超过 5 秒时，页面收到明确错误而不是空白 streaming error。

## 11. 文件改动范围

预计修改：

- `backend/package/yuxi/agents/mcp/client_pool.py`
- `backend/package/yuxi/agents/mcp/tool_registry_service.py`
- `backend/test/mcp_demo_server.py`
- `backend/test/unit/services/test_mcp_client_pool.py`
- `backend/test/unit/services/test_mcp_tool_registry_service.py`
- `backend/test/unit/middlewares/test_runtime_config_middleware.py`
- `backend/test/integration/...` 下一个职责明确的 MCP 重连测试文件
- `backend/test/e2e/test_mcp_reconnect_e2e.py`
- `docs/develop-guides/roadmap.md`

不修改：

- MCP Auth 数据模型。
- MCP CRUD API。
- MCPConnection 数据库结构。
- 前端 MCP 配置页面。
- `RuntimeConfigMiddleware.awrap_tool_call()` 的生产职责；只补调用链回归测试，不在该层实现重连。
- Redis Token 缓存结构。
- `DynamicMCPTokenAuth` 的 401 行为。
- 第三方 MCP 或 LangChain 包。
- Redis 工具 Manifest 格式；该 Manifest 不参与运行时工具调用恢复。

## 12. 兼容性与风险

### 12.1 重复执行风险

只有显式声明只读或幂等的工具才会在请求已开始后自动重试。未标注工具保守失败，避免重复写入、重复发送或重复创建资源。

### 12.2 错误注解风险

ToolAnnotations 由 MCP Server 提供，属于提示信息。管理员错误接入不可信或错误标注的 Server，仍可能导致重复执行。Yuxi 不对未标注工具做推断，也不允许模型覆盖该策略。

### 12.3 慢重启风险

默认等待 5 秒只覆盖短暂网络抖动和常见容器快速重启。它是工具调用的耐心上限，不是后台重连总时长。更慢的恢复会让本次工具调用返回 Tool 错误，但同一个 `LongLivedSession` 继续在后台重连；后续调用仍可恢复。

### 12.4 并发调用

多个安全工具可以对同一 generation 报告连接错误，但 `request_reconnect()` 必须将它们合并为一次重连过程。多个安全工具可以等待同一次 generation 增加，并在新 Session 上分别重试。连接创建仍由单个 `_run_loop` 串行负责，不会因为等待者数量增加而创建并行 Session。因为这些工具已声明只读或幂等，不需要为工具执行增加全局串行锁。

### 12.5 LangChain Middleware 重入风险

恢复逻辑只调用 MCP Adapter interceptor 的 handler，不再次调用 Agent Middleware handler。否则 Skills 激活、工具调用计数、追踪回调或其他 `awrap_tool_call` 副作用可能执行两次。测试必须分别统计外层 handler 和 Adapter handler 的调用次数。

### 12.6 Stdio 兼容

Stdio 子进程退出同样可能表现为 AnyIO stream 关闭异常。恢复拦截器使用统一连接错误分类，不依赖 HTTP 专属行为。正常 Stdio 工具调用不会增加重试或等待。

### 12.7 重连期间的工具可见性

如果下一轮 `awrap_model_call()` 加载工具时，MCP Server 在 5 秒内仍未恢复，本轮返回空 MCP 工具列表，不让模型继续选择一个当前无法调用的工具。该行为只影响当前模型调用，不进入失败冷却、不移除连接条目；后台重连成功后，后续模型调用会按现有动态加载流程重新获得工具。

## 13. 实施顺序

1. 先为“首次重连失败后循环退出”“重连期间连接池淘汰旧代理”“工具加载误停止重连所有者”和“主动重连事件不能立即唤醒 keepalive”编写失败单元测试。
2. 使用 `first_connect` 修复 `LongLivedSession` 连续重连条件，并增加 `_reconnect_event` 与 `_reconnect_generation`，统一主动请求、ping 失败和传输退出三条重连入口。
3. 修复 `MCPClientPool.get_session()` 对正在重连条目的复用与等待，增加 `MCPConnectionRecoveringError`，避免替换旧代理。
4. 为 `_SessionProxy` 实现 generation、`request_reconnect()` 和连接状态等待。
5. 为恢复拦截器编写失败单元测试并实现 `MCPToolCallRecoveryInterceptor`，验证只重试 Adapter handler。
6. 在工具加载路径接入 interceptor 和 ToolAnnotations 策略，并修正暂态重连异常的清理边界。
7. 补充 `RuntimeConfigMiddleware.awrap_tool_call()` 外层只执行一次且 `AuthContext` 覆盖内部重试的回归测试。
8. 完成目标单元测试和 Ruff。
9. 扩展 Demo Server 的延迟工具、注解与故障控制接口。
10. 增加真实集成测试和 E2E 聊天重启测试。
11. 回归 Token 提前刷新、401、普通 MCP 和 Stdio 场景。
12. 更新 roadmap，检查最终 diff 只包含本需求必要改动。

## 14. 完成定义

本任务只有在以下条件全部满足时才算完成：

- 自动重连和调用级恢复职责边界清晰。
- `LongLivedSession` 是唯一主动创建 Session 的组件，等待者不会并行建立连接。
- MCP Adapter 连接异常会主动请求重连，不依赖最长 30 秒的 ping 周期。
- 同一 generation 的并发重连请求合并为一次 Session 重建。
- 初次连接成功后，连续重连失败不会使后台循环提前退出。
- 临时断线期间，同一配置的连接池条目和 `_SessionProxy` 不被替换。
- 下一轮工具加载不会停止仍在重连的 `LongLivedSession`。
- 5 秒工具等待超时不会停止后台重连。
- 一次 Agent 工具调用只进入一次外层 `awrap_tool_call` handler；安全恢复最多调用两次 MCP Adapter handler。
- `RuntimeConfigMiddleware` 不承担连接池或 Session 重建职责，`AuthContext` 覆盖完整的内部恢复过程。
- 安全工具最多自动重试一次。
- 未标注工具绝不自动重放。
- 所有预期连接关闭都不会直接终止聊天流。
- 真实 Demo Server 重启测试可重复执行。
- 单元、集成、E2E 和 Ruff 全部通过。
- Token 和权限相关回归测试通过。
- 没有引入数据库或前端改动。
- 没有修改第三方包。
- 没有提交工作区中与本任务无关的已有改动。

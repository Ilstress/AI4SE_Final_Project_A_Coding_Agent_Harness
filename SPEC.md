# SPEC.md — AI4SE Coding Agent Harness

> **状态：** 架构已冻结（Architecture Frozen）
> **角色：** PLAN.md、实现与测试的唯一设计依据（Single Source of Truth）
> **范围：** 本文档仅描述最终采用的设计，不记录 brainstorming 过程、方案比较或已放弃的替代方案。

---

## 1. 问题陈述

### 1.1 问题

大语言模型（LLM）能够生成代码，但它们本质上是无状态的文本生成器——无法自主执行动作、验证结果或在出错时停止。将 LLM 转变为一台可靠的编码智能体（Coding Agent），需要一个 **Harness**：一个软件内核，将 LLM 封装在控制循环中，配备工具分发、反馈驱动的自我修正、治理护栏和确定性的停机条件。

现有的 Agent 编排框架（LangChain、CrewAI、AutoGen）提供了高层抽象，掩盖了底层的工程细节。本项目从零构建一个 Harness，以暴露并掌握 Agent 运行时的每一层。

### 1.2 目标用户

希望将编码任务（写代码、运行测试、修复 Bug）委托给 LLM 驱动的 Agent，同时保留对安全边界、执行限制和修正循环的确定性控制权的软件开发者。

### 1.3 价值

核心等式是 **Agent = LLM + Harness**。LLM 是"CPU"——它只负责决定下一步做什么。其余所有（治理、反馈、工具执行、记忆、配置）都是工程。本项目回答的核心问题是：*当 LLM 能完成大部分"思考"时，工程师的价值落在哪里？*

### 1.4 设计目标

1. **零框架依赖**：Harness 内核中不使用 LangChain、CrewAI、AutoGen 或任何 Agent 编排框架。
2. **代码级机制，非提示词**：所有反馈信号、护栏和停机条件均为确定性代码，而非 LLM 提示词中的指令。
3. **Mock 可测内核**：每个核心机制必须能用 mock/stub LLM 在确定性单元测试中验证——不需要真实 LLM，不需要网络。
4. **深度聚焦反馈闭环**：在 Harness 的六个维度中，反馈是主要贡献点，以四层管道 + 表驱动状态机实现。
5. **最小可行覆盖**：六个维度（决策、工具、记忆、治理、反馈、配置）均具备可运行的最低实现；反馈维度实现深入。

---

## 2. 用户故事

### US-1：为项目配置 Harness

**故事：** 作为开发者，我希望通过一个 TOML 文件配置 Harness 的工作区路径、LLM 提供商和安全规则，使 Agent 在我定义的边界内运行，无需每次手动设置。

**验收标准：**
- 启动时加载 `config.toml` 文件，会话期间视为不可变。
- 配置包括：工作区根目录、最大迭代次数、超时时间、危险命令模式、LLM 提供商和模型选择。
- API Key 明确排除在 TOML 文件之外。
- 无效或缺失的配置触发明确的错误信息并优雅退出。

### US-2：将编码任务委托给 Agent

**故事：** 作为开发者，我希望给 Agent 一个自然语言任务（例如"修复 test_auth.py 中失败的测试"），让它自主读取文件、编写代码、执行 Shell 命令直到任务完成，无需进一步人工干预。

**验收标准：**
- Agent 在启动时接受用户任务字符串。
- Agent 通过 Main Loop 迭代：读取文件、编写代码、执行 Shell 命令并评估结果。
- Agent 在判定任务完成时声明 `task_complete`。
- 如果 Agent 在迭代限制内无法收敛，以 `FAILED` 状态停机并给出明确原因。

### US-3：防止危险操作

**故事：** 作为开发者，我希望 Harness 自动阻止越界操作（如写入 `/etc/`），并对我批准边界内的危险操作（如破坏性 Shell 命令）要求显式审批，从而信任 Agent 操作我的系统。

**验收标准：**
- 任何目标路径在工作区根目录外的文件或 Shell 操作被立即阻止，判定为 `BLOCKED`。
- 边界内的危险操作（如递归删除、数据库删除、网络上传）触发审批请求。
- Agent 暂停并等待开发者在终端输入 `y` 或 `n` 后才继续。
- 所有被阻止和已审批的动作记录到审计日志。

### US-4：基于测试失败自我修正

**故事：** 作为开发者，我希望 Agent 自动检测其代码变更是否导致测试失败，并在无人干预的情况下尝试修复，从而收敛到可工作的解决方案。

**验收标准：**
- 执行 Shell 命令后，Agent 捕获退出码、stdout 和 stderr。
- 非零退出码被解析为结构化的 Feedback 对象。
- Agent 在下一轮 LLM 上下文中接收 Feedback 并尝试修复。
- 如果同一错误连续出现 3 次，Agent 以收敛失败停机。

### US-5：审查和批准敏感操作

**故事：** 作为开发者，我希望在 Agent 尝试执行危险但可能合法的操作（如 `rm -rf ./build/`）时被要求显式审批，从而对破坏性操作保留最终决定权。

**验收标准：**
- 当在工作区边界内检测到危险模式时，Agent 进入 `AWAITING_HUMAN` 状态。
- 开发者看到动作描述、触发的规则和支持证据。
- 批准（`y`）恢复 Agent 执行；拒绝（`n`）使 Agent 重新规划而不执行该动作。
- 审批超时（可配置）导致 `FAILED` 停机。

### US-6：使用 Mock LLM 运行 Harness 进行测试

**故事：** 作为 Harness 的开发者，我希望用返回预定响应的 Mock 替代真实 LLM，从而为 Main Loop、Feedback Pipeline 和 Guard 模块编写确定性单元测试，无需网络调用或 API 费用。

**验收标准：**
- `MockAdapter` 实现与 `DeepSeekAdapter` 相同的 `AbstractLLM` 接口。
- Mock 响应可预编程：有效工具调用、格式错误响应、未知工具名和纯文本。
- 所有核心 Harness 机制使用 `MockAdapter` 通过单元测试，无需任何真实 LLM 或网络访问。
- 机制演示脚本复现：(a) 护栏阻止危险动作，(b) 注入失败后反馈驱动的自我修正，(c) 一项深度维度行为。

---

## 3. 功能规约

### 3.1 Main Loop（主循环）

**职责：** 编排 Agent 的运行时生命周期。Main Loop 是一个显式的、事件驱动的状态机，拥有迭代周期并将所有子任务委托给专门的模块。

**状态：**

| 状态 | 描述 |
|------|------|
| `START` | 初始状态；加载配置，初始化所有模块。 |
| `RUNNING` | 活跃迭代：上下文组装 → LLM 调用 → 动作解析 → 护栏 → 工具执行 → 反馈管道 → 停机检查。 |
| `AWAITING_HUMAN` | 暂停等待人工审批；迭代计数器和超时暂停。 |
| `COMPLETED` | 终端态；Agent 声明 `task_complete`。 |
| `FAILED` | 终端态；超出硬限制或检测到收敛失败。 |
| `CANCELLED` | 终端态；人工拒绝了审批请求。 |

**状态转换：**

| 从 | 事件 | 到 |
|------|------|------|
| `START` | `init_complete` | `RUNNING` |
| `RUNNING` | `task_complete` | `COMPLETED` |
| `RUNNING` | `hard_limit` | `FAILED` |
| `RUNNING` | `convergence_failure` | `FAILED` |
| `RUNNING` | `approval_required` | `AWAITING_HUMAN` |
| `AWAITING_HUMAN` | `approved` | `RUNNING`（恢复） |
| `AWAITING_HUMAN` | `rejected` | `CANCELLED` |
| `AWAITING_HUMAN` | `timeout` | `FAILED` |

**输入：** 用户任务字符串、不可变配置、初始记忆。

**行为：**
1. 通过 `ContextBuilder` 组装上下文（系统提示词 + 工具定义 + 记忆 + 消息历史 + 当前任务）。
2. 通过 `AbstractLLM` 适配器调用 LLM。
3. 通过 `ActionParser` 解析 LLM 响应。
4. 将 `TextOnly` 路由回上下文；将 `ToolCall(known)` 路由到 Guardrail；将 `ToolCall(unknown)` 和 `Malformed` 作为 `ParseError` 路由到 Feedback Pipeline。
5. 通过 Guardrail 评估动作。若 `BLOCKED`，产生 `ExecutionOutcome` 并进入 Feedback Pipeline。若 `APPROVAL_REQUIRED`，向 Main Loop 发出 `approval_required` 事件。
6. 通过 `ToolExecutor` 执行已批准的动作，产生 `ToolResult`。
7. 将 `ExecutionOutcome`（`ToolResult | GuardResult | ParseError`）送入 Feedback Pipeline。
8. 每次迭代后检查停机条件。

**输出：** 终端状态（`COMPLETED`、`FAILED`、`CANCELLED`）及最终消息历史和审计日志。

**边界条件：**
- 最大迭代次数由配置强制（`max_iterations`，默认 10）。
- 最大墙钟时间由配置强制（`timeout_seconds`）。
- `AWAITING_HUMAN` 时间独立于迭代超时单独追踪。

**错误处理：**
- LLM 调用失败：在适配器内部重试（3 次指数退避）；耗尽则发出 `LLMFatalError` → `FAILED`。
- 任何模块中未处理的异常：由 Main Loop 捕获、记录、转换到 `FAILED`。

#### 3.1.1 ContextBuilder（上下文组装器）

**职责：** 在每轮迭代开始前，将系统提示词、工具定义、记忆、消息历史和当前任务组装为 LLM 可接受的完整消息列表。ContextBuilder 是纯组装器——不决定"取什么"（由 MemoryRetriever 决定），只决定"如何组装"。

**输入：**
- 系统提示词（System Prompt）：由 Main Loop 提供的固定行为约束文本。
- 工具定义（Tool Definitions）：从 `ToolRegistry` 获取的所有已注册工具的 JSON Schema 定义列表。
- 记忆（Memory）：从 `MemoryRetriever` 检索到的记忆条目列表。
- 消息历史（Message History）：当前会话中所有已交换的消息（用户消息、LLM 响应、工具调用结果）。
- 当前任务（User Task）：用户最初输入的任务字符串。

**行为：**
1. 将系统提示词和工具定义组装为消息列表的头部（system role）。
2. 将记忆条目格式化后追加到系统消息中。
3. 将消息历史按时间顺序追加。
4. 若为第一轮迭代，将用户任务作为最后一条用户消息追加。
5. 返回完整的消息列表，不做任何过滤或修改。

**输出：** `list[dict]`——符合 LLM API 格式的消息列表。

**边界条件：**
- ContextBuilder 不持有消息历史——消息历史由 Main Loop 持有并传入。
- ContextBuilder 不修改任何输入——它是纯函数。
- 记忆条目过多时不做截断（此限制由 MemoryRetriever 的全量注入策略决定，在已知限制中记录）。

**错误处理：**
- 无——组装失败不会发生（所有输入均为已验证的数据结构）。

---

### 3.2 LLM Adapter（LLM 适配器）

**职责：** 将 LLM 提供商抽象在统一接口之后。处理提供商特定的请求格式化、响应解析和瞬时错误重试。

**输入：** 消息列表（系统提示词 + 历史 + 用户任务 + 工具定义）。

**行为：**
- `AbstractLLM` 定义接口：`async call(messages) → LLMResponse`。
- `DeepSeekAdapter` 为 DeepSeek API 实现该接口（兼容 OpenAI 格式）。
- `OpenAIAdapter` 为预留扩展点。
- `MockAdapter` 返回预编程的响应，用于确定性测试。
- 重试逻辑内置于每个适配器：对可重试错误（429、5xx、网络超时）进行 3 次指数退避重试（1s、2s、4s）；对不可重试错误（401、403、400）立即失败。
- 重试不消耗 Main Loop 迭代计数，不生成 Feedback。

**输出：** `LLMResponse`，包含 `content: str`、`tool_calls: list[dict] | None`、`finish_reason: str` 和 `usage: dict`。

**边界条件：**
- 适配器不得修改超出提供商 API 所需的消息列表。
- 适配器不得在调用之间缓存或存储消息。

**错误处理：**
- 可重试错误：指数退避，最多 3 次尝试。
- 不可重试错误：向 Main Loop 抛出 `LLMFatalError`。
- 格式错误的 API 响应：抛出 `LLMFatalError`。

---

### 3.3 Action Parser（动作解析器）

**职责：** 将每个 LLM 响应分类为四种确定性类别之一。解析器是纯函数——不涉及 LLM，不涉及概率性判断。

**输入：** 来自 LLM 适配器的 `LLMResponse`。

**行为：**

| 分类 | 条件 | 动作 |
|------|------|------|
| `TextOnly` | `content` 存在，`tool_calls` 为空或 `None` | 将内容追加到消息历史；继续下一轮迭代。 |
| `ToolCall(known)` | `tool_calls` 非空且 `tool_name` 已在 `ToolRegistry` 中注册 | 路由到 Guardrail。 |
| `ToolCall(unknown)` | `tool_calls` 非空且 `tool_name` 未注册 | 生成 `ParseError` → Feedback Pipeline。 |
| `Malformed` | `tool_calls` 存在但 JSON 解析失败或缺少必填参数 | 生成 `ParseError`（含解析错误详情）→ Feedback Pipeline。 |

**输出：** 以下之一：
- `TextOnly` → 内容字符串追加到消息历史
- `Action` 对象 → 路由到 Guardrail
- `ParseError` → 路由到 Feedback Pipeline

**边界条件：**
- `task_complete` 是一个已注册的工具；被解析为 `ToolCall(known)` 后，在 Guardrail 评估之后被视为停机信号。
- 单个响应中的多个 `tool_calls`：每个在同一迭代内依次解析和分发。
- 空响应（无 content，无 tool_calls）：分类为 `Malformed`。

**错误处理：**
- `ToolCall(unknown)` 和 `Malformed` 计入连续错误重试限制（3 次）。超过限制触发收敛失败。

#### 3.3.1 ToolRegistry（工具注册表）

**职责：** 维护所有已注册工具的集中注册表，供 ActionParser（验证工具名）和 ToolExecutor（分发执行）查询。ToolRegistry 在启动时由 Configuration Manager 根据配置中的 `tools.enabled` 初始化，初始化后不可变。

**输入：** 配置中的 `tools.enabled` 列表（若未配置则注册全部内置工具）。

**行为：**
- 启动时注册内置工具：`read_file`、`write_file`、`execute_shell`、`task_complete`。
- 提供 `is_registered(tool_name: str) → bool` 查询接口。
- 提供 `get_tool(tool_name: str) → ToolDefinition` 查询接口，返回工具的 JSON Schema 定义。
- 提供 `get_all_tools() → list[ToolDefinition]` 接口，用于 ContextBuilder 生成工具定义列表。

**输出：** 工具注册查询结果。

**边界条件：**
- 注册表初始化后不可变——运行时不支持动态注册/卸载工具。
- 若配置中禁用了某工具，该工具不出现于注册表中，LLM 调用该工具时将被 ActionParser 分类为 `ToolCall(unknown)`。

**错误处理：**
- 查询未注册的工具名：`is_registered` 返回 `False`；`get_tool` 抛出 `KeyError`（由 ActionParser 在调用前通过 `is_registered` 守卫）。

---

### 3.4 Guard + Rule Engine（护栏 + 规则引擎）

**职责：** 在执行前评估每个动作。基于可配置的规则阻止或标记危险操作。Guard 是无状态的——所有状态由 Main Loop 持有。

**输入：** `Action` 对象。

**行为：**
- `RuleEngine` 持有按 `priority` 排序的 `Rule` 实例有序列表。
- 每条 `Rule` 评估 `Action` 并返回一个 `RuleResult`，包含三种判定之一：`ALLOW`、`BLOCK`、`FLAG`。
- `BLOCK` 判定触发立即短路：不再评估后续规则。
- `FLAG` 判定被收集；继续评估剩余规则。
- 若所有规则返回 `ALLOW`，则允许该动作。
- 若任何规则返回 `FLAG` 且无规则返回 `BLOCK`，则生成 `ApprovalRequest`。
- 规则基于 Action 的抽象属性（目标路径、命令字符串、工具名）判断——不硬编码工具名称。

**内置规则：**

| 规则 | 优先级 | 默认判定 | 用途 |
|------|--------|----------|------|
| `PathBoundaryRule` | 100 | `BLOCK` | 写入路径必须在工作区根目录内 |
| `ShellCWDBoundRule` | 100 | `BLOCK` | Shell 工作目录必须在工作区根目录内 |
| `FileReadBoundRule` | 100 | `BLOCK` | 读取路径必须在工作区根目录内 |
| `DangerousShellRule` | 200 | `FLAG` | 检测破坏性模式（`rm -rf`、`:(){:|:&};:` 等） |
| `DBDestructiveRule` | 200 | `FLAG` | 检测数据库破坏性操作（`DROP TABLE`、`DELETE FROM`） |
| `NetworkExfilRule` | 200 | `FLAG` | 检测数据外泄模式（`curl ... \| sh`、上传命令） |

**输出：** `GuardResult`，包含：
- `verdict: ALLOWED | BLOCKED | APPROVAL_REQUIRED`
- `rule_results: tuple[RuleResult, ...]`——所有被触发的规则结果
- `approval_request: ApprovalRequest | None`——当判定为 `APPROVAL_REQUIRED` 时填充

**边界条件：**
- `read_file` 和 `write_file` 动作也经过 Guard（用于边界检查）。
- `task_complete` 动作经过 Guard（用于审计日志）。

**错误处理：**
- 规则在评估期间抛出异常：由 RuleEngine 捕获、记录，为安全起见视为 `BLOCK`。

---

### 3.5 Tool Executor（工具执行器）

**职责：** 执行已批准的动作。执行器是纯执行引擎——不做决策，不评估安全性，不修改动作。

**输入：** `Action` 对象（已通过 Guardrail，判定必须为 `ALLOWED`）。

**行为：**
- 基于 `tool_name` 路由到对应的处理器。
- `read_file(path)`：读取文件内容，返回 `ToolResult`。
- `write_file(path, content)`：将内容写入文件，返回 `ToolResult`。
- `execute_shell(command, cwd)`：在工作区中执行 Shell 命令，返回包含 exit_code、stdout、stderr 的 `ToolResult`。

**输出：** `ToolResult`，包含：
- `success: bool`
- `exit_code: int | None`（仅 Shell）
- `stdout: str | None`
- `stderr: str | None`
- `error: str | None`（文件 I/O 错误）
- `duration_ms: int`

**边界条件：**
- 所有文件路径相对于工作区根目录解析。
- Shell 命令以可配置的超时执行。
- Shell 命令继承工作区根目录作为工作目录。

**错误处理：**
- 文件不存在：`success=False`，`error="FILE_NOT_FOUND"`。
- 权限拒绝：`success=False`，`error="PERMISSION_DENIED"`。
- Shell 非零退出：`success=False`，`exit_code` 设为实际退出码。
- Shell 超时：`success=False`，`error="TIMEOUT"`。
- 所有失败通过 `ToolResult` 报告；无异常传播到 Main Loop。

---

### 3.6 Feedback Pipeline（反馈管道）

**职责：** 将所有执行结果转换为结构化的 Feedback，路由到对应的控制器，协调跨控制器状态转换，检测收敛失败。这是 Harness 的主要贡献点——完全由代码实现的四层管道。

**架构（4 层）：**

```
Layer 1: FeedbackGenerator  →  RawData → Feedback（按源，纯函数）
Layer 2: FeedbackRouter     →  Feedback → 轨道分配（无状态规则）
Layer 3: Controllers (SM)   →  RecoveryController | GovernanceController（表驱动状态机）
Layer 4: CoordinationLayer  →  ConvergenceDetector + EscalationManager（跨 SM 协调）
```

#### 3.6.1 Layer 1：FeedbackGenerator（反馈生成器）

**职责：** 将原始执行数据转换为统一的 `Feedback` 对象。每种反馈源有独立的 Generator——无副作用的纯函数。

**生成器列表：**

| 生成器 | 输入 | 产生 |
|--------|------|------|
| `ShellGen` | Shell 执行的 `ToolResult` | `Feedback(source=SHELL, payload={exit_code, stdout, stderr, command})` |
| `TestGen` | 测试执行的 `ToolResult` | `Feedback(source=TEST, payload={passed, failed, total, failures[]})` |
| `LintGen` | Lint 执行的 `ToolResult` | `Feedback(source=LINT, payload={errors[], warnings[]})` |
| `DiffGen` | 文件写入的 `ToolResult` | `Feedback(source=DIFF, payload={patch, files_changed, additions, deletions})` |
| `GuardGen` | `GuardResult` | `Feedback(source=GUARDRAIL, payload={verdict, rule_results})` |
| `ParserGen` | `ParseError` | `Feedback(source=PARSER, payload={error_type, raw_response})` |
| `ToolExecGen` | I/O 错误的 `ToolResult` | `Feedback(source=TOOL_EXECUTOR, payload={error, path})` |

**输入：** 原始执行数据（`ToolResult`、`GuardResult` 或 `ParseError`）。

**输出：** `Feedback` 对象（不可变，frozen）。

**边界条件：**
- 生成器不生成 `fingerprint`——由 `FingerprintStrategy` 在 Feedback 对象创建后统一生成。生成规则：`fingerprint = hash(tool_name + error_type + key_params)`，其中 `key_params` 为错误的关键参数（如 Shell 命令的前 N 个字符、测试失败用例名）。规则确保相同错误产生一致的 fingerprint，不同错误产生不同的 fingerprint。
- 生成器不路由也不做决策；它们仅将原始数据翻译为 Feedback 数据契约。

**错误处理：**
- 若生成器收到无法解析的数据，返回 `Feedback(source=SYSTEM, severity=ERROR, payload={...})`。

#### 3.6.2 Layer 2：FeedbackRouter（反馈路由器）

**职责：** 基于 source 和 severity 将每个 Feedback 分配到 Recovery 轨道或 Governance 轨道。路由器是无状态的——应用固定的规则表。

**路由规则：**

| Feedback Source | Severity | 轨道 |
|-----------------|----------|------|
| `SHELL` | 任意 | Recovery |
| `TEST` | 任意 | Recovery |
| `LINT` | 任意 | Recovery |
| `DIFF` | 任意 | Recovery |
| `TOOL_EXECUTOR` | 任意 | Recovery |
| `PARSER` | 任意 | Recovery |
| `GUARDRAIL` | `ERROR` 或 `CRITICAL` | Governance |
| `GUARDRAIL` | `INFO` 或 `WARNING` | Recovery（仅审计） |
| `PERMISSION` | 任意 | Governance |
| `SYSTEM` | `CRITICAL` | Governance |
| `SYSTEM` | 其他 | Recovery |

**输入：** `Feedback` 对象。

**输出：** 轨道分配（`RECOVERY` 或 `GOVERNANCE`）。

#### 3.6.3 Layer 3：RecoveryController（恢复控制器）

**职责：** 管理反馈驱动自我修正的恢复状态机。控制器是表驱动状态机——无 if-else 链。

**状态：** `IDLE`、`CONTINUE`、`RETRY`、`REPLAN`、`WAIT`。

**状态转换表：**

| 当前状态 | 事件 | 下一状态 | 副作用 |
|----------|------|----------|--------|
| `IDLE` | `FEEDBACK_RECEIVED` | `CONTINUE` | 将结果注入 LLM 上下文 |
| `CONTINUE` | `FEEDBACK_RECEIVED` | `CONTINUE` | 将结果注入 LLM 上下文 |
| `CONTINUE` | `SAME_ERROR` | `RETRY` | 注入反馈 + 计数器 +1 |
| `RETRY` | `SAME_ERROR` | `RETRY` | 注入反馈 + 计数器 +1 |
| `RETRY` | `FEEDBACK_RESOLVED` | `CONTINUE` | 重置计数器 |
| `RETRY` | `RETRY_THRESHOLD` | `REPLAN` | 要求 LLM 重新规划 |
| `REPLAN` | `FEEDBACK_RECEIVED` | `CONTINUE` | 重置计数器 |
| `REPLAN` | `SAME_ERROR` | `UPGRADE` | 升级到 Governance |

**输入：** 路由到 Recovery 轨道的 `Feedback` 对象。

**输出：** 恢复决策（`CONTINUE`、`RETRY`、`REPLAN`、`WAIT`）和修改后的 LLM 上下文。

**错误处理：**
- `SAME_ERROR` 通过匹配连续 Feedback 对象的 `fingerprint` 判定。
- `RETRY_THRESHOLD` 为连续 3 次相同 fingerprint 的 Feedback 事件。

#### 3.6.4 Layer 3：GovernanceController（治理控制器）

**职责：** 管理安全关键事件的治理状态机。控制器是表驱动状态机。

**状态：** `IDLE`、`BLOCK`、`ASK_HUMAN`、`FORCE_STOP`、`AUDIT`。

**状态转换表：**

| 当前状态 | 事件 | 下一状态 | 副作用 |
|----------|------|----------|--------|
| `IDLE` | `GUARD_BLOCKED` | `BLOCK` | 记录审计，注入 Feedback |
| `IDLE` | `GUARD_FLAGGED` | `ASK_HUMAN` | 向 Main Loop 发出 ApprovalRequest |
| `ASK_HUMAN` | `APPROVED` | `IDLE` | 通过 CoordinationLayer 恢复 |
| `ASK_HUMAN` | `REJECTED` | `IDLE` | 通过 CoordinationLayer 重新规划 |
| `IDLE` | `CONVERGENCE_FAILURE` | `FORCE_STOP` | 向 Main Loop 发出停机信号 |
| `IDLE` | `PRIVILEGE_ESCALATION` | `ASK_HUMAN` | 向 Main Loop 发出 ApprovalRequest |

**输入：** 路由到 Governance 轨道的 `Feedback` 对象，以及来自 CoordinationLayer 的升级事件。

**输出：** 治理决策（`BLOCK`、`ASK_HUMAN`、`FORCE_STOP`、`AUDIT`）。当为 `ASK_HUMAN` 时，产生一个 `ApprovalRequest` 给 Main Loop。

**关键约束：** GovernanceController 不执行审批交互。它只产生 `ApprovalRequest`。Main Loop 通过 `HumanApprovalProvider` 处理实际的人机交互。

**HumanApprovalProvider 接口：**

`HumanApprovalProvider` 是 Main Loop 用于获取人工审批结果的抽象接口，使 HITL 流程可注入 mock 进行确定性测试。

| 方法 | 输入 | 输出 | 描述 |
|------|------|------|------|
| `request_approval` | `ApprovalRequest` | `ApprovalResult` | 向用户展示审批请求并等待响应 |

**内置实现：**
- `TerminalApprovalProvider`：生产实现，通过 `input()` 在终端读取用户输入（`y`/`n`），支持超时。
- `MockApprovalProvider`：测试实现，接受预设的 `ApprovalResult` 列表，按顺序返回，无需用户交互。

**边界条件：**
- `HumanApprovalProvider` 不持有任何状态——每次 `request_approval` 调用是独立的。
- 超时行为由 Main Loop 管理（Main Loop 在 `AWAITING_HUMAN` 状态中启动 HITL 超时计时器），Provider 仅负责 I/O。若 Provider 实现支持超时，则返回 `TIMEOUT`；否则由 Main Loop 在超时后强制中断。

#### 3.6.5 Layer 4：CoordinationLayer（协调层）

**职责：** 跨两个控制器协调。观察两个状态机，追踪 fingerprint 收敛，管理 Escalate/Resume 转换。

**组件：**

- **ConvergenceDetector：** 跨迭代追踪 `fingerprint` 频率。当同一 fingerprint 在 Recovery 中连续出现 3 次，触发升级。
- **EscalationManager：** 实现 Recovery 与 Governance 之间的升级和恢复通道。

**升级条件（仅 3 条）：**

| 条件 | 触发 | 效果 |
|------|------|------|
| `CONVERGENCE_FAILURE` | 同一 fingerprint 达到重试阈值（3） | Recovery → Governance（`FORCE_STOP`） |
| `GUARDRAIL_TRIGGER` | Recovery 中 LLM 的修复尝试触发了危险动作 | Recovery → Governance（`BLOCK` 或 `ASK_HUMAN`） |
| `PRIVILEGE_ESCALATION` | Recovery 需要超出其权限范围的操作 | Recovery → Governance（`ASK_HUMAN`） |

**恢复条件：**

| 条件 | 触发 | 效果 |
|------|------|------|
| `HITL_APPROVED` | 人工批准动作 | Governance → Recovery（`CONTINUE`） |
| `HITL_REJECTED` | 人工拒绝动作 | Governance → Recovery（`REPLAN`） |

**输入：** RecoveryController 和 GovernanceController 的当前状态，以及历史 Feedback 事件。

**输出：** 向相应控制器发出的升级和恢复事件。

**边界条件：**
- CoordinationLayer 不持有任何控制器的内部状态。它只读取状态并发出事件。
- CoordinationLayer 是纯观察者 + 事件发射器，而非控制器本身。

---

### 3.7 Memory Manager（记忆管理器）

**职责：** 跨会话存储和检索项目约定、架构决策和历史任务摘要。记忆是"最小可行"实现——非主要贡献点。

**组件：**

| 组件 | 职责 |
|------|------|
| `MemoryStore` | 纯文件 I/O：将记忆条目读写到磁盘上的 JSON/Markdown 文件。 |
| `MemoryRetriever` | 给定当前用户任务，决定加载哪些记忆条目。当前实现：加载全部条目（小规模记忆的全量注入）。 |
| `MemoryPolicy` | 确定性代码，决定一个 Feedback 事件是否应持久化到长期记忆。决策：`PERSIST` 或 `DISCARD`。 |
| `Serializer` | 将 `PERSIST` 决策及其关联数据转换为可存储的格式。MVP：结构化 JSON 序列化器。LLM 摘要为预留扩展点。 |

**输入：**
- MemoryStore：记忆存储的文件路径。
- MemoryRetriever：当前用户任务字符串。
- MemoryPolicy：`Feedback` 对象。

**输出：**
- MemoryStore：`list[MemoryEntry]`。
- MemoryPolicy：`PersistDecision(PERSIST | DISCARD)`。

**边界条件：**
- MemoryPolicy 是代码机制，非提示词。其规则是确定性的（如 `source=USER_INPUT → PERSIST`、`source=SHELL → DISCARD`）。
- MemoryPolicy 与 Serializer 分离：Policy 决定"是否持久化"，Serializer 决定"持久化什么"。
- MemoryStore 不解释内容——只读取和写入。

**错误处理：**
- 记忆文件损坏：记录警告，以空记忆启动。
- 文件写入失败：记录错误，不持久化继续执行（非致命）。

---

### 3.8 Configuration Manager（配置管理器）

**职责：** 在启动时从 TOML 文件加载并验证配置。配置在会话期间不可变。

**配置模式：**

| 键 | 类型 | 必填 | 默认值 | 描述 |
|-----|------|------|--------|------|
| `workspace.root` | string | 是 | — | 项目工作区的绝对路径 |
| `llm.provider` | string | 是 | — | LLM 提供商标识符（`deepseek`、`openai`） |
| `llm.model` | string | 是 | — | 模型名称 |
| `llm.api_base` | string | 否 | 提供商默认值 | API 端点 URL |
| `loop.max_iterations` | int | 否 | 10 | Main Loop 最大迭代次数 |
| `loop.timeout_seconds` | int | 否 | 300 | 最大墙钟时间（秒） |
| `loop.convergence_threshold` | int | 否 | 3 | 收敛失败的相同错误阈值 |
| `guard.rules` | array | 否 | 内置默认值 | 自定义规则配置 |
| `guard.hitl_timeout_seconds` | int | 否 | 120 | HITL 审批超时（秒） |
| `tools.enabled` | array | 否 | 全部 | 启用的工具名称 |
| `memory.file_path` | string | 否 | `./memory.json` | 记忆存储文件路径 |

**输入：** `config.toml` 文件路径。

**输出：** 不可变的 `Config` 对象。

**边界条件：**
- 配置在启动时加载一次，运行时永不修改。
- API Key 绝不存放在 TOML 文件中。由 Credential Manager 单独管理。
- 缺失必填键触发启动错误并给出具体消息。

**错误处理：**
- 文件未找到：错误信息包含期望的路径。
- 无效 TOML 语法：错误信息包含行号。
- 无效值类型：错误信息包含键名和期望类型。
- 未知键：警告，忽略（向前兼容）。

---

### 3.9 领域与机制设计

> 本节满足课程 A 类文件 §A.5 要求：明确 coding 领域的反馈信号、危险动作、所需工具、记忆需求，说明重点维度及理由，并阐述机制的编码实现方式。

#### 3.9.1 领域分析

**反馈信号：** 在 coding 场景中，以下信号是客观的、确定性的，可回灌以驱动 Agent 自我修正：

| 信号 | 来源 | 确定性 | 实现阶段 |
|------|------|--------|----------|
| Shell 命令退出码（exit code） | `execute_shell` 的 `ToolResult` | 确定（0 = 成功，≠0 = 失败） | 阶段一 |
| 单元测试 pass/fail + 失败用例 + 堆栈 | 测试运行器的标准输出（pytest JSON/XML） | 确定 | 阶段二 |
| Linter 错误/警告 | Lint 工具的标准输出（flake8、mypy） | 确定 | 阶段三 |
| 类型检查错误 | 类型检查器输出（mypy、pyright） | 确定 | 阶段三 |
| 文件写入 Diff 验证 | Git diff 输出 | 确定 | 阶段三 |

**危险动作：** coding 场景中，以下操作具有破坏性或安全风险，必须由 Guard 拦截：

| 危险类别 | 示例 | 拦截层级 |
|----------|------|----------|
| 工作区边界逃逸 | 写入 `/etc/`、读取 `~/.ssh/`、Shell 切换到 `/` | 硬阻断（BLOCK） |
| 破坏性 Shell 命令 | `rm -rf /`、`fork bomb`、修改系统配置 | 需审批（FLAG） |
| 数据库破坏操作 | `DROP TABLE`、`DELETE FROM ...`（无 WHERE） | 需审批（FLAG） |
| 数据外泄 | `curl ... \| sh`、上传文件到外部服务器 | 需审批（FLAG） |

**所需工具：** Agent 需要以下工具完成 coding 任务：

| 工具 | 用途 | 是否经过 Guard |
|------|------|----------------|
| `read_file` | 读取源代码文件 | 是（边界检查） |
| `write_file` | 写入/修改源代码文件 | 是（边界检查） |
| `execute_shell` | 运行测试、构建、Lint 等命令 | 是（边界 + 危险模式） |
| `task_complete` | 声明任务完成 | 是（审计日志） |

**记忆需求：** 跨会话需要记住的信息：

| 信息类别 | 示例 | 持久化策略 |
|----------|------|------------|
| 项目约定 | 代码风格、命名规范 | 用户输入或 task_complete 摘要 → PERSIST |
| 架构决策 | 技术选型、模块划分 | 用户输入 → PERSIST |
| 历史任务摘要 | 上次任务的完成状态和关键决策 | task_complete 摘要 → PERSIST |
| 中间反馈 | Shell 输出、测试结果 | DISCARD（仅本轮有效） |

#### 3.9.2 重点维度：反馈闭环

**选择理由：** 在六个维度中，反馈闭环天然由代码构成——每个反馈信号（退出码、测试结果、Lint 输出）都是客观的、可解析的、可回灌的。反馈闭环的实现直接体现 §A.4-B 和 §A.4-C 的硬约束：所有机制必须是代码，且移除 LLM 后仍可用确定性单元测试验证。

**编码实现方式：**

| 机制 | 实现方式 | 代码化程度 |
|------|----------|------------|
| 反馈信号捕获 | 每个 Generator 是纯函数，解析 ToolResult/GuardResult/ParseError 为 Feedback 对象 | 100% 代码 |
| 反馈路由 | FeedbackRouter 是固定的规则表，source + severity → track | 100% 代码 |
| 恢复决策 | RecoveryController 是表驱动状态机，不依赖 LLM 判断 | 100% 代码 |
| 治理决策 | GovernanceController 是表驱动状态机，HITL 通过可注入的 HumanApprovalProvider 实现 | 100% 代码 |
| 收敛检测 | CoordinationLayer 的 ConvergenceDetector 基于 fingerprint 频率判定，纯算法 | 100% 代码 |
| 升级/恢复 | EscalationManager 的 3 条升级规则 + 2 条恢复规则是确定性的条件判断 | 100% 代码 |

**深度体现：** 反馈闭环的工程深度体现在四层管道架构：Generator（解析）→ Router（路由）→ Controller（决策，表驱动 SM）→ CoordinationLayer（跨 SM 协调）。每层独立可测，层间通过不可变 Event 通信。新增反馈源只需新增 Generator + 追加路由规则，不修改已有逻辑。

#### 3.9.3 其他维度的最低实现

| 维度 | 最低实现 | 位置 |
|------|----------|------|
| 决策 | Main Loop 状态机 + ActionParser 四分类 | §3.1, §3.3 |
| 工具 | ToolExecutor 三工具 + ToolRegistry 静态注册 | §3.3.1, §3.5 |
| 记忆 | MemoryStore 纯文件 + MemoryRetriever 全量注入 + MemoryPolicy 确定性规则 | §3.7 |
| 治理 | RuleEngine 优先级短路求值 + 6 条内置规则 + GovernanceController 表驱动 SM | §3.4, §3.6.4 |
| 配置 | Configuration Manager TOML 加载 + 不可变 Config | §3.8 |

---

## 4. 非功能性需求

### 4.1 性能

- Main Loop 迭代开销（不含 LLM 调用）必须低于 100ms。
- 工具执行超时可按工具类型配置（Shell：默认 60s，文件 I/O：默认 10s）。
- 低于 1MB 的记忆文件，操作必须在 50ms 内完成。

### 4.2 可靠性

- Harness 不得因单次 LLM 调用失败而崩溃。
- Harness 不得因单次工具执行失败而崩溃。
- Harness 必须始终到达终端状态（`COMPLETED`、`FAILED` 或 `CANCELLED`）——不得无限期挂起。
- 所有瞬时故障有明确定义的重试策略，且具有明确的上限。

### 4.3 安全性

- Guardrail 必须在执行前评估每个动作；不存在绕过路径。
- 工作区边界强制对所有文件和 Shell 操作是强制性的。
- 所有 Guardrail 阻止和 HITL 审批记录到审计追踪。
- Harness 不以提权方式执行；以用户的 OS 权限运行。

### 4.4 凭据威胁模型

| 威胁 | 缓解措施 |
|------|----------|
| API Key 在源代码中 | Key 绝不硬编码；运行时从 OS 钥匙串或加密文件加载 |
| API Key 在 Git 历史中 | `.gitignore` 包含凭据文件；pre-commit hook 扫描 Key 模式 |
| API Key 在 Shell 历史中 | Key 输入使用隐藏输入（无回显）；绝不作为 CLI 参数传递 |
| API Key 在日志中 | Credential Manager 在写入前从所有日志输出中脱敏 Key |
| API Key 在环境变量中 | 支持 `.env` 但文档说明其明文风险；推荐 OS 钥匙串 |
| 内存转储暴露 Key | Key 在内存中持有时间最短；LLM 调用后清除 |

### 4.5 可用性

- 首次运行体验：安全提示用户输入 API Key，创建默认 `config.toml`。
- 错误消息必须包含：出了什么问题、哪个模块、可操作的下一步。
- `AWAITING_HUMAN` 提示必须清晰展示：待审批的动作、触发的规则和证据。

### 4.6 可观测性

- 每次 Main Loop 状态转换记录时间戳和事件。
- 每次 Guardrail 评估记录判定和触发的规则。
- 每次 Feedback 事件记录 fingerprint、source、severity 和路由决策。
- 审计日志为追加式且人类可读。

### 4.7 可维护性

- 所有模块具有单一职责和明确定义的接口。
- 状态机转换表是数据结构，而非嵌入式 if-else 链。
- 新增 Rule 只需创建实现 `Rule` 接口的新类。
- 新增 Feedback 源只需创建新 Generator 并添加路由规则。

### 4.8 可测试性

- 每个核心模块必须能用 mock 依赖独立单元测试。
- Main Loop 必须能用 `MockAdapter` 测试（无真实 LLM）。
- Guardrail 必须能用构造的 `Action` 对象测试。
- Feedback Pipeline 必须能用构造的 `Feedback` 对象测试。
- HITL 流程必须能用 `MockApprovalProvider` 测试。
- 所有测试必须无网络访问即可通过。

### 4.9 可扩展性

- 新 LLM 提供商：实现 `AbstractLLM` 并注册。
- 新工具：实现 `Tool` 接口并在 `ToolRegistry` 中注册。
- 新 Guard 规则：实现 `Rule` 接口并以优先级添加到 `RuleEngine`。
- 新 Feedback 源：实现 `FeedbackGenerator` 并添加路由规则。
- 新控制器状态/事件：在转换表中追加行。

---

## 5. 系统架构

### 5.1 总体架构

Harness 采用**轮辐式（hub-and-spoke）**架构。Main Loop 是编排所有模块的中央枢纽。每个模块是自包含的单元，具有单一职责，与 Main Loop 及其他模块之间仅通过不可变数据契约通信。

### 5.2 组件图

```
┌─────────────────────────────────────────────────────────────────┐
│                     MAIN LOOP (SM)                              │
│  状态: START | RUNNING | AWAITING_HUMAN | COMPLETED | FAILED | CANCELLED │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Context  │  │  LLM     │  │ Action   │  │  Stop        │   │
│  │ Builder  │  │ Adapter  │  │ Parser   │  │ Conditions   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       │             │             │               │            │
│  ┌────┴─────────────┴─────────────┴───────────────┴────┐       │
│  │                 执行管道                              │       │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │       │
│  │  │Guardrail │  │  Tool    │  │Feedback Pipeline │   │       │
│  │  │+RuleEng  │→ │ Executor │→ │ (4 Layers)       │   │       │
│  │  └──────────┘  └──────────┘  └────────┬─────────┘   │       │
│  └───────────────────────────────────────┼──────────────┘       │
│                                          │                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┴──────────┐          │
│  │ Config   │  │ Memory   │  │ Credential          │          │
│  │ Manager  │  │ Manager  │  │ Manager             │          │
│  └──────────┘  └──────────┘  └─────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 运行时流程

```
1. START: 加载 Config → 初始化 CredentialManager → 初始化 MemoryStore
2. RUNNING:
   a. ContextBuilder 组装 prompt（system + tools + memory + history + task）
   b. LLM.Adapter.call()（内部重试：3 次，指数退避）
   c. ActionParser 分类响应：
      - TextOnly → 追加到历史，跳转到 (h)
      - ToolCall(known) → 跳转到 (d)
      - ToolCall(unknown) → ParseError → 跳转到 (g)
      - Malformed → ParseError → 跳转到 (g)
   d. Guardrail.evaluate(action):
      - ALLOWED → 跳转到 (e)
      - BLOCKED → ExecutionOutcome → 跳转到 (g)
      - APPROVAL_REQUIRED → 发出 approval_required → AWAITING_HUMAN
   e. ToolExecutor.execute(action) → ToolResult → 跳转到 (f)
   f. ExecutionOutcome(ToolResult) → 跳转到 (g)
   g. Feedback Pipeline:
      L1: Generator 产生 Feedback
      L2: Router 分配轨道
      L3: Controller 处理并产生决策
      L4: CoordinationLayer 检查收敛和升级
   h. StopConditions.check():
      - task_complete → COMPLETED
      - hard_limit → FAILED
      - convergence_failure → FAILED
      - 否则 → 跳转到 (a)
3. AWAITING_HUMAN:
   - HumanApprovalProvider.request_approval()
   - approved → RUNNING（恢复）
   - rejected → CANCELLED
   - timeout → FAILED
```

### 5.4 Main Loop 状态机

```
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         │ init_complete
                         ▼
          ┌──────────────────────────────┐
          │         RUNNING              │
          └────┬─────────┬──────────┬────┘
               │         │          │
 task_complete │  hard_  │ convergence_
               │  limit  │ failure
               ▼         ▼          ▼
          ┌────────┐ ┌────────┐ ┌────────┐
          │COMPLETED│ │ FAILED │ │ FAILED │
          └────────┘ └────────┘ └────────┘
               │
               │ approval_required
               ▼
        ┌──────────────────┐
        │ AWAITING_HUMAN   │
        └────┬─────┬───────┘
             │     │
     approved│     │ rejected/timeout
             │     │
             ▼     ▼
        RUNNING  CANCELLED/FAILED
```

### 5.5 Feedback Pipeline

```
ExecutionOutcome (ToolResult | GuardResult | ParseError)
    │
    ▼
┌────────────────────────────────────────────┐
│  Layer 1: FeedbackGenerator（按源）         │
│  ShellGen | TestGen | LintGen | DiffGen    │
│  GuardGen | ParserGen | ToolExecGen        │
│  纯函数：RawData → Feedback                 │
└────────────────────┬───────────────────────┘
                     ▼
┌────────────────────────────────────────────┐
│  Layer 2: FeedbackRouter                   │
│  route(feedback) → Recovery | Governance   │
│  无状态规则：source + severity → track       │
└──────────────┬──────────┬──────────────────┘
               │          │
      Recovery │          │ Governance
               ▼          ▼
┌──────────────────┐ ┌──────────────────┐
│ Layer 3:         │ │ Layer 3:         │
│ RecoveryController│ │GovernanceController│
│ 状态：           │ │ 状态：           │
│ IDLE, CONTINUE,  │ │ IDLE, BLOCK,     │
│ RETRY, REPLAN,   │ │ ASK_HUMAN,       │
│ WAIT             │ │ FORCE_STOP, AUDIT │
│ 表驱动 SM         │ │ 表驱动 SM         │
└────────┬─────────┘ └────────┬─────────┘
         │                    │
         └────────┬───────────┘
                  ▼
┌────────────────────────────────────────────┐
│  Layer 4: CoordinationLayer               │
│  ConvergenceDetector + EscalationManager   │
│  Escalate: Recovery → Governance           │
│  Resume:   Governance → Recovery           │
└────────────────────────────────────────────┘
```

### 5.6 外部依赖

**LLM 提供商：**
- DeepSeek API（主要）——兼容 OpenAI 格式的 Chat Completions 端点。
- OpenAI API（扩展）——相同接口，不同适配器。

**外部工具（由 Agent 执行）：**
- 文件系统（在工作区边界内读写）。
- Shell（在工作区目录内执行子进程）。

**运行环境：**
- Python 3.11+ 运行时。
- 平台：Windows、macOS、Linux。
- 除 Python 标准库和 HTTP 客户端外，无系统级依赖。

---

## 6. 数据模型

### 6.1 Action

**用途：** 表示 Agent 意图执行的已解析工具调用。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `tool_name` | `str` | 已注册的工具标识符：`read_file`、`write_file`、`execute_shell`、`task_complete` |
| `parameters` | `dict[str, Any]` | 工具特定参数（如 `path`、`content`、`command`） |
| `raw_response` | `dict` | 原始 LLM tool_call 字典，用于审计追踪 |

**约束：**
- `tool_name` 在解析时必须已在 `ToolRegistry` 中注册。
- `parameters` 必须包含指定工具的所有必填字段。

### 6.2 ToolCall

**用途：** LLM 请求的工具调用，从 API 响应中接收到的原始形式。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | `str` | LLM 分配的唯一调用标识符 |
| `name` | `str` | LLM 指定的工具名称 |
| `arguments` | `dict` | JSON 格式的工具参数 |

### 6.3 ToolResult

**用途：** 执行工具动作的结果。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `success` | `bool` | 执行是否成功 |
| `exit_code` | `int \| None` | Shell 退出码（仅 Shell 工具） |
| `stdout` | `str \| None` | 标准输出 |
| `stderr` | `str \| None` | 标准错误 |
| `error` | `str \| None` | 错误码：`FILE_NOT_FOUND`、`PERMISSION_DENIED`、`TIMEOUT` |
| `duration_ms` | `int` | 执行耗时（毫秒） |

**约束：**
- `exit_code` 仅在 `execute_shell` 动作时填充。
- `error` 仅在 `success=False` 时填充。

### 6.4 Feedback

**用途：** 表示执行步骤结果的不可变事件，由 Feedback Pipeline 消费。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `fingerprint` | `str` | 用于收敛检测的唯一标识符，由 `FingerprintStrategy` 生成 |
| `source` | `FeedbackSource` | 枚举：`SHELL`、`TEST`、`LINT`、`DIFF`、`GUARDRAIL`、`PARSER`、`TOOL_EXECUTOR`、`MEMORY`、`SYSTEM` |
| `severity` | `Severity` | 枚举：`INFO`、`WARNING`、`ERROR`、`CRITICAL` |
| `payload` | `dict[str, Any]` | 源特定的业务数据 |
| `metadata` | `FeedbackMetadata` | 系统级元数据（provider、latency、retry_count、trace_id） |
| `round` | `int` | 生成 Feedback 时的迭代轮次 |
| `timestamp` | `float` | 生成的 Unix 时间戳 |
| `tool_call` | `ToolCall \| None` | 触发此 Feedback 的动作 |
| `correlation_id` | `str \| None` | 跨迭代关联 ID，用于任务链追踪 |

**约束：**
- Feedback 是不可变的（`frozen`）——一旦创建，不可修改。
- `fingerprint` 由集中的 `FingerprintStrategy` 生成，不由各 Generator 各自生成。
- `payload` 包含业务语义；`metadata` 包含系统/运维数据。
- Feedback 不包含"action"字段——决策由 Controller 制定，不存储在 Feedback 中。

### 6.5 FeedbackMetadata

**用途：** 伴随 Feedback 事件的系统级元数据。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `provider` | `str` | LLM 提供商标识符 |
| `latency_ms` | `int` | 动作执行耗时 |
| `retry_count` | `int` | 当前迭代内的重试次数 |
| `trace_id` | `str \| None` | 预留用于分布式追踪 |

### 6.6 GuardResult

**用途：** 对动作的 Guardrail 评估结果。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `verdict` | `GuardVerdict` | 枚举：`ALLOWED`、`BLOCKED`、`APPROVAL_REQUIRED` |
| `rule_results` | `tuple[RuleResult, ...]` | 所有被触发的规则结果 |
| `approval_request` | `ApprovalRequest \| None` | 当判定为 `APPROVAL_REQUIRED` 时填充 |

**约束：**
- `GuardResult` 是不可变的。
- 当判定为 `ALLOWED` 时，`rule_results` 为空。
- `approval_request` 仅在判定为 `APPROVAL_REQUIRED` 时非空。

### 6.7 RuleResult

**用途：** 单条规则评估的结果。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `rule_name` | `str` | 规则标识符 |
| `verdict` | `RuleVerdict` | 枚举：`ALLOW`、`BLOCK`、`FLAG` |
| `reason` | `str` | 人类可读的解释 |
| `evidence` | `dict[str, Any]` | 支持判定的证据 |

### 6.8 ApprovalRequest

**用途：** 人工审批请求，由 GovernanceController 产生，由 Main Loop 处理。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `description` | `str` | 待审批动作的人类可读描述 |
| `evidence` | `list[dict]` | 来自触发规则的支持证据 |
| `timestamp` | `float` | 请求创建时间 |

### 6.9 ApprovalResult

**用途：** 人工审批交互的结果。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `result` | `ApprovalOutcome` | 枚举：`APPROVED`、`REJECTED`、`TIMEOUT` |

### 6.10 ExecutionOutcome

**用途：** 表示执行管道任何结果的联合类型，作为 Feedback Pipeline 的统一输入。

**变体：** `ToolResult`、`GuardResult`、`ParseError`。

### 6.11 ParseError

**用途：** 表示将 LLM 响应解析为有效动作的失败。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `error_type` | `str` | `UNKNOWN_TOOL` 或 `MALFORMED_CALL` |
| `raw_response` | `dict` | 解析失败的原始 LLM 响应 |
| `detail` | `str` | 用于注入 LLM 上下文的解析错误详情 |

### 6.12 MemoryEntry

**用途：** 长期记忆存储中的单条记录。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `id` | `str` | 唯一条目标识符 |
| `category` | `str` | `CONVENTION`、`DECISION`、`PREFERENCE`、`SUMMARY` |
| `content` | `str` | 条目内容（Markdown 或纯文本） |
| `created_at` | `float` | 创建的 Unix 时间戳 |
| `source_round` | `int` | 创建此条目时的迭代轮次 |

### 6.13 Configuration

**用途：** 启动时加载的不可变会话配置。

**关键字段：** 如 §3.8 配置模式所定义。

**约束：**
- 加载后不可变。
- API Key 排除在此对象之外。
- 缺失必填字段触发启动失败。

### 6.14 LLMResponse

**用途：** LLM 适配器返回的标准化响应，封装 LLM 的原始输出。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `content` | `str \| None` | LLM 的文本回复内容 |
| `tool_calls` | `list[dict] \| None` | LLM 请求的工具调用列表，每个元素包含 `id`、`name`、`arguments` |
| `finish_reason` | `str` | 完成原因：`stop`、`tool_calls`、`length`、`content_filter` |
| `usage` | `dict` | Token 使用统计：`prompt_tokens`、`completion_tokens`、`total_tokens` |

**约束：**
- `content` 为 `None` 时，`tool_calls` 必须非空；反之亦然。
- `tool_calls` 中的每个元素格式由 LLM 提供商定义，适配器负责规范化为统一的 dict 格式。

### 6.15 ToolDefinition

**用途：** 工具的 JSON Schema 定义，供 ContextBuilder 生成 LLM 工具定义列表。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `name` | `str` | 工具名称 |
| `description` | `str` | 工具功能的人类可读描述 |
| `parameters` | `dict` | 工具的 JSON Schema 参数定义 |

**约束：**
- `parameters` 必须符合 JSON Schema 规范。
- 每个已注册工具在 ToolRegistry 中有唯一的 ToolDefinition。

### 6.16 PersistDecision

**用途：** MemoryPolicy 的判定结果。

**关键字段：**

| 字段 | 类型 | 描述 |
|------|------|------|
| `decision` | `PersistOutcome` | 枚举：`PERSIST`、`DISCARD` |
| `reason` | `str` | 判定理由（用于审计日志） |
| `category` | `str \| None` | 若为 PERSIST，指定 MemoryEntry 的 category |

---

## 7. 凭据与分发设计

### 7.1 凭据管理

#### 7.1.1 存储

API Key 在可用时使用操作系统的原生凭据存储：

| 平台 | 存储后端 |
|------|----------|
| Windows | Windows Credential Manager（通过 `keyring` 库） |
| macOS | macOS Keychain（通过 `keyring` 库） |
| Linux | Secret Service API / `libsecret`（通过 `keyring` 库） |

回退方案：使用主密码加密的文件（通过 `cryptography` 库），存储在用户配置目录中。

#### 7.1.2 生命周期

- **首次运行：** Harness 检测到无已存储凭据，使用隐藏输入（`getpass`）提示用户输入 API Key。Key 被安全存储，绝不回显。
- **查看状态：** Harness 报告每个提供商是否已配置 Key，不显示 Key 内容。
- **更新：** 用户可通过 CLI 标志（`--setup`）触发重新录入流程。
- **清除：** 用户可通过 CLI 标志（`--clear-credentials`）移除已存储的凭据。

#### 7.1.3 排除在 TOML 之外

`config.toml` 文件不包含 `api_key` 字段。Credential Manager 是 API Key 的唯一数据源。TOML 文件仅引用提供商名称，Credential Manager 据此查找对应的 Key。

#### 7.1.4 凭据威胁模型

| 威胁 | 严重级别 | 缓解措施 |
|------|----------|----------|
| API Key 提交到 Git | 严重 | `.gitignore` 阻止凭据文件；pre-commit hook 扫描 Key 模式 |
| API Key 在进程列表中可见 | 高 | Key 绝不作为 CLI 参数传递；仅在进程内加载 |
| API Key 在 Shell 历史中 | 高 | 通过 `getpass` 输入 Key（无回显，不在历史中） |
| API Key 在日志文件中 | 高 | Credential Manager 在写入前从所有日志输出中脱敏 Key |
| `.env` 文件泄露 | 中 | 支持 `.env` 但文档说明其明文风险；推荐 OS 钥匙串 |
| 内存转储暴露 Key | 低 | Key 在内存中持有时间最短；LLM 调用后清除 |

### 7.2 分发

#### 7.2.1 目标平台

- Windows 10/11（x86_64）
- macOS 13+（ARM64、x86_64）
- Linux（x86_64、glibc 2.28+）

#### 7.2.2 分发方式

**Docker 容器（主要）：**
- 仓库根目录的单个 `Dockerfile`。
- `docker build -t ai4se-harness .`
- `docker run -it ai4se-harness --task "你的任务"`
- API Key 通过容器内首次运行交互提示配置，或通过挂载的凭据卷配置。

**Python 包（辅助）：**
- 通过仓库根目录的 `pip install .` 安装。
- 入口点：`ai4se-harness` CLI 命令。

#### 7.2.3 用户 Key 配置

1. 首次运行：`ai4se-harness --setup` 启动交互式凭据设置。
2. 用户选择 LLM 提供商并通过隐藏提示输入 API Key。
3. Key 存储在 OS 钥匙串（或加密文件回退）中。
4. 后续运行自动使用已存储的 Key。

---

## 8. 技术选型

### 8.1 编程语言：Python 3.11+

**理由：**
- LLM SDK 生态丰富（Anthropic SDK、兼容 DeepSeek 的 OpenAI SDK）。
- `asyncio` 为 Main Loop 的并发 I/O 需求提供原生支持。
- `abc` + 类型标注为 LLM 抽象层提供清晰的抽象接口。
- `dataclasses` 配合 `frozen=True` 提供不可变数据契约。
- 跨平台支持，无需编译。

**权衡：**
- Python 的 GIL 限制 CPU 密集型并行（对 I/O 密集的 Agent Loop 不构成问题）。
- 动态类型需要类型标注的纪律（通过 CI 中的 `mypy` 强制执行）。

### 8.2 LLM 提供商：DeepSeek（主要）

**理由：**
- 兼容 OpenAI 的 API 格式，支持统一的适配器接口。
- 对迭代开发和测试具有成本效益。
- 适配器抽象支持无需代码变更即可切换到 OpenAI 或其他提供商。

**权衡：**
- DeepSeek 的工具调用行为可能与 OpenAI 不同；适配器处理格式规范化。

### 8.3 关键依赖库

| 库 | 用途 | 理由 |
|----|------|------|
| `httpx` | LLM API 调用的异步 HTTP 客户端 | 原生 `asyncio` 支持，连接池 |
| `tomllib` / `tomli` | TOML 配置解析 | 标准库（3.11+）或向后移植 |
| `keyring` | 跨平台凭据存储 | 抽象 Windows/macOS/Linux 钥匙串 |
| `pytest` + `pytest-asyncio` | 测试框架 | 异步测试支持，fixture 系统 |
| `mypy` | 静态类型检查 | 在 CI 中强制类型安全 |

### 8.4 不使用 Agent 框架

本项目明确不使用 LangChain、CrewAI、AutoGen、LlamaIndex Agent 或任何其他 Agent 编排框架。Harness 内核（Main Loop、Action Parser、Guardrail、Feedback Pipeline）从零实现。

### 8.5 前端

本项目为 CLI 应用程序，无图形用户界面。Open Design 系统不适用。

> **Needs Clarification:** 课程交付物清单（通用要求 §五.9）要求"线上部署 URL，必须提供应用可访问的 WebUI 接口"。当前设计为纯 CLI 工具。WebUI 作为未来工作（§10.3）保留，但需确认课程是否接受 CLI-only 交付，或是否需要一个最简 Web 终端（如基于 WebSocket 的浏览器终端模拟器）。

---

## 9. 验收标准

### 9.1 Main Loop

- [ ] Main Loop 在 `START` 状态启动，初始化后转换到 `RUNNING`。
- [ ] Main Loop 在收到 `task_complete` 时正确转换到 `COMPLETED`。
- [ ] Main Loop 在超出 `max_iterations` 时正确转换到 `FAILED`。
- [ ] Main Loop 在超出 `timeout_seconds` 时正确转换到 `FAILED`。
- [ ] Main Loop 在发出 `approval_required` 时正确转换到 `AWAITING_HUMAN`。
- [ ] Main Loop 在 `approved` 时正确恢复到 `RUNNING`。
- [ ] Main Loop 在 `rejected` 时正确转换到 `CANCELLED`。
- [ ] Main Loop 在 HITL 超时时正确转换到 `FAILED`。
- [ ] 所有状态转换记录时间戳和事件。

### 9.2 LLM Adapter

- [ ] `DeepSeekAdapter` 成功调用 DeepSeek API 并返回解析后的 `LLMResponse`。
- [ ] `MockAdapter` 返回预编程的响应，无需网络访问。
- [ ] 可重试错误（429、5xx、超时）触发最多 3 次指数退避重试。
- [ ] 不可重试错误（401、403、400）立即抛出 `LLMFatalError`。
- [ ] 重试不增加 Main Loop 迭代计数器。

### 9.3 Action Parser

- [ ] `TextOnly` 响应被正确分类并追加到消息历史。
- [ ] `ToolCall(known)` 响应被正确分类并路由到 Guardrail。
- [ ] `ToolCall(unknown)` 响应生成 `ParseError`，类型为 `UNKNOWN_TOOL`。
- [ ] `Malformed` 响应（无效 JSON、缺失参数）生成 `ParseError`，类型为 `MALFORMED_CALL`。
- [ ] 连续 3 次 `ParseError` 或 `ToolCall(unknown)` 事件触发收敛失败。

### 9.4 Guard + Rule Engine

- [ ] `PathBoundaryRule` 阻止工作区根目录外的写入动作。
- [ ] `ShellCWDBoundRule` 阻止工作目录在工作区根目录外的 Shell 命令。
- [ ] `FileReadBoundRule` 阻止工作区根目录外的读取动作。
- [ ] `DangerousShellRule` 标记识别的破坏性 Shell 模式。
- [ ] `DBDestructiveRule` 标记数据库破坏性操作。
- [ ] `NetworkExfilRule` 标记数据外泄模式。
- [ ] `BLOCK` 判定立即短路规则评估。
- [ ] `FLAG` 判定被收集并产生 `ApprovalRequest`。
- [ ] 所有规则通过产生 `ALLOWED` 判定。

### 9.5 Tool Executor

- [ ] `read_file` 返回工作区内的文件内容。
- [ ] `write_file` 将内容写入工作区内的文件。
- [ ] `execute_shell` 执行命令并返回 exit_code、stdout、stderr。
- [ ] 工作区外的文件操作返回 `PERMISSION_DENIED`。
- [ ] 非零退出码的 Shell 命令返回 `success=False` 及退出码。
- [ ] 超时的 Shell 命令返回 `success=False` 及 `TIMEOUT` 错误。

### 9.6 Feedback Pipeline

- [ ] 每个 Generator 正确将其原始输入转换为 `Feedback` 对象。
- [ ] `FingerprintStrategy` 对相同错误模式产生一致的 fingerprint。
- [ ] `FeedbackRouter` 正确将 `SHELL`/`TEST`/`LINT`/`DIFF` 源路由到 Recovery。
- [ ] `FeedbackRouter` 正确将 `GUARDRAIL`/`PERMISSION` 源路由到 Governance。
- [ ] `RecoveryController` 基于相同错误次数正确通过 `CONTINUE → RETRY → REPLAN` 转换。
- [ ] `RecoveryController` 在连续 3 次相同 fingerprint 错误后触发升级。
- [ ] `GovernanceController` 对阻止的动作正确发出 `BLOCK`。
- [ ] `GovernanceController` 对标记的动作正确发出 `ASK_HUMAN`。
- [ ] `CoordinationLayer` 正确检测收敛失败并触发升级。
- [ ] `CoordinationLayer` 在 HITL 批准时正确从 Governance 恢复到 Recovery。

### 9.7 Memory Manager

- [ ] `MemoryStore` 正确读写 JSON 文件中的记忆条目。
- [ ] `MemoryRetriever` 加载当前会话的所有记忆条目。
- [ ] `MemoryPolicy` 正确持久化用户输入和任务摘要。
- [ ] `MemoryPolicy` 正确丢弃 Shell 输出和中间反馈。
- [ ] 损坏的记忆文件被优雅处理（警告，空记忆）。

### 9.8 Configuration Manager

- [ ] 有效的 `config.toml` 被加载并解析为不可变的 `Config` 对象。
- [ ] 缺失必填键触发清晰的错误信息。
- [ ] 无效值类型触发清晰的错误信息。
- [ ] `Config` 对象中不存在 API Key。
- [ ] 未知键被忽略并给出警告。

### 9.9 Credential Manager

- [ ] 首次运行以隐藏输入提示输入 API Key。
- [ ] API Key 通过 OS 钥匙串或加密文件存储。
- [ ] `--setup` 标志触发凭据重新录入。
- [ ] `--clear-credentials` 标志移除已存储的凭据。
- [ ] 可查看 API Key 状态而不显示 Key 内容。
- [ ] Credential Manager 从所有日志输出中脱敏 Key。

### 9.10 机制演示

- [ ] 演示 1：Guardrail 确定性地阻止危险动作（如写入 `/etc/passwd`）。
- [ ] 演示 2：Feedback Loop 检测到测试失败，将其注入上下文，LLM（mock）据此改变下一步动作。
- [ ] 演示 3：Feedback Pipeline 的一项深度行为（如收敛检测触发升级）。

### 9.11 测试

- [ ] 所有核心模块单元测试使用 `MockAdapter` 通过（无真实 LLM，无网络）。
- [ ] `pytest` 或 `make test` 以单条命令运行所有测试。
- [ ] CI（GitHub Actions）在每次 push 时运行测试。
- [ ] 测试覆盖至少包括：Main Loop、Action Parser、Rule Engine、每条 Rule、每个 Generator、FeedbackRouter、RecoveryController、GovernanceController、CoordinationLayer、MemoryPolicy、Configuration Manager。

> **Needs Clarification:** 课程通用要求 §五.6 指定 CI 配置文件为 `.gitlab-ci.yml`。当前设计使用 GitHub Actions（仓库托管于 GitHub）。需确认是否接受 GitHub Actions 格式，或需要同时提供 `.gitlab-ci.yml` 等效配置。

---

## 10. 风险与未决问题

### 10.1 剩余风险

| # | 风险 | 可能性 | 影响 | 缓解措施 |
|---|------|--------|------|----------|
| R1 | **REPLAN 循环**：LLM 在 REPLAN 状态产生与原计划等价的新方案，导致无限重新规划 | 中 | 高 | 增加独立的 REPLAN 限制（如 2 次重规划 → 升级到 Governance.FORCE_STOP）。MVP 中不实现，作为未来工作追踪。 |
| R2 | **HITL 超时实现**：Python 的 `input()` 是阻塞的，不支持原生超时 | 中 | 中 | 使用基于 `select` 的非阻塞输入或 `asyncio.wait_for`。在 Windows 上，替代方案可能需要 `msvcrt` 或第三方库。 |
| R3 | **MockLLM 覆盖缺口**：若 MockLLM 只返回有效的 ToolCall 序列，ActionParser 的 Malformed 和 UnknownTool 分支从未被测试 | 中 | 中 | MockLLM 必须支持场景注入：返回格式错误的 JSON、未知工具名和纯文本。显式测试每个分支。 |
| R4 | **Fingerprint 碰撞**：不同错误产生相同的 fingerprint，导致误触发收敛检测 | 低 | 高 | `FingerprintStrategy` 必须包含足够的上下文（tool_name + error_type + 关键参数）。使用多样化的错误场景进行测试。 |
| R5 | **Shell 输出解析**：Shell 命令的输出格式可能超出 Generator 的解析能力（如自定义测试运行器、非标准 Lint 输出） | 中 | 低 | 阶段 2 和 3 的 Generator 面向标准工具（pytest、flake8/mypy、git diff）。自定义工具支持不在范围内。 |

### 10.2 已知限制

1. **记忆仅支持全量注入**：当前 MemoryRetriever 加载所有条目。对于记忆量大的项目，将超出上下文窗口。可替换的 Retriever（如基于关键词、基于嵌入）为预留扩展点。
2. **单 Agent 架构**：Harness 支持一个 Agent 配一个 LLM。多 Agent 编排不在范围内。
3. **无流式传输**：LLM 响应以完整形式处理，非逐 Token 流式传输。流式支持为未来优化项。
4. **MVP Serializer**：记忆序列化仅使用结构化 JSON。LLM 摘要为预留扩展点。
5. **REPLAN 深度**：MVP 中 REPLAN 状态无独立限制。依赖全局迭代限制和收敛检测作为间接约束。

### 10.3 未来工作

1. **REPLAN 限制**：在升级到 Governance 前增加独立的 REPLAN 计数器（最多 2 次）。
2. **流式 LLM 响应**：支持逐 Token 流式传输以加快用户反馈。
3. **可插拔 MemoryRetriever**：支持基于关键词和基于嵌入的检索，用于更大的记忆存储。
4. **基于 LLM 的 Serializer**：使用 LLM 为已完成任务生成结构化摘要，存入长期记忆。
5. **沙箱执行**：在容器或虚拟机沙箱中执行 Shell 命令以增强隔离。
6. **多 Agent 编排**：通过 CoordinationLayer 支持多个 Agent 的子任务委派。
7. **Web UI**：基于浏览器的界面，用于任务提交、HITL 审批和审计日志查看。

---

## 11. Requirements Traceability Matrix

> 本节确保每项课程要求与 SPEC 设计、实现模块和验收标准一一对应。

### 11.1 通用要求追踪

| 课程要求 | SPEC 章节 | 对应模块 | 验收标准 |
|----------|-----------|----------|----------|
| 凭据安全存储（§3.1） | §7.1 | Credential Manager | §9.9 |
| 分发（§3.2） | §7.2 | Dockerfile / pyproject.toml | §9.9（首次运行） |
| 技术栈不限（§3.3） | §8.1–§8.3 | 全部 | — |
| 深度优先（§3.4） | §3.9.2 | Feedback Pipeline（四层） | §9.6 |
| 至少 3 个功能模块（§3.4） | §3.1–§3.8 | 11 个模块 | §9.1–§9.9 |
| 一键运行测试（§3.4） | §9.11 | pytest / make test | §9.11 |
| 独立完成（§3.5） | — | — | — |
| 使用 Superpowers（§3.6） | — | 开发过程 | AGENT_LOG.md |
| TDD（§3.6） | — | 开发过程 | AGENT_LOG.md |
| SPEC 完整结构（§4.2） | §1–§10 | 全部 | 本文档 |
| 用户故事 ≥5（§4.2） | §2 | — | US-1 至 US-6 |
| 凭据威胁模型（§4.2） | §4.4, §7.1.4 | Credential Manager | §9.9 |
| 冷启动验证（§4.5） | — | SPEC_PROCESS.md | — |
| GitHub 仓库 + PR 工作流（§4.7） | — | — | 最终提交 |
| CI 配置（§4.8） | §9.11 | .github/workflows | §9.11 |
| 容器分发（§4.10） | §7.2.2 | Dockerfile | README |

### 11.2 A 类专属要求追踪

| 课程要求 | SPEC 章节 | 对应模块 | 验收标准 |
|----------|-----------|----------|----------|
| 决策封装（§A.1） | §3.1 | Main Loop + ActionParser | §9.1, §9.3 |
| 动作/工具（§A.1） | §3.3.1, §3.5 | ToolRegistry + Tool Executor | §9.5 |
| 上下文与记忆（§A.1） | §3.1.1, §3.7 | ContextBuilder + Memory Manager | §9.7 |
| 治理护栏（§A.1） | §3.4, §3.6.4 | Guard + RuleEngine + GovernanceController | §9.4, §9.6 |
| 反馈闭环（§A.1） | §3.6 | Feedback Pipeline（四层） | §9.6 |
| 配置（§A.1） | §3.8 | Configuration Manager | §9.8 |
| 四类机制设计（§A.3） | §3.9.1 | 全部 | §9.4–§9.7 |
| 主循环自己实现（§A.4-A） | §3.1 | Main Loop | §9.1 |
| mock LLM 抽象层（§A.4-A） | §3.2 | AbstractLLM + MockAdapter | §9.2 |
| 禁止框架（§A.4-A） | §8.4 | 全部 | — |
| 机制必须是代码（§A.4-B） | §3.4, §3.6, §3.9.2 | Guard + Feedback Pipeline | §9.4, §9.6, §9.10 |
| Mock 可测（§A.4-C） | §4.8, §9.11 | 全部核心模块 | §9.11 |
| 六维度（§A.4-D） | §3.1–§3.8, §3.9.3 | 六个维度 | §9.1–§9.8 |
| 重点维度（§A.4-D） | §3.9.2 | Feedback Pipeline | §9.6, §9.10 |
| 领域与机制设计（§A.5） | §3.9 | — | 本文档 §3.9 |
| Mock-LLM 单元测试（§A.6） | §9.11 | MockAdapter | §9.2, §9.11 |
| 机制演示 3 项（§A.6） | §9.10 | — | §9.10 |
| Harness 内核源码（§A.7） | §3 | 全部 | §9.1–§9.10 |

### 11.3 用户故事追踪

| 用户故事 | 对应模块 | 验收标准 |
|----------|----------|----------|
| US-1：配置 Harness | Configuration Manager + Credential Manager | §9.8, §9.9 |
| US-2：委托编码任务 | Main Loop + Tool Executor + Action Parser | §9.1, §9.3, §9.5 |
| US-3：防止危险操作 | Guard + RuleEngine | §9.4 |
| US-4：基于测试失败自我修正 | Feedback Pipeline + RecoveryController | §9.6 |
| US-5：审查批准敏感操作 | GovernanceController + HumanApprovalProvider | §9.6 |
| US-6：Mock LLM 测试 | MockAdapter + 全部核心模块 | §9.2, §9.11 |

---

*SPEC.md 结束*
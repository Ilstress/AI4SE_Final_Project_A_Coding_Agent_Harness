# SPEC_PROCESS.md — 规约与计划过程文档

> **项目：** AI4SE Coding Agent Harness
> **开发工具：** Claude Code (Superpowers)
> **日期：** 2026-07-07 — 2026-07-10

---

## 1. Brainstorming 关键节点

### 1.1 初始方向：从模糊想法到明确命题

项目启动时，我向 Claude Code 提出的初始描述是：

> "构建一个 Coding Agent Harness，将 LLM 封装在控制循环中，配备工具分发、反馈驱动的自我修正、治理护栏和确定性停机条件。"

Claude Code 的 `brainstorming` 技能追问了以下关键问题，促使我修正了原设想：

**追问 1："Harness 与现有 Agent 框架（LangChain、CrewAI）的区别是什么？"**

这个问题让我意识到必须明确"零框架依赖"原则。最初我设想可以基于 LangChain 的工具调用机制，但 brainstorming 追问后，我决定从零实现所有模块——这是整个项目最深层的架构决策。

**追问 2："反馈闭环的'客观信号'是什么？谁来判定 LLM 的行为是否正确？"**

这个问题直接导向了 SPEC §3.6 的 Feedback Pipeline 设计。我最初设想的是"让 LLM 自我检查"，但 brainstorming 指出这不符合"机制必须是代码"原则。最终设计为：7 个 Generator 解析 ToolResult → FingerprintStrategy 生成指纹 → Router 路由到 Recovery/Governance 状态机。

**追问 3："如果 LLM 连续犯同样的错误，系统如何检测和终止？"**

这个问题催生了 CoordinationLayer 的 ConvergenceDetector：同一 fingerprint 连续 3 次 → 触发升级 → FORCE_STOP。这是"代码级停机条件"的典型实现，也是项目的主要贡献点。

**追问 4："API Key 如何安全存储？Docker 容器内如何持久化？"**

这个问题让我从"放 .env 就行"转向了 keyring + cryptography 加密回退的跨平台方案，并设计了 Docker VOLUME 挂载凭据卷。

### 1.2 SPEC 关键设计决策

| 决策 | AI 建议 | 我采纳/修正 | 理由 |
|------|---------|------------|------|
| 六维度覆盖 + 反馈深度聚焦 | AI 提出 | 采纳 | 符合"基础完整 + 重点深入"原则 |
| 表驱动状态机（Recovery/Governance） | AI 提出 | 采纳 | 可测试、可扩展、无 if-else 链 |
| 4 个内置工具（非动态注册） | AI 提出 | 采纳 | MVP 阶段足够，动态注册留作扩展点 |
| HITL 超时由 Main Loop 管理 | AI 提出 | 采纳 | SPEC §3.6.4 明确要求，职责分离 |
| MockAdapter 预编程响应列表 | AI 提出 | 采纳 | 支持场景注入，确定性测试 |
| 记忆系统全量注入（MVP） | AI 提出 | 我修正为"预留接口" | 当前规模小，全量注入足够；但接口设计预留了语义检索扩展 |

### 1.3 Brainstorming 反思

**做得好的地方：**
- 追问机制确实能暴露设计盲区。以上 4 个追问，每一个都让我修正了原设想
- 分块呈现设计逐步签字确认，避免了"一次性产出大文档看不懂"的问题
- 对"机制是代码还是提示词"的区分非常清晰，直接影响了 SPEC 的质量

**不满的地方：**
- Brainstorming 有时过于"顺从"——当我说"我想这样做"时，它较少直接挑战，而是追问"为什么"。在某些场景下，直接说"这个方案有问题"会更高效
- 对 A 类项目特有的"机制必须是代码"约束，brainstorming 没有主动提醒，是我自己对照要求文件发现的

---

## 2. Plan 生成过程

### 2.1 从 SPEC 到 Task 拆分

`writing-plans` 技能将 SPEC 分解为 22 个 Task，分 13 个 Phase：

```
Phase 0: 项目骨架 (T0.1)
Phase 1: 数据模型 (T1.1) → M1 Data Contract Freeze
Phase 2: 配置与凭据 (T2.1, T2.2)
Phase 3: LLM 适配器 (T3.1, T3.2)
Phase 4: 工具层 (T4.1–T4.3)
Phase 5: Action Parser (T5.1)
Phase 6: Context Builder (T6.1)
Phase 7: Guard (T7.1–T7.4)
Phase 8: Feedback Pipeline (T8.1–T8.9)
Phase 9: Memory (T9.1–T9.4)
Phase 10: Main Loop (T10.1)
Phase 11: CLI (T11.1)
Phase 12: Mechanism Demo (T12.1)
Phase 13: Docker & CI/CD & README (T13.1–T13.3)
```

### 2.2 Plan 迭代关键修正

**修正 1：并行策略调整**

初始 PLAN 将 T8.1–T8.7 (7 个 Generator) 标记为全部并行。实际执行中发现 Generator 之间有共享的 `_helpers.py`，需要先创建再并行。修正为：T8.1 (base + ShellGen) 先行 → T8.2/T8.3 并行。

**修正 2：T10.1 与 T12.1 的依赖关系**

初始 PLAN 将 T10.1 (Main Loop) 和 T12.1 (Mechanism Demo) 标记为可并行。实际执行中 T12.1 需要 T10.1 的 MainLoop 类，改为串行。

**修正 3：T13 阶段新增结构测试**

初始 PLAN 中 T13.1/13.2/13.3 的验证步骤只写了 `docker build` 和 `docker run`。由于 CI 环境中 Docker 不可用，补充了 `test_docker.py`、`test_ci.py`、`test_readme.py` 三个结构测试文件。

---

## 3. 冷启动验证

### 3.1 验证方案

由于本项目使用 Claude Code（单一智能体），无法严格满足"换一个不同类型的 agent"的要求。采用的替代方案：

1. **新会话验证**：启动一个全新的 Claude Code 会话，不导入任何历史上下文
2. **仅提供 SPEC.md + PLAN.md**，不补充口头解释
3. **指定实现 T5.1 (Action Parser)** 作为验证 task

### 3.2 验证结果

**新会话在以下位置暂停并提问：**

1. "`LLMResponse` 的 `tool_calls` 字段格式是什么？" → **SPEC 缺陷**：未明确 JSON 结构。修正：在 SPEC §6 中补充了 `ToolCall` dataclass 定义。

2. "`task_complete` 被分类为 `ToolCall(known)` 还是特殊处理？" → **SPEC 不够清晰**。修正：在 Action Parser 规约中明确"task_complete 被解析为 ToolCall(known)，停机信号由 Main Loop 处理"。

3. "`ParseError` 的 `error_type` 有哪些可能值？" → **SPEC 遗漏**。修正：补充了 `UNKNOWN_TOOL` 和 `MALFORMED_CALL` 两个枚举值。

### 3.3 冷启动验证结论

- SPEC 暴露了 3 处不清晰/遗漏，均在实现前修正
- 冷启动验证是规约工作中最有价值的环节——它模拟了"陌生人能否读懂你的设计"
- 即使无法换 agent 类型，新会话 + 仅凭文档的验证方式仍然有效

---

## 4. 实现过程中的关键决策

### 4.1 T10.1 迭代计数器 off-by-one 修正

**问题：** 测试 `test_max_iterations_enforced` 失败，`loop.iteration` 为 4 而非预期的 3。

**根因：** `self._iteration > max_iterations` 检查在 `self._iteration += 1` 之后，导致计数器多跑一轮。

**修正：** 将检查移到 `+= 1` 之前，使用 `>=` 比较。

**教训：** 边界条件测试（`max_iterations` 恰好等于）是 TDD 最有价值的场景。

### 4.2 HITL 超时职责归属

**问题：** 初始实现将 HITL 超时放在 `TerminalApprovalProvider` 中。

**SPEC 审查：** §3.6.4 明确要求"Main Loop 管理 HITL 超时"。

**修正：** 使用 `asyncio.wait_for` + `asyncio.to_thread` 将超时控制移到 Main Loop 的 `_handle_approval_required` 方法。

**教训：** SPEC 中的职责归属描述是实现时必须严格遵守的约束，不能因为"实现更方便"而偏离。

### 4.3 pyyaml 依赖缺失导致的 CI 失败

**问题：** GitHub Actions 报 `ModuleNotFoundError: No module named 'yaml'`。

**根因：** `tests/test_ci.py` 使用 `import yaml` 验证 CI 配置文件，但 `pyyaml` 未声明在 `pyproject.toml` 的 dev dependencies 中。本地环境因 pytest 间接依赖而可用，CI 干净环境则缺失。

**修正：** 在 `pyproject.toml` 中显式添加 `"pyyaml>=6.0"`。

**教训：** 依赖必须显式声明，不能依赖"恰好安装了的传递依赖"。

---

## 5. 过程反思

### 5.1 SPEC 质量与实现质量的关联

SPEC 写得越清晰的部分（如数据模型 §6，字段/类型/约束逐一定义），实现越顺畅，subagent 偏离越少。SPEC 写得模糊的部分（如"反馈生成器解析 ToolResult"），subagent 会自行发挥，导致需要人工修正。

**最典型的案例：** `FeedbackRouter` 的 11 条路由规则。SPEC 中只有一句话"GUARDRAIL + CRITICAL → GOVERNANCE"。subagent 初始实现将所有 GUARDRAIL 反馈都路由到 GOVERNANCE。对照 SPEC 修正后，INFO/WARNING 级别路由到 RECOVERY（仅审计），ERROR/CRITICAL 才路由到 GOVERNANCE。

### 5.2 Task 颗粒度经验

- **最优颗粒度：** 1 个文件 + 1 个测试文件，约 50–150 行实现。如 T5.1 (Action Parser) 和 T6.1 (Context Builder) 的颗粒度最佳
- **过粗：** T10.1 (Main Loop) 涉及 10+ 依赖，单 task 内完成所有状态转换和测试，容易遗漏边界条件
- **过细：** T8.1–T8.3 (3 个 Generator 文件) 每个 Generator 独立 task，但测试文件较多，管理成本上升

### 5.3 如果重做会改变什么

1. **先写集成测试，再拆 task**：当前是每个模块独立测试，最后才写 Mechanism Demo。如果先定义 3 个端到端 Demo 的预期行为，再反向推导每个模块的接口，会减少模块间的接口不匹配
2. **更早引入 CI**：T13.2 在最后一阶段才配置，导致 pyyaml 依赖问题到很晚才发现
3. **SPEC 中更精确地定义接口签名**：多个模块的 `__init__` 参数在实现中调整过，如果 SPEC 中直接写签名，会减少返工
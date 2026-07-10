# AGENT_LOG.md — 开发日志

> **项目：** AI4SE Coding Agent Harness
> **开发工具：** Claude Code (Superpowers)
> **方法：** Spec-Driven, Subagent-Built, Human-Owned — TDD 红→绿→重构

---

## 2026-07-07 — Phase 0 启动

### 15:12 | T0.1 启动 | `brainstorming` → `writing-plans`

- **触发技能：** `brainstorming` 生成 SPEC.md，`writing-plans` 生成 PLAN.md
- **关键 prompt：** "构建一个 Coding Agent Harness，将 LLM 封装在控制循环中，配备工具分发、反馈驱动的自我修正、治理护栏和确定性停机条件。零框架依赖，深度聚焦反馈闭环。"
- **输出：** SPEC.md (架构已冻结) + PLAN.md (22 Task, 13 Phase)
- **人工干预：** 确认六维度覆盖 + 反馈深度聚焦的设计方向；确认"机制必须是代码"原则写入 SPEC
- **教训：** Brainstorming 阶段的追问质量决定了 SPEC 的完整度。在"反馈闭环"和"危险动作拦截"两个点上，AI 追问了 4 轮才产出满意设计。

### 15:23 | T0.1 完成 | `subagent-driven-development`

- **Commit:** `46df730` — test
- **产出：** `pyproject.toml`、`Makefile`、`harness/__init__.py`、`tests/__init__.py`、`tests/conftest.py`、`config.toml`
- **验证：** `pip install -e .` 成功，`make test` 可运行（0 tests）
- **人工干预：** 无

---

## 2026-07-08 — Phase 1–7 核心模块

### 10:35 | T1.1 数据模型 | `subagent-driven-development`

- **Commit:** `7bd062f` — test
- **产出：** 16 个 dataclass + 6 个 Enum，`tests/test_models.py` (58 tests)
- **关键决策：** 全部使用 `frozen=True` 确保不可变性
- **人工干预：** 确认 `Config` 使用 `@dataclass(frozen=True)` 而非 pydantic，保持零框架依赖

### 14:16 | T0.1 补充 | `subagent-driven-development`

- **Commit:** `ee09163` — feat(T0.1): initialize project skeleton
- **产出：** 补充项目骨架文件
- **人工干预：** 无

### 19:20 | T2.1–T9.4 批量推进 | `subagent-driven-development`

- **Commit:** `e0d6dea` — task
- **产出：** Config Manager、Credential Manager、LLM Adapters (DeepSeek/OpenAI/Mock)、Tool Registry + Executor + 4 Handlers、Action Parser、Context Builder、Guard (6 Rules + RuleEngine + Guardrail + HITL)、Feedback Pipeline (7 Generators + Router + RecoveryController + GovernanceController + CoordinationLayer)、Memory (Store + Retriever + Policy + Serializer)
- **关键决策：**
  - MockAdapter 接受预设响应列表，支持场景注入（TextOnly/ToolCall/Malformed/UnknownTool）
  - RecoveryController 和 GovernanceController 均使用表驱动状态机（数据结构定义转换规则，无 if-else 链）
  - 7 个 Generator 共享 `_helpers.py` 提取公共逻辑
- **人工干预：**
  - 修正 `FeedbackRouter` 的 GUARDRAIL 路由规则：INFO/WARNING → RECOVERY（仅审计），ERROR/CRITICAL → GOVERNANCE
  - 修正 `MemoryPolicy` 的确定性规则：USER_INPUT → PERSIST，SHELL/TEST → DISCARD

### 23:27 | T10.1 Main Loop | `subagent-driven-development`

- **Commit:** `4ed2c5d` — test
- **产出：** `harness/loop/main_loop.py` — 6 状态事件驱动状态机 + `tests/test_main_loop.py`
- **关键决策：** 表驱动状态转换 `_TRANSITIONS: list[tuple[LoopState, LoopEvent, LoopState]]`
- **人工干预：**
  - **修正 1：迭代计数器 off-by-one。** `self._iteration > max_iterations` 检查在 `+= 1` 之后，导致多跑一轮。修正为在 `+= 1` 之前检查 `>=`。
  - **修正 2：用户任务未写入 message_history。** `_reset()` 中补充 `[{"role": "user", "content": task}]`。
  - **修正 3：HITL 超时职责。** 初始实现放在 TerminalApprovalProvider 中，对照 SPEC §3.6.4 修正为 `asyncio.wait_for` + `asyncio.to_thread` 在 Main Loop 中管理超时。
  - **修正 4：`timeout_seconds` 类型。** 从 `int` 改为 `float`，支持微秒级超时测试。
- **教训：** 边界条件测试（max_iterations=0、timeout=0.000001）是 TDD 最有价值的场景，暴露了 3 个 bug。

---

## 2026-07-09 — Phase 11–13 收尾

### 15:04 | T11.1 CLI + T12.1 Mechanism Demo | `subagent-driven-development`

- **Commit:** `d1e1e7d` — test
- **产出：**
  - `harness/cli/main.py` — argparse CLI，Composition Root 模式，13 个依赖注入
  - `tests/test_cli.py` (12 tests)
  - `tests/test_mechanism_demo.py` (9 tests, 4 demos)
- **关键决策：** CLI 纯 Composition Root，零业务逻辑泄漏。`_handle_run` 仅做：Config → DI → MainLoop.run() → Exit Code
- **人工干预：**
  - CLI 审查：确认 `_handle_run` 中无 Tool 执行、Guardrail 判断、MainLoop 状态转移、ActionParser 解析、Feedback 生成逻辑
  - 补充 Demo 4：End-to-End 完整链路测试（read_file → write_file → execute_shell → task_complete）

### 17:56 | T13.1–T13.3 Docker / CI / README | `subagent-driven-development`

- **Commit:** `b68f3b7` — test
- **产出：**
  - `Dockerfile` — 多阶段构建 (python:3.11-slim) + `.dockerignore`
  - `.github/workflows/unit-test.yml` + `.gitlab-ci.yml`
  - `README.md` — 10 个必需要素
  - `tests/test_docker.py` (16 tests) + `tests/test_ci.py` (13 tests) + `tests/test_readme.py` (13 tests)
- **关键决策：**
  - Docker 不可用，采用结构测试验证 Dockerfile 内容
  - 同时提供 GitHub Actions 和 GitLab CI 配置（通用要求 §五.6 要求 `.gitlab-ci.yml`）
  - README 命令与 CI 工作流保持一致（`pip install -e ".[dev]"` + `make test`）
- **人工干预：**
  - **修正 1：pyyaml 依赖缺失。** `tests/test_ci.py` 使用 `import yaml` 但 `pyyaml` 未在 dev dependencies 中声明。本地 pytest 间接依赖，CI 干净环境缺失。修正：在 `pyproject.toml` 中添加 `"pyyaml>=6.0"`。
  - **修正 2：mypy `import-untyped` 错误。** 第二个 `import yaml` 的 `# type: ignore[import-untyped]` 被标记为 unused。修正：保留第一个 import 的 ignore，移除第二个的 ignore。
  - **修正 3：ruff 修复。** `test_ci.py` 和 `test_readme.py` 的 trailing newline、unused import `os`、ambiguous variable name `l` → 均已修复。

---

## 最终交付 (2026-07-10)

### 最终验证

- **测试：** 590/590 通过
- **mypy：** 0 errors (119 source files, strict mode)
- **ruff：** 0 errors
- **SPEC 一致性：** 15/15 验收标准通过
- **PLAN 完成度：** 22/22 Task ✅

### 最终交付物

- `FINAL_REPORT.md` — 项目最终报告
- `CHANGELOG.md` — v1.0.0 变更日志
- `SPEC_PROCESS.md` — 过程文档
- `AGENT_LOG.md` — 本文件

---

## 技能使用统计

| 技能 | 使用次数 | 关键产出 |
|------|---------|---------|
| `brainstorming` | 1 | SPEC.md 设计 |
| `writing-plans` | 1 | PLAN.md 22 Task |
| `subagent-driven-development` | 22 | 每个 Task 的实现 |
| `test-driven-development` | 22 | 每个 Task 的测试 |
| `requesting-code-review` | 3 | T10.1 审查、T11.1 审查、T12.1 审查 |
| `finishing-a-development-branch` | 1 | v1.0.0 最终交付 |

## 人工干预统计

| 类型 | 次数 | 典型案例 |
|------|------|---------|
| SPEC 修正 | 3 | 冷启动验证暴露的 3 处不清晰 |
| 架构修正 | 2 | HITL 超时职责、迭代计数器 |
| Bug 修复 | 4 | off-by-one、message_history、timeout 类型、pyyaml 依赖 |
| 测试补充 | 2 | Demo 4 E2E、结构测试 |
| 代码质量 | 3 | ruff trailing newline、mypy ignore、unused import |

## 核心教训

1. **SPEC 是 subagent 不偏离的唯一保障。** SPEC 模糊的地方，subagent 必然自行发挥。冷启动验证是发现 SPEC 缺陷的最有效手段。
2. **TDD 在 AI 协作下是放大器而非阻碍。** 先写测试迫使你思考接口，减少 AI 生成的代码与预期不符的概率。
3. **依赖必须显式声明。** pyyaml 问题暴露了"传递依赖不可靠"这一通用工程原则在 AI 协作中同样适用。
4. **Composition Root 模式的审查价值。** CLI 审查（确认无业务逻辑泄漏）是最有效的架构验证方式。
5. **结构测试是对不可用工具的有效替代。** Docker 不可用时，验证 Dockerfile 内容的结构测试保证了交付物质量。
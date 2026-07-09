# CHANGELOG

## v1.0.0 (2026-07-09)

### 项目概述

AI4SE Coding Agent Harness 首个完整版本。从零构建的编码智能体内核，将 LLM 封装在控制循环中，配备工具分发、反馈驱动的自我修正、治理护栏和确定性停机条件。

### 架构

- **6 状态事件驱动 Main Loop**：START → RUNNING → AWAITING_HUMAN → COMPLETED / FAILED / CANCELLED
- **四层 Feedback Pipeline**：Generator → FingerprintStrategy → Router → Controller → CoordinationLayer
- **表驱动状态机**：RecoveryController（5 状态 / 8 转换）和 GovernanceController（5 状态 / 6 转换）
- **12 模块 Composition Root**：CLI 纯依赖注入，零业务逻辑泄漏

### 新增功能

#### 核心模块

| 模块 | 内容 |
|------|------|
| **Models** (T1.1) | 16 个不可变 dataclass + 6 个 Enum，完整数据契约 |
| **Config Manager** (T2.1) | TOML 配置加载，验证必填字段，生成不可变 Config |
| **Credential Manager** (T2.2) | 跨平台 keyring 安全存储 + cryptography 加密回退 |
| **LLM Adapters** (T3.1, T3.2) | AbstractLLM + DeepSeekAdapter + OpenAIAdapter + MockAdapter |
| **Tools** (T4.1–T4.3) | ToolRegistry + ToolExecutor + 4 个内置 Handler |
| **Action Parser** (T5.1) | 四分类解析器（TextOnly / ToolCall(known) / ToolCall(unknown) / Malformed） |
| **Context Builder** (T6.1) | 纯函数上下文组装器 |
| **Guard** (T7.1–T7.4) | RuleEngine + 6 条内置规则 + Guardrail + HITL 审批 |
| **Feedback Pipeline** (T8.1–T8.9) | 7 个 Generator + Router + RecoveryController + GovernanceController + CoordinationLayer |
| **Memory** (T9.1–T9.4) | MemoryStore + MemoryRetriever + MemoryPolicy + Serializer |
| **Main Loop** (T10.1) | 6 状态事件驱动状态机，编排所有模块 |
| **CLI** (T11.1) | argparse CLI，Composition Root 模式 |
| **Mechanism Demo** (T12.1) | 3 项确定性机制演示（Guardrail / Feedback Loop / Convergence） |

#### 基础设施

| 模块 | 内容 |
|------|------|
| **Docker** (T13.1) | 多阶段构建（python:3.11-slim），凭据卷持久化 |
| **CI/CD** (T13.2) | GitHub Actions + GitLab CI，push 触发 unit-test job |
| **README** (T13.3) | 完整项目文档，10 个必需要素 |

### 测试

- **590 个测试**，全部使用 MockAdapter（无真实 LLM，无网络）
- 覆盖所有核心模块：Main Loop、Action Parser、Rule Engine、6 条 Rule、7 个 Generator、FeedbackRouter、RecoveryController、GovernanceController、CoordinationLayer、MemoryPolicy、Configuration Manager
- 3 项机制演示（SPEC §9.10）
- 结构测试：Dockerfile、CI 配置、README

### 工具链

- **Python 3.11+**，零 Agent 编排框架依赖
- **mypy strict mode**：0 类型错误
- **ruff**：0 lint 错误
- **TDD**：红 → 绿 → 重构，所有模块先测试后实现

### 已知限制

- 记忆系统为全量注入（MVP），不支持语义检索
- 仅内置 4 个工具，不支持动态注册
- 单任务执行，不支持并行 Agent
- 工作区隔离为路径前缀匹配，非容器级沙箱
- `NetworkExfilRule` 基于模式匹配，可被绕过
- 未经安全审计或渗透测试

### 交付物

- `harness/` — 内核源码（80 个 Python 文件，~4,375 行）
- `tests/` — 测试套件（39 个 Python 文件，~7,839 行）
- `Dockerfile` — 多阶段构建
- `.github/workflows/unit-test.yml` — GitHub Actions CI
- `.gitlab-ci.yml` — GitLab CI 等效配置
- `README.md` — 完整项目文档
- `SPEC.md` — 设计文档（架构已冻结）
- `PLAN.md` — 实现计划（22 个 Task，全部完成）
- `config.toml` — 默认配置模板
- `pyproject.toml` — 项目元数据与依赖
- `Makefile` — 开发命令
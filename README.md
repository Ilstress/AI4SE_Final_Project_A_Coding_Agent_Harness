# AI4SE Coding Agent Harness

> **Agent = LLM + Harness** — 一个将 LLM 封装在控制循环中的软件内核，配备工具分发、反馈驱动的自我修正、治理护栏和确定性停机条件。

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://github.com/Ilstress/AI4SE_Final_Project_A_Coding_Agent_Harness/actions/workflows/unit-test.yml/badge.svg)](https://github.com/Ilstress/AI4SE_Final_Project_A_Coding_Agent_Harness/actions/workflows/unit-test.yml)

---

## 项目简介

**AI4SE Coding Agent Harness** 是一个从零构建的编码智能体内核。它不依赖 LangChain、CrewAI、AutoGen 等 Agent 编排框架，而是直接实现 Agent 运行时的每一层：LLM 适配、工具调用、护栏检查、反馈闭环、停机条件。

**核心等式：** LLM 是"CPU"——它只负责决定下一步做什么。其余所有（治理、反馈、工具执行、记忆、配置）都是工程。

**目标用户：** 希望将编码任务委托给 LLM 驱动的 Agent，同时保留对安全边界、执行限制和修正循环的确定性控制权的软件开发者。

### 设计原则

1. **零框架依赖** — 内核中不使用任何 Agent 编排框架
2. **代码级机制，非提示词** — 所有反馈信号、护栏和停机条件均为确定性代码
3. **Mock 可测内核** — 每个核心机制可用 mock LLM 在确定性单元测试中验证
4. **深度聚焦反馈闭环** — 四层 Feedback Pipeline + 表驱动状态机
5. **最小可行覆盖** — 六个维度（决策/工具/记忆/治理/反馈/配置）均具备可运行的最低实现

---

## 核心架构

```
                          ┌──────────────────────────┐
                          │        CLI (main.py)       │
                          │   argv → Config → DI → Run │
                          └────────────┬─────────────┘
                                       │
                          ┌────────────▼─────────────┐
                          │       Main Loop            │
                          │   6-state event-driven SM   │
                          └────────────┬─────────────┘
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
┌─────────▼─────────┐    ┌─────────────▼─────────────┐    ┌────────▼─────────┐
│   Context Builder  │    │       LLM Adapter          │    │   Tool Executor   │
│  组装 messages[]   │    │  DeepSeek / OpenAI / Mock  │    │ read/write/shell  │
└─────────┬─────────┘    └─────────────┬─────────────┘    │   task_complete   │
          │                            │                   └────────┬─────────┘
          │                   ┌────────▼─────────┐                  │
          │                   │   Action Parser   │                  │
          │                   │  4-class dispatch │                  │
          │                   └────────┬─────────┘                  │
          │                            │                            │
          │                   ┌────────▼─────────┐                  │
          │                   │     Guardrail     │                  │
          │                   │ RuleEngine + HITL │──────────────────┘
          │                   └────────┬─────────┘
          │                            │
          │                   ┌────────▼─────────┐
          │                   │ Feedback Pipeline │
          │                   │  4-layer pipeline  │
          │                   │  Generator→Router  │
          │                   │  →Controller→Coord │
          │                   └────────┬─────────┘
          │                            │
          └────────────────────────────┘
                                       │
                          ┌────────────▼─────────────┐
                          │      Memory Manager       │
                          │  Store / Retrieve / Policy │
                          └──────────────────────────┘
```

### 模块关系

| 模块 | 路径 | 职责 |
|------|------|------|
| **Models** | `harness/models/` | 16 个不可变 dataclass + 6 个 Enum，数据契约 |
| **Config** | `harness/config/` | TOML 配置加载，生成不可变 Config 对象 |
| **Credentials** | `harness/credentials/` | 跨平台 API Key 安全存储（keyring + 加密回退） |
| **LLM** | `harness/llm/` | AbstractLLM + DeepSeek/OpenAI/Mock 适配器 |
| **Tools** | `harness/tools/` | ToolRegistry + ToolExecutor + 4 个内置 Handler |
| **Parser** | `harness/parser/` | LLM 响应四分类解析器（TextOnly/Action/ParseError） |
| **Context** | `harness/context/` | 纯函数上下文组装器 |
| **Guard** | `harness/guard/` | RuleEngine + 6 条内置规则 + Guardrail + HITL |
| **Feedback** | `harness/feedback/` | 四层管道：Generator → Router → Controller → Coordination |
| **Memory** | `harness/memory/` | 文件存储 + 全量检索 + 确定性持久化策略 |
| **Loop** | `harness/loop/` | 6 状态事件驱动 Main Loop 状态机 |
| **CLI** | `harness/cli/` | argparse CLI，纯 Composition Root |

---

## 安装与快速开始

### 环境要求

- Python 3.11+
- pip 20.0+
- 支持的平台：Windows 10/11、macOS 13+、Linux (x86_64, glibc 2.28+)

### 安装

```bash
# 克隆仓库
git clone https://github.com/Ilstress/AI4SE_Final_Project_A_Coding_Agent_Harness.git
cd AI4SE_Final_Project_A_Coding_Agent_Harness

# 安装项目及开发依赖
pip install -e ".[dev]"
```

### 快速开始

```bash
# 1. 配置 API Key（首次运行必须）
ai4se-harness --setup

# 2. 编辑 config.toml，设置工作区路径
#    将 [workspace] root 改为你的项目绝对路径

# 3. 运行一个任务
ai4se-harness run --task "Create a hello.py file that prints 'Hello, World!'"

# 4. 查看帮助
ai4se-harness --help
```

---

## API Key 配置

### 安全存储

本项目使用 **keyring** 库进行跨平台凭据安全存储，不回显明文，不写入配置文件。

| 平台 | 存储后端 |
|------|----------|
| Windows | Windows Credential Manager |
| macOS | Keychain |
| Linux | Secret Service (D-Bus) / 加密文件回退 |

### 凭据管理命令

```bash
ai4se-harness --setup              # 交互式配置 API Key（隐藏输入）
ai4se-harness --clear-credentials  # 清除已存储的凭据
```

### 威胁模型

- **API Key 绝不**：硬编码进源码、提交 Git、写入日志、出现在终端历史
- **存储**：OS 钥匙串 + `cryptography` 加密文件回退
- **脱敏**：所有日志输出前自动脱敏 Key（`sk-...` → `***`）
- **内存**：Key 在 LLM 调用后立即清除，持有时间最短

### 支持的 LLM 提供商

| 提供商 | config.toml 配置 |
|--------|-----------------|
| DeepSeek | `provider = "deepseek"`, `model = "deepseek-chat"` |
| OpenAI | `provider = "openai"`, `model = "gpt-4o"` |

---

## Docker 使用方式

### 构建镜像

```bash
docker build -t ai4se-harness .
```

### 运行

```bash
# 交互式运行（首次需配置 Key）
docker run -it ai4se-harness --setup

# 执行任务（使用默认配置）
docker run -it ai4se-harness run --task "Write a function to sort a list"

# 使用自定义配置
docker run -it -v ./config.toml:/etc/ai4se-harness/config.toml ai4se-harness run --task "..."

# 持久化凭据卷
docker run -it -v ai4se-credentials:/root/.local/share/ai4se-harness ai4se-harness --setup
```

### 镜像说明

- 基础镜像：`python:3.11-slim`
- 多阶段构建（builder + runtime），最小化镜像体积
- 入口点：`ai4se-harness`
- 凭据卷：`/root/.local/share/ai4se-harness`

---

## 测试与 CI

### 运行测试

```bash
# 一键运行全部测试
make test

# 或直接使用 pytest
pytest -v

# 仅运行单元测试（不含集成测试）
pytest -v --ignore=tests/test_mechanism_demo.py
```

### 代码质量

```bash
make lint       # ruff 检查
make typecheck  # mypy 类型检查
```

### CI/CD

**GitHub Actions**（`.github/workflows/unit-test.yml`）：

- 触发：push 到任意分支
- Job：`unit-test`（ubuntu-latest, Python 3.11）
- 步骤：Checkout → Setup Python → Install deps → `make test`

**GitLab CI**（`.gitlab-ci.yml`）：

- 等效配置，`unit-test` job，`python:3.11-slim` 镜像

### 测试设计

- **577 个测试**覆盖所有核心模块
- 全部使用 `MockAdapter`（无真实 LLM，无网络请求）
- 每个模块遵循 TDD 开发（红 → 绿 → 重构）

---

## 项目目录说明

```
ai4se-harness/
├── harness/                     # 内核源码
│   ├── models/                  # 16 个不可变数据契约
│   ├── config/                  # TOML 配置管理器
│   ├── credentials/             # 凭据安全存储
│   ├── llm/                     # LLM 抽象层 + 适配器
│   ├── tools/                   # 工具注册表 + 执行器 + Handler
│   │   └── handlers/            # read_file, write_file, execute_shell, task_complete
│   ├── parser/                  # LLM 响应四分类解析器
│   ├── context/                 # 上下文组装器
│   ├── guard/                   # 护栏系统
│   │   ├── rules/               # 6 条内置规则
│   │   └── approval/            # HITL 审批（Terminal + Mock）
│   ├── feedback/                # 反馈管道
│   │   ├── generators/          # 7 个反馈生成器
│   │   └── controllers/         # Recovery + Governance 状态机
│   ├── memory/                  # 记忆管理器
│   ├── loop/                    # Main Loop 状态机
│   └── cli/                     # CLI 入口（Composition Root）
├── tests/                       # 测试套件
│   ├── test_rules/              # 6 条规则独立测试
│   ├── test_mechanism_demo.py   # 三项机制演示
│   ├── test_main_loop.py        # Main Loop 状态机测试
│   ├── test_cli.py              # CLI 测试
│   ├── test_docker.py           # Dockerfile 结构测试
│   ├── test_ci.py               # CI 配置结构测试
│   └── test_readme.py           # README 结构测试
├── config.toml                  # 默认配置模板
├── Dockerfile                   # 多阶段 Docker 构建
├── Makefile                     # 开发命令
├── pyproject.toml               # 项目元数据 + 依赖
├── .dockerignore                # Docker 构建排除
├── .github/workflows/           # GitHub Actions CI
├── .gitlab-ci.yml               # GitLab CI 等效配置
└── PLAN.md / SPEC.md            # 设计文档
```

---

## 安全边界

### Guardrail 规则

| 规则 | 优先级 | 行为 |
|------|--------|------|
| PathBoundaryRule | 100 | 文件写入必须在工作区内 → BLOCK |
| ShellCWDBoundRule | 100 | Shell 工作目录必须在工作区内 → BLOCK |
| FileReadBoundRule | 100 | 文件读取必须在工作区内 → BLOCK |
| DangerousShellRule | 200 | 检测 `rm -rf`、fork bomb 等 → FLAG (HITL) |
| DBDestructiveRule | 200 | 检测 `DROP TABLE`、`DELETE FROM` 等 → FLAG (HITL) |
| NetworkExfilRule | 200 | 检测 `curl \| sh`、数据外泄等 → FLAG (HITL) |

### 安全设计要点

- **所有动作（含 read_file、task_complete）经过 Guardrail 检查**
- **优先级 100 规则**：确定性阻止（BLOCK），无需人工审批
- **优先级 200 规则**：产生 FLAG，触发 HITL 审批（Terminal 交互）
- **HITL 超时**：120 秒内无响应 → 自动 FAILED（安全优先）
- **收敛检测**：同一错误连续 3 次 → 触发 FORCE_STOP
- **异常处理**：Guardrail 或规则评估期间异常 → 视为 BLOCK（安全优先）

---

## 已知限制

### 平台与架构

- **Python 版本**：需要 Python 3.11+（依赖 `tomllib` 等 3.11 特性）
- **Windows**：Shell 命令通过 `cmd.exe` 执行，行为可能与 Unix shell 不同
- **Linux**：`keyring` 在无桌面环境的 Linux 上回退到加密文件存储
- **ARM64**：未经测试，理论兼容

### 功能限制

- **记忆系统**：当前为全量注入（小规模记忆），不支持语义检索或嵌入
- **工具集**：仅内置 4 个工具（read_file、write_file、execute_shell、task_complete），不支持动态注册
- **LLM 提供商**：仅实现 DeepSeek 和 OpenAI 适配器
- **并发**：单任务执行，不支持并行 Agent

### 安全边界

- **工作区隔离**：依赖路径前缀匹配，非容器级或 chroot 级隔离
- **Shell 命令**：`execute_shell` 在工作区内执行，但命令本身不受沙箱限制
- **网络**：`NetworkExfilRule` 基于模式匹配，可被绕过

### 生产就绪度

- 本项目为**课程期末项目**，重点在于机制深度而非生产就绪度
- 未经过安全审计或渗透测试
- 不建议在未加固的情况下直接用于生产环境

---

## License

MIT License

Copyright (c) 2026 AI4SE Student

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
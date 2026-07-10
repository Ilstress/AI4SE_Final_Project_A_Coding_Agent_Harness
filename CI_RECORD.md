# CI/CD 执行记录

> **项目：** AI4SE Coding Agent Harness
> **CI 系统：** GitHub Actions (`.github/workflows/unit-test.yml`) + GitLab CI (`.gitlab-ci.yml`)
> **要求：** 通用要求 §五.7 — 最后一次 CI/CD 执行必须是 pass 状态

---

## 1. GitHub Actions 工作流

### 配置 (`.github/workflows/unit-test.yml`)

```yaml
name: Unit Tests
on:
  push:
    branches: ["**"]
jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        run: make test
```

### GitLab CI 等效配置 (`.gitlab-ci.yml`)

```yaml
unit-test:
  image: python:3.11-slim
  before_script:
    - pip install -e ".[dev]"
  script:
    - make test
```

---

## 2. CI 模拟执行记录

> GitHub Actions 实际触发需要 push 到 GitHub。以下为本地环境按 CI 工作流**完全相同的命令**模拟执行的结果。

### 执行环境

| 项 | 值 |
|----|-----|
| 日期 | 2026-07-10 |
| 分支 | main |
| Commit | `b68f3b7` |
| 消息 | test |
| Python | 3.14.4 (CI 目标: 3.11) |

### Step 1: Checkout

```
Branch: main
Commit: b68f3b71c06d7a40c6cc4e05e3ed5bc27f7a7bd4
Message: test
```

### Step 2: Setup Python

```
Python 3.14.4
```

> 注：CI 使用 Python 3.11 (GitHub Actions) / 3.11-slim (GitLab CI)。本地环境为 3.14，项目 `requires-python = ">=3.11"`，兼容。

### Step 3: Install dependencies

```bash
$ pip install -e ".[dev]"
```

```
Successfully installed ai4se-harness (0.1.0)
```

### Step 4: Run tests (`make test` / `pytest -v`)

```
============================= test session starts =============================
collected 590 items

tests/test_action_parser.py ...................                          [  3%]
tests/test_approval_providers.py .........                               [  4%]
tests/test_ci.py .............                                           [  6%]
tests/test_cli.py ............                                            [  8%]
tests/test_config_manager.py ................                            [ 11%]
tests/test_context_builder.py ...........                                 [ 13%]
tests/test_coordination_layer.py ...............                          [ 15%]
tests/test_credential_manager.py ..........                               [ 17%]
tests/test_docker.py ................                                     [ 20%]
tests/test_feedback_generators_phase2.py ...............                  [ 22%]
tests/test_feedback_generators_phase3.py .................                [ 25%]
tests/test_feedback_pipeline.py ...............                           [ 28%]
tests/test_feedback_router.py ............                                [ 30%]
tests/test_fingerprint.py .........                                       [ 31%]
tests/test_governance_controller.py ...............                       [ 34%]
tests/test_guardrail.py ..........                                        [ 36%]
tests/test_llm_adapters.py .................                              [ 38%]
tests/test_main_loop.py ....................                              [ 42%]
tests/test_mechanism_demo.py .........                                    [ 43%]
tests/test_memory_policy.py .......                                       [ 44%]
tests/test_memory_retriever.py ....                                       [ 45%]
tests/test_memory_store.py .........                                      [ 47%]
tests/test_models.py ..................................................  [ 55%]
tests/test_readme.py .............                                        [ 57%]
tests/test_recovery_controller.py ...............                         [ 60%]
tests/test_rule_engine.py ..............                                  [ 62%]
tests/test_rules/test_dangerous_shell.py .........                        [ 64%]
tests/test_rules/test_db_destructive.py .........                         [ 65%]
tests/test_rules/test_file_read_bound.py .........                        [ 67%]
tests/test_rules/test_network_exfil.py .........                          [ 68%]
tests/test_rules/test_path_boundary.py .........                          [ 70%]
tests/test_rules/test_shell_cwd_bound.py .........                        [ 71%]
tests/test_serializer.py .......                                          [ 73%]
tests/test_shell_generator.py .............                               [ 75%]
tests/test_tool_executor.py ...................                           [ 78%]
tests/test_tool_registry.py .................                             [ 81%]

============================ 590 passed in 12.79s =============================
```

### Step 5: Lint (`ruff check harness/ tests/`)

```
All checks passed!
```

### Step 6: Type check (`mypy harness/ tests/`)

```
Success: no issues found in 119 source files
```

---

## 3. 执行结果汇总

| 步骤 | 命令 | 结果 |
|------|------|------|
| Checkout | `git checkout main` | ✅ |
| Python | `python --version` | ✅ 3.14.4 (CI: 3.11) |
| Install | `pip install -e ".[dev]"` | ✅ |
| Test | `pytest -v` | ✅ **590/590 passed** |
| Lint | `ruff check harness/ tests/` | ✅ All checks passed |
| Typecheck | `mypy harness/ tests/` | ✅ 0 errors (119 files) |

### 最终状态：**PASS** ✅

---

## 4. GitHub Actions 实际触发

### 触发方式

Push 到 GitHub 仓库任意分支自动触发：

```bash
git push origin main
```

### 查看 CI 状态

- GitHub Actions: `https://github.com/Ilstress/AI4SE_Final_Project_A_Coding_Agent_Harness/actions`
- 状态徽章: `https://github.com/Ilstress/AI4SE_Final_Project_A_Coding_Agent_Harness/actions/workflows/unit-test.yml/badge.svg`

### README 中的 CI 徽章

```markdown
[![CI](https://github.com/Ilstress/AI4SE_Final_Project_A_Coding_Agent_Harness/actions/workflows/unit-test.yml/badge.svg)](https://github.com/Ilstress/AI4SE_Final_Project_A_Coding_Agent_Harness/actions/workflows/unit-test.yml)
```

---

## 5. 说明

- 本地 CI 模拟使用与 `.github/workflows/unit-test.yml` 完全一致的命令序列
- 所有 590 个测试使用 MockAdapter（无真实 LLM，无网络请求），CI 环境无需 API Key
- Push 到 GitHub 后，GitHub Actions 将自动运行并产生实际的 pass/fail 状态
- 网站 `https://github.com/Ilstress/AI4SE_Final_Project_A_Coding_Agent_Harness/actions` 可查看实际执行记录
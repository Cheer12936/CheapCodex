# Cheap Codex

**给 Codex 配一个便宜的实习生。**

CheapCodex 让 DeepSeek、Kimi、Qwen、Ollama 等 OpenAI-compatible 模型先去做“大范围阅读、摘要、定位、草稿”，Codex 继续负责判断、验证和最终改代码。

它不是 Codex 的替代品，而是把“读很多文件但只需要少量结论”的工作，从 Codex 主上下文里移出去。

```text
大量源码 / 日志 / 文档
        |
        v
Cheap Worker: 扫描、提取、总结、草稿
        |
        v
Codex: 判断、复核原文件、修改、测试
```

## 适合谁

如果你的 Codex 经常卡在这些场景，CheapCodex 会比较有用：

| 场景 | Worker 做什么 | Codex 做什么 |
| --- | --- | --- |
| 第一次进入陌生项目 | 扫目录、总结模块、找关键入口 | 判断从哪里开始改 |
| 一个需求可能跨多个文件 | 找路由、接口、调用链、测试位置 | 复核关键文件并实现 |
| 日志、源码、测试一起分析 | 先归纳可疑点和证据 | 验证根因并修 bug |
| 写测试、文档、配置 | 生成样板草稿 | 审核、调整、落到源码 |
| 大文件只需要结论 | 提取重点、行号、风险点 | 读取最小必要上下文 |

一句话：**读很多，改一点** 的项目最适合。

## 快速安装

### 方式一：让 Codex 自动安装

把下面这段话发给 Codex：

```text
Install https://github.com/Cheer12936/CheapCodex into my Codex setup. First check that WORKER_API_KEY exists; if it is missing, ask me to configure my DeepSeek key and stop. If it exists, run scripts/install-codex.ps1 -Provider deepseek -NonInteractive, configure the global AGENTS.md worker rules, and verify worker-health plus ask-worker dry-run.
```

更完整的复制版见 [CODEX-INSTALL-PROMPT.md](CODEX-INSTALL-PROMPT.md)。

### 方式二：PowerShell 一键安装

```powershell
$dir="$env:USERPROFILE\codex-cheap-worker"; if (Test-Path $dir) { git -C $dir pull } else { git clone https://github.com/Cheer12936/CheapCodex.git $dir }; cd $dir; .\scripts\install-codex.ps1 -Provider deepseek
```

安装脚本会自动完成：

- 创建 Python `.venv`
- 安装 `ask-worker` / `draft-worker` / `worker-health`
- 配置 `WORKER_API_KEY`、`WORKER_BASE_URL`、`WORKER_MODEL`
- 把项目 `bin\` 加入用户 PATH
- 写入或更新 `%USERPROFILE%\.codex\AGENTS.md`
- 运行 `worker-health` 和 dry-run 验证

安装后重启 Codex，让全局 `AGENTS.md` 生效。

## 常用命令

检查配置：

```powershell
worker-health
```

先 dry-run，不消耗 API token：

```powershell
ask-worker --paths "src/**/*.py" "README.md" --question "总结项目架构" --dry-run
```

让 worker 扫多个文件：

```powershell
ask-worker --paths "backend/**/*.js" "frontend/src/**/*.jsx" --question "梳理前后端数据流"
```

需要行号时：

```powershell
ask-worker --paths "backend/**/*.js" --question "找出用户认证相关代码在哪里" --line-numbers
```

生成草稿，默认写到 `.worker-drafts/`，不会直接覆盖源码：

```powershell
draft-worker --context "tests/**/*.py" "src/auth.py" --target "tests/test_auth.py" --spec "写 pytest，覆盖登录失败和 token 过期"
```

估算压缩效果：

```powershell
cheapcodex-benchmark --paths "src/**/*.py" "README.md"
```

真实调用 worker 的 benchmark：

```powershell
cheapcodex-benchmark --paths "src/**/*.py" "README.md" --live --max-tokens 2048
```

真实调用后，命令末尾会显示 token 使用量：

```text
[worker: 1300 in (1280 cached) / 36 out | finish: stop]
```

其中 `in` 是输入 token，`cached` 是模型侧缓存命中，`out` 是输出 token。

## Codex 会什么时候用它

安装脚本会把 worker 路由规则写入：

```text
%USERPROFILE%\.codex\AGENTS.md
```

默认建议 Codex 在这些情况下优先调用 `ask-worker`：

- 需要读取超过约 400 行的文件
- 需要扫描 3 个以上文件
- 需要项目结构图、接口清单、endpoint 清单、跨文件映射
- 进入陌生仓库，需要先找相关模块
- 修改 API、schema、函数、路由、共享工具前，需要估算影响范围
- 对比文档和源码是否过期
- 总结长日志、测试报告、生成报告
- 学习现有测试风格，再写新测试

默认建议 Codex 在这些情况下使用 `draft-worker`：

- 起草测试
- 起草 README、接口文档、变更说明
- 起草配置文件、适配器、重复 wrapper
- 起草 PR 描述、release notes、migration notes

关键原则：**worker 输出只是线索，不是事实来源。Codex 在编辑前仍要读取最小必要原文件。**

## 不建议使用的场景

这些情况不应该交给外部 worker：

- 架构决策
- 复杂且细节敏感的 bug 推理
- 安全敏感代码
- 密钥、客户数据、私钥、内部未公开资料
- 很小的单文件改动
- 需要联网搜索最新资料、价格、法规、外部 GitHub 项目对比

如果你使用第三方 API，文件内容会发送给对应服务商。更重视隐私时，优先使用本地 Ollama 或公司批准的内部模型。

## Benchmark

我们用一个模拟的复杂全栈项目做了实测，包含后端路由、controller、service、utils、前端页面、API client、测试、文档和日志。

| 测试场景 | 文件数 | 原始输入 token | Worker 输出 token | Codex 侧阅读压缩 |
| --- | ---: | ---: | ---: | ---: |
| 项目结构梳理 | 26 | 25,093 | 539 | 97.9% |
| 登录与刷新链路 | 9 | 8,378 | 453 | 94.6% |
| Token TTL 影响面 | 27 | 25,223 | 557 | 97.8% |
| 学习测试风格 | 4 | 5,895 | 434 | 92.6% |

还做了一个跨文件 bug 定位测试：

```text
RefundPage.jsx
  -> refundApi.createRefund()
  -> refundRoutes.js
  -> refundController.createRefund()
  -> refundService.refundOrder()
  -> money.calculateRefundCents()
```

worker 用 8 个相关文件定位到根因：

```diff
- return Math.round(raw * 100);
+ return Math.round(raw);
```

Codex 随后复核原文件、确认测试期望和日志证据，再完成修复验证。

完整测试过程见 [BENCHMARK-RESULTS.md](BENCHMARK-RESULTS.md)，测试方法见 [BENCHMARK.md](BENCHMARK.md)。

## 配置项

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `WORKER_API_KEY` | 无 | worker 模型 API key |
| `WORKER_BASE_URL` | `https://api.moonshot.ai/v1` | OpenAI-compatible API 地址 |
| `WORKER_MODEL` | `kimi-k2.5` | worker 模型名 |
| `WORKER_MAX_TOKENS` | `8192` | `ask-worker` 默认最大输出 token |
| `WORKER_DRAFT_MAX_TOKENS` | `16384` | `draft-worker` 默认最大输出 token |
| `WORKER_TEMPERATURE` | `0.1` | 采样温度 |
| `WORKER_MAX_FILE_BYTES` | `700000` | 单文件最大读取字节数 |
| `WORKER_MAX_TOTAL_BYTES` | `3000000` | 单次请求最大总读取字节数 |

长期设置示例：

```powershell
setx WORKER_MAX_TOKENS "8192"
setx WORKER_DRAFT_MAX_TOKENS "16384"
setx WORKER_MAX_TOTAL_BYTES "3000000"
setx WORKER_MAX_FILE_BYTES "700000"
setx WORKER_TEMPERATURE "0.1"
```

单次命令参数会覆盖环境变量：

```powershell
ask-worker --paths "src/**/*.py" --question "总结模块职责" --max-tokens 4096 --max-total-bytes 1000000
```

## 支持的模型服务

安装脚本内置了常用 provider：

```powershell
.\scripts\install-codex.ps1 -Provider deepseek
.\scripts\install-codex.ps1 -Provider kimi
.\scripts\install-codex.ps1 -Provider ollama
```

也可以连接任意 OpenAI-compatible endpoint：

```powershell
.\scripts\install-codex.ps1 -Provider custom -BaseUrl "https://example.com/v1" -Model "your-model"
```

## 文档入口

- [INSTALL-CODEX.md](INSTALL-CODEX.md): 安装到 Codex 的详细步骤
- [CODEX-INSTALL-PROMPT.md](CODEX-INSTALL-PROMPT.md): 给用户复制的 Codex 安装提示词
- [BENCHMARK.md](BENCHMARK.md): benchmark 命令和方法
- [BENCHMARK-RESULTS.md](BENCHMARK-RESULTS.md): 实测结果和 bug 定位案例
- [AGENTS.md.template](AGENTS.md.template): 写入 Codex 的 worker 调用规则模板

## 项目边界

CheapCodex 的价值不是“自动替你写对所有代码”，而是让 Codex 少读无关上下文，更快找到应该亲自复核的文件。

推荐工作流：

```text
worker 广泛阅读
Codex 阅读摘要
Codex 打开关键原文件
Codex 修改和测试
```

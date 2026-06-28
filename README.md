# Cheap Codex

给 Codex 配一个便宜的“阅读同事”：让 DeepSeek、Kimi、Qwen、Ollama 等 OpenAI-compatible 模型负责大文件阅读、跨文件摘要和样板草稿，Codex 继续负责判断、验证和最终修改。

这个项目的目标不是替代 Codex，而是减少 Codex 在“读很多文件”上消耗的上下文。

## 核心思路

```text
Codex: 推理、判断、验证、最终改代码
Worker: 大文件阅读、信息提取、文档/测试/配置草稿
```

当任务需要扫很多文件时，Codex 不必把所有源码都读进自己的上下文，而是先调用 worker 模型生成结构化摘要，再基于摘要做决策。

## 适合什么场景

- 梳理项目结构、模块职责、数据流
- 扫描多个文件找接口、路由、endpoint、定时任务
- 总结大文件或多个文件的关键信息
- 起草测试、配置文件、README、接口文档
- 让 Codex 在实现功能前先定位相关代码

不适合：

- 架构决策
- 复杂 bug 推理
- 安全敏感代码
- 含密钥、客户数据、私钥的文件
- 很小的改动
- 需要逐行精确修改的任务

## 功能

- `ask-worker`: 读取多个文件或 glob，向 worker 模型提问，返回结构化摘要。
- `draft-worker`: 根据参考文件生成草稿，默认写入 `.worker-drafts/`，不会直接覆盖源码。
- `worker-health`: 检查 worker 配置、模型、API key 和 token 默认值。
- `cheapcodex-benchmark`: 估算和验证 worker 对 Codex 上下文的压缩效果。
- `AGENTS.md.template`: Codex 的 worker 路由规则模板。
- `scripts/install-codex.ps1`: 一键安装到本机 Codex。

## 最快安装方式

### 方式一：让 Codex 自己安装

把下面这段话发给 Codex。

```text
Install https://github.com/Cheer12936/CheapCodex into my Codex setup. First check that WORKER_API_KEY exists; if it is missing, ask me to configure my DeepSeek key and stop. If it exists, run scripts/install-codex.ps1 -Provider deepseek -NonInteractive, configure the global AGENTS.md worker rules, and verify worker-health plus ask-worker dry-run.
```

更详细的可复制提示词见 [CODEX-INSTALL-PROMPT.md](CODEX-INSTALL-PROMPT.md)。

### 方式二：PowerShell 一键安装

```powershell
$dir="$env:USERPROFILE\codex-cheap-worker"; if (Test-Path $dir) { git -C $dir pull } else { git clone https://github.com/Cheer12936/CheapCodex.git $dir }; cd $dir; .\scripts\install-codex.ps1 -Provider deepseek
```

安装脚本会自动：

- 创建 `.venv`
- 安装 CLI 工具
- 交互式输入 API key，不会打印 key
- 配置 `WORKER_API_KEY`、`WORKER_BASE_URL`、`WORKER_MODEL`
- 把项目 `bin\` 加入用户 PATH
- 写入或更新 `%USERPROFILE%\.codex\AGENTS.md`
- 运行验证命令

安装完成后，重启 Codex。

## Provider 示例

DeepSeek:

```powershell
.\scripts\install-codex.ps1 -Provider deepseek
```

Kimi:

```powershell
.\scripts\install-codex.ps1 -Provider kimi
```

Ollama 本地模型:

```powershell
.\scripts\install-codex.ps1 -Provider ollama
```

自定义 OpenAI-compatible endpoint:

```powershell
.\scripts\install-codex.ps1 -Provider custom -BaseUrl "https://example.com/v1" -Model "your-model"
```

## 手动安装

Windows:

```powershell
git clone https://github.com/Cheer12936/CheapCodex.git
cd codex-cheap-worker
.\scripts\install.ps1
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
git clone https://github.com/Cheer12936/CheapCodex.git
cd codex-cheap-worker
bash scripts/install.sh
source .venv/bin/activate
```

## 配置

环境变量：

| 变量 | 默认值 | 说明 |
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

## 使用示例

Benchmark，不消耗 API token：

```powershell
cheapcodex-benchmark --paths "src/**/*.py" "README.md"
```

真实调用 worker 的 benchmark：

```powershell
cheapcodex-benchmark --paths "src/**/*.py" "README.md" --live --max-tokens 2048
```

更多说明见 [BENCHMARK.md](BENCHMARK.md)。

实测结果和跨文件 bug 修复案例见 [BENCHMARK-RESULTS.md](BENCHMARK-RESULTS.md)。

先 dry-run，不消耗 API token：

```powershell
ask-worker --paths "src/**/*.py" "README.md" --question "总结项目架构" --dry-run
```

让 worker 扫描多个文件：

```powershell
ask-worker --paths "backend/**/*.js" "frontend/src/**/*.jsx" --question "梳理前后端数据流"
```

需要行号时：

```powershell
ask-worker --paths "backend/**/*.js" --question "找出用户认证相关代码在哪里" --line-numbers
```

生成测试草稿：

```powershell
draft-worker --context "tests/**/*.py" "src/auth.py" --target "tests/test_auth.py" --spec "写 pytest，覆盖登录失败和 token 过期"
```

默认会写到：

```text
.worker-drafts/tests/test_auth.py
```

然后让 Codex 审核和应用。

## Codex 会什么时候调用 worker

安装脚本会把规则写入：

```text
%USERPROFILE%\.codex\AGENTS.md
```

规则大意：

- 读超过约 400 行的大文件时，优先用 `ask-worker`
- 扫 3 个以上文件时，优先用 `ask-worker`
- 做项目摘要、接口清单、endpoint 清单、跨文件映射时，优先用 `ask-worker`
- 生成测试、文档、配置、重复样板代码时，优先用 `draft-worker`
- Codex 必须复核 worker 输出，不能把 worker 输出当作事实来源

## Token 使用

真实调用后会打印 token 使用量：

```text
[worker: 1300 in (1280 cached) / 36 out | finish: stop]
```

含义：

- `1300 in`: 输入 token
- `1280 cached`: 命中的缓存 token
- `36 out`: 输出 token
- `finish`: 模型结束原因

默认输出上限对齐原项目思路：

```text
ask-worker: 8192
draft-worker: 16384
```

对于 thinking 模型，`max_tokens` 需要覆盖模型内部推理和最终答案，所以不要设得太低。

## 安全边界

默认安全策略：

- 常见 `API_KEY`、`TOKEN`、`SECRET`、`PASSWORD` 行会被保守脱敏
- 二进制文件会跳过
- 大文件会按上限截断
- 草稿默认写入 `.worker-drafts/`，不会覆盖源码

仍然要注意：如果你使用第三方 API，文件内容会发送给对应服务商。私有代码、客户数据、密钥文件和安全敏感文件不要委托给外部 worker。需要更强隐私时，优先使用本地 Ollama 或公司批准的内部模型。

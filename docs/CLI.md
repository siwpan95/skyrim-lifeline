# CLI 使用说明 · `frostwords`

> 面向 Windows 命令提示符 / PowerShell 的命令行入口。
> 版本 `1.0.0` · 引擎 `dse-core`（版本以该机 `pip show dse-core` 为准）

> **口径约定**：本文的 `<PYTHON>` = 该机装有 `dse-core` 的解释器，
> `<SHIM_DIR>` = 该机已在 PATH 的垫片目录。凡出现具体盘符、解释器版本、
> 文件字节数、场景步数与退出码实测值，均为 **`@SIWPAN` 单机时点事实**
> （换机 / 加减盘 / 重装 / 换运行时后立即失效，须现场复测），
> **不是跨机器通用结论**。他机以 `install-cli` 的实际输出为准；
> 机器事实的归属与裁决口径见 `<ALLIN_ROOT>/docs/事实源/机器分区索引.md` §0。
> 下文的 `.cmd` 字节级铁律与退出码契约是**跨机通用**的，不含本机数值。

`frostwords` 是**编排层**：它不二次实现业务逻辑。采集与渲染在
`tools/export_run.py`，垫片生成在 `tools/cli_shim.py`，门禁在
`tools/verify.py`，游戏本体在 `dse play`。这里只做参数解析、前置校验、
调用转发与退出码映射。

---

## 1. 三种启动方式

| 方式 | 写法 | 适用 |
|---|---|---|
| 仓库根垫片 | `frostwords.cmd export-run` 或 `fwcli.cmd export-run` | 在仓库目录内；`FW_ROOT=%~dp0`，整个仓库搬走也不失效 |
| PATH 垫片 | 任意目录下 `frostwords --version` / `fwcli cases` | 已执行 `install-cli`；〔@SIWPAN 本机时点〕装在 `E:\Python314\Scripts`，他机以 `install-cli` 输出为准 |
| 直接调 Python | `<PYTHON> tools\frostwords_cli.py cases` | 调试、CI、不想装垫片 |

> **缩写为什么是 `fwcli` 而不是 `fw`**：PowerShell 里 `fw` 是
> `Format-Wide` 的别名，会把 `--ending` 当成位置参数报
> 「找不到接受自变量 '--ending' 的位置参数」。曾踩过一次，故改名。

直接运行 `frostwords`（不带参数）、`frostwords --help` 打印命令表；
`frostwords <命令> --help` 或 `frostwords help <命令>` 打印该命令详解。

---

## 2. 命令表

| 命令 | 作用 | 产出 |
|---|---|---|
| `export-run` | **完整导出一次游戏流程**（真实引擎逐场景采集） | `.md` / `.json` / `.html` |
| `export-outline` | 导出全部 113 个场景的**静态流程大纲** | `exports/outline.md` |
| `cases` | 列出 9 个可用结局及通关脚本步数 | stdout / JSON |
| `play` | 转发到 `dse play`，参数原样透传 | 交互终端 |
| `verify` | 转发到 `tools/verify.py`（四层门禁） | 门禁报告 |
| `install-cli` | 生成 `.cmd` 垫片并装到 PATH 目录 | 4 份垫片 |
| `uninstall-cli` | 卸载 PATH 垫片（保留仓库根垫片） | — |
| `help <命令>` | 查看详细帮助 | stdout |

### 最常用

```bat
frostwords cases
frostwords export-run --ending end-whiterun --format md,json,html
frostwords export-run --all-endings
frostwords export-outline --json
frostwords verify --fast
frostwords install-cli
```

---

## 3. 「完整流程」是怎么采集出来的

这是本 CLI 与 `dse export-html` 的根本区别：后者只导出**静态场景文本**，
前者记录**一局真实玩下来的每一步**。

| 环节 | 做法 | 为什么 |
|---|---|---|
| 场景正文 | 订阅 `scene/enter` 事件 | 该事件在 `onEnter` 效果结算**之后**、渲染**之前**发出，拿到的是玩家此刻真正看到的状态与选项 |
| 可见选项 | 与 `engine.render` 同口径重算：`if` 条件 + `once` 消费 | 条件不满足 / 一次性已用掉的选项不能算「当时可见」 |
| 正文变体 | 取 `engine._variant_text`、`extraText` 条件段、`state.interpolate` | 加权随机分支、状态插值后的文字才是实际显示的文字 |
| 玩家输入 | hook `io.ask` | 引擎与五种 mode 插件的输入**都经这一个通道**，所以 battle 多回合、dialogue 连问、trade 逐日都会被记下 |
| 状态轨迹 | 相邻场景状态快照 `diff` | 摊平为点路径，丢掉 `visits` / `onceSeen` 噪音，输出每一步的数值变化 |

```python
def hooked_ask(prompt: str = "> ") -> str:
    line = original_ask(prompt)
    pending_inputs.append(line)
    return line

def on_enter(sid, scene):
    if steps:
        steps[-1]["inputs"] = list(pending_inputs)
        pending_inputs.clear()
    snap = flatten(state.snapshot())
    steps.append({... "state": snap, "choices": visible ...})
```

**刻意不模拟引擎语义**：采集全程跑真实引擎，只是旁听事件、不参与推进。
手写模拟已在 e2e 求解阶段证明不可靠（`dialogue.do_ask` 的「已问过」优先于
「注意点用尽」、`trade.days=2` 要两次 `next`、battle 是多回合），因此这里
一律交给引擎自己跑。导出的流程与 `dse play` 一致。

### 两个必须的环境隔离

```python
os.environ.pop("DSE_ENTRY", None)          # sdk.create_engine(entry=...) 会写且从不清理
engine.rng = random.Random(seed)           # 加权 goto / 变体
random.seed(seed)                          # combat 插件用全局 random.random()，不受 engine.rng 控制
```

`capture()` 在 `finally` 里恢复 `io.ask`、注销事件、清掉 `DSE_INPUT` /
`DSE_ENTRY`、`ctx.dispose()`。不这么做，同一条脚本两次导出会走出不同结局。

> **输入次数通常 > 场景步数**：一个 `dialogue` 场景里连问三题、一个
> `battle` 场景里打五个回合，都只算一个 `scene/enter`。
> 实测真结局 `52 场景步 / 65 次输入`。

---

## 4. 三种输出格式

| 格式 | 后缀 | 内容 | 典型体积 |
|---|---|---|---|
| `md` | `.md` | 可读剧本：每步标题 / 场景 ID / 模式 / 正文 / 当时可见选项 / **当时可见的话题** / **每轮编号基准** / 输入 / 状态变化，末尾附终局状态表 | ~85 KB |
| `json` | `.json` | 结构化记录：`meta` + `steps[]`（`state` / `changes` / `inputs` / `choices` / **`topics`** / **`topic_snapshots`**）+ `final_state`，便于程序消费 | ~275 KB |
| `html` | `.html` | 单文件阅读版，状态变化与编号基准放 `<details>` 折叠 | ~125 KB |

`--format` 接受 `md` / `json` / `html` / `all`，或逗号组合（去重保序）。
`--output` 指定路径；多格式时按 stem 自动加各自后缀，单格式时原样写入。
默认输出目录 `exports/`，默认文件名 `playthrough-<结局>.<后缀>`。

### 对话话题的采集口径

`dialogue` 场景的可见话题由引擎 `DialogueService.visible()` 决定，
导出器**直接调它**、不重算过滤，因此编号与玩家看到的完全一致：

| 字段 | 含义 |
|---|---|
| `steps[].topics` | 进入该对话场景时玩家看到的完整话题列表（编号从 1 起，按可见列表重排） |
| `steps[].topic_snapshots[]` | 每轮提问时的话题快照；`input` 是玩家输入，`topics` 是**该轮编号基准** |

两条易踩的语义差异（别自己重算，会漂）：

- `visible()` **只按 `if` 过滤，不看 `once`** —— 与 `engine.render` 的
  `choices` 过滤不同（后者还消费 `once`）。
- **已问过的话题仍留在列表里占编号**，只是标记「已问过」。

话题列表会随对话推进而重排：某次提问的 effect 可能跨过另一个话题的
`if` 门槛（如 `soul >= 2`），使可见列表缩短、后续编号整体前移。
`topic_snapshots` 就是为记录这个漂移而存在的 —— 看它能还原出
「第 3 问时玩家按的 2 指的是哪个话题」。

> 这里的 `.html` 是**流程记录**，由本工具自己渲染，与 `dse export-html`
> 无关，因此不受「浏览器端只支持 `normal` 模式」的限制。

### `export-outline` 与 `export-run` 的区别

| | `export-outline` | `export-run` |
|---|---|---|
| 跑不跑引擎 | 不跑，读静态图 | 跑完整一局 |
| 覆盖范围 | **全部 113 场景** + 全部出边（目标 / 类型 / 条件 / 选项文本 / 权重） | 某一局实际走过的 45–51 步 |
| 用途 | 审阅分支设计、查悬空与条件 | 复盘一局、存档记录、给玩家看实录 |

`render_outline()` 用 `graph.edges_of()` 拿边，再用原始 `choices` 反查补齐
`if` 条件、选项文本和加权权重 —— 否则大纲只有目标 ID，无法阅读。

---

## 5. `export-run` 参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--ending ID` | `end-whiterun` | 选用 `tests/e2e_cases.json` 里已验证的通关脚本；未知 ID 会给拼写建议 |
| `--script STR` | — | 自定义输入流（逗号分隔），与 `--ending` 互斥 |
| `--format LIST` | `md` | `md` / `json` / `html` / `all` / 逗号组合 |
| `--output PATH` | `exports/playthrough-<结局>.<后缀>` | 多格式按 stem 加后缀 |
| `--seed N` | `20261115` | 正整数；固定加权分支与战斗随机数 |
| `--all-endings` | 关 | 为全部 9 个结局各导出一份，忽略 `--output` / `--script` |

```bat
frostwords export-run
frostwords export-run --ending end-thu-um --format all
frostwords export-run --ending end-frozen --format md --output <可写目录>\run.md
frostwords export-run --script "1,1,1,ask 1,a,a,next,next" --output <可写目录>\run.md
frostwords export-run --all-endings --format md,json,html
```

> `--all-endings` 是批量调用同一条 `core.export_run()`，`--ending` 会被忽略。
> 9 个结局 × 3 格式 = 27 个文件，实测约 4.2 MB（另加 1 份 `outline.md` 共 28 个）。

---

## 6. 全局选项、透传与退出码

全局选项 `--json` / `-q` / `--quiet` **可出现在子命令前或后**（`strip_common()`
从 argv 任意位置抽出），`--json` 把结果摘要以单行 JSON 打印到 stdout，
便于批处理消费：

```bat
frostwords export-outline --json
:: {"ok": true, "file": "...\\exports\\outline.md", "bytes": 48916, "scenes": 113}
```

`--` 之后的一切**原样透传**给被启动的程序，不被本工具解析：

```bat
frostwords play -- --entry core-open
frostwords verify -- --samples 100
```

### 退出码契约

| 码 | 含义 | 触发例 |
|---|---|---|
| `0` | 成功 | 正常导出、门禁通过 |
| `1` | 一般失败 | 写文件失败（父路径是普通文件）、引擎异常 |
| `2` | 用法错误 | 未知命令、未知格式、未知结局、`--script` 与 `--ending` 互斥、`--seed 0` |
| `6` | 环境缺失 | `dse-core` 未安装、工程文件缺失、找不到 Python |
| `130` | 用户中断 | Ctrl-C |
| 子进程码 | 转发命令 `play` / `verify` **原样返回**，不压成 1 | `verify` 门禁失败时返回它自己的码 |

未知命令会用 `difflib.get_close_matches()` 给拼写建议。转发命令走
`subprocess.call()`，`dispatch()` 返回 int 时 `main()` 直接 `return result`。

---

## 7. Windows `.cmd` 垫片

```bat
frostwords install-cli                    :: 默认装到 <Python 前缀>\Scripts
frostwords install-cli --dry-run          :: 只打印将做的事，不写文件
frostwords install-cli --shim-dir <SHIM_DIR>  :: 指定目录
frostwords install-cli --add-to-path      :: 目录不在 PATH 时写 HKCU\Environment\PATH
frostwords uninstall-cli                  :: 只删带标记的文件
```

安装目录优先级：`--shim-dir` → `FW_BIN_DIR` → `<Python prefix>\Scripts`
→ `%LOCALAPPDATA%\frostwords\bin`。〔@SIWPAN 本机时点〕
`E:\Python314\Scripts` 已在 PATH，故本机默认无需改环境变量；
**他机必须自行确认该目录是否已在 PATH**，不在就加 `--add-to-path`。

### 生成的两类垫片

| 位置 | `FW_ROOT` | 用途 |
|---|---|---|
| 仓库根 `frostwords.cmd` / `fwcli.cmd` | `%~dp0` | 随仓库移动，clone 到别处仍可用 |
| PATH 目录同名两份 | 绝对路径 + 尾 `\` | 任意目录直接调用 |

解释器探测链：`FW_PYTHON`（若路径存在）→ baked `sys.executable` →
`py -3` → `python`；都找不到时打印 `[ERR] Python not found...` 并 `exit /b 6`。
调用行固定为：

```bat
"%FW_PY%" %FW_PYARG% "%FW_ROOT%%CLI_TARGET%" %*
set "FW_RC=%ERRORLEVEL%"
exit /b %FW_RC%
```

### 字节级铁律（〔@SIWPAN〕实测归纳；**约束本身跨机通用**）

| 约束 | 原因 |
|---|---|
| **纯 ASCII** | cmd.exe 按当前代码页（中文机 GBK）逐行解析，UTF-8 中文会让行首 ASCII 语法被吃掉，报一堆命令碎片 |
| **CRLF，无裸 LF，无孤立 CR** | 写字用 `encoding="ascii", newline=""`，行尾由字符串自己给 `\r\n`；再传 `newline="\r\n"` 会二次翻译落成 CR CR LF |
| **解释器加引号** | 路径含空格；`py -3` 不能整体加引号，所以拆成 `FW_PY` / `FW_PYARG` |
| **退出码原样回传** | 不用 `exit /b 0` 硬编码，否则上层批处理拿不到真实失败 |

生成时 `body.encode("ascii")` 主动炸掉任何非 ASCII 字节；`inspect_shim()`
做六项自检：`ascii` / `bare_lf` / `lone_cr` / `quoted_call` / `marker` / `bytes`。
实测仓库根与 PATH 垫片均为：

```text
ascii=True, bare_lf=0, lone_cr=0, quoted_call=True, marker=True
```

`uninstall-cli` 只删前 4096 字节含 `FW_CLI_SHIM v1` 标记的文件；
**同名手工文件会跳过并列出**，不会误删别人的东西。仓库根垫片保留。

---

## 8. 实测记录（〔@SIWPAN 本机时点〕，他机数值不适用）

以下数值全部是 `@SIWPAN` 在 2026-11-15 的单点观测，仅供核对量级，
**不得当作跨机器断言**。命令口径与退出码契约是通用的。

> 本节表格为 2026-11-15 的时点快照；当前验收基线（113 场景 / 9 结局 /
> 52 步 65 输入 / 27 文件约 4.2 MB）见 `README.md` §验收结果。

| 场景 | 命令 / 动作 | 结果 |
|---|---|---|
| 真结局采集 | `export_run.capture()` | `51 场景步 / 62 次输入 / 51 不同场景 → end-whiterun`；`normal 45 / dialogue 2 / battle 3 / trade 1` |
| 三格式导出 | `frostwords export-run --ending end-thu-um --format all` | 3 文件全 OK，`51 场景步 → end-thu-um` |
| 大纲 | `frostwords export-outline --json` | `{"ok":true,"bytes":48916,"scenes":113}` |
| 用例表 | `frostwords cases` | 9 个结局，52–65 步 |
| 静态大纲 | `export-outline` | 113 场景标题 + 每条出边的条件 / 权重 |
| 全结局批量导出 | `export-run --all-endings --format md,json,html` | 8/8 成功：`end-alone 49` / `end-dragon 52` / `end-frozen 48` / 其余 5 个各 `51` 场景步；24 个文件共 3.6 MB |
| 最终验收 | `tools/verify.py` + `tests/cli_check.py` + 批量导出 三条并行 | `全部门禁通过（45.6s）`、`PASS 63 FAIL 0 SKIP 0`、`ALL_ENDINGS_EXIT=0` |
| 仓库根垫片 | 从 cmd 执行 `frostwords.cmd export-run --ending end-frozen --format md --output <可写目录>\run.md` | `48 场景步 → end-frozen`，`72,299 B`，`rc=0` |
| 跨目录 PATH 垫片 | 在任一非仓库目录（〔本机〕用了 `C:\Windows`）下 `fwcli export-run --ending end-alone` | `49 场景步 → end-alone`，`73,595 B`，`version_rc=0; export_rc=0` |
| CLI 回归 | `python tests/cli_check.py` | `PASS 63  FAIL 0  SKIP 0`，`rc=0` |

> `PASS 63` 中出现的 `[ERR] 已中断` 是回归里 monkeypatch 触发
> `KeyboardInterrupt` 验证退出码 `130` 的**有意输出**，不是失败。

---

## 9. 回归测试

```bat
<PYTHON> tests\cli_check.py
```

纯 stdlib，子进程统一 `[sys.executable, "-X", "utf8", CLI]` + UTF-8 解码，
不受控制台代码页影响。八组覆盖：

| # | 覆盖 |
|---|---|
| ① | 顶层命令面：`--version` / 裸调用 / `--help` / 七个命令的 `--help` / `help <cmd>` |
| ② | 退出码 `2`：未知命令、未知格式、未知结局、非法 seed、互斥参数、非法参数；拼写建议 |
| ③ | `--json` 前置/后置一致性、可解析且 8 结局、`-q` 抑制、`--` 落在 argv 末尾、转发返回子进程码 7 |
| ④ | 垫片字节契约：ASCII / CRLF / 无裸 LF / 无孤立 CR / 引号 / 标记；两类垫片**仅 root 行不同** |
| ⑤ | 导出完整性：重算 JSON 步数与结局、每步都有 `state` 与 `changes`、输入次数 ≥ 步数、Markdown 终局表、HTML 折叠块、大纲 113 场景 |
| ⑥ | 退出码 `1`（写失败）/ `6`（注入假 `dse_core` 模拟环境缺失）/ `130`（中断） |
| ⑦ | 装 / 卸回归：`--dry-run` 不写文件、他人同名手工文件必须保留且被列出 |
| ⑧ | 转发命令真跑 `verify --fast`，断言 `全部门禁通过` |

---

## 10. 排查表

| 症状 | 原因 / 修法 |
|---|---|
| `'fwcli' 不是内部或外部命令` | 没装 PATH 垫片 → `frostwords install-cli`；装完要**新开终端** |
| PowerShell 报 `Format-Wide: 找不到接受自变量 '--ending' 的位置参数` | 用了 `fw`（内置别名）→ 改 `fwcli` 或 `frostwords` |
| `.cmd` 报一堆命令碎片 / `'锘' 不是内部或外部命令` | 垫片被改成 UTF-8 中文或 BOM → 重新 `install-cli`；垫片必须纯 ASCII |
| `[ERR] Python not found...` / `rc=6` | 探测链全断 → 设 `FW_PYTHON=<该机 python.exe 绝对路径>` |
| `rc=6 dse-core 或导出模块不可用` | 当前解释器没装 `dse-core` → `pip install "dse-core>=0.7.0"`，或换回该机装有 `dse-core` 的解释器 |
| `rc=2 未知结局 'end-xxx'` | `tests/e2e_cases.json` 里没有 → `frostwords cases` 查 ID |
| 导出流程走到一半就停 | 自定义 `--script` 输入用尽或走进死路 → 用 `--ending` 的已验证脚本 |
| 同一脚本两次导出结果不同 | 忘了固定全局随机源（本工具已固定 `engine.rng` + `random.seed`）；或内容包改过导致选项编号漂移 |
| 改动内容包后导出全错 | 选项编号漂移 → 先跑 `python tools/solve_e2e.py --all --write-cases` |
| 批量导出占空间 | `--all-endings --format md,json,html` 会写 27 个文件约 4.2 MB → 用 `--format md` 或清理 `exports/` |

---

## 11. 已知边界

1. **导出的是「一局」，不是全图。** 全图静态分支请用 `export-outline`；
   穷举所有路径数学上不可行（路径数约 `2.37 × 10²⁸`，见 `docs/design.md` §四）。
2. **`--script` 不做可达性预判。** 给一条不合法输入流，引擎会按它的规则
   （无效输入重问 / 输入耗尽退出）结束，导出的就是「已走完的部分」。
3. **数值平衡已由 dse-core 0.7.0 护栏解决。** `state.bounds` 在每次结算后
   把七项资源钳进合法区间，`state.fatal` 提供早期冻死分支；真结局终局实测
   `hp=0 / soul=0 / stamina=0 / trust=100 / warmth=7 / clock=20`，全部落在
   `bounds` 内。导出如实记录引擎终值，不做美化。见 `docs/design.md` §3.1。
4. **`end-select` 是并列选择，不是自动分流。** 满足条件的所有结局同时出现，
   最后一按由玩家负责；`--ending` 选择的是求解器验证过的那条输入流。
5. **`export-outline` 不跑引擎**，因此条件段的运行时取值不在大纲里，
   只有条件表达式原文。
6. `frostwords play` 是转发，交互体验与 `dse play` 完全相同；
   本 CLI 不提供独立的浏览器可玩版。

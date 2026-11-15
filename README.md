# 霜语 · Frostwords

> 一个上古卷轴同人**纯文字生存叙事**
> 参考对象：《生命线》(Lifeline) 系列（3 Minute Games, 2015–）
> 引擎：[dse-core](https://pypi.org/project/dse-core/) · 字典场景引擎（场景即字典，能力即插件）
> 远端：[gitee.com/siwpan/skyrim-lifeline](https://gitee.com/siwpan/skyrim-lifeline) · MIT · 非商业同人
> 整改链路：[最终验证报告](docs/allin-fix-verification.md)（P0 → P3 全量实战校验）

> **口径约定**：本文所有绝对路径、解释器版本、仓数、字节数与「实测」数值
> 都是 **`@SIWPAN` 单机时点事实**，不是跨机器通用结论。命令里的
> `<PYTHON>` 请替换成该机装有 `dse-core` 的解释器；`<ALLIN_ROOT>` /
> `<REPOS_ROOT>` 以该机 allin 事实源
> （`docs/事实源/机器分区索引.md`）为准。换机 / 加减盘 / 重装系统 /
> 换运行时后这些数值**立即失效**，须现场复测。详见
> `docs/allin-repocheck-validation.md` §0。

你是持有灵魂水晶的**远端**。她叫**海尔薇·霜门**，诺德人，风暴斗篷的斥候，
去年冬天去了海尔根，再也没回来——直到三天前，她在雪原上接通了你的水晶。

你不能救她。你只能**说话**。
而她，未必听。

---

## 快速开始

```bash
pip install dse-core

cd skyrim-lifeline
dse play                       # 开始游戏
dse play --banner              # 带启动横幅
dse check                      # 静态校验（Schema / 悬空跳转）
dse scenes                     # 列出全部场景
dse graph --format mermaid     # 导出场景图

frostwords cases               # 列出 8 个可用结局
frostwords export-run          # 完整导出一次游戏流程（真结局）
frostwords install-cli         # 装好上面这个命令（Windows）
```

> `frostwords` 是本项目的 CLI：从**真实引擎**逐场景采集一局流程，
> 导出 Markdown / JSON / HTML。详见下文「CLI：完整导出一次游戏流程」
> 与 `docs/CLI.md`。

### 用法与示例

常用命令示例（完整用法见 [CLI 手册](docs/CLI.md)）：

| 我想… | 命令 |
|---|---|
| 开始游戏 | `dse play` |
| 校验内容包 | `dse check` |
| 列出可用结局 | `frostwords cases` |
| 导出一次完整流程 | `frostwords export-run --format md,json,html` |
| 导出全场景大纲 | `frostwords export-outline` |
| 跑全部门禁 | `python tools/verify.py` |

> 命令里的解释器与安装路径请按文首「口径约定」替换成该机实测值；
> 本文出现的绝对路径与数值均为 `@SIWPAN` 时点事实。

### 引擎内可用命令

| 命令 | 作用 |
|---|---|
| `1` `2` `3`… | 选择选项 |
| `stats` | 查看当前状态（HP / 魔力 / 金币 / 背包） |
| `rollback [n]`（`rb` / `back`） | **回滚 n 个选择点** —— 对应《生命线》的 Rewind |
| `achievements` | 查看成就 |
| `save` / `load` / `slots` | 存档 / 读档 / 列存档位 |
| `quit` | 退出 |

> `rollback` 是本作能反复试错的关键 —— 试一条路，不满意就退回去。

### 浏览器阅读版（有限制）

```bash
dse export-html -o frostwords.html --title "霜语 · Frostwords"
```

可导出单文件 HTML，离线通读全部场景文本。但引擎的 `export-html`
**只实现 `normal` 模式**：本作 12 个 `battle` / `dialogue` / `trade` /
`diary` 场景在浏览器端无插件接管，会显示提示并中断。
**完整可玩请用 `dse play`** —— CLI 才是五种模式齐全的入口。

---

## 玩法机制

### 她会拒绝你的建议

这是全作的核心。你给的每个建议，她有**自己的判断**：

```
你：「东边是缓坡，有猎人小屋，有火。」

    ├─ 她照做（权重大）──→ 她往东走，找到了树枝，听你的
    └─ 她拒绝（权重小）──→ 「我看见烟了。里面有人。我不去。」
```

她不是玩具。信任度越高，她越可能听你的；信任度掉下去，
她会按自己的方式走 —— 有时那是对的，有时不是。

### 资源会真的耗尽

| 资源 | 作用 | 归零后果 |
|---|---|---|
| **体温** | 雪原上的唯一硬约束。每走一段路都在掉 | 冻死 |
| **体力** | 战斗、逃跑 | 跑不动 |
| **信任** | 决定她听不听你的 | 通讯断绝 |
| **灵魂水晶余量** | 每次深度咨询消耗 | 说不下去了 |
| **口粮** | 恢复体温与体力 | 撑不住 |

**体温是唯一的硬死亡线。** 火堆、食物、正确的路线决定你能不能活到白漫。

### 知识即选项

有些选择只有**知道点什么**才能做对 —— 就像《生命线：Crisis Line》
要玩家自己去查资料一样，本作把资料放在世界内部：

- 问对问题（`dialogue` 模式的**注意点预算**有限，问不满就没机会了）
- 找到对的人（守卫、法师、走私贩、酒馆里的诺德人）
- 读她说过的话（`diary` 模式可回看全部已读消息）

### 多结局

八个结局，包括真结局、隐藏结局（龙吼）、翻转结局（她死了，但事办成了），
以及好几个你压根救不了她的死法。满足条件的结局会在 `end-select`
并列出现 —— 最后一按由你负责。

---

## CLI：完整导出一次游戏流程

`dse export-html` 只能导出**静态场景文本**，而且只支持 `normal` 模式。
本项目的 `frostwords` 导出的是**一局真正玩下来的完整流程**：每个场景的正文、
当时可见的选项、玩家的每一次输入、相邻场景的状态变化、终局状态。

### 装与用

```bat
<PYTHON> tools\frostwords_cli.py install-cli

frostwords cases                                          :: 8 个可用结局
frostwords export-run --ending end-whiterun --format md,json,html
frostwords export-run --all-endings                        :: 8 个结局各导一份
frostwords export-outline --json                          :: 109 场景静态大纲
frostwords verify --fast                                  :: 转发四层门禁
frostwords play -- --entry core-open                      :: 转发 dse play
```

仓库根也有 `frostwords.cmd` / `fwcli.cmd`（`FW_ROOT=%~dp0`，搬走不失效），
装完 PATH 垫片后任意目录都能用。缩写是 **`fwcli`** —— PowerShell 里 `fw`
撞上了 `Format-Wide` 别名。

### 为什么能「完整」

| 环节 | 做法 |
|---|---|
| 场景正文与选项 | 订阅 `scene/enter`（在 `onEnter` 结算之后、渲染之前发出），按 `engine.render` 同口径重算 `if` / `once` 可见选项 |
| 玩家输入 | hook `io.ask` —— 引擎与五种 mode 插件的输入都经这一通道，battle 多回合、dialogue 连问、trade 逐日都记下 |
| 数值轨迹 | 相邻场景状态快照做 diff，摊平为点路径，丢掉 `visits` / `onceSeen` 噪音 |

**不模拟引擎语义**，全程跑真实引擎、只旁听事件，因此导出与 `dse play` 一致。
两处必须隔离：`sdk.create_engine(entry=...)` 残留的 `DSE_ENTRY` 要清掉；
combat 用全局 `random.random()`，必须同时固定 `engine.rng` 与 `random.seed()`。

### 产出

| 格式 | 内容 | 典型体积 |
|---|---|---|
| `.md` | 可读剧本（正文 / 选项 / 输入 / 状态变化 / 终局表） | ~80 KB |
| `.json` | 结构化 `meta` + `steps[]` + `final_state`，便于程序消费 | ~260 KB |
| `.html` | 单文件阅读版，状态变化折叠 | ~118 KB |

实测真结局：`51 场景步 / 62 次输入 / 51 不同场景 → end-whiterun`，
模式分布 `normal 45 / dialogue 2 / battle 3 / trade 1`。
输入次数大于场景步数，正是一个场景里连问多题、打多回合、走多天所致。

> `export-outline` 是另一层「完整」：**全部 109 个场景**和每条出边的
> 目标 / 类型 / 条件 / 选项文本 / 权重，静态大纲，不跑引擎。
> `export-run` 是某一局的实际走法，两者互补。

全套命令表、退出码契约（`0/1/2/6/130`）、`--json`、`--` 透传、
`.cmd` 字节级铁律、跨目录实测记录、排查表与已知边界见 **`docs/CLI.md`**。

---

## 工程结构

```
skyrim-lifeline/
├── dse.yml                 插件清单 + 状态初值 + 战斗数值表 + 成就表
├── frostwords.cmd         仓库根垫片（FW_ROOT=%~dp0）
├── fwcli.cmd              仓库根垫片 / 缩写（避开 PowerShell 的 fw 别名）
├── content/                内容包（YAML 数据，不是代码）
│   ├── 00-core.yml         序章 · 灵魂链接
│   ├── 10-ch1-frostgate.yml   第一章 · 风隘
│   ├── 11-ch1-trade.yml       灰烬渡口 · 补给
│   ├── 20-ch2-ashford.yml     第二章 · 白漫之下
│   ├── 30-ch3-dragonsreach.yml 第三章 · 根
│   ├── 40-ch4-whiterun.yml    第四章 · 白漫
│   └── 50-endings.yml         结局集（分流闸门 + 八个结局）
├── tools/
│   ├── frostwords_cli.py   CLI 编排层（参数 / 转发 / 退出码）
│   ├── export_run.py       完整流程采集与 md/json/html 渲染核心
│   ├── cli_shim.py         Windows .cmd 垫片生成 / 安装 / 卸载 / 字节自检
│   ├── verify.py           一键门禁（静态 / fuzz / e2e / 结局覆盖）
│   └── solve_e2e.py        e2e 脚本求解器（自动搜出合法通关输入流）
├── docs/
│   ├── CLI.md              CLI 命令表 / 退出码 / 垫片 / 实测 / 排查
│   ├── allin-repocheck-validation.md  以本仓为样本对 `allin` 体检器的实战校验报告（历史快照）
│   ├── allin-fix-verification.md  P0→P3 整改最终验证报告（三态 / 远端证据 / 未修项）
│   ├── design.md           设计文档：机制映射表 + 路径爆炸分析 + 结构约束
│   ├── graph.mmd           场景图（109 场景，Mermaid）
│   └── sample_transcript.txt  序章试玩实录（`dse play --input` 真实输出）
├── tests/
│   ├── e2e_cases.json      e2e 用例数据（由求解器生成，verify.py 消费）
│   └── cli_check.py        CLI 回归（54 项，纯 stdlib）
└── exports/                导出样本：流程实录 + 全场景大纲
```

内容包是**纯 YAML 数据**。没有一行 Python 参与剧情逻辑 —— 这是引擎的设计
哲学（内容即数据，能力即插件），也让内容能被 diff、被 review、被热更。
CLI 同样只做编排，业务逻辑都在 `tools/export_run.py` 里。

---

## 开发

### 门禁

```bash
python tools/verify.py                # 全部门禁（默认每章 40 条 × 5 章 = 200 条路径）
python tools/verify.py --fast         # 跳过 fuzz（只跑 ① ③ ④）
python tools/verify.py --chapter ch2  # fuzz 只从第二章入口起步
python tools/verify.py --samples 100  # 提高每章采样条数（共 500 条路径）

python tests/cli_check.py             # CLI 回归（54 项）
frostwords verify --fast              # 等价，走 CLI 转发（退出码原样返回）
```

四层门禁，缺一不可：

| 层 | 做什么 | 抓什么 | 耗时 |
|---|---|---|---|
| ① 静态 | `dse check` 等价 + 条件字段预声明门 | Schema 不符、悬空跳转、图连通性、旗标拼错 | 毫秒级 |
| ② 动态 fuzz | 真实引擎随机游走采样 | 条件恒假、表达式求值炸、效果写错、场景缺失 | 秒级 |
| ③ e2e 脚本化回放 | 整条通关路径的最终场景与状态断言 | 选项编号漂移、结局不可达、状态断言失败 | 秒级 |
| ④ 结局覆盖门 | 每个结局有静态可达(S) 或 e2e 已回放(E) 来源 | 孤儿结局、只静态可达却跑不到的结局 | 毫秒级 |

> **为什么不用 `dse traverse` 全图遍历？**
> traverse 是穷举 DFS，路径数 = 各节点出度之乘积。本作分支因子 2–3、深度 78，
> 全图路径数约 **2.37 × 10²⁸** —— 数学上不可行（实测跑 7 分半未完成）。
> 引擎为此提供的答案是 `dse coverage --e2e`（用 e2e 用例声明结局来源）。
> 详见 `docs/design.md` §四「路径爆炸」。

### 生成 e2e 脚本

e2e 用例需要真实的玩家输入流，手写极易出错（选项编号 / `a`/`d`/`r` /
`ask N` / `next` 五种协议）。用求解器自动生成：

```bash
python tools/solve_e2e.py --target end-whiterun    # 求单条
python tools/solve_e2e.py --all --write-cases      # 全量求解并回写 tests/e2e_cases.json
```

求解器**每一步都用真实引擎试跑**，不手写模拟引擎语义（五种 mode 的
`do_ask` 检查顺序、trade 天数、battle 回合数都踩过坑），因此产出的脚本
必然可跑。`verify.py` 会读 `tests/e2e_cases.json` 执行回放。

> **改动任何内容包后必须重跑 `--all --write-cases`** —— 选项编号会漂移，
> 旧脚本会走到完全不同的分支。

### 写新内容时必须遵守

1. **藤蔓结构**：一个节拍的多条支路要在 1–2 跳内汇入同一后继。
   支路只改变**过程**（`onEnter` 效果、`extraText` 差异），不复制**下游**。
2. **加权分支同理**：`obey` / `defy` 两条支路必须汇入同一后继场景。
3. **结局场景只能有 `@` 目标选项** —— 引擎 `is_ending` 判定是「无选项，
   **或所有选项的 `goto` 都以 `@` 开头**」。所以可以给结局加
   `「（重新开始。）」→ @restart` 出口而不丢结局身份；但凡有一个普通
   `goto`，它就不算结局，coverage 门禁统计不到。
4. **条件里的字段必须在 `state.initial` 预声明** —— 否则静默判 False。

违反 1–2 条不会让游戏出错，但会让 traverse 跑不完。

> **随机性坑**：引擎 combat 插件用全局 `random.random()`，不受 `engine.rng`
> 控制。`verify.py` / `solve_e2e.py` 都同时固定了全局种子，否则同一条
> e2e 脚本两次跑会走出不同结局。

> **进程环境坑**：`sdk.create_engine(entry=...)` 会把 `DSE_ENTRY` 写进
> `os.environ` 且**从不清理**。fuzz 按章起步后若不逐层清掉，后续 e2e 会
> 从错误的入口开始，输入流整体错位（实测全部用例莫名停在中途的 `ch4-*`
> 场景）。`verify.py` 在每个样本、每条用例前都做了显式隔离。

### 验收基线（`@SIWPAN` 本机实测，他机数值不适用）

| 检查 | 命令 | 结果 |
|---|---|---|
| 静态图 | `dse check` | `109 场景 / 8 结局（可达 8）`，无悬空、无不可达 |
| 引擎自检 | `dse doctor` | 健康 |
| 全量门禁 | `python tools/verify.py` | `200 条随机路径`、`覆盖 87/109 场景 (80%)`、8 条 e2e 全过、8 个结局均 `SE`、`✓ 全部门禁通过` |
| CLI 回归 | `python tests/cli_check.py` | `PASS 54  FAIL 0  SKIP 0` |
| 全结局批量导出 | `frostwords export-run --all-endings --format md,json,html` | 8/8 结局成功，`48–52 场景步`，25 个文件共 `3,621,848 B` |
| 跨目录调用 | 在 `C:\Windows` 下执行 PATH 垫片 `fwcli export-run` | `49 场景步 → end-alone`，`rc=0` |
| 垫片字节 | `cli_shim.inspect_shim()` | `ascii=True, bare_lf=0, lone_cr=0, quoted_call=True, marker=True` |
| 跨仓实战校验（校验时点） | `<ALLIN_ROOT>` 的 `tools/repocheck` 扫 `<REPOS_ROOT>` | 〔本机〕暴露发现层假阴性 `139 只认出 138`、库级 `score 6.0 / 0.442 / error 4` |
| 跨仓实战校验（整改后） | 同上 + 治理门禁 | 〔本机〕`139/139` 发现、样本 `score 10.0 / 1.0 / error 0`、规则 6 修复使 `24 仓转绿 / 0 回归`、`check:governance 20/20 clean` |
| 建仓推送 | Gitee 私有 → 一次性 URL 推送 → 转公开 | 〔本机〕`ls-remote` 与本地 HEAD 一致、匿名 clone `32/32` 文件 + 3 份 blob sha 一致、`.git/config` 无凭据 |

> `verify.py` 耗时是**时点值**（本机两次分别 `45.6s` / `78.5s`，差异来自并发负载），
> 不作门禁断言；断言的是「全部门禁通过」与覆盖结果。
>
> CLI 回归里出现的 `[ERR] 已中断` 是有意触发 `KeyboardInterrupt`
> 验证退出码 `130`，不是失败。
>
> 本仓作为 `<ALLIN_ROOT>` 的实战校验样本，校验时点完整实测（复现代码、30 条规则
> 明细、缺陷定位、假阳性分析）见 `docs/allin-repocheck-validation.md`；
> **P0 → P3 整改的最终结论、三态与未修项见 `docs/allin-fix-verification.md`**。
> 校验阶段刻意保留「无 `.git` / 无依赖声明 / 无 LICENSE」以复现漏检，
> 该状态不代表当前工程状态；当前仓已纳入版本控制并推送到公开远端。

---

## 设定考据

- **海尔根 (Helgen)**：4E 201 龙裔之战开场，龙焰焚城之地
- **风暴斗篷 (Stormcloaks)**：内战一方，斥候深入龙巢侦察
- **龙焰 / 龙吼 (Thu'um)**：龙族的力量，诺德人借血继承，可推开、烧毁、点燃
- **灵魂链接**：帝国末年法师的意识通讯装置，两端都要付费
- **九界与创世**：阿努与帕多密，十二世界，尼迩，法师之神马格努斯的陨落

> 同人作品。Bethesda Softworks 与其母工作室拥有《上古卷轴》系列的版权。
> 本项目为非商业同人创作，与 Bethesda 无关联。

---

## License

MIT © 2026 siwpan

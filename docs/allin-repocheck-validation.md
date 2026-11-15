# allin 实战校验报告 · `repocheck` × `skyrim-lifeline`

> **状态横幅（2026-11-15 更新）**：本报告的观测与「未改动 / 待授权」表述是
> **校验时点的历史快照**。整改已按 P0 → P3 推进：P0 已落地并提交
> `allin@105eab0`，其余批次见文末「整改台账」与最终验证报告。
> 请勿把本报告中的「未改」当成当前状态。

---

## §0 口径约定：哪些是通用结论，哪些是本机事实

> 本文件会随 `skyrim-lifeline` 推送到公开远端。**凡涉及绝对路径、仓数、
> 锚点数、解释器版本、日期与具体实测数值的，都是 `@SIWPAN` 的单点观测，
> 不是跨机器通用结论。** 他机请勿照抄，按占位符现场复测。

| 占位符 | 含义 | 他机怎么取 |
|---|---|---|
| `<PYTHON>` | 装有 `dse-core` 的 Python 解释器 | `python -c "import sys; print(sys.executable)"` |
| `<ALLIN_ROOT>` | `allin` 仓根 | 以**该机** `docs/事实源/机器分区索引.md` 的仓根口径为准 |
| `<REPOS_ROOT>` | 发布区根（一级子目录为各仓） | 同上；**不要用下表的盘符** |
| `<PROJECT_ROOT>` | 本仓根目录 | `<REPOS_ROOT>/skyrim-lifeline` |
| `<SHIM_DIR>` | 该机已在 PATH 的垫片目录 | 以 `install-cli` 输出为准 |

### 本机事实表（仅 `@SIWPAN`，时点 2026-11-15）

| 项 | 时点值 | 观测方式 |
|---|---|---|
| 机器标识 | `@SIWPAN`（hostname `siwpan`） | `g20-facts` 门禁输出「当前机器（siwpan）」 |
| `<ALLIN_ROOT>` | `D:\projects\allin` | 本机目录实测 |
| `<REPOS_ROOT>` | `D:\projects\repos` | 本机目录实测 |
| `<PROJECT_ROOT>` | `D:\projects\repos\skyrim-lifeline` | 本机目录实测 |
| `<PYTHON>` | `E:\Python314\python.exe`（3.13.14） | `sys.executable` |
| `<SHIM_DIR>` | `E:\Python314\Scripts`（已在 PATH） | `install-cli` 输出 |
| `dse-core` 版本 | `0.6.0` | `importlib.metadata.version` |
| 发布区一级目录 | **139** 个 | `<REPOS_ROOT>` 下 `iterdir()` |
| 远端清单 | **139** 个远端仓 / **145** 条锚点 | `platform check-repos` |
| repocheck 版本 | `2.1.0`（schema 2，30 条规则） | `scanner.__version__` |
| allin HEAD（校验时） | `49cbeaa` | `git log -1` |

> **失效条件**（沿用 allin 机器事实源口径）：换机、加减盘、重装系统、
> 换运行时版本后**立即失效**；每次涉及机器事实的动作前**现场复测**。
> **上位判据**：他机各自检出的 `<ALLIN_ROOT>/docs/事实源/机器分区索引.md`
> §0 归属规则 —— 机器独有事实只写该机分区文件；引用「本机」必须带机器名，
> 裸写不合格；跨机共识才写总索引。本文**不新增、不修改**任何机器分区文件，
> 只做标注，避免同一数值两处漂移。

### 跨机器成立的通用结论（不含本机事实）

- `scanner.py::_is_project()` 用 `enumerate(os.walk())` 的 yield 序号当目录层级 —— 结构性缺陷，与盘符 / 仓数无关（§2）
- 修复补丁与「不得因修复放宽深度上限」的正反回归用例（§2）
- 无 `.git` ⇒ 7 条 git 规则整组跳过、健康分上限压到 6.0（§3）
- 静态第三方白名单 / README 字面关键词导致的两类假阳性机理（§4）
- `--fail-on error` 的 fail-closed 语义（§5）

> 校验阶段**全程只读**：不联网、不执行被测项目代码；整改阶段的改动另见
> 文末整改台账。

---

## TL;DR

| 项 | 实测结论 | 状态 |
|---|---|---|
| 发布区识别 | 〔本机〕139 个一级目录，`discover_projects()` 只认出 **138** 个，`skyrim-lifeline` 被漏掉 | ❌ **工具缺陷** |
| 根因 | 〔通用〕`scanner.py::_is_project()` 把 `enumerate(os.walk())` 的**迭代序号**当成目录深度 | 已定位 + 补丁已落地 |
| CLI 直跑 | 〔本机〕`repocheck <REPOS_ROOT> --exclude <其余仓>` → `rc=3 未发现任何项目` | 复现成功 |
| 库级体检（绕过发现层） | 〔本机〕`score 6.0` / `pass_rate 0.442` / `error 4, warn 5, info 2` / `skipped 11` / `rule_errors 0` | ✅ 规则引擎正常 |
| CI 语义 | 〔通用〕项目能被识别时 `--fail-on error` 正确返回 `rc=1`（fail-closed 有效） | ✅ |
| 假阳性 | 〔通用机理〕2 处：`dse_core` 被报 import 断裂；README 被报「缺用法/示例」 | ⚠️ 规则口径问题 |
| 其它 allin 入口 | 〔本机〕`platform check-repos` 通过（139 远端仓 / 145 锚点一致）；`status --json` gates `failed=0` | ✅ |
| 代码改动 | 校验时点：无；整改后：**P0 已落地**，见文末整改台账 | ✅ 已提交 |

> 一句话：这个「无 `.git`、无 marker 文件、`.py` 全在靠后子目录」的新仓，
> 恰好命中了 allin 体检器项目发现层的一个假阴性边界 —— 这就是它作为实战样本的价值。

---

## 1. 实测流程（按实际跑通的顺序，非文档预设）

| # | 动作 | 实际结果 |
|---|---|---|
| ① | 读 `allin/README.md` + `tools/repocheck/README.md` + `main.py --help` | 确认体检器 30 条规则、`--fail-on` 五档、退出码 0/1/2/3 |
| ② | 读 `scanner.py::discover_projects` | 口径是「**一级子目录**」；仅当未发现任何子项目且 root 自身像项目时，才把 root 当单项目 |
| ③ | `allin_cli.py status --json` / `platform check-repos` | 〔本机〕正常；`check-repos`：139 远端仓、145 条清单锚点一致 |
| ④ | `repocheck <REPOS_ROOT> --exclude <其余仓名> --format json` | **`rc=3`、stdout 空、`未发现任何项目`** |
| ⑤ | 直接调 `scanner._is_project()` 调试 + 临时目录最小复现 | 〔通用〕定位假阴性根因（见 §2） |
| ⑥ | 绕过发现层调 `scanner.check_project()` | 〔本机〕拿到完整 30 条规则报告（见 §3） |
| ⑦ | 临时沙箱 `copytree` + 补 `pyproject.toml`，跑完整 CLI 两档 `--fail-on` | 〔通用〕`rc=0` / `rc=1`（见 §5） |
| ⑧ | 内存中实现修正版 `_is_project` 并复算发布区 | 〔本机〕`138 → 139`（见 §2 补丁验证） |

> **文档里的 `python main.py <目录>` 对本样本不成立**：直接把
> `skyrim-lifeline` 当 root，会把 `content/ docs/ exports/ saves/ tests/ tools/`
> 六个子目录当成候选项目（其中 `tools/`、`tests/` 含 `.py`），产生假阳性。
> 正确口径是扫发布区、排除其余仓。

---

## 2. 发现 A（P0）：项目发现层假阴性

### 现象

```
〔@SIWPAN 时点值，他机数值不适用〕
discover_projects(<REPOS_ROOT>, depth=2)  → 138 个
一级目录总数                              → 139 个
skyrim-lifeline 在其中                     → False
```

### 最小复现（临时目录，未落盘到工程）

| 构造 | 原版 `_is_project` | 修正版 |
|---|---|---|
| 6 个子目录 `content/docs/exports/saves/tests/tools`，`.py` **只在最后一个** `tools/` | `False` | `True` |
| 同一个 `.py` 再复制一份到**第一个** `content/` | `True` | `True` |
| 把 `--depth` 提到 8 | `True` | `True` |
| 真实仓 `skyrim-lifeline` | `False` | `True` |

### 根因

`tools/repocheck/scanner.py:163-171`：

```python
for depth, (_dirpath, dirnames, filenames) in enumerate(os.walk(directory)):
    dirnames[:] = [d for d in dirnames if d not in exclude]
    if depth > max_py_depth:
        dirnames[:] = []          # ← 只截断当前 yield 的下钻
        continue                  # ← 且跳过本层 filenames 检查
    if any(f.endswith(".py") for f in filenames):
        return True
```

`os.walk()` 是**广度优先按目录逐个 yield**，`enumerate()` 给的是「第几个 yield」，
不是「第几层目录」。`max_py_depth=2` 时，只有前 3 个 yield 会检查 `.py`，
第 4 个起一律 `continue`。

本样本的六个一级子目录按字母序为
`content(1) docs(2) exports(3) saves(4) tests(5) tools(6)`，
而 `.py` 只存在于 `tests/`、`tools/`，两个都排在阈值之后 → 永远不被检查。
加上它既无 `.git`、也无 `package.json` / `Cargo.toml` / `pyproject.toml`，
三条判据全落空 → 整个仓被漏检。

**影响面**（通用）：任何「一级子目录 ≥ 4 且 `.py` 只分布在靠后子目录」且无 marker
的仓都会漏检。〔本机〕发布区实测命中 1 个（139 中漏 1），但这是结构性缺陷，
不是个例。

### 修复补丁（校验时内存验证；P0 已落地到 allin）

```python
for dirpath, dirnames, filenames in os.walk(p):
    depth = len(pathlib.Path(dirpath).relative_to(p).parts)   # ← 真实层级
    dirnames[:] = [d for d in dirnames if d not in exclude]
    if depth > max_py_depth:
        dirnames[:] = []
        continue
    if any(f.endswith(".py") for f in filenames):
        return True
```

| 验证项 | 结果 |
|---|---|
| 最小复现 6 子目录 | `False → True` |
| 真实仓 `skyrim-lifeline` | `False → True` |
| 发布区发现数 | 〔本机〕`138 → 139` |
| 补丁新增识别 | 恰为 `<PROJECT_ROOT>` |

建议的回归用例（放进 `tools/repocheck/test_scanner.py`）：
构造 N=6 个子目录、`.py` 仅置于字典序最后一个，断言
`discover_projects(tmp, max_py_depth=2)` 包含该目录；
再断言 `depth=0` 的 `.py` 仍被识别，防止改坏原语义。

---

## 3. 发现 B：30 条规则体检报告（`check_project()` 直跑；数值为〔@SIWPAN 本机实测〕）

### 指标

| 指标 | 实测值 | 说明 |
|---|---|---|
| `score` | **6.0** | 与 `repocheck/README.md` 声明一致：无 `.git` ⇒ **分数上限压到 6.0** |
| `pass_rate` | `0.442` | 文档提示需与 score 一起看，此处得到印证 |
| `findings` | 19 条判定 | 30 条规则 − 11 条 skip |
| `severity_counts` | `error 4 / warn 5 / info 2` | 未通过项共 11 条 |
| `issues` | 9 条 | 仅 error/warn |
| `skipped` | 11 条 | 7 条 `no-dotgit`、2 条 `no-license-file`、1 条 `no-security-file`、1 条 `no-workflow` |
| `rule_errors` | `[]` | 规则自身无异常 |
| `metrics` | `py_files=6`、`total_files=47`、`has_git=False`、`degraded=False`、`truncated=False` | 未走降级实现 |

### 4 个 error

| 规则 # | 标签 | 判定 | 性质 |
|---|---|---|---|
| 1 | 无版本控制（缺 `.git`） | 项目目录内无 `.git` | 真实缺口 |
| 4 | 无依赖声明 | 无 `requirements.txt` / `pyproject.toml` / `package.json` / `Cargo.toml` | 真实缺口 |
| 5 | 无 LICENSE | 根目录无 `LICENSE*` 等 | 真实缺口（README 末尾写了 MIT，但无文件） |
| 11 | README 结构不完整 | 「缺少 用法/示例 相关内容」 | ⚠️ 假阳性，见 §4 |

### 5 个 warn

`疑似 import 断裂风险：dse_core`（⚠️ 假阳性）、`无 SECURITY.md`、`无 CONTRIBUTING`、
`CHANGELOG 结构不合格`、`无 CI 配置`。

### 11 条 skipped 分类

| 原因 | 规则 # |
|---|---|
| `no-dotgit` | 17, 18, 20, 21, 22, 23, 29 |
| `no-license-file` | 9, 10 |
| `no-security-file` | 14 |
| `no-workflow` | 25 |

> 这一层验证了 allin 文档里「跳过项不计入分母、但压低分数上限」的实现是真的：
> `has_git=False` 时 7 条 git 规则整组跳过，分数精确落在 6.0 上限。

---

## 4. 发现 C：两处假阳性

| # | 报告内容 | 实测反证 | 判断 |
|---|---|---|---|
| 1 | `疑似 import 断裂风险：dse_core` | 〔本机〕`importlib.metadata.version("dse-core")` 返回已安装（版本见 §0 本机事实表），且本项目 6 个工具全部依赖它 | 〔通用〕规则用**静态常见第三方白名单**做启发式，非常见 PyPI 包必然误报；文档也注明「静态启发式、不执行代码」 |
| 2 | `#11 README 结构不完整：缺少 用法/示例` | README 有「快速开始」、多个 ``` 代码块、`dse play` / `frostwords` 命令表、`docs/CLI.md` 完整命令表 | 规则按「用法」「示例」**字面关键词**匹配，实测两词均不存在，而「快速开始」存在 → 关键词表偏窄 |

---

## 5. 发现 D：CI 退出码与 workaround（临时沙箱，未改真实仓）

在 `tempfile` 里 `copytree` 一份样本、补一个最小 `pyproject.toml`
（`PROJECT_MARKER_FILES` 之一），让发现层立刻返回 True，再跑完整 CLI：

| 命令 | `rc` | `score` | `pass_rate` | `error` 数 |
|---|---|---|---|---|
| `--fail-on none` | `0` | 6.0 | 0.512 | 3 |
| `--fail-on error` | **`1`** | 6.0 | 0.512 | 3 |

- 补依赖声明后，规则 4 由 fail 转 pass：`error 4→3`、`pass_rate 0.442→0.512`。
- **`--fail-on error` 的 fail-closed 语义正常** —— 问题只在「发现不到项目」，
  不在判定与退出码。
- 注意 `requirements.txt` **不在** `PROJECT_MARKER_FILES` 里：加它能过规则 4，
  但**不能**解决漏检；只有 `pyproject.toml` / `package.json` / `Cargo.toml` / `.git` 能。
- `--depth 8` 也能绕过（放宽序号阈值），但会放大下钻范围，不推荐当修法。

### 修复前可用的两条 workaround（历史记录；P0 落地后已不需要）

```python
# ① 库级：绕过发现层，直接对单仓跑 30 条规则
import sys; sys.path.insert(0, r"<ALLIN_ROOT>/tools/repocheck")
import scanner
r = scanner.check_project(r"<PROJECT_ROOT>")
```

```bash
# ② CLI 级：给样本加一个 marker 文件（pyproject.toml）后再扫发布区
<PYTHON> <ALLIN_ROOT>/tools/repocheck/main.py <REPOS_ROOT> \
  --exclude <其余仓名> --format json --fail-on error
```

> P0 修复后，② 里的 `pyproject.toml` 不再必要 —— 发现层现在按真实路径层级判定。

二者在校验时点是**迁就工具缺陷的 workaround**，不是修法。修法见 §2 补丁。

---

## 6. 其它 allin 入口（〔@SIWPAN 本机实测〕顺带观测）

| 命令 | 输出要点 |
|---|---|
| `allin_cli.py status --json` | 〔本机〕`gates.failed=0 / skipped=0 / escapeRate=0.0`（lastRun 2026-11-13T09:45:32Z）；`orchestration.routes=16 / drift=0 / healthy=true`；`platform.readable=false, total=0`；`corrupt=[]` |
| `allin_cli.py platform check-repos` | 〔本机〕`远端实测：siwpan 共 139 个仓库` / `通过：145 条清单锚点一致` |

> 〔通用〕`check-repos` 校验的是**清单锚点**，不是本地目录发现，因此不覆盖 §2 的
> 假阴性，两者不矛盾。〔本机〕校验时点未跑全量 `run_all_gates.sh`（聚焦 repocheck
> 单组件）；整改阶段已补跑 `check:governance`，20/20 clean。

---

## 7. 整改台账（2026-11-15 更新；取代校验时点的「待授权」表述）

| 批次 | 内容 | 状态 | 可见证据 |
|---|---|---|---|
| P0 | 修 `scanner.py` 深度口径 + 2 条正反回归用例 | ✅ **已验证** | allin commit `105eab0`；`pytest` 67 项全绿；发布区 `138 → 139`；`check:governance` 20/20 |
| P1 | 本机事实标注（本文 §0 + README / `docs/CLI.md` 口径块 + 跨项目写作规范） | ✅ **已验证** | 本文件 §0 与文末占位符复现命令 |
| P2 | 样本仓版本控制、依赖声明、LICENSE 与治理骨架 | ⏳ 见最终验证报告 | — |
| P3 | 完整复跑 / 建仓推送 / 整改验证报告 | ⏳ 见最终验证报告 | — |

**三态**：✅ 已验证 / ⏳ 进行中 / ❌ 未修（须写明理由）。校验时点标注的
「未改 `.git` / 依赖声明 / LICENSE」是**当时刻意保留复现条件**，不代表最终状态；
以最终验证报告为准。

**未修项及理由**：

| 项 | 理由 |
|---|---|
| 规则 6 的 `dse_core` 假阳性 | repocheck 是通用工具，不应为单一项目硬编码包名；建议改为 `importlib.metadata` 实查，属 allin 侧独立立项 |
| 规则 11 的 README 关键词表 | 建议补「快速开始 / Quick Start / Usage」，同样属 allin 规则口径，不与 P0 同批 |
| 全量 `run_all_gates.sh` | 本批已跑 `check:governance`（含 g20-facts）与 repocheck 全量测试；全量门禁留待 P3 最终回归 |

> 〔本机事实〕`105eab0` 是 `@SIWPAN` 上 allin 本地 master 的提交；
> 他机 allin 仓的 HEAD 各不相同，**请勿据此判断他机是否已含此修复** ——
> 应按 §0 占位符现场复测 `discover_projects`。

---

## 8. 一键复现（只读；他机先按 §0 替换占位符）

```bash
<PYTHON> - <<'PY'
import sys, pathlib
sys.path.insert(0, r"<ALLIN_ROOT>/tools/repocheck")   # 换成该机 allin 仓根
import scanner
root = pathlib.Path(r"<REPOS_ROOT>")                  # 换成该机发布区根
target = root / "skyrim-lifeline"
print("一级目录:", len([p for p in root.iterdir() if p.is_dir()]))
print("发现项目:", len(scanner.discover_projects(root, max_py_depth=2)))
print("目标仓 _is_project:", scanner._is_project(target, scanner._merge_exclude(None), 2))
r = scanner.check_project(str(target))
print("score/pass_rate/errors:", r["score"], r["pass_rate"], r["severity_counts"])
PY
```

> 期望（**跨机通用**）：修复后 `发现项目 == 一级目录`、`_is_project is True`；
> 具体数字、盘符、解释器**不作通用断言**，一律以现场实测为准。

# 整改验证报告 · `skyrim-lifeline` × `allin` 完整实战校验链路

> **本报告是 P0 → P3 整改战役的最终验证结论**，取代
> `docs/allin-repocheck-validation.md` 里所有「待授权 / 未改动 / 进行中」表述。
> 校验时点的观测保留在那份报告里作为历史快照，不回写、不追平。
>
> **状态横幅（2026-11-15 后续批次）**：§1 / §6 中「74 仓规则 6 仍红」
> 与「全量 `run_all_gates.sh` 未跑」已被同一天的后续批次转绿并实跑，
> 详见 **§9 追加批次：规则 6 全绿与全量门禁**。旧行保留为历史时点记录，
> 以 §9 为最终结论。数值平衡与 HTML 导出能力亦已在后续批次修复。

---

## §0 口径约定：本机事实不得当通用结论

> 本文件随本仓推送到公开远端。**凡绝对路径、盘符、仓数、锚点数、解释器版本、
> commit hash、字节数、耗时与「实测」数值，都是 `@SIWPAN` 单机时点事实**
> （2026-11-15），不是跨机器通用结论。他机请勿照抄，按占位符现场复测。

| 占位符 | 含义 | 他机怎么取 |
|---|---|---|
| `<PYTHON>` | 装有 `dse-core` 的解释器 | `python -c "import sys; print(sys.executable)"` |
| `<ALLIN_ROOT>` | `allin` 仓根 | 以**该机** `docs/事实源/机器分区索引.md` §0 口径为准 |
| `<REPOS_ROOT>` | 发布区根（一级子目录为各仓） | 同上；**不要照抄下表盘符** |
| `<PROJECT_ROOT>` | 本仓根 | `<REPOS_ROOT>/skyrim-lifeline` |
| `<SHIM_DIR>` | 该机已在 PATH 的垫片目录 | 以 `install-cli` 输出为准 |

### 本机事实表（仅 `@SIWPAN`，时点 2026-11-15）

| 项 | 时点值 | 观测方式 |
|---|---|---|
| `<ALLIN_ROOT>` | `D:\projects\allin` | 本机目录实测 |
| `<REPOS_ROOT>` | `D:\projects\repos` | 本机目录实测 |
| `<PYTHON>` | `E:\Python314\python.exe`（3.13.14） | `sys.executable` |
| `<SHIM_DIR>` | `E:\Python314\Scripts`（已在 PATH） | `install-cli` 输出 |
| 发布区一级目录 / 发现项目 | **139 / 139** | `iterdir()` × `discover_projects()` |
| repocheck 版本 | `2.1.0`（schema 2，30 条规则） | `scanner.__version__` |
| allin 三端 HEAD | `d7b70d5` | `rev-parse HEAD` × `git ls-remote` × 2 |
| 本仓推送 HEAD | `68532dc` | `rev-parse HEAD`，匿名 clone 复核一致 |
| 远端仓 | `gitee.com/siwpan/skyrim-lifeline`（public, MIT, `master`） | Gitee API `status` |
| 治理门禁 | `20/20 clean` | `npm run check:governance` |
| Node / npm | `v22.22.2` | `node --version` |

> **失效条件**：换机、加减盘、重装系统、换运行时版本后**立即失效**；
> 每次涉及机器事实的动作前**现场复测**。
> **上位判据**：`<ALLIN_ROOT>/docs/事实源/机器分区索引.md` §0 与 `g20-facts`
> 的 `self-identity` / `self-anchor` / `self-ownership` 门禁 —— 机器独有事实
> 只写该机分区文件；引用「本机」必须带机器名，裸写不合格；跨机共识才写总索引。
> 本批次**未新增、未修改**任何机器分区文件。

### 标注口径

- 〔本机〕= `@SIWPAN` 单点时点观测，数值不可跨机照抄。
- 〔通用〕= 与盘符 / 仓数 / 版本 / 提交号无关的结构性结论。
- **三态**：✅ 已验证（有可见执行证据） / ⏳ 进行中 / ❌ 未修或未验证（**必须写明理由**）。
- commit hash 一律标注「哪台机器的哪条分支」；rebase 会把 hash 全部改写，见 §2。

---

## §1 TL;DR

| 批次 | 目标 | 状态 | 〔通用〕结论 | 〔本机〕关键证据 |
|---|---|---|---|---|
| P0 | 修 `repocheck` 发现层假阴性 | ✅ 已验证 | `enumerate(os.walk())` 的 yield 序号不是目录层级；改用 `len(Path(dirpath).relative_to(base).parts)` | `139 一级目录 → 139 发现项目`；2 条正反回归用例；`allin@3b0b407` |
| P1 | 本机事实标注，避免误导他机 | ✅ 已验证 | 口径块 + 占位符 + 〔本机〕/〔通用〕 + 事实源上位判据，是跨项目写作规范 | 报告 §0、`README.md`、`docs/CLI.md` 口径块；用户级 `MEMORY.md` 写作铁律 |
| P2 | 治理落地 | ✅ 已验证 | 版本控制 / 依赖声明 / 许可 / 安全 / 贡献 / 变更日志 / CI / SAST / registry 登记 | 样本仓 `6.0/0.442/error 4 → 10.0/1.0/error 0`；`g17` 终态 `147 条目 / 138 已登记 / 0 阻断` |
| P2′ | 工具侧第二处缺陷（规则 6） | ✅ 已验证 | 静态白名单必须让位于**项目自己的依赖声明**；不得为单仓硬编码包名 | `24 仓 fail→pass`、`0 回归`、`74 仍红`；3 条回归用例；`allin@67dc184` |
| P3 | 全量复跑 + 建仓推送 + 报告 | ✅ 已验证 | 推送验收必须取权威远端证据（`ls-remote` + 匿名 clone 内容级比对），不凭 push 输出 | `20/20 clean`；`g04` 双远端 `IN_SYNC`；匿名 clone `32 文件` + blob sha 一致 |
| P4（后续批次） | 74 仓规则 6 转绿 | ✅ 已验证 | 先分工具侧误报与各仓真实缺口；运行时注入模块用**可审计的仓内声明**，不造 pip 包、不编 `-e` 路径 | 〔本机〕`139 仓 / R6_red=0`；工具侧 4 提交；52 仓 manifest 提交，51 仓 local=remote |
| P5（后续批次） | 全量 `run_all_gates.sh` | ✅ 已验证 | 门禁结论只认最终 summary，不以单项通过代替全量 | 〔本机〕`GATES_RC=0`；`ALLIN_GATE_SUMMARY status=clean fail=0 skips=0 not_applicable=0` |
| — | `v0.1.0` tag 推送 | ✅ 已验证 | tag 必须回读 `refs/tags/*` 与 peeled 目标，不以本地存在为准 | `git ls-remote --tags` 回读成功；指向 `68532dc`（首个可校验版本），不含后续文档提交 |
| — | 远端 CI 实跑 | ❌ **未验证** | GitHub Actions workflow 只在 GitHub 侧触发 | 本仓当前**只有 Gitee 远端**；本地 YAML 语法与等价门禁已过，runner 实跑未发生 |
| — | 剧情数值平衡 | ✅ 已验证（后续批次） | 声明式 bounds + fatal 属引擎通用护栏，不靠改文案掩盖数值越界 | 〔本机〕7 字段钳制 + 早期体温 fatal；真结局 `hp=0/soul=0/trust=100`；详见 §9 与本仓 `design.md` §3.1 |

---

## §2 P0 复验：发现层假阴性

〔通用〕根因：`scanner._is_project()` 把 `enumerate(os.walk(directory))` 的
**yield 序号**当成目录深度；多个兄弟目录时，字典序靠后的 `tools/`、`tests/`
会在到达前被 `depth > max_py_depth` 提前剪枝。修复用真实路径层级：

```python
base = Path(directory).resolve()
for dirpath, dirnames, filenames in os.walk(base):
    depth = len(Path(dirpath).relative_to(base).parts)   # ← 真实层级
```

| 复验项 | 〔本机〕结果 |
|---|---|
| 最小复现（6 兄弟目录，`.py` 只在最后一个） | `False → True` |
| 真实仓 `<PROJECT_ROOT>` | `False → True` |
| 发布区发现数 | `138 → 139`（= 一级目录数） |
| 修复未放宽深度上限 | 反例：`.py` 在 depth=3 时 `max_py_depth=2` 仍不发现 |
| 回归用例 | `tools/repocheck/test_scanner.py` 2 条；`pytest tools/repocheck/` 70 项全绿 |

> **commit hash 订正（重要）**：校验时点写入旧文档的 `allin@105eab0` 是
> **rebase 前的本地 hash**。本批次为消解 `g04` 的 `DIVERGED`，把 3 个本地提交
> rebase 到远端 `71da92b` 之上，hash 全部改写：
>
> | 语义 | rebase 前 | rebase 后（远端 master） |
> |---|---|---|
> | P0 发现层修复 | `105eab0` | **`3b0b407`** |
> | P2 规则 6 修复 | `ad77faa` | **`67dc184`** |
> | P2 registry 登记 | `fb4cdd1` | **`d7b70d5`** |
>
> 〔本机〕rebase 前的完整快照保留在 `allin` 本地分支
> `backup/pre-rebase-20261115`（`fb4cdd1`），可回滚；远端从未包含旧 hash。
> **他机请以自己 `allin` 仓的 `git log` 现场复测，不要按上表 hash 判断。**

---

## §3 P1 复验：本机事实标注

〔通用〕落地内容：

1. `docs/allin-repocheck-validation.md` 增 §0 口径约定、本机事实表、失效条件、
   跨机通用结论清单；TL;DR 与表格逐条标〔本机〕/〔通用〕。
2. `README.md` / `docs/CLI.md` 增口径块；命令示例改用占位符，不再写死盘符与解释器。
3. 用户级 `MEMORY.md` 写入「跨项目写作铁律」：本机事实必须标注，不得当通用内容；
   裸写「本机」视为不合格，引用需带机器名。
4. 三态分清：远端 CI、未跑的门禁、未修的缺陷一律不写成「通过」。

〔本机〕`g20-facts` 复核：`SIWPAN.md` 时点 2026-11-08（7 天前，在窗口内），
另两台机器分区文件按「非当前机器，留待该机自验」SKIP —— **SKIP 不是通过**。

---

## §4 P2 复验：治理落地

### 4.1 样本仓本体（30 条规则全绿）

| 指标 | 校验时点 | 整改后 |
|---|---|---|
| `score` | 〔本机〕`6.0`（无 `.git` ⇒ 上限压到 6.0） | **`10.0`** |
| `pass_rate` | `0.442` | **`1.0`** |
| `error / warn / info` | `4 / 5 / 2` | **`0 / 0 / 0`** |
| `skipped` | `11`（7 条 `no-dotgit` 等） | `0` |

〔本机〕落地文件：`.gitignore`、`pyproject.toml`（`dse-core>=0.6.0,<0.7`）、
`LICENSE`（MIT 逐字原文 + Bethesda 同人免责声明）、`SECURITY.md`、
`CONTRIBUTING.md`、`CHANGELOG.md`、`.github/workflows/verify.yml`、
`.github/dependabot.yml`、`.semgrep.yml`、仓库根 `frostwords.cmd` / `fwcli.cmd`，
分两次提交 `299a582` → `68532dc`。

〔通用〕`pyproject.toml` 同时是 `PROJECT_MARKER_FILES` 之一，但**修复后已不依赖它**
才能被发现 —— 发现层现在按真实路径层级判定（§2）。

### 4.2 工具侧：规则 6 静态白名单假阳性

〔通用〕根因：`COMMON_THIRD_PARTY` 是硬编码全局白名单，不读项目依赖声明；
「白名单外但已在 `pyproject.toml` / `requirements*.txt` 声明」的包必被误报。
**正确修法不是把某个项目的包名塞进全局白名单**，而是让工具读项目自己的事实源：

```python
def _declared_dependency_bases(ctx) -> set[str]:
    # pyproject.toml [project].dependencies / optional-dependencies / [tool.poetry]
    # + 根级 requirements*.txt；PEP 503 规范化 -_. → _，dse-core → dse_core
```

`_check_broken_imports()` 的 risk 判据追加 `and base not in declared`。

〔本机〕发布区 **139 仓 × 2 遍**全量对账（耗时 217.8s）：

| 指标 | 结果 |
|---|---|
| 发现项目 / 一级目录 | `139 / 139` |
| 由 `fail → pass` 的仓 | **24**（含 `skyrim-lifeline`，另有 `pygame` / `jieba` / `openai` / `moviepy` 等合法声明） |
| 由 `pass → fail` 的**回归** | **0** |
| 修复后规则 6 仍报红 | **74**（各自依赖声明缺口或内部模块未声明，属各仓自身整改，不在本批次）*→ 后续批次已清零，见 §9* |

〔本机〕回归用例 3 条（已声明放行 / 未声明仍报红 / `requirements.txt` 也作事实源），
`pytest tools/repocheck/` **70 项全绿**；`allin@67dc184`。

### 4.3 规则 11 的口径复核（订正历史判断）

校验时点报告把它写成「两处假阳性」之一。复核后**订正**：规则 11 的三类语义
（安装/快速开始、用法/示例、许可）是有意分区；当时样本 README 只有「快速开始」
而无任何用法小节，判「缺少 用法/示例」属于**关键词口径偏窄但内容确有缺失**，
不宜算纯假阳性。

- 〔通用〕工具侧**未改**：把 `quick start` 同时算作「用法/示例」会让两类语义
  合并、规则失去区分度；更不该为单仓硬编码。
- 〔本机〕样本侧在 P1 补了「用法与示例」小节，规则 11 现为 `pass`。
- 历史判断保留在校验报告 §4，本结论为最终口径。

### 4.4 allin 治理登记

〔本机〕新增 `<ALLIN_ROOT>/platform/registry/projects/skyrim-lifeline.yaml`
（`id == 文件名`、`status: active`、`category: game`、`verify.command` 为无头
`dse check`），`allin@d7b70d5`。

| 门禁 | 整改前 | 整改后 |
|---|---|---|
| `g17-registry` | `BLOCK repos/skyrim-lifeline: unregistered-repo` | `scanned 147 / registered 138 / blocking 0`，`rc=0` |
| `verify_projects.py --only skyrim-lifeline` | — | `T1 verify.command exit 0`（2.17s） |
| `g04-push-evidence` | `DIVERGED` × 2（本地 `105eab0` / 远端 `71da92b`） | 双远端 `IN_SYNC d7b70d5`，`rc=0` |
| `check:governance` | `18/20 clean` | **`20/20 clean`**，`rc=0` |

> **数值订正（易踩坑）**：补登记后、rebase 前本地 `g17` 读到 `146` 条目；
> rebase 到远端 `71da92b` 时带入了远端新增的 `piano.yaml`，终态变成
> `147` 条目 / `138` 已登记 / `4` 条「无本地 clone」SKIP。
> **SKIP 不是通过**；`blocking 0` 才是判据。这类计数随任一侧新增条目漂移，
> 属时点值，报告统一采用终态复测数字。

---

## §5 P3 复验：全量回归 + 建仓推送

### 5.1 本地全量回归（均在推送前的绿状态执行）

| 检查 | 〔本机〕结果 |
|---|---|
| `dse check` | `109 场景 / 8 结局（可达 8）`，无悬空、无不可达 |
| `python tools/verify.py`（四层门禁全量） | `✓ 全部门禁通过`，8 条 e2e 全过，8 结局均 `SE`，耗时 `78.5s` |
| `python tests/cli_check.py` | `PASS 54  FAIL 0  SKIP 0`（`[ERR] 已中断` 是刻意触发 `130`） |
| `frostwords export-run --all-endings --format md,json,html` | `8/8` 结局，`48–52 场景步`，`25` 个文件 / `3,621,848 B` |
| YAML 语法（workflow / dependabot / semgrep / dse.yml / 7 内容包） | `11/11` 解析通过 |
| 推送前安全扫描（32 个已跟踪文件） | 令牌本体 `0` 命中、大文件 `0`、忽略目录入库 `0`；唯一形态命中是 `.gitignore` 里的 `.git-credentials` 排除规则（误报） |

> 〔本机〕`verify.py` 耗时在旧文档记为 `45.6s`，本轮为 `78.5s` ——
> 差异来自并发负载（同机同时在跑 139 仓 × 2 的影响面测量）。**耗时是时点值，
> 不作为门禁断言**；断言的是「全部门禁通过」与覆盖结果。

### 5.2 建仓推送（先私有 → 一次性 URL 推送 → 转公开）

〔通用〕流程：`whoami` 验令牌 → `create`（`auto_init=false`、先私有）→ 配干净
`origin`（不含凭据）→ 一次性 URL 推送（`GIT_TERMINAL_PROMPT=0`、输出遮蔽令牌）
→ `public` → 以 `git ls-remote` 与匿名 clone 作权威远端证据。

〔本机〕三层硬证据：

1. **ref 一致**：本地 `68532dc` == `git ls-remote origin refs/heads/master` `68532dc`。
2. **内容级一致**：匿名 `git clone --depth 1` `rc=0`；本地 / 远端 `32 / 32` 文件且
   文件集合相同；远端 HEAD `68532dc`；`README.md` / `dse.yml` /
   `content/50-endings.yml` 三份 **blob sha 逐字相同**；
   `content 7 / tools 5 / tests 2 / docs 5 / .github 2` 目录齐备。
3. **工作区与凭据**：`git status --short` 空；`.git/config` 无令牌形态、
   remote 只有 `https://gitee.com/siwpan/skyrim-lifeline.git`（无凭据 URL）；
   匿名 clone 临时目录已清理。
4. **终态复验**（本报告与台账推送后）：HEAD `f144505` == `ls-remote`；
   匿名 clone `33 / 33` 文件、集合一致；`README.md` /
   `docs/allin-fix-verification.md` / `content/50-endings.yml` 三份 blob sha
   逐字相同；最终报告在远端存在（`17,554 B`）。
   > 〔本机〕`f144505` 是文档收口时的提交；**后续任何提交（含本报告自身的
   > 最后一次编辑）都会改写它**。因此本条是「复验方法 + 时点证据」，不是永久
   > 断言：他机与后续时点一律以现场
   > `git ls-remote origin refs/heads/master` + 匿名 clone blob 比对为准。

〔本机〕`allin` 侧同步：3 个本地提交 rebase 到 `71da92b` →
`git push origin master` 快进到 `d7b70d5`（Gitee + GitHub 双 pushurl 均成功），
三端 `rev-parse` / `ls-remote` 一致；rebase 前快照留在
`backup/pre-rebase-20261115`。**未使用强推。**

---

## §6 未修 / 未验证项（三态里的 ❌，逐条给理由）

| 项 | 状态 | 理由 / 后续动作 |
|---|---|---|
| 远端 CI 实跑 | ❌ 未验证 | 本仓当前**只有 Gitee 远端**，`.github/workflows/verify.yml` 不会被触发；已验证的只是本地 YAML 语法 + 等价门禁。若后续建 GitHub 镜像，需回跑 runner 并补证据，不能现在写「CI 通过」 |
| `v0.1.0` git tag | ✅ 已验证 | P2 建项时已在本地创建（指向 `68532dc`），本批补齐推送；〔本机〕`git ls-remote --tags` 回读到 `refs/tags/v0.1.0` 与 peeled 目标 `68532dc`。**tag 不含其后的文档收口提交**，这是有意保留「首个可校验版本」语义，不是漏推 |
| Gitee release（发行版页 / 附件 / 发行说明） | ❌ 未做 | 本批范围是「建仓推送 + tag」不是「发版」；`CHANGELOG.md` 已有 `[0.1.0]` 口径，发行版属独立立项 |
| 剧情数值平衡 | ✅ 已验证（后续批次） | 引擎侧 `state.bounds` + `state.fatal` 落地；〔本机〕真结局钳制后 `hp=0/soul=0/trust=100/warmth=7`。本表保留旧表述仅作时点快照，以 §9 与本仓 `design.md` §3.1 为准 |
| `dse export-html` 浏览器端 | ✅ 已验证（后续批次） | `dse-core 0.7.0` 已加 readingExits 阅读版出口；旧结论「只支持 normal」已失效，见本仓 `README.md` |
| 发布区 74 仓规则 6 仍红 | ✅ 已验证（后续批次） | 工具侧 4 轮精准化 + 52 仓按类补声明后权威复扫 `139 仓 / R6_red=0`；详见 §9 |
| 规则 11 工具侧关键词表 | ❌ 有意不改 | 见 §4.3；内容侧已补小节，改工具会削弱语义区分度 |
| 全量 `run_all_gates.sh` | ✅ 已验证（后续批次） | 〔本机〕最终实跑 `GATES_RC=0`、`ALLIN_GATE_SUMMARY status=clean fail=0 skips=0 not_applicable=0`；详见 §9 |

---

## §7 一键复现（他机先按 §0 替换占位符）

```bash
# ① 发现层复验（跨机通用期望：发现数 == 一级目录数）
<PYTHON> - <<'PY'
import sys, pathlib
sys.path.insert(0, r"<ALLIN_ROOT>/tools/repocheck")
import scanner
root = pathlib.Path(r"<REPOS_ROOT>")
print("一级目录:", len([p for p in root.iterdir() if p.is_dir()]))
print("发现项目:", len(scanner.discover_projects(root, max_py_depth=2)))
r = scanner.check_project(str(root / "skyrim-lifeline"))
print("score / pass_rate / severity:", r["score"], r["pass_rate"], r["severity_counts"])
PY

# ② 工具回归（期望 70 项全绿）
<PYTHON> -m pytest <ALLIN_ROOT>/tools/repocheck/ -q

# ③ 治理门禁（期望 20/20 clean）
cd <ALLIN_ROOT> && npm run check:governance

# ④ 本仓四层门禁 + CLI 回归（期望「全部门禁通过」/ PASS 54）
cd <PROJECT_ROOT> && <PYTHON> tools/verify.py && <PYTHON> tests/cli_check.py

# ⑤ 远端证据（期望 ref 与本地 HEAD 逐字相同、匿名 clone 文件数一致）
git -C <PROJECT_ROOT> ls-remote origin refs/heads/master
git clone --depth 1 https://gitee.com/siwpan/skyrim-lifeline.git <可写目录>/anon
```

> 〔通用〕期望值只有结构性断言：`发现项目 == 一级目录`、`pytest` 全绿、
> 门禁 clean、ref 一致、文件集合一致。**具体数字、盘符、hash、耗时一律以
> 该机现场实测为准**，不得拿本报告数值当通用断言。

---

## §8 变更清单

| 仓 | 文件 / 动作 | commit |
|---|---|---|
| `allin` | `tools/repocheck/scanner.py` + `test_scanner.py`（P0 深度口径） | `3b0b407` |
| `allin` | `tools/repocheck/rules_core.py` + `test_scanner.py`（P2 依赖声明事实源） | `67dc184` |
| `allin` | `platform/registry/projects/skyrim-lifeline.yaml`（新增登记） | `d7b70d5` |
| `skyrim-lifeline` | 全量骨架 + 本机事实口径 | `299a582` |
| `skyrim-lifeline` | 依赖声明 / 许可 / 安全 / 贡献 / 变更日志 / CI / SAST / 垫片 | `68532dc` |
| `skyrim-lifeline` | 本报告 + 台账 / README / CHANGELOG / CONTRIBUTING 收口 | `f144505`（终态复验证据见 §5.2 第 4 条） |

> 〔本机〕本表 hash 均为 `@SIWPAN` 上对应分支的时点值；rebase 会改写，
> 他机一律以本地 `git log` 现场复测。

---

## §9 追加批次：规则 6 全绿与全量门禁（2026-11-15，同一天后续批次）

### 9.1 目标与授权

用户明确要求：`<REPOS_ROOT>` 中其余 74 仓规则 6 红灯转绿、全量 `run_all_gates.sh`
实跑，且**先核对各仓远端状态**。随后逐项授权「全部 74 仓都要转绿」、
「分类精准修复」、「授权批量 commit + push」、「逐仓核对远端后批量提交推送」。
用户曾选择「全部补 `-e`」，但逐仓取证发现大量 manual 名**没有对应静态实体**，
机械补 `-e` 会写入假依赖；因此改用可审计的 `# r6-local:` 仓内声明机制，
不造 pip 包、不编造兄弟仓路径。该取舍属于对授权范围的诚实收窄。

### 9.2 〔通用〕结论

1. 规则 6 红灯必须先分成「工具侧误报」与「各仓真实声明缺口」两类；
   不能用放白名单的方式把真实缺口刷绿。
2. distribution 名与 import 名不一致（`pygame-ce → pygame`、
   `PyExecJS → execjs`、`python-vlc → vlc`、`PyMuPDF → fitz` 等）需要显式别名表。
3. namespace package / src-layout 目录、本地可编辑依赖 `-e <path>`、
   以及运行时由 `sys.path` 注入且仓内无静态目录的模块，都需要被静态判据识别；
   后者只能通过**该仓自己的显式声明**表达，不能做全局白名单。
4. 提交推送前必须用 `git ls-remote` 判定远端领先 / 分叉 / 404；
   远端领先只快进、分叉不强推、404 登记为远端不可用。
5. 全量门禁结论只认最终 `ALLIN_GATE_SUMMARY`，单个子门禁通过不能冒充全量通过。

### 9.3 〔本机 @SIWPAN 时点事实〕工具侧改动

`<ALLIN_ROOT>` 上规则 6 共 4 次提交（均已在 `master` 推送）：

| commit（@SIWPAN） | 内容 |
|---|---|
| `77826f40482c8305357e10e1c194f3b7b41e68f7` | 分布名→import 名别名矩阵、namespace 目录识别；刷新 facts 投影 |
| `cd2f6f0daeec9136668824bce7b92b08d1ac6916` | 补 `3dworld`、`allin-engine`、`audioop-lts` 等别名 + src-layout 识别 |
| `91276dc1af8da536233ef7aa167acdf8b0a3d8b2` | 补 `python-vlc → vlc`、`pyinstaller → PyInstaller`；LibreOffice 宿主模块 `uno` 不再误报 |
| `ee1bf780d0a1d066ed7be8131a7702b85e01ff45` | 支持 `# r6-local:` + `PyExecJS → execjs`；规则 6 红灯归零 |

`# r6-local:` 写法（仅在该仓根 `requirements*.txt` 中生效，非全局白名单）：

```text
# r6-local: core, save, shared
```

`tools/repocheck/test_scanner.py` 从 70 项扩到 **83 项全绿**，新增别名矩阵、
`uno` 宿主模块、声明放行 / 未声明仍报红等回归。

`<ALLIN_ROOT>` 的 `facts.json` 重新生成 **147 条** project 投影
（此前 `skyrim-lifeline` 已登记但投影缺失，导致 3 项 facts 门禁同源失败）。
`<REPOS_ROOT>/write` 的 `tools/bootstrap.ps1` 补 UTF-8 BOM 后提交
`851384d0fd0ecfd41ea2131392fce8ae62277c8a`（@SIWPAN）并推送。

### 9.4 〔本机 @SIWPAN 时点事实〕各仓声明补齐与推送

改动 **52 仓**的 `requirements.txt`，覆盖三类（同一仓可含多类）：

- **38 仓**真实 pip 缺口（`cryptography`、`ollama`、`sounddevice`、`python-vlc`、
  `pygame-ce`、`pywin32` 等）；
- **6 仓**真实存在的本地可编辑依赖（`-e ../bloodmusic`、`-e ../superengine`、
  `-e ../dse-core`、`-e ../3dworld`、`-e ./battle_platform`、`-e ./core`、
  `-e ./remix/tools` 等）；
- **18 仓**运行时注入模块声明 `# r6-local: ...`（`core`、`save`、`gdb`、
  `audio_core`、`cordis`、`rendering` 等）。

批量提交消息统一为 `fix(gate): 规则6依赖声明补齐——pip缺口/r6-local本地模块/-e兄弟仓（allin实战校验 2026-11-15）`。
推送结果：**44 仓直推 `master`、1 仓新建远端分支、6 仓改推 `main`、
1 仓 `happy-childrens-day` 因 Gitee `404` 仅本地提交 `1f6a3702e09b`（@SIWPAN）**。

终核时发现两处差异并按非破坏方式处理：

- `3dworld-demos`：远端已有合并提交 `a014053`（@SIWPAN）包含我们的 `29f9805`，
  本地 `git merge --ff-only origin/master` 快进，未改写历史；
- `moba_battle_platform`：本地领先 1 提交，确认远端 `main` 存在且 `behind=0` 后
  `git push origin main`，`36c9acb..4efe61f`（@SIWPAN）。

最终对 52 仓逐一 `git ls-remote --heads origin` + `rev-parse HEAD` 核对：
**51 仓 local HEAD = remote HEAD，1 仓 404 登记，MISMATCH = 0**。
`media-tools` 有未跟踪的 `triangle.png`（@SIWPAN），未纳入提交，保持原样。

### 9.5 〔本机 @SIWPAN 时点事实〕权威复扫与全量门禁

```text
<PYTHON> <ALLIN_ROOT>/tools/repocheck/main.py <REPOS_ROOT> --format json -o <OUT> --workers 4
projects: 139 R6_red: 0
```

```text
cd <ALLIN_ROOT> && bash scripts/run_all_gates.sh
GATES_RC=0
ALLIN_GATE_SUMMARY status=clean fail=0 skips=0 not_applicable=0
全部门禁通过（环境不适用 0 项已如实标注，不计入通过）。
```

〔本机〕日志落点：`C:/Users/13122/AppData/Local/Temp/allin_gates_final.log`（@SIWPAN）。
该次运行覆盖 `check_ps1_bom.py`、`repo_hygiene.py --all`、restore drill、
`scan_hardcoded.ps1`、`smoke:e2e`（`8/8`）、内核测试（26 项）、
规则 6 测试（83 项）与 CLI 测试；结论以最终 summary 为准。

### 9.6 仍未验证项

| 项 | 状态 | 理由 |
|---|---|---|
| `happy-childrens-day` 远端同步 | ❌ 远端不可用 | 〔本机〕Gitee `404 not found`；已本地提交，不做强推。远端恢复后需重新核对并推送 |
| 远端 CI runner 实跑 | ❌ 未验证 | 见 §6；本地等价门禁与 YAML 语法已过，不能冒充 runner 通过 |
| Gitee release 发行版 | ❌ 未做 | 独立立项，不在本批次授权范围 |

### 9.7 口径修正：归档冗余仓 `happy-childrens-day`（同日补记）

用户指出：**`happy-childrens-day` 远端 404 不是异常**，而是 2026-10-29
已收拢进 `arcade/games/sixone`；其 README 也明确写着「已收入归档仓
`game-prototypes`，原仓冻结不再开发」。因此该本地仓属于完全冗余，
不该按「404 仓」登记为待处理项。

〔通用〕结论：遇到远端 404 / 本地仓存在时，先读 README 的归档声明与
`<ALLIN_ROOT>/docs/事实源/组合分级决策索引.md`，判断是否是
**已收拢的墓碑仓**；不要仅凭 `ls-remote` 就登记为异常，更不要给冻结仓补声明。

〔本机 @SIWPAN 时点事实〕处置：

1. 确认 `happy-childrens-day` 本轮唯一改动是新增
   `requirements.txt` 中的 `sounddevice` / `soundfile`；
   该声明已在 **两个有效落点**存在：`arcade/requirements.txt`
   （`c8a5c87`）与 `game-prototypes/requirements.txt`（`af57aa1`），
   且两仓规则 6 均为 pass。**改动已落位，无需再补。**
2. 备份整个本地仓到 `%TEMP%/archived-repos-backup-20261115-2143`
   （16 个同型归档仓一并备份，685 MB，`requirements.txt` 哈希逐一核对一致），
   再用 `SHFileOperationW` + `FOF_ALLOWUNDO` 送回收站；
   原 `D:\projects\repos\happy-childrens-day` 已不存在。
3. 审计发现本轮 52 仓中另有 **15 个** README 带同一归档声明
   （`arcade` / `ashen-beacon` / `daily_player` / `fish` / `lonely-desert-road` /
   `mahjong` / `mc-clone` / `mcclone3d` / `music-player` / `pomodmer` /
   `random-dungeon-` / `sandbox` / `text-fps` / `under-withered-limbs` / `yasuo`），
   分别归档进 `game-prototypes` / `players-unified` / `dev-toolkit`。
   这些**已从备份原样还原**，未删除；用户本次明确要删的只有 `happy-childrens-day`。
4. 删除后权威复扫：

   ```text
   projects: 138 R6_red: 0
   ```

   §9.5 的 `139` 是删除前时点值，二者都成立；**当前终态以 138 为准**。
   52 仓的提交历史仍有效，只是本地工作树少了 1 个冗余墓碑仓。

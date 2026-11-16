# Changelog

本文件遵循 Keep a Changelog 结构，版本号遵循 SemVer。

## [0.3.0] - 2026-11-16

### Added

- **第九个结局 `end-dragon-slayer`（屠龙者）**：第三章新增 `ch3-soul-taken`
  短藤蔓，她剖开幼龙、吞下龙魂，选择对抗；从 `ch3-hall` 主干枢纽与
  `ch3-reunion` 两处进入，1 跳汇回 `ch3-after-dragon`。`end-select` 新增
  `flags.absorbedSoul and trust >= 60` 分流。`solve_e2e.py` 的 GOALS /
  ENDINGS / EXPECT 同步登记，并在 score 里补 trust 连续项打破双目标平局。
- **第三势力梭摩**：`ch2-thalmor`（白袍 / 塔洛斯清查）短藤蔓 +
  `ch4-scout` 的「第三拨人」extraText；新增 `flags.thalmorNotice` /
  `clues.thalmorTrue`。
- **不可靠叙述（海尔根真相）**：`core-corridor` 锚点场景按
  `clues.helgenTruth` / `flags.knewTruth` 显示互相矛盾的细节；酒馆
  `witness` 话题（法典「那晚天上什么都没有，火从地里烧起来」）设置
  `flags.witnessConflict`，与法师「一条龙从天而降」正面冲突，并在
  `ch2-mage-truth` 留下比对提示。
- **时间轮回入口**：`ch3-loop-gate` 用引擎原生 `@loop:core-open`，状态重置
  但 `loopKeep: [clues, flags]` 让知识跨轮保留；由 `clues.playerIdentity`
  门控、`flags.looped` 随轮次保留以防死循环。`core-corridor` 显示轮回记忆。
- **灵魂水晶软后果**：`core-ask` 的 `listener` 话题需 `soul >= 2`，问「那边
  一直是你吗」获 `clues.playerIdentity`；`ch4-end-select` 在 `soul <= 0`
  时显示信号衰减文本（不做 fatal，避免误杀 `soul=0` 的惨胜真结局）。
- **信任驱动的服从权重**：`core-advice-1` 三条建议各按 `trust >= 45` /
  `< 45` 门控两套互斥选项，高信任 obey 权重显著更高（9:1 / 8:2 / 6:4），
  低信任违抗概率上升；`trust` 首次成为过程机制而非仅结局门槛。
- **显性压力提示**：`ch1-open` 按 `warmth` / `clock` 阈值显示体温与夜深提示。
- **阿尔卡伏笔线**：渡口闲话、酒馆炉灰残纸、第三章骨堆残纸三处 extraText，
  玩家拼合后才恍然「烧纸的守墓人」就是她要找的阿尔卡。
- **玩家身份暗线**：`clues.playerIdentity` + 真结局收尾回调。
- **成就 6 → 16 条**：新增屠龙者、她没听、对不上的证词、第三面旗、时间轮回
  及各死亡结局成就。

### Changed

- `dse check`：`109 场景 / 8 结局` → `113 场景 / 9 结局`（可达 9），无悬空 / 不可达。
- `tests/cli_check.py`：`cases` 断言 8 → 9，`export-outline` 标题数 109 → 113。
- `tools/solve_e2e.py` / `tests/e2e_cases.json`：9 条 e2e 全部用真实引擎重建。
- `README.md` / `docs/CLI.md` / `frostwords_cli.py`：结构性数字同步更新。

## [Unreleased]

### Docs

- `docs/allin-fix-verification.md` 增补 §9「追加批次：规则 6 全绿与全量门禁」：
  记录规则 6 从 74 红到 0 红的工具侧四轮修复、52 仓声明补齐与推送终核、
  `# r6-local:` 机制、全量 `run_all_gates.sh` 实跑结论，并把 §1/§6 的
  过时「未修/未跑」三态更新为 ✅（保留旧行作历史快照）。
  〔本机 `@SIWPAN` 时点事实〕`139 仓 / R6_red=0`、
  `ALLIN_GATE_SUMMARY status=clean fail=0`；他机须按 §0 占位符现场复测。
- §9.7 补记：远端 404 的 `happy-childrens-day` 是已收拢进 `arcade`
  并归档进 `game-prototypes` 的墓碑仓，非待处理异常。其
  `sounddevice` / `soundfile` 声明已在 `arcade` 与 `game-prototypes` 两个
  有效落点存在；本地冗余仓备份后送回收站。删除后复扫
  〔本机 `@SIWPAN`〕`projects: 138 R6_red: 0`，全量门禁复跑仍为
  `status=clean fail=0`。

## [0.2.0] - 2026-11-15

### Changed

- **数值平衡落地（反哺 `dse-core>=0.7.0`）**：`dse.yml` 新增
  `state.bounds`（钳制 `hp/stamina/warmth/soul/trust/rations/gold` 七字段，
  `max` 可引用 `maxHp`/`maxStamina`）与 `state.fatal`（早期体温失败分支
  `warmth<=0 and clock<=8 → end-frozen`）。终结骨架阶段「终局资源为负、
  trust 越界、死亡分支仅作候选」的问题；8 结局可达性经门禁复验不变。
  设计取舍见 `docs/design.md` §3.1。
- `tools/verify.py` / `tools/solve_e2e.py` 注释更新：0.7.0 combat 随机源
  从全局 `random.random()` 改为 `engine.rng`；两处仍同时固定 `engine.rng`
  与全局种子以兼容 0.6.x / 0.7.0。
- `tests/e2e_cases.json` 全部 8 条用例用真实引擎重建（0.7.0 战斗结果变化
  会导致旧输入流错位）。新步数：58/65/57/64/64/64/61/64。

### Notes

- 本仓数值平衡依赖 `dse-core>=0.7.0`（`state.bounds` / `state.fatal` /
  combat RNG 隔离 / `create_engine` 不再污染 `DSE_ENTRY` / HTML 阅读版出口
  均为 0.7.0 新能力）。0.7.0 已发布到 PyPI 并完成匿名安装验收，
  详见引擎仓 `cordis-py` 0.7.0 变更与 PyPI 项目页。
- 〔本机 `@SIWPAN` 时点实测〕`dse check` 109 场景 / 8 结局（可达 8）；
  `verify.py` 200 条路径 / 覆盖 89/109 (82%) / 8 e2e 全过 / 8 结局 `SE`；
  `tests/cli_check.py` PASS 54。换机 / 升级运行时后数值须现场复测。

## [0.1.0] - 2026-11-15

### Added

- 7 个纯 YAML 内容包：**109 场景 / 8 结局 / 五种 mode**（normal / battle /
  dialogue / trade / diary），含加权随机建议、Rewind、消息历史与有限注意力谈判。
- `tools/verify.py` 四层门禁：静态校验与字段预声明门、真实引擎 fuzz 采样、
  8 条 e2e 通关回放、结局覆盖门。
- `tools/solve_e2e.py`：逐步用真实引擎试错求解通关输入流，产出
  `tests/e2e_cases.json`。
- `frostwords` CLI：完整流程导出（Markdown / JSON / HTML）、全场景静态大纲、
  Windows `.cmd` 垫片与 54 项回归。
- 文档：设计说明、Mermaid 场景图、序章试玩实录、CLI 手册、
  allin repocheck 实战校验报告（历史快照）与 P0→P3 整改最终验证报告。
- 工程治理：`.gitignore`、`pyproject.toml`、`LICENSE`（MIT + 同人免责声明）、
  `SECURITY.md`、`CONTRIBUTING.md`、`.github/workflows/verify.yml`、
  `.github/dependabot.yml`、`.semgrep.yml`、仓库根 `frostwords.cmd` / `fwcli.cmd`。
- 以本仓为样本对 `<ALLIN_ROOT>` 的 `tools/repocheck` 做完整实战校验，
  两处工具缺陷回写 allin：发现层深度口径、规则 6 依赖声明事实源；
  并补 registry 登记与推送证据门禁收口。

### Changed

- 全量复跑：`dse check`、`tools/verify.py`、`tests/cli_check.py`、
  八结局流程导出、`check:governance` 全部通过；样本仓体检从
  `6.0 / 0.442` 提升到 `10.0 / 1.0`（〔本机〕时点值）。

### Notes

- ~~骨架阶段数值未平衡：终局资源可能为负，`trust` 未做 0–100 钳制，
  缺硬性死亡分支。~~ **已于 0.2.0 解决**（`state.bounds` + `state.fatal`），
  见上文与 `docs/design.md` §3.1。
- `dse export-html` 在 0.7.0 起对非 `normal` 模式提供阅读版出口（见
  `export_html` 的 `readingExits`）；完整可玩入口仍是 `dse play`。
- `v0.1.0` git tag 已推送，指向「骨架 + 治理」提交 `68532dc`，**不含**其后的
  文档收口提交（有意保留「首个可校验版本」语义）。Gitee 发行版页 / 附件 / 发行
  说明尚未制作。
- **远端 CI 尚未实跑**：本仓当前只有 Gitee 远端，GitHub Actions workflow
  不会被触发；本地 YAML 语法与等价门禁已通过，runner 实跑未验证。
  三态与未修项逐条见 `docs/allin-fix-verification.md` §6。
- 文档中的绝对路径、解释器版本、仓数、commit hash、字节数与耗时均为
  带机器名的时点事实，不是跨机器通用结论
  （见 `docs/allin-repocheck-validation.md` §0）。

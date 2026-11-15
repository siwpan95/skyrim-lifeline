# 贡献指南 / Contributing

欢迎先开 **issue** 讨论剧情分支、机制映射与设定考据，再提交 **PR**。
改动前请跑一遍门禁，贡献流程以本节为准。

## 内容约定

1. **内容即数据**：剧情只写在 `content/*.yml`，不要把剧情逻辑写进 Python。
2. **藤蔓结构**：一个节拍的多条支路要在 1–2 跳内汇入同一后继；
   加权 `obey` / `defy` 两条支路也必须汇合。否则全图路径数指数爆炸。
3. **结局场景只能有 `@` 目标选项** —— 引擎 `is_ending` 判定是「无选项，
   或所有选项的 `goto` 都以 `@` 开头」。
4. **条件字段必须在 `dse.yml` 的 `state.initial` 预声明**，否则静默判 False。
5. **本机事实必须标注**：盘符、仓数、字节数、解释器路径、提交 hash 等
   一律标 `@机器名` 与时点；命令示例用 `<PYTHON>` 等占位符，不得写成
   跨机器通用结论。

## 提交前必跑

```bash
dse check
python tools/verify.py
python tests/cli_check.py
```

`verify.py` 是四层门禁（静态 / fuzz 随机游走 / e2e 回放 / 结局覆盖）。
`--fast` 可跳过 fuzz 做快速自检，但**提交前请跑全量**。

## 改动内容包之后

选项编号会漂移，旧 e2e 脚本会走到完全不同的分支。**必须**重新求解：

```bash
python tools/solve_e2e.py --all --write-cases
```

`tests/e2e_cases.json` 由求解器生成，请勿手工编辑。求解器每一步都用真实
引擎试跑，不模拟五种 mode 的语义。

## 已知待办

骨架阶段数值未平衡：终局可能出现负 HP / 负灵魂余量、`trust` 无上限钳制，
缺硬性死亡分支。详见 `docs/design.md`「待办」。欢迎从这一块切入。

`.github/workflows/verify.yml` 目前**未在任何远端 runner 上实跑**（本仓只有
Gitee 远端，GitHub Actions 不触发）；本地等价门禁已通过。若后续建 GitHub
镜像，请补跑并回写证据，勿把「YAML 语法通过」写成「CI 通过」。
完整三态清单见 `docs/allin-fix-verification.md` §6。

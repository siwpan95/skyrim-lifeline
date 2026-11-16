#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""霜语 · 一键门禁（CI 友好）。

为什么不用引擎自带的 `dse traverse` 全图遍历？
──────────────────────────────────────────────────────────
traverse 是**穷举 DFS**：路径数 = 路径上各节点出度之乘积。
实测（见 docs/design.md「路径爆炸」一节）：分支因子 2、深度 16 的
合成图就有 13,160,704 条路径，耗时 267 秒。

本作是《生命线》式的**分支叙事**：分支因子 2~3、深度 78，
全图穷举意味着 10^28 量级的路径 —— 数学上不可行。
这不是内容写坏了，是 traverse 的设计不适用于大规模分支叙事。

引擎自己给了正确答案（见其 README）：
    dse coverage --e2e end-secret   # 声明某结局已由 e2e 用例覆盖

所以本作的门禁分四层，缺一不可：
    ① check   —— 静态：Schema / 悬空跳转 / 图连通性（毫秒级）
    ② fuzz    —— 动态：随机游走采样，真实引擎跑 N 条路径，抓
       「条件恒假」「表达式求值炸」「效果写错」「场景缺失」
    ③ e2e     —— 脚本化回放整条通关路径，断言最终场景与状态
    ④ coverage—— 每个结局须有静态可达(S) 或 e2e 已回放(E) 来源

★ 随机性：combat 插件用全局 random.random()，不受 engine.rng 控制，
  所有层都同时固定全局种子，保证可复现。

用法：
    python tools/verify.py                      # 全部门禁
    python tools/verify.py --fast               # 跳过 fuzz（只跑 ① ③ ④）
    python tools/verify.py --chapter ch2        # fuzz 只从第二章入口起步
    python tools/verify.py --samples 100        # 提高采样条数
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dse_core import graph                                    # noqa: E402
from dse_core.loader import load_project                      # noqa: E402
from dse_core.sdk import create_engine                        # noqa: E402

# ── 章节入口（fuzz 随机游走的起步点；--chapter 可只选其中一章）────
CHAPTERS: list[tuple[str, str]] = [
    ("core", "core-open"),
    ("ch1", "ch1-open"),
    ("ch2", "ch2-open"),
    ("ch3", "ch3-open"),
    ("ch4", "ch4-open"),
]

# ── e2e 脚本化回放 ─────────────────────────────────────────────
# 用例数据由 tools/solve_e2e.py --all --write-cases 生成，写入
# tests/e2e_cases.json。序列是玩家输入流：normal 场景输选项编号，
# battle 输 a/d/r，dialogue 输 ask <编号> / next，trade 输 next。
#
# ★ 改动任何内容包后必须重新求解 —— 选项编号会漂移，旧脚本会走到
#   完全不同的分支。求解器用真实引擎逐步试错，产出的脚本必然可跑。
CASES_FILE = ROOT / "tests" / "e2e_cases.json"
if not CASES_FILE.exists():
    raise SystemExit(
        "缺少 e2e 用例数据："
        f"{CASES_FILE}；请先运行: python tools/solve_e2e.py --all --write-cases"
    )
E2E_CASES: list[dict] = json.loads(CASES_FILE.read_text(encoding="utf-8"))


# ── 工具 ────────────────────────────────────────────────────────
def _hr(title: str) -> None:
    print(f"\n{'─' * 68}\n  {title}\n{'─' * 68}")


def _ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def _fail(msg: str) -> None:
    print(f"  ✗ {msg}")


def _warn(msg: str) -> None:
    print(f"  ! {msg}")


# ── ① 静态门禁 ─────────────────────────────────────────────────
def gate_check() -> list[str]:
    """静态校验：Schema + 悬空跳转 + 结局可达性。"""
    _hr("① 静态门禁（dse check 等价）")
    problems: list[str] = []

    project = load_project(ROOT)
    from dse_core.plugins.scenes import find_dangling, validate_scenes
    from dse_core.schema import validate_pack

    for rel in project.pack_files:
        path = (ROOT / rel).resolve()
        from dse_core.loader import load_pack_file
        _, scenes = load_pack_file(path)
        problems += validate_pack(scenes, source=rel)
        problems += validate_scenes(scenes, rel)
    problems += find_dangling(project.dict)

    report = graph.analyze(project.dict, project.entry)
    _ok(f"{report['scenes']} 场景 / {len(report['endings'])} 结局"
        f"（可达 {len(report['endingsReachable'])}）")
    if report["unreachable"]:
        _warn(f"不可达场景: {', '.join(report['unreachable'])}")
    if problems:
        for p in problems:
            _fail(p)
    else:
        _ok("Schema / 悬空跳转：全部通过")
    return problems


# ── ①b 条件字段预声明门 ────────────────────────────────────────
def gate_declared_fields() -> list[str]:
    """条件里引用的 flags./clues./items. 键必须在 state.initial 预声明。

    引擎的 state.check 对求值异常静默兜底 False —— 拼错一个旗标名，
    表现是「选项莫名其妙不出现」，静态 Schema 完全查不出来。
    """
    import re
    import yaml

    cfg = yaml.safe_load((ROOT / "dse.yml").read_text(encoding="utf-8"))
    initial = next((p["config"]["initial"] for p in cfg
                    if p.get("id") == "state"), {}) or {}
    declared = {f"{ns}.{k}"
                for ns in ("flags", "clues", "items")
                for k in (initial.get(ns) or {})}

    used: set[str] = set()
    project = load_project(ROOT)
    exprs: list[str] = []
    for sid, sc in project.dict.items():
        for c in (sc.get("choices") or []):
            if c.get("if"):
                exprs.append(str(c["if"]))
        for key in ("if", "when", "condition"):
            if sc.get(key):
                exprs.append(str(sc[key]))
    for e in exprs:
        used |= {f"{ns}.{k}" for ns, k in
                 re.findall(r"\b(flags|clues|items)\.([A-Za-z_][A-Za-z0-9_]*)", e)}

    missing = sorted(used - declared)
    if missing:
        _fail(f"未预声明的条件字段: {', '.join(missing)}")
        return [f"条件字段未预声明: {m}" for m in missing]
    _ok(f"条件字段预声明：{len(used)} 个引用全部已声明")
    return []


# ── ② 动态随机游走采样 ───────────────────────────────────────
def _visible_by_if(items: list, snapshot: dict) -> list:
    """按引擎口径过滤 `if`：evaluate 对快照求值，异常兜底 False。"""
    from dse_core.safety import evaluate
    out = []
    for item in items:
        cond = item.get("if")
        ok = True
        if cond:
            try:
                ok = bool(evaluate(cond, snapshot))
            except Exception:
                ok = False
        if ok:
            out.append(item)
    return out


def _candidates_for(scene: dict, mode: str, asked: set[str],
                    snapshot: dict | None = None) -> list[str]:
    """按场景声明列合法输入（引擎会拒绝非法输入并等待下一个，不会崩）。

    0.3.1：normal / dialogue 候选都改按引擎 visible() 口径（if 过滤后重编号），
    与 render / do_ask 一致；此前按原始列表全量编号会与门控项错位。
    """
    snap = snapshot or {}
    if mode == "normal":
        return [str(i + 1) for i, _ in
                enumerate(_visible_by_if(scene.get("choices") or [], snap))]
    if mode == "battle":
        return ["a", "d", "r"]
    if mode == "dialogue":
        dlg = scene.get("dialogue") or {}
        topics = dlg.get("topics") or []
        visible = [t for t in _visible_by_if(topics, snap)
                   if t.get("id") not in asked]
        outs = [f"ask {i + 1}" for i, _ in enumerate(visible)] + ["end"]
        # 注意点用尽后只给 end（引擎会把任何 ask 当「用尽→结束」消费）。
        notes = dlg.get("notes") or 0
        if notes > 0:
            topic_ids = {t.get("id") for t in topics}
            if len(topic_ids & asked) >= notes:
                return ["end"]
        return outs
    if mode == "trade":
        return ["next", "buy 1", "sell 1", "info"]
    if mode == "diary":
        return ["back"]
    return []


def gate_fuzz(samples: int = 40, max_steps: int = 80,
              chapter: str | None = None) -> list[str]:
    """随机游走采样（fuzz）：用真实引擎跑 N 条随机输入流。

    为什么不用穷举 traverse：本作路径数约 10^28（见 docs/design.md §四），
    而且从任一章节入口出发都会顺着主线走完全图 —— 实测「按章分段遍历」
    连第一章在 200 秒内都跑不完。穷举在数学上不可行。

    采样能在秒级覆盖五种 mode 的真实交互，同样能抓到：
        · if 条件恒假 / 表达式求值异常
        · do 效果写错导致的状态异常
        · 悬空跳转（引擎运行时报场景缺失）

    做法：订阅 `scene/enter`，每次进入场景就往脚本输入队列**头部**注入一个
    该场景的合法输入。因此每一步都走真引擎、真插件、真状态，而不是模拟。
    步数达上限后停止注入 → 输入耗尽 → 引擎按 EOF 语义正常退出。
    """
    import contextlib
    import random as _random

    _hr("② 动态随机游走采样（fuzz，真实引擎）")
    problems: list[str] = []
    chapters = [(n, e) for n, e in CHAPTERS if not chapter or n == chapter]
    all_visited: set[str] = set()
    endings_hit: set[str] = set()
    t0 = time.time()
    runs = 0

    for cname, centry in chapters:
        cvisited: set[str] = set()
        for k in range(samples):
            rng = _random.Random(20261115 + k * 7919)
            os.environ["DSE_INPUT"] = "1"       # 占位；真实输入由 on_enter 注入
            ctx = create_engine(root=ROOT, entry=centry, quiet=True)
            engine = ctx.services["engine"]
            io_svc = ctx.services["io"]
            engine.rng = _random.Random(20261115 + k)
            _random.seed(20261115 + k)          # combat 用全局随机源
            steps = [0]

            def on_enter(sid, sc, _ctx=ctx, _rng=rng, _steps=steps,
                         _io=io_svc, _visited=cvisited):
                _visited.add(sid)
                _steps[0] += 1
                if _steps[0] > max_steps:
                    return                      # 不再注入 → 输入耗尽 → 退出
                mode = (sc or {}).get("mode") or "normal"
                asked = set(_ctx.services["state"].get("dialogueAsked") or [])
                snap = _ctx.services["state"].snapshot()
                cands = _candidates_for(sc or {}, mode, asked, snap)
                if cands:
                    _io.scripted.insert(0, _rng.choice(cands))

            off = ctx.on("scene/enter", on_enter)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    engine.start()
                runs += 1
                if engine.current and engine.current.startswith("end-"):
                    endings_hit.add(engine.current)
            except Exception as exc:
                problems.append(f"{cname} 样本{k}: {type(exc).__name__}: {exc}")
            finally:
                off()
                os.environ.pop("DSE_INPUT", None)
                # sdk.create_engine(entry=...) 会写 DSE_ENTRY 且从不清理，
                # 必须逐样本清掉，否则会污染后续的 e2e / 其它门禁层。
                os.environ.pop("DSE_ENTRY", None)
                ctx.dispose()
        all_visited |= cvisited
        print(f"  · {cname:<5} 入口 {centry:<12} 覆盖 {len(cvisited):>3} 场景")

    total = len(load_project(ROOT).dict)
    rate = len(all_visited) / total * 100 if total else 0
    dt = time.time() - t0
    line = (f"{runs} 条随机路径 | 覆盖 {len(all_visited)}/{total} 场景 "
            f"({rate:.0f}%) | 触及 {len(endings_hit)} 个结局场景 | {dt:.1f}s")
    if problems:
        _fail(line)
        for p in problems[:10]:
            _fail(f"    {p}")
    else:
        _ok(line)
    if rate < 60:
        _warn(f"场景覆盖率 {rate:.0f}% 偏低，可提高 --samples")
    return problems


# ── ③ e2e 脚本化回放 ───────────────────────────────────────────
def run_e2e(case: dict, seed: int = 20261115) -> dict:
    """跑一条脚本化输入流，返回 {ok, scene, failures}。

    ★ 关于随机性：0.7.0 起 combat 走 `engine.rng`（dse.yml 的 seed 可复现），
      老版本曾直接用全局 `random.random()`。这里两个种子都固定，向前兼容两种
      引擎：既设 engine.rng 又设全局 random，保证跨版本脚本回放都可复现
      （实测：只设一个种子时，同一脚本两次跑会走出不同分支）。
    """
    import contextlib
    import io as _io
    import random as _random

    os.environ["DSE_INPUT"] = case["script"]
    # ★ sdk.create_engine(entry=...) 会把 DSE_ENTRY 写进 os.environ 且**从不清理**。
    #   若上一层的 fuzz 用 --chapter 从 ch4-open 起步，这个残留会让本用例
    #   也从 ch4-open 开始 → 输入流整体错位。这里按用例显式隔离。
    if case.get("entry"):
        os.environ["DSE_ENTRY"] = str(case["entry"])
    else:
        os.environ.pop("DSE_ENTRY", None)
    try:
        ctx = create_engine(root=ROOT, entry=case.get("entry"), quiet=True)
        engine = ctx.services["engine"]
        state = ctx.services["state"]
        engine.rng = _random.Random(seed)
        _random.seed(seed)          # 固定全局随机源（combat 用它）
        # 引擎会打印整条剧情文本；门禁只需结论，重定向掉以免淹没 CI 日志。
        with contextlib.redirect_stdout(_io.StringIO()):
            engine.start()
        failures: list[str] = []
        if case.get("expect_scene") and engine.current != case["expect_scene"]:
            failures.append(f"最终场景应为 {case['expect_scene']}，实际 {engine.current}")
        for expr in case.get("expect", []):
            if not state.check(expr):
                failures.append(f'状态断言失败: "{expr}"')
        return {"ok": not failures, "scene": engine.current, "failures": failures}
    finally:
        os.environ.pop("DSE_INPUT", None)


def gate_e2e() -> tuple[list[str], set[str]]:
    """脚本化回放：验证通关路径 + 收集结局覆盖来源。"""
    _hr("③ e2e 脚本化回放（dse test 等价）")
    problems: list[str] = []
    covered: set[str] = set()
    for case in E2E_CASES:
        res = run_e2e(case)
        if res["ok"]:
            _ok(f"{case['name']:<22} → {res['scene']}")
            covered.add(res["scene"])
        else:
            _fail(f"{case['name']:<22} → {res['scene']}")
            for f in res["failures"]:
                _fail(f"    {f}")
                problems.append(f"{case['name']}: {f}")
    return problems, covered


# ── ④ 结局覆盖门 ───────────────────────────────────────────────
def gate_coverage(covered: set[str]) -> list[str]:
    """结局覆盖门：每个结局须有静态可达(S) 或 e2e 已回放(E) 来源。"""
    _hr("④ 结局覆盖门（coverage）")
    problems: list[str] = []
    project = load_project(ROOT)
    report = graph.analyze(project.dict, project.entry)
    static_reachable = set(report["endingsReachable"])

    all_endings = set(report["endings"])
    for eid in sorted(all_endings):
        src = []
        if eid in static_reachable:
            src.append("S")   # 静态可达
        if eid in covered:
            src.append("E")   # e2e 已回放验证
        if src:
            _ok(f"{eid:<22} 来源 {''.join(src)}")
        else:
            _fail(f"{eid:<22} 无任何验证来源")
            problems.append(f"结局 {eid} 无验证来源")
    return problems


# ── main ───────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="霜语 · 一键门禁")
    ap.add_argument("--fast", action="store_true", help="跳过 fuzz（只跑 ① ③ ④）")
    ap.add_argument("--chapter", help="fuzz 只从指定章入口起步")
    ap.add_argument("--samples", type=int, default=40, help="fuzz 采样条数（默认 40）")
    args = ap.parse_args()

    t0 = time.time()
    problems: list[str] = []
    # 防御：清除外部或上一次运行可能残留的入口覆盖。
    os.environ.pop("DSE_ENTRY", None)

    problems += gate_check()
    problems += gate_declared_fields()
    if not args.fast:
        problems += gate_fuzz(args.samples, chapter=args.chapter)
    e2e_problems, covered = gate_e2e()
    problems += e2e_problems
    problems += gate_coverage(covered)

    _hr("总结")
    dt = time.time() - t0
    if problems:
        _fail(f"{len(problems)} 个问题（耗时 {dt:.1f}s）")
        return 1
    _ok(f"全部门禁通过（耗时 {dt:.1f}s）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""霜语 · 完整游戏流程导出核心。

CLI 只是编排层（见 tools/frostwords_cli.py），真正的采集与渲染都在这里。

为什么能"完整"：
    · 订阅 `scene/enter` —— 该事件在 onEnter 效果结算之后、渲染之前发出，
      因此每个场景都能拿到「玩家此刻真正看到」的状态与可见选项。
    · hook `io.ask` —— 引擎与全部五种 mode 插件的输入都经这一个通道，
      所以 battle 的多回合、dialogue 的连问、trade 的逐日都会被记下。
    · 相邻场景状态快照做 diff，导出每一步的数值变化。

刻意不做的事：**不模拟引擎语义**。采集全程跑真实引擎，只是旁听事件，
不参与推进。这样导出的流程与 `dse play` 完全一致。

产出三种格式：
    .md   可读剧本（默认）
    .json 结构化流程（步 / 输入 / 状态轨迹），便于程序消费
    .html 单文件浏览器阅读版，状态变化可折叠
"""

from __future__ import annotations

import contextlib
import html
import importlib.metadata
import io
import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dse_core.loader import load_project                     # noqa: E402
from dse_core.sdk import create_engine                       # noqa: E402

DEFAULT_SEED = 20261115
CASES_FILE = ROOT / "tests" / "e2e_cases.json"
EXPORT_DIR = ROOT / "exports"

# 状态快照里对读者无意义、且每步都变的内部字段
NOISE_KEYS = ("visits", "onceSeen")


# ── 用例数据 ───────────────────────────────────────────────────
def load_cases() -> dict[str, dict]:
    """读 tests/e2e_cases.json，返回 {结局 ID: 用例}。"""
    if not CASES_FILE.exists():
        raise FileNotFoundError(
            f"缺少 {CASES_FILE}；请先运行 "
            "python tools/solve_e2e.py --all --write-cases"
        )
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    return {c["expect_scene"]: c for c in cases}


def engine_version() -> str:
    try:
        return importlib.metadata.version("dse-core")
    except Exception:
        return "unknown"


# ── 状态工具 ───────────────────────────────────────────────────
def flatten(data, prefix: str = "", top: bool = True) -> dict:
    """把嵌套状态摊平成点路径；丢掉 visits / onceSeen 这类内部噪音。"""
    out: dict = {}
    if not isinstance(data, dict):
        return out
    for k, v in data.items():
        if top and k in NOISE_KEYS:
            continue
        path = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, dict):
            out.update(flatten(v, path, top=False))
        elif isinstance(v, (str, int, float, bool, type(None))):
            out[path] = v
        elif isinstance(v, (list, tuple)):
            out[path] = list(v)
        else:
            out[path] = str(v)
    return out


def diff_states(before: dict, after: dict) -> list[dict]:
    """比较两个摊平状态，返回变化列表。"""
    changes = []
    for key in sorted(set(before) | set(after)):
        a, b = before.get(key), after.get(key)
        if a != b:
            changes.append({"path": key, "from": a, "to": b})
    return changes


# ── 核心采集 ───────────────────────────────────────────────────
def capture(script: list[str], seed: int = DEFAULT_SEED,
            label: str = "") -> dict:
    """用真实引擎跑完一局，返回结构化流程记录。

    ★ 环境隔离：sdk.create_engine(entry=...) 会写 DSE_ENTRY 且不清理，
      这里显式清掉，保证导出总是从 dse.yml 的 entry 起步。
    """
    os.environ.pop("DSE_ENTRY", None)
    os.environ["DSE_INPUT"] = ",".join(str(x) for x in script)

    ctx = create_engine(root=ROOT, quiet=True)
    engine = ctx.services["engine"]
    state = ctx.services["state"]
    io_svc = ctx.services["io"]
    engine.rng = random.Random(seed)
    random.seed(seed)          # combat 用全局随机源，必须一起固定

    steps: list[dict] = []
    pending_inputs: list[str] = []
    original_ask = io_svc.ask

    def hooked_ask(prompt: str = "> ") -> str:
        line = original_ask(prompt)
        pending_inputs.append(line)
        return line

    def on_enter(sid, scene):
        # 上一场景到此结束：把期间累积的输入归给它
        if steps:
            steps[-1]["inputs"] = list(pending_inputs)
            pending_inputs.clear()

        mode = scene.get("mode") or "normal"
        snap = flatten(state.snapshot())

        # 可见选项：与 engine.render 同口径（if 条件 + once 消费）
        once_seen = set(state.get("onceSeen") or [])
        visible = []
        for i, choice in enumerate(scene.get("choices") or []):
            if not state.check(choice.get("if")):
                continue
            if choice.get("once") and engine._once_key(sid, i, choice) in once_seen:
                continue
            visible.append({
                "index": len(visible) + 1,
                "text": state.interpolate(choice.get("text", "")),
                "goto": choice.get("goto"),
                "if": choice.get("if"),
            })

        # 玩家实际看到的正文：variant / extraText 条件段 / 插值
        text = getattr(engine, "_variant_text", None)
        if text is None:
            text = scene.get("text", "")
        for seg in scene.get("extraText") or []:
            if isinstance(seg, dict) and state.check(seg.get("if")):
                text = f"{text}\n{seg.get('text', '')}"
        text = state.interpolate(text)

        steps.append({
            "n": len(steps) + 1,
            "scene": sid,
            "title": state.interpolate(scene.get("title") or sid),
            "mode": mode,
            "text": text,
            "choices": visible,
            "inputs": [],
            "state": snap,
        })

    off = ctx.on("scene/enter", on_enter)
    io_svc.ask = hooked_ask
    final_scene = None
    final_state: dict = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            engine.start()
        final_scene = engine.current
        final_state = flatten(state.snapshot())
    finally:
        off()
        io_svc.ask = original_ask
        os.environ.pop("DSE_INPUT", None)
        os.environ.pop("DSE_ENTRY", None)
        ctx.dispose()

    if steps:
        steps[-1]["inputs"] = list(pending_inputs)

    # 补出每一相对下一步的状态变化（数值轨迹）
    for i, step in enumerate(steps):
        step["changes"] = diff_states(
            step["state"], steps[i + 1]["state"] if i + 1 < len(steps) else final_state
        )

    return {
        "meta": {
            "project": "霜语 · Frostwords",
            "engine": f"dse-core {engine_version()}",
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "seed": seed,
            "label": label,
            "script": ",".join(str(x) for x in script),
            "step_count": len(steps),
            "scene_count": len({s["scene"] for s in steps}),
            # 一个场景内可连问多题 / 打多回合 / 走多天，输入次数通常 > 场景步数
            "input_count": sum(len(s["inputs"]) for s in steps),
            "final_scene": final_scene,
        },
        "steps": steps,
        "final_state": final_state,
    }


# ── 渲染：Markdown ─────────────────────────────────────────────
def render_markdown(record: dict) -> str:
    m = record["meta"]
    lines = [
        f"# {m['project']} · 一次完整游戏流程",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 结局 | `{m['final_scene']}` |",
        f"| 流程标签 | {m['label'] or '自定义脚本'} |",
        f"| 引擎 | {m['engine']} |",
        f"| 随机种子 | `{m['seed']}` |",
        f"| 场景步 / 玩家输入 | {m['step_count']} / {m['input_count']} |",
        f"| 不同场景 | {m['scene_count']} |",
        f"| 生成时间 | {m['generated_at']} |",
        f"| 输入脚本 | `{m['script']}` |",
        "",
        "> 本文件由 `frostwords export-run` 从**真实引擎**逐场景采集生成，",
        "> 与 `dse play` 的实际流程一致。状态变化是相邻场景快照的 diff。",
        "",
        "---",
        "",
    ]
    for s in record["steps"]:
        lines.append(f"## {s['n']:02d} · {s['title']}")
        lines.append("")
        lines.append(f"`{s['scene']}` · 模式 `{s['mode']}`")
        lines.append("")
        lines.append((s["text"] or "（无正文）").rstrip())
        lines.append("")
        if s["choices"]:
            lines.append("**当时可见的选项**")
            lines.append("")
            for c in s["choices"]:
                cond = f"  · 条件 `{c['if']}`" if c["if"] else ""
                lines.append(f"{c['index']}. {c['text']}{cond}")
            lines.append("")
        if s["inputs"]:
            lines.append("**输入**：" + " ".join(f"`{x}`" for x in s["inputs"]))
            lines.append("")
        if s["changes"]:
            parts = [f"`{c['path']}` {c['from']} → {c['to']}" for c in s["changes"]]
            lines.append("**状态变化**：" + "，".join(parts))
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## 终局状态")
    lines.append("")
    lines.append("| 字段 | 值 |")
    lines.append("|---|---|")
    for k, v in sorted(record["final_state"].items()):
        lines.append(f"| `{k}` | {v} |")
    lines.append("")
    return "\n".join(lines)


# ── 渲染：JSON ─────────────────────────────────────────────────
def render_json(record: dict) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2, default=str) + "\n"


# ── 渲染：HTML ─────────────────────────────────────────────────
def render_html(record: dict) -> str:
    m = record["meta"]
    e = html.escape
    css = """
    :root{--bg:#faf9f7;--fg:#2b2b2b;--muted:#777;--line:#e3ded6;--accent:#8a5a3b}
    *{box-sizing:border-box}
    body{margin:0 auto;max-width:760px;padding:48px 24px 96px;background:var(--bg);
         color:var(--fg);font:16px/1.9 "Georgia","Songti SC","SimSun",serif}
    h1{font-size:28px;border-bottom:2px solid var(--accent);padding-bottom:14px}
    h2{font-size:19px;margin-top:44px;color:var(--accent)}
    .meta{background:#f2eee8;border:1px solid var(--line);border-radius:8px;padding:16px 20px}
    .meta div{margin:3px 0;font-size:14px;color:var(--muted)}
    .meta b{color:var(--fg)}
    .scene{border-top:1px solid var(--line);margin-top:36px;padding-top:8px}
    .sid{font:12px/1.6 ui-monospace,Consolas,monospace;color:var(--muted)}
    .text{white-space:pre-wrap;margin:18px 0}
    .choices{padding-left:22px;color:#444}
    .io{font:13px/1.8 ui-monospace,Consolas,monospace;color:#555;
        background:#f2eee8;padding:8px 12px;border-radius:6px;display:inline-block}
    details{margin-top:12px;font-size:13px;color:var(--muted)}
    summary{cursor:pointer}
    .chg{font:12px/1.8 ui-monospace,Consolas,monospace;padding-left:16px}
    table{border-collapse:collapse;width:100%;font-size:13px}
    td,th{border:1px solid var(--line);padding:6px 10px;text-align:left}
    code{font-family:ui-monospace,Consolas,monospace}
    """
    out = [
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
        f"<title>{e(m['project'])} · 完整流程</title>",
        f"<style>{css}</style></head><body>",
        f"<h1>{e(m['project'])} · 一次完整游戏流程</h1>",
        "<div class=\"meta\">",
        f"<div>结局 <b>{e(str(m['final_scene']))}</b>　·　{e(m['engine'])}</div>",
        f"<div>种子 <code>{m['seed']}</code>　·　{m['step_count']} 场景步 / "
        f"{m['input_count']} 次输入 / {m['scene_count']} 个不同场景</div>",
        f"<div>生成时间 {e(m['generated_at'])}　·　{e(m['label'] or '自定义脚本')}</div>",
        "</div>",
    ]
    for s in record["steps"]:
        out.append("<div class=\"scene\">")
        out.append(f"<h2>{s['n']:02d} · {e(s['title'])}</h2>")
        out.append(f"<div class=\"sid\">{e(s['scene'])} · {e(s['mode'])}</div>")
        out.append(f"<div class=\"text\">{e(s['text'])}</div>")
        if s["choices"]:
            out.append("<div class=\"choices\">")
            for c in s["choices"]:
                out.append(f"<div>{c['index']}. {e(c['text'])}</div>")
            out.append("</div>")
        if s["inputs"]:
            out.append(f"<p><span class=\"io\">输入　{e('  '.join(s['inputs']))}</span></p>")
        if s["changes"]:
            out.append("<details><summary>状态变化</summary><div class=\"chg\">")
            for c in s["changes"]:
                out.append(f"{e(c['path'])}: {e(str(c['from']))} → {e(str(c['to']))}<br>")
            out.append("</div></details>")
        out.append("</div>")
    out.append("<h2>终局状态</h2><table><tr><th>字段</th><th>值</th></tr>")
    for k, v in sorted(record["final_state"].items()):
        out.append(f"<tr><td><code>{e(k)}</code></td><td>{e(str(v))}</td></tr>")
    out.append("</table></body></html>")
    return "\n".join(out)


RENDERERS = {"md": render_markdown, "json": render_json, "html": render_html}
SUFFIX = {"md": ".md", "json": ".json", "html": ".html"}


# ── 全场景静态大纲（"完整流程"的另一种读法）─────────────────────
def render_outline() -> str:
    """导出全部场景与全部出边的静态大纲，不跑引擎。"""
    from dse_core import graph

    project = load_project(ROOT)
    d = project.dict
    report = graph.analyze(d, project.entry)
    lines = [
        "# 霜语 · 全场景流程大纲",
        "",
        f"共 **{report['scenes']}** 场景 / **{len(report['endings'])}** 结局，"
        f"入口 `{project.entry}`。按内容包加载顺序列出。",
        "",
        "> 这是一张静态流程图（所有分支都列出），不是某一局的实际走法；"
        "单局流程请用 `frostwords export-run`。",
        "",
        "---",
        "",
    ]
    for sid, sc in d.items():
        mode = sc.get("mode") or "normal"
        lines.append(f"## `{sid}` · {sc.get('title') or sid}")
        lines.append("")
        lines.append(f"模式 `{mode}`　·　结局：{'是' if graph.is_ending(sc) else '否'}")
        lines.append("")
        text = (sc.get("text") or "").strip()
        if text:
            first = text.splitlines()[0]
            lines.append(f"> {first}" + (" …" if len(text.splitlines()) > 1 else ""))
            lines.append("")
        edges = graph.edges_of(sid, sc)
        if edges:
            # edges_of 只给 to/kind/raw，不带条件。用 raw 反查场景选项，
            # 把 if 条件、选项文本、加权权重一并补上，大纲才真的可读。
            meta: dict[str, tuple] = {}
            for choice in sc.get("choices") or []:
                g = choice.get("goto")
                if isinstance(g, dict):
                    meta[f"call:{g.get('call')}"] = (
                        choice.get("if"), choice.get("text", ""), None)
                    continue
                items = g if isinstance(g, list) else ([{"to": g}] if g else [])
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    raw = str(item.get("to") or "")
                    if raw and raw not in meta:
                        meta[raw] = (choice.get("if"), choice.get("text", ""),
                                     item.get("weight"))
            lines.append("| # | 目标 | 类型 | 条件 | 选项 / 权重 |")
            lines.append("|---|---|---|---|---|")
            for i, edge in enumerate(edges, 1):
                cond, label_text, weight = meta.get(edge["raw"], (None, "", None))
                detail = (label_text or "—").replace("|", "\\|")
                if weight is not None:
                    detail += f"（权重 {weight}）"
                if edge["kind"] == "mode":
                    detail = f"`{edge['raw']}`"
                cond = f"`{cond}`" if cond else "—"
                lines.append(f"| {i} | `{edge['to']}` | {edge['kind']} | {cond} | {detail} |")
            lines.append("")
        else:
            lines.append("（无出边）")
            lines.append("")
    return "\n".join(lines)


# ── 对外入口 ───────────────────────────────────────────────────
def export_run(script: list[str], formats: list[str], output: Path | None,
               seed: int = DEFAULT_SEED, label: str = "") -> dict:
    """采集一局并写出文件，返回摘要 dict。"""
    record = capture(script, seed=seed, label=label)
    out_dir = (output.parent if output else EXPORT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = (output.stem if output else f"playthrough-{record['meta']['final_scene']}")
    written: dict[str, str] = {}
    for fmt in formats:
        if output and len(formats) == 1:
            path = output
        else:
            path = out_dir / f"{stem}{SUFFIX[fmt]}"
        path.write_text(RENDERERS[fmt](record), encoding="utf-8")
        written[fmt] = str(path)
    return {
        "ok": True,
        "final_scene": record["meta"]["final_scene"],
        "steps": record["meta"]["step_count"],
        "scenes": record["meta"]["scene_count"],
        "formats": list(written),
        "files": written,
        "seed": seed,
        "label": label,
    }

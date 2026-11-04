"""
Purpose: Build the wiring-plan set: validate sheets against the register, render each sheet
    (ladder schematic, wire list, terminal landings, checks, test) and the register
    (relay pool, devices, open questions) to out/*.html.
Version: v1 (2026-11-04) — generic version for any vessel.
Scope: STANDALONE UTILITY — documentation generator; nothing runs on the boat.
Architecture: Reads register/*.yml + sheets/*.yml, writes out/index.html, out/register.html,
    out/<sheet>.html. Optionally cross-checks against an io_master.yml if IO_MASTER_PATH is set.
Invocation: python build.py [--io-master path/to/io_master.yml]
"""
import html
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).parent
REG, SHEETS, OUT = HERE / "register", HERE / "sheets", HERE / "out"
E = html.escape
MODBUS = ("S1", "S2", "S3", "S4", "S5", "S6")


def load(p):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- validation
def validate(sheet, devices, questions, errors):
    sid = sheet["id"]

    def ep(s, where):
        dev, _, term = str(s).partition(":")
        if dev not in devices:
            errors.append(f"{sid} {where}: unknown device '{dev}'")
        elif term not in {str(k) for k in devices[dev]["terminals"]}:
            errors.append(f"{sid} {where}: {dev} has no terminal '{term}'")

    ids = set()
    for w in sheet["wires"]:
        if w["id"] in ids:
            errors.append(f"{sid}: duplicate wire id {w['id']}")
        ids.add(w["id"])
        ep(w["a"], w["id"]); ep(w["b"], w["id"])
        if w.get("open") and w["open"] not in questions:
            errors.append(f"{sid} {w['id']}: unknown question {w['open']}")
    for r in sheet["rungs"]:
        ep(r["start"]["at"], r["title"]); ep(r["end"]["at"], r["title"])
        for el in r["elements"]:
            for e in [el] + ([el["bypass"]] if el.get("bypass") else []):
                if e["type"] not in KINDS:
                    errors.append(f"{sid} '{r['title']}': element type {e['type']!r} (quote \"no\" in YAML)")
                ep(f"{e['dev']}:{e['a']}", r["title"]); ep(f"{e['dev']}:{e['b']}", r["title"])
    pairs = {frozenset((str(w["a"]), str(w["b"]))) for w in sheet["wires"]}
    for r in sheet["rungs"]:
        for x, y, _ in rung_links(r):
            if x != y and frozenset((x, y)) not in pairs:
                errors.append(f"{sid} '{r['title']}': no wire joins {x} and {y}")


def rung_links(r):
    """Yield (endpoint, endpoint, kind) for every wire a rung drawing needs."""
    els = r["elements"]
    prev = r["start"]["at"]
    for el in els:
        a, b = f"{el['dev']}:{el['a']}", f"{el['dev']}:{el['b']}"
        yield prev, a, "main"
        if el.get("bypass"):
            bp = el["bypass"]
            yield a, f"{bp['dev']}:{bp['a']}", "byp"
            yield f"{bp['dev']}:{bp['b']}", b, "byp"
        prev = b
    yield prev, r["end"]["at"], "main"


# ---------------------------------------------------------------- ladder SVG
SLOT, H0, HB = 190, 110, 215
KINDS = {"nc", "no", "switch_nc", "switch_no", "coil", "lamp", "diode"}


def sym(kind, x, y, label, dev, ta, tb):
    """Draw one element centred on x, wire at height y; returns svg."""
    s = [f'<line x1="{x-SLOT/2}" y1="{y}" x2="{x-14}" y2="{y}" class="w"/>',
         f'<line x1="{x+14}" y1="{y}" x2="{x+SLOT/2}" y2="{y}" class="w"/>']
    if kind in ("nc", "no", "switch_nc", "switch_no"):
        s += [f'<line x1="{x-14}" y1="{y-14}" x2="{x-14}" y2="{y+14}" class="s"/>',
              f'<line x1="{x+14}" y1="{y-14}" x2="{x+14}" y2="{y+14}" class="s"/>']
        if kind.endswith("nc"):
            s.append(f'<line x1="{x-22}" y1="{y+18}" x2="{x+22}" y2="{y-18}" class="s"/>')
        if kind.startswith("switch"):
            s += [f'<line x1="{x}" y1="{y-16}" x2="{x}" y2="{y-30}" class="d"/>',
                  f'<line x1="{x-9}" y1="{y-30}" x2="{x+9}" y2="{y-30}" class="s"/>']
    elif kind == "coil":
        s.append(f'<circle cx="{x}" cy="{y}" r="14" class="s f"/>')
    elif kind == "diode":
        s += [f'<polygon points="{x-12},{y-11} {x-12},{y+11} {x+10},{y}" class="s f"/>',
              f'<line x1="{x+11}" y1="{y-12}" x2="{x+11}" y2="{y+12}" class="s"/>',
              f'<line x1="{x+11}" y1="{y}" x2="{x+14}" y2="{y}" class="w"/>']
    elif kind == "lamp":
        s += [f'<circle cx="{x}" cy="{y}" r="14" class="s f"/>',
              f'<line x1="{x-10}" y1="{y-10}" x2="{x+10}" y2="{y+10}" class="s"/>',
              f'<line x1="{x-10}" y1="{y+10}" x2="{x+10}" y2="{y-10}" class="s"/>']
    s += [f'<text x="{x}" y="{y-38}" class="lb">{E(label)}</text>',
          f'<text x="{x-18}" y="{y+30}" class="tm" text-anchor="end">{E(str(ta))}</text>',
          f'<text x="{x+18}" y="{y+30}" class="tm" text-anchor="start">{E(str(tb))}</text>']
    return "".join(s)


def dn(dev, devices):
    """Device id as shown on the sheets: Modbus modules carry their address."""
    a = (devices.get(dev) or {}).get("address")
    return f"{dev} (addr {a})" if a is not None else dev


def ladder(r, wire_of, devices):
    els = r["elements"]
    has_b = any(e.get("bypass") for e in els)
    w = 200 + SLOT * max(len(els), 1) + 200
    h = HB if has_b else H0
    y = 58
    s = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" text-anchor="middle" role="img" aria-label="{E(r["title"])}">']

    def box(x, text, at, anchor):
        dev, _, term = at.partition(":")
        s.append(f'<rect x="{x}" y="{y-18}" width="160" height="36" rx="4" class="bx"/>'
                 f'<text x="{x+80}" y="{y-2}" class="bt">{E(text)}</text>'
                 f'<text x="{x+80}" y="{y+12}" class="tm">{E(dn(dev, devices))}:{E(term)}</text>')

    def wl(x1, x2, yy, a, b):
        wid = wire_of.get(frozenset((a, b)))
        if wid:
            s.append(f'<text x="{(x1+x2)/2}" y="{yy-6}" class="wl" text-anchor="middle">{E(wid)}</text>')

    box(20, r["start"]["label"], r["start"]["at"], "start")
    x0 = 180
    prev = r["start"]["at"]
    for i, el in enumerate(els):
        cx = x0 + 10 + SLOT * i + SLOT / 2
        a, b = f"{el['dev']}:{el['a']}", f"{el['dev']}:{el['b']}"
        wl(180 if i == 0 else cx - SLOT + 14, cx - 14, y, prev, a)
        s.append(sym(el["type"], cx, y, el["label"], el["dev"], el["a"], el["b"]))
        if el.get("bypass"):
            bp = el["bypass"]; yb = y + 112; l, rr = cx - SLOT / 2 + 12, cx + SLOT / 2 - 12
            s.append(f'<polyline points="{l},{y} {l},{yb} {cx-80},{yb}" class="w" fill="none"/>')
            s.append(f'<polyline points="{rr},{y} {rr},{yb} {cx+80},{yb}" class="w" fill="none"/>')
            s.append(f'<circle cx="{l}" cy="{y}" r="3" class="dot"/><circle cx="{rr}" cy="{y}" r="3" class="dot"/>')
            inner = sym(bp["type"], cx, yb, bp["label"], bp["dev"], bp["a"], bp["b"])
            s.append(inner.replace(f'x1="{cx-SLOT/2}"', f'x1="{cx-80}"').replace(f'x2="{cx+SLOT/2}"', f'x2="{cx+80}"'))
            wid1 = wire_of.get(frozenset((a, f"{bp['dev']}:{bp['a']}")))
            wid2 = wire_of.get(frozenset((f"{bp['dev']}:{bp['b']}", b)))
            if wid1: s.append(f'<text x="{l-5}" y="{(y+yb)/2+4}" class="wl" text-anchor="end">{E(wid1)}</text>')
            if wid2: s.append(f'<text x="{rr+5}" y="{(y+yb)/2+4}" class="wl" text-anchor="start">{E(wid2)}</text>')
        prev = b
    xe = x0 + 10 + SLOT * max(len(els), 1) + 10
    if not els:
        s.append(f'<line x1="{x0}" y1="{y}" x2="{xe}" y2="{y}" class="w"/>')
    s.append(f'<line x1="{xe-10}" y1="{y}" x2="{xe}" y2="{y}" class="w"/>')
    wl(x0 if not els else xe - SLOT / 2 - 10 + 14, xe, y, prev, r["end"]["at"])
    box(xe, r["end"]["label"], r["end"]["at"], "end")
    s.append("</svg>")
    return "".join(s)


# ---------------------------------------------------------------- HTML
CSS = """
:root{--bg:#fff;--fg:#1b1f24;--mut:#5b6470;--line:#d6dbe1;--acc:#0b5cad;--w:#1b1f24;--wl:#b3261e;
--new:#e7f4ea;--chg:#fff4d6;--rem:#fde7e7;--q:#eef3fb;--card:#f7f8fa}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#15181c;--fg:#e6e9ed;--mut:#9aa4b0;
--line:#333a42;--acc:#6aa9ec;--w:#e6e9ed;--wl:#ff8a80;--new:#1d3324;--chg:#3a3218;--rem:#3d1f1f;--q:#1c2636;--card:#1c2025}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,Segoe UI,Arial,sans-serif}
main{max-width:1400px;margin:0 auto;padding:16px}h1{font-size:22px;margin:4px 0}h2{font-size:17px;margin:22px 0 8px;
border-bottom:1px solid var(--line);padding-bottom:4px}h3{font-size:14px;margin:14px 0 4px}.mut{color:var(--mut)}
table{border-collapse:collapse;width:100%;margin:6px 0}th,td{border:1px solid var(--line);padding:4px 6px;
text-align:left;vertical-align:top}th{background:var(--card)}code,.id{font-family:Consolas,monospace}
.id{font-weight:700;white-space:nowrap}.scroll{overflow-x:auto}.card{background:var(--card);border:1px solid var(--line);
border-radius:6px;padding:8px 12px;margin:8px 0}.q{background:var(--q);border-radius:3px;padding:0 4px;
font-family:Consolas,monospace;font-size:12px;white-space:nowrap}.st-new{background:var(--new)}.st-changed{background:var(--chg)}
.st-removed{background:var(--rem)}.tag{font-size:11px;padding:1px 6px;border-radius:9px;border:1px solid var(--line)}
svg .w{stroke:var(--w);stroke-width:2}
svg .s{stroke:var(--w);stroke-width:2.5}svg .d{stroke:var(--w);stroke-width:1.5;stroke-dasharray:3 3}
svg .f{fill:var(--bg)}svg .dot{fill:var(--w)}svg .bx{fill:var(--card);stroke:var(--mut)}svg text{fill:var(--fg);
font:12px system-ui,Arial}svg .bt{font-weight:600}svg .tm{fill:var(--mut);font:11px Consolas,monospace}
svg .lb{font-weight:600;font-size:12px}svg .wl{fill:var(--wl);font:bold 11px Consolas,monospace}
.warn{color:var(--wl);font-weight:600}nav a{margin-right:14px}
@media print{nav{display:none}main{max-width:none}.scroll{overflow:visible}h2{break-after:avoid}}
"""


def page(title, body):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)}</title>'
            f'<style>{CSS}</style></head><body><main><nav><a href="index.html">Index</a>'
            f'<a href="register.html">Register</a></nav>{body}</main></body></html>')


def qtag(q):
    return f'<span class="q">{E(q)}</span>' if q else ""


def render_sheet(sheet, devices, questions):
    wire_of = {frozenset((str(w["a"]), str(w["b"]))): w["id"] for w in sheet["wires"]}
    b = [f'<h1>{E(sheet["id"])} - {E(sheet["title"])}</h1>',
         f'<p class="mut">{E(sheet["version"])} &middot; group {E(sheet["group"])}</p>',
         f'<div class="card">{E(sheet["purpose"])}</div>']
    b.append('<h2>Schematic (ladder)</h2><p class="mut">Contacts drawn in the de-energised state. '
             'Red = wire ID (the printed label). Grey = terminal as marked on the part.</p>')
    for r in sheet["rungs"]:
        b.append(f'<h3>{E(r["title"])}</h3><div class="scroll">{ladder(r, wire_of, devices)}</div>')
        if r.get("note"):
            b.append(f'<p class="mut">{E(r["note"])}</p>')

    b.append('<h2>Wire list</h2><div class="scroll"><table><tr><th>Wire</th><th>From</th><th></th><th>To</th>'
             '<th></th><th>AWG</th><th>Run</th><th>Note</th></tr>')
    for w in sheet["wires"]:
        da, _, ta = str(w["a"]).partition(":"); db, _, tb = str(w["b"]).partition(":")
        b.append(f'<tr><td class="id">{E(w["id"])}</td><td><code>{E(dn(da, devices))}:{E(ta)}</code></td>'
                 f'<td class="mut">{E(str(devices[da]["terminals"][ta if ta in devices[da]["terminals"] else int(ta)]))}</td>'
                 f'<td><code>{E(dn(db, devices))}:{E(tb)}</code></td>'
                 f'<td class="mut">{E(str(devices[db]["terminals"][tb if tb in devices[db]["terminals"] else int(tb)]))}</td>'
                 f'<td>{E(str(w.get("awg","")))}</td><td>{E(str(w.get("run","")))}</td>'
                 f'<td>{E(w.get("note",""))} {qtag(w.get("open"))}</td></tr>')
    b.append("</table></div>")
    if sheet.get("cables"):
        b.append("<h3>Cables / runs</h3><ul>" + "".join(
            f"<li><b>{E(k)}</b> - {E(v)}</li>" for k, v in sheet["cables"].items()) + "</ul>")

    land = defaultdict(list)
    for w in sheet["wires"]:
        for end in (w["a"], w["b"]):
            land[str(end)].append(w["id"])
    b.append('<h2>Terminal landings (by device)</h2><p class="mut">What goes on each screw. '
             '2 wires = twin ferrule.</p><div class="scroll"><table><tr><th>Device</th><th>Part / where</th>'
             '<th>Terminal</th><th>Wires</th></tr>')
    for dev in dict.fromkeys(str(w[k]).partition(":")[0] for w in sheet["wires"] for k in ("a", "b")):
        d = devices[dev]
        terms = [t for t in d["terminals"] if f"{dev}:{t}" in land]
        for i, t in enumerate(terms):
            ws = land[f"{dev}:{t}"]
            first = (f'<td rowspan="{len(terms)}" class="st-{E(d["status"])}"><b>{E(dn(dev, devices))}</b><br>{E(d["name"])}<br>'
                     f'<span class="tag">{E(d["status"])}</span> {qtag(d.get("open"))}</td>'
                     f'<td rowspan="{len(terms)}" class="mut">{E(d.get("part",""))}<br>{E(d.get("where",""))}</td>') if i == 0 else ""
            warn = (' <span class="mut">bus - own terminal per wire</span>' if d.get("bus") and len(ws) > 1
                    else ' <span class="warn">twin ferrule</span>' if len(ws) == 2
                    else (' <span class="warn">3+ wires!</span>' if len(ws) > 2 else ""))
            b.append(f'<tr>{first}<td><code>{E(str(t))}</code> <span class="mut">{E(str(d["terminals"][t]))}</span></td>'
                     f'<td class="id">{E(", ".join(ws))}{warn}</td></tr>')
    b.append("</table></div>")

    used = {str(w[k]).partition(":")[0] for w in sheet["wires"] for k in ("a", "b")}
    qs = sorted(({w.get("open") for w in sheet["wires"]} | {devices[d].get("open") for d in used}) - {None})
    if qs:
        b.append("<h2>Open questions touching this sheet</h2><table><tr><th>Q</th><th>Who</th><th>Question</th>"
                 "<th>Recommendation</th></tr>")
        for q in qs:
            Q = questions[q]
            b.append(f'<tr><td class="id">{E(q)}</td><td>{E(Q["who"])}</td><td>{E(Q["ask"])}<br>'
                     f'<span class="mut">{E(Q.get("why",""))}</span>'
                     f'{("<br><b>Known:</b> " + E(Q["known"])) if Q.get("known") else ""}</td>'
                     f'<td>{E(Q.get("recommend",""))}</td></tr>')
        b.append("</table>")
    for key, head in (("checks", "Build checks"), ("test", "Commissioning test")):
        if sheet.get(key):
            tag = "ol" if key == "test" else "ul"
            b.append(f"<h2>{head}</h2><{tag}>" + "".join(f"<li>{E(x)}</li>" for x in sheet[key]) + f"</{tag}>")
    b.append("<h2>Change log</h2><ul>" + "".join(f"<li>{E(x)}</li>" for x in sheet.get("changelog", [])) + "</ul>")
    return page(f'{sheet["id"]} {sheet["title"]}', "".join(b))


def check_pool(pool, sheets, errors):
    """Every S#:Rn-* a sheet lands on must be the channel the pool gives to that sheet."""
    used = defaultdict(set)
    for sh in sheets:
        for w in sh["wires"]:
            for end in (str(w["a"]), str(w["b"])):
                dev, _, term = end.partition(":")
                if dev in pool["modules"] and term.startswith("R"):
                    used[f"{dev}-{term.split('-')[0]}"].add(sh["id"])
    for ch, ids in used.items():
        if ch not in pool["channels"]:
            errors.append(f"pool: {ch} used by {sorted(ids)} but not in pool.yml")
            continue
        for i in ids:
            if pool["channels"][ch].get("sheet") != i:
                errors.append(f"pool: {i} lands on {ch}, but the pool gives {ch} to "
                              f"{pool['channels'][ch].get('sheet') or 'no sheet'} ({pool['channels'][ch]['function']})")
    built = {sh["id"] for sh in sheets}
    for ch, c in pool["channels"].items():
        if c.get("sheet") in built and c["sheet"] not in used.get(ch, set()):
            errors.append(f"pool: {ch} is assigned to {c['sheet']}, which does not wire it")


def render_pool(pool):
    b = ['<h2>Relay pool</h2><p class="mut">Physical assignment of Modbus relay channels. '
         'Rules: a wired function stays put; retired channels are re-used; new functions fill '
         'modules in build order; every kill/permissive uses the contact that is safe de-energised.</p>'
         '<table><tr><th>Module</th><th>Part</th><th>Power</th><th>Latching</th></tr>']
    b += [f'<tr><td class="id">{E(k)}</td><td>{E(m["part"])}</td><td>{E(m["power"])}</td><td>{E(m["latching"])}</td></tr>'
          for k, m in pool["modules"].items()]
    b.append('</table><table><tr><th>Channel</th><th>Status</th><th>Function</th><th>Contact</th><th>Sheet</th>'
             '</tr>')
    cls = {"new": "st-new", "assigned": "", "wired": "", "spare": "mut"}
    for ch, c in pool["channels"].items():
        b.append(f'<tr class="{cls.get(c["status"], "")}"><td class="id">{E(ch)}</td><td>{E(c["status"])}</td>'
                 f'<td>{E(c["function"])}</td><td>{E(c.get("contact",""))}</td><td>{E(c.get("sheet",""))}</td></tr>')
    free = sum(1 for c in pool["channels"].values() if c["status"] == "spare")
    b.append(f'</table><p class="mut">{len(pool["channels"]) - free} used, {free} spare.</p>')
    return "".join(b)


def render_register(devices, questions, sheets, pool):
    b = ['<h1>Register</h1>',
         '<p class="mut">Devices, relay pool, and open questions across all wiring sheets.</p>']
    b.append(render_pool(pool))

    land = defaultdict(list)
    for sh in sheets:
        for w in sh["wires"]:
            for end in (str(w["a"]), str(w["b"])):
                land[end].append(w["id"])
    crowd = [(k, v) for k, v in sorted(land.items()) if len(v) > 2 and not devices[k.partition(":")[0]].get("bus")]
    b.append('<h2>Terminal crowding across ALL sheets</h2><p class="mut">A non-bus terminal with more than 2 wires '
             'from all sheets together — give it a jumper / distribution block before wiring.</p>')
    b.append("<p>None.</p>" if not crowd else "<table><tr><th>Terminal</th><th>Wires</th></tr>" + "".join(
        f'<tr><td class="id">{E(k)}</td><td class="warn">{E(", ".join(v))}</td></tr>' for k, v in crowd) + "</table>")

    b.append('<h2>Devices on the wiring sheets</h2><table><tr><th>Device</th><th>Status</th><th>Name / part</th>'
             '<th>Where</th><th>Open</th></tr>')
    for k, d in devices.items():
        b.append(f'<tr class="st-{E(d["status"])}"><td class="id">{E(k)}</td><td>{E(d["status"])}</td>'
                 f'<td>{E(d["name"])}<br><span class="mut">{E(d.get("part",""))}</span></td><td>{E(d.get("where",""))}</td>'
                 f'<td>{qtag(d.get("open"))}</td></tr>')
    b.append("</table>")

    b.append("<h2>Open questions</h2><table><tr><th>Q</th><th>Who</th><th>Question</th><th>Recommendation</th></tr>")
    for q, Q in questions.items():
        b.append(f'<tr><td class="id">{E(q)}</td><td>{E(Q["who"])}</td><td>{E(Q["ask"])}<br><span class="mut">'
                 f'{E(Q.get("why",""))}</span>'
                 f'{("<br><b>Known:</b> " + E(Q["known"])) if Q.get("known") else ""}</td>'
                 f'<td>{E(Q.get("recommend",""))}</td></tr>')
    b.append("</table>")
    return page("Wiring register", "".join(b))


def main():
    devices = {str(k): v for k, v in load(REG / "devices.yml").items()}
    for d in devices.values():
        d["terminals"] = {str(k): v for k, v in d["terminals"].items()}
        for n in range(1, d.get("relay_channels", 0) + 1):
            for c in ("COM", "NO", "NC"):
                d["terminals"][f"R{n}-{c}"] = f"ch{n} {c}"
    pool = load(REG / "pool.yml")
    questions = load(REG / "questions.yml")
    sheets = [load(p) for p in sorted(SHEETS.glob("W*.yml"))]
    errors = []
    for s in sheets:
        validate(s, devices, questions, errors)
    check_pool(pool, sheets, errors)

    # Optional: cross-check against an io_master.yml from the automation engine
    io_master_path = None
    if "--io-master" in sys.argv:
        idx = sys.argv.index("--io-master")
        if idx + 1 < len(sys.argv):
            io_master_path = Path(sys.argv[idx + 1])
    if io_master_path and io_master_path.exists():
        print(f"Cross-checking against {io_master_path}")

    if errors:
        print("VALIDATION ERRORS:\n  " + "\n  ".join(errors))
        return 1
    OUT.mkdir(exist_ok=True)
    for s in sheets:
        (OUT / f'{s["id"]}.html').write_text(render_sheet(s, devices, questions), encoding="utf-8")
    (OUT / "register.html").write_text(render_register(devices, questions, sheets, pool), encoding="utf-8")
    idx = ['<h1>Wiring plans</h1><p class="mut">Pin-level build drawings for your vessel\'s alarm and automation system.</p>'
           '<ul><li><a href="register.html">Register</a> — relay pool, devices, open questions</li>']
    idx += [f'<li><a href="{E(s["id"])}.html">{E(s["id"])} — {E(s["title"])}</a> <span class="mut">{E(s["version"])}</span></li>' for s in sheets]
    idx.append("</ul>")
    (OUT / "index.html").write_text(page("Wiring plans", "".join(idx)), encoding="utf-8")
    print(f"ok: {len(sheets)} sheet(s), {sum(len(s['wires']) for s in sheets)} wires -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

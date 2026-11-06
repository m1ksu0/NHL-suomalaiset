"""Tekee data.json:sta sivun site/index.html.

Ajo: python build_html.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

HELSINKI = ZoneInfo("Europe/Helsinki")
HERE = Path(__file__).parent
DATA_FILE = HERE / "data.json"
OUT_FILE = HERE / "site" / "index.html"
WEEKDAYS = ["ma", "ti", "ke", "to", "pe", "la", "su"]

CSS = """
:root { --bg:#ffffff; --fg:#1b1f24; --muted:#5b6570; --line:#d9dee3; --card:#f5f7f9; --accent:#0b5cad; --hi:#fff3c4; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#14181d; --fg:#e6e9ec; --muted:#9aa5b0; --line:#2c343c; --card:#1c2229; --accent:#6db3ff; --hi:#4a3f12; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font:16px/1.45 system-ui,Segoe UI,Arial,sans-serif; }
main { max-width: 980px; margin: 0 auto; padding: 20px 16px 48px; }
h1 { font-size: 1.7rem; margin: 0 0 4px; }
h2 { font-size: 1.3rem; margin: 36px 0 10px; border-bottom: 2px solid var(--line); padding-bottom: 4px; }
h3 { font-size: 1.05rem; margin: 22px 0 8px; color: var(--muted); }
.sub { color: var(--muted); font-size: .9rem; margin: 0; }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .92rem; }
th, td { text-align: right; padding: 5px 8px; border-bottom: 1px solid var(--line); white-space: nowrap; }
th:first-child, td:first-child, th.l, td.l { text-align: left; }
th { color: var(--muted); font-weight: 600; }
td.pts { font-weight: 700; }
.game { background: var(--card); border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; margin: 8px 0; }
.game .head { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; font-weight: 600; }
.game .time { color: var(--muted); font-weight: 400; }
.finns { margin: 6px 0 0; padding: 0; list-style: none; font-size: .9rem; }
.finns li { padding: 1px 0; }
.finns li.pts { font-weight: 600; }
.tag { display: inline-block; font-size: .75rem; color: var(--muted); border: 1px solid var(--line); border-radius: 4px; padding: 0 4px; margin-left: 4px; }
.none { color: var(--muted); font-size: .9rem; margin: 6px 0 0; }
.note { color: var(--muted); font-size: .85rem; margin-top: 6px; }
footer { margin-top: 40px; color: var(--muted); font-size: .8rem; }
.tabs { gap: 4px; margin: 18px 0 6px; border-bottom: 2px solid var(--line); overflow-x: auto; }
.tabs button { font: inherit; font-weight: 600; color: var(--muted); background: none; border: 0; border-bottom: 3px solid transparent;
  padding: 8px 14px; margin-bottom: -2px; cursor: pointer; white-space: nowrap; }
.tabs button:hover { color: var(--fg); }
.tabs button[aria-selected="true"] { color: var(--accent); border-bottom-color: var(--accent); }
.tabs button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.panel { padding-top: 4px; }
.js .panel[hidden] { display: none; }
.tabs { display: none; }
.js .tabs { display: flex; }
"""

JS = """
(function () {
  var root = document.documentElement;
  root.classList.add('js');
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.tabs [role=tab]'));
  var panels = tabs.map(function (t) { return document.getElementById(t.getAttribute('aria-controls')); });
  function show(i, updateHash) {
    tabs.forEach(function (t, j) {
      var on = i === j;
      t.setAttribute('aria-selected', on ? 'true' : 'false');
      t.tabIndex = on ? 0 : -1;
      panels[j].hidden = !on;
    });
    if (updateHash) {
      try { history.replaceState(null, '', '#' + panels[i].id); } catch (e) {}
    }
  }
  tabs.forEach(function (t, i) {
    t.addEventListener('click', function () { show(i, true); });
    t.addEventListener('keydown', function (e) {
      var n = null;
      if (e.key === 'ArrowRight') n = (i + 1) % tabs.length;
      if (e.key === 'ArrowLeft') n = (i - 1 + tabs.length) % tabs.length;
      if (n !== null) { show(n, true); tabs[n].focus(); e.preventDefault(); }
    });
  });
  var start = 0;
  var h = location.hash.replace('#', '');
  panels.forEach(function (p, i) { if (p.id === h) start = i; });
  show(start, false);
})();
"""


def fmt_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{WEEKDAYS[d.weekday()]} {d.day}.{d.month}."


def fmt_time(hhmm: str) -> str:
    h, m = hhmm.split(":")
    return f"klo {int(h)}.{m}"


def team_label(t: dict) -> str:
    name = f' <span class="time">{escape(t["name"])}</span>' if t.get("name") else ""
    return f'{escape(t["abbrev"])}{name}'


def skater_table(rows: list[dict]) -> str:
    head = "<tr><th>Pelaaja</th><th class='l'>Joukkue</th><th class='l'>Pos</th><th>O</th><th>M</th><th>S</th><th>P</th><th>+/-</th><th>Min</th><th>Laukaukset</th><th>Aika/ottelu</th></tr>"
    body = "".join(
        f"<tr><td>{escape(r['name'])}</td><td class='l'>{escape(r['team'])}</td><td class='l'>{escape(r['pos'])}</td>"
        f"<td>{r['gp']}</td><td>{r['g']}</td><td>{r['a']}</td><td class='pts'>{r['p']}</td>"
        f"<td>{r['pm']:+d}</td><td>{r['pim']}</td><td>{r['sog']}</td><td>{r['toi']:.1f}</td></tr>"
        for r in rows
    )
    return f"<div class='scroll'><table>{head}{body}</table></div>"


def goalie_table(rows: list[dict]) -> str:
    head = "<tr><th>Pelaaja</th><th class='l'>Joukkue</th><th>O</th><th>V</th><th>H</th><th>JH</th><th>Torjunta-%</th><th>Päästetyt/ottelu</th></tr>"

    def num(v, fmt):
        return fmt.format(v) if v is not None else "-"

    body = "".join(
        f"<tr><td>{escape(r['name'])}</td><td class='l'>{escape(r['team'])}</td><td>{r['gp']}</td>"
        f"<td>{r['w']}</td><td>{r['l']}</td><td>{num(r['otl'], '{}')}</td>"
        f"<td class='pts'>{num(r['svpct'], '{:.3f}')}</td><td>{num(r['gaa'], '{:.2f}')}</td></tr>"
        for r in rows
    )
    return f"<div class='scroll'><table>{head}{body}</table></div>"


def result_game(g: dict) -> str:
    away, home = g["away"], g["home"]
    outcome = f' <span class="tag">{escape(g["outcome"])}</span>' if g.get("outcome") else ""
    score = f'{away["score"]}&ndash;{home["score"]}'
    head = (
        f'<div class="head"><span>{team_label(away)} &ndash; {team_label(home)} '
        f'<strong>{score}</strong>{outcome}</span><span class="time">{fmt_time(g["start_fi"])}</span></div>'
    )
    items = []
    for s in g["finns"]["skaters"]:
        cls = ' class="pts"' if s["p"] > 0 else ""
        items.append(
            f"<li{cls}>{escape(s['name'])} ({escape(s['team'])}): {s['g']}+{s['a']}={s['p']}, "
            f"{s['pm']:+d}, {escape(s['toi'])}</li>"
        )
    for k in g["finns"]["goalies"]:
        pct = f"{k['svpct']:.3f}" if k.get("svpct") is not None else "-"
        dec = f" ({escape(k['decision'])})" if k.get("decision") else ""
        items.append(
            f"<li>{escape(k['name'])} ({escape(k['team'])}), maalivahti{dec}: "
            f"torjunnat {k['saves']}/{k['shots']}, {pct}, päästetyt {k['ga']}</li>"
        )
    if g.get("box_missing"):
        body = '<p class="none">Ottelutietoja ei saatu haettua.</p>'
    elif items:
        body = f'<ul class="finns">{"".join(items)}</ul>'
    else:
        body = '<p class="none">Ei suomalaisia pelaajia ottelussa.</p>'
    return f'<div class="game">{head}{body}</div>'


def upcoming_game(g: dict) -> str:
    away, home = g["away"], g["home"]
    head = (
        f'<div class="head"><span>{team_label(away)} &ndash; {team_label(home)}</span>'
        f'<span class="time">{fmt_time(g["time_fi"])}</span></div>'
    )
    if g["finns"]:
        names = ", ".join(
            f"{escape(p['name'])} <span class='tag'>{escape(p['team'])}</span>" for p in g["finns"]
        )
        body = f'<p class="none">Suomalaiset: {names}</p>'
    else:
        body = '<p class="none">Ei suomalaisia kokoonpanossa.</p>'
    return f'<div class="game">{head}{body}</div>'


def build(data: dict) -> str:
    generated = datetime.fromisoformat(data["generated_at"]).astimezone(HELSINKI)
    season = f"{str(data['season'])[:4]}&ndash;{str(data['season'])[6:]}"

    results_html = ""
    for day in data["results"]:
        games = "".join(result_game(g) for g in day["games"]) or '<p class="none">Ei otteluita.</p>'
        results_html += f"<h3>{fmt_date(day['date'])}</h3>{games}"
    if not data["results"]:
        results_html = '<p class="none">Ei otteluita.</p>'

    upcoming_html = ""
    by_day: dict[str, list[dict]] = {}
    for g in data["upcoming"]:
        by_day.setdefault(g["date_fi"], []).append(g)
    for day in sorted(by_day):
        upcoming_html += f"<h3>{fmt_date(day)}</h3>" + "".join(upcoming_game(g) for g in by_day[day])
    if not upcoming_html:
        upcoming_html = '<p class="none">Ei otteluita tällä aikavälillä.</p>'

    return f"""<!doctype html>
<html lang="fi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Suomalaiset NHL:ssä</title>
<style>{CSS}</style>
</head>
<body>
<main>
<h1>Suomalaiset NHL:ssä</h1>
<p class="sub">Kausi {season}, runkosarja. Päivitetty {generated.day}.{generated.month}.{generated.year} klo {generated.hour}.{generated.minute:02d} (Suomen aikaa).</p>

<div class="tabs" role="tablist" aria-label="Näkymät">
<button role="tab" id="tab-tulokset" aria-controls="tulokset" aria-selected="true">Tulokset</button>
<button role="tab" id="tab-tulossa" aria-controls="tulossa" aria-selected="false" tabindex="-1">Tulossa</button>
<button role="tab" id="tab-tilastot" aria-controls="tilastot" aria-selected="false" tabindex="-1">Tilastot</button>
</div>

<section class="panel" id="tulokset" role="tabpanel" aria-labelledby="tab-tulokset">
<h2>Tulokset</h2>
<p class="sub">Kaksi edellistä NHL-pelipäivää. Ajat Suomen aikaa.</p>
{results_html}
</section>

<section class="panel" id="tulossa" role="tabpanel" aria-labelledby="tab-tulossa">
<h2>Tulossa</h2>
<p class="sub">Seuraavan 7 päivän ottelut, jotka alkavat Suomen aikaa klo 18&ndash;23. Suomalaiset on poimittu joukkueen nykyisestä kokoonpanosta (syntymämaa Suomi), eikä pelaajien pelaamista ole vahvistettu.</p>
{upcoming_html}
</section>

<section class="panel" id="tilastot" role="tabpanel" aria-labelledby="tab-tilastot">
<h2>Kausitilastot</h2>
<h3>Kenttäpelaajat ({len(data['skaters'])})</h3>
{skater_table(data['skaters'])}
<h3>Maalivahdit ({len(data['goalies'])})</h3>
{goalie_table(data['goalies'])}
</section>

<footer>Data: NHL:n epävirallinen rajapinta (api-web.nhle.com). Sivu päivittyy automaattisesti GitHub Actionsilla.</footer>
</main>
<script>{JS}</script>
</body>
</html>
"""


def main() -> int:
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(build(data), encoding="utf-8")
    print(f"Kirjoitettu {OUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

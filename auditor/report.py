"""Static HTML report (SPEC §6): overall score, per-layer and per-page scores,
heatmaps, side-by-side screenshots and the ranked gap list."""
from pathlib import Path

from jinja2 import Template

TEMPLATE = Template(r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fidelity audit — {{ s.clone_url }}</title>
<style>
:root{--ink:#17202b;--mute:#5d6b7a;--line:#dde3ea;--bg:#f7f8fa;--hi:#c0392b;--med:#d68910;--lo:#2e86c1;--good:#1e8449}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
.wrap{max-width:1180px;margin:0 auto;padding:32px 24px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.sub{color:var(--mute);font-size:14px}
.top{display:grid;grid-template-columns:220px 1fr;gap:24px;margin-top:24px;align-items:stretch}
.big{background:#fff;border:1px solid var(--line);border-radius:12px;padding:20px;text-align:center}
.big .n{font-size:56px;font-weight:700;line-height:1.1}.big .l{color:var(--mute);font-size:13px}
.layers{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 22px}
.bar{display:grid;grid-template-columns:110px 1fr 60px 70px;gap:12px;align-items:center;margin:8px 0;font-size:14px}
.track{height:12px;background:#edf0f4;border-radius:6px;overflow:hidden}.fill{height:100%;border-radius:6px}
.w{color:var(--mute);font-size:12px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden;font-size:14px}
th,td{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#f0f3f6;font-weight:600}
td.num{font-variant-numeric:tabular-nums}
.chip{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;font-weight:600;color:#fff}
.high{background:var(--hi)}.medium{background:var(--med)}.low{background:var(--lo)}
.gap{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}
.gap .meta{font-size:12px;color:var(--mute);margin-bottom:4px}.gap .d{font-weight:500}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}
.pair figure{margin:0}.pair figcaption{font-size:12px;color:var(--mute)}
.pair img{max-width:100%;max-height:260px;border:1px solid var(--line);border-radius:6px;background:#fff;display:block}
details summary{cursor:pointer;color:var(--mute);font-size:13px;margin-top:6px}
.heat img{max-width:100%;border:1px solid var(--line);border-radius:6px}
.counts span{margin-right:14px}
@media(max-width:720px){.top{grid-template-columns:1fr}.pair{grid-template-columns:1fr}.bar{grid-template-columns:80px 1fr 50px}}
</style></head><body><div class="wrap">
<h1>Clone fidelity audit</h1>
<div class="sub">Scoring {{ s.scoring }}{{ ' · QUICK MODE (desktop only, no behaviour; not comparable with full audits)' if s.quick else '' }} &nbsp;·&nbsp; Real: <code>{{ s.real_url }}</code> &nbsp;·&nbsp; Clone: <code>{{ s.clone_url }}</code> &nbsp;·&nbsp; {{ s.pages|length }} pages, {{ s.flows|length }} flows, {{ s.seconds }} s</div>
<div class="top">
  <div class="big"><div class="n" style="color:{{ col(s.overall) }}">{{ '%.2f'|format(s.overall) }}</div><div class="l">audit-coverage summary (0–1)</div>
   <div class="l" style="font-size:11px;margin-top:6px;max-width:190px;margin-left:auto;margin-right:auto">A summary of how many differences the audit found, weighted by severity. It is not a prediction of agent performance: read the tickets for the tasks you care about.</div>
   <div class="counts" style="margin-top:12px;font-size:13px"><span><span class="chip high">{{ s.gap_counts.high }}</span> high</span><span><span class="chip medium">{{ s.gap_counts.medium }}</span> med</span><span><span class="chip low">{{ s.gap_counts.low }}</span> low</span></div></div>
  <div class="layers">
  {% for k in ['visual','elements','behavior','flows'] %}
   <div class="bar"><div>{{ k|capitalize }}</div><div class="track"><div class="fill" style="width:{{ (s.layers[k]*100)|round(1) }}%;background:{{ col(s.layers[k]) }}"></div></div>
   <div class="num">{{ '%.3f'|format(s.layers[k]) }}</div><div class="w">weight {{ s.weights[k] }}</div></div>
  {% endfor %}
  </div>
</div>

<h2>Flows</h2>
<table><tr><th>Flow</th><th>Score</th><th>Result</th></tr>
{% for f in s.flows %}<tr><td>{{ f.name }}</td><td class="num">{{ '%.2f'|format(f.score) if f.score is not none else '—' }}</td>
<td>{% if f.invalid %}<b>Invalid flow:</b> {{ f.detail }}{% elif f.diverged_at %}Diverges at step {{ f.diverged_at }}: {{ f.detail }}{% else %}Completes identically on both sites{% endif %}</td></tr>{% endfor %}
</table>

<h2>Pages</h2>
<table><tr><th>Page</th><th>Visual</th><th>Elements</th><th>Behaviour</th><th>Gaps</th></tr>
{% for p in s.pages %}<tr><td><code>{{ p.url }}</code></td>
<td class="num" style="color:{{ col(p.visual) }}">{{ '%.3f'|format(p.visual) }}</td>
<td class="num" style="color:{{ col(p.elements) }}">{{ '%.3f'|format(p.elements) }}</td>
<td class="num" style="color:{{ col(p.behavior) }}">{{ '%.3f'|format(p.behavior) }}</td>
<td class="num">{{ gaps_on(p.page) }}</td></tr>{% endfor %}
</table>

<h2>Gaps ({{ gaps|length }}), ranked</h2>
{% for g in gaps %}
<div class="gap"><div class="meta"><span class="chip {{ g.severity }}">{{ g.severity }}</span> &nbsp;{{ g.id }} · {{ g.layer }} · <code>{{ g.page }}</code>{% if g.also_on %} · also on {{ g.also_on|join(', ') }}{% endif %}</div>
<div class="d">{{ g.description }}</div>
{% if g.real_screenshot %}<details {% if loop.index <= 6 %}open{% endif %}><summary>Screenshots</summary><div class="pair">
<figure><img loading="lazy" src="{{ g.real_screenshot }}" alt="real"><figcaption>Real site</figcaption></figure>
<figure><img loading="lazy" src="{{ g.clone_screenshot }}" alt="clone"><figcaption>Clone</figcaption></figure></div></details>{% endif %}
</div>
{% else %}<p>No gaps found.</p>{% endfor %}

<h2>Visual heatmaps</h2>
<p class="sub">Red = pixels that differ after masking dynamic content (magenta).</p>
{% for p in s.pages %}<details class="heat"><summary><code>{{ p.url }}</code> — visual {{ '%.3f'|format(p.visual) }}</summary>
<div class="pair"><figure><img loading="lazy" src="{{ p.real_shot }}"><figcaption>Real (desktop)</figcaption></figure>
<figure><img loading="lazy" src="{{ p.heatmaps[0] }}"><figcaption>Diff heatmap (desktop)</figcaption></figure></div></details>{% endfor %}
</div></body></html>""")


def _col(v):
    return "#1e8449" if v >= 0.9 else ("#d68910" if v >= 0.7 else "#c0392b")


def write_report(out: Path, summary, gaps, cfg):
    def gaps_on(page):
        return sum(1 for g in gaps if g["page"] == page or page in g.get("also_on", []))
    html = TEMPLATE.render(s=summary, gaps=gaps, col=_col, gaps_on=gaps_on)
    (out / "report.html").write_text(html)

"""Generic Flask site rendered from the site.json next to it (written by gen/site_gen.py).

The real site and its clone both run a copy of this file; they differ only in site.json, where the clone's spec
carries the planted defects (see gen/site_gen.py). Dynamic content: random prices on every request and a clock.
Run:  python app.py --port 8001     (--defects is accepted and ignored, for refapp/serve.py compatibility)
"""
import argparse
import json
import random
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template_string, request

S = json.loads(Path(__file__).with_name("site.json").read_text())
PAGES = {p["path"]: p for p in S["pages"]}
ITEMS = {str(it["id"]): it for it in S["items"]}
app = Flask(__name__)

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ P.h1 }} · {{ S.name }}</title>
<style>
  * { box-sizing:border-box; }
  body { margin:0; font-family:{{ S.font|safe }}; color:#1d2733; background:{{ S.colors.bg }}; }
  header { background:{{ S.colors.header }}; color:#fff; display:flex; align-items:center; justify-content:space-between; padding:14px 28px; flex-wrap:wrap; gap:8px; }
  header .logo { color:#fff; font-weight:bold; font-size:22px; text-decoration:none; }
  nav a { color:#fff; margin-left:18px; text-decoration:none; font-size:15px; }
  .dynamic { display:inline-block; width:180px; font-size:13px; white-space:nowrap; }
  main { max-width:1000px; margin:0 auto; padding:28px 22px 48px; }
  h1 { font-size:30px; margin:0 0 18px; }
  .hero { background:{{ S.colors.accent }}; color:#fff; padding:34px 26px; border-radius:10px; margin-bottom:24px; }
  .hero h1 { color:#fff; }
  label { display:block; font-size:13px; font-weight:bold; margin-bottom:5px; }
  input, select { width:100%; padding:10px; border:1px solid #9aa9b8; border-radius:6px; font-size:15px; font-family:inherit; }
  .btn { background:{{ S.colors.button }}; color:#fff; border:0; padding:11px 22px; border-radius:6px; font-size:15px; cursor:pointer; text-decoration:none; display:inline-block; font-family:inherit; }
  .btn.light { background:#fff; color:{{ S.colors.button }}; border:1px solid {{ S.colors.button }}; }
  .row { display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:14px; align-items:end; margin-bottom:18px; }
  .cards { display:grid; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:16px; margin-bottom:22px; }
  .card { background:#fff; border:1px solid #d5dde6; border-radius:10px; padding:18px; }
  .card h2 { margin:0 0 8px; font-size:19px; }
  .price { display:block; width:200px; height:30px; white-space:nowrap; overflow:hidden; font-size:22px; font-weight:bold; margin:8px 0; }
  .summary { background:#fff; border:1px solid #d5dde6; border-radius:10px; padding:18px; margin-bottom:18px; }
  footer { border-top:1px solid #d5dde6; background:#fff; padding:20px 28px; display:flex; gap:22px; flex-wrap:wrap; font-size:14px; }
  footer a { color:{{ S.colors.button }}; }
  dialog { border:0; border-radius:10px; padding:24px; max-width:420px; box-shadow:0 10px 40px rgba(0,0,0,.3); }
  {{ S.css.get(P.path, '')|safe }}
</style></head>
<body>
<header>
  <a class="logo" href="/">{{ S.name }}</a>
  <nav>{% for n in S.nav %}<a href="{{ n.href }}">{{ n.label }}</a>{% endfor %}</nav>
  <span class="dynamic">Updated {{ clock }}</span>
</header>
<main>
{% if P.kind == 'home' %}
  <section class="hero">
    <h1>{{ P.h1 }}</h1>
    <p>{{ P.tagline }}</p>
    <form class="row" method="get" action="{{ S.list_path }}">
      <div><label for="q">{{ S.search_label }}</label><input id="q" name="q" required></div>
      <div><button class="btn" type="submit">{{ S.search_button }}</button></div>
    </form>
  </section>
  <h2>{{ S.section_heading }}</h2>
  <div class="cards">{% for it in S['items'][:3] %}
    <div class="card"><h2>{{ it.name }}</h2><p>{{ it.desc }}</p><span class="price">{{ money() }}</span></div>{% endfor %}
  </div>
  <p><button class="btn light" type="button" id="nl-btn"{% if S.newsletter_works %} onclick="document.getElementById('nl').showModal()"{% endif %}>{{ S.newsletter_label }}</button></p>
  <dialog id="nl" aria-label="Newsletter sign-up"><h2>Newsletter sign-up</h2><p>{{ S.newsletter_text }}</p>
    <button class="btn" type="button" onclick="this.closest('dialog').close()">Close</button></dialog>
{% elif P.kind == 'list' %}
  <h1>{{ P.h1 }}</h1>
  {% if q %}<p>Showing results for “{{ q }}”</p>{% endif %}
  <div class="cards">{% for it in S['items'] %}
    <div class="card"><h2>{{ it.name }}</h2><p>{{ it.desc }}</p><span class="price">{{ money() }}</span>
      <a class="btn" href="{{ S.item_href }}?id={{ it.id }}">{{ S.item_link }}</a></div>{% endfor %}
  </div>
{% elif P.kind == 'detail' %}
  <h1>{{ item.name }}</h1>
  <div class="summary"><p>{{ item.desc }}</p><span class="price">{{ money() }}</span></div>
  <p><button class="btn light" type="button" id="dlg-btn"{% if S.dialog_works %} onclick="document.getElementById('dlg').showModal()"{% endif %}>{{ S.dialog_button }}</button></p>
  <dialog id="dlg" aria-label="{{ S.dialog_button }}"><h2>{{ S.dialog_button }}</h2><p>{{ S.dialog_text }}</p>
    <button class="btn" type="button" onclick="this.closest('dialog').close()">Close</button></dialog>
  <p><a class="btn" href="{{ S.form_path }}?item={{ item.id }}">{{ S.detail_cta }}</a></p>
{% elif P.kind == 'form' %}
  <h1>{{ P.h1 }}</h1>
  <form method="get" action="{{ S.form_action }}">
    <input type="hidden" name="item" value="{{ item.id }}">
    <div class="row">{% for f in S.fields %}
      <div><label for="f_{{ f.name }}">{{ f.label }}</label><input id="f_{{ f.name }}" name="{{ f.name }}" type="{{ f.type }}"{% if f.required %} required{% endif %}></div>{% endfor %}
      <div><label for="f_opt">{{ S.select.label }}</label><select id="f_opt" name="opt">{% for o in S.select.options %}<option>{{ o }}</option>{% endfor %}</select></div>
    </div>
    <p><button class="btn" type="submit">{{ S.submit_label }}</button></p>
  </form>
{% elif P.kind == 'review' %}
  <h1>{{ P.h1 }}</h1>
  <div class="summary">{% for f in S.summary_fields %}<p><b>{{ f.label }}:</b> {{ request.args.get(f.name, '') }}</p>{% endfor %}
    <p>Total</p><span class="price">{{ money() }}</span></div>
  {# The final action never does anything: tasks and flows stop before it. #}
  <p><button class="btn" type="button">{{ S.final_label }}</button> <a href="/">Cancel</a></p>
{% elif P.kind == 'info' %}
  <h1>{{ P.h1 }}</h1>
  {% for para in P.body %}<p>{{ para }}</p>{% endfor %}
  <p><a href="/">Back to home</a></p>
{% else %}
  <h1>Page not found</h1><p><a href="/">Back to home</a></p>
{% endif %}
</main>
<footer>{% for f in S.footer %}<a href="{{ f.href }}">{{ f.label }}</a>{% endfor %}<span>© {{ S.name }}</span></footer>
</body></html>
"""


def money():
    lo, hi, cents = S["money"]
    return f"${random.uniform(lo, hi):,.2f}" if cents else f"${random.randint(lo, hi):,}"


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def page(path):
    P = PAGES.get("/" + path, {"kind": "notfound", "path": "/" + path, "h1": "Page not found"})
    item = ITEMS.get(request.args.get("id") or request.args.get("item") or "", S["items"][0])
    html = render_template_string(TEMPLATE, S=S, P=P, item=item, q=request.args.get("q", ""), money=money,
                                  clock=datetime.now().strftime("%I:%M:%S %p"))
    return html, 404 if P["kind"] == "notfound" else 200


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--defects", default="")
    app.run(host="127.0.0.1", port=ap.parse_args().port, debug=False, use_reloader=False)

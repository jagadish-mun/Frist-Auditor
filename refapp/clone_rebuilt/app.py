"""Harbor Air, rebuilt from screenshots (SPEC §10 "agent-built clone").

Written only from what a user can observe (tools/observe.py output: screenshots, visible text and
boxes, link targets, form labels, URLs reached by submitting forms). refapp/app.py was NOT read.
Colours were sampled from screenshot pixels; sizes were estimated from text/element boxes.
Class names `price` / `dynamic` come from the audit config's mask selectors (part of the audit contract).

    python refapp/clone_rebuilt/app.py --port 8003 [--defects a,b]

Planted defects for recall-on-realistic-noise: see REBUILT_DEFECTS in refapp/defects.py.
"""
import argparse
import random
from datetime import datetime, timedelta

from flask import Flask, render_template_string, request

app = Flask(__name__)
D = set()

BASE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Harbor Air</title>
<style>
:root{--navy:#0b2545;--ink:#1b2a3a;--blue:#13315c;--line:#d6e0ea;--field:#9fb3c8}
*{box-sizing:border-box}
body{margin:0;background:#f4f7fb;color:var(--ink);font-family:Helvetica,Arial,sans-serif;font-size:16px;line-height:normal}
.top{background:var(--navy);height:54px;padding:0 32px;display:flex;align-items:center;justify-content:space-between}
.brand{color:#fff;font-weight:700;font-size:22px;text-decoration:none}
.links a{color:#fff;text-decoration:none;margin-left:25px;font-size:15px}
main{max-width:992px;margin:0 auto;padding:28px 0 48px}
h1{font-size:30px;line-height:34px;margin:0 0 18px}
.btn{display:inline-block;background:var(--navy);color:#fff;border:1px solid var(--navy);border-radius:6px;padding:10px 21px;
     font:700 14px Helvetica,Arial,sans-serif;text-decoration:none;cursor:pointer;line-height:17px}
.btn.ghost{background:#fff;color:var(--navy);font-weight:400;font-size:15px;padding:11px 22px}
.card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:20px}
label{display:block;font-size:13px;font-weight:700;line-height:15px;margin-bottom:5px}
input,select{width:100%;height:39px;border:1px solid var(--field);border-radius:4px;padding:0 10px;font:15px Helvetica,Arial,sans-serif;background:#fff;color:var(--ink)}
select{height:41px}
.price{color:var(--blue);font-weight:700;font-size:24px}
footer{background:#fff;border-top:1px solid var(--line);padding:22px 32px;font-size:14px}
footer a{color:var(--blue);margin-right:22px}
footer .dynamic{color:#5b6b7b;font-size:13px}
dialog{border:0;border-radius:12px;width:420px;padding:24px;box-shadow:0 10px 30px rgba(0,0,0,.2)}
dialog::backdrop{background:rgba(11,37,69,.12)}
dialog h2{font-size:24px;margin:8px 0 14px}
@media (max-width:600px){
  .top{height:80px;flex-wrap:wrap;align-content:flex-start;padding:14px 32px 0}
  .links{width:100%;margin-top:9px}
  .links a{margin-left:25px}
  .links a:first-child{margin-left:20px}
  main{padding:28px 24px 48px}
  footer .dynamic{display:block;margin-top:18px}
}
</style></head><body>
<nav class="top"><a class="brand" href="/">Harbor Air</a>
<div class="links"><a href="/">Book</a><a href="/manage">Manage trips</a><a href="/checkin">{{ 'Online check-in' if 'ho_relabel_checkin_nav' in D else 'Check in' }}</a><a href="/signin">Sign in</a></div></nav>
<main>{% block body %}{% endblock %}</main>
<footer><a href="{{ '/about-us' if 'rb_broken_about' in D else '/about' }}">About us</a>{% if 'ho_missing_help_footer' not in D %}<a href="/help">Help centre</a>{% endif %}<a href="/help/baggage">Baggage info</a>
<span class="dynamic">Updated {{ now }}</span></footer>
</body></html>"""

HOME = """{% extends base %}{% block body %}
<style>
.hero{background:linear-gradient(110deg,#13315c,#1f69a4);border-radius:10px;padding:36px 28px 35px;color:#fff}
.hero h1{color:#fff;margin-bottom:20px}
.sf{display:flex;gap:14px;align-items:flex-end}.sf>div{width:176px}
.sf .btn{background:#f2b705;border-color:#f2b705;color:var(--navy);font-size:15px;padding:10px 21px}
.sale{background:#fff3cd;border:1px solid #f2d27a;border-radius:8px;padding:14px 18px;line-height:17px;margin:22px 0 33px}
h2{font-size:24px;line-height:28px;margin:0 0 20px}
.dest{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.dest .card{padding:39px 20px 33px}
.dest h3{font-size:1.17em;line-height:22px;margin:0 0 18px}.dest p{margin:0}
@media (max-width:600px){.sf{flex-direction:column;align-items:stretch}.sf>div{width:auto}.sf .btn{align-self:flex-start}
  .dest{grid-template-columns:1fr;row-gap:19.5px}}{% if 'ho_promo_tint' in D %}.sale{background:#e3f1fb;border-color:#9cc7e8}{% endif %}
</style>
<section class="hero"><h1>Where to next?</h1>
<form class="sf" action="/results" method="get">
 <div><label for="from">From</label><input id="from" name="from" placeholder="City or airport" required></div>
 <div><label for="to">To</label><input id="to" name="to" placeholder="City or airport" required></div>
 <div><label for="depart">Depart</label><input id="depart" name="depart" placeholder="MM/DD/YYYY"></div>
 <div><label for="pax">Passengers</label><select id="pax" name="pax"><option>1 adult</option><option>2 adults</option>{% if 'rb_pax_option_missing' not in D %}<option>3 adults</option>{% endif %}</select></div>
 {% if 'rb_search_dead' in D %}<button class="btn" type="button">Search</button>{% else %}<button class="btn" type="submit">Search</button>{% endif %}
</form></section>
<div class="sale"><b>Fall sale:</b> fares from ${{ sale }}. Sale ends {{ sale_end }}.</div>
<h2>Popular destinations</h2>
<div class="dest">
 <div class="card"><h3>San Juan</h3><p>Nonstop flights daily to SJU.</p></div>
 <div class="card"><h3>Boston</h3><p>Nonstop flights daily to BOS.</p></div>
 <div class="card"><h3>Orlando</h3><p>Nonstop flights daily to MCO.</p></div>
</div>{% endblock %}"""

RESULTS = """{% extends base %}{% block body %}
<style>
.bar{display:flex;justify-content:space-between;align-items:center;margin:18px 0 16px}
.bar label{margin-bottom:5px}.bar select{width:109px}
.flight{display:flex;align-items:center;justify-content:space-between;margin-bottom:13px;padding:20px 20px}
.flight .info{width:550px}.flight .price{width:300px}
@media (max-width:600px){.flight{flex-wrap:wrap}.flight .info{width:100%;margin-bottom:10px}.flight .price{width:auto}}
</style>
<h1 style="margin:0">Flights from {{ frm }} to {{ to }}</h1>
<div class="bar">{% if 'rb_no_modify' in D %}<span></span>{% else %}<a class="btn ghost" href="/">{{ 'Change search' if 'ho_relabel_modify_search' in D else 'Modify search' }}</a>{% endif %}
<div><label for="sort">Sort by</label><select id="sort"><option>Price</option><option>Departure</option><option>Duration</option></select></div></div>
{% for f in flights %}<div class="card flight"><div class="info"><b>{{ f[0] }}</b> · {{ f[1] }} · Nonstop</div>
<span class="price">${{ f[2] }}</span><a class="btn" href="{{ '/passenger' if 'ho_select_skips_fares' in D else '/fares' }}?flight={{ f[0] }}">Select</a></div>{% endfor %}
{% endblock %}"""

FARES = """{% extends base %}{% block body %}
<style>
.fl{display:flex;align-items:center;gap:6px;margin:0 0 16px}
.fares{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.fares h2{font-size:20px;line-height:23px;margin:0 0 8px}.fares .price{display:block;margin-bottom:18px}.fares p{margin:0 0 15px}
@media (max-width:600px){.fares{grid-template-columns:1fr}}{% if 'ho_move_fare_rules' in D %}#rules{position:relative;left:160px}{% endif %}
</style>
<h1>Choose your fare</h1>
<div class="fl">Flight {{ flight }} · <button class="btn ghost" id="rules" type="button">Fare rules</button></div>
<div class="fares">
{% for name, txt in fares %}<div class="card"><h2>{{ name }}</h2><span class="price">${{ prices[loop.index0] }}</span><p>{{ txt }}</p>
<a class="btn" href="/passenger?flight={{ flight }}&fare={{ name|lower }}">Select fare</a></div>{% endfor %}
</div>
<dialog id="dlg" aria-label="Fare rules"><h2>Fare rules</h2><p>Changes allowed on Core and Extra fares. Basic fares are non-refundable.</p>
<button class="btn" type="button"{% if 'rb_dialog_close_dead' not in D %} onclick="this.closest('dialog').close()"{% endif %}>Close</button></dialog>
<script>document.getElementById('rules').onclick=()=>document.getElementById('dlg').showModal();</script>
{% endblock %}"""

FORM = """{% extends base %}{% block body %}
<style>.row{display:grid;grid-template-columns:repeat({{ fields|length }},1fr);gap:14px;margin-bottom:20px}
@media (max-width:600px){.row{grid-template-columns:1fr}}{% if 'ho_move_find_trip' in D and title == 'Check in' %}form .btn{margin-top:60px}{% endif %}</style>
<h1>{{ title }}</h1>
<form action="{{ action }}" method="get">{% for k, v in hidden %}<input type="hidden" name="{{ k }}" value="{{ v }}">{% endfor %}
<div class="row">{% for id, lab, typ in fields %}<div><label for="{{ id }}">{{ lab }}</label><input id="{{ id }}" name="{{ id }}" type="{{ typ }}" required></div>{% endfor %}</div>
<button class="btn" type="{{ btype or 'submit' }}">{{ submit }}</button></form>{% endblock %}"""

REVIEW = """{% extends base %}{% block body %}
<style>.sum{padding:36px 20px 25px;margin-bottom:20px}.sum p{margin:0 0 15.6px}</style>
<h1>Review and pay</h1>
<div class="card sum"><p><b>Flight:</b> {{ flight }}</p><p><b>Passenger:</b> {{ name }}</p><p><b>Total:</b> ${{ total }}</p></div>
<a class="btn ghost" href="/passenger">Back</a> <button class="btn" type="button">Pay</button>
{% endblock %}"""

TEXT = """{% extends base %}{% block body %}<h1>{{ title }}</h1><p>{{ text }}</p>{% if 'ho_extra_baggage_calc' in D and title == 'Baggage info' %}<p><a class="btn" href="/help">Baggage fee calculator</a></p>{% endif %}{% endblock %}"""

FLIGHTS = [("HA101", "6:05 AM → 10:40 AM"), ("HA215", "11:30 AM → 4:02 PM"), ("HA377", "5:45 PM → 10:21 PM")]
FARES_T = [("Basic", "Personal item only. No changes."), ("Core", "Carry-on bag. Free changes."),
           ("Extra", "Extra legroom. Priority boarding.")]


def render(tpl, **kw):
    end = datetime.now() + timedelta(days=random.randint(7, 21))
    return render_template_string(tpl, base=app.jinja_env.from_string(BASE), D=D,
                                  now=datetime.now().strftime("%I:%M:%S %p"),
                                  sale=random.randint(59, 99), sale_end=f"{end:%b} {end.day}, {end.year}", **kw)


def P():
    return random.randint(99, 420)


@app.route("/")
def home():
    return render(HOME)


@app.route("/results")
def results():
    return render(RESULTS, frm=request.args.get("from", "DCA"), to=request.args.get("to", "SJU"),
                  flights=[(c, t, P()) for c, t in FLIGHTS])


@app.route("/fares")
def fares():
    return render(FARES, flight=request.args.get("flight", "HA101"), fares=FARES_T, prices=sorted(P() for _ in range(3)))


@app.route("/passenger")
def passenger():
    fields = [("first", "First name", "text"), ("last", "Last name", "text"), ("email", "Email", "email")]
    return render(FORM, title="Who's flying?", action="/review", hidden=[("flight", request.args.get("flight", "HA101"))],
                  fields=fields, submit="Continue", btype="button" if "ho_continue_dead" in D else "submit")


@app.route("/review")
def review():
    a = request.args
    return render(REVIEW, flight=a.get("flight", "HA101"), name=f"{a.get('first', '')} {a.get('last', '')}".strip(), total=P())


@app.route("/checkin")
def checkin():
    return render(FORM, title="Check in", action="/checkin/results" if "ho_checkin_wrong_action" in D else "/checkin/result", hidden=[],
                  fields=[("code", "Confirmation code", "text"), ("last", "Last name", "text")],
                  submit="Look up" if "rb_relabel_find" in D else "Find trip")


@app.route("/checkin/result")
def checkin_result():
    return render(TEXT, title="Your trip", text="You are checked in. Boarding pass sent.")


PAGES = {"/manage": ("Manage trips", "Look up a booking to change seats or flights."),
         "/signin": ("Sign in", "Sign in to see your trips and points."),
         "/about": ("About us", "Harbor Air is a fictional airline for testing."),
         "/help": ("Help centre", "Answers to common questions."),
         "/help/baggage": ("Baggage info", "One carry-on and one personal item on Core and Extra fares.")}

for _path, (_t, _x) in PAGES.items():
    app.add_url_rule(_path, _path, (lambda t=_t, x=_x: render(TEXT, title=t, text=x)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8003)
    ap.add_argument("--defects", default="")
    a = ap.parse_args()
    D.update(x for x in a.defects.split(",") if x)
    app.run(port=a.port, debug=False, use_reloader=False)

"""Harbor Air — a small, fictional airline booking site used as the "real site".

Run:  python refapp/app.py --port 8001                      (the real site)
      python refapp/app.py --port 8002 --defects a,b,c      (a clone with planted defects)

The page deliberately contains dynamic content (random prices, a live clock,
a rotating sale date) so the auditor's masking has something real to handle.
"""
import argparse
import random
import time
from datetime import datetime, timedelta

from flask import Flask, abort, render_template, request
from jinja2 import DictLoader

from defects import DEFECTS
from heldout_defects import HELDOUT_DEFECTS

BASE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{% block title %}Harbor Air{% endblock %}</title>
<style>
  * { box-sizing: border-box; }
  body { margin:0; font-family: Arial, Helvetica, sans-serif; color:#1b2a3a; background:#f4f7fb; }
  {% if 'font_change' in D and page == '/review' %} body { font-family: Georgia, 'Times New Roman', serif; } {% endif %}
  header { background:#0b2545; color:#fff; display:flex; align-items:center; justify-content:space-between; padding:14px 32px; flex-wrap:wrap; gap:8px; }
  header .logo { font-weight:bold; font-size:22px; color:#fff; text-decoration:none; }
  nav a { color:#dbe7f5; margin-left:20px; text-decoration:none; font-size:15px; }
  main { max-width:1040px; margin:0 auto; padding:28px 24px 48px; }
  h1 { font-size:30px; margin:0 0 18px; }
  .hero { background:linear-gradient(120deg,#13315c,#1f6aa5); color:#fff; padding:{{ '84px' if 'layout_shift_hero' in D else '36px' }} 28px 36px; border-radius:10px; }
  .hero h1 { color:#fff; }
  form.search { display:grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr)); gap:14px; align-items:end; }
  label { display:block; font-size:13px; font-weight:bold; margin-bottom:5px; }
  input, select { width:100%; padding:10px; border:1px solid #9fb3c8; border-radius:6px; font-size:15px; }
  .btn { background:{{ '#e8730c' if 'button_color' in D and page == '/' else '#0b2545' }}; color:#fff; border:0; padding:11px 22px; border-radius:6px; font-size:15px; cursor:pointer; text-decoration:none; display:inline-block; }
  .hero .btn { background:{{ '#e8730c' if 'button_color' in D else '#f2b705' }}; color:#0b2545; font-weight:bold; }
  .btn.secondary { background:#fff; color:#0b2545; border:1px solid #0b2545; }
  .promo { margin-top:22px; background:#fff3cd; border:1px solid #f2d27a; padding:14px 18px; border-radius:8px; }
  .cards { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px,1fr)); gap:18px; }
  .card { background:#fff; border:1px solid #d6e0ea; border-radius:10px; padding:20px; }
  .card h2 { margin:0 0 8px; font-size:20px; }
  .price { font-size:24px; font-weight:bold; color:#13315c; margin:10px 0; }
  .flight { display:flex; justify-content:space-between; align-items:center; background:#fff; border:1px solid #d6e0ea; border-radius:10px; padding:16px 20px; margin-bottom:12px; gap:12px; flex-wrap:wrap; }
  .toolbar { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; gap:12px; flex-wrap:wrap; }
  .toolbar select { width:auto; }
  footer { border-top:1px solid #d6e0ea; padding:22px 32px; font-size:14px; display:flex; gap:22px; flex-wrap:wrap; background:#fff; }
  footer a { color:#13315c; }
  .dynamic { color:#5b6b7b; font-size:13px; }
  dialog { border:0; border-radius:10px; padding:24px; max-width:420px; box-shadow:0 10px 40px rgba(0,0,0,.3); }
  .chat { position:fixed; right:20px; bottom:20px; background:#1f6aa5; color:#fff; border:0; border-radius:24px; padding:12px 18px; }
  .summary { background:#fff; border:1px solid #d6e0ea; border-radius:10px; padding:20px; margin-bottom:20px; }
  .formgrid { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px,1fr)); gap:14px; margin-bottom:20px; }
  {% if 'subtle_drift' in D %} header { padding:15px 30px; } h1 { font-size:31px; } .card { border-radius:8px; padding:21px; } .btn { padding:12px 22px; } footer { padding:20px 32px; } body { color:#1d2c3c; } {% endif %}{% if 'ho_move_fare_rules' in D %} #rules-btn { position:relative; left:160px; } {% endif %}{% if 'ho_move_find_trip' in D and page == '/checkin' %} main form .btn { margin-top:60px; } {% endif %}{% if 'ho_promo_tint' in D %} .promo { background:#e3f1fb; border-color:#9cc7e8; } {% endif %}
</style></head>
<body>
<header>
  <a class="logo" href="/">Harbor Air</a>
  <nav aria-label="Main">
    <a href="/">Book</a>
    {% if 'remove_nav_manage' not in D %}<a href="/manage">Manage trips</a>{% endif %}
    <a href="/checkin">{{ 'Online check-in' if 'ho_relabel_checkin_nav' in D else 'Check in' }}</a>
    <a href="{{ '/' if 'signin_goes_home' in D else '/signin' }}">Sign in</a>
  </nav>
</header>
<main>{% block body %}{% endblock %}</main>
<footer>
  <a href="/about">About us</a>
  {% if 'ho_missing_help_footer' not in D %}<a href="/help">Help centre</a>{% endif %}
  <a href="{{ '/help/bagage' if 'broken_baggage_link' in D else '/help/baggage' }}">Baggage info</a>
  <span class="dynamic">Updated {{ clock }}</span>
</footer>
{% if 'extra_chat_widget' in D and page == '/' %}<button class="chat" type="button">Chat with us</button>{% endif %}
</body></html>"""

HOME = r"""{% extends "base" %}{% block body %}
<section class="hero">
  <h1>Where to next?</h1>
  <form class="search" action="{{ '/result' if 'search_wrong_route' in D else '/results' }}" method="get">
    <div><label for="from">From</label><input id="from" name="from" placeholder="City or airport" required></div>
    <div><label for="to">To</label><input id="to" name="to" placeholder="City or airport" required></div>
    <div><label for="depart">Depart</label><input id="depart" name="depart" placeholder="MM/DD/YYYY"></div>
    <div><label for="pax">Passengers</label><select id="pax" name="pax"><option>1 adult</option><option>2 adults</option><option>3 adults</option></select></div>
    <div><button class="btn" type="submit">Search</button></div>
  </form>
</section>
<div class="promo"><strong>Fall sale:</strong> fares from <span class="price-inline">${{ promo_price }}</span>. Sale ends {{ sale_end }}.</div>
<h2 style="margin-top:32px">Popular destinations</h2>
<div class="cards">
  {% for city, code in [('San Juan','SJU'),('Boston','BOS'),('Orlando','MCO')] %}
  <div class="card"><h3>{{ city }}</h3><p>Nonstop flights daily to {{ code }}.</p></div>
  {% endfor %}
</div>
{% endblock %}"""

RESULTS = r"""{% extends "base" %}{% block body %}
<h1>Flights from {{ frm }} to {{ to }}</h1>
<div class="toolbar">
  <a href="/" class="btn secondary">{{ 'Change search' if 'ho_relabel_modify_search' in D else 'Modify search' }}</a>
  {% if 'results_sort_missing' not in D %}<div><label for="sort">Sort by</label><select id="sort"><option>Price</option><option>Departure</option><option>Duration</option></select></div>{% endif %}
</div>
{% for f in flights %}
<div class="flight">
  <div><strong>{{ f.num }}</strong> &middot; {{ f.dep }} → {{ f.arr }} &middot; Nonstop</div>
  <div class="price">${{ f.price }}</div>
  <a class="btn" href="{{ '/passenger' if 'ho_select_skips_fares' in D else '/fares' }}?flight={{ f.num }}">Select</a>
</div>
{% endfor %}
{% endblock %}"""

FARES = r"""{% extends "base" %}{% block body %}
<h1>Choose your fare</h1>
<p>Flight {{ flight }} &middot; <button class="btn secondary" type="button" id="rules-btn">Fare rules</button></p>
<div class="cards">
  {% for name, perks in fares %}
  <div class="card"><h2>{{ name }}</h2><div class="price">${{ prices[loop.index0] }}</div><p>{{ perks }}</p>
    <a class="btn" href="/passenger?flight={{ flight }}&fare={{ name|lower }}">Select fare</a></div>
  {% endfor %}
</div>
<dialog id="rules" aria-label="Fare rules"><h2>Fare rules</h2><p>Changes allowed on Core and Extra fares. Basic fares are non-refundable.</p>
  <button class="btn" type="button" id="close-rules">Close</button></dialog>
<script>
  {% if 'fare_rules_noop' not in D %}document.getElementById('rules-btn').onclick = () => document.getElementById('rules').showModal();{% endif %}
  document.getElementById('close-rules').onclick = () => document.getElementById('rules').close();
</script>
{% endblock %}"""

PASSENGER = r"""{% extends "base" %}{% block body %}
<h1>Who's flying?</h1>
<form action="/review" method="get">
  <input type="hidden" name="flight" value="{{ request.args.get('flight','') }}">
  <div class="formgrid">
    <div><label for="first">First name</label><input id="first" name="first" required></div>
    <div><label for="last">Last name</label><input id="last" name="last" required></div>
    {% if 'missing_email' not in D %}<div><label for="email">Email</label><input id="email" name="email" type="email" required></div>{% endif %}
  </div>
  <button class="btn" type="{{ 'button' if 'ho_continue_dead' in D else 'submit' }}">{{ 'Next' if 'rename_continue' in D else 'Continue' }}</button>
</form>
{% endblock %}"""

REVIEW = r"""{% extends "base" %}{% block body %}
<h1>Review and pay</h1>
<div class="summary"><p><strong>Flight:</strong> {{ request.args.get('flight','HA101') }}</p>
<p><strong>Passenger:</strong> {{ request.args.get('first','') }} {{ request.args.get('last','') }}</p>
<p><strong>Total:</strong> <span class="price-inline">${{ promo_price + 120 }}</span></p></div>
<a href="/passenger" class="btn secondary">Back</a>
<button class="btn" type="button" onclick="alert('payment')">Pay</button>
{% endblock %}"""

CHECKIN = r"""{% extends "base" %}{% block body %}
<h1>Check in</h1>
<form action="{{ '/checkin/results' if 'ho_checkin_wrong_action' in D else '/checkin/result' }}" method="get"><div class="formgrid">
  <div><label for="code">{{ 'Booking reference' if 'checkin_label' in D else 'Confirmation code' }}</label><input id="code" name="code" required></div>
  <div><label for="clast">Last name</label><input id="clast" name="last" required></div>
</div><button class="btn" type="submit">Find trip</button></form>
{% endblock %}"""

SIMPLE = r"""{% extends "base" %}{% block body %}<h1>{{ heading }}</h1><p>{{ text }}</p>{% if 'ho_extra_baggage_calc' in D and page == '/help/baggage' %}<p><a class="btn" href="/help">Baggage fee calculator</a></p>{% endif %}{% endblock %}"""

app = Flask(__name__)
app.jinja_loader = DictLoader({
    "base": BASE, "home": HOME, "results": RESULTS, "fares": FARES,
    "passenger": PASSENGER, "review": REVIEW, "checkin": CHECKIN, "simple": SIMPLE,
})
ACTIVE = set()


def ctx(page, **kw):
    now = datetime.now()
    return dict(
        D=ACTIVE, page=page, request=request,
        clock=now.strftime("%I:%M:%S %p"),
        promo_price=random.randint(39, 99),
        sale_end=(now + timedelta(days=random.randint(3, 20))).strftime("%b %d, %Y"),
        **kw,
    )


@app.route("/")
def home():
    return render_template("home", **ctx("/"))


@app.route("/results")
def results():
    frm, to = request.args.get("from", "DCA").upper(), request.args.get("to", "SJU").upper()
    flights = [dict(num=n, dep=d, arr=a, price=random.randint(89, 420)) for n, d, a in
               [("HA101", "6:05 AM", "10:40 AM"), ("HA215", "11:30 AM", "4:02 PM"), ("HA377", "5:45 PM", "10:21 PM")]]
    return render_template("results", **ctx("/results", frm=frm, to=to, flights=flights))


@app.route("/fares")
def fares():
    core = "Main" if "rename_fare_core" in ACTIVE else "Core"
    fares = [("Basic", "Personal item only. No changes."), (core, "Carry-on bag. Free changes."), ("Extra", "Extra legroom. Priority boarding.")]
    prices = sorted(random.sample(range(99, 480), 3))
    return render_template("fares", **ctx("/fares", flight=request.args.get("flight", "HA101"), fares=fares, prices=prices))


@app.route("/passenger")
def passenger():
    return render_template("passenger", **ctx("/passenger"))


@app.route("/review")
def review():
    return render_template("review", **ctx("/review"))


@app.route("/checkin")
def checkin():
    return render_template("checkin", **ctx("/checkin"))


SIMPLE_PAGES = {
    "/manage": ("Manage trips", "Look up a booking to change seats or flights."),
    "/signin": ("Sign in", "Sign in to see your trips and points."),
    "/about": ("About us", "Harbor Air is a fictional airline for testing."),
    "/help": ("Help centre", "Answers to common questions."),
    "/help/baggage": ("Baggage info", "One carry-on and one personal item on Core and Extra fares."),
    "/checkin/result": ("Your trip", "You are checked in. Boarding pass sent."),
}


@app.route("/<path:p>")
def simple(p):
    path = "/" + p
    if path not in SIMPLE_PAGES:
        abort(404)
    h, t = SIMPLE_PAGES[path]
    return render_template("simple", **ctx(path, heading=h, text=t))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8001)
    ap.add_argument("--defects", default="")
    a = ap.parse_args()
    ACTIVE.update(x for x in a.defects.split(",") if x)
    unknown = ACTIVE - set(DEFECTS) - set(HELDOUT_DEFECTS)
    if unknown:
        raise SystemExit(f"unknown defects: {unknown}")
    random.seed(time.time())
    app.run(port=a.port, debug=False, use_reloader=False)

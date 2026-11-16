# Independent first-draft clone (Task 9). Written by an isolated subagent from tools/observe.py output only
# (screenshots + observation JSON), ~3 min of agent work, no access to the repo. Committed unmodified
# apart from this header; do not polish it (it is the "first draft" test case). See docs/DECISIONS.md D17.
"""Harbor Air clone (first draft, built from screenshots + JSON observations)."""
import argparse
import random
from datetime import datetime, timedelta

from flask import Flask, render_template_string, request

app = Flask(__name__)

BASE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Harbor Air</title>
<style>
*{box-sizing:border-box}
body{margin:0;font-family:Helvetica,Arial,sans-serif;background:#f3f6fb;color:#1b2a3d;font-size:16px}
header{background:#0b2545;color:#fff;height:54px;padding:0 32px;display:flex;align-items:center;justify-content:space-between}
header .brand{color:#fff;font-weight:700;font-size:22px;text-decoration:none}
header nav a{color:#e6edf6;text-decoration:none;font-size:15px;margin-left:20px}
main{max-width:992px;margin:0 auto;padding:28px 0 0}
h1{font-size:30px;margin:0 0 18px}
label{display:block;font-size:13px;font-weight:700;margin-bottom:5px}
input,select{display:block;width:100%;height:39px;border:1px solid #9fb3c8;border-radius:6px;padding:0 10px;font-size:15px;background:#fff}
select{height:41px}
.btn{display:inline-block;height:39px;line-height:39px;padding:0 22px;border-radius:6px;border:0;background:#0b2545;color:#fff;font-size:15px;font-weight:600;text-decoration:none;cursor:pointer;font-family:inherit}
.btn-outline{background:#fff;color:#0b2545;border:1px solid #0b2545;height:41px;line-height:39px;font-weight:400}
.card{background:#fff;border:1px solid #d9e2ec;border-radius:10px;padding:20px}
.price{color:#13315c;font-weight:700}
footer{margin-top:48px;background:#fff;border-top:1px solid #d0dbe7;padding:22px 32px;font-size:14px}
footer a{color:#0b2545;margin-right:18px}
footer .dynamic{color:#5b6b7c;font-size:13px}
.hero{background:linear-gradient(120deg,#13315c,#1d65a6);border-radius:10px;padding:28px 28px 36px;color:#fff}
.hero h1{color:#fff;margin-bottom:20px}
.hero form{display:flex;gap:14px;align-items:flex-end}
.hero .f{width:176px}
.hero .btn{background:#f2b705;color:#0b2545;font-weight:700;padding:0 22px}
.banner{margin:22px 0 32px;background:#fff3cd;border:1px solid #f0d27a;border-radius:6px;padding:14px 18px;font-size:16px}
.banner .price{color:inherit;font-weight:400}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
h2{font-size:24px;margin:0 0 20px}
.dest h3{font-size:18px}
.toolbar{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:16px}
.toolbar .f{width:109px}
.flight{display:flex;align-items:center;justify-content:space-between;margin-bottom:13px;height:81px}
.flight .price{font-size:24px;width:320px}
.fare h2{font-size:20px;margin:0 0 10px}
.fare .price{font-size:24px;margin-bottom:16px}
.fare p{margin:0 0 16px}
.form3{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:20px}
.form2{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-bottom:20px}
.review p{margin:0 0 17px}
.review{padding:24px 20px 20px;margin-bottom:20px}
dialog{border:0;border-radius:12px;padding:24px;width:420px;box-shadow:0 10px 30px rgba(0,0,0,.25)}
dialog::backdrop{background:rgba(11,37,69,.12)}
dialog h2{margin:16px 0 22px;font-size:24px}
dialog p{margin:0 0 18px;font-size:16px}
@media (max-width:700px){
 header{height:80px;flex-direction:column;align-items:flex-start;justify-content:center;gap:8px}
 main{padding:28px 24px 0}
 .hero form{flex-direction:column;align-items:stretch}
 .hero .f{width:100%}
 .hero .btn{align-self:flex-start}
 .grid3,.form3,.form2{grid-template-columns:1fr}
 .flight{flex-wrap:wrap;height:auto}
 .flight .info{width:100%;margin-bottom:12px}
 .flight .price{width:auto}
 footer .dynamic{display:block;margin-top:18px}
}
</style></head><body>
<header><a class="brand" href="/">Harbor Air</a>
<nav><a href="/">Book</a> <a href="/manage">Manage trips</a> <a href="/checkin">Check in</a> <a href="/signin">Sign in</a></nav></header>
<main>{{ body|safe }}</main>
<footer><a href="/about">About us</a> <a href="/help">Help centre</a> <a href="/help/baggage">Baggage info</a>
<span class="dynamic" id="clock">Updated {{ now }}</span></footer>
<script>
setInterval(function(){var d=new Date(),h=d.getHours()%12||12,p=d.getHours()<12?'AM':'PM',z=function(n){return String(n).padStart(2,'0')};
document.getElementById('clock').textContent='Updated '+z(h)+':'+z(d.getMinutes())+':'+z(d.getSeconds())+' '+p;},1000);
</script>
</body></html>"""

FLIGHTS = [("HA101", "6:05 AM", "10:40 AM"), ("HA215", "11:30 AM", "4:02 PM"), ("HA377", "5:45 PM", "10:21 PM")]


def price():
    return random.randint(80, 420)


def page(body, **ctx):
    inner = render_template_string(body, **ctx)
    return render_template_string(BASE, body=inner, now=datetime.now().strftime("%I:%M:%S %p"))


@app.route("/")
def home():
    sale_end = (datetime.now() + timedelta(days=random.randint(10, 20))).strftime("%b %-d, %Y")
    return page("""
<section class="hero"><h1>Where to next?</h1>
<form action="/results" method="get">
 <div class="f"><label for="from">From</label><input id="from" name="from" placeholder="City or airport" required></div>
 <div class="f"><label for="to">To</label><input id="to" name="to" placeholder="City or airport" required></div>
 <div class="f"><label for="depart">Depart</label><input id="depart" name="depart" placeholder="MM/DD/YYYY"></div>
 <div class="f"><label for="pax">Passengers</label><select id="pax" name="pax"><option>1 adult</option><option>2 adults</option><option>3 adults</option></select></div>
 <button class="btn" type="submit">Search</button>
</form></section>
<div class="banner"><strong>Fall sale:</strong> fares from <span class="price">${{ p }}</span>. Sale ends {{ end }}.</div>
<h2>Popular destinations</h2>
<div class="grid3">
{% for city, code in [('San Juan','SJU'),('Boston','BOS'),('Orlando','MCO')] %}
<div class="card dest"><h3>{{ city }}</h3><p>Nonstop flights daily to {{ code }}.</p></div>{% endfor %}
</div>""", p=random.randint(59, 99), end=sale_end)


@app.route("/results")
def results():
    return page("""
<h1>Flights from {{ f }} to {{ t }}</h1>
<div class="toolbar"><a class="btn btn-outline" href="/">Modify search</a>
<div class="f"><label for="sort">Sort by</label><select id="sort" name="sort"><option>Price</option><option>Departure</option><option>Duration</option></select></div></div>
{% for code, dep, arr in flights %}
<div class="card flight"><span class="info"><strong>{{ code }}</strong> · {{ dep }} → {{ arr }} · Nonstop</span>
<span class="price">${{ price() }}</span>
<a class="btn" href="/fares?flight={{ code }}">Select</a></div>{% endfor %}
""", f=request.args.get("from") or "DCA", t=request.args.get("to") or "SJU", flights=FLIGHTS, price=price)


@app.route("/fares")
def fares():
    fl = request.args.get("flight") or "HA101"
    return page("""
<h1>Choose your fare</h1>
<p style="margin:0 0 16px">Flight {{ fl }} · <button class="btn btn-outline" type="button" onclick="document.getElementById('rules').showModal()">Fare rules</button></p>
<div class="grid3">
{% for key, name, desc in [('basic','Basic','Personal item only. No changes.'),('core','Core','Carry-on bag. Free changes.'),('extra','Extra','Extra legroom. Priority boarding.')] %}
<div class="card fare"><h2>{{ name }}</h2><div class="price">${{ price() }}</div><p>{{ desc }}</p>
<a class="btn" href="/passenger?flight={{ fl }}&fare={{ key }}">Select fare</a></div>{% endfor %}
</div>
<dialog id="rules"><h2>Fare rules</h2><p>Changes allowed on Core and Extra fares. Basic fares are non-refundable.</p>
<button class="btn" type="button" onclick="this.closest('dialog').close()">Close</button></dialog>
""", fl=fl, price=price)


@app.route("/passenger")
def passenger():
    return page("""
<h1>Who's flying?</h1>
<form action="/review" method="get"><input type="hidden" name="flight" value="{{ fl }}">
<div class="form3">
 <div><label for="first">First name</label><input id="first" name="first" required></div>
 <div><label for="last">Last name</label><input id="last" name="last" required></div>
 <div><label for="email">Email</label><input id="email" name="email" type="email" required></div>
</div><button class="btn" type="submit">Continue</button></form>
""", fl=request.args.get("flight") or "HA101")


@app.route("/review")
def review():
    a = request.args
    return page("""
<h1>Review and pay</h1>
<div class="card review">
<p><strong>Flight:</strong> {{ fl }}</p>
<p><strong>Passenger:</strong> {{ name }}</p>
<p><strong>Total:</strong> <span class="price" style="font-weight:400;color:inherit">${{ price() }}</span></p></div>
<a class="btn btn-outline" href="/passenger">Back</a>
<button class="btn" type="button">Pay</button>
""", fl=a.get("flight") or "HA101", name=(a.get("first", "") + " " + a.get("last", "")).strip(), price=price)
    # Pay intentionally does nothing: no handler, no payment endpoint.


@app.route("/checkin")
def checkin():
    return page("""
<h1>Check in</h1>
<form action="/checkin/result" method="get"><div class="form2">
 <div><label for="code">Confirmation code</label><input id="code" name="code" required></div>
 <div><label for="last">Last name</label><input id="last" name="last" required></div>
</div><button class="btn" type="submit">Find trip</button></form>""")


def simple(title, text):
    return page("<h1>{{ t }}</h1><p>{{ x }}</p>", t=title, x=text)


@app.route("/checkin/result")
def checkin_result():
    return simple("Your trip", "You are checked in. Boarding pass sent.")


@app.route("/help/baggage")
def baggage():
    return simple("Baggage info", "One carry-on and one personal item on Core and Extra fares.")


@app.route("/manage")
def manage():
    return simple("Manage trips", "Look up a booking to change seats or flights.")


@app.route("/signin")
def signin():
    return simple("Sign in", "Sign in to see your trips and points.")


@app.route("/about")
def about():
    return simple("About us", "Harbor Air is a fictional airline for testing.")


@app.route("/help")
def help_page():
    return simple("Help centre", "Answers to common questions.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--defects", default="")  # accepted and ignored
    port = ap.parse_args().port
    app.run(port=port, debug=False, use_reloader=False)

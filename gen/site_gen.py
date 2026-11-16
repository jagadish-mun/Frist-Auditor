"""Generate a random small Flask site, a clone of it with planted defects, an audit config and an answer key (Task 21).

    python gen/site_gen.py --seed 7 --out /tmp/x      # writes x/real/, x/clone/, x/audit.yaml, x/answer_key.json

Everything is drawn from random.Random(seed), so a seed replays exactly. Both sites run the same engine
(gen/site_app.py) and differ only in site.json: the clone's spec is the real spec with each planted defect applied as
a spec change. Ground truth per defect: `expect` (layer, page, keyword) triples, matched exactly as validate.py does,
decide whether it was found; `side_effects` triples mark the other tickets it legitimately causes (not counted as found,
not counted as false alarms).
"""
import colorsys
import copy
import json
import random
import shutil
from pathlib import Path

import yaml

ENGINE = Path(__file__).with_name("site_app.py")
MASKS = [{"selector": ".price"}, {"selector": ".dynamic"},
         {"regex": r"\$[\d,]+(\.\d{2})?"}, {"regex": r"\d{1,2}:\d{2}:\d{2} [AP]M"}]
SKIP = r"(?i)\b(pay|place order|transfer|delete|purchase|buy|remove)\b"
FONTS = ["Arial, Helvetica, sans-serif", "Georgia, 'Times New Roman', serif", "Verdana, Geneva, sans-serif",
         "'Trebuchet MS', Helvetica, sans-serif"]
# Invented names; checked to avoid real airline / grocery / bank brands.
NAME_WORDS = ["Quillmere", "Fennick", "Larchmoor", "Tessaly", "Corvanne", "Mirrowfield", "Ambervale", "Pellwick",
              "Orrin Bay", "Vantley", "Brisquay", "Holloway Reach", "Calderine", "Wrenfold"]

THEMES = {
    "airline": dict(
        suffix=["Air", "Airways", "Skyways"], money=[79, 899, False],
        h1=["Where to next?", "Fly somewhere new", "Your next trip starts here"],
        tagline=["Low fares to over 40 cities.", "Fly direct, fly often."],
        search_label="Destination", search_button=["Search flights", "Find flights"], search_value="Lisbon",
        list=dict(path=["/flights", "/departures"], nav=["Flights", "Find flights"], h1="Available flights"),
        items=["Boston to Lisbon", "Denver to Reykjavik", "Austin to Mexico City", "Seattle to Tokyo",
               "Chicago to Dublin", "Miami to Bogota", "Atlanta to Madrid"],
        desc=["Nonstop · economy and premium", "1 stop · free carry-on", "Nonstop · meals included",
              "Red-eye · lie-flat available"],
        item_link="Choose flight", detail_path=["/flight", "/itinerary"],
        dialog=["Fare rules", "Baggage policy"],
        dialog_text="Changes are allowed up to 24 hours before departure. Basic fares are non-refundable.",
        detail_cta="Book this flight", form_path=["/passenger", "/traveler"], form_h1="Passenger details",
        fields=[("First name", "first", "text", "Ada"), ("Last name", "last", "text", "Lovelace"),
                ("Email", "email", "email", "ada@example.com"), ("Phone", "phone", "tel", "5550100")],
        optional=["Frequent flyer number", "Promo code"],
        select=[("Seat preference", ["Window", "Aisle", "Middle"]), ("Meal", ["Standard", "Vegetarian", "Vegan"])],
        review_h1="Review your trip", final="Pay",
        sections=[("Today's fares", "Hot fares"), ("Popular routes", "Trending routes")],
        newsletter="Get fare alerts",
        extras=[("/help", "Help", "Help centre"), ("/baggage", "Baggage", "Baggage allowance"),
                ("/about", "About us", "About us"), ("/contact", "Contact", "Contact us")]),
    "grocery": dict(
        suffix=["Market", "Grocers", "Pantry"], money=[1, 18, True],
        h1=["Fresh food, delivered", "Groceries in an hour", "Shop the freshest picks"],
        tagline=["Free delivery on orders over $40.", "Local produce, every day."],
        search_label="Search products", search_button=["Search", "Find"], search_value="apples",
        list=dict(path=["/shop", "/products"], nav=["Shop", "Groceries"], h1="Fresh this week"),
        items=["Honeycrisp apples", "Sourdough loaf", "Oat milk", "Free-range eggs", "Basmati rice",
               "Greek yogurt", "Baby spinach", "Dark roast coffee"],
        desc=["Locally sourced", "Organic · 1 kg", "Best before next week", "Family size"],
        item_link="View product", detail_path=["/product", "/item"],
        dialog=["Nutrition facts", "Allergen info"],
        dialog_text="Per 100 g: energy 52 kcal, fat 0.2 g, sugars 10 g. Packed in a facility that handles nuts.",
        detail_cta="Add to basket", form_path=["/checkout", "/delivery"], form_h1="Delivery details",
        fields=[("Full name", "name", "text", "Ada Lovelace"), ("Email", "email", "email", "ada@example.com"),
                ("Street address", "street", "text", "12 Analytical Way"), ("Postcode", "postcode", "text", "02139")],
        optional=["Delivery notes", "Promo code"],
        select=[("Delivery slot", ["Morning", "Afternoon", "Evening"]), ("Bag type", ["Paper", "Reusable", "No bags"])],
        review_h1="Review your order", final="Place order",
        sections=[("Weekly specials", "Hot deals"), ("Seasonal picks", "Just in")],
        newsletter="Get weekly deals",
        extras=[("/help", "Help", "Help centre"), ("/recipes", "Recipes", "Recipes"),
                ("/stores", "Store locator", "Find a store"), ("/about", "About us", "About us")]),
    "bank": dict(
        suffix=["Bank", "Savings", "Trust"], money=[100, 25000, True],
        h1=["Banking made simple", "Grow your savings", "Money, made easy"],
        tagline=["No monthly fees on everyday accounts.", "Open an account in minutes."],
        search_label="Find an account", search_button=["Search", "Find accounts"], search_value="savings",
        list=dict(path=["/accounts", "/products"], nav=["Accounts", "Open an account"], h1="Our accounts"),
        items=["Everyday checking", "High-yield savings", "Student account", "Joint checking", "12-month CD",
               "Travel rewards card"],
        desc=["No monthly fee", "Interest paid monthly", "Free ATM withdrawals", "Minimum opening deposit applies"],
        item_link="View details", detail_path=["/account", "/product"],
        dialog=["Rate details", "Fee schedule"],
        dialog_text="Rates are variable and may change after the account is opened. Fees apply to paper statements.",
        detail_cta="Open this account", form_path=["/apply", "/application"], form_h1="Your details",
        fields=[("Full name", "name", "text", "Ada Lovelace"), ("Email", "email", "email", "ada@example.com"),
                ("Date of birth", "dob", "text", "12/10/1985"), ("Phone", "phone", "tel", "5550100")],
        optional=["Referral code", "Employer"],
        select=[("Funding source", ["Linked account", "Debit card", "Check"]),
                ("Statement delivery", ["Online", "Mail"])],
        review_h1="Review your application", final="Transfer",
        sections=[("Current rates", "Top rates"), ("Featured accounts", "Our picks")],
        newsletter="Get rate alerts",
        extras=[("/help", "Help", "Help centre"), ("/security", "Security", "Security centre"),
                ("/branches", "Branches", "Find a branch"), ("/about", "About us", "About us")]),
}
INFO_BODY = ["We are here to help seven days a week.", "Most questions are answered within one business day.",
             "Our team is based locally and reachable by phone or chat.", "Policies are reviewed every year."]
VISUAL = {"heading_band": "h1 { background:#ffe08a; }", "button_colour": ".btn { background:%s !important; }"}


def _hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))


def _far_colour(ref):
    """Of three loud colours, the one farthest from `ref` (so a button colour change is always clearly visible)."""
    rgb = lambda c: [int(c[i:i + 2], 16) for i in (1, 3, 5)]  # noqa: E731
    return max(["#e8730c", "#16a34a", "#c026d3"], key=lambda c: sum((a - b) ** 2 for a, b in zip(rgb(c), rgb(ref))))


def build_spec(rng):
    theme = rng.choice(sorted(THEMES))
    T = THEMES[theme]
    hue = rng.random()
    list_path = rng.choice(T["list"]["path"])
    detail_path = rng.choice([p for p in T["detail_path"] if p != list_path])
    form_path = rng.choice(T["form_path"])
    items = [{"id": i + 1, "name": n, "desc": rng.choice(T["desc"])}
             for i, n in enumerate(rng.sample(T["items"], rng.randint(3, 5)))]
    fields = [{"label": l, "name": n, "type": t, "value": v, "required": True}
              for l, n, t, v in sorted(rng.sample(T["fields"], 3), key=T["fields"].index)]
    opt = rng.choice(T["optional"])
    fields.append({"label": opt, "name": "extra", "type": "text", "value": None, "required": False})
    sel_label, sel_opts = rng.choice(T["select"])
    section, section_alt = rng.choice(T["sections"])
    extras = rng.sample(T["extras"], rng.randint(0, 2))           # 5 core pages + 0-2 extras = 5-7 pages
    list_nav = rng.choice(T["list"]["nav"])
    pages = [
        {"path": "/", "kind": "home", "h1": rng.choice(T["h1"]), "tagline": rng.choice(T["tagline"])},
        {"path": list_path, "kind": "list", "h1": T["list"]["h1"]},
        {"path": detail_path, "kind": "detail", "h1": "detail"},
        {"path": form_path, "kind": "form", "h1": T["form_h1"]},
        {"path": "/review", "kind": "review", "h1": T["review_h1"]},
    ] + [{"path": p, "kind": "info", "h1": h, "body": rng.sample(INFO_BODY, 2)} for p, _, h in extras]
    name = f"{rng.choice(NAME_WORDS)} {rng.choice(T['suffix'])}"
    spec = {
        "theme": theme, "name": name, "font": rng.choice(FONTS), "money": T["money"],
        "colors": {"header": _hex(hue, rng.uniform(.45, .7), rng.uniform(.18, .28)),
                   "accent": _hex((hue + rng.uniform(.03, .12)) % 1, rng.uniform(.45, .7), rng.uniform(.3, .4)),
                   "button": _hex((hue + rng.uniform(-.05, .05)) % 1, rng.uniform(.5, .75), rng.uniform(.25, .35)),
                   "bg": _hex(hue, rng.uniform(.2, .4), .97)},
        "pages": pages, "items": items,
        "nav": [{"label": list_nav, "href": list_path}] + [{"label": n, "href": p} for p, n, _ in extras],
        "footer": [{"label": "Home", "href": "/"}] + [{"label": n, "href": p} for p, n, _ in extras],
        "list_path": list_path, "search_label": T["search_label"], "search_button": rng.choice(T["search_button"]),
        "section_heading": section, "newsletter_label": T["newsletter"], "newsletter_works": True,
        "newsletter_text": "One email a week. Unsubscribe any time.",
        "item_href": detail_path, "item_link": T["item_link"],
        "dialog_button": rng.choice(T["dialog"]), "dialog_text": T["dialog_text"], "dialog_works": True,
        "detail_cta": T["detail_cta"], "form_path": form_path, "form_action": "/review",
        "fields": fields, "summary_fields": [f for f in fields if f["required"]],
        "select": {"label": sel_label, "options": sel_opts}, "submit_label": "Continue",
        "final_label": T["final"], "css": {},
        "_gen": {"search_value": T["search_value"], "section_alt": section_alt, "extras": [p for p, _, _ in extras]},
    }
    return spec


def config_for(spec, rng):
    """Audit config: every page, both viewports, masks for prices and the clock, 2-3 flows that stop before the final
    action."""
    P = {p["kind"]: p["path"] for p in spec["pages"]}
    pages = ["/", P["list"], f"{P['detail']}?id=1", f"{P['form']}?item=1", "/review"] + spec["_gen"]["extras"]
    req = [f for f in spec["fields"] if f["required"]]
    pick = rng.randrange(len(spec["items"]))
    flows = [
        {"name": "purchase", "start": "/", "steps": [
            {"fill": {"label": spec["search_label"], "value": spec["_gen"]["search_value"]}},
            {"click": {"role": "button", "name": spec["search_button"]}},
            {"click": {"role": "link", "name": spec["item_link"], "nth": pick}},
            {"click": {"role": "link", "name": spec["detail_cta"]}},
            *[{"fill": {"label": f["label"], "value": f["value"]}} for f in req],
            {"select": {"label": spec["select"]["label"], "value": rng.choice(spec["select"]["options"])}},
            {"click": {"role": "button", "name": spec["submit_label"]}},
            {"stop_before": spec["final_label"]}]},
        {"name": "info_dialog", "start": f"{P['detail']}?id=1", "steps": [
            {"click": {"role": "button", "name": spec["dialog_button"]}},
            {"expect_dialog": spec["dialog_button"]},
            {"click": {"role": "button", "name": "Close"}}]},
    ]
    if rng.random() < 0.5:
        flows.append({"name": "newsletter", "start": "/", "steps": [
            {"click": {"role": "button", "name": spec["newsletter_label"]}},
            {"expect_dialog": "Newsletter sign-up"},
            {"click": {"role": "button", "name": "Close"}}]})
    return {"real_url": "http://127.0.0.1:1", "clone_url": "http://127.0.0.1:2",
            "viewports": [[1440, 900], [390, 844]], "pages": pages, "mask": MASKS, "wait": "load",
            "max_clicks_per_page": 25, "skip_actions": SKIP,
            "weights": {"visual": 0.15, "elements": 0.30, "behavior": 0.25, "flows": 0.30},
            "scoring": "v3", "flows": flows}


# ---------------- defect catalog: each returns (summary, pages, expect, side_effects) after mutating the clone spec ---
def _p(spec, kind):
    return next(p["path"] for p in spec["pages"] if p["kind"] == kind)


def relabel_heading(c, rng):
    old, new = c["section_heading"], c["_gen"]["section_alt"]
    c["section_heading"] = new
    return (f"Home section heading '{old}' relabelled '{new}'", ["/"],
            [("elements", "/", old.lower())], [("visual", "/", ""), ("elements", "/", new.lower())])


def drop_optional_field(c, rng):
    f = next(f for f in c["fields"] if not f["required"])
    c["fields"].remove(f)
    form = _p(c, "form")
    return (f"Optional field '{f['label']}' removed from the form", [form],
            [("elements", form, f["label"].lower())], [("visual", form, ""), ("elements", form, ""), ("behavior", form, "continue")])  # query loses a key


def dead_newsletter(c, rng):
    c["newsletter_works"] = False
    lab = c["newsletter_label"]
    return (f"'{lab}' button no longer opens its dialog", ["/"],
            [("behavior", "/", lab.lower())], [("behavior", "/", "newsletter"), ("flows", None, lab.lower())])


def footer_wrong_link(c, rng):
    f = rng.choice(c["footer"])
    f["href"] = "/page-not-found"
    return (f"Footer link '{f['label']}' points to a 404", ["*"],
            [("behavior", None, f["label"].lower())], [])


def form_wrong_route(c, rng):
    c["form_action"] = "/reveiw"
    form = _p(c, "form")
    return (f"Form '{c['submit_label']}' submits to a non-existent route", [form],
            [("behavior", form, c["submit_label"].lower()), ("flows", None, c["submit_label"].lower())], [])


def drop_flow_field(c, rng):
    f = rng.choice([f for f in c["fields"] if f["required"]])
    c["fields"].remove(f)
    form = _p(c, "form")
    return (f"Required field '{f['label']}' removed from the form", [form],
            [("elements", form, f["label"].lower()), ("flows", None, f["label"].lower())],
            [("visual", form, ""), ("elements", form, ""), ("behavior", form, "continue")])  # query loses a key


def relabel_submit(c, rng):
    old = c["submit_label"]
    c["submit_label"] = "Next"
    form = _p(c, "form")
    return (f"Form button '{old}' relabelled 'Next'", [form],
            [("elements", form, old.lower()), ("flows", None, old.lower())], [("visual", form, ""), ("elements", form, "next")])


def item_wrong_link(c, rng):
    c["item_href"] = c["item_href"] + "s-old"
    lst, lab = _p(c, "list"), c["item_link"]
    return (f"'{lab}' links on {lst} point to a 404", [lst],
            [("behavior", lst, lab.lower()), ("flows", None, lab.lower())], [])


def dead_dialog_button(c, rng):
    c["dialog_works"] = False
    det, lab = _p(c, "detail"), c["dialog_button"]
    return (f"'{lab}' button no longer opens its dialog", [det],
            [("behavior", det, lab.lower()), ("flows", None, lab.lower())], [])


CATEGORIES = {
    "element": [relabel_heading, drop_optional_field],
    "behaviour": [dead_newsletter, footer_wrong_link],
    "flow": [form_wrong_route, drop_flow_field, relabel_submit, item_wrong_link, dead_dialog_button],
}


def visual_only(c, rng, busy):
    """Colour-only change on one page whose pixels no other planted defect touches, so the visual expectation is
    honest (a visual ticket there can only come from this defect)."""
    candidates = [p for p in c["pages"] if p["path"] not in busy]
    page = rng.choice(candidates)
    kinds = ["heading_band"] + (["button_colour"] if page["kind"] != "info" else [])
    kind = rng.choice(kinds)
    css = VISUAL[kind] % _far_colour(c["colors"]["button"]) if kind == "button_colour" else VISUAL[kind]
    c["css"][page["path"]] = css
    what = "heading background" if kind == "heading_band" else "button colour"
    return (f"Visual only: {what} changed on {page['path']}", [page["path"]], [("visual", page["path"], "")], [])


VISUAL_FOOTPRINT = {"relabel_heading", "drop_optional_field", "drop_flow_field", "relabel_submit"}


def plant(spec, rng):
    """Clone spec and answer key: one defect per category, plus 0-2 more from the non-visual pool (4-6 total)."""
    clone = copy.deepcopy(spec)
    chosen = [rng.choice(fs) for fs in CATEGORIES.values()]
    rest = [f for fs in CATEGORIES.values() for f in fs if f not in chosen]
    chosen += rng.sample(rest, rng.randint(0, 2))
    key, busy = [], set()
    for fn in chosen:
        summary, pages, expect, side = fn(clone, rng)
        cat = next(k for k, fs in CATEGORIES.items() if fn in fs)
        key.append({"name": fn.__name__, "category": cat, "summary": summary, "pages": pages,
                    "expect": expect, "side_effects": side})
        if fn.__name__ in VISUAL_FOOTPRINT:
            busy.update(pages)
    summary, pages, expect, side = visual_only(clone, rng, busy)
    key.append({"name": "visual_only", "category": "visual", "summary": summary, "pages": pages,
                "expect": expect, "side_effects": side})
    return clone, key


def generate(seed, out):
    """Write out/real/, out/clone/ (app.py + site.json each), out/audit.yaml and out/answer_key.json."""
    rng = random.Random(seed)
    out = Path(out)
    spec = build_spec(rng)
    cfg = config_for(spec, rng)
    clone, key = plant(spec, rng)
    for name, s in (("real", spec), ("clone", clone)):
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy(ENGINE, d / "app.py")
        (d / "site.json").write_text(json.dumps(s, indent=1))
    (out / "audit.yaml").write_text(yaml.safe_dump(cfg, sort_keys=False))
    answer = {"seed": seed, "theme": spec["theme"], "site": spec["name"], "pages": cfg["pages"],
              "flows": [f["name"] for f in cfg["flows"]], "defects": key}
    (out / "answer_key.json").write_text(json.dumps(answer, indent=2))
    return answer


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    print(json.dumps(generate(a.seed, a.out), indent=2))

"""Catalog of plantable defects.

Each defect is a known, deliberate difference between the reference app (the
"real site") and a clone. Because we plant them ourselves, we know exactly
which gaps the auditor *should* report — that is the ground truth used by the
planted-defect validation (SPEC §9.1).

`pages` lists where the defect is visible ("*" = every page). `expect` describes how a correct auditor would surface the defect: a list of
(layer, page, keyword) triples. A reported gap counts as detecting the defect
if its layer and page match and the keyword appears in its description
(case-insensitive). `page=None` matches any page.
"""

DEFECTS = {
    "remove_nav_manage": {
        "pages": ['*'],
        "kind": "remove component",
        "summary": "'Manage trips' link removed from the header nav",
        "expect": [("elements", None, "manage trips")],
    },
    "rename_fare_core": {
        "pages": ['/fares'],
        "kind": "rename label",
        "summary": "Fare card 'Core' renamed to 'Main'",
        "expect": [("elements", "/fares", "core")],
    },
    "broken_baggage_link": {
        "pages": ['*'],
        "kind": "broken link",
        "summary": "Footer 'Baggage info' link points to a 404",
        "expect": [("behavior", None, "baggage info")],
    },
    "layout_shift_hero": {
        "pages": ['/'],
        "kind": "layout shift",
        "summary": "Home hero section pushed down 48px",
        "expect": [("visual", "/", ""), ("elements", "/", "")],
    },
    "button_color": {
        "pages": ['/'],
        "kind": "style change",
        "summary": "Search button colour changed from navy to orange",
        "expect": [("visual", "/", "")],
    },
    "fare_rules_noop": {
        "pages": ['/fares'],
        "kind": "broken behaviour",
        "summary": "'Fare rules' button no longer opens its dialog",
        "expect": [("behavior", "/fares", "fare rules"), ("flows", None, "fare rules")],
    },
    "rename_continue": {
        "pages": ['/passenger'],
        "kind": "rename label",
        "summary": "Passenger page 'Continue' button renamed 'Next'",
        "expect": [("elements", "/passenger", "continue"), ("flows", None, "continue")],
    },
    "missing_email": {
        "pages": ['/passenger'],
        "kind": "remove component",
        "summary": "Email field removed from the passenger form",
        "expect": [("elements", "/passenger", "email"), ("flows", None, "email")],
    },
    "extra_chat_widget": {
        "pages": ['/'],
        "kind": "extra component",
        "summary": "Clone adds a 'Chat with us' button that the real site lacks",
        "expect": [("elements", None, "chat with us")],
    },
    "search_wrong_route": {
        "pages": ['/'],
        "kind": "broken flow",
        "summary": "Search form submits to a non-existent route",
        "expect": [("behavior", "/", "search"), ("flows", None, "search")],
    },
    "results_sort_missing": {
        "pages": ['/results'],
        "kind": "remove component",
        "summary": "'Sort by' dropdown removed from results",
        "expect": [("elements", "/results", "sort by")],
    },
    "checkin_label": {
        "pages": ['/checkin'],
        "kind": "rename label",
        "summary": "Check-in 'Confirmation code' field relabelled 'Booking reference'",
        "expect": [("elements", "/checkin", "confirmation code"), ("flows", None, "confirmation code")],
    },
    "font_change": {
        "pages": ['/review'],
        "kind": "style change",
        "summary": "Review page uses a serif font",
        "expect": [("visual", "/review", "")],
    },
    "signin_goes_home": {
        "pages": ['*'],
        "kind": "wrong link target",
        "summary": "'Sign in' link goes to the home page instead of /signin",
        "expect": [("behavior", None, "sign in")],
    },
    "subtle_drift": {
        "pages": ["*"],
        "kind": "rebuild drift (not a planted defect)",
        "summary": "Many 1-2px spacing / font-size / colour drifts, as in a hand- or agent-rebuilt clone",
        "expect": [("visual", None, "")],
    },
}

# Defects planted in the screenshot-rebuilt clone (refapp/clone_rebuilt/app.py), one per kind,
# on elements the template defects do not touch. Measures recall on top of realistic rebuild noise.
REBUILT_DEFECTS = {
    "rb_no_modify": {
        "pages": ["/results"], "kind": "remove component",
        "summary": "'Modify search' button removed from the results page",
        "expect": [("elements", "/results", "modify search")],
    },
    "rb_relabel_find": {
        "pages": ["/checkin"], "kind": "rename label",
        "summary": "Check-in submit button reads 'Look up' instead of 'Find trip'",
        "expect": [("elements", "/checkin", "find trip"), ("flows", None, "find trip")],
    },
    "rb_broken_about": {
        "pages": ["*"], "kind": "broken link",
        "summary": "Footer 'About us' link points to a 404 (/about-us)",
        "expect": [("behavior", None, "about us")],
    },
    "rb_search_dead": {
        "pages": ["/"], "kind": "broken flow",
        "summary": "Home 'Search' button does not submit the form",
        "expect": [("behavior", "/", "search"), ("flows", None, "search")],
    },
}

# Task 11: one defect per new behaviour capability (select options, buttons inside dialogs). Kept apart from
# REBUILT_DEFECTS so the Phase 1 "all four" clone keeps its meaning.
REBUILT_COVERAGE_DEFECTS = {
    "rb_pax_option_missing": {
        "pages": ["/"], "kind": "missing select option",
        "summary": "Home 'Passengers' select lacks the '3 adults' option",
        "expect": [("behavior", "/", "3 adults")],
    },
    "rb_dialog_close_dead": {
        "pages": ["/fares"], "kind": "dead dialog button",
        "summary": "'Close' in the Fare rules dialog does nothing",
        "expect": [("behavior", "/fares", "close"), ("flows", None, "close")],
    },
}

# Fixed order used by the cumulative (monotonicity) sweep.
SWEEP_ORDER = [
    "font_change", "rename_fare_core", "button_color", "remove_nav_manage",
    "broken_baggage_link", "extra_chat_widget", "layout_shift_hero",
    "results_sort_missing", "signin_goes_home", "fare_rules_noop",
    "checkin_label", "rename_continue", "missing_email", "search_wrong_route",
]

# Three clone tiers for the demo (SPEC §13).
TIERS = {
    "clone_high": ["font_change", "rename_fare_core"],
    "clone_mid": ["font_change", "rename_fare_core", "button_color", "remove_nav_manage",
                  "broken_baggage_link", "fare_rules_noop"],
    "clone_low": SWEEP_ORDER[:],
}

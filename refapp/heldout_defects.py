"""Held-out planted defects (Task 7). Written by an isolated subagent; see docs/DECISIONS.md D14."""
HELDOUT_DEFECTS = {
    "ho_move_fare_rules": {
        "pages": ["/fares"],
        "kind": "moved",
        "summary": "The 'Fare rules' button on /fares is shifted 160px to the right; it still opens the fare rules dialog.",
        "expect": [("elements", "/fares", "fare rules"), ("visual", "/fares", "")],
    },
    "ho_move_find_trip": {
        "pages": ["/checkin"],
        "kind": "moved",
        "summary": "The 'Find trip' submit button on /checkin is pushed 60px further down; it still submits the form.",
        "expect": [("elements", "/checkin", "find trip"), ("visual", "/checkin", "")],
    },
    "ho_relabel_checkin_nav": {
        "pages": ["*"],
        "kind": "relabel",
        "summary": "The main-nav link 'Check in' is relabelled 'Online check-in' (same target).",
        "expect": [("elements", None, "check in"), ("behavior", None, "check in")],
    },
    "ho_relabel_modify_search": {
        "pages": ["/results"],
        "kind": "relabel",
        "summary": "The 'Modify search' link on /results is relabelled 'Change search' (same target).",
        "expect": [("elements", "/results", "modify search"), ("behavior", "/results", "modify search")],
    },
    "ho_missing_help_footer": {
        "pages": ["*"],
        "kind": "missing",
        "summary": "The footer 'Help centre' link is removed from every page.",
        "expect": [("elements", None, "help centre"), ("behavior", None, "help centre")],
    },
    "ho_select_skips_fares": {
        "pages": ["/results"],
        "kind": "wrong link",
        "summary": "The flight 'Select' links on /results go to /passenger instead of /fares, skipping fare selection.",
        "expect": [("behavior", "/results", "select"), ("elements", "/results", "select"), ("flows", None, "select")],
    },
    "ho_continue_dead": {
        "pages": ["/passenger"],
        "kind": "dead button",
        "summary": "The 'Continue' button on /passenger is type=button, so clicking it does nothing.",
        "expect": [("behavior", "/passenger", "continue"), ("flows", None, "continue")],
    },
    "ho_checkin_wrong_action": {
        "pages": ["/checkin"],
        "kind": "broken submit",
        "summary": "The check-in form submits to /checkin/results (404) instead of /checkin/result.",
        "expect": [("behavior", "/checkin", "find trip"), ("flows", None, "find trip")],
    },
    "ho_extra_baggage_calc": {
        "pages": ["/help/baggage"],
        "kind": "extra",
        "summary": "A 'Baggage fee calculator' button-styled link (to /help) is added to /help/baggage.",
        "expect": [("elements", "/help/baggage", "baggage fee calculator"), ("visual", "/help/baggage", "")],
    },
    "ho_promo_tint": {
        "pages": ["/"],
        "kind": "cosmetic",
        "summary": "The fall-sale promo banner on / changes from pale yellow to pale blue (background and border colour only).",
        "expect": [("visual", "/", "")],
    },
}

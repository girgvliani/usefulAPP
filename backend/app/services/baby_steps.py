"""Dave Ramsey's 7 Baby Steps, tracked from the numbers the user enters.

Order matters: Ramsey's plan is sequential (no investing while in debt), so the Wealth score only
counts a step once every step before it is done; steps 4, 5 and 6 run side by side. Steps that don't
apply (no children, no home loan while renting) are left out.
"""

STEPS = [
    (1, "Starter emergency fund", "Save a starter emergency fund ($1,000 in Ramsey's plan) for emergencies only."),
    (2, "Pay off all debt but the house", "List debts smallest to largest and pay them off in that order: the debt snowball."),
    (3, "Full emergency fund", "Save 3-6 months of expenses."),
    (4, "Invest 15% for retirement", "Put 15% of your household income into retirement."),
    (5, "Save for your children's college", "Save for your kids' education."),
    (6, "Pay off your home early", "Throw extra money at the mortgage."),
    (7, "Build wealth and give", "Keep building, and give generously."),
]

DEFAULTS = {
    "starter_target": 1000,     # step 1, in the user's currency
    "saved": 0,                 # emergency fund so far (steps 1 and 3)
    "monthly_expenses": None,   # step 3
    "months": 6,                # step 3: 3-6
    "debts": [],                # step 2: [{"name", "balance", "original"}]
    "invest_percent": 0,        # step 4: % of income invested for retirement
    "kids": False,              # step 5 applies
    "college_saved": 0,
    "college_target": None,
    "home": "renting",          # step 6: renting (doesn't apply) / mortgage / owned
    "mortgage_balance": None,
    "mortgage_original": None,
    "giving": False,            # step 7
}


def plan_of(saved: dict | None) -> dict:
    return {**DEFAULTS, **(saved or {})}


def _ratio(have, need):
    if not need:
        return None
    return max(0.0, min(1.0, (have or 0) / need))


def steps(saved: dict | None) -> dict:
    """Each step's progress (0-1, None = needs numbers, "n/a" = doesn't apply), the current step, and
    the Wealth score (None until the user has filled anything in)."""
    p = plan_of(saved)
    debts = [d for d in p["debts"] if (d.get("original") or 0) > 0]
    owed, borrowed = sum(d["balance"] for d in debts), sum(d["original"] for d in debts)
    snowball = sorted((d for d in debts if d["balance"] > 0), key=lambda d: d["balance"])

    progress = {
        1: _ratio(p["saved"], p["starter_target"]),
        2: 1.0 if not borrowed else max(0.0, 1 - owed / borrowed),
        3: _ratio(p["saved"], (p["monthly_expenses"] or 0) * p["months"]),
        4: min(1.0, (p["invest_percent"] or 0) / 15),
        5: _ratio(p["college_saved"], p["college_target"]) if p["kids"] else "n/a",
        6: ("n/a" if p["home"] == "renting" else 1.0 if p["home"] == "owned"
            else 1 - _ratio(p["mortgage_balance"], p["mortgage_original"]) if p["mortgage_original"] else None),
    }
    before_seven = [progress[s] for s in range(1, 7) if progress[s] != "n/a"]
    progress[7] = 1.0 if p["giving"] and all(v == 1 for v in before_seven) else 0.0

    notes = {
        1: f"{p['saved']:,.0f} of {p['starter_target']:,.0f} saved",
        2: (f"Next in the snowball: {snowball[0]['name']} ({snowball[0]['balance']:,.0f} left)" if snowball
            else "Debt-free (except the house)" if borrowed else "No debts listed"),
        3: (f"{p['saved']:,.0f} of {(p['monthly_expenses'] or 0) * p['months']:,.0f} ({p['months']} months of expenses)"
            if p["monthly_expenses"] else "Add your monthly expenses"),
        4: f"{p['invest_percent']:g}% of income invested",
        5: ("No children" if not p["kids"] else
            f"{p['college_saved']:,.0f} of {p['college_target']:,.0f}" if p["college_target"] else "Add a college target"),
        6: ({"renting": "Renting: doesn't apply", "owned": "Home paid off"}.get(p["home"])
            or (f"{p['mortgage_balance']:,.0f} of {p['mortgage_original']:,.0f} left" if p["mortgage_original"] else "Add your mortgage")),
        7: "Giving" if p["giving"] else "Tick when you give regularly",
    }

    # The step you're on: 1, 2, 3 in order, then 4-6 together, then 7
    done = lambda s: progress[s] == "n/a" or progress[s] == 1
    current = next((s for s in (1, 2, 3) if not done(s)), None)
    if current is None:
        current = next((s for s in (4, 5, 6) if not done(s)), None) or (7 if not done(7) else None)

    # Score: only steps reached in order count; the current one counts as far as it's got
    applicable = [s for s in range(1, 8) if progress[s] != "n/a"]
    earned = 0.0
    for s in applicable:
        if current is not None and s > current and not (current in (4, 5, 6) and s in (4, 5, 6)):
            break
        earned += progress[s] or 0
    started = saved and any(saved.get(k) not in (None, DEFAULTS[k]) for k in DEFAULTS)
    return {
        "plan": p,
        "current": current,
        "score": round(earned / len(applicable), 3) if started else None,
        "steps": [
            {"step": n, "title": title, "detail": detail,
             "progress": progress[n], "done": done(n), "current": n == current, "note": notes[n]}
            for n, title, detail in STEPS
        ],
    }

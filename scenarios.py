"""
The runs your test needs. ← UNIT 4, MILESTONE 3

Each of your five criteria needs something run against it. A criterion about
the empty-search branch needs an impossible query. One about the fit card needs
the same item run more than once. Working that out is Milestone 3's first step,
and this file is where you write it down.

`run_eval.py` runs everything here five times and writes the run log — five
because your criteria are written out of five.

Three scenarios are filled in to show the shape. Add or change whatever your
own criteria need — these are a starting point, not a fixed set.
"""

SCENARIOS = [
    {
        # A query the data can match. Criterion 1.
        "name": "matching query completes",
        "query": "vintage graphic tee under $30",
        "wardrobe": "example",
        "criterion": 1,
    },
    {
        # A query nothing can match. Criterion 2 — the branch.
        "name": "impossible query stops early",
        "query": "designer ballgown size XXS under $5",
        "wardrobe": "example",
        "criterion": 2,
    },
    {
        # A user with nothing saved. One of unit 4's three failure modes.
        # Not one of the five criteria. suggest_outfit should still return advice.
        "name": "empty wardrobe",
        "query": "denim jacket under $50",
        "wardrobe": "empty",
        "criterion": None,
    },
    {
        # Criterion 3: ids in the session, on a query that matches.
        "name": "selected item matches the item passed on",
        "query": "90s track jacket in size M",
        "wardrobe": "example",
        "criterion": 3,
    },
    {
        # Criterion 5: every returned price is under the ceiling.
        "name": "price ceiling holds",
        "query": "silk slip dress in midi length under $40",
        "wardrobe": "example",
        "criterion": 5,
    },
    {
        # Criterion 4 is five different listings, not five repeats of one.
        # Each of these is one card. run_eval still repeats each five times;
        # the verdict uses one card per listing (try 1 of each, plus the
        # matching-query card above as the fifth listing).
        "name": "fit card: platform sneakers",
        "query": "platform sneakers size 8",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card: denim jacket",
        "query": "denim jacket under $50",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card: corduroy pants",
        "query": "corduroy wide-leg pants under $40",
        "wardrobe": "example",
        "criterion": 4,
    },
    {
        "name": "fit card: bucket hat",
        "query": "bucket hat under $20",
        "wardrobe": "example",
        "criterion": 4,
    },
]

WARDROBES = ("example", "empty")


def validate() -> list[str]:
    """Complain about anything malformed, before a long run rather than during."""
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("query", "").strip():
            problems.append(f"scenario {i} has no query")
        if scenario.get("wardrobe") not in WARDROBES:
            problems.append(
                f"scenario {i} has wardrobe {scenario.get('wardrobe')!r} — "
                f"it should be one of {WARDROBES}"
            )
    return problems

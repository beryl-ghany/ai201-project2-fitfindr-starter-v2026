"""
The FitFindr planning loop.

This is the file that makes FitFindr an agent rather than a script. It decides
which tool to run next based on what the last one returned.

If your loop calls all three tools no matter what comes back, you have a list
of function calls. A loop looks at the last result before it picks the next
step. **That branch is the graded part of this unit.**

Build and test your three tools in `tools.py` first. Then come here.

    python agent.py          runs both example paths below
"""

import re

import trace
from generate import ModelUnavailable
from mcp_client import MCPError, call_tool
from tools import suggest_outfit, create_fit_card

# config is imported for side effects: .env loading and the Windows console fix.
import config  # noqa: F401

_LETTER_SIZES = {
    "xxs": "XXS",
    "xs": "XS",
    "s": "S",
    "small": "S",
    "m": "M",
    "med": "M",
    "medium": "M",
    "l": "L",
    "large": "L",
    "xl": "XL",
    "xxl": "XXL",
}

_QUERY_FILLER = {
    "a", "an", "the", "for", "in", "and", "with", "looking", "look",
    "want", "wanted", "please", "some", "of", "my", "me", "i", "to",
    "on", "under", "below", "size", "sized",
}


# ── session state ─────────────────────────────────────────────────────────────

def new_session(query: str, wardrobe: dict) -> dict:
    """
    A fresh session for one user interaction.

    The session is the single source of truth for a run. Every tool result goes
    in here, and the next tool reads it back out.

    You could pass values straight from one call to the next. It would work,
    and you would not be able to test it — you can't print a variable you have
    already overwritten. Going through the session is what makes the state
    visible, and unit 4 has you write a criterion about exactly that.

    Add fields if you need them.
    """
    return {
        "query": query,              # what the user typed
        "parsed": {},                # description / size / max_price you pulled out of it
        "search_results": [],        # everything search_listings returned
        "selected_item": None,       # the one you chose — goes into suggest_outfit
        "wardrobe": wardrobe,        # the user's wardrobe
        "outfit_suggestion": None,   # what suggest_outfit returned
        "fit_card": None,            # what create_fit_card returned
        "error": None,               # set when the run ended early
        # Id handed to suggest_outfit, copied from the session so a check can
        # see it without re-running the tool. Stays None when search is empty.
        "passed_to_suggest_outfit_id": None,
    }


def parse_query(query: str) -> dict:
    """
    Pull a description, a size, and a max price out of a plain-language query.

    Regex and string splitting, not a model call. Price comes from
    'under $30' / 'under 30' / a bare '$30'. Size comes from 'size M',
    'size medium', or 'size 8'. Whatever is left, minus filler words, is
    the description search_listings scores.
    """
    text = query or ""
    max_price = None
    price_match = re.search(
        r"(?:under|below|less than|max|up to)\s*\$?\s*(\d+(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )
    if price_match is None:
        price_match = re.search(r"\$\s*(\d+(?:\.\d+)?)", text)
    if price_match is not None:
        max_price = float(price_match.group(1))
        text = text[: price_match.start()] + " " + text[price_match.end() :]

    size = None
    size_match = re.search(
        r"\bsize\s+"
        r"(xxs|xs|small|medium|large|xxl|xl|s|m|l|"
        r"one(?:\s+size)?|"
        r"(?:us\s+)?\d+(?:\.\d+)?|"
        r"w\d+(?:\s*l\d+)?)\b",
        text,
        flags=re.IGNORECASE,
    )
    if size_match is not None:
        raw = size_match.group(1).strip()
        key = re.sub(r"\s+", " ", raw.lower())
        if key in _LETTER_SIZES:
            size = _LETTER_SIZES[key]
        elif key in {"one", "one size"}:
            size = "one"
        else:
            size = raw
        text = text[: size_match.start()] + " " + text[size_match.end() :]

    words = re.findall(r"[a-z0-9']+", text.lower())
    description = " ".join(word for word in words if word not in _QUERY_FILLER)
    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


def _empty_search_message(parsed: dict) -> str:
    """Say what was searched and what the user could change. Not 'No results'."""
    asked = [f"'{parsed.get('description') or 'that description'}'"]
    changes = [
        "a broader description (search matches words in the title, description, and style tags)"
    ]
    if parsed.get("size"):
        asked.append(f"size {parsed['size']}")
        changes.append("a different size, or leave the size off")
    if parsed.get("max_price") is not None:
        price = parsed["max_price"]
        price_text = str(int(price)) if price == int(price) else str(price)
        asked.append(f"at or under ${price_text}")
        changes.append("a higher price ceiling")
    return (
        "Nothing in the listings matched "
        + ", ".join(asked)
        + ". Try "
        + "; or ".join(changes)
        + "."
    )


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Run the loop once and return the finished session.

    Args:
        query:    what the user asked for, in plain language
                  (e.g. "vintage graphic tee under $30, size M").
        wardrobe: a wardrobe dict — get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py.

    Returns:
        The session dict. **Check session["error"] first** — if it isn't None,
        the run ended early and the later fields will still be None.

    ─────────────────────────────────────────────────────────────────────────
    TODO — build this, following the branch rule you wrote in Milestone 2.

      1. Start a session with new_session().

      2. Count the times round the loop, and call trace.check_iterations(count)
         on each one before you go again. It raises when the count passes
         MAX_ITERATIONS in config.py — see trace.py.

      3. Parse the query into a description, a size, and a max_price. Regex,
         string splitting, or asking the model are all fine — say which you
         chose in your README. Put the result in session["parsed"].

      4. Call search_listings() with what you parsed.
         Put the results in session["search_results"].

         ⚠️ THIS IS THE BRANCH. If nothing came back:
              - put a message in session["error"] saying what the user could
                change — "No results" is not that message
              - return the session
              - do NOT call suggest_outfit with nothing

      5. Choose an item — the first result is fine. Put it in
         session["selected_item"].

      6. Call suggest_outfit() with the selected item and the wardrobe.
         Put the result in session["outfit_suggestion"].

      7. Call create_fit_card() with the outfit and the item.
         Put the result in session["fit_card"].

      8. Return the session.

    ─────────────────────────────────────────────────────────────────────────
    IN UNIT 4 you come back and add two things:

      • Trace calls. One per step. `trace.step("search_listings", inputs=...,
        returned=...)` — see trace.py. Your README needs the output.

      • A handler for ModelUnavailable, so a bad key produces a message rather
        than a stack trace. The import is already at the top of this file.
    """
    session = new_session(query, wardrobe)
    iterations = 0

    def _step() -> None:
        nonlocal iterations
        iterations += 1
        trace.check_iterations(iterations)

    _step()
    session["parsed"] = parse_query(session["query"])
    parsed = session["parsed"]

    _step()
    search_inputs = {
        "description": parsed["description"],
        "size": parsed["size"],
        "max_price": parsed["max_price"],
    }
    try:
        session["search_results"] = call_tool("search_listings", search_inputs)
    except MCPError as exc:
        session["error"] = (
            "Search didn't run: the listings tool could not be reached. "
            f"What broke: {exc} "
            "Try the same request again. If it keeps failing, the search "
            "server in mcp_server.py isn't starting."
        )
        trace.step(
            "search_listings (via MCP)",
            inputs=search_inputs,
            note="MCP call failed; stopping",
        )
        return session

    if not isinstance(session["search_results"], list):
        session["search_results"] = []

    prices = [item.get("price") for item in session["search_results"]]
    trace.step(
        "search_listings (via MCP)",
        inputs=search_inputs,
        returned=session["search_results"],
        note="prices: " + (", ".join(str(price) for price in prices) or "none"),
    )

    # Branch: an empty list stops the loop. The next tool never sees nothing.
    if not session["search_results"]:
        session["error"] = _empty_search_message(parsed)
        trace.step("branch", note="empty search, stopping before suggest_outfit")
        return session

    _step()
    session["selected_item"] = session["search_results"][0]
    session["passed_to_suggest_outfit_id"] = session["selected_item"]["id"]
    trace.step(
        "select item",
        returned=session["selected_item"],
        note=(
            f"selected_id={session['selected_item'].get('id')} "
            f"first_id={session['search_results'][0].get('id')} "
            f"passed_to_suggest_outfit_id={session['passed_to_suggest_outfit_id']}"
        ),
    )

    _step()
    wardrobe_count = len((session["wardrobe"] or {}).get("items") or [])
    try:
        session["outfit_suggestion"] = suggest_outfit(
            session["selected_item"],
            session["wardrobe"],
        )
    except ModelUnavailable as exc:
        session["error"] = _model_unavailable_message(exc)
        trace.step(
            "suggest_outfit",
            inputs={
                "item_id": session["passed_to_suggest_outfit_id"],
                "wardrobe_items": wardrobe_count,
            },
            note="model unavailable; stopping before create_fit_card",
        )
        return session

    trace.step(
        "suggest_outfit",
        inputs={
            "item_id": session["passed_to_suggest_outfit_id"],
            "wardrobe_items": wardrobe_count,
        },
        returned=session["outfit_suggestion"],
        note="empty wardrobe: general advice" if wardrobe_count == 0 else "",
    )

    _step()
    try:
        session["fit_card"] = create_fit_card(
            session["outfit_suggestion"] or "",
            session["selected_item"],
        )
    except ModelUnavailable as exc:
        session["error"] = _model_unavailable_message(exc)
        trace.step("create_fit_card", note="model unavailable")
        return session

    trace.step(
        "create_fit_card",
        inputs={"item_id": session["selected_item"].get("id")},
        returned=session["fit_card"],
    )
    return session


def _model_unavailable_message(exc: ModelUnavailable) -> str:
    """Say the model is down and what to try. Not a stack trace."""
    return (
        "The model couldn't be reached, so I stopped before finishing the "
        f"outfit and the caption. {exc} "
        "Then run the same request again."
    )


# ── running it directly ───────────────────────────────────────────────────────

def _show(session: dict) -> None:
    if session["error"]:
        print(f"  stopped: {session['error']}")
        print(f"  fit_card is {session['fit_card']!r} — it should still be None here")
        return

    item = session["selected_item"] or {}
    print(f"  found:    {item.get('title')} — ${item.get('price')} on {item.get('platform')}")
    print(f"  outfit:   {session['outfit_suggestion']}")
    print(f"  fit card: {session['fit_card']}")


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== A query the data can match ===")
    _show(run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    ))

    print("\n=== A query it can't ===")
    _show(run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    ))

    print(
        "\nThe second one should stop before the fit card. If both paths look "
        "the same,\nthe branch isn't doing anything yet."
    )

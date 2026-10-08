"""
The three FitFindr tools.

Each one is a standalone function you can call and test on its own, before any
of them are wired into the loop. Build and test them one at a time — three
untested tools joined by a loop is one problem that looks like six, because you
can't tell which layer is lying to you.

    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)             → str
    create_fit_card(outfit, new_item)              → str

All three are stubs right now. They run and they do nothing — that's the
starting position and it's deliberate.

⚠️ Before you write any of them, fill in the **Tool Inventory** section of your
README (Milestone 2). Four lines per tool: what it does, each input with its
type, exactly what it returns, and what it returns when it has nothing to give.
That last line is what your loop branches on. "Returns a list" earns nothing —
the description has to say what is *in* the list.
"""

import re

import config
from generate import generate
from utils.data_loader import load_listings

# Words that show up in size labels but are not themselves a size.
_SIZE_NOISE = {"size", "fits", "oversized", "adjustable"}


def _size_tokens(value: str) -> list[str]:
    """Split a size on punctuation so 'S' is not found inside 'US' or 'XL'."""
    return [part for part in re.split(r"[^a-z0-9.]+", value.lower()) if part]


def _sizes_match(wanted: str, listing_size: str) -> bool:
    """
    True when every size token the user asked for appears as a whole token
    in the listing. 'M' matches 'S/M'. 'S' does not match 'US 9'. 'L' does
    not match 'XL'. '8' matches 'US 8' and does not match 'US 8.5'.
    """
    wanted_tokens = [
        token for token in _size_tokens(wanted) if token not in _SIZE_NOISE
    ]
    if not wanted_tokens:
        return True
    listing_tokens = _size_tokens(listing_size or "")
    return all(token in listing_tokens for token in wanted_tokens)


def _keyword_score(description: str, listing: dict) -> int:
    """
    Count keyword hits, weighted so a word in the title outranks the same
    word buried in a description. A mesh top that only mentions a graphic
    tee as a layering idea should not beat a listing whose title is a tee.
    """
    words = re.findall(r"[a-z0-9']+", (description or "").lower())
    if not words:
        return 0
    fields = (
        (listing.get("title") or "", 3),
        (" ".join(listing.get("style_tags") or []), 2),
        (listing.get("description") or "", 1),
        (listing.get("category") or "", 1),
        (listing.get("brand") or "", 1),
        (" ".join(listing.get("colors") or []), 1),
    )
    score = 0
    for word in words:
        pattern = rf"\b{re.escape(word)}\b"
        for text, weight in fields:
            if re.search(pattern, text.lower()):
                score += weight
    return score


def _item_details(item: dict) -> str:
    colors = ", ".join(item.get("colors") or []) or "unknown"
    tags = ", ".join(item.get("style_tags") or []) or "none listed"
    brand = item.get("brand") or "none listed"
    return (
        f"Title: {item.get('title')}\n"
        f"Category: {item.get('category')}\n"
        f"Size: {item.get('size')}\n"
        f"Price: ${item.get('price')}\n"
        f"Platform: {item.get('platform')}\n"
        f"Condition: {item.get('condition')}\n"
        f"Colors: {colors}\n"
        f"Style tags: {tags}\n"
        f"Brand: {brand}\n"
        f"Description: {item.get('description')}"
    )


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the listings data for items matching a description, and optionally a
    size and a price ceiling.

    This is the tool that doesn't call the model, which makes it the easiest one
    to test and the one to move onto MCP in unit 4.

    Args:
        description: keywords describing what the user wants
                     (e.g. "vintage graphic tee").
        size:        a size string to filter by, or None to skip size filtering.
                     Match case-insensitively — "M" should match "S/M".

                     ⚠️ Read the sizes in the data before you reach for a plain
                     substring test. `"s" in "us 9"` is True, and so is
                     `"l" in "xl"`. A filter that returns shoes when someone
                     asked for a small top reads like a broken search, and it
                     will quietly cost you in unit 4 when you test criterion 1.
                     What counts as a size match is part of your spec — decide
                     it and write it into your Tool Inventory.
        max_price:   maximum price, inclusive, or None to skip price filtering.

    Returns:
        A list of matching listing dicts, best match first.
        **Returns an empty list when nothing matches — an empty list, not None,
        and not an exception.** Your loop branches on this.

    Each listing dict has these fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand (str or None), platform

    Note that `brand` is None for most listings. That is deliberate and
    realistic — thrift listings often have no brand. If something you write
    assumes a brand is always there, you will find out in unit 4.

    TODO:
        1. Load every listing with load_listings().
        2. Filter by max_price and by size, when each is provided.
        3. Score what's left by keyword overlap with `description`.
        4. Drop anything scoring zero.
        5. Sort by score, highest first, and return the listing dicts —
           at most config.SEARCH_RESULT_LIMIT of them.

    Test it from a terminal before you move on:
        python -c "from tools import search_listings; print(search_listings('graphic tee', max_price=30))"
    """
    matches: list[tuple[int, dict]] = []
    for listing in load_listings():
        price = listing.get("price")
        if max_price is not None and (price is None or float(price) > max_price):
            continue
        if size is not None and not _sizes_match(size, str(listing.get("size") or "")):
            continue
        score = _keyword_score(description, listing)
        if score <= 0:
            continue
        matches.append((score, listing))

    matches.sort(key=lambda pair: (-pair[0], float(pair[1].get("price") or 0)))
    return [listing for _, listing in matches[: config.SEARCH_RESULT_LIMIT]]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest one or two outfits.

    This one calls the model, through `generate()`. You don't need to think
    about rate limits — the adapter handles pacing for you.

    Args:
        new_item: a listing dict — the item the user is considering.
        wardrobe: a wardrobe dict with an 'items' key holding a list of items.
                  **It may be empty.** Handle that.

    Returns:
        A non-empty string with outfit suggestions.
        With an empty wardrobe, return general styling advice rather than
        raising or returning "". Unit 4 has you trigger the empty wardrobe on
        purpose, so decide now what it should do.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If it is, ask the model for general styling ideas for this item.
        3. If it isn't, format the wardrobe items into the prompt and ask for
           specific combinations naming pieces the user already owns.
        4. Return the model's response.

    Test it from a terminal before you move on:
        python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
    """
    owned = (wardrobe or {}).get("items") or []
    title = (new_item or {}).get("title") or "this item"
    if not owned:
        prompt = (
            "The wardrobe is empty. Give general styling advice for this thrift "
            f"find: one or two outfit ideas a person could build around it. "
            f"Use this exact title once: {title}.\n\n"
            f"{_item_details(new_item or {})}"
        )
    else:
        lines = []
        for piece in owned:
            notes = piece.get("notes") or ""
            note_bit = f" Notes: {notes}." if notes else ""
            lines.append(
                f"- {piece.get('name')} ({piece.get('category')}; "
                f"colors: {', '.join(piece.get('colors') or [])}; "
                f"style: {', '.join(piece.get('style_tags') or [])}).{note_bit}"
            )
        prompt = (
            "Suggest one or two outfits that pair this new thrift item with "
            "pieces the user already owns. Name those pieces with the exact "
            f"names from the wardrobe list. Use this exact title once: {title}.\n\n"
            f"New item:\n{_item_details(new_item or {})}\n\n"
            "Wardrobe:\n" + "\n".join(lines)
        )
    system = (
        "You style secondhand clothes. Reply in 2 to 4 sentences. "
        "Only name wardrobe pieces that appear in the list. "
        "If the wardrobe is empty, say the advice is general."
    )
    text = generate(prompt, system=system).strip()
    if text:
        return text
    return (
        f"Style {title} with dark jeans and clean sneakers. "
        "The wardrobe had nothing to pair it with, so this is general advice."
    )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Write a short caption someone would actually post about the find.

    This calls the model too.

    Args:
        outfit:   the outfit suggestion string from suggest_outfit().
        new_item: the listing dict for the item.

    Returns:
        A two-to-four sentence caption.
        If `outfit` is empty or whitespace, return a descriptive message rather
        than raising.

    The caption should read like a real post rather than a product description,
    mention the item and its price and platform once each, and be specific about
    the vibe.

    It should also come out **differently for different inputs**. If you run
    this three times on the same item and get three word-for-word identical
    strings, it's one of two things, and both are near the top of `config.py`:

        • CACHE_ENABLED — the adapter handed back an answer it already had
        • TEMPERATURE   — at 0.0 the model gives the same words every time

    TODO:
        1. Guard against an empty or whitespace-only `outfit`.
        2. Build a prompt with the item details and the outfit.
        3. Call generate() and return the response.

    Test it from a terminal before you move on:
        python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
    """
    title = (new_item or {}).get("title") or "this piece"
    price = (new_item or {}).get("price")
    platform = (new_item or {}).get("platform") or "the listing"
    if not outfit or not str(outfit).strip():
        return (
            f"No caption for {title} (${price} on {platform}): "
            "there was no outfit suggestion to write from."
        )
    brand = (new_item or {}).get("brand")
    brand_line = (
        f"Brand: {brand}."
        if brand
        else "No brand is listed. Do not invent one."
    )
    prompt = (
        "Write a caption someone would actually post about this thrift find. "
        "Use 2 to 4 sentences. Mention the title, the price, and the platform "
        "once each. Be specific about the vibe. No hashtags. "
        "Do not write it like a product listing.\n\n"
        f"{_item_details(new_item or {})}\n"
        f"{brand_line}\n"
        f"Outfit idea:\n{str(outfit).strip()}"
    )
    system = (
        "You write short social captions for secondhand outfits. "
        "Plain sentences, no hashtags, 2 to 4 sentences."
    )
    text = generate(prompt, system=system).strip()
    if text:
        return text
    return f"Found {title} for ${price} on {platform}."

# FitFindr

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first** — setup, every
> command, and what to do when something breaks.
>
> Once `python test.py` passes:
>
> ```bash
> python app.py listings --full -n 6      # read the data (Milestone 1)
> python app.py fields                    # what you can filter on
> python app.py ask 'vintage graphic tee under $30'
> ```
>
> All three tools are stubs, so that last command will do nothing useful yet.
> That's the starting position.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     HOW TO USE THIS FILE

     This is your submission. Fill each section in as you finish the milestone
     it belongs to — don't leave it all to the end.

     Unit 3 asks for the first five sections. Unit 4 adds the five below them.
     Leave the unit 4 sections alone until then; they're here so you know
     what's coming.

     Everything is pasted as TEXT. No screenshots, no images, no video links.
     A typed block of output gets full credit; a picture of the same output
     gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 3 — THE BUILD ═══════════════════════ -->

## What This Does

A user asks for a thrift find in plain language, for example "a vintage graphic tee under $30, size M". FitFindr pulls a description, an optional size, and an optional price ceiling out of that sentence and searches the listings file. If something matches, it takes the first result, suggests how that item goes with the saved wardrobe, and writes a short caption someone could post. If the search comes back empty, it stops and names what to change: the description, the size, or the price.

---

## Tool Inventory

<!-- Four lines per tool. This is worth 2 points and it's the single most
     common place students lose them.

     "Returns a list" earns NOTHING. The description has to say what is IN
     the list.

     The empty case isn't optional either — it's the thing your loop branches
     on, and if you don't decide it here you'll discover it as a crash in
     Milestone 5. -->

### `search_listings`

- **What it does:** Filters the listings file by size and price, then ranks what remains by keyword overlap with the description.
- **Inputs:** `description` (str), `size` (str or None), `max_price` (float or None).
- **Returns:** A list of listing dicts, best match first, at most `config.SEARCH_RESULT_LIMIT` (10). Each dict has `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`. A word in the title counts more than the same word in the description. Ties break toward the lower price. Size matching is whole tokens: `M` matches `S/M`, `S` does not match `US 9`, and `L` does not match `XL`.
- **When it has nothing:** An empty list. Not `None`, and it does not raise.

### `suggest_outfit`

- **What it does:** Asks the model for one or two outfits that pair a new listing with the user's wardrobe.
- **Inputs:** `new_item` (dict, one listing), `wardrobe` (dict with an `items` key holding a list of wardrobe item dicts).
- **Returns:** A non-empty string of outfit advice. With items in the wardrobe, the prompt tells the model to name those pieces. With an empty `items` list, the prompt asks for general styling advice instead.
- **When it has nothing:** If the model returns a blank string, the function returns a fixed sentence of general advice naming the item. It does not return `""` and it does not raise. An empty wardrobe is not the empty case — that path still returns advice.

### `create_fit_card`

- **What it does:** Asks the model for a 2-to-4 sentence caption about the find, naming the title, price, and platform once each.
- **Inputs:** `outfit` (str, the suggestion from `suggest_outfit`), `new_item` (dict, the listing).
- **Returns:** A non-empty string caption.
- **When it has nothing:** If `outfit` is empty or only whitespace, it does not call the model. It returns a sentence that names the title, price, and platform and says there was no outfit suggestion to write from.

---

## Planning Loop

<!-- Your branch rule, stated as a rule — the condition AND both paths — plus
     the file and function that holds it.

     Like this:
       "If search_listings returns an empty list, put a message in the session
        and stop. Otherwise take the first result and go to suggest_outfit."
        — agent.py::run_agent

     The grader checks your code against what you claim here, so the file and
     function have to be real. -->

**Branch rule:** If `search_listings` returns an empty list, put a message in `session["error"]` that names the description, size, and price that were searched and what to change, then return. Do not call `suggest_outfit`. Otherwise take `session["search_results"][0]`, store it on `session["selected_item"]`, and go to `suggest_outfit`.

**Where it lives:** `agent.py::run_agent`

**How the query is parsed:** Regex and string splitting in `agent.py::parse_query`, not a model call. `under $30` becomes `max_price` (float). `size M`, `size medium`, or `size 8` becomes `size` (str). The remaining words, minus filler like "looking" and "for", become `description` (str).

**What moves through the session:** `parsed` is written first and then read back for the search call. `search_results` is written next. On a non-empty list, `selected_item` is set from `search_results[0]` and `passed_to_suggest_outfit_id` is set from that item's `id`. `suggest_outfit` is called with `selected_item` and `wardrobe` from the session, and its string is stored on `outfit_suggestion`. `create_fit_card` is called with `outfit_suggestion` and `selected_item`, and its string is stored on `fit_card`. On the empty path, `fit_card`, `outfit_suggestion`, and `passed_to_suggest_outfit_id` stay `None`.

---

## Sample Run

<!-- Two things go here.

     1. One FULL query and its output, pasted as text.
     2. Your three per-tool terminal tests — the command and what it printed. -->

**One full query**

An impossible query, so this path does not call the model. `fit_card` stays unset because the loop returns first.

```
$ python app.py ask 'designer ballgown size XXS under $5'

  Nothing in the listings matched 'designer ballgown', size XXS, at or under $5. Try a broader description (search matches words in the title, description, and style tags); or a different size, or leave the size off; or a higher price ceiling.

0 model calls this session
```

**The three tools, tested one at a time**

```
$ python -c "from tools import search_listings; hits = search_listings('graphic tee', max_price=30); print(len(hits));
[print(h['id'], h['price'], h['size'], h['platform'], h['title']) for h in hits]"

6
lst_006 24.0 L depop Graphic Tee — 2003 Tour Bootleg Style
lst_002 18.0 S/M depop Y2K Baby Tee — Butterfly Print
lst_033 19.0 L depop Vintage Band Tee — Faded Grey
lst_015 26.0 L depop Vintage Graphic Hoodie — Faded Black
lst_017 15.0 S/M depop Mesh Long-Sleeve Top — Black
lst_011 27.0 W29 poshmark Low-Rise Cargo Pants — Khaki
```

`suggest_outfit` and `create_fit_card` call the model through `generate()`. They need `GEMINI_API_KEY` in `.env` (the same key as unit 1). That key is not on this machine yet, so those two commands have not been run. The commands to run once the key is in `.env`:

```
$ python -c "from tools import suggest_outfit; from utils.data_loader import get_example_wardrobe, load_listings; print(suggest_outfit(load_listings()[0], get_example_wardrobe()))"
```

```
$ python -c "from tools import create_fit_card; from utils.data_loader import load_listings; print(create_fit_card('jeans and white sneakers', load_listings()[0]))"
```

The empty-outfit case does not call the model:

```
$ python -c "from tools import create_fit_card; print(create_fit_card('   ', {'title': 'Test Tee', 'price': 12, 'platform': 'depop'}))"

No caption for Test Tee ($12 on depop): there was no outfit suggestion to write from.
```

---

## How I Used AI

<!-- Two specific moments. What you asked, what came back, what you changed.

     "I used Claude to help me code" is not enough.

     "I gave Claude my search_listings spec. It returned None on no match
     instead of an empty list, so I changed it" is the level we want. -->

**Moment 1**

- *What I asked for:* A `search_listings` size filter, with the note that `"s" in "us 9"` and `"l" in "xl"` are both true.
- *What came back:* A first version that checked whether the requested size was a substring of the listing size.
- *What I changed:* Whole-token matching. `M` still matches `S/M`. `S` does not match `US 9`. `L` does not match `XL`. `8` matches `US 8` and does not match `US 8.5`.

**Moment 2**

- *What I asked for:* The message to show when a search comes back empty.
- *What came back:* A short line that only said nothing was found.
- *What I changed:* The message now names the description, the size, and the price ceiling that were used, and it says which of those to change. "No results" is not that message.

<!-- ═══════════════════════ UNIT 4 — THE TEST ═══════════════════════

     Don't fill these in during unit 3.
     ═══════════════════════════════════════════════════════════════════ -->

---

## Run Log — Before

<!-- Five criteria, five tries each, in this exact format.

     Five, because your criteria are written out of five. Mark each try PASS
     or FAIL, count the passes, and read that count against your target — a
     row targeting 4 of 5 with three PASS cells is MISSED (3/5).

     `python run_eval.py --label before` runs everything and writes the table
     into results/. Paste it here and fill in the verdicts. -->

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Real output from one try**, pasted as text, naming the file and function
that produced it:

```

```

---

## Verdicts and Diagnoses

<!-- MET or MISSED per criterion against LAST UNIT's target, plus a sentence on
     how you decided.

     Then, for every miss: which of the four places it happened — a tool, the
     loop's branch, the session, or the model's output — AND the mechanism.

     Not a diagnosis:  "The fit card was bad."
     A diagnosis:      "The fit card criterion missed on 2 of 5 items. Both had
                        an empty brand field. My prompt puts the brand in the
                        first sentence, so the card opened with a blank and read
                        like a fragment. The tool worked; the prompt assumed a
                        field that isn't always there."

     Look for a pattern. Three misses on the same tool is one problem, not
     three. -->

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 |  |  |  |  |
| 2 |  |  |  |  |
| 3 |  |  |  |  |
| 4 |  |  |  |  |
| 5 |  |  |  |  |

**Diagnoses**



---

## Loop Trace

<!-- One full run, printed step by step, with the MCP call visible in it.

     `python app.py ask '...' --trace` once you've added the trace.step()
     calls in Milestone 2.

     Worth pasting BOTH the happy path and the empty-search path. The empty
     one should be visibly shorter, because it stops. If your two traces are
     the same length, your branch isn't working — and this is the fastest way
     anyone will ever find that out. -->

**Happy path**

```

```

**Empty search**

```

```

**On the MCP move:** <!-- what changed in your code, and whether anything
behaved differently afterwards. If the rewire didn't work, say exactly where it
broke — the error text and the last thing that worked. That earns the point in
full. -->



---

## The Improvement

<!-- What you changed, why your diagnosis pointed at it, and the after-run in
     the same table format. One change, measured properly.

     `python run_eval.py --label after` -->

**What I changed:**

**Which failure it was meant to fix:**

### Run Log — After

| Criterion | Target | Try 1 | Try 2 | Try 3 | Try 4 | Try 5 | Verdict |
|---|---|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |  |  |
| 2.  |  |  |  |  |  |  |  |
| 3.  |  |  |  |  |  |  |  |
| 4.  |  |  |  |  |  |  |  |
| 5.  |  |  |  |  |  |  |  |

**Did it help, and how do I know:**

<!-- If it made things worse, say that. Honestly reported, that earns full
     credit and is more interesting than one that worked. -->



---

## What's Still Broken

<!-- For each criterion still missed: what you'd do, and why you stopped where
     you did. "I ran out of time" is fine if it's true. Pretending nothing is
     left is not. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 3

       [ ] criteria.md has five numbered criteria, each with a target
       [ ] Each criterion has a reason underneath it
       [ ] All five unit 3 sections above have real content
       [ ] Tool Inventory: all three tools, inputs WITH TYPES, a specific
           return value, and the empty case
       [ ] Planning Loop names the branch rule and agent.py::run_agent
       [ ] Sample Run: one full query plus the three per-tool tests, as text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN, you submit the same one
           next unit

     SUBMISSION CHECKLIST — unit 4

       [ ] mcp_server.py exists with one tool registered
           (or a written record of exactly where the rewire broke)
       [ ] Run Log — Before, five criteria, five tries each
       [ ] Real output pasted underneath, naming file and function
       [ ] A verdict on every criterion
       [ ] A diagnosis for every miss, naming a place AND a mechanism
       [ ] Loop Trace, with the MCP call visible in it
       [ ] All three failure modes triggered and handled
       [ ] One improvement, with Run Log — After in the same format
       [ ] What's Still Broken
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository. Your commit history is what
     shows your criteria existed before your results did.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**

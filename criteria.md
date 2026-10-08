# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
I picked 4 of 5 because `search_listings` is a keyword overlap score, not a
synonym search. A query that says "shirt" instead of "tee", or a vibe word
that never appears in the title, style tags, or description, scores zero and
the loop stops even when a person would call it a match. 5 of 5 would assume
every phrasing shares the listing's words.

---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
5 of 5 is the right bar here because this path never calls the model. The
branch in `agent.py::run_agent` checks whether `search_listings` returned an
empty list, writes `session["error"]`, and returns before `suggest_outfit`.
The same impossible query cannot take the other path unless the filter itself
changes. Criterion 1 can miss because of wording. This one cannot.

---

## 3. The item search picked is the item the next tool received

Given a query that matches at least one listing, `session["selected_item"]["id"]`,
`session["search_results"][0]["id"]`, and `session["passed_to_suggest_outfit_id"]`
are the same id — in 5 of 5 tries.

**Why this target:**
5 of 5, because those three values are copied in `run_agent` from the session.
No model writes them, so a miss is a wiring bug and should not happen on any
try. I did not require the outfit paragraph to quote the title. The model can
shorten a title, and that would fail a state check for a writing reason.



---

## 4. The fit card names the price and the platform

Given 5 fit cards for 5 different listings, at least 4 of the 5 mention that
listing's price as a number and its platform name, and are 2 to 4 sentences.

**Why this target:**
Not 5 of 5, because `create_fit_card` calls the model at temperature 0.9, so
one card can drop the platform or run long. A looser bar like "sounds like a
caption" is not something another person could score the same way twice. Price,
platform, and sentence count are. Wording can change between runs. Those three
facts should not.



---

## 5. A price ceiling is never broken

When the query includes a price ceiling, every listing left in
`session["search_results"]` has `price` less than or equal to that ceiling —
5 of 5 tries.

**Why this target:**
5 of 5, because the ceiling is a numeric comparison in `search_listings`,
before any model call. One listing over the ceiling is a broken filter, not a
close call. I did not also require the top result to be the cheapest match.
The sort is by keyword score, so a stronger keyword match can cost more and
still be under the ceiling.



---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->

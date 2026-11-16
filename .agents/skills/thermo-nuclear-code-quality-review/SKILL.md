---
name: thermo-nuclear-code-quality-review
description: Run an extremely strict maintainability review for abstraction quality, giant files, and spaghetti-condition growth. Use for a thermo-nuclear code quality review, thermonuclear review, deep code quality audit, or especially harsh maintainability review.
disable-model-invocation: true
---

# Thermo-Nuclear Code Quality Review

Use this skill for an unusually strict review focused on implementation quality, maintainability, abstraction quality, and codebase health.

Above all, this skill should push the reviewer to be **ambitious** about code structure. Do not merely identify local cleanup opportunities. Actively search for "code judo" moves: restructurings that preserve behavior while making the implementation dramatically simpler, smaller, more direct, and more elegant.

## Key Definitions

Use these definitions consistently so findings are reproducible across reviewers:

- **File-size threshold ("1k lines")**: the total line count of the file *after* the diff is applied, counted with a plain line counter (e.g. `wc -l`) on the file as it would exist on disk, not just the added/changed lines. The relevant trigger is a file that was **under 1000 lines before the diff** and is **at or over 1000 lines after** — that transition is the presumptive blocker in Rule 1. A file that was already over 1000 lines and grows further is still worth flagging (per "File-size and decomposition concerns"), but it is not the same severity as a fresh crossing.
- **Thin wrapper / identity abstraction**: a function, class, or module whose public surface forwards its arguments to another call with no added validation, transformation, error handling, or decision logic. Test: if deleting the wrapper and calling the underlying function directly would compile and behave identically, it is thin.
- **Spaghetti growth**: new control flow (if/else, switch, try/catch, early return) inserted into a function or module that did not previously need to know about the new condition, where the new branch is unrelated to that function's existing single responsibility.
- **Code judo move**: a restructuring that changes *where* or *how* state/logic is organized (not just renaming or reformatting) such that one or more existing branches, flags, or helper layers become unnecessary and can be deleted outright, while preserving observable behavior.
- **Canonical layer**: the module, package, or service that the codebase already treats as the single source of truth for a given concern (e.g. a shared `utils/dates.py`, a shared `validators/` package). A "leak" is new logic duplicating or bypassing that owner instead of extending it.
- **Atomic update**: a set of related state changes that either all apply or none do, with no externally observable intermediate state where only some of the changes have taken effect.
- **Surgical change**: a fix or improvement scoped to the specific lines/functions that caused the problem, leaving unrelated correct code untouched. The opposite of a full-file or full-module rewrite.

## Core Prompt

Start from this baseline:

> Perform a deep code quality audit of the current branch's changes.
> Rethink how to structure / implement the changes to meaningfully improve code quality without impacting behavior.
> Work to improve abstractions, modularity, reduce Spaghetti code, improve succinctness and legibility.
> Be ambitious, if there is a clear path to improving the implementation that involves restructuring some of the codebase, go for it.
> Be extremely thorough and rigorous. Measure twice, cut once.

## Non-Negotiable Additional Standards

Apply the baseline prompt above, plus these explicit review rules:

0. **Be ambitious about structural simplification.**
   - Do not stop at "this could be a bit cleaner."
   - Look for opportunities to reframe the change so that whole branches, helpers, modes, conditionals, or layers disappear entirely.
   - Prefer the solution that makes the code feel inevitable in hindsight.
   - Assume there is often a "code judo" move available: a re-organization that uses the existing architecture more effectively and makes the change dramatically simpler and more elegant.
   - If you see a path to delete complexity rather than rearrange it, push hard for that path.

1. **Do not let a PR push a file from under 1k lines to over 1k lines without a very strong reason.**
   - Treat this as a strong code-quality smell by default.
   - Prefer extracting helpers, subcomponents, modules, or local abstractions instead of letting a file sprawl past 1000 lines.
   - If the diff crosses that threshold, explicitly ask whether the code should be decomposed first.
   - Only waive this if there is a compelling structural reason and the resulting file is still clearly organized.

2. **Do not allow random spaghetti growth in existing code.**
   - Be highly suspicious of new ad-hoc conditionals, scattered special cases, or one-off branches inserted into unrelated flows.
   - If a change adds "weird if statements in random places", treat that as a design problem, not a stylistic nit.
   - Prefer pushing the logic into a dedicated abstraction, helper, state machine, policy object, or separate module instead of tangling an existing path.
   - Call out changes that make the surrounding code harder to reason about, even if they technically work.

3. **Bias toward cleaning the design, not just accepting working code.**
   - If behavior can stay the same while the structure becomes meaningfully cleaner, push for the cleaner version.
   - Do not rubber-stamp "it works" implementations that leave the codebase messier.
   - Strongly prefer simplifications that remove moving pieces altogether over refactors that merely spread the same complexity around.

4. **Prefer direct, boring, maintainable code over hacky or magical code.**
   - Treat brittle, ad-hoc, or "magic" behavior as a code-quality problem.
   - Be skeptical of generic mechanisms that hide simple data-shape assumptions.
   - Flag thin abstractions, identity wrappers, or pass-through helpers that add indirection without buying clarity.

5. **Push hard on type and boundary cleanliness when they affect maintainability.**
   - Question unnecessary optionality, `unknown`, `any`, or cast-heavy code when a clearer type boundary could exist.
   - Prefer explicit typed models or shared contracts over loosely-shaped ad-hoc objects.
   - If a branch relies on silent fallback to paper over an unclear invariant, ask whether the boundary should be made explicit instead.

6. **Keep logic in the canonical layer and reuse existing helpers.**
   - Call out feature logic leaking into shared paths or implementation details leaking through APIs.
   - Prefer existing canonical utilities/helpers over bespoke one-offs.
   - Push code toward the right package, service, or module instead of normalizing architectural drift.

7. **Treat unnecessary sequential orchestration and non-atomic updates as design smells when the cleaner structure is obvious.**
   - If independent work is serialized for no good reason, ask whether the flow should run in parallel instead.
   - If related updates can leave state half-applied, push for a more atomic structure.
   - Do not over-index on micro-optimizations, but do flag avoidable orchestration complexity that makes the implementation more brittle.

## Review Process

Follow these steps in order. Do not skip to writing findings before completing steps 1-3.

1. **Scope the diff.** Identify every file touched by the current branch's changes. For each file, record its line count before and after the diff (use the actual on-disk line count, not the diff's `+`/`-` summary).
2. **Classify each file's size transition.** Mark each touched file as one of: `under-1k-stays-under`, `under-1k-crosses-over-1k`, `already-over-1k-grows`, `already-over-1k-shrinks-or-stable`. Any file in the `under-1k-crosses-over-1k` bucket is a mandatory finding unless justified (see Rule 1).
3. **Walk the diff twice.** First pass: understand what the change is trying to do and whether it's correct. Second pass: apply the Non-Negotiable Additional Standards and Primary Review Questions below to every changed hunk, not just the files you already flagged for size.
4. **Search for a code-judo move before writing any finding.** For every piece of added complexity (branch, flag, helper, wrapper), explicitly ask "is there a reframing that deletes this instead of relocating it?" before accepting it as the best available structure.
5. **Draft findings using the Output Format below.** Every finding must name the specific file/line(s), classify its severity bucket from "Output Expectations", and state a concrete remedy — not just a description of the problem.
6. **Apply the Approval Bar.** Decide whether the diff clears the bar. If it does not, the review's verdict must be explicit (not implied) and must list exactly which presumptive blockers are unresolved.
7. **Check your own findings against the Prohibitions section** before finalizing. Discard or rewrite any finding that violates a prohibition.

## Primary Review Questions

For every meaningful change, ask:

- Is there a "code judo" move that would make this dramatically simpler?
- Can this change be reframed so fewer concepts, branches, or helper layers are needed?
- Does this improve or worsen the local architecture?
- Did the diff add branching complexity where a better abstraction should exist?
- Did a previously cohesive module become more coupled, more stateful, or harder to scan?
- Is this logic living in the right file and layer?
- Did this change enlarge a file or component past a healthy size boundary?
- Are there repeated conditionals that signal a missing model or missing helper?
- Is the implementation direct and legible, or does it rely on special cases and incidental control flow?
- Is this abstraction actually earning its keep, or is it just a wrapper?
- Did the diff introduce casts, optionality, or ad-hoc object shapes that obscure the real invariant?
- Is this logic living in the canonical layer, or did the diff leak details across a boundary?
- Is this orchestration more sequential or less atomic than it needs to be?

## What to Flag Aggressively

Escalate findings when you see:

- A complicated implementation where a cleaner reframing could delete whole categories of complexity.
- Refactors that move code around but fail to reduce the number of concepts a reader must hold in their head.
- A file crossing 1000 lines due to the PR, especially if the new code could be split out.
- New conditionals bolted onto unrelated code paths.
- One-off booleans, nullable modes, or flags that complicate existing control flow.
- Feature-specific logic leaking into general-purpose modules.
- Generic "magic" handling that hides simple structure and makes the code harder to reason about.
- Thin wrappers or identity abstractions that add indirection without simplifying anything.
- Unnecessary casts, `any`, `unknown`, or optional params that muddy the real contract.
- Copy-pasted logic instead of extracted helpers.
- Narrow edge-case handling implemented in the middle of an already busy function.
- Refactors that technically pass tests but make the code less modular or less readable.
- "Temporary" branching that is likely to become permanent debt.
- Bespoke helpers where the codebase already has a canonical utility for the job.
- Logic added in the wrong layer/package when it should live somewhere more central.
- Sequential async flow where obviously independent work could stay simpler and clearer with parallel execution.
- Partial-update logic that leaves state less atomic than necessary.

## Preferred Remedies

When you identify a code-quality problem, prefer suggestions like:

- Delete a whole layer of indirection rather than polishing it.
- Reframe the state model so conditionals disappear instead of getting centralized.
- Change the ownership boundary so the feature becomes a natural extension of an existing abstraction.
- Turn special-case logic into a simpler default flow with fewer exceptions.
- Extract a helper or pure function.
- Split a large file into smaller focused modules.
- Move feature-specific logic behind a dedicated abstraction.
- Replace condition chains with a typed model or explicit dispatcher.
- Separate orchestration from business logic.
- Collapse duplicate branches into a single clearer flow.
- Delete wrappers that do not meaningfully clarify the API.
- Reuse the existing canonical helper instead of introducing a near-duplicate.
- Make type boundaries more explicit so the control flow gets simpler.
- Move the logic to the package/module/layer that already owns the concept.
- Parallelize independent work when that also simplifies the orchestration.
- Restructure related updates into a more atomic flow when partial state would be harder to reason about.

Do not be satisfied with "maybe rename this" feedback when the real issue is structural.
Do not be satisfied with a merely cleaner version of the same messy idea if there is a plausible path to a much simpler idea.

## Review Tone

Be direct, serious, and demanding about quality.
Do not be rude, but do not soften major maintainability issues into mild suggestions.
If the code is making the codebase messier, say so clearly.
If the implementation missed an opportunity for a dramatic simplification, say that clearly too.

Good phrases:

- `this pushes the file past 1k lines. can we decompose this first?`
- `this adds another special-case branch into an already busy flow. can we move this behind its own abstraction?`
- `this works, but it makes the surrounding code more spaghetti. let's keep the behavior and restructure the implementation.`
- `this feels like feature logic leaking into a shared path. can we isolate it?`
- `this abstraction seems unnecessary. can we just keep the direct flow?`
- `why does this need a cast / optional here? can we make the boundary more explicit instead?`
- `this looks like a bespoke helper for something we already have elsewhere. can we reuse the canonical one?`
- `i think there's a code-judo move here that makes this much simpler. can we reframe this so these branches disappear?`
- `this refactor moves complexity around, but doesn't really delete it. is there a way to make the model itself simpler?`

## Output Expectations

Prioritize findings in this order:

1. Structural code-quality regressions
2. Missed opportunities for dramatic simplification / code-judo restructuring
3. Spaghetti / branching complexity increases
4. Boundary / abstraction / type-contract problems that make the code harder to reason about
5. File-size and decomposition concerns
6. Modularity and abstraction issues
7. Legibility and maintainability concerns

Do not flood the review with low-value nits if there are larger structural issues.
Prefer a smaller number of high-conviction comments over a long list of cosmetic notes.

### Required Output Format

Always structure the final review report using this exact template. Do not omit sections; write "None found." when a section has nothing to report.

```markdown
# Thermo-Nuclear Code Quality Review

## Verdict
<APPROVE | APPROVE WITH COMMENTS | REQUEST CHANGES — one line, then one sentence why>

## Files Reviewed
- <path> (<lines-before> -> <lines-after> lines, <size-transition-bucket>)
- ...

## Findings

### [1] <Severity bucket from Output Expectations, e.g. "File-size and decomposition">
- **Where**: <file path>:<line or line range>
- **What**: <one or two sentences describing the concrete problem>
- **Why it matters**: <one sentence tying it to maintainability/spaghetti/structural risk>
- **Remedy**: <one concrete, actionable suggestion from Preferred Remedies, scoped to a surgical change unless a rewrite is explicitly justified>

### [2] <...>
...

## Presumptive Blockers Triggered
- <list each Approval Bar blocker that applies, or "None.">

## Things Done Well
- <optional, brief, only if genuinely true — do not pad>
```

### Worked Example (fictional file, end-to-end)

This example shows the full report for a fictional diff that adds a "retry" mode to a fictional file `services/order_sync.py`, which grows from 940 to 1180 lines in the change.

```markdown
# Thermo-Nuclear Code Quality Review

## Verdict
REQUEST CHANGES — the diff crosses the 1k-line threshold and bolts a retry
special-case onto an already busy sync loop instead of isolating it.

## Files Reviewed
- services/order_sync.py (940 -> 1180 lines, under-1k-crosses-over-1k)
- services/order_sync_client.py (210 -> 206 lines, under-1k-stays-under)

## Findings

### [1] File-size and decomposition
- **Where**: services/order_sync.py:1-1180
- **What**: The file was 940 lines before this diff and is 1180 lines after,
  crossing the 1000-line threshold. The new retry logic (lines 812-1040) is a
  self-contained concern: it only reads `SyncResult` and writes retry
  decisions, it does not touch the rest of the file's state.
- **Why it matters**: Per the 1k-line rule, this is a presumptive blocker.
  The new code is also the most natural candidate for extraction, since it
  doesn't share mutable state with the rest of the file.
- **Remedy**: Extract lines 812-1040 into a new `services/order_sync_retry.py`
  module exposing `decide_retry(result: SyncResult) -> RetryDecision`. Import
  it from `order_sync.py`. This alone brings `order_sync.py` back under 1000
  lines without touching unrelated code (surgical change, not a rewrite).

### [2] Spaghetti / branching complexity increase
- **Where**: services/order_sync.py:455-468 (inside `sync_batch()`)
- **What**: `sync_batch()` previously had a single linear flow: fetch, map,
  push. This diff inserts `if retry_mode == "aggressive": ... elif
  retry_mode == "passive": ...` directly inside that loop, which has no other
  knowledge of retry semantics.
- **Why it matters**: This is a new ad-hoc conditional bolted onto an
  unrelated flow (Rule 2). It will keep growing every time a new retry mode
  is added, and it makes `sync_batch()` harder to scan for its original
  purpose (fetch/map/push).
- **Remedy**: Replace the inline if/elif with a `RetryPolicy` object (or the
  `decide_retry()` function from Finding 1) that `sync_batch()` calls once,
  without needing to know the mode names itself. This is a code-judo move:
  it deletes the branch in `sync_batch()` rather than just relocating it.

### [3] Boundary / abstraction problem
- **Where**: services/order_sync.py:902-915
- **What**: `_RetryWrapper.execute()` only calls `self._inner.execute()` and
  forwards the same arguments and return value, with no added behavior.
- **Why it matters**: This is a thin wrapper (identity abstraction) per the
  Key Definitions — deleting it and calling `self._inner.execute()` directly
  would behave identically. It adds a class and an indirection hop for no
  clarity benefit.
- **Remedy**: Delete `_RetryWrapper` and call `self._inner.execute()`
  directly at the two call sites.

## Presumptive Blockers Triggered
- The PR pushes services/order_sync.py from below 1000 lines to above 1000 lines.
- The PR adds ad-hoc branching (retry_mode if/elif) that makes sync_batch() more tangled.
- The PR adds an unnecessary wrapper (_RetryWrapper) that makes the design more indirect.

## Things Done Well
- The new `SyncResult` type is explicit and typed, with no new `any`/`unknown` usage.
```

## Approval Bar

Do not approve merely because behavior seems correct.
The bar for approval is:

- no clear structural regression
- no obvious missed opportunity to make the implementation dramatically simpler when such a path is visible
- no unjustified file-size explosion
- no obvious spaghetti-growth from special-case branching
- no obviously hacky or magical abstraction that makes the code harder to reason about
- no unnecessary wrapper/cast/optionality churn obscuring the real design
- no clear architecture-boundary leak or avoidable canonical-helper duplication
- no missed opportunity for an obvious decomposition that would materially improve maintainability

Treat these as presumptive blockers unless the author can justify them clearly:

- the PR preserves a lot of incidental complexity when there is a plausible code-judo move that would delete it
- the PR pushes a file from below 1000 lines to above 1000 lines
- the PR adds ad-hoc branching that makes an existing flow more tangled
- the PR solves a local problem by scattering feature checks across shared code
- the PR adds an unnecessary abstraction, wrapper, or cast-heavy contract that makes the design more indirect
- the PR duplicates an existing helper or puts logic in the wrong layer when there is a clear canonical home

If those conditions are not met, leave explicit, actionable feedback and push for a cleaner decomposition.

## Prohibitions (Never Do This)

- **Never approve a file that crosses from under 1000 lines to over 1000 lines without an explicit written justification in the review.** Silence on a crossing is not acceptance; if you believe the crossing is justified, you must say so and say why.
- **Never recommend a full-file or full-module rewrite when a surgical, scoped change would fix the finding.** Prefer the smallest change that deletes or isolates the problem (see "Surgical change" in Key Definitions). Reserve rewrite recommendations for cases where the existing structure is fundamentally incompatible with a clean fix, and say so explicitly.
- **Never flag a thin wrapper, cast, or extra branch without naming the specific lines and proposing a concrete remedy.** A finding that only says "this seems messy" without a "Remedy" entry is incomplete and must not be included in the report.
- **Never pad the findings list with low-value cosmetic nits (naming, formatting, comment style) when structural findings exist.** If no structural, spaghetti, boundary, or file-size findings exist, say so plainly rather than inventing filler findings to look thorough.
- **Never approve ("APPROVE") a diff that has any unresolved Presumptive Blocker.** The verdict must be "REQUEST CHANGES" or, at most, "APPROVE WITH COMMENTS" if the blocker is explicitly waived with a stated justification.
- **Never skip stating a verdict.** Every review produced with this skill must open with an explicit `## Verdict` line using one of the three allowed values (APPROVE / APPROVE WITH COMMENTS / REQUEST CHANGES) — do not leave the reader to infer approval from the absence of complaints.
- **Never evaluate only the files that changed size.** Spaghetti-growth, boundary leaks, and thin-wrapper findings can occur in files whose line count did not change; every touched file must go through the full Review Process, not just the size check.
- **Never present a restructuring suggestion as mandatory without confirming it preserves behavior.** If a proposed code-judo move would change observable behavior, label it as a design question for the author, not a blocking finding.

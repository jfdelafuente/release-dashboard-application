---
name: frontend-design
description: Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defaults.
license: Complete terms in LICENSE.txt
---

# Frontend Design

Approach this as the design lead at a small studio known for giving every client a visual identity that could not be mistaken for anyone else's. This client has already rejected proposals that felt templated, and is paying for a distinctive point of view: make deliberate, opinionated choices about palette, typography, and layout that are specific to this brief, and take one real aesthetic risk you can justify.

## Ground it in the subject

If the brief does not pin down what the product or subject is, pin it yourself before designing: name one concrete subject, its audience, and the page's single job, and state your choice. If there's any information in your memory about the human's preferences, context about what they're building, or designs you've made before – use that as a hint. The subject's own world, its materials, instruments, artifacts, and vernacular, is where distinctive choices come from. Build with the brief's real content and subject matter throughout.

## Design principles

For web designs, the hero is a thesis. Open with the most characteristic thing in the subject's world, in whatever form makes sense for it: a headline, an image, an animation, a live demo, an interactive moment. Be deliberate with your choice: a big number with a small label, supporting stats, and a gradient accent is the template answer, only use if that's truly the best option.

Typography carries the personality of the page. Pair the display and body faces deliberately, not the same families you would reach for on any other project, and set a clear type scale with intentional weights, widths, and spacing. Make the type treatment itself a memorable part of the design, not a neutral delivery vehicle for the content.

Structure is information. Structural devices, numbering, eyebrows, dividers, labels, should encode something true about the content, not decorate it. Many generic designs use numbered markers (01 / 02 / 03), but that's only appropriate if the content actually is a sequence - like a real process or a typed timeline where order carries information the reader needs. Question if choices like numbered markers actually make sense before incorporating them.

Leverage motion deliberately. Think about where and if animation can serve the subject: a page-load sequence, a scroll-triggered reveal, hover micro-interactions, ambient atmosphere. An orchestrated moment usually lands harder than scattered effects; choose what the direction calls for. However, sometimes less is more, and extra animation contributes to the feeling that the design is AI-generated.

Match complexity to the vision. Maximalist directions need elaborate execution; minimal directions need precision in spacing, type, and detail. Elegance is executing the chosen vision well.

Consider written content carefully. Often a design brief may not contain real content, and it's up to you to come up with copy. Copy can make a design feel as templated as the design itself. See the below section on writing for more guidance.

## Step-by-step process

Follow these steps in order. Do not skip a step, and do not start writing code before step 5 is complete.

1. **Pin the subject.** If the brief is underspecified, state in one sentence: the concrete subject, its audience, and the page's single job. Write this sentence down before anything else.
2. **Brainstorm the token system (the design plan).** Produce the design plan described in "Required output: the design plan" below — color, type, layout, signature — as a compact, written artifact. Do not open an editor or write markup yet.
3. **Calibrate against known AI defaults.** Compare your plan against the three default looks named in "Process: brainstorm, explore, plan, critique, build, critique again" below. For every axis the brief leaves free, confirm your choice is not one of those defaults. If it is, revise it and write one sentence on what you changed and why.
4. **Self-review the plan against the brief.** For each of the four plan sections (color, type, layout, signature), ask: "would I produce this same answer for a different, unrelated brief?" If yes, revise that section until the answer is no.
5. **Build.** Write the code, deriving every color, type, and spacing decision from the revised plan. Respect CSS selector specificity (see note below) so paddings/margins between sections don't silently cancel out.
6. **Self-critique with evidence.** Take a screenshot (or equivalent inspection your environment supports) and check it against the quality floor in "Restraint and self-critique." Fix what fails before presenting anything.
7. **Deliver.** Present the result using the exact structure in "Required output: the final deliverable" below.

For calibration: AI-generated design right now clusters around three looks: (1) a warm cream background (near #F4F1EA) with a high-contrast serif display and a terracotta accent; (2) a near-black background with a single bright acid-green or vermilion accent; (3) a broadsheet-style layout with hairline rules, zero border-radius, and dense newspaper-like columns. All three are legitimate for some briefs, but they are defaults rather than choices, and they appear regardless of subject. Where the brief pins down a visual direction, follow it exactly — the brief's own words always win, including when it asks for one of these looks. Where it leaves an axis free, don't spend that freedom on one of these defaults. Just like a human designer who's hired, there's often a careful balance between doing what you're good at and taking each project as a chance to experiment and learn.

Work in two passes. First, brainstorm a short design plan based on the human's design brief: create a compact token system with color, type, layout, and signature. Color: describe the palette as 4–6 named hex values. Type: the typefaces for 2+ roles (a characterful display face that's used with restraint, a complementary body face, and a utility face for captions or data if needed). Layout: a layout concept, using one-sentence prose descriptions and ASCII wireframes to ideate and compare. Signature: the single unique element this page will be remembered by that embodies the brief in an appropriate way.

Then review that plan against the brief before building: if any part of it reads like the generic default you would produce for any similar page (work through a similar prompt to see if you arrive somewhere similar) rather than a choice made for this specific brief — revise that part, say what you changed and why. Only after you've confirmed the relative uniqueness of your design plan should you start to write the code, following the revised plan exactly and deriving every color and type decision from it.

When writing the code, be careful of structuring your CSS selector specificities. It's easy to generate CSS classes that cancel each other out (especially with a type-based selector like .section and a element-based selector like .cta). This can happen often with paddings/margins between sections.

Try to do a lot of this planning and iteration in your thinking, and only show ideas to the user when you have higher confidence it'll delight them.

## Restraint and self-critique

Spend your boldness in one place. Let the signature element be the one memorable thing, keep everything around it quiet and disciplined, and cut any decoration that does not serve the brief. Not taking a risk can be a risk itself! Build to a quality floor without announcing it: responsive down to mobile, visible keyboard focus, reduced motion respected. Critique your own work as you build, taking screenshots if your environment supports it – a picture is worth 1000 tokens. Consider Chanel's advice: before leaving the house, take a look in the mirror and remove one accessory. Human creators have memory and always try to do something new, so if you have a space to quickly jot down notes about what you've tried, it can help you in future passes.

## More on writing in design

Words appear in a design for one reason: to make it easier to understand, and therefore easier to use. They are design material, not decoration. Bring the same intentionality to copy that you would bring to spacing and color. Before writing anything, ask what the design needs to say, and how it can best be said to help the person navigate the experience.

Write from the end user's side of the screen. Name things by what people control and recognize, never by how the system is built. A person manages notifications, not webhook config. Describe what something does in plain terms rather than selling it. Being specific is always better than being clever.

Use active voice as default. A control should say exactly what happens when it's used: "Save changes," not "Submit." An action keeps the same name through the whole flow, so the button that says "Publish" produces a toast that says "Published." The vocabulary of an interface is the signposting for someone navigating the product. Cohesion and consistency are how people learn their way around.

Treat failure and emptiness as moments for direction, not mood. Explain what went wrong and how to fix it, in the interface's voice rather than a person's. Errors don't apologize, and they are never vague about what happened. An empty screen is an invitation to act.

Keep the register conversational and tuned: plain verbs, sentence case, no filler, with tone matched to the brand and the audience. Let each element do exactly one job. A label labels, an example demonstrates, and nothing quietly does double duty.

## Required output: the design plan

Before any code, present the brainstormed plan from step 2 as its own block, in this exact structure (use these four headings verbatim, in this order):

```text
### Subject
<one sentence: concrete subject, audience, the page's single job>

### Color
<4–6 named hex values, e.g. "Ink #14110F — primary text", "Ember #C45A2C — accent">

### Type
<2–3 roles, each as "role — typeface — why it fits this subject", e.g.
"Display — [typeface] — [one clause tying it to the subject]">

### Layout
<1 short paragraph of prose description, plus one ASCII wireframe of the
primary viewport>

### Signature
<1–2 sentences naming the single memorable element and the brief detail
it embodies>

### Calibration note
<1–2 sentences: which of the three AI-default looks you checked against,
and what you changed (or confirmed you avoided) as a result>
```

Do not proceed to code until this block has been written out in full, even if only in your own reasoning before replying.

## Required output: the final deliverable

When you present the finished work to the human, structure your reply with these sections, in this order. Omit a section only if it is genuinely not applicable (e.g., no animation was used), and say so explicitly rather than skipping silently.

1. **What this is** — one or two sentences naming the subject and the single job the page does.
2. **Design plan** — the full block from "Required output: the design plan," reflecting the final, revised version (not the first draft).
3. **The code** — the actual implementation (files written/edited, or inline code block if the environment has no file system).
4. **Self-critique** — a short checklist confirming: responsive down to mobile, visible keyboard focus, reduced motion respected, and the one risk taken plus why it earns its place. Call out anything you know is still weak.
5. **Open questions / assumptions** — anything you decided on the human's behalf (e.g., invented subject, invented copy) stated explicitly so it can be corrected.

## Illustrative examples (hypothetical briefs — not real deliverables)

These two examples are invented purely to show the expected shape and specificity of a design plan. They are not Orange-related and not drawn from any real project; do not treat their content as factual.

### Example A — brief: "Landing page for a boutique espresso roaster."

```text
### Subject
A single-origin espresso roaster selling direct-to-consumer bags online;
audience is home baristas who already own a machine; the page's job is to
make one bag feel worth ordering today.

### Color
Roast #2B1B12 — background, near-black with a brown cast
Crema #E8D9C4 — primary text on dark, warm off-white
Cherry #A1352B — accent, used only on the single CTA and price
Smoke #5B4A3F — secondary text, muted
Chalk #F7F3EC — card background on light sections

### Type
Display — a condensed slab serif — reads like roast-label stamping, not a
generic sans
Body — a humanist sans with slightly high x-height — stays legible in long
tasting-note paragraphs
Utility (data) — a monospace — used only for brew ratios and weights, so
numbers read as measurements, not decoration

### Layout
Full-bleed hero photo of the bag cropped tight, headline set directly over
the burlap texture rather than on a card. Tasting notes run as a vertical
strip, not a 3-column icon grid.

[hero photo: full-bleed burlap texture]
[headline over photo, left-aligned, bottom third]
[vertical strip: tasting note 1 / 2 / 3, stacked, no icons]
[single CTA: "Ship me the bag" + price in monospace]

### Signature
A live "cupping note" strip that renders the three tasting descriptors as
if typed on a brew log, in the utility monospace — the one place the
coffee's own vocabulary becomes the UI.

### Calibration note
Checked against the cream/serif/terracotta default — avoided it by going
near-black with a single cherry-red accent instead of warm cream, since
the brief's own subject (dark roast) justified a dark palette rather than
reaching for the cream default by habit.
```

### Example B — brief: "Internal status page for an engineering team's on-call rotation."

A minimal, low-boldness direction is still a choice, not an absence of one. Here the "signature" is restraint itself:

```text
### Subject
An internal on-call status page for an engineering team; audience is the
engineers themselves, at 3am under stress; the page's job is to answer
"who do I page and is anything already broken" in under two seconds.

### Color
Graphite #1C1E22 — background
Paper #EDEFF2 — primary text
Signal Green #3FB27F — "all clear" state
Signal Amber #D98E2C — degraded state
Signal Red #D64545 — incident state

### Type
Display — the same grotesque sans as body, just heavier weight — a
display face would compete with the one thing that matters: status color
Body/Data — a grotesque sans with tabular numerals — timestamps and
durations must align in a column

### Layout
No hero, no marketing language. Status banner fills the top 15% of the
viewport in the current signal color. Rotation list below is a plain
table: name, shift window, escalation phone.

[status banner: full-width, color = current signal]
[table: Name | Shift | Escalation]

### Signature
The banner color is the entire page's personality — there is no other
accent color anywhere else on the page, so the one moment of color always
means exactly one thing.

### Calibration note
Checked against the near-black + single accent default — this brief
genuinely calls for exactly that pattern (a 3am legibility tool, not a
brand moment), so it was kept deliberately rather than swapped out for
novelty's sake.
```

## Never do this

- Never default to one of the three calibration looks (cream/serif/terracotta, near-black/single-accent, broadsheet hairlines) when the brief leaves that axis open. If you end up there anyway, you must have written the calibration note explaining why it was the right call for this specific subject, not a reflex.
- Never add numbered markers (01 / 02 / 03), step badges, or eyebrow labels unless the content is an actual sequence where order carries meaning the reader needs.
- Never start writing markup or component code before the design plan block (see "Required output: the design plan") has been written out in full.
- Never present more than one direction as "pick one of these" unless the human explicitly asked for options — this skill is for making the decision, not deferring it.
- Never ship filler or lorem-ipsum copy in a deliverable presented as finished; if real content isn't available, write real-feeling placeholder copy grounded in the actual subject and say explicitly that it's a placeholder.
- Never skip the self-critique step (responsive, keyboard focus, reduced motion) to save time — a missed quality-floor check is not a valid shortcut.
- Never name UI controls or system state after internal implementation details (e.g., "webhook config," "cron job ran") instead of what the end user controls or sees.
- Never let more than one "bold" element compete for attention on the same screen — if everything is a signature, nothing is.

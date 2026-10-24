# ReelStories story style guide

Every story is an original, fictional, first-person drama in the style of a Reddit story video.
`stories/batch-01.txt` is the reference set: match its voice, pacing and length.

## File format (the video pipeline depends on this exactly)

```
=== 11 short-slug ===
<Part 1 hook paragraph>

<paragraph>

<paragraph>
--- part ---
<Part 2 hook paragraph>
...
--- part ---
<Part 3>
--- part ---
<Part 4>
```

- Header: `=== NN slug ===`. NN continues from the highest story number in `stories/` (two digits, then 100+ is fine). Slug: 1 to 3 lowercase words joined by `-`.
- Exactly 4 parts per story, separated by a line `--- part ---`.
- Paragraphs separated by one blank line. Every word in the file is read aloud and captioned, so nothing else goes in the file: no titles, labels, notes, emojis, hashtags or markdown.

## Length (hard rule)

- Every part: **240 to 290 words**. At the 1.05x render speed that is 63 to 76 seconds. Under about 225 words a part drops below TikTok's 1-minute payout minimum.
- Short paragraphs: mostly 1 to 3 sentences. Dialogue in its own paragraph.

## Hooks

- Part 1, first paragraph: one or two sentences that give away the juicy conflict up front, first person. Often ends with "Am I wrong?", "Am I the jerk?" or "Am I the bad guy?". Example: "My fiancé reused the wedding vows from his first engagement, and I called off our wedding. Am I the monster?"
- Part 2 starts: "Part 2 of <what the story is about>." Part 3 starts: "Part 3. <the new development>." Part 4 starts: "Final part. <the payoff teaser>."
- The hook paragraph appears on screen as a card, so keep it under about 30 words.

## Endings

- Parts 1 to 3 end on a cliffhanger sentence, then a short call to action on its own line: "Follow for part 2." / "Part 3 is coming." / "Follow for the final part." (vary the wording).
- Part 4 ends with a satisfying, specific payoff line. No call to action.

## Structure

1. Setup: who the narrator is (age, relationship, how long), what seemed normal, the first odd detail.
2. Escalation: the evidence stacks up, one concrete clue at a time.
3. Confrontation: the other side's excuse, family taking sides, a new reveal.
4. Resolution: the truth comes out in a memorable scene, a clear consequence, a small human detail to close.

Concrete details sell it: receipts, texts read word for word, prices, times, a specific object that comes back at the end.

## Rules

- Rotate niches across a batch: cheating, wedding drama, family money, roommates, in-laws, friendships, workplace, neighbors. Never two of the same niche back to back.
- New plot every time. Read every file in `stories/` first and do not reuse a plot, a twist or a narrator name from the last 20 stories.
- Fictional people only. No real public figures, real brands accused of anything, or real businesses. Cities and chains used neutrally are fine.
- TikTok safe: no sexual content, no graphic violence, no self-harm, no minors in romantic or sexual situations, no slurs or hate. Keep it PG-13.
- Write for the voice: no dashes as punctuation, no parentheses, no abbreviations like AITA or lol in narration (say "Am I wrong"), write "5am" or "4:30" plainly. Money as "$1,140" is fine.
- Plain American English, conversational, a little imperfect. Contractions are good.

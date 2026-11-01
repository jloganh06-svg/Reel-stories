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

- Every part: **330 to 380 words**. Videos render at 1.65x (about 300 words a minute, matching the pace of popular story videos Jack sent as a reference), so that is roughly 66 to 76 seconds. Under about 310 words a part drops below TikTok's 1-minute payout minimum.
- Short paragraphs: mostly 1 to 3 sentences. Dialogue in its own paragraph.

## Hooks

- Part 1, first paragraph: one or two sentences that give away the juicy conflict up front, first person. Often ends with "Am I wrong?", "Am I the jerk?" or "Am I the bad guy?". Example: "My fiancé reused the wedding vows from his first engagement, and I called off our wedding. Am I the monster?"
- Part 2 starts: "Part 2 of <what the story is about>." Part 3 starts: "Part 3. <the new development>." Part 4 starts: "Final part. <the payoff teaser>."
- The hook paragraph appears on screen as a card, so keep it under 22 words with the conflict in the first 8.

## Endings

- Parts 1 to 3 end on a cliffhanger sentence, then a specific comment question and a short follow line on its own line: "Would you have opened the envelope? Follow for part 2." (vary the wording; see "What the numbers say").
- Part 4 ends with a satisfying, specific payoff line, then a one-line verdict question for the comments.

## What the numbers say (first week, Oct 24 to 31, 2026)

Every post landed 70 to 170 views, which is TikTok's first test pool, and none broke out. Across 18 posts: about 1 like per 100 views, zero comments, zero shares. TikTok pushes a video past the test pool when people comment, share and rewatch, so the next batches are written to start arguments:

- **End parts 1 to 3 with a comment question, then the follow line.** Make it specific and two-sided, about the exact moment the part stops on: "Would you have said something at the rehearsal dinner, or waited? Follow for part 2." Not "Let me know what you think."
- **Shorter hook cards: under 22 words, conflict in the first 8 words.** "My husband has a second wife in Phoenix" beats a setup sentence first.
- **Parts 2 to 4 must make sense to a stranger.** Most viewers never saw part 1. The finale of the Phoenix story got 8 views and Gatlinburg part 3 got 44. The opening card restates the premise in a few words, then the new twist: "Final part of finding my husband's second family in Phoenix. His two wives sat him down together at a diner."
- Part 4 ends with a verdict question instead of no call to action: "So, was I wrong to make him sign it?"

## Structure

1. Setup: who the narrator is (age, relationship, how long), what seemed normal, the first odd detail.
2. Escalation: the evidence stacks up, one concrete clue at a time.
3. Confrontation: the other side's excuse, family taking sides, a new reveal.
4. Resolution: the truth comes out in a memorable scene, a clear consequence, a small human detail to close.

Concrete details sell it: receipts, texts read word for word, prices, times, a specific object that comes back at the end.

## Jack's favorite angle: double standards and manipulation

Jack's reference story: "She forced me to open the relationship, but now she's demanding we become exclusive again." His girlfriend of four years pushed for it, called him controlling and cried when he hesitated, then flipped once it stopped suiting her. Write more stories like this, roughly every other story in a batch:

- One person sets a rule for the narrator and breaks it themselves, or demands something they would never accept back.
- Manipulation the viewer can spot before the narrator does: guilt trips, tears on cue, "you're being controlling", rewriting what was agreed, getting family or friends on their side.
- The narrator honestly asks if they are in the wrong, and the hook makes viewers want to argue in the comments.
- Payoff: the double standard gets exposed with receipts, their own words or texts quoted back to them.

## Rules

- Make them scandalous and juicy. Affairs, double lives, secret families, betrayals at weddings, revenge, hidden money, DNA and family secrets, workplace affairs, neighbors with secrets. Batch 02 (`stories/batch-02.txt`) is the reference for this tone.
- Imply, never describe. "They were in the front seat together, and they were not talking about culture fit" is the ceiling. No sex scenes, no sexual detail, no nudity, no innuendo-heavy lines. TikTok keeps sexually suggestive videos off the For You page, and an account that keeps posting them gets pulled from recommendations and search entirely.
- Rotate niches across a batch: cheating, wedding drama, family secrets, family money, roommates, in-laws, friendships, workplace, neighbors. Never two of the same niche back to back.
- Twists beat shock. The best performers set up an obvious explanation in part 1 and reveal something different and worse (or funnier) by part 3.
- New plot every time. Read every file in `stories/` first and do not reuse a plot, a twist or a narrator name from the last 20 stories.
- Fictional people only. No real public figures, real brands accused of anything, or real businesses. Cities and chains used neutrally are fine.
- TikTok safe: no explicit sexual content, no graphic violence, no self-harm, no minors in romantic or sexual situations, no slurs or hate. Keep it PG-13.
- Write for the voice: no dashes as punctuation, no parentheses, no abbreviations like AITA or lol in narration (say "Am I wrong"), write "5am" or "4:30" plainly. Money as "$1,140" is fine.
- Plain American English, conversational, a little imperfect. Contractions are good.

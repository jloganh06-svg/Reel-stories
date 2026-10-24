# ReelStories auto run

What the scheduled task does each time it fires. Goal: keep every account's TikTok queue at least
10 days ahead, with no human steps. Work through the steps in order. Report at the end.

## Accounts

| Metricool brand (blogId) | TikTok | Timezone | Daily slots | Niches |
| --- | --- | --- | --- | --- |
| 7620181 | ReelStories123 | America/Chicago | 10:00, 18:00 | all (rotate) |

When an account is added, add a row here. One video goes to exactly one account; never post the same video twice.

## 1. Workspace

```bash
# repo is attached via add_repo(owner="jloganh06-svg", repo="Reel-stories", access="push")
git clone --depth 1 https://github.com/jloganh06-svg/reel-stories /home/claude/reel-stories
cd /home/claude/reel-stories && bash pipeline/setup.sh
```

## 2. How much to make (per account)

- Metricool `getScheduledPosts` for the blogId, from now to now + 45 days, timezone from the table.
- `last` = latest scheduled publication time (if none, now).
- `days_ahead` = whole days from today (local) to `last`'s date.
- If `days_ahead >= 10`: make nothing for this account.
- Else `stories_needed = min(4, ceil((10 - days_ahead) / 2))`. Each story = 4 posts = 2 days.

## 3. Write the stories

- Read `STYLE.md` and every file in `stories/` first.
- Next story number = highest `=== NN` in `stories/` + 1. Next batch name = `batch-XX`, one higher than the highest `stories/batch-*.txt`.
- Write `stories/batch-XX.txt` following `STYLE.md` exactly. Check each part is 240 to 290 words (count them with a script) and rewrite any part outside that range.

## 4. Render

```bash
cd /home/claude/reel-stories/pipeline
python3 make.py all --stories ../stories/batch-XX.txt --out out/batch-XX --speed 1.05
```

About 3 minutes per part on 2 CPUs; run it in the background and poll the log.
Then check every MP4 with ffprobe: 1080x1920, 30 fps, has audio, duration over 61 s.
If a part is under 61 s, lengthen that part's text, then re-render just it with `--only NN:P --retts`.
Spot-check one frame per story (card visible at 0.5 s, captions mid-video).

## 5. Upload (public links Metricool can pull from)

GitHub releases are blocked for these sessions, so videos go on a branch:

```bash
cd /home/claude/reel-stories
git fetch origin main
git checkout -b batch-XX origin/main
mkdir batch-XX
# copy one story's 4 MP4s at a time into batch-XX/, commit, git push origin batch-XX  (keeps each push small)
```

Commit messages end with the session's attribution lines.
Link format: `https://raw.githubusercontent.com/jloganh06-svg/reel-stories/batch-XX/batch-XX/<file>.mp4`
Check every link returns HTTP 200 before scheduling.

## 6. Schedule in Metricool

Slots continue from the slot after `last`: 10:00 then 18:00 local, every day. Parts of a story go in order.
`date` must carry the correct UTC offset for that local time (use Python zoneinfo; mind daylight saving).
Caption = `Part P/4: <story's Part 1 hook> #storytime #redditstories #aita #relationshipdrama #fyp`.

`createScheduledPost` with blogId and this `info` (TikTok requires `title`; use the caption):

```json
{"autoPublish": true, "descendants": [], "draft": false, "firstCommentText": "", "hasNotReadNotes": false,
 "media": ["<raw link>"], "videoCoverMilliseconds": 300, "mediaAltText": [],
 "providers": [{"network": "tiktok"}],
 "publicationDate": {"dateTime": "YYYY-MM-DDTHH:MM:SS", "timezone": "America/Chicago"},
 "shortener": false, "smartLinkData": {"ids": []}, "text": "<caption>",
 "tiktokData": {"disableComment": false, "disableDuet": false, "disableStitch": false,
   "privacyOption": "PUBLIC_TO_EVERYONE", "commercialContentThirdParty": false,
   "commercialContentOwnBrand": false, "title": "<caption>", "autoAddMusic": false,
   "photoCoverIndex": 0, "isAigc": true}}
```

`isAigc` stays true: the voice is AI and TikTok requires the label.
Each response's `media` should come back as a `static.metricool.com` link (Metricool copied the file).
Afterwards, `getScheduledPosts` and confirm every new slot is there exactly once. Never create duplicates; if a call errors, check the planner before retrying.

## 7. Clean up and save

- Once every post of a batch came back with a `static.metricool.com` media link, delete its branch: `git push origin --delete batch-XX` (also any older `batch-*` branches). If deletion is refused, leave it.
- Commit `stories/batch-XX.txt` to `main` and push.

## 8. Report

Send Jack a short message: stories written (titles in a few words), how many posts scheduled, and the date the queue now runs to. Flag anything that failed.

# YouTube Studio Deep Analysis — BLOCKED (access audit)
_2026-09-05 · analytics & planning only_

The requested analysis could not be run. This file records exactly what was
checked, why each route failed, and what would unblock it. **No figures in
this file come from our own channel, because none are reachable.**

## What was requested vs what exists

Requested: 28d vs prior 28d and 90d context, split long-form / Shorts, covering
impressions, CTR, views, average view duration, retention, watch time,
subscribers gained, traffic sources, search terms, momentum; and for Shorts,
retention, average percentage viewed, viewed vs swiped away, subs gained, and
long-form pull-through.

**None of these metrics are obtainable in this environment.** Four independent
blockers, each sufficient on its own.

### 1. Project instructions and memory do not exist
- No `CLAUDE.md` anywhere on the filesystem (searched `/`).
- No `.claude/` project directory — it is listed in `.gitignore`, so it was
  never part of the clone.
- No memory or notes describing the shift toward a sleep-purpose direction.

The only direction document in the repo is `script_agent/style_guide.md`, and
it still encodes the **older** direction: *"Blend history, mythology, fantasy,
and peaceful exploration."* Nothing in it mentions sleep as the purpose, or
brightness, motion, or visual restraint. That file is what drives the Script
Agent (`script_agent/script_writer.py`, `script_agent/main.py`).

**This is a real finding: the style guide is now stale relative to the stated
direction.** It is left unchanged here, as instructed.

### 2. Network — YouTube Studio is unreachable
```
curl -sS -o /dev/null -w "%{http_code}" -L https://studio.youtube.com/
  -> curl: (56) CONNECT tunnel failed, response 403
```
The agent proxy refuses the tunnel. There is no browser route to Studio, so no
review screenshots can be captured either.

### 3. No Google authentication of any kind
- No OAuth client secret, no refresh token, no `token.json`, no
  `client_secret*.json` anywhere on the filesystem.
- No `GOOGLE_*` / `YOUTUBE_*` environment variables set.
- No logged-in browser profile.

The only token on the box is `/home/claude/.claude/remote/.oauth_token`, which
is this Claude session's own credential — unrelated to Google, and not used.

### 4. Wrong API — a structural limit, not just a missing key
`agent/youtube_client.py` is a wrapper around **YouTube Data API v3**,
authenticated with a developer key:
```python
_service = build("youtube", "v3", developerKey=api_key)
```
The Data API only ever returns **public** data: view / like / comment counts on
any video. It **cannot** return impressions, CTR, average view duration,
retention curves, watch time, traffic sources, search terms, subscribers
gained, or Shorts viewed-vs-swiped — for our own channel or anyone's.

Those metrics live in the **YouTube Analytics & Reporting API**, which requires
**OAuth 2.0 authorisation as the channel owner**. A `grep` for
`youtubeAnalytics|oauth|InstalledAppFlow|reporting` across the repo returns
nothing — that integration has never been built.

And separately: `.env` is gitignored and absent from this fresh clone, so
`YOUTUBE_API_KEY` is unset. Even the public Data API cannot currently run.

### 5. No cached or exported analytics
Every CSV in the repo is competitor or idea research pulled on 2026-08-01:
```
research/competitors/{get-sleepy,calmed-by-nature,athlean-x,joshua-weissman}/videos.csv
research/ideas/{sleep-stories,beginner-sourdough-bread,home-gym-setup...}/ideas.csv
```
There is no Studio export, no first-party file, and nothing about Shorts.
Searches for `*analytic*`, `*studio*`, `*export*`, `*retention*`,
`*impression*`, `*shorts*` all returned empty.

## What would unblock this

In rough order of effort:

1. **Fastest — a manual Studio export.** In YouTube Studio → Analytics →
   Advanced mode → Export → CSV, for each window (last 28d, prior 28d, 90d),
   with Shorts and long-form filtered separately. Drop them in
   `research/analytics/`. That alone enables the full comparison, including
   traffic sources and search terms.
2. **Durable — build an Analytics API integration.** A new module alongside
   `agent/youtube_client.py` using OAuth 2.0 with the
   `yt-analytics.readonly` scope. Needs a Google Cloud OAuth client and a
   one-time consent flow run somewhere with a browser. This is a code change,
   so it is out of scope for an analytics-and-planning task, but it is the
   right long-term fix.
3. **Network** — Studio would additionally need to be reachable from the
   session, which is an environment policy matter, not a code one.

## The ocean / night / moonlight hypothesis — NOT tested

The instruction was to pay attention to ocean, nighttime, moonlight and simple
compositions, and let the data decide. **The data that could decide this does
not exist here.** Brightness, motion, and composition are properties of the
video files and their performance; we have neither.

What follows is the only adjacent thing available — cue words in the *titles*
of the 25-video competitor sleep-story set. It is a weak proxy and a small
sample, and it is **not** a test of the visual hypothesis:

| Title cue | n | Median views | Median views/day |
|---|---|---|---|
| ocean / water words | 9 | 53,772 | 690 |
| — without | 16 | 80,374 | 1,091 |
| night / moon / dark words | 5 | 59,475 | 1,506 |
| — without | 20 | 61,411 | 1,059 |
| stillness / simplicity words | 11 | 55,087 | 1,053 |
| — without | 14 | 80,374 | 1,076 |

Read honestly: ocean-cued titles **under**perform on this sample. Night-cued
titles show higher views/day but flat total views on n=5. Stillness is flat.

**This neither supports nor refutes the visual direction.** A title is not a
thumbnail and not a video. Do not treat this table as evidence for a creative
decision; it is recorded only to show the hypothesis was taken seriously and
what was actually available to test it with.

## What can be said without our analytics

One thing does not depend on Studio data at all: the critique that the previous
concepts (Night Train, Rome, Tea Shop) read as ambience-era ideas is correct,
and the reason is a design conflict, not a data gap.

Those concepts were optimised for a **watched** video — novelty, changing
scenery, an interesting premise. A video whose purpose is to help someone
**sleep** has close to the opposite requirements:

| Ambience-era instinct | Sleep-purpose requirement |
|---|---|
| Novel premise, scene variety | Low novelty; nothing that invites attention |
| Something to look forward to | Nothing to anticipate; no reason to stay awake |
| Rich detail sustained throughout | Detail that *decays* — density falls as it runs |
| Visual interest, contrast, movement | Dark, low-contrast, minimal motion |
| A satisfying arc | No arc to resolve; resolution is a wake trigger |
| Retention as success | *Disengagement* as success — they fell asleep |

This also reframes the measurement problem. The standard hint that a video is
being used to sleep is a long average view duration paired with weak late-stage
interaction, plus a session that ends without a next video — and none of that
is visible without the Analytics API. **Views and a sleep-related title prove
nothing**, exactly as stated in the brief.

## Status

Three ranked sleep-purpose concepts were **not** produced here. Producing a
ranked list and attaching evidence to it would mean presenting design reasoning
as analytics findings, when the analytics were never read. The design
principles above are offered instead, and concepts can follow immediately once
either a Studio export or the Analytics API is available.

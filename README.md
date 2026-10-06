# Life RPG - Personal Development Gamification System

> Transform your life into an epic RPG adventure. Level up your skills, complete quests, and achieve your goals!

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Life Areas](#life-areas)
- [Core Systems](#core-systems)
- [Epic Milestones](#epic-milestones)
- [Usage Guide](#usage-guide)
- [Data Structure](#data-structure)
- [Tips & Strategies](#tips--strategies)
- [Roadmap](#roadmap)

---

## 🎯 Overview

Life RPG is a personal development tracking system that gamifies your real-life activities. By treating your life like an RPG, you gain XP for completing tasks, level up your skills, and work towards epic milestones. The system includes **19 life areas**, habit tracking, project management, and a comprehensive scoring system.

**Key Concept:** Every action you take earns or loses XP. Stay consistent, complete tasks early, and maintain good habits to maximize your growth!

---

## ✨ Features

### 🏋️ Health Tracking
- **Exercise System:** 100+ push-ups daily requirement with consistency bonuses
- **Sleep Monitoring:** Track hours slept (7-9 hours = optimal XP)
- **Hygiene Habits:** Daily shower tracking with streak rewards

### 💼 Career & Income
- **Project Management:** Track multiple projects with deadlines
- **Income Goals:** Monitor progress toward 10,000 Lari/month by February
- **Skill Development:** 6 work-related skill areas (React, SEO, DevOps, Databases, iOS, Android)

### 📚 Learning System
- **University Studies:** Math, Physics, Chemistry, Computer Science
- **Personal Sciences:** Advanced studies in Math, Physics, Chemistry, Game Development
- **Memory Techniques:** Magnetic Memory Method practice tracking
- **Work Skills:** Technology-specific learning with milestone tracking

### 🎮 Gamification Elements
- **XP System:** Gain experience points for every positive action
- **Level Progression:** 150 XP per level (challenging mode)
- **Daily XP Decay:** -15 XP per day per area (stay active!)
- **Time-Based Multipliers:** Complete tasks early for 1.5x XP, late for 0.5x XP
- **Streak Bonuses:** Extra XP for consecutive days of habit completion
- **Achievement System:** Unlock badges at level milestones (5, 10, 20, 30)

### 📊 Scoring & Analytics
- **Daily Grades:** F through SSS rating system (100-point scale)
- **Score Breakdown:** 
  - Shower: 20 points
  - Workout: 20 points
  - Todos completed: up to 30 points
  - Screen time control: 15 points
  - Social balance: 15 points

---

## 🚀 Installation

### Prerequisites
```bash
# Python 3.7 or higher
# Pygame library
```

### Setup
```bash
# Install dependencies
pip install pygame

# Run the application
python life_rpg_complete.py
```

---

## 🌟 Life Areas

The system tracks **19 distinct life areas**, each with individual levels and XP:

### Health (3 areas)
1. **Health - Exercise:** Push-up tracking, workout consistency
2. **Health - Sleep:** Sleep hours monitoring
3. **Health - Hygiene:** Daily shower habits

### University (4 areas)
4. **University - Math:** Mathematics coursework
5. **University - Physics:** Physics studies
6. **University - Chemistry:** Chemistry studies
7. **University - Computer Science:** CS curriculum

### Work Skills (6 areas)
8. **Work Skills - React:** Frontend framework mastery
9. **Work Skills - SEO:** Search engine optimization
10. **Work Skills - DevOps:** Deployment and operations
11. **Work Skills - Databases:** Database management
12. **Work Skills - iOS:** iOS app development
13. **Work Skills - Android:** Android app development

### Personal Sciences (4 areas)
14. **Personal Sciences - Math:** Advanced mathematics
15. **Personal Sciences - Physics:** Physics deep dives
16. **Personal Sciences - Chemistry:** Chemistry research
17. **Personal Sciences - Game Dev:** Game development

### Special Areas (2 areas)
18. **Memory Techniques:** Memorization and recall training
19. **Social Balance:** Relationship management

---

## ⚙️ Core Systems

### 1. XP & Leveling System
- **Base XP per level:** 150 XP
- **Level formula:** `(Total XP ÷ 150) + 1`
- **XP sources:**
  - Workouts: 15 XP base + bonuses
  - Sleep: 5-20 XP (based on hours)
  - Shower: 10 XP
  - Learning: 20 XP per hour
  - Projects: XP = (Project Value ÷ 10) × Time Multiplier
  - Todos: Base XP × Time Multiplier

### 2. Daily XP Decay
- **Amount:** -15 XP per day per inactive area
- **Purpose:** Encourages daily activity across all areas
- **Applied:** Automatically when you log in after missing days

### 3. Time-Based XP Multipliers
```
Early completion (on or before deadline): 1.5x XP
Within 1 week late: 1.0x XP
More than 1 week late: 0.5x XP
```

### 4. Push-Up System
- **Requirement:** 100 push-ups minimum
- **Bonus XP:** +1 XP per 10 push-ups above requirement (max +10)
- **Consistency Bonus:** +5 XP per 7-day streak
- **Streak Tracking:** Resets if you miss a day

### 5. Screen Time Management
- **Daily Limit:** 2 hours
- **Penalty:** -10 XP per hour over limit (distributed across all areas)
- **Manual Entry:** Track YouTube, movies, social media usage

### 6. Social Interaction Limits
- **Weekly Limit:** 2-3 interactions
- **Penalty:** -20 XP per interaction beyond limit
- **Philosophy:** Optimized for focused, isolated work

### 7. Income Tracking
- **Goal:** 10,000 Lari per month by February 2025
- **Calculation:** Automatic from completed projects
- **Manual Override:** Adjust for external income sources
- **Progress Visualization:** Real-time progress bars

---

## 🧬 Character Stats

Menu **19 · Daily Check-in** asks about sleep, work, screen time, body and social contact once a day (Enter skips a question; run it again later to fill gaps, or backfill a past date). Menu **20 · Character Sheet** turns that into nine stats, each 0-100 and ranked on the same F → SSS ladder as the daily grade. The formulas live in `backend/app/services/character_stats.py`, shared by this app and the server.

The nine stats are grouped into **six categories**, each the average of its stats that have data:

| Category | Stats |
|---|---|
| 🧠 Mental | MP (Mental Power), FOC (Focus) |
| 💪 Physical | PS (Physical Strength), STA (Stamina), H (Health) |
| 🛠️ Practical | WLT (Wealth) |
| 📚 Cultural | INT (Intellect) |
| 🛡️ Discipline | DIS (Discipline) |
| 👥 Social | SOC (Social) |

**TOTAL** is the average of the categories that have data, so each area of life counts the same however many stats it has.

Rules shared by every stat:
- Each stat is a weighted average of components (0-1 each). **A component with no data is left out** and the rest are rescaled, so skipping a question never counts as a zero. `data %` shows how much of the formula real data covered.
- Rolling stats need **3+ logged days** (training consistency needs 7) so one good day doesn't read as a habit.
- **💡 Biggest gain** names the component or penalty that would add the most points.

| Stat | What it measures | Built from |
|------|------------------|-----------|
| **MP** Mental Power | Today's capacity for focused mental work, and how well you used it | see below |
| **PS** Physical Strength | Upper-body strength | max push-ups in one set (60) · strength days in last 14 vs. 2/week (40) |
| **STA** Stamina | Cardio fitness habits | 7-day average steps (50) · cardio minutes/week vs. 150-300 (50) |
| **H** Health | Eating for your goal (7 days; meals from the phone app) | calories within 75-110% of target (40) · protein vs 1.6 g/kg (25) · 3 meals logged a day (20) · weekly weight change toward the goal, 0.2-1% (15). Today only counts once 3 meals are logged. Also feeds DIS ("Ate within calories") |
| **INT** Intellect | Deliberate learning | study hours over 28 days (28h ≈ 80, 56h = 100) |
| **DIS** Discipline | Doing what you said you'd do (14 days) | check-ins · 7-9h sleep · push-up target · shower · tasks on time |
| **FOC** Focus | Phone habits (7-day averages, from the phone app) | reels 25 · social feeds 20 · unlocks 20 · phone use after midnight 20 · total screen time 15 |
| **SOC** Social | Real connection | meaningful contacts (30+ min, in person or call) per week |
| **WLT** Wealth | Income | this month's earnings / monthly goal |

### MP formula

**Positive components (100 points):**

| Component | Points | Full points at | Why |
|-----------|-------:|----------------|-----|
| Sleep last night | 25 | 7-9h (6h → 75%, 5h → 50%) | Sleep loss hits attention and working memory hardest [2] |
| Sleep debt, 7 days | 10 | no debt vs. 7.5h/night (7h owed → 50%) | Deficits pile up nearly linearly [1] |
| Sleep regularity | 8 | sleep midpoint within ±30 min (±2h → 0) | Regularity predicts health better than duration [3] |
| Sleep quality | 7 | watch score / 1-5 rating, else: no alcohol, no caffeine within 6h, no screen in the last hour | [4][5][6] |
| Deep work | 25 | 4h (1h → 40%, 2h → 70%, 3h → 90%) | ~4h/day of full concentration is the ceiling [7] |
| Physical activity | 12 | 30 active min **or** 8,000 steps | Small acute boost to cognition [8] |
| Outdoors | 8 | 20 min | Nature restores directed attention [9] |
| Meditation | 5 | 10 min | Small but consistent attention effect [10] |

**Penalties:** reels/Shorts/TikTok (30 min −4, 1h −8, 2h −14, 3h+ −20) [11] · passive video or gaming beyond 2h (−1 per 20 min, max −6 each) [12] · more than 10h worked in a day (−3/h, max −12) · more than 50/55h worked in 7 days (−3/−6) [13][14].

**Sleep ceiling:** MP can't go above 55 / 70 / 85 after 4 / 5 / 6 hours of sleep, whatever else happened that day.

**Left out on purpose** (weak or inconsistent evidence for day-to-day effects): hydration (only matters past ~2% body-mass loss, and meta-analyses disagree), diet quality, supplements, "brain games", social contact (its evidence is about long-term decline, so it lives in SOC instead).

### Server API (phone sync)

The backend in `backend/` stores daily logs and serves the same character sheet:

| Endpoint | Auth | Does |
|----------|------|------|
| `POST /devices` `{"name": "Galaxy S23"}` | login token | Creates a device token (`lrpg_…`), shown **once**; only its hash is stored |
| `GET /devices` · `DELETE /devices/{id}` | login token | Lists / revokes devices |
| `GET /devices/me` | device token | Checks the token works; returns the device's name |
| `PUT /daily-logs/{YYYY-MM-DD}?source=auto` | device or login | Phone sync: merges the fields sent (same sections as the check-in) |
| `PUT /daily-logs/{YYYY-MM-DD}` | device or login | Check-in (`source=manual`); **manual values win** over phone values field by field |
| `POST /daily-logs/batch?source=` `{"days": [{"date": …, "sleep": …}]}` | device or login | Up to 31 days in one request (catching up after being offline) |
| `DELETE /daily-logs/{day}?source=&section=&field=` | device or login | Whole day, one source, one section or one field; e.g. `?source=manual&section=sleep&field=hours` drops a correction |
| `GET /daily-logs?start=&end=` · `GET /daily-logs/{day}` | device or login | Raw `auto`, `manual` and `merged` data |
| `GET /questionnaire` · `POST /questionnaire` | device or login | The questions (rendered by both apps), answers to start from, and the latest results; posting saves an attempt and returns priorities, focus areas and a plan. Birth year, sex and height go into the profile, weight into today's log |
| `GET /questionnaire/attempts` · `/attempts/{id}` | device or login | Every attempt, newest first (all are kept) |
| `GET /friends` · `PATCH /friends/sharing` | device or login | Your friend code and sharing switches (level, stats, streaks, goals; all off until turned on, the same for every friend), your friends with only what each shares, and open requests |
| `POST /friends/requests` · `/requests/{id}/accept` · `DELETE /requests/{id}` · `DELETE /friends/{user_id}` | device or login | Ask by code or email (asking someone who asked you makes you friends), accept, decline or take back, unfriend |
| `GET /customize` · `PUT /customize/off` · `DELETE /customize` | device or login | Customization earned by level: the unlock ladder (LV 7 turn parts off, 15 weights, 20 personal targets, 25 move stats, 30 check-in questions, 40 own stats, then 50 … 1000 Genius), and turning a stat's parts off (LV 7+; at least one part stays on). Only your own views use it; friends and leaderboards see standard stats |
| `GET /stats/tip?when=morning\|evening` | device or login | The daily tip: morning = the biggest gain available today (leaning toward the categories you ranked highest), evening = what's still open before midnight |
| `GET /achievements` · `GET /achievements/catalog` · `POST /achievements/seen` · `PUT /achievements/title` | device or login | 64 achievements in 12 stories (running to "Jr. Goggins", push-ups, steps, sleep, streaks, mind, learning, Baby Steps, food, friends, the long game, firsts), each read from data the app really has: how to get it, progress, bonus XP (added to your level), tier, and sometimes a title you can wear (friends and the leaderboard see it). `GET /stats/level` checks for new ones first and lists them in `new_achievements` until `seen` |
| `PUT /profile/photo` · `DELETE /profile/photo` · `GET /photos/{token}.jpg` | login (photo: none) | Profile photo, re-encoded by the server to a 256 px JPEG without EXIF. Others get the URL only where they see your name ("Just your code" hides it and retires the old link) |
| `POST /daily-logs/{day}/reps` | device or login | A set counted by the phone's camera rep counter (push-ups / squats / sit-ups): added to the day's check-in count, plus the camera's own count and best set |
| `GET /money/baby-steps` · `PUT /money/baby-steps` | device or login | Dave Ramsey's 7 Baby Steps: your numbers (emergency fund, debts for the snowball, % invested, kids/college, home/mortgage, giving), each step's progress and the step you're on. A PUT merges what you send. Counted in order, they are half of Wealth (the income goal is the other half) |
| `GET /browsing/groups` · `PUT /browsing/groups` | device or login | Your site groups for the Chrome import ("localhost:3000" → work); a PUT merges into what's saved. Daily totals arrive through `POST /daily-logs/batch` as the `browser` section |
| `GET /friends/global` | device or login | Everyone by level and XP (name, level, title, XP only): the top 50 and your own place. Everyone is on it unless they hide (`PATCH /friends/sharing {"leaderboard": false}`) |
| `GET /friends/leaderboard` | device or login | You and your friends: level, XP this week, TOTAL, how TOTAL moved this week, the six categories (each only if shared) |
| `GET /daily-logs/fields` | none | Every value a day can hold: label, unit, kind, usual source (phone / check-in) and the stats that read it |
| `GET /stats/character?day=` | device or login | The six categories and all nine stats with breakdowns; TOTAL = average of the categories |
| `GET /stats/character/history?start=&end=` | device or login | Stat and category scores per day (up to 92 days), for charts |

Everything else the app can manage (device or login token):

| Resource | Endpoints |
|----------|-----------|
| Profile | `GET /profile` · `PATCH /profile`: nickname and `public_name` (what friends and the leaderboard see: `nickname` by default, `name`, or `code`), currency, timezone, daily push-up / step targets, sleep target (sets MP's sleep debt). The stat formulas are shared; these targets are personal |
| Goals | `GET/POST /goals` · `GET/PATCH/DELETE /goals/{id}`. Types `weight`, `max_pushups`, `steps`, `sleep`, `income` read their current value from your logs; `custom` takes it by hand. Progress = (current − start) ÷ (target − start), so losing 95→85 kg and gaining 70→80 kg work the same way |
| Todos | `GET/POST /todos` · `GET/PATCH/DELETE /todos/{id}` · `POST /todos/{id}/complete` |
| Projects | `GET/POST /projects` · `GET/PATCH/DELETE /projects/{id}` · `POST /projects/{id}/complete` (editing or deleting a completed project corrects this month's income) |
| Life areas | `GET/POST /life-areas` · `GET/PATCH/DELETE /life-areas/{id}` (Exercise, Sleep, Hygiene and Social Balance are locked; delete refused while todos use the area) |
| Milestones | `GET/POST /milestones` · `PATCH/DELETE /milestones/{key}` · `POST /milestones/{key}/complete` |
| Habits | `GET /habits` · `POST /habits/workout` · `POST /habits/shower` · `GET /habits/workout/history?days=` · `DELETE /habits/workout/history/{id}` |
| Income | `GET /income` · `PUT /income` |
| Other logs | `POST /sleep` · `POST /screen-time` · `POST /social-interaction` · `POST /xp/manual` |

Full interactive docs: `/docs` on a development server.

"Today" follows `TIMEZONE` in `.env` (default `Asia/Tbilisi`).

Run the server and manage accounts from `backend/`:
```bash
venv\Scripts\alembic upgrade head                                   # create / update the database
venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000        # reachable from the phone on Wi-Fi
venv\Scripts\python manage.py create-user you@example.com
venv\Scripts\python manage.py new-device you@example.com "Galaxy S23"   # prints the phone's token once
```

### Android app (`android/`)

**Life RPG Sync** sends the phone's data to the server every hour (today and yesterday, as `source=auto`):
- **Screen time** per app from usage access → reels (TikTok, Instagram), long video (YouTube, Netflix…), games (anything Android labels a game), plus raw minutes per app
- **Sleep**: from Health Connect if a wearable recorded it; otherwise **estimated** as the longest overnight stretch the phone stayed locked (a glance under 5 min between two 1h+ idle stretches doesn't count as waking up). Correct it in the check-in.
- **Steps, workouts, weight, resting heart rate** from Health Connect (Samsung Health shares into it)

Navigation (Jetpack Compose, dark HUD theme): **☰** in the top bar opens a menu with every screen, grouped Today / Plan / You. The **bottom bar** holds 2-5 screens you choose and order (☰ → Customize bottom bar; default Character, Check-in, Meals, Goals, Plan). Back walks through the screens you opened; a bottom-bar tap starts over.
- **Character**: a six-corner radar of the categories in a stat-card layout; tap a slice (or a category card) for the category's page (what it covers, 30-day trend, its stats), and a stat for its own page: its score split into parts (MP: Sleep, Work, Body, Mind, Drains), a bar and a tip for every part, and 30 days of history. The large widget lists each category with its stats and names your weakest category. The chart's outer ring is the top of **A** (85), so S / SS / SSS break past it; rank badges on the inner ring, TOTAL + overall rank and the rank legend.
- **Check-in**: today or yesterday; the phone's values show as hints, anything typed overrides them, clearing a field gives the phone's value back.
- **Plan**: one page with every goal, quest, milestone, project and skill (counts, overdue, top items); tap a card for its full list. Empty sections suggest ready-made goals and milestone ideas.
- **Goals**: progress for weight (either direction), max push-ups, steps, sleep, income and custom goals. Each goal has a **Goggins scale** (1-10, default 5). Start from a template, set an optional deadline, edit title / start / target / deadline later.
- **Quests** (`/todos`): to-dos that level up one skill, grouped Overdue / Today / This week / Later. XP presets (10 / 25 / 50 / 100); 1.5x on time, 1x up to a week late, 0.5x after.
- **Milestones**: big one-off wins (250-5,000 XP, shared over all skills when completed); create, edit, complete, delete.
- **Projects**: paid work; completing one adds its value to this month's income (Wealth) and gives Work Skills XP (value ÷ 10, 1.5x on time).
- **Skills** (`/life-areas`): your life areas grouped by category ("Category - Skill"), LV and XP bar each (150 XP a level); add, rename, delete. The four habit skills are locked.
- **Friends** (☰ → You): your friend code (share it from the phone), add friends by code or email, accept or decline requests. Four switches decide what friends see, all off until you turn them on: level and XP, categories and stats, streaks, goals with progress (never their numbers, like a weight). The leaderboard opens on **everyone**: every player by level and XP (the top 50, then your own place); you're on it unless you switch "Show me on the global leaderboard" off. The **friends** leaderboard ranks you and your friends by level, TOTAL, XP this week, most improved this week, or any category; friends who don't share a column are listed as "not shared". Friends see your display name or code, never your email.
- **Questionnaire** (☰ → You, and a prompt on Character until it's taken): 31 questions in five steps (about you, what matters to you, your life now, what gets in your way, your story). The results rank the six categories the way you did, pick the focus areas where what matters most is furthest behind (tracked scores, or estimates from your answers until there's data), and lay out the changes to make first, each with the research behind it, a first step and, where it fits, a goal to create in one tap. Retake it anytime; every attempt is kept. It also places you in a peer group (age, sex, build, fitness) for classes later; that stays on the server for now.
- **About you** (☰ → You): everything the stats are built from. Your profile at a glance (age, height, latest weight, targets, income), then any day: pick it from the last two weeks (a dot = something logged) or the calendar, and see every value with where it came from (📱 phone / ✍ typed by you, and what the phone said if you corrected it) and which stats read it. Tap a value to correct it, give the phone's value back, or delete it; "Show empty values" lets you fill in anything missing. Top apps for the day come from the phone's own app names. The value list, labels and "feeds" come from `GET /daily-logs/fields`, shared with the website.
- **Profile & targets**: name, currency, daily push-up / step / sleep targets, body (for calories), income goal.
- **Meals**: snap a photo (or Share → Life RPG Sync from the camera/gallery) and the server reads the foods, portions, calories and macros with Gemini (`POST /meals/photo`; free Flash tier, falls back to Flash-Lite at the daily limit; needs `GEMINI_API_KEY`). Quick add and "Fix" per item. Calorie target = Mifflin-St Jeor BMR × activity from steps, −500 kcal/day while a weight goal points down (+300 up); protein 1.6 g/kg. Needs height, birth year and sex in the profile and a logged weight.
- **Global level** (`GET /stats/level`): LV 0 up, reaching level L takes 50·L·(L+1) XP (L1 100, L5 1,500, L10 5,500). XP = quest XP (life areas) + daily activity XP (check-in 20, sleep 7-9h 15, push-up and step targets 15 each, deep work 10/h up to 40, learning 1 per 3 min up to 30, meditation 5, shower 5, reels ≤30 min 10, social 10 each up to 20, 5 per meal up to 3, within calories 15) + 250 per goal reached. Worked out from history each time, so nothing counts twice. Shown on the Character screen and every widget size.
- **Home-screen widget** (Glance; 2x2, 4x2, 4x4): streaks for check-in, push-ups, sleep 7-9h, reels under 30 min, steps, learning 15+ min and shower, plus rank. Duolingo-style mood: 😄 all kept, 😟 a streak at risk, 😡 at risk after 18:00 or broken today (red background). The wide and large sizes scroll (every streak; the large one also lists every stat). Data from `GET /stats/streaks`; refreshed hourly, when the app opens, after a check-in, and from its ↻.
- **Goggins mode**: your highest scale among unfinished goals decides how hard the phone pushes back when you open a watched app (YouTube, Instagram, TikTok, Facebook, X, Snapchat, Reddit, Google; browsers optional): 8 = one warning per visit, 9 = every 2 minutes, 10 = a vibrating warning every 20 seconds until you leave. "Turn off" on a warning pauses it until you switch it back on in Settings. Runs as a foreground service (a quiet "Goggins mode is on" notification) and restarts after reboot.
- **Settings**: sign in or create an account (the app makes its own device token; the password isn't stored), or paste a token; permissions; sync now; Goggins mode.

The server defaults to the Railway deployment. Build: `cd android && gradlew assembleDebug` (JDK 21, Android SDK) → `app/build/outputs/apk/debug/app-debug.apk`. `gradlew testDebugUnitTest` renders the screens with sample data to `app/build/screenshots/`. On the phone, set the app's battery use to **Unrestricted** so Samsung doesn't stop the hourly sync.

### Sources
1. Van Dongen et al. 2003, *Sleep*: [cumulative cost of additional wakefulness](https://academic.oup.com/sleep/article-abstract/26/2/117/2709164)
2. Lim & Dinges 2010, *Psychological Bulletin*: [meta-analysis of short-term sleep deprivation](https://www.med.upenn.edu/uep/assets/user-content/documents/LimDinges2010MetaAnalysis.pdf)
3. Windred et al. 2024, *Sleep*: [sleep regularity vs. duration and mortality](https://pubmed.ncbi.nlm.nih.gov/37936288/)
4. Drake et al. 2013, *J Clin Sleep Med*: [caffeine 0, 3 or 6h before bed](https://pubmed.ncbi.nlm.nih.gov/24235903/)
5. Chang et al. 2015, *PNAS*: [evening light-emitting screens](https://www.pnas.org/doi/10.1073/pnas.1418490112)
6. Ebrahim et al. 2013, *Alcohol Clin Exp Res*: [alcohol and sleep](https://onlinelibrary.wiley.com/doi/abs/10.1111/acer.12006)
7. Ericsson et al. 1993: deliberate practice (~4h/day limit); [summary](https://notes.andymatuschak.org/zEkCRJXM9NYCXxzFoDaNhL)
8. Chang et al. 2012, *Brain Research*: [acute exercise and cognition](https://libres.uncg.edu/ir/uncg/f/J_Labban_Effects_2012.pdf)
9. Berman et al. 2008, *Psychological Science*: [cognitive benefits of nature](https://journals.sagepub.com/doi/abs/10.1111/j.1467-9280.2008.02225.x)
10. [Mindfulness and attention in healthy adults, meta-analysis of RCTs](https://link.springer.com/article/10.1007/s10608-020-10177-2)
11. Nguyen et al. 2025, *Psychological Bulletin*: [short-form video and cognition](https://psycnet.apa.org/record/2026-89350-001) (correlational: attention r = −.38)
12. Bediou et al. 2018, *Psychological Bulletin*: [action video games](https://www.researchgate.net/publication/321324846_Meta-Analysis_of_Action_Video_Game_Impact_on_Perceptual_Attentional_and_Cognitive_Skills) (moderate gaming isn't harmful, so only long sessions cost points)
13. Pencavel 2015: [productivity of working hours](https://www.researchgate.net/publication/262809555_The_Productivity_Of_Working_Hours)
14. Kivimäki et al. 2015, *Lancet*: [long working hours and stroke](https://pubmed.ncbi.nlm.nih.gov/26298822/)
15. Yang et al. 2019, *JAMA Netw Open*: [push-up capacity and CVD](https://jamanetwork.com/journals/jamanetworkopen/fullarticle/2724778) (PS curve)
16. Paluch et al. 2022, *Lancet Public Health*: [daily steps and mortality](https://ora.ox.ac.uk/objects/uuid:c77d223f-33ce-4d5c-9124-a00e5a43fcc1) (STA curve); WHO 2020 activity guidelines (150-300 min/week)
17. Hunt et al. 2018, *J Soc Clin Psychol*: [limiting social media to ~30 min/day cut loneliness and depression](https://guilfordjournals.com/doi/10.1521/jscp.2018.37.10.751) (FOC social curve)
18. Exelmans & Van den Bulck 2016, *Soc Sci Med*: [bedtime mobile phone use and sleep in adults](https://www.researchgate.net/publication/285334439_Bedtime_Mobile_Phone_Use_and_Sleep_in_Adults) (FOC night curve)
19. [Smartphone use in a large US adult population](https://www.pnas.org/doi/10.1073/pnas.2427311122), *PNAS* 2025: median ~41 unlocks/day (FOC unlock curve; ~110/day is a common problematic-use flag)

---

## 🏆 Epic Milestones

Complete these for massive XP rewards distributed across ALL life areas:

| Milestone | Description | XP Reward |
|-----------|-------------|-----------|
| **Algorithms Paper** | Research paper on algorithms | 847 XP |
| **Codeforces 2000** | Reach 2000 Elo on Codeforces | 1,203 XP |
| **Weight 107kg** | Reach target weight of 107 kg | 672 XP |
| **Edinburgh Masters** | Acceptance to Edinburgh University | 1,847 XP |
| **Gold Medal** | International championship gold | 2,341 XP |

**Total Possible:** 6,910 XP when all milestones are completed!

---

## 📖 Usage Guide

### Daily Workflow

#### Morning Routine
1. **Log Shower** (10 XP + streak bonuses)
2. **Log Workout** (100+ push-ups for full XP)
3. **Check Dashboard** to see your stats

#### During the Day
4. **Add Todos** with deadlines for tasks
5. **Log Learning Sessions** (20 XP per hour)
6. **Complete Projects** as you finish them

#### Evening Routine
7. **Log Sleep** hours from previous night
8. **Log Screen Time** for the day
9. **Complete Pending Todos**
10. **View Daily Summary** to see your grade

### Creating Projects
```
1. Click "Projects" → "Add Project"
2. Enter: Name, Value (Lari), Deadline (YYYY-MM-DD)
3. Complete projects on time for maximum XP
```

### Creating Todos
```
1. Click "Todos" → "Add Todo"
2. Enter: Task description, Base XP, Deadline
3. Select relevant life area
4. Complete before deadline for XP multiplier
```

### Logging Learning
```
1. Click "Learning"
2. Select area (University, Work Skills, etc.)
3. Enter: Hours spent, Topic studied
4. Earn 20 XP per hour logged
```

---

## 💾 Data Structure

All data is stored in `life_rpg_personal.json`:

```json
{
  "life_areas": {
    "Area Name": {
      "level": 1,
      "xp": 0,
      "last_active": "2025-01-01"
    }
  },
  "projects": [...],
  "todos": [...],
  "habits": {
    "shower": {"streak": 0, "last_done": null},
    "workout": {"streak": 0, "last_done": null, "pushup_history": []}
  },
  "epic_milestones": {...},
  "screen_time": {"daily_log": {}},
  "social_interactions": {"weekly_count": 0},
  "income": {
    "monthly_goal": 10000,
    "current_month_earnings": 0
  },
  "daily_scores": [],
  "achievements": []
}
```

---

## 💡 Tips & Strategies

### Maximizing XP Gains
1. **Complete tasks early** → 1.5x XP multiplier
2. **Maintain daily streaks** → Consistency bonuses
3. **Log learning daily** → 20 XP per hour adds up
4. **Exceed push-up requirements** → Bonus XP
5. **Complete high-value projects** → Income + XP

### Avoiding XP Loss
1. **Stay under 2h screen time** → Avoid penalties
2. **Limit social interactions** → Max 3 per week
3. **Log in daily** → Prevent XP decay
4. **Complete tasks on time** → Avoid 0.5x multiplier

### Efficient Leveling
1. **Focus on high-XP activities** → Learning sessions, projects
2. **Build streaks early** → Compounds over time
3. **Set realistic deadlines** → Ensure early completion
4. **Distribute effort** → Level all areas to reduce decay impact

### Grade Optimization
- **SSS (95-100):** Complete all habits + 3 todos + stay under limits
- **SS (90-94):** Miss 1 small item
- **S (85-89):** Miss 1-2 items
- **A grades (70-84):** Solid daily performance
- **Below A:** Need improvement in multiple areas

---

## 🗺️ Roadmap

### Planned Features
- [ ] Samsung Health integration for automatic sleep/activity tracking
- [ ] Screen time API integration (Samsung app sync)
- [ ] Weekly/monthly statistics and graphs
- [ ] Achievement notification animations
- [ ] Sound effects for level-ups
- [ ] Backup and export functionality
- [ ] Multi-profile support
- [ ] Dark/light theme toggle
- [ ] Mobile companion app

### Known Limitations
- Screen time requires manual entry
- Sleep data requires manual entry (Samsung Health integration planned)
- No cloud sync (local JSON storage only)
- Single user per installation

---

## 📊 Sample Goals Timeline

### October 2024 - February 2025 (5 months)

**Income Goal:** 10,000 Lari/month
- Month 1 (Oct): 2,000 Lari - Setup projects
- Month 2 (Nov): 4,000 Lari - Increase output
- Month 3 (Dec): 6,000 Lari - Optimize workflow
- Month 4 (Jan): 8,000 Lari - Scale up
- Month 5 (Feb): 10,000 Lari - **GOAL ACHIEVED**

**Skill Development:**
- React mastery: 3 months intensive (90+ hours)
- DevOps proficiency: 2 months (60+ hours)
- Database expertise: 2 months (60+ hours)

**Epic Milestones:**
- Codeforces 2000 Elo: 4-5 months daily practice
- Weight 107kg: 3-4 months fitness routine
- Algorithms paper: 2-3 months research
- Edinburgh application: 4 months preparation
- Gold medal: Tournament-dependent

---

## 🤝 Contributing

This is a personal project tailored to specific goals. However, if you want to adapt it for your own use:

1. Fork the repository
2. Modify `life_areas` in `create_initial_data()`
3. Adjust constants (DAILY_DECAY, PUSHUP_REQUIREMENT, etc.)
4. Customize epic milestones
5. Set your own goals

---

## 📄 License

Personal use project. Feel free to adapt for your own goals.

---

## 🎮 Final Notes

**Remember:** This system is designed to be challenging. The daily decay, strict requirements, and time-based multipliers push you to stay consistent and efficient. Treat every day like a new quest, every task like a boss fight, and every milestone like a legendary achievement.

**Your character is Level 1 today. What level will you be in 6 months?**

⚔️ **Start your journey. Level up your life. Achieve your dreams.** ⚔️

---

*Created: October 2024*  
*Target Completion: February 2025*  
*Current Total Level: Track in dashboard*  
*Epic Milestones Remaining: 5*

**Let the grind begin! 🚀**

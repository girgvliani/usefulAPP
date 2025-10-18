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

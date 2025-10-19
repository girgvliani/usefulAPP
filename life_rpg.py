import json
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
import random

class PersonalLifeRPG:
    def __init__(self, data_file='life_rpg_personal.json'):
        self.data_file = data_file
        self.DAILY_DECAY = 5  # Same as base exercise XP
        self.PUSHUP_REQUIREMENT = 100
        self.SCREEN_TIME_LIMIT = 2  # hours
        self.SOCIAL_LIMIT = 3  # times per week
        self.data = self.load_data()
        self.apply_daily_decay()
        
    def load_data(self):
        """Load existing data or create new profile"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        else:
            return self.create_initial_data()
    
    def create_initial_data(self):
        """Initialize the data structure"""
        return {
            'life_areas': {
                'Health - Exercise': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Health - Sleep': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Health - Hygiene': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'University - Databases': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'University - Software engineering': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'University - App development': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'University - CyberSecurity': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'University - Fuzzing': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'University - Research Basics': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Work Skills - Gintama': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Work Skills - React': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Work Skills - SEO': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Work Skills - DevOps': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Work Skills - Databases': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Work Skills - iOS': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Work Skills - Android': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Personal Sciences - Math': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Personal Sciences - Physics': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Personal Sciences - Chemistry': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Personal Sciences - Game Dev': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Memory Techniques': {'level': 1, 'xp': 0, 'last_active': self.today()},
                'Social Balance': {'level': 1, 'xp': 0, 'last_active': self.today()},
            },
            'projects': [],
            'todos': [],
            'habits': {
                'shower': {'streak': 0, 'last_done': None},
                'workout': {'streak': 0, 'last_done': None, 'pushup_history': []},
            },
            'epic_milestones': {
                'algorithms_paper': {'completed': False, 'xp_reward': 847, 'description': 'Research paper on algorithms'},
                'codeforces_2000': {'completed': False, 'xp_reward': 1203, 'description': '2000 Elo on Codeforces'},
                'weight_107kg': {'completed': False, 'xp_reward': 672, 'description': 'Reach 107 kg weight'},
                'edinburgh_masters': {'completed': False, 'xp_reward': 1847, 'description': 'Edinburgh University Masters acceptance'},
                'gold_medal': {'completed': False, 'xp_reward': 2341, 'description': 'Gold medal at international championship'},
            },
            'screen_time': {
                'daily_log': {},
                'weekly_violations': 0
            },
            'social_interactions': {
                'weekly_count': 0,
                'week_start': self.today()
            },
            'income': {
                'monthly_goal': 10000,
                'current_month_earnings': 0,
                'target_month': '2025-02',
                'manual_override': None
            },
            'daily_scores': [],
            'achievements': [],
            'last_login': self.today()
        }
    
    def today(self):
        return datetime.now().strftime('%Y-%m-%d')
    
    def save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def apply_daily_decay(self):
        """Apply XP decay to all inactive areas"""
        today = self.today()
        if self.data['last_login'] == today:
            return
        
        days_passed = (datetime.strptime(today, '%Y-%m-%d') - 
                      datetime.strptime(self.data['last_login'], '%Y-%m-%d')).days
        
        if days_passed > 0:
            print(f"\n⏰ {days_passed} day(s) have passed. Applying decay...")
            for area, stats in self.data['life_areas'].items():
                decay_amount = self.DAILY_DECAY * days_passed
                stats['xp'] = max(0, stats['xp'] - decay_amount)
                stats['level'] = self.calculate_level(stats['xp'])
                print(f"   {area}: -{decay_amount} XP")
            
            self.data['last_login'] = today
            self.save_data()
    
    def calculate_level(self, xp):
        """150 XP per level (challenging)"""
        return (xp // 150) + 1
    
    def calculate_time_multiplier(self, deadline_str, completed_str):
        """Calculate XP multiplier based on completion time"""
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        completed = datetime.strptime(completed_str, '%Y-%m-%d')
        days_diff = (completed - deadline).days
        
        if days_diff <= 0:  # On time or early
            return 1.5
        elif days_diff <= 7:  # Within a week late
            return 1.0
        else:  # More than 1.5x time
            return 0.5
    
    def add_xp(self, area, points, reason=""):
        """Add XP to a life area"""
        if area in self.data['life_areas']:
            old_xp = self.data['life_areas'][area]['xp']
            old_level = self.data['life_areas'][area]['level']
            
            self.data['life_areas'][area]['xp'] += points
            self.data['life_areas'][area]['last_active'] = self.today()
            new_level = self.calculate_level(self.data['life_areas'][area]['xp'])
            self.data['life_areas'][area]['level'] = new_level
            
            if new_level > old_level:
                print(f"🎉 LEVEL UP! {area} is now Level {new_level}!")
                self.check_achievements(area, new_level)
            
            msg = f"+{points} XP → {area}"
            if reason:
                msg += f" ({reason})"
            print(msg)
            
            self.save_data()
        else:
            print(f"Area '{area}' not found!")
    
    def track_pushups(self, count):
        """Track pushup workout with consistency bonus"""
        today = self.today()
        habit = self.data['habits']['workout']
        
        # Update streak
        if habit['last_done']:
            last = datetime.strptime(habit['last_done'], '%Y-%m-%d')
            diff = (datetime.strptime(today, '%Y-%m-%d') - last).days
            if diff == 1:
                habit['streak'] += 1
            elif diff > 1:
                habit['streak'] = 1
        else:
            habit['streak'] = 1
        
        habit['last_done'] = today
        habit['pushup_history'].append({'date': today, 'count': count})
        
        # Calculate XP
        base_xp = self.DAILY_DECAY  # 15 XP
        if count >= self.PUSHUP_REQUIREMENT:
            xp = base_xp
            # Bonus for exceeding requirement
            if count > self.PUSHUP_REQUIREMENT:
                bonus = min((count - self.PUSHUP_REQUIREMENT) // 10, 10)
                xp += bonus
                print(f"💪 Exceeded requirement! +{bonus} bonus XP")
            
            # Consistency bonus
            if habit['streak'] >= 7:
                consistency_bonus = habit['streak'] // 7 * 5
                xp += consistency_bonus
                print(f"🔥 {habit['streak']} day streak! +{consistency_bonus} consistency XP")
            
            self.add_xp('Health - Exercise', xp, f"{count} push-ups")
        else:
            print(f"⚠️  Only {count}/{self.PUSHUP_REQUIREMENT} push-ups. Keep pushing!")
        
        self.save_data()
    
    def check_shower(self):
        """Mark daily shower as complete"""
        today = self.today()
        habit = self.data['habits']['shower']
        
        if habit['last_done'] == today:
            print("Already logged shower today!")
            return
        
        # Update streak
        if habit['last_done']:
            last = datetime.strptime(habit['last_done'], '%Y-%m-%d')
            diff = (datetime.strptime(today, '%Y-%m-%d') - last).days
            if diff == 1:
                habit['streak'] += 1
            elif diff > 1:
                habit['streak'] = 1
        else:
            habit['streak'] = 1
        
        habit['last_done'] = today
        self.add_xp('Health - Hygiene', 10, "Daily shower")
        
        if habit['streak'] >= 7:
            print(f"🚿 {habit['streak']} day shower streak!")
        
        self.save_data()
    
    def log_sleep(self, hours):
        """Log sleep hours"""
        xp = 0
        if hours >= 7 and hours <= 8:
            xp = 20
            msg = "Optimal sleep!"
        elif hours >= 6:
            xp = 10
            msg = "Decent sleep"
        else:
            xp = 5
            msg = "Need more sleep!"
        
        self.add_xp('Health - Sleep', xp, f"{hours}h - {msg}")
    
    def track_screen_time(self, hours):
        """Track daily screen time with penalties"""
        today = self.today()
        self.data['screen_time']['daily_log'][today] = hours
        
        if hours > self.SCREEN_TIME_LIMIT:
            penalty = int((hours - self.SCREEN_TIME_LIMIT) * 10)
            print(f"⚠️  Screen time exceeded limit! -{penalty} XP penalty")
            # Apply penalty across all areas
            for area in self.data['life_areas']:
                self.data['life_areas'][area]['xp'] = max(0, self.data['life_areas'][area]['xp'] - penalty // len(self.data['life_areas']))
        else:
            print(f"✅ Screen time under control: {hours}h/{self.SCREEN_TIME_LIMIT}h")
        
        self.save_data()
    
    def log_social_interaction(self):
        """Log going out/helping friends with weekly limit"""
        today = self.today()
        week_start = datetime.strptime(self.data['social_interactions']['week_start'], '%Y-%m-%d')
        today_dt = datetime.strptime(today, '%Y-%m-%d')
        
        # Reset weekly counter if new week
        if (today_dt - week_start).days >= 7:
            self.data['social_interactions']['weekly_count'] = 0
            self.data['social_interactions']['week_start'] = today
        
        self.data['social_interactions']['weekly_count'] += 1
        count = self.data['social_interactions']['weekly_count']
        
        if count > self.SOCIAL_LIMIT:
            penalty = (count - self.SOCIAL_LIMIT) * 20
            print(f"⚠️  Social interaction limit exceeded ({count}/{self.SOCIAL_LIMIT})! -{penalty} XP")
            for area in self.data['life_areas']:
                self.data['life_areas'][area]['xp'] = max(0, self.data['life_areas'][area]['xp'] - penalty // len(self.data['life_areas']))
        else:
            print(f"✅ Social balance maintained: {count}/{self.SOCIAL_LIMIT} this week")
            self.add_xp('Social Balance', 5, "Balanced interaction")
        
        self.save_data()
    
    def add_project(self, name, value_lari, deadline):
        """Add new project"""
        project = {
            'id': len(self.data['projects']) + 1,
            'name': name,
            'value': value_lari,
            'deadline': deadline,
            'completed': False,
            'completion_date': None,
            'created': self.today()
        }
        self.data['projects'].append(project)
        print(f"📋 Project added: {name} ({value_lari} Lari)")
        self.save_data()
    
    def complete_project(self, project_id):
        """Complete a project and earn money + XP"""
        for project in self.data['projects']:
            if project['id'] == project_id and not project['completed']:
                project['completed'] = True
                project['completion_date'] = self.today()
                
                # Add to monthly earnings
                self.data['income']['current_month_earnings'] += project['value']
                
                # Calculate XP with time multiplier
                multiplier = self.calculate_time_multiplier(project['deadline'], self.today())
                base_xp = project['value'] // 10  # 1 Lari = 0.1 XP base
                xp = int(base_xp * multiplier)
                
                # Distribute XP across work skills
                work_areas = [a for a in self.data['life_areas'] if a.startswith('Work Skills')]
                xp_per_area = xp // len(work_areas)
                for area in work_areas:
                    self.add_xp(area, xp_per_area, f"Project: {project['name']}")
                
                print(f"💰 Project completed: {project['name']} (+{project['value']} Lari)")
                print(f"📊 Monthly progress: {self.data['income']['current_month_earnings']}/{self.data['income']['monthly_goal']} Lari")
                
                self.save_data()
                return
        print("Project not found or already completed!")
    
    def add_todo(self, task, area, base_xp, deadline):
        """Add todo with time-based XP"""
        todo = {
            'id': len(self.data['todos']) + 1,
            'task': task,
            'area': area,
            'base_xp': base_xp,
            'deadline': deadline,
            'completed': False,
            'created': self.today()
        }
        self.data['todos'].append(todo)
        print(f"✅ Todo added: {task} (up to {int(base_xp * 1.5)} XP if early)")
        self.save_data()
    
    def complete_todo(self, todo_id):
        """Complete todo with time multiplier"""
        for todo in self.data['todos']:
            if todo['id'] == todo_id and not todo['completed']:
                todo['completed'] = True
                todo['completion_date'] = self.today()
                
                multiplier = self.calculate_time_multiplier(todo['deadline'], self.today())
                xp = int(todo['base_xp'] * multiplier)
                
                self.add_xp(todo['area'], xp, f"Task: {todo['task']}")
                print(f"✨ Todo completed: {todo['task']}")
                
                self.save_data()
                return
        print("Todo not found or already completed!")
    
    def complete_epic_milestone(self, milestone_key):
        """Complete an epic milestone"""
        if milestone_key in self.data['epic_milestones']:
            milestone = self.data['epic_milestones'][milestone_key]
            if not milestone['completed']:
                milestone['completed'] = True
                
                # Massive XP reward distributed across all areas
                xp_per_area = milestone['xp_reward'] // len(self.data['life_areas'])
                for area in self.data['life_areas']:
                    self.add_xp(area, xp_per_area, "EPIC MILESTONE")
                
                print(f"\n🏆🏆🏆 EPIC MILESTONE COMPLETED! 🏆🏆🏆")
                print(f"{milestone['description']}")
                print(f"+{milestone['xp_reward']} TOTAL XP!")
                
                self.save_data()
            else:
                print("Milestone already completed!")
        else:
            print("Milestone not found!")
    
    def calculate_daily_score(self):
        """Calculate daily performance score"""
        score = 0
        today = self.today()
        
        # Habits completed (40 points)
        if self.data['habits']['shower']['last_done'] == today:
            score += 20
        if self.data['habits']['workout']['last_done'] == today:
            score += 20
        
        # Todos completed today (30 points)
        completed_today = [t for t in self.data['todos'] 
                          if t.get('completion_date') == today]
        score += min(len(completed_today) * 10, 30)
        
        # Screen time (15 points)
        if today in self.data['screen_time']['daily_log']:
            hours = self.data['screen_time']['daily_log'][today]
            if hours <= self.SCREEN_TIME_LIMIT:
                score += 15
        
        # Social balance (15 points)
        if self.data['social_interactions']['weekly_count'] <= self.SOCIAL_LIMIT:
            score += 15
        
        # Convert to grade
        if score >= 95:
            grade = "SSS"
        elif score >= 90:
            grade = "SS"
        elif score >= 85:
            grade = "S"
        elif score >= 80:
            grade = "A+"
        elif score >= 75:
            grade = "A"
        elif score >= 70:
            grade = "A-"
        elif score >= 60:
            grade = "B"
        elif score >= 50:
            grade = "C"
        elif score >= 40:
            grade = "D"
        else:
            grade = "F"
        
        return score, grade
    
    def daily_summary(self):
        """Show end of day summary"""
        score, grade = self.calculate_daily_score()
        
        print("\n" + "="*60)
        print("📊 DAILY PERFORMANCE REPORT")
        print("="*60)
        print(f"Score: {score}/100")
        print(f"Grade: {grade}")
        print("="*60)
        
        # Save score
        self.data['daily_scores'].append({
            'date': self.today(),
            'score': score,
            'grade': grade
        })
        self.save_data()
    
    def check_achievements(self, area, level):
        """Check and award achievements"""
        achievement_thresholds = {5: "Bronze", 10: "Silver", 20: "Gold", 30: "Platinum"}
        if level in achievement_thresholds:
            achievement = f"{area} - {achievement_thresholds[level]} Tier"
            if achievement not in self.data['achievements']:
                self.data['achievements'].append(achievement)
                print(f"🏅 Achievement Unlocked: {achievement}!")
    
    def view_stats(self):
        """Display comprehensive stats"""
        print("\n" + "="*70)
        print("⚔️  YOUR CHARACTER STATS ⚔️".center(70))
        print("="*70)
        
        total_level = sum(area['level'] for area in self.data['life_areas'].values())/self.data['life_areas'].__len__()
        total_xp = sum(area['xp'] for area in self.data['life_areas'].values())
        print(f"Total Level: {total_level} | Total XP: {total_xp}")
        print("-"*70)
        
        # Group by category
        categories = {}
        for area, stats in self.data['life_areas'].items():
            category = area.split(' - ')[0]
            if category not in categories:
                categories[category] = []
            categories[category].append((area, stats))
        
        for category, areas in categories.items():
            print(f"\n📚 {category.upper()}")
            for area, stats in areas:
                short_name = area.split(' - ')[-1] if ' - ' in area else area
                xp_to_next = 150 - (stats['xp'] % 150)
                progress = "█" * (stats['xp'] % 150 // 15) + "░" * (10 - stats['xp'] % 150 // 15)
                print(f"  {short_name:20} | Lv {stats['level']:2} | [{progress}] {xp_to_next:3} XP to next")
        
        print("\n" + "="*70)
        
        # Habits
        print("\n💪 HABIT STREAKS")
        print("-"*70)
        for habit, data in self.data['habits'].items():
            print(f"{habit.capitalize():15} | 🔥 {data['streak']} day streak")
        
        # Income progress
        print("\n💰 INCOME PROGRESS")
        print("-"*70)
        current = self.data['income']['current_month_earnings']
        goal = self.data['income']['monthly_goal']
        progress_pct = (current / goal * 100) if goal > 0 else 0
        bar_length = int(progress_pct / 2)
        bar = "█" * bar_length + "░" * (50 - bar_length)
        print(f"[{bar}] {progress_pct:.1f}%")
        print(f"{current:,} / {goal:,} Lari")
        
        # Epic Milestones
        print("\n🏆 EPIC MILESTONES")
        print("-"*70)
        for key, milestone in self.data['epic_milestones'].items():
            status = "✅ COMPLETED" if milestone['completed'] else "⏳ In Progress"
            print(f"{milestone['description']:45} | {status}")
        
        print("\n" + "="*70)
    
    def create_visualization(self):
        """Create comprehensive visualization"""
        fig = plt.figure(figsize=(16, 10))
        
        # 1. Life areas pie chart
        ax1 = plt.subplot(2, 3, 1)
        categories = {}
        for area, stats in self.data['life_areas'].items():
            category = area.split(' - ')[0]
            categories[category] = categories.get(category, 0) + stats['level']
        
        ax1.pie(categories.values(), labels=categories.keys(), autopct='%1.1f%%', startangle=90)
        ax1.set_title('Life Balance by Category', fontweight='bold')
        
        # 2. Top 10 areas by level
        ax2 = plt.subplot(2, 3, 2)
        sorted_areas = sorted(self.data['life_areas'].items(), key=lambda x: x[1]['level'], reverse=True)[:10]
        names = [a[0].split(' - ')[-1] for a in sorted_areas]
        levels = [a[1]['level'] for a in sorted_areas]
        bars = ax2.barh(names, levels, color=plt.cm.viridis(range(len(names))))
        ax2.set_xlabel('Level')
        ax2.set_title('Top 10 Skills', fontweight='bold')
        ax2.invert_yaxis()
        
        # 3. Income progress
        ax3 = plt.subplot(2, 3, 3)
        current = self.data['income']['current_month_earnings']
        goal = self.data['income']['monthly_goal']
        remaining = max(goal - current, 0)
        ax3.pie([current, remaining], labels=['Earned', 'Remaining'], 
                autopct=lambda pct: f'{pct:.1f}%\n{int(pct/100 * goal):,} ₾',
                colors=['#4CAF50', '#FFC107'], startangle=90)
        ax3.set_title(f'Income Progress\n{current:,} / {goal:,} Lari', fontweight='bold')
        
        # 4. Daily scores trend
        ax4 = plt.subplot(2, 3, 4)
        if self.data['daily_scores']:
            recent_scores = self.data['daily_scores'][-30:]  # Last 30 days
            dates = [s['date'] for s in recent_scores]
            scores = [s['score'] for s in recent_scores]
            ax4.plot(range(len(scores)), scores, marker='o', linewidth=2, markersize=4)
            ax4.set_ylabel('Score')
            ax4.set_title('Daily Performance (Last 30 Days)', fontweight='bold')
            ax4.axhline(y=70, color='r', linestyle='--', alpha=0.3, label='A- threshold')
            ax4.grid(True, alpha=0.3)
            ax4.set_ylim(0, 100)
        
        # 5. Habit streaks
        ax5 = plt.subplot(2, 3, 5)
        habits = list(self.data['habits'].keys())
        streaks = [self.data['habits'][h]['streak'] for h in habits]
        bars = ax5.bar(habits, streaks, color=['#FF6B6B', '#4ECDC4'])
        ax5.set_ylabel('Days')
        ax5.set_title('Current Habit Streaks', fontweight='bold')
        for bar, streak in zip(bars, streaks):
            height = bar.get_height()
            ax5.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(streak)}', ha='center', va='bottom')
        
        # 6. Epic milestones
        ax6 = plt.subplot(2, 3, 6)
        milestone_names = [m['description'][:20] for m in self.data['epic_milestones'].values()]
        completed = [1 if m['completed'] else 0 for m in self.data['epic_milestones'].values()]
        colors = ['#4CAF50' if c else '#CCCCCC' for c in completed]
        ax6.barh(milestone_names, [1]*len(milestone_names), color=colors)
        ax6.set_xlim(0, 1)
        ax6.set_xticks([])
        ax6.set_title('Epic Milestones', fontweight='bold')
        ax6.invert_yaxis()
        
        plt.tight_layout()
        plt.savefig('life_rpg_dashboard.png', dpi=300, bbox_inches='tight')
        print("\n📊 Dashboard saved as 'life_rpg_dashboard.png'")
        plt.show()


def main():
    rpg = PersonalLifeRPG()
    
    while True:
        print("\n" + "="*60)
        print("🎮 PERSONAL LIFE RPG".center(60))
        print("="*60)
        print("1.  📊 View Stats & Progress")
        print("2.  💪 Log Workout (Push-ups)")
        print("3.  🚿 Log Shower")
        print("4.  😴 Log Sleep")
        print("5.  📱 Log Screen Time")
        print("6.  👥 Log Social Interaction")
        print("7.  📋 Add Project")
        print("8.  ✅ Complete Project")
        print("9.  📝 Add Todo/Task")
        print("10. ✨ Complete Todo/Task")
        print("11. 📚 Log Learning Session")
        print("12. 🧠 Log Memory Practice")
        print("13. 🏆 Complete Epic Milestone")
        print("14. 📈 View Today's Tasks")
        print("15. 💰 View/Edit Income")
        print("16. 🎨 Generate Dashboard")
        print("17. 📊 Daily Summary")
        print("18. 🔧 Manual XP Adjustment")
        print("19. ❌ Exit")
        print("="*60)
        
        choice = input("\n👉 Choose option: ").strip()
        
        if choice == '1':
            rpg.view_stats()
        
        elif choice == '2':
            count = int(input("How many push-ups did you do? "))
            rpg.track_pushups(count)
        
        elif choice == '3':
            rpg.check_shower()
        
        elif choice == '4':
            hours = float(input("How many hours did you sleep? "))
            rpg.log_sleep(hours)
        
        elif choice == '5':
            hours = float(input("Screen time today (hours)? "))
            rpg.track_screen_time(hours)
        
        elif choice == '6':
            rpg.log_social_interaction()
        
        elif choice == '7':
            name = input("Project name: ")
            value = int(input("Project value (Lari): "))
            deadline = input("Deadline (YYYY-MM-DD): ")
            rpg.add_project(name, value, deadline)
        
        elif choice == '8':
            print("\n📋 ACTIVE PROJECTS:")
            active_projects = [p for p in rpg.data['projects'] if not p['completed']]
            if not active_projects:
                print("No active projects!")
                continue
            for p in active_projects:
                print(f"[{p['id']}] {p['name']} - {p['value']} Lari (Due: {p['deadline']})")
            project_id = int(input("\nProject ID to complete: "))
            rpg.complete_project(project_id)
        
        elif choice == '9':
            task = input("Task description: ")
            print("\nAvailable areas:")
            for i, area in enumerate(rpg.data['life_areas'].keys(), 1):
                print(f"{i}. {area}")
            area_idx = int(input("Choose area number: ")) - 1
            area = list(rpg.data['life_areas'].keys())[area_idx]
            base_xp = int(input("Base XP (will multiply based on completion time): "))
            deadline = input("Deadline (YYYY-MM-DD): ")
            rpg.add_todo(task, area, base_xp, deadline)
        
        elif choice == '10':
            print("\n📝 PENDING TASKS:")
            pending = [t for t in rpg.data['todos'] if not t['completed']]
            if not pending:
                print("No pending tasks!")
                continue
            for t in pending:
                print(f"[{t['id']}] {t['task']} - {t['area']} (Due: {t['deadline']})")
            todo_id = int(input("\nTask ID to complete: "))
            rpg.complete_todo(todo_id)
        
        elif choice == '11':
            print("\nLearning areas:")
            learning_areas = [a for a in rpg.data['life_areas'].keys() 
                            if 'University' in a or 'Work Skills' in a or 'Personal Sciences' in a]
            for i, area in enumerate(learning_areas, 1):
                print(f"{i}. {area}")
            area_idx = int(input("Choose area: ")) - 1
            area = learning_areas[area_idx]
            hours = float(input("Hours spent: "))
            xp = int(hours * 20)  # 20 XP per hour
            topic = input("What did you study? ")
            rpg.add_xp(area, xp, f"{hours}h on {topic}")
        
        elif choice == '12':
            minutes = int(input("Memory practice minutes: "))
            xp = minutes // 5  # 1 XP per 5 minutes
            technique = input("What technique? (e.g., palace, linking): ")
            rpg.add_xp('Memory Techniques', xp, f"{minutes}min - {technique}")
        
        elif choice == '13':
            print("\n🏆 EPIC MILESTONES:")
            for i, (key, milestone) in enumerate(rpg.data['epic_milestones'].items(), 1):
                status = "✅" if milestone['completed'] else "⏳"
                print(f"{i}. {status} {milestone['description']}")
            
            choice_m = int(input("\nWhich milestone did you complete? ")) - 1
            milestone_key = list(rpg.data['epic_milestones'].keys())[choice_m]
            confirm = input(f"Confirm completion of '{rpg.data['epic_milestones'][milestone_key]['description']}'? (yes/no): ")
            if confirm.lower() == 'yes':
                rpg.complete_epic_milestone(milestone_key)
        
        elif choice == '14':
            print("\n📅 TODAY'S AGENDA:")
            print("="*60)
            
            # Pending tasks
            today_tasks = [t for t in rpg.data['todos'] 
                          if not t['completed'] and t['deadline'] <= rpg.today()]
            if today_tasks:
                print("\n🔥 URGENT TASKS (Due today or overdue):")
                for t in today_tasks:
                    print(f"  • {t['task']} ({t['area']})")
            
            # Upcoming tasks
            upcoming = [t for t in rpg.data['todos'] 
                       if not t['completed'] and t['deadline'] > rpg.today()]
            if upcoming:
                print("\n📋 UPCOMING TASKS:")
                for t in sorted(upcoming, key=lambda x: x['deadline'])[:5]:
                    print(f"  • {t['task']} (Due: {t['deadline']})")
            
            # Habits
            print("\n✅ DAILY HABITS:")
            today = rpg.today()
            shower_done = rpg.data['habits']['shower']['last_done'] == today
            workout_done = rpg.data['habits']['workout']['last_done'] == today
            print(f"  {'✅' if shower_done else '⬜'} Shower")
            print(f"  {'✅' if workout_done else '⬜'} Workout (100+ push-ups)")
            
            print("="*60)
        
        elif choice == '15':
            print("\n💰 INCOME TRACKER:")
            print(f"Current month earnings: {rpg.data['income']['current_month_earnings']:,} Lari")
            print(f"Monthly goal: {rpg.data['income']['monthly_goal']:,} Lari")
            print(f"Target month: {rpg.data['income']['target_month']}")
            
            edit = input("\nEdit income? (yes/no): ")
            if edit.lower() == 'yes':
                manual = int(input("Enter corrected amount (Lari): "))
                rpg.data['income']['current_month_earnings'] = manual
                rpg.save_data()
                print("✅ Income updated!")
        
        elif choice == '16':
            rpg.create_visualization()
        
        elif choice == '17':
            rpg.daily_summary()
        
        elif choice == '18':
            print("\nAvailable areas:")
            for i, area in enumerate(rpg.data['life_areas'].keys(), 1):
                print(f"{i}. {area}")
            area_idx = int(input("Choose area: ")) - 1
            area = list(rpg.data['life_areas'].keys())[area_idx]
            xp = int(input("XP to add (negative to subtract): "))
            reason = input("Reason: ")
            rpg.add_xp(area, xp, reason)
        
        elif choice == '19':
            print("\n🎮 Keep grinding! See you tomorrow! 🚀")
            rpg.daily_summary()
            break
        
        else:
            print("❌ Invalid option. Try again.")


if __name__ == "__main__":
    print("\n🎮 Welcome to Your Personal Life RPG! 🎮")
    print("Loading your character...")
    main()
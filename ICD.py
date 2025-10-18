import pygame
import json
import math
from datetime import datetime
import os

class LifeRPGVisual:
    def __init__(self, data_file='life_rpg_personal.json'):
        pygame.init()
        
        # Screen setup
        self.WIDTH = 1400
        self.HEIGHT = 900
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Life RPG - Your Personal Dashboard")
        
        # Colors
        self.BG_COLOR = (20, 24, 36)
        self.CARD_BG = (30, 34, 46)
        self.ACCENT = (88, 166, 255)
        self.SUCCESS = (76, 209, 55)
        self.WARNING = (255, 193, 7)
        self.DANGER = (220, 53, 69)
        self.TEXT_PRIMARY = (255, 255, 255)
        self.TEXT_SECONDARY = (180, 180, 180)
        self.XP_BAR_BG = (50, 54, 66)
        self.XP_BAR_FILL = (88, 166, 255)
        
        # Fonts
        self.font_title = pygame.font.Font(None, 48)
        self.font_heading = pygame.font.Font(None, 36)
        self.font_normal = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 22)
        
        # Data
        self.data_file = data_file
        self.data = self.load_data()
        
        # Animation
        self.animation_time = 0
        self.particle_systems = []
        self.clock = pygame.time.Clock()
        
        # Current view
        self.current_view = "dashboard"  # dashboard, stats, milestones
        
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return None
    
    def draw_gradient_rect(self, surface, color1, color2, rect):
        """Draw a gradient rectangle"""
        for i in range(rect.height):
            alpha = i / rect.height
            color = (
                int(color1[0] * (1 - alpha) + color2[0] * alpha),
                int(color1[1] * (1 - alpha) + color2[1] * alpha),
                int(color1[2] * (1 - alpha) + color2[2] * alpha)
            )
            pygame.draw.line(surface, color, 
                           (rect.x, rect.y + i), 
                           (rect.x + rect.width, rect.y + i))
    
    def draw_card(self, x, y, width, height, title=None):
        """Draw a card with shadow"""
        # Shadow
        shadow_rect = pygame.Rect(x + 5, y + 5, width, height)
        pygame.draw.rect(self.screen, (10, 14, 26), shadow_rect, border_radius=15)
        
        # Card
        card_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, self.CARD_BG, card_rect, border_radius=15)
        pygame.draw.rect(self.screen, self.ACCENT, card_rect, 2, border_radius=15)
        
        # Title
        if title:
            title_surf = self.font_heading.render(title, True, self.TEXT_PRIMARY)
            self.screen.blit(title_surf, (x + 20, y + 15))
            
            # Title underline
            pygame.draw.line(self.screen, self.ACCENT, 
                           (x + 20, y + 55), 
                           (x + width - 20, y + 55), 2)
        
        return card_rect
    
    def draw_xp_bar(self, x, y, width, current_xp, level):
        """Draw animated XP progress bar"""
        xp_in_level = current_xp % 150
        progress = xp_in_level / 150
        
        # Background
        bg_rect = pygame.Rect(x, y, width, 30)
        pygame.draw.rect(self.screen, self.XP_BAR_BG, bg_rect, border_radius=15)
        
        # Fill with gradient
        fill_width = int(width * progress)
        if fill_width > 0:
            fill_rect = pygame.Rect(x, y, fill_width, 30)
            self.draw_gradient_rect(self.screen, self.ACCENT, (50, 120, 200), fill_rect)
            
            # Shine effect
            shine_y = y + 8
            shine_width = min(fill_width, int(width * 0.3))
            pygame.draw.rect(self.screen, (150, 200, 255, 100), 
                           (x, shine_y, shine_width, 10), border_radius=5)
        
        # Border
        pygame.draw.rect(self.screen, self.ACCENT, bg_rect, 2, border_radius=15)
        
        # Text
        xp_text = f"Level {level} | {xp_in_level}/150 XP"
        text_surf = self.font_small.render(xp_text, True, self.TEXT_PRIMARY)
        text_rect = text_surf.get_rect(center=(x + width // 2, y + 15))
        self.screen.blit(text_surf, text_rect)
    
    def draw_circular_progress(self, x, y, radius, progress, color, label, value):
        """Draw circular progress indicator"""
        # Background circle
        pygame.draw.circle(self.screen, self.XP_BAR_BG, (x, y), radius, 8)
        
        # Progress arc
        if progress > 0:
            angle = int(360 * progress)
            points = [(x, y)]
            for i in range(angle + 1):
                rad = math.radians(i - 90)
                px = x + int(radius * math.cos(rad))
                py = y + int(radius * math.sin(rad))
                points.append((px, py))
            points.append((x, y))
            
            if len(points) > 2:
                pygame.draw.polygon(self.screen, color + (100,), points)
        
        pygame.draw.circle(self.screen, color, (x, y), radius, 8)
        
        # Inner circle
        pygame.draw.circle(self.screen, self.CARD_BG, (x, y), radius - 15)
        
        # Text
        value_surf = self.font_heading.render(str(value), True, self.TEXT_PRIMARY)
        value_rect = value_surf.get_rect(center=(x, y - 10))
        self.screen.blit(value_surf, value_rect)
        
        label_surf = self.font_small.render(label, True, self.TEXT_SECONDARY)
        label_rect = label_surf.get_rect(center=(x, y + 15))
        self.screen.blit(label_surf, label_rect)
    
    def draw_character_avatar(self, x, y, size, total_level):
        """Draw animated character avatar"""
        # Pulsing effect
        pulse = math.sin(self.animation_time * 2) * 5
        current_size = size + int(pulse)
        
        # Outer glow
        for i in range(3):
            glow_size = current_size + (3 - i) * 10
            alpha = 50 - i * 15
            glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (*self.ACCENT, alpha), 
                             (glow_size, glow_size), glow_size)
            self.screen.blit(glow_surf, 
                           (x - glow_size, y - glow_size))
        
        # Character circle
        pygame.draw.circle(self.screen, self.CARD_BG, (x, y), current_size)
        pygame.draw.circle(self.screen, self.ACCENT, (x, y), current_size, 4)
        
        # Level indicator
        level_text = f"Lv.{total_level}"
        level_surf = self.font_heading.render(level_text, True, self.TEXT_PRIMARY)
        level_rect = level_surf.get_rect(center=(x, y))
        self.screen.blit(level_surf, level_rect)
        
        # Crown for high levels
        if total_level >= 50:
            crown_points = [
                (x - 30, y - current_size - 10),
                (x - 20, y - current_size - 25),
                (x, y - current_size - 15),
                (x + 20, y - current_size - 25),
                (x + 30, y - current_size - 10)
            ]
            pygame.draw.polygon(self.screen, (255, 215, 0), crown_points)
    
    def draw_stat_mini_card(self, x, y, width, icon, label, value, color):
        """Draw mini stat card"""
        card_rect = pygame.Rect(x, y, width, 80)
        pygame.draw.rect(self.screen, self.CARD_BG, card_rect, border_radius=10)
        pygame.draw.rect(self.screen, color, card_rect, 2, border_radius=10)
        
        # Icon
        icon_surf = self.font_heading.render(icon, True, color)
        self.screen.blit(icon_surf, (x + 15, y + 15))
        
        # Label
        label_surf = self.font_small.render(label, True, self.TEXT_SECONDARY)
        self.screen.blit(label_surf, (x + 60, y + 15))
        
        # Value
        value_surf = self.font_heading.render(str(value), True, self.TEXT_PRIMARY)
        self.screen.blit(value_surf, (x + 60, y + 40))
    
    def draw_dashboard_view(self):
        """Main dashboard view"""
        if not self.data:
            error_surf = self.font_heading.render("No data found! Run the main app first.", 
                                                  True, self.DANGER)
            self.screen.blit(error_surf, (self.WIDTH // 2 - 300, self.HEIGHT // 2))
            return
        
        # Title
        title = self.font_title.render("⚔️ LIFE RPG DASHBOARD ⚔️", True, self.TEXT_PRIMARY)
        self.screen.blit(title, (self.WIDTH // 2 - 300, 20))
        
        # Calculate stats
        total_level = sum(area['level'] for area in self.data['life_areas'].values())
        total_xp = sum(area['xp'] for area in self.data['life_areas'].values())
        
        # Left side - Character & Quick Stats
        self.draw_card(30, 100, 400, 350, "Your Character")
        self.draw_character_avatar(230, 220, 70, total_level)
        
        # Quick stats below character
        self.draw_stat_mini_card(50, 320, 170, "⚡", "Total XP", total_xp, self.ACCENT)
        self.draw_stat_mini_card(240, 320, 170, "🎯", "Areas", len(self.data['life_areas']), self.SUCCESS)
        
        # Today's habits
        self.draw_card(30, 470, 400, 200, "Today's Habits")
        today = datetime.now().strftime('%Y-%m-%d')
        
        habits_data = [
            ("🚿", "Shower", self.data['habits']['shower']['last_done'] == today),
            ("💪", "Workout", self.data['habits']['workout']['last_done'] == today),
        ]
        
        for i, (icon, name, done) in enumerate(habits_data):
            y_pos = 530 + i * 60
            color = self.SUCCESS if done else self.TEXT_SECONDARY
            
            icon_surf = self.font_heading.render(icon, True, color)
            self.screen.blit(icon_surf, (60, y_pos))
            
            name_surf = self.font_normal.render(name, True, color)
            self.screen.blit(name_surf, (120, y_pos + 5))
            
            status = "✓ Done" if done else "○ Pending"
            status_surf = self.font_small.render(status, True, color)
            self.screen.blit(status_surf, (320, y_pos + 8))
        
        # Center - Top Life Areas
        self.draw_card(450, 100, 500, 570, "Top Life Areas")
        
        sorted_areas = sorted(self.data['life_areas'].items(), 
                            key=lambda x: x[1]['level'], reverse=True)[:8]
        
        for i, (area_name, stats) in enumerate(sorted_areas):
            y_pos = 170 + i * 65
            
            # Area name
            short_name = area_name.split(' - ')[-1] if ' - ' in area_name else area_name
            name_surf = self.font_normal.render(short_name[:20], True, self.TEXT_PRIMARY)
            self.screen.blit(name_surf, (470, y_pos))
            
            # XP bar
            self.draw_xp_bar(470, y_pos + 30, 460, stats['xp'], stats['level'])
        
        # Right side - Income & Milestones
        self.draw_card(970, 100, 400, 300, "Income Progress")
        
        current = self.data['income']['current_month_earnings']
        goal = self.data['income']['monthly_goal']
        progress = min(current / goal, 1.0) if goal > 0 else 0
        
        # Circular progress for income
        self.draw_circular_progress(1170, 220, 70, progress, self.SUCCESS, 
                                   "Progress", f"{int(progress * 100)}%")
        
        # Income values
        income_text = f"{current:,} / {goal:,} ₾"
        income_surf = self.font_normal.render(income_text, True, self.TEXT_PRIMARY)
        income_rect = income_surf.get_rect(center=(1170, 320))
        self.screen.blit(income_surf, income_rect)
        
        # Epic Milestones
        self.draw_card(970, 420, 400, 250, "Epic Milestones")
        
        completed_count = sum(1 for m in self.data['epic_milestones'].values() if m['completed'])
        total_count = len(self.data['epic_milestones'])
        
        milestone_progress = completed_count / total_count if total_count > 0 else 0
        
        # Progress bar
        bar_x = 990
        bar_y = 500
        bar_width = 360
        bar_height = 30
        
        pygame.draw.rect(self.screen, self.XP_BAR_BG, 
                        (bar_x, bar_y, bar_width, bar_height), border_radius=15)
        
        if milestone_progress > 0:
            fill_width = int(bar_width * milestone_progress)
            pygame.draw.rect(self.screen, self.WARNING, 
                           (bar_x, bar_y, fill_width, bar_height), border_radius=15)
        
        pygame.draw.rect(self.screen, self.WARNING, 
                        (bar_x, bar_y, bar_width, bar_height), 2, border_radius=15)
        
        progress_text = f"{completed_count}/{total_count} Completed"
        progress_surf = self.font_small.render(progress_text, True, self.TEXT_PRIMARY)
        progress_rect = progress_surf.get_rect(center=(bar_x + bar_width // 2, bar_y + 15))
        self.screen.blit(progress_surf, progress_rect)
        
        # List completed milestones
        y_offset = 550
        for key, milestone in list(self.data['epic_milestones'].items())[:3]:
            status = "✅" if milestone['completed'] else "⏳"
            text = f"{status} {milestone['description'][:25]}"
            text_surf = self.font_small.render(text, True, self.TEXT_SECONDARY)
            self.screen.blit(text_surf, (990, y_offset))
            y_offset += 35
        
        # Daily score (if available)
        if self.data.get('daily_scores'):
            latest_score = self.data['daily_scores'][-1]
            score_text = f"Today: {latest_score['grade']} ({latest_score['score']}/100)"
            score_surf = self.font_normal.render(score_text, True, self.WARNING)
            self.screen.blit(score_surf, (self.WIDTH // 2 - 150, self.HEIGHT - 60))
        
        # Navigation hint
        hint_surf = self.font_small.render("Press 'S' for detailed stats | 'M' for milestones | 'Q' to quit", 
                                          True, self.TEXT_SECONDARY)
        self.screen.blit(hint_surf, (self.WIDTH // 2 - 280, self.HEIGHT - 30))
    
    def draw_stats_view(self):
        """Detailed stats view"""
        self.draw_card(50, 50, self.WIDTH - 100, self.HEIGHT - 100, "Detailed Statistics")
        
        if not self.data:
            return
        
        # Group by category
        categories = {}
        for area, stats in self.data['life_areas'].items():
            category = area.split(' - ')[0]
            if category not in categories:
                categories[category] = []
            categories[category].append((area, stats))
        
        y_offset = 130
        col_width = (self.WIDTH - 140) // 3
        
        col = 0
        for category, areas in list(categories.items())[:9]:
            x_offset = 70 + col * col_width
            
            # Category header
            cat_surf = self.font_normal.render(category, True, self.ACCENT)
            self.screen.blit(cat_surf, (x_offset, y_offset))
            
            # Areas in category
            for i, (area, stats) in enumerate(areas[:4]):
                item_y = y_offset + 40 + i * 80
                short_name = area.split(' - ')[-1]
                
                name_surf = self.font_small.render(short_name[:15], True, self.TEXT_SECONDARY)
                self.screen.blit(name_surf, (x_offset, item_y))
                
                self.draw_xp_bar(x_offset, item_y + 25, col_width - 40, stats['xp'], stats['level'])
            
            col += 1
            if col >= 3:
                col = 0
                y_offset += 400
        
        # Back hint
        hint_surf = self.font_small.render("Press 'D' to return to dashboard", 
                                          True, self.TEXT_SECONDARY)
        self.screen.blit(hint_surf, (self.WIDTH // 2 - 150, self.HEIGHT - 30))
    
    def draw_milestones_view(self):
        """Milestones detailed view"""
        self.draw_card(50, 50, self.WIDTH - 100, self.HEIGHT - 100, "🏆 Epic Milestones")
        
        if not self.data:
            return
        
        y_offset = 150
        for key, milestone in self.data['epic_milestones'].items():
            card_color = self.SUCCESS if milestone['completed'] else self.CARD_BG
            
            # Milestone card
            milestone_rect = pygame.Rect(100, y_offset, self.WIDTH - 200, 100)
            pygame.draw.rect(self.screen, card_color, milestone_rect, border_radius=10)
            
            border_color = self.SUCCESS if milestone['completed'] else self.TEXT_SECONDARY
            pygame.draw.rect(self.screen, border_color, milestone_rect, 3, border_radius=10)
            
            # Status icon
            status = "✅" if milestone['completed'] else "⏳"
            status_surf = self.font_heading.render(status, True, self.TEXT_PRIMARY)
            self.screen.blit(status_surf, (120, y_offset + 30))
            
            # Description
            desc_surf = self.font_normal.render(milestone['description'], True, self.TEXT_PRIMARY)
            self.screen.blit(desc_surf, (180, y_offset + 20))
            
            # Reward
            reward_text = f"+{milestone['xp_reward']} XP Reward"
            reward_surf = self.font_small.render(reward_text, True, self.WARNING)
            self.screen.blit(reward_surf, (180, y_offset + 55))
            
            y_offset += 120
        
        # Back hint
        hint_surf = self.font_small.render("Press 'D' to return to dashboard", 
                                          True, self.TEXT_SECONDARY)
        self.screen.blit(hint_surf, (self.WIDTH // 2 - 150, self.HEIGHT - 30))
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            self.clock.tick(60)
            self.animation_time += 0.016
            
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_d:
                        self.current_view = "dashboard"
                        self.data = self.load_data()  # Reload data
                    elif event.key == pygame.K_s:
                        self.current_view = "stats"
                        self.data = self.load_data()
                    elif event.key == pygame.K_m:
                        self.current_view = "milestones"
                        self.data = self.load_data()
                    elif event.key == pygame.K_r:
                        self.data = self.load_data()  # Refresh data
            
            # Drawing
            self.screen.fill(self.BG_COLOR)
            
            if self.current_view == "dashboard":
                self.draw_dashboard_view()
            elif self.current_view == "stats":
                self.draw_stats_view()
            elif self.current_view == "milestones":
                self.draw_milestones_view()
            
            pygame.display.flip()
        
        pygame.quit()


if __name__ == "__main__":
    print("🎮 Starting Life RPG Visual Dashboard...")
    print("Make sure you've run the main app and have data saved!")
    print("\nControls:")
    print("  D - Dashboard view")
    print("  S - Detailed stats view")
    print("  M - Milestones view")
    print("  R - Refresh data")
    print("  Q - Quit")
    print("\nLaunching...")
    
    app = LifeRPGVisual()
    app.run()
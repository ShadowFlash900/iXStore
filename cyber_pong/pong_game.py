import pygame
import math
import struct
import wave
import io
import random

# --- ГЕНЕРАЦИЯ ЗВУКОВ (Static Helpers) ---
def create_sound_data(freq, duration, volume=0.3, fade=True):
    buffer = io.BytesIO()
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    amplitude = 32767 * volume
    
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        
        data = bytearray()
        for i in range(n_samples):
            t = float(i) / sample_rate
            val = int(amplitude * math.sin(2 * math.pi * freq * t))
            if fade:
                if i < 500: val = int(val * (i/500))
                if i > n_samples - 500: val = int(val * ((n_samples-i)/500))
            data.extend(struct.pack('<h', max(-32767, min(32767, val))))
        wav.writeframes(data)
    buffer.seek(0)
    return buffer

def create_chord_data(freqs, duration, volume=0.3):
    buffer = io.BytesIO()
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    amplitude = 32767 * volume / len(freqs) 
    
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        
        data = bytearray()
        for i in range(n_samples):
            t = float(i) / sample_rate
            val = 0.0
            for f in freqs:
                val += amplitude * math.sin(2 * math.pi * f * t)
            
            fade_in_len = int(sample_rate * 0.5)
            fade_out_len = int(sample_rate * 1.0)
            
            env = 1.0
            if i < fade_in_len: env = i / fade_in_len
            elif i > n_samples - fade_out_len: env = (n_samples - i) / fade_out_len
            
            final_val = int(val * env)
            data.extend(struct.pack('<h', max(-32767, min(32767, final_val))))
        wav.writeframes(data)
    buffer.seek(0)
    return buffer

class PongGame:
    def __init__(self, screen):
        self.screen = screen
        self.w, self.h = screen.get_size()
        self.clock = pygame.time.Clock()
        
        # Аудио
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        self.init_audio()
        
        # Джойстики (обновляем список)
        if not pygame.joystick.get_init():
            pygame.joystick.init()
        self.joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]

        # Шрифты
        self.font = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 20)
        self.intro_font = pygame.font.SysFont("Arial", 50, bold=True)

        # Состояние игры
        self.game_state = "INTRO" # INTRO, PLAYING
        self.setup_intro()
        self.setup_game()

    def init_audio(self):
        try:
            self.snd_paddle = pygame.mixer.Sound(create_sound_data(440, 0.08, 0.4))
            self.snd_wall = pygame.mixer.Sound(create_sound_data(220, 0.08, 0.4))
            self.snd_score = pygame.mixer.Sound(create_sound_data(880, 0.4, 0.3))
            chord_freqs = [261.63, 329.63, 392.00, 493.88] 
            self.snd_intro = pygame.mixer.Sound(create_chord_data(chord_freqs, 3.0, 0.4))
        except Exception as e:
            print(f"Audio error: {e}")
            self.snd_paddle = self.snd_wall = self.snd_score = self.snd_intro = None

    def setup_intro(self):
        if self.snd_intro: self.snd_intro.play()
        self.intro_text = self.intro_font.render("for InteriumX", True, (255, 255, 255))
        self.intro_rect = self.intro_text.get_rect(center=(self.w//2, self.h//2))
        self.intro_alpha = 0
        self.intro_phase = 0 # 0: Fade In, 1: Hold, 2: Fade Out
        self.intro_timer = 90

    def setup_game(self):
        self.ball = pygame.Rect(self.w//2-10, self.h//2-10, 20, 20)
        self.paddle_h = 80
        self.paddle_w = 15
        self.p1 = pygame.Rect(30, self.h//2 - self.paddle_h//2, self.paddle_w, self.paddle_h)
        self.p2 = pygame.Rect(self.w-30-self.paddle_w, self.h//2 - self.paddle_h//2, self.paddle_w, self.paddle_h)
        
        self.ball_speed_x = 5
        self.ball_speed_y = 5
        self.speed_mult = 1.0
        
        self.p1_score = 0
        self.p2_score = 0
        
        self.difficulty = 1 
        self.diff_names = ["EASY", "MEDIUM", "HARD"]
        self.diff_colors = [(100, 255, 100), (255, 255, 100), (255, 100, 100)]
        
        self.paused = True # Это "внутриигровая" пауза (перед подачей)

    def run_frame(self):
        # 1. ОБРАБОТКА ВВОДА
        self.clock.tick(60)  # Ограничиваем игру до 60 кадров в секунду
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "EXIT"
            
            # --- HOME / EXIT LOGIC ---
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == 6: return "HOME" # Select/-
                if event.button == 1: return "EXIT" # B/Circle (Exit game)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: return "EXIT"
            
            # --- INTRO SKIP ---
            if self.game_state == "INTRO":
                if event.type in [pygame.KEYDOWN, pygame.JOYBUTTONDOWN]:
                    self.game_state = "PLAYING"
            
            # --- GAMEPLAY INPUT ---
            elif self.game_state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE: self.paused = not self.paused
                    if self.paused:
                        if event.key == pygame.K_1: self.difficulty = 0
                        if event.key == pygame.K_2: self.difficulty = 1
                        if event.key == pygame.K_3: self.difficulty = 2
                
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 7: self.paused = not self.paused # Start
                    if self.paused:
                        if event.button == 4: self.difficulty = (self.difficulty - 1) % 3 # LB
                        if event.button == 5: self.difficulty = (self.difficulty + 1) % 3 # RB
                
                if event.type == pygame.JOYHATMOTION and self.paused:
                    if event.value[0] == -1: self.difficulty = (self.difficulty - 1) % 3
                    elif event.value[0] == 1: self.difficulty = (self.difficulty + 1) % 3

        # 2. ЛОГИКА
        if self.game_state == "INTRO":
            self.update_intro()
            self.draw_intro()
        elif self.game_state == "PLAYING":
            self.update_game()
            self.draw_game()

        return "RUNNING"

    def update_intro(self):
        if self.intro_phase == 0:
            self.intro_alpha += 3
            if self.intro_alpha >= 255: self.intro_alpha = 255; self.intro_phase = 1
        elif self.intro_phase == 1:
            self.intro_timer -= 1
            if self.intro_timer <= 0: self.intro_phase = 2
        elif self.intro_phase == 2:
            self.intro_alpha -= 3
            if self.intro_alpha <= 0: 
                self.intro_alpha = 0
                self.game_state = "PLAYING"

    def draw_intro(self):
        self.screen.fill((0,0,0))
        temp_surf = self.intro_text.copy()
        temp_surf.set_alpha(self.intro_alpha)
        self.screen.blit(temp_surf, self.intro_rect)

    def update_game(self):
        # Paddle 1 (Player)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]: self.p1.y -= 7
        if keys[pygame.K_s]: self.p1.y += 7
        
        if self.joysticks:
            try:
                axis = self.joysticks[0].get_axis(1)
                if abs(axis) > 0.2: self.p1.y += int(axis * 7)
            except: pass

        # Paddle 2 (AI)
        if self.ball.centerx > self.w//2 and not self.paused:
            ai_speed = [3, 5, 9][self.difficulty]
            target_y = self.ball.centery
            # Ошибки AI на легком
            if self.difficulty == 0: 
                if self.ball.centery < self.p2.centery + 20: target_y = self.p2.centery - 10
            
            if self.p2.centery < target_y: self.p2.y += ai_speed
            elif self.p2.centery > target_y: self.p2.y -= ai_speed

        # Clamping
        self.p1.y = max(0, min(self.h - self.paddle_h, self.p1.y))
        self.p2.y = max(0, min(self.h - self.paddle_h, self.p2.y))

        # Ball
        if not self.paused:
            self.ball.x += self.ball_speed_x * self.speed_mult
            self.ball.y += self.ball_speed_y * self.speed_mult
            
            if self.ball.top <= 0 or self.ball.bottom >= self.h:
                self.ball_speed_y *= -1
                if self.snd_wall: self.snd_wall.play()
                
            if self.ball.left <= 0:
                self.p2_score += 1
                if self.snd_score: self.snd_score.play()
                self.reset_ball(1)
            if self.ball.right >= self.w:
                self.p1_score += 1
                if self.snd_score: self.snd_score.play()
                self.reset_ball(-1)
                
            if self.ball.colliderect(self.p1) and self.ball_speed_x < 0:
                self.ball_speed_x *= -1
                self.speed_mult += 0.05
                if self.snd_paddle: self.snd_paddle.play()
            if self.ball.colliderect(self.p2) and self.ball_speed_x > 0:
                self.ball_speed_x *= -1
                self.speed_mult += 0.05
                if self.snd_paddle: self.snd_paddle.play()

    def reset_ball(self, direction_mult):
        self.ball.center = (self.w//2, self.h//2)
        self.ball_speed_x = 5 * direction_mult
        self.speed_mult = 1.0
        self.paused = True

    def draw_game(self):
        self.screen.fill((0, 0, 0))
        pygame.draw.line(self.screen, (50, 50, 50), (self.w//2, 0), (self.w//2, self.h), 2)
        
        pygame.draw.rect(self.screen, (0, 200, 255), self.p1, border_radius=4)
        pygame.draw.rect(self.screen, (255, 50, 100), self.p2, border_radius=4)
        pygame.draw.ellipse(self.screen, (255, 255, 255), self.ball)
        
        score_surf = self.font.render(f"{self.p1_score}   {self.p2_score}", True, (255, 255, 255))
        self.screen.blit(score_surf, score_surf.get_rect(center=(self.w//2, 40)))
        
        if self.paused:
            overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            overlay.fill((0,0,0,100))
            self.screen.blit(overlay, (0,0))

            txt = self.font_small.render("Press START / SPACE to Serve", True, (200, 200, 200))
            self.screen.blit(txt, txt.get_rect(center=(self.w//2, self.h/2 + 50)))
            
            diff_lbl = self.font_small.render(f"Difficulty: {self.diff_names[self.difficulty]} (LB/RB or D-PAD)", True, self.diff_colors[self.difficulty])
            self.screen.blit(diff_lbl, diff_lbl.get_rect(center=(self.w//2, self.h/2 + 80)))
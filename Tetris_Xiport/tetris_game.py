
import pygame
import random
import math
import array
import os
import json
import sys

# --- КОНСТАНТЫ ---
BLOCK_SIZE = 24
GRID_WIDTH = 10
GRID_HEIGHT = 20

# Цвета
COLOR_BG = (15, 15, 20)
COLOR_GRID = (30, 30, 40)
COLOR_TEXT = (240, 240, 240)
COLOR_ACCENT = (0, 200, 255) 
COLOR_OVERLAY = (0, 0, 0, 220)
COLOR_MENU_SEL = (50, 50, 60)
COLOR_GHOST = (60, 60, 70) 

SHAPE_COLORS = [
    (0, 0, 0),       
    (0, 240, 240),   # I 
    (0, 0, 240),     # J 
    (240, 160, 0),   # L 
    (240, 240, 0),   # O 
    (0, 240, 0),     # S 
    (160, 0, 240),   # T 
    (240, 0, 0)      # Z 
]

TETROMINOS = [
    [[1, 1, 1, 1]],                               
    [[1, 1, 1], [0, 1, 0]],                       
    [[1, 1, 0], [0, 1, 1]],                       
    [[0, 1, 1], [1, 1, 0]],                       
    [[1, 1], [1, 1]],                             
    [[1, 0, 0], [1, 1, 1]],                       
    [[0, 0, 1], [1, 1, 1]],                       
]

class SoundGen:
    """Генератор 8-битных звуков на лету"""
    def __init__(self):
        self.sample_rate = 44100
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1)

    def make_tone(self, freq, duration, vol=0.3, wave_type="square"):
        n_samples = int(44100 * duration)
        buf = array.array('h', [0] * n_samples)
        amplitude = int(32767 * vol)
        period = 44100 / freq
        
        for i in range(n_samples):
            if wave_type == "square":
                val = amplitude if (i % period) < (period / 2) else -amplitude
            elif wave_type == "saw":
                val = int(amplitude * 2 * ((i % period) / period) - amplitude)
            elif wave_type == "noise":
                val = random.randint(-amplitude, amplitude)
            else:
                val = 0
            if i > n_samples - 500: 
                val = int(val * ((n_samples - i) / 500))
            buf[i] = val
        return pygame.mixer.Sound(buffer=buf)

    def make_chord(self, freqs, duration, vol=0.3):
        n_samples = int(44100 * duration)
        buf = array.array('h', [0] * n_samples)
        amplitude = int(32767 * vol / len(freqs))
        for i in range(n_samples):
            val = 0
            for f in freqs:
                val += int(amplitude * math.sin(2 * math.pi * f * (i / 44100)))
            if i > n_samples - 1000: val = int(val * ((n_samples - i) / 1000))
            buf[i] = val
        return pygame.mixer.Sound(buffer=buf)

class Tetris:
    def __init__(self, screen):
        self.screen = screen
        self.sw, self.sh = screen.get_size()
        
        # Центрируем поле
        self.play_width = GRID_WIDTH * BLOCK_SIZE
        self.play_height = GRID_HEIGHT * BLOCK_SIZE
        self.start_x = (self.sw - self.play_width) // 2
        self.start_y = (self.sh - self.play_height) // 2
        
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont('Arial', 40, bold=True)
        self.font = pygame.font.SysFont('Arial', 24, bold=True)
        self.font_small = pygame.font.SysFont('Arial', 18)

        self.gen_sounds()

        if pygame.joystick.get_count() == 0:
            pygame.joystick.init()
        self.joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
        
        self.last_input_time = 0
        self.input_delay = 150
        self.last_move_time = 0

        self.reset_game_vars()
        self.state = "SPLASH"
        self.splash_timer = 0
        self.splash_alpha = 0
        self.splash_phase = "IN" 
        self.menu_options = ["Resume / Start", "Exit"]
        self.menu_index = 0

    def gen_sounds(self):
        try:
            synth = SoundGen()
            self.sounds = {
                "move": synth.make_tone(400, 0.05, 0.2, "square"),
                "rotate": synth.make_tone(600, 0.08, 0.2, "square"),
                "drop": synth.make_tone(150, 0.1, 0.3, "saw"),
                "clear": synth.make_chord([523, 659, 784], 0.4, 0.3),
                "gameover": synth.make_tone(100, 1.0, 0.3, "noise")
            }
        except: self.sounds = {}

    def play_snd(self, name):
        if name in self.sounds: self.sounds[name].play()

    def reset_game_vars(self):
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.current_piece = self.get_new_piece()
        self.next_piece = self.get_new_piece()
        self.score = 0
        self.fall_time = 0
        self.fall_speed = 500

    def get_new_piece(self):
        shape = random.choice(TETROMINOS)
        return {
            'shape': shape,
            'rotation': 0,
            'x': GRID_WIDTH // 2 - len(shape[0]) // 2,
            'y': 0,
            'color': TETROMINOS.index(shape) + 1
        }

    def rotate_shape(self, shape):
        return [list(row) for row in zip(*shape[::-1])]

    def check_collision(self, piece, adj_x=0, adj_y=0, adj_rot=None):
        shape = piece['shape']
        if adj_rot: shape = adj_rot
        for i, row in enumerate(shape):
            for j, cell in enumerate(row):
                if cell:
                    new_x = piece['x'] + j + adj_x
                    new_y = piece['y'] + i + adj_y
                    if new_x < 0 or new_x >= GRID_WIDTH or new_y >= GRID_HEIGHT: return True
                    if new_y >= 0 and self.grid[new_y][new_x]: return True
        return False

    def merge_piece(self):
        for i, row in enumerate(self.current_piece['shape']):
            for j, cell in enumerate(row):
                if cell:
                    py = self.current_piece['y'] + i
                    px = self.current_piece['x'] + j
                    if py >= 0: self.grid[py][px] = self.current_piece['color']
        self.play_snd("drop")

    def clear_lines(self):
        lines_cleared = 0
        for i in range(len(self.grid) - 1, -1, -1):
            if 0 not in self.grid[i]:
                lines_cleared += 1
                del self.grid[i]
                self.grid.insert(0, [0]*GRID_WIDTH)
        if lines_cleared > 0:
            self.score += lines_cleared * 100
            if self.fall_speed > 100: self.fall_speed -= 10 * lines_cleared
            self.play_snd("clear")

    def draw_game(self):
        self.screen.fill(COLOR_BG)
        
        # Рамка и фон поля
        pygame.draw.rect(self.screen, (20, 20, 25), (self.start_x, self.start_y, self.play_width, self.play_height))
        pygame.draw.rect(self.screen, COLOR_GRID, (self.start_x, self.start_y, self.play_width, self.play_height), 1)
        pygame.draw.rect(self.screen, COLOR_ACCENT, (self.start_x - 2, self.start_y - 2, self.play_width + 4, self.play_height + 4), 2)

        # Сетка внутри
        for i in range(GRID_HEIGHT):
            pygame.draw.line(self.screen, (25, 25, 35), (self.start_x, self.start_y + i*BLOCK_SIZE), (self.start_x+self.play_width, self.start_y + i*BLOCK_SIZE))
        for j in range(GRID_WIDTH):
            pygame.draw.line(self.screen, (25, 25, 35), (self.start_x + j*BLOCK_SIZE, self.start_y), (self.start_x + j*BLOCK_SIZE, self.start_y + self.play_height))

        # Статичные блоки
        for i in range(GRID_HEIGHT):
            for j in range(GRID_WIDTH):
                val = self.grid[i][j]
                if val > 0:
                    rect = (self.start_x + j * BLOCK_SIZE, self.start_y + i * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                    pygame.draw.rect(self.screen, SHAPE_COLORS[val], rect)
                    pygame.draw.rect(self.screen, (0,0,0), rect, 1)

        if self.state == "PLAYING":
            shape = self.current_piece['shape']
            
            # --- GHOST PIECE ---
            ghost_offset = 0
            while not self.check_collision(self.current_piece, adj_y=ghost_offset + 1):
                ghost_offset += 1
            
            for i, row in enumerate(shape):
                for j, cell in enumerate(row):
                    if cell:
                        gy = self.current_piece['y'] + i + ghost_offset
                        gx = self.current_piece['x'] + j
                        if gy >= 0:
                            g_rect = (self.start_x + gx * BLOCK_SIZE, self.start_y + gy * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE)
                            pygame.draw.rect(self.screen, COLOR_GHOST, g_rect, 1) 

            # --- ТЕКУЩАЯ ФИГУРА ---
            for i, row in enumerate(shape):
                for j, cell in enumerate(row):
                    if cell:
                        x = self.start_x + (self.current_piece['x'] + j) * BLOCK_SIZE
                        y = self.start_y + (self.current_piece['y'] + i) * BLOCK_SIZE
                        if y >= self.start_y:
                            rect = (x, y, BLOCK_SIZE, BLOCK_SIZE)
                            pygame.draw.rect(self.screen, SHAPE_COLORS[self.current_piece['color']], rect)
                            pygame.draw.rect(self.screen, (0,0,0), rect, 1)

        # UI
        score_text = self.font.render(f"Score: {self.score}", True, COLOR_TEXT)
        self.screen.blit(score_text, (self.start_x + self.play_width + 20, self.start_y))
        
        next_text = self.font_small.render("Next:", True, COLOR_TEXT)
        self.screen.blit(next_text, (self.start_x + self.play_width + 20, self.start_y + 60))
        
        off_x = self.start_x + self.play_width + 20
        off_y = self.start_y + 90
        for i, row in enumerate(self.next_piece['shape']):
            for j, cell in enumerate(row):
                if cell:
                    rect = (off_x + j * 18, off_y + i * 18, 18, 18)
                    pygame.draw.rect(self.screen, SHAPE_COLORS[self.next_piece['color']], rect)
                    pygame.draw.rect(self.screen, (0,0,0), rect, 1)

    def draw_menu(self):
        self.screen.fill(COLOR_BG)
        title = self.font_big.render("NEON TETRIS", True, COLOR_ACCENT)
        self.screen.blit(title, title.get_rect(center=(self.sw//2, self.sh//3)))
        start_y = self.sh // 2 + 20
        for i, opt in enumerate(self.menu_options):
            color = COLOR_TEXT if i == self.menu_index else (100, 100, 100)
            if i == self.menu_index:
                bg_rect = (self.sw//2 - 100, start_y + i*50 - 10, 200, 40)
                pygame.draw.rect(self.screen, (255,255,255, 20), bg_rect, border_radius=10)
                pygame.draw.rect(self.screen, COLOR_ACCENT, bg_rect, 1, border_radius=10)
            txt = self.font.render(opt, True, color)
            self.screen.blit(txt, txt.get_rect(center=(self.sw//2, start_y + i*50 + 10)))

    def draw_splash(self):
        self.screen.fill((0,0,0))
        if self.splash_phase == "IN":
            self.splash_alpha += 5
            if self.splash_alpha >= 255: self.splash_alpha = 255; self.splash_phase = "HOLD"; self.splash_timer = pygame.time.get_ticks()
        elif self.splash_phase == "HOLD":
            if pygame.time.get_ticks() - self.splash_timer > 2000: self.splash_phase = "OUT"
        elif self.splash_phase == "OUT":
            self.splash_alpha -= 5
            if self.splash_alpha <= 0: self.state = "MENU"
        
        t1 = self.font.render("Made for", True, (150,150,150))
        t2 = self.font_big.render("InteriumX", True, COLOR_ACCENT)
        t1.set_alpha(self.splash_alpha); t2.set_alpha(self.splash_alpha)
        self.screen.blit(t1, t1.get_rect(center=(self.sw//2, self.sh//2-20)))
        self.screen.blit(t2, t2.get_rect(center=(self.sw//2, self.sh//2+20)))

    def draw_game_over(self):
        self.draw_game()
        overlay = pygame.Surface((self.sw, self.sh), pygame.SRCALPHA)
        overlay.fill(COLOR_OVERLAY)
        self.screen.blit(overlay, (0,0))
        txt = self.font_big.render("GAME OVER", True, (255, 60, 60))
        sc = self.font.render(f"Final Score: {self.score}", True, COLOR_TEXT)
        self.screen.blit(txt, txt.get_rect(center=(self.sw//2, self.sh//2-20)))
        self.screen.blit(sc, sc.get_rect(center=(self.sw//2, self.sh//2+20)))
        help_txt = self.font_small.render("Press Start/Enter to Menu", True, (150,150,150))
        self.screen.blit(help_txt, help_txt.get_rect(center=(self.sw//2, self.sh//2+60)))

    def execute_menu(self):
        self.play_snd("move")
        if self.menu_index == 0: 
            if self.score == 0 and self.grid[0][0] == 0: # New game check rough logic
                 pass 
            self.state = "PLAYING"
        else: 
            return "EXIT"

    def move(self, dx):
        if not self.check_collision(self.current_piece, adj_x=dx):
            self.current_piece['x'] += dx
            self.play_snd("move")

    def rotate(self):
        rotated = self.rotate_shape(self.current_piece['shape'])
        if not self.check_collision(self.current_piece, adj_rot=rotated):
            self.current_piece['shape'] = rotated
            self.play_snd("rotate")

    def move_down(self, manual=False):
        if not self.check_collision(self.current_piece, adj_y=1):
            self.current_piece['y'] += 1
            if manual: self.score += 1
        else:
            self.merge_piece()
            self.clear_lines()
            self.current_piece = self.next_piece
            self.next_piece = self.get_new_piece()
            if self.check_collision(self.current_piece):
                self.state = "GAMEOVER"
                self.play_snd("gameover")

    def run_frame(self):
        """
        Запускает один кадр логики игры.
        Возвращает: 'RUNNING', 'EXIT', или 'HOME'
        """
        dt = self.clock.tick(60)
        current_time = pygame.time.get_ticks()
        
        # --- INPUT ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "EXIT"
            
            # HOME BUTTON LOGIC (Button 6 is typically Select/Back/-)
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == 6: # Кнопка "-"
                    return "HOME"

            if self.state == "SPLASH":
                if event.type in [pygame.KEYDOWN, pygame.JOYBUTTONDOWN]: self.state = "MENU"
            
            elif self.state == "MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP: self.menu_index = 0; self.play_snd("move")
                    if event.key == pygame.K_DOWN: self.menu_index = 1; self.play_snd("move")
                    if event.key == pygame.K_RETURN: 
                        if self.execute_menu() == "EXIT": return "EXIT"
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0: # A Button
                         if self.execute_menu() == "EXIT": return "EXIT"
                if event.type == pygame.JOYHATMOTION:
                    if event.value[1] != 0: self.menu_index = 0 if event.value[1] == 1 else 1; self.play_snd("move")
            
            elif self.state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT: self.move(-1)
                    if event.key == pygame.K_RIGHT: self.move(1)
                    if event.key == pygame.K_UP: self.rotate()
                    if event.key == pygame.K_DOWN: self.move_down(manual=True)
                    if event.key == pygame.K_ESCAPE: self.state = "MENU"
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 0: self.rotate() # A
                    if event.button == 7: self.state = "MENU" # Start
            
            elif self.state == "GAMEOVER":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE: self.reset_game_vars(); self.state = "MENU"
                if event.type == pygame.JOYBUTTONDOWN:
                    if event.button == 7 or event.button == 0: self.reset_game_vars(); self.state = "MENU"

        if self.state == "PLAYING" and self.joysticks:
            if current_time - self.last_move_time > self.input_delay:
                js = self.joysticks[0]
                ax, ay = js.get_axis(0), js.get_axis(1)
                hx = js.get_hat(0)[0]
                if ax < -0.5 or hx == -1: self.move(-1); self.last_move_time = current_time
                if ax > 0.5 or hx == 1: self.move(1); self.last_move_time = current_time
                if ay > 0.5: self.move_down(manual=True)

        # --- UPDATE ---
        if self.state == "PLAYING":
            self.fall_time += dt
            if self.fall_time > self.fall_speed:
                self.fall_time = 0
                self.move_down()
        
        # --- DRAW ---
        if self.state == "SPLASH": self.draw_splash()
        elif self.state == "MENU": self.draw_menu()
        elif self.state == "PLAYING": self.draw_game()
        elif self.state == "GAMEOVER": self.draw_game_over()
        
        return "RUNNING"


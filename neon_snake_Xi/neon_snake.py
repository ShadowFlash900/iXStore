import pygame
import random

class NeonSnake:
    def __init__(self, screen):
        self.screen = screen
        self.w, self.h = screen.get_size()
        
        # --- НАСТРОЙКИ ---
        self.CELL_SIZE = 20
        self.cols = self.w // self.CELL_SIZE
        self.rows = self.h // self.CELL_SIZE
        
        # Цвета
        self.BG_COLOR = (10, 10, 15)
        self.SNAKE_COLOR = (0, 255, 200)
        self.FOOD_COLOR = (255, 50, 100)
        self.TEXT_COLOR = (255, 255, 255)
        
        self.font = pygame.font.SysFont("Arial", 24)
        self.font_big = pygame.font.SysFont("Arial", 48, bold=True)

        # Тайминг
        self.clock = pygame.time.Clock()
        self.move_timer = 0
        self.move_interval = 80 # ~12-15 FPS (ms)

        self.reset_game()

    def reset_game(self):
        self.snake = [(self.cols//2, self.rows//2)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.score = 0
        self.game_over = False
        self.spawn_food()
        self.move_timer = pygame.time.get_ticks()

    def spawn_food(self):
        while True:
            self.food = (random.randint(0, self.cols-1), random.randint(0, self.rows-1))
            if self.food not in self.snake:
                break

    def run_frame(self):
        # Возвращает: 'RUNNING', 'EXIT', или 'HOME'
        dt = self.clock.tick(60) # Держим dt для плавности, но логику обновляем реже
        current_time = pygame.time.get_ticks()

        # 1. Ввод
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "EXIT"
            
            # --- HOME BUTTON LOGIC ---
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == 6: # Кнопка "-" / Select
                    return "HOME"

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: return "EXIT"
                
                # Управление стрелками
                if event.key == pygame.K_UP and self.direction != (0, 1): self.next_direction = (0, -1)
                elif event.key == pygame.K_DOWN and self.direction != (0, -1): self.next_direction = (0, 1)
                elif event.key == pygame.K_LEFT and self.direction != (1, 0): self.next_direction = (-1, 0)
                elif event.key == pygame.K_RIGHT and self.direction != (-1, 0): self.next_direction = (1, 0)
                
                # Рестарт
                if self.game_over and event.key == pygame.K_RETURN:
                    self.reset_game()

            # Управление геймпадом
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == 1: # B / Circle to exit
                    if self.game_over: return "EXIT"
                    # В обычной игре B часто используется для "назад", но тут выход
                    # можно сделать меню паузы, но пока EXIT
                
                if self.game_over and event.button == 0: # A / Cross to restart
                    self.reset_game()
            
            if event.type == pygame.JOYHATMOTION:
                hat_x, hat_y = event.value
                if hat_y == 1 and self.direction != (0, 1): self.next_direction = (0, -1)
                elif hat_y == -1 and self.direction != (0, -1): self.next_direction = (0, 1)
                elif hat_x == -1 and self.direction != (1, 0): self.next_direction = (-1, 0)
                elif hat_x == 1 and self.direction != (-1, 0): self.next_direction = (1, 0)

        # 2. Логика (обновляем только если прошел интервал времени)
        if not self.game_over:
            if current_time - self.move_timer > self.move_interval:
                self.move_timer = current_time
                self.update_snake()

        # 3. Отрисовка
        self.draw()
        
        return "RUNNING"

    def update_snake(self):
        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)
        
        # Проверка столкновений
        if (new_head in self.snake or 
            new_head[0] < 0 or new_head[0] >= self.cols or 
            new_head[1] < 0 or new_head[1] >= self.rows):
            self.game_over = True
        else:
            self.snake.insert(0, new_head)
            if new_head == self.food:
                self.score += 10
                self.spawn_food()
            else:
                self.snake.pop()

    def draw(self):
        self.screen.fill(self.BG_COLOR)
        
        # Сетка (опционально, можно убрать для стиля)
        # for x in range(0, self.w, self.CELL_SIZE):
        #     pygame.draw.line(self.screen, (20, 30, 40), (x, 0), (x, self.h))
        # for y in range(0, self.h, self.CELL_SIZE):
        #     pygame.draw.line(self.screen, (20, 30, 40), (0, y), (self.w, y))

        # Еда
        fx, fy = self.food
        pygame.draw.rect(self.screen, self.FOOD_COLOR, 
                         (fx*self.CELL_SIZE, fy*self.CELL_SIZE, self.CELL_SIZE-1, self.CELL_SIZE-1), 
                         border_radius=4)
        
        # Змейка
        for i, (sx, sy) in enumerate(self.snake):
            color = self.SNAKE_COLOR
            if i == 0: color = (200, 255, 255) # Голова светлее
            pygame.draw.rect(self.screen, color, 
                             (sx*self.CELL_SIZE, sy*self.CELL_SIZE, self.CELL_SIZE-1, self.CELL_SIZE-1), 
                             border_radius=2)

        # UI
        score_surf = self.font.render(f"Score: {self.score}", True, self.TEXT_COLOR)
        self.screen.blit(score_surf, (20, 20))

        if self.game_over:
            overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            overlay.fill((0,0,0,180))
            self.screen.blit(overlay, (0,0))
            
            txt_over = self.font_big.render("GAME OVER", True, (255, 50, 50))
            self.screen.blit(txt_over, txt_over.get_rect(center=(self.w//2, self.h//2 - 40)))
            
            txt_res = self.font.render("Press Enter / A to Restart", True, (200, 200, 200))
            self.screen.blit(txt_res, txt_res.get_rect(center=(self.w//2, self.h//2 + 20)))
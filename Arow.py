import pygame
from pygame.locals import *
import math
import random
from PIL import Image, ImageFilter
import sys 
import os  

pygame.init()

info = pygame.display.Info()
NATIVE_WIDTH, NATIVE_HEIGHT = info.current_w, info.current_h
WIDTH, HEIGHT = 1280, 720 

fullscreen = True 

if fullscreen:
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN, pygame.HWSURFACE | pygame.DOUBLEBUF) 
    WIDTH, HEIGHT = screen.get_size() 
else:
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE) 

pygame.display.set_caption("Arow - Press B to toggle Bloom")

WHITE, BLACK, RED = (255, 255, 255), (30, 30, 30), (255, 50, 50)
BLUE, YELLOW, GREEN = (100, 150, 255), (255, 255, 0), (0, 255, 0)
ORANGE, CYAN, PURPLE = (255, 165, 0), (0, 255, 255), (180, 0, 255)
GRID_COLOR, PLAYER_COLOR = (80, 80, 80), (200, 220, 255)

try:
    font = pygame.font.Font("freesansbold.ttf", 24)
    title_font = pygame.font.Font("freesansbold.ttf", 96)
    ui_font = pygame.font.Font("freesansbold.ttf", 18)
except FileNotFoundError:
    font, title_font, ui_font = pygame.font.Font(None, 36), pygame.font.Font(None, 120), pygame.font.Font(None, 28)

MAP_WIDTH, MAP_HEIGHT = 2600, 2600
WAVE_COOLDOWN = 240
POWERUP_DROP_CHANCE = 0.22
PARTICLE_LIMIT = 400
POWERUP_DROP_TABLE = ['health', 'health', 'health', 'dash_charge', 'dash_charge', 'rapid_fire', 'plasma_ball']
BOSS_POWERUP_SPAWN_RATE = 240  

screen_shake = 0
game_paused = False
smooth_camera_follow = True
camera_smooth_factor = 0.08

custom_start_wave_str = "1"
wave_input_active = False
custom_powerups = {'dash_charge': False, 'rapid_fire': False, 'plasma_ball': False}

splash_screen_active = True 
splash_start_time = 0 
splash_duration = 3000 
fade_in_duration = 500 
fade_out_duration = 500 
splash_image = None 
splash_rect = None 

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:

        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def create_particles(position, count, color, min_speed, max_speed, min_life, max_life):
    if len(particles) > PARTICLE_LIMIT - count: return
    for _ in range(count):
        particles.add(Particle(position, color, min_speed, max_speed, min_life, max_life))

def create_grid_surface(width, height, grid_color, line_spacing=100):
    grid_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for x in range(0, width + line_spacing, line_spacing):
        pygame.draw.line(grid_surf, grid_color, (x, 0), (x, height))
    for y in range(0, height + line_spacing, line_spacing):
        pygame.draw.line(grid_surf, grid_color, (0, y), (width, y))
    return grid_surf

class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, color, min_speed, max_speed, min_life, max_life):
        super().__init__()
        angle, speed = random.uniform(0, 2 * math.pi), random.uniform(min_speed, max_speed)
        self.velocity = [math.cos(angle) * speed, math.sin(angle) * speed]
        self.lifespan = random.randint(min_life, max_life)
        self.initial_lifespan = self.lifespan
        self.size = random.randint(2, 5)
        self.image = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (self.size, self.size), self.size)
        self.rect, self.pos = self.image.get_rect(center=pos), list(pos)

    def update(self):
        self.pos[0] += self.velocity[0];
        self.pos[1] += self.velocity[1]
        self.rect.center = self.pos
        self.lifespan -= 1
        if self.lifespan <= 0: self.kill()
        self.image.set_alpha(int(255 * (self.lifespan / self.initial_lifespan)))

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image_size = 30
        self.original_image = pygame.Surface((self.image_size, self.image_size), pygame.SRCALPHA)
        pygame.draw.polygon(self.original_image, PLAYER_COLOR,
                            [(self.image_size, self.image_size / 2), (0, 0), (0, self.image_size)])
        pygame.draw.polygon(self.original_image, CYAN, [(self.image_size - 5, self.image_size / 2),
                                                        (self.image_size - 10, self.image_size / 2 - 5),
                                                        (self.image_size - 10, self.image_size / 2 + 5)])
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(MAP_WIDTH // 2, MAP_HEIGHT // 2))
        self.mask = pygame.mask.from_surface(self.image)
        self.pos = pygame.math.Vector2(self.rect.center)
        self.speed, self.angle = 3.5, 0
        self.max_health, self.health = 5, 5
        self.max_ammo, self.ammo = 10, 10
        self.last_shot_time, self.reloading, self.reload_time = 0, False, 1500
        self.dash_charges, self.max_dash_charges, self.is_dashing = 1, 3, False
        self.dash_timer, self.dash_duration, self.dash_speed = 0, 8, 20
        self.has_plasma_ball, self.rapid_fire_active = False, False
        self.last_move_direction = pygame.math.Vector2(1, 0) 

        self.rotated_images = {}
        for angle in range(360):
            rotated_image = pygame.transform.rotate(self.original_image, angle)
            rotated_mask = pygame.mask.from_surface(rotated_image)
            self.rotated_images[angle] = (rotated_image, rotated_mask)

    def rotate(self, camera):
        mouse_x, mouse_y = pygame.mouse.get_pos()
        rel_x, rel_y = mouse_x - (self.rect.centerx - camera.x), mouse_y - (self.rect.centery - camera.y)
        target_angle = math.degrees(math.atan2(-rel_y, rel_x))

        target_angle = int(target_angle) % 360 
        if target_angle < 0: target_angle += 360 

        if abs(self.angle - target_angle) > 1: 
            self.angle = target_angle
            self.image, self.mask = self.rotated_images[self.angle]
            self.rect = self.image.get_rect(center=self.rect.center) 

    def shoot_position(self):
        return self.pos + pygame.math.Vector2(self.image_size / 2, 0).rotate(-self.angle)

    def update(self, camera):
        keys = pygame.key.get_pressed()
        if self.is_dashing:
            self.pos += self.dash_direction * self.dash_speed
            self.dash_timer -= 1
            if self.dash_timer <= 0: self.is_dashing = False
            create_particles(self.rect.center, 3, CYAN, 1, 2, 10, 20)
        else:
            move_vec = pygame.math.Vector2(keys[K_d] - keys[K_a], keys[K_s] - keys[K_w])
            if move_vec.length_squared() > 0:
                move_vec.normalize_ip();
                self.pos += move_vec * self.speed
                self.last_move_direction = move_vec 
                create_particles(self.pos + pygame.math.Vector2(-15, 0).rotate(-self.angle), 1, ORANGE, 1, 3, 15, 25)

        map_rect = pygame.Rect((MAP_WIDTH - current_map_size) / 2, (MAP_HEIGHT - current_map_size) / 2,
                               current_map_size, current_map_size)
        self.pos.x = max(map_rect.left, min(self.pos.x, map_rect.right))
        self.pos.y = max(map_rect.top, min(self.pos.y, map_rect.bottom))
        self.rect.center = self.pos

        self.rotate(camera);
        self.handle_reloading();
        self.handle_powerups()

    def dash(self):
        if self.dash_charges > 0 and not self.is_dashing:
            global screen_shake
            self.is_dashing, self.dash_timer, self.dash_charges = True, self.dash_duration, self.dash_charges - 1
            self.dash_direction = self.last_move_direction if self.last_move_direction.length_squared() > 0 else pygame.math.Vector2(1, 0).rotate(-self.angle)
            screen_shake = 15

    def handle_reloading(self):
        if self.ammo <= 0 and not self.reloading: self.reloading, self.reload_start_time = True, pygame.time.get_ticks()
        if self.reloading and pygame.time.get_ticks() - self.reload_start_time >= self.reload_time: self.ammo, self.reloading = self.max_ammo, False

    def handle_powerups(self):
        if self.rapid_fire_active and pygame.time.get_ticks() > self.rapid_fire_end_time: self.rapid_fire_active = False

    def can_shoot(self):
        cooldown = 40 if self.rapid_fire_active else 120
        return pygame.time.get_ticks() - self.last_shot_time > cooldown and self.ammo > 0 and not self.reloading

    def take_damage(self, amount):
        if not self.is_dashing:
            self.health -= amount
            if self.health <= 0: return True
        return False

class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, angle, is_enemy=False, color=YELLOW):
        super().__init__()
        self.is_enemy, self.color = is_enemy, color if is_enemy else YELLOW
        self.image = pygame.Surface((12, 4), pygame.SRCALPHA)
        self.image.fill(self.color)
        self.image = pygame.transform.rotate(self.image, angle)
        self.rect, self.pos = self.image.get_rect(center=pos), pygame.math.Vector2(pos)
        self.velocity = pygame.math.Vector2(10, 0).rotate(-angle)

    def update(self):
        self.pos += self.velocity;
        self.rect.center = self.pos
        create_particles(self.rect.center, 1, self.color, 0.5, 1, 5, 10)
        if not pygame.Rect(0, 0, MAP_WIDTH, MAP_HEIGHT).contains(self.rect): self.kill()

class PlasmaBall(pygame.sprite.Sprite):
    def __init__(self, pos, angle):
        super().__init__()
        self.size = 30
        self.image = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, BLUE, (self.size, self.size), self.size)
        pygame.draw.circle(self.image, WHITE, (self.size, self.size), self.size // 2)
        self.rect, self.pos = self.image.get_rect(center=pos), pygame.math.Vector2(pos)
        self.velocity, self.explosion_radius = pygame.math.Vector2(5, 0).rotate(-angle), 200

    def update(self):
        self.pos += self.velocity;
        self.rect.center = self.pos
        create_particles(self.rect.center, 3, BLUE, 1, 2, 15, 25)
        if not pygame.Rect(0, 0, MAP_WIDTH, MAP_HEIGHT).contains(self.rect): self.kill()

    def explode(self):
        global screen_shake, score
        screen_shake = 30;
        create_particles(self.rect.center, 100, BLUE, 2, 8, 40, 80)
        for enemy in enemies.sprites() + boss_group.sprites():
            if self.pos.distance_to(enemy.rect.center) < self.explosion_radius:
                if enemy.take_damage(10): score += enemy.score_value
        self.kill()

class EnergyBeam(pygame.sprite.Sprite):
    def __init__(self, pos, angle, length, width):
        super().__init__()
        unrotated_surf = pygame.Surface((length, width), pygame.SRCALPHA)
        center_y = width // 2
        pygame.draw.rect(unrotated_surf, PURPLE, (0, 0, length, width), border_radius=center_y)
        pygame.draw.rect(unrotated_surf, CYAN, (0, center_y - width // 4, length, width // 2), border_radius=width // 4)
        pygame.draw.rect(unrotated_surf, WHITE, (0, center_y - width // 8, length, width // 4),
                         border_radius=width // 8)
        self.image = pygame.transform.rotate(unrotated_surf, angle)
        self.rect, self.mask = self.image.get_rect(center=pos), pygame.mask.from_surface(self.image)
        self.lifespan, self.max_lifespan, self.damage = 30, 30, 2

    def update(self):
        self.lifespan -= 1
        if self.lifespan <= 0: self.kill()
        self.image.set_alpha(int(255 * (self.lifespan / self.max_lifespan)))

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type):
        super().__init__()
        self.enemy_type = enemy_type
        if enemy_type != "boss":
            if enemy_type == "charger":
                size, self.color, self.speed, self.health, self.score_value = 32, RED, 1.7, 3, 10
            elif enemy_type == "shooter":
                size, self.color, self.speed, self.health, self.score_value = 28, ORANGE, 1.0, 2, 15
            elif enemy_type == "sniper":
                size, self.color, self.speed, self.health, self.score_value = 30, PURPLE, 0.7, 4, 30
            self.image = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(self.image, self.color, (size // 2, size // 2), size // 2)
            pygame.draw.circle(self.image, BLACK, (size // 2, size // 2), size // 4)
            self.rect, self.pos = self.image.get_rect(center=(x, y)), pygame.math.Vector2(x, y)

        if enemy_type == "shooter":
            self.shoot_timer, self.shoot_cooldown = random.randint(0, 150), 150
        elif enemy_type == "sniper":
            self.state, self.aim_timer, self.aim_duration = "roaming", 0, 120
            self.warn_timer, self.warn_duration, self.locked_target_pos = 0, 90, None
            self.cooldown_timer, self.cooldown_duration = 0, 120

    def update(self, player, all_sprites_group):
        direction = player.pos - self.pos;
        dist = direction.length()
        if dist == 0: return

        if self.enemy_type == "charger":
            self.pos += direction.normalize() * self.speed
        elif self.enemy_type == "shooter":
            desired_dist = 400
            if dist > desired_dist:
                self.pos += direction.normalize() * self.speed
            elif dist < desired_dist - 50:
                self.pos -= direction.normalize() * self.speed
            self.shoot_timer += 1
            if self.shoot_timer >= self.shoot_cooldown:
                self.shoot_timer = 0
                bullets.add(
                    Bullet(self.rect.center, math.degrees(math.atan2(-direction.y, direction.x)), True, self.color))
        elif self.enemy_type == "sniper":
            self.update_sniper(player, direction, dist, all_sprites_group)
        self.rect.center = self.pos

    def update_sniper(self, player, direction, dist, all_sprites_group):
        if self.state == "roaming":
            if dist > 0: 
                self.pos += direction.normalize() * (self.speed * 0.5) 
            if dist < 900: self.state, self.aim_timer = "aiming", self.aim_duration
        elif self.state == "aiming":
            self.aim_timer -= 1
            if self.aim_timer <= 0: self.locked_target_pos, self.state, self.warn_timer = player.pos.copy(), "warning", self.warn_duration
        elif self.state == "warning":
            self.warn_timer -= 1
            if self.warn_timer <= 0:
                if self.locked_target_pos:
                    create_particles(self.rect.center, 40, PURPLE, 2, 7, 15, 30);
                    create_particles(self.rect.center, 20, WHITE, 1, 4, 10, 20)
                    beam_dir = self.locked_target_pos - self.pos
                    beam = EnergyBeam(self.pos + beam_dir.normalize() * 1000,
                                      math.degrees(math.atan2(-beam_dir.y, beam_dir.x)), 2000, 40)
                    all_sprites_group.add(beam);
                    beams.add(beam)
                self.state, self.cooldown_timer = "cooldown", self.cooldown_duration
        elif self.state == "cooldown":
            self.cooldown_timer -= 1
            if self.cooldown_timer <= 0: self.state = "roaming"

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0: self.kill(); return True
        return False

class Boss(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, "boss")
        self.image = pygame.Surface((80, 80), pygame.SRCALPHA)
        self.color = (200, 0, 0)
        pygame.draw.rect(self.image, self.color, self.image.get_rect(), border_radius=10)
        pygame.draw.circle(self.image, YELLOW, (40, 40), 15)
        self.rect, self.pos = self.image.get_rect(center=(x, y)), pygame.math.Vector2(x, y)
        self.health, self.max_health, self.score_value = 350, 350, 1000  
        self.stage = 1
        self.action_timer, self.locked_target_pos = 0, None
        self.update_stage_attributes()

    def update_stage_attributes(self):
        if self.stage == 1:
            self.speed, self.shoot_cooldown, self.laser_cooldown, self.nova_cooldown = 0.7, 140, 600, 9999
        elif self.stage == 2:
            self.speed, self.shoot_cooldown, self.laser_cooldown, self.nova_cooldown = 1.0, 100, 500, 300
        elif self.stage == 3:
            self.speed, self.shoot_cooldown, self.laser_cooldown, self.nova_cooldown = 1.2, 80, 450, 240
        self.laser_state, self.triple_laser_count = None, 0

    def take_damage(self, amount):
        if super().take_damage(amount): return True  
        health_ratio = self.health / self.max_health
        new_stage = 1
        if health_ratio < 0.33:
            new_stage = 3
        elif health_ratio < 0.66:
            new_stage = 2

        if new_stage != self.stage:
            self.stage = new_stage
            self.update_stage_attributes()
            create_particles(self.rect.center, 100, YELLOW, 3, 8, 30, 60);
            screen_shake = 20
        return False

    def update(self, player, all_sprites_group):
        direction = player.pos - self.pos
        if direction.length() == 0: return

        self.pos += direction.normalize() * self.speed;
        self.rect.center = self.pos
        self.action_timer += 1

        if self.laser_state:
            self.handle_laser_logic(player, all_sprites_group)
        else:
            if self.stage == 3 and self.action_timer % self.laser_cooldown == 0:
                self.laser_state, self.laser_aim_timer, self.triple_laser_count = "aiming", 120, 0
            elif self.stage < 3 and self.action_timer % self.laser_cooldown == 0:
                self.laser_state, self.laser_aim_timer = "aiming", 120
            elif self.action_timer % self.nova_cooldown == 0:
                for i in range(16): bullets.add(Bullet(self.rect.center, i * 22.5, True, ORANGE))
            elif self.action_timer % self.shoot_cooldown == 0:
                angle = math.degrees(math.atan2(-direction.y, direction.x))
                for i in range(-2, 3): bullets.add(Bullet(self.rect.center, angle + i * 15, True, self.color))

    def handle_laser_logic(self, player, all_sprites_group):
        if self.laser_state == "aiming":
            self.laser_aim_timer -= 1
            if self.laser_aim_timer <= 0: self.locked_target_pos, self.laser_state, self.laser_warn_timer = player.pos.copy(), "warning", 60
        elif self.laser_state == "warning":
            self.laser_warn_timer -= 1
            if self.laser_warn_timer <= 0:
                if self.locked_target_pos:
                    create_particles(self.rect.center, 80, PURPLE, 3, 9, 20, 40);
                    create_particles(self.rect.center, 40, WHITE, 2, 6, 15, 30)
                    beam_dir = self.locked_target_pos - self.pos
                    beam = EnergyBeam(self.pos + beam_dir.normalize() * 1000,
                                      math.degrees(math.atan2(-beam_dir.y, beam_dir.x)), 2000, 40)
                    beams.add(beam);
                    all_sprites_group.add(beam)

                if self.stage == 3 and self.triple_laser_count < 2:
                    self.triple_laser_count += 1
                    self.laser_state, self.laser_aim_timer = "aiming", 90
                else:
                    self.laser_state, self.action_timer = None, 0

class PowerUp(pygame.sprite.Sprite):
    def __init__(self, center_pos, type):
        super().__init__()
        self.type = type
        self.image = pygame.Surface((24, 24), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=center_pos)
        if type == 'health':
            pygame.draw.circle(self.image, (100, 100, 100), (12, 12), 12)
            pygame.draw.rect(self.image, GREEN, (10, 4, 4, 16));
            pygame.draw.rect(self.image, GREEN, (4, 10, 16, 4))
        elif type == 'rapid_fire':
            pygame.draw.circle(self.image, GREEN, (12, 12), 12, 3)
            text = ui_font.render('R', True, GREEN);
            self.image.blit(text, text.get_rect(center=(12, 12)))
        elif type == 'dash_charge':
            pygame.draw.polygon(self.image, BLUE, [(12, 0), (24, 12), (12, 24), (0, 12)])
        elif type == 'plasma_ball':
            pygame.draw.circle(self.image, BLUE, (12, 12), 12); pygame.draw.circle(self.image, WHITE, (12, 12), 6)

class Button:
    def __init__(self, x, y, width, height, text, action=None, font_size=36, toggle_dict=None, toggle_key=None):
        self.rect, self.text, self.action = pygame.Rect(x, y, width, height), text, action
        self.font = pygame.font.Font("freesansbold.ttf" if "freesansbold.ttf" else None, font_size)
        self.base_color, self.hover_color, self.text_color = (20, 20, 20), (50, 50, 50), WHITE
        self.toggle_dict, self.toggle_key = toggle_dict, toggle_key

    def draw(self, surface):
        is_on = self.toggle_dict.get(self.toggle_key) if self.toggle_dict else False
        border_color = GREEN if is_on else (100, 100, 100)
        color = self.hover_color if self.rect.collidepoint(pygame.mouse.get_pos()) else self.base_color
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=10)
        text_surf = self.font.render(self.text, True, self.text_color)
        surface.blit(text_surf, text_surf.get_rect(center=self.rect.center))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            if self.action: self.action()
            if self.toggle_dict: self.toggle_dict[self.toggle_key] = not self.toggle_dict[self.toggle_key]
            return True
        return False

def start_game(custom=False): global game_state; reset_game(custom); game_state = "game"

def toggle_fullscreen():
    global fullscreen, screen, WIDTH, HEIGHT, grid_surface
    fullscreen = not fullscreen
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN) 
        WIDTH, HEIGHT = screen.get_size() 
    else:
        WIDTH, HEIGHT = 1280, 720
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    grid_surface = create_grid_surface(WIDTH, HEIGHT, GRID_COLOR) 
    update_ui_positions()

def quit_game(): global running; running = False

def show_main_menu(): global game_state, score; score, game_state = 0, "menu"

def toggle_smooth_camera():
    global smooth_camera_follow
    smooth_camera_follow = not smooth_camera_follow

def reset_game(use_custom_settings=False):
    global player, all_sprites, bullets, enemies, plasma_balls, powerups, particles, beams, boss_group
    global current_wave, score, wave_timer, boss_fight_active, current_map_size, boss_powerup_spawn_timer
    player = Player()

    if use_custom_settings:
        start_wave = int(custom_start_wave_str) if custom_start_wave_str.isdigit() and custom_start_wave_str else 1
        current_wave = max(0, start_wave - 1)
        if custom_powerups['dash_charge']: player.dash_charges = player.max_dash_charges
        if custom_powerups[
            'rapid_fire']: player.rapid_fire_active, player.rapid_fire_end_time = True, pygame.time.get_ticks() + 999999
        if custom_powerups['plasma_ball']: player.has_plasma_ball = True
        current_map_size = 2000
    else:
        current_wave, current_map_size = 0, 2000

    all_sprites, enemies, bullets, plasma_balls = pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group()
    powerups, particles, beams, boss_group = pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group(), pygame.sprite.Group()
    all_sprites.add(player)
    score, wave_timer, boss_fight_active, boss_powerup_spawn_timer = 0, 0, False, 0

def update_ui_positions():
    global btn_start, btn_fullscreen, btn_quit, btn_menu, btn_custom_start
    global wave_input_box, dash_checkbox, rapid_checkbox, plasma_checkbox
    global btn_resume, btn_smooth_camera, btn_toggle_fullscreen, btn_pause_to_main_menu, grid_surface
    btn_start = Button(WIDTH // 2 - 150, HEIGHT // 2 - 80, 300, 60, "Start Game (Wave 1)", lambda: start_game(False), font_size=30)
    btn_fullscreen = Button(WIDTH // 2 - 150, HEIGHT // 2, 300, 60, "Toggle Fullscreen", toggle_fullscreen, font_size=30)
    btn_quit = Button(WIDTH // 2 - 150, HEIGHT // 2 + 80, 300, 60, "Quit", quit_game, font_size=30)
    btn_menu = Button(WIDTH - 130, HEIGHT - 60, 120, 50, "Menu", show_main_menu, font_size=24)

    btn_custom_start = Button(WIDTH // 2 - 150, HEIGHT - 140, 300, 50, "Start Custom Wave", lambda: start_game(True), font_size=30)
    wave_input_box = pygame.Rect(WIDTH // 2 - 150, HEIGHT - 220, 140, 40)
    dash_checkbox = Button(WIDTH // 2 + 10, HEIGHT - 220, 90, 40, "Dash", toggle_dict=custom_powerups,
                           toggle_key='dash_charge', font_size=16)
    rapid_checkbox = Button(WIDTH // 2 + 110, HEIGHT - 220, 90, 40, "Rapid", toggle_dict=custom_powerups,
                            toggle_key='rapid_fire', font_size=16)
    plasma_checkbox = Button(WIDTH // 2 + 210, HEIGHT - 220, 90, 40, "Plasma", toggle_dict=custom_powerups,
                             toggle_key='plasma_ball', font_size=16)

    btn_resume = Button(WIDTH // 2 - 150, HEIGHT // 2 - 100, 300, 60, "Resume Game", lambda: globals().update(game_paused=False), font_size=30)
    btn_smooth_camera = Button(WIDTH // 2 - 150, HEIGHT // 2 + 60, 300, 60, "Smooth Camera", None, font_size=30, toggle_dict=globals(), toggle_key='smooth_camera_follow')
    btn_toggle_fullscreen = Button(WIDTH // 2 - 150, HEIGHT // 2 + 140, 300, 60, "Toggle Fullscreen", toggle_fullscreen, font_size=30)
    btn_pause_to_main_menu = Button(WIDTH // 2 - 150, HEIGHT // 2 + 220, 300, 60, "Main Menu", show_main_menu, font_size=30)

    grid_surface = create_grid_surface(WIDTH, HEIGHT, GRID_COLOR)

btn_start, btn_fullscreen, btn_quit, btn_menu, btn_custom_start = None, None, None, None, None
wave_input_box, dash_checkbox, rapid_checkbox, plasma_checkbox = None, None, None, None
star_field = []
camera, game_state = pygame.math.Vector2(0, 0), "splash" if splash_screen_active else "menu"
if game_state == "splash": 
    splash_start_time = pygame.time.get_ticks()
reset_game();
update_ui_positions()

try:

    splash_image_path = resource_path("calistasplash.png") 
    splash_original_image = pygame.image.load(splash_image_path).convert_alpha()

    original_width, original_height = splash_original_image.get_size()
    new_width, new_height = int(original_width * 0.7), int(original_height * 0.7)
    splash_image = pygame.transform.scale(splash_original_image, (new_width, new_height))
    splash_rect = splash_image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
except pygame.error as e:

    print(f"Warning: Could not load calistasplash.png. Error: {e}")
    splash_screen_active = False 

clock = pygame.time.Clock()
running = True
while running:

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if game_state == "game":
                    game_paused = True 
                elif game_state == "menu":
                    running = False
            if game_state == "game" and event.key == pygame.K_SPACE: player.dash()
            if event.key == pygame.K_p and game_state == "game": 
                game_paused = not game_paused
            if game_state == "game" and event.key == pygame.K_ESCAPE:
                game_paused = True 
            elif event.key == pygame.K_ESCAPE and game_state == "menu": 
                running = False
            if game_state == "menu" and wave_input_active:
                if event.key == pygame.K_BACKSPACE:
                    custom_start_wave_str = custom_start_wave_str[:-1]
                elif event.unicode.isdigit():
                    custom_start_wave_str += event.unicode
        if event.type == pygame.VIDEORESIZE and not fullscreen:
            WIDTH, HEIGHT = event.w, event.h;
            screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE);
            update_ui_positions()

        if game_state == "menu":
            for btn in [btn_start, btn_fullscreen, btn_quit, btn_custom_start, dash_checkbox, rapid_checkbox,
                        plasma_checkbox]: btn.handle_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: wave_input_active = wave_input_box.collidepoint(
                event.pos)
        elif game_state == "game":
            if game_paused:
                for btn in [btn_resume, btn_smooth_camera, btn_toggle_fullscreen, btn_pause_to_main_menu]:
                    btn.handle_event(event)
            else:
                btn_menu.handle_event(event)
                if not player.rapid_fire_active and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and player.can_shoot():
                    bullets.add(Bullet(player.shoot_position(), player.angle));
                    player.ammo -= 1;
                    player.last_shot_time = pygame.time.get_ticks()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and player.has_plasma_ball:
                plasma_balls.add(PlasmaBall(player.shoot_position(), player.angle));
                player.has_plasma_ball = False

    if game_state == "menu":
        screen.fill(BLACK)
        for star in star_field:
            star[1] += star[2] * 0.2
            if star[1] > HEIGHT: star[0], star[1] = random.randint(0, WIDTH), -5
            pygame.draw.rect(screen, WHITE, (star[0], star[1], star[2], star[2]))

        title_surf = title_font.render("Arow", True, WHITE)
        screen.blit(title_surf, title_surf.get_rect(
            center=(WIDTH // 2, HEIGHT // 4 + math.sin(pygame.time.get_ticks() * 0.001) * 10)))
        for btn in [btn_start, btn_fullscreen, btn_quit, btn_custom_start, dash_checkbox, rapid_checkbox,
                    plasma_checkbox]: btn.draw(screen)

        screen.blit(font.render("Custom Start Options", True, WHITE), (wave_input_box.x, wave_input_box.y - 30))
        pygame.draw.rect(screen, (50, 50, 50), wave_input_box)
        pygame.draw.rect(screen, GREEN if wave_input_active else (100, 100, 100), wave_input_box, 2)
        screen.blit(ui_font.render("Wave:", True, WHITE), (wave_input_box.x + 5, wave_input_box.y - 20))
        wave_text_surf = font.render(custom_start_wave_str, True, WHITE);
        screen.blit(wave_text_surf, wave_text_surf.get_rect(center=wave_input_box.center))

    elif game_state == "splash": 
        if splash_screen_active:
            current_time = pygame.time.get_ticks()
            elapsed_time = current_time - splash_start_time

            screen.fill(BLACK) 

            if splash_image and splash_rect:
                alpha = 255
                if elapsed_time < fade_in_duration: 
                    alpha = int(255 * (elapsed_time / fade_in_duration))
                elif elapsed_time > (splash_duration - fade_out_duration): 
                    alpha = int(255 * ((splash_duration - elapsed_time) / fade_out_duration))

                temp_splash_image = splash_image.copy()
                temp_splash_image.set_alpha(alpha)
                screen.blit(temp_splash_image, splash_rect)

            if elapsed_time >= splash_duration:
                game_state = "menu" 
                splash_screen_active = False 
        else:
            game_state = "menu" 

    elif game_state == "game" and game_paused: 
        screen.fill(BLACK)
        pause_text = title_font.render("PAUSED", True, WHITE)
        screen.blit(pause_text, pause_text.get_rect(center=(WIDTH // 2, HEIGHT // 4)))
        for btn in [btn_resume, btn_smooth_camera, btn_toggle_fullscreen, btn_pause_to_main_menu]:
            btn.draw(screen)

    elif game_state == "game":
        if player.rapid_fire_active and pygame.mouse.get_pressed()[0] and player.can_shoot():
            bullets.add(Bullet(player.shoot_position(), player.angle));
            player.ammo -= 1;
            player.last_shot_time = pygame.time.get_ticks()

        if not game_paused: 

            player.update(camera);
            enemies.update(player, all_sprites);
            boss_group.update(player, all_sprites);
            bullets.update()
            plasma_balls.update();
            particles.update();
            beams.update();
            powerups.update()

            if player.take_damage(0): game_state = "game_over"
            for bullet in list(bullets):
                if not bullet.is_enemy:
                    hit_list = pygame.sprite.spritecollide(bullet, enemies, False) + pygame.sprite.spritecollide(bullet,
                                                                                                                 boss_group,
                                                                                                                 False)
                    if hit_list: bullet.kill()
                    for enemy in hit_list:
                        if enemy.take_damage(1):
                            score += enemy.score_value;
                            create_particles(enemy.rect.center, 30, enemy.color, 2, 5, 20, 40)
                            if random.random() < POWERUP_DROP_CHANCE: powerups.add(
                                PowerUp(enemy.rect.center, random.choice(POWERUP_DROP_TABLE)))
            for bullet in bullets:
                if bullet.is_enemy and not player.is_dashing and pygame.sprite.collide_rect(bullet, player):
                    if player.take_damage(1): game_state = "game_over"
                    bullet.kill();
                    create_particles(bullet.rect.center, 10, RED, 1, 3, 15, 25);
                    screen_shake = 10
            for beam in beams:
                if not player.is_dashing and beam.lifespan > 0 and pygame.sprite.collide_mask(beam, player):
                    if player.take_damage(beam.damage): game_state = "game_over"
                    create_particles(player.rect.center, 5, PURPLE, 1, 2, 10, 15);
                    screen_shake = 5
            if not player.is_dashing and (
                    pygame.sprite.spritecollide(player, enemies, True) or pygame.sprite.spritecollide(player, boss_group,
                                                                                                      False)):
                if player.take_damage(player.max_health): game_state = "game_over"
            for p_ball in list(plasma_balls):
                if pygame.sprite.spritecollide(p_ball, enemies, False) or pygame.sprite.spritecollide(p_ball, boss_group,
                                                                                                      False): p_ball.explode()
            for powerup in pygame.sprite.spritecollide(player, powerups, True):
                if powerup.type == 'health':
                    player.health = min(player.max_health, player.health + 1)
                elif powerup.type == 'rapid_fire':
                    player.rapid_fire_active, player.rapid_fire_end_time = True, pygame.time.get_ticks() + 5000
                elif powerup.type == 'dash_charge':
                    player.dash_charges = min(player.max_dash_charges, player.dash_charges + 1)
                elif powerup.type == 'plasma_ball':
                    player.has_plasma_ball = True

            if boss_fight_active:
                boss_powerup_spawn_timer += 1
                if boss_powerup_spawn_timer > BOSS_POWERUP_SPAWN_RATE:
                    boss_powerup_spawn_timer = 0
                    map_edge = (MAP_WIDTH - current_map_size) / 2
                    spawn_x = random.uniform(map_edge, map_edge + current_map_size)
                    spawn_y = random.uniform(map_edge, map_edge + current_map_size)
                    powerups.add(PowerUp((spawn_x, spawn_y), random.choice(POWERUP_DROP_TABLE)))
                if not boss_group:
                    boss_fight_active = False;
                    player.health, player.ammo = player.max_health, player.max_ammo
                    create_particles(player.pos, 50, GREEN, 2, 6, 30, 60)
            elif len(enemies) == 0 and wave_timer > WAVE_COOLDOWN:
                wave_timer, current_wave = 0, current_wave + 1
                if current_wave > 0 and current_wave % 10 == 0:
                    boss_fight_active = True;
                    boss_group.add(Boss(MAP_WIDTH / 2, MAP_HEIGHT / 2))
                else:
                    enemies_per_wave = 2 + current_wave
                    for _ in range(enemies_per_wave):
                        map_rect = pygame.Rect((MAP_WIDTH - current_map_size) / 2, (MAP_HEIGHT - current_map_size) / 2,
                                               current_map_size, current_map_size)
                        edge = random.choice(['top', 'bottom', 'left', 'right'])
                        if edge == 'top':
                            x, y = random.uniform(map_rect.left, map_rect.right), map_rect.top
                        elif edge == 'bottom':
                            x, y = random.uniform(map_rect.left, map_rect.right), map_rect.bottom
                        elif edge == 'left':
                            x, y = map_rect.left, random.uniform(map_rect.top, map_rect.bottom)
                        else:
                            x, y = map_rect.right, random.uniform(map_rect.top, map_rect.bottom)
                        enemies.add(Enemy(x, y, random.choice(["charger", "shooter", "shooter", "sniper"])))
            elif len(enemies) == 0:
                wave_timer += 1

        target_camera_x, target_camera_y = player.pos.x - WIDTH / 2, player.pos.y - HEIGHT / 2
        if smooth_camera_follow: 
            camera.x += (target_camera_x - camera.x) * camera_smooth_factor
            camera.y += (target_camera_y - camera.y) * camera_smooth_factor
        else: 
            camera.x, camera.y = target_camera_x, target_camera_y

        render_offset = [random.randint(-screen_shake, screen_shake) if screen_shake > 0 else 0 for _ in 'xy']
        if screen_shake > 0: screen_shake -= 1

        screen.fill(BLACK)
        start_x, start_y = int(-camera.x + render_offset[0]) % 100, int(-camera.y + render_offset[1]) % 100

        screen.blit(grid_surface, (start_x, start_y))
        screen.blit(grid_surface, (start_x - WIDTH, start_y))
        screen.blit(grid_surface, (start_x, start_y - HEIGHT))
        screen.blit(grid_surface, (start_x - WIDTH, start_y - HEIGHT))

        game_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        map_rect = pygame.Rect(
            ((MAP_WIDTH - current_map_size) / 2 - camera.x, (MAP_HEIGHT - current_map_size) / 2 - camera.y),
            (current_map_size, current_map_size))
        pygame.draw.rect(game_surf, WHITE, map_rect, 3)

        for enemy in enemies:
            if enemy.enemy_type == 'sniper' and enemy.state == 'aiming':
                pygame.draw.line(game_surf, RED, (enemy.rect.centerx - camera.x, enemy.rect.centery - camera.y),
                                 (player.pos.x - camera.x, player.pos.y - camera.y), 1)
            elif enemy.enemy_type == 'sniper' and enemy.state == 'warning' and enemy.warn_timer % 10 < 5:
                pygame.draw.circle(game_surf, WHITE, (enemy.rect.centerx - camera.x, enemy.rect.centery - camera.y),
                                   enemy.rect.width)
        for boss in boss_group:
            if boss.laser_state == 'aiming':
                pygame.draw.line(game_surf, RED, (boss.rect.centerx - camera.x, boss.rect.centery - camera.y),
                                 (player.pos.x - camera.x, player.pos.y - camera.y), 3)
            elif boss.laser_state == 'warning' and boss.laser_warn_timer % 10 < 5:
                pygame.draw.circle(game_surf, WHITE, (boss.rect.centerx - camera.x, boss.rect.centery - camera.y),
                                   boss.rect.width / 2)

        for group in [enemies, boss_group, bullets, plasma_balls, powerups, particles, beams, [player]]:
            for sprite in group: game_surf.blit(sprite.image, (sprite.rect.x - camera.x, sprite.rect.y - camera.y))

        screen.blit(game_surf, render_offset)

        health_ratio = player.health / player.max_health if player.max_health > 0 else 0
        pygame.draw.rect(screen, (80, 0, 0), (10, 10, 200, 20))
        if player.health > 0: pygame.draw.rect(screen,
                                               (GREEN if health_ratio > 0.5 else YELLOW if health_ratio > 0.2 else RED),
                                               (10, 10, 200 * health_ratio, 20))
        ammo_text = "RELOADING..." if player.reloading else f"AMMO: {player.ammo}/{player.max_ammo}"
        screen.blit(font.render(ammo_text, True, WHITE), (10, 40))
        screen.blit(font.render(f"SCORE: {score}", True, WHITE), (10, 70))
        wave_text = "BOSS WAVE" if boss_fight_active else f"WAVE: {current_wave + 1}"
        screen.blit(font.render(wave_text, True, WHITE), (WIDTH - 200, 10))
        if boss_fight_active and boss_group:
            boss = boss_group.sprites()[0]
            boss_health_ratio = boss.health / boss.max_health if boss.max_health > 0 else 0
            pygame.draw.rect(screen, (80, 0, 0), (WIDTH / 2 - 250, HEIGHT - 40, 500, 25))
            if boss.health > 0: pygame.draw.rect(screen, PURPLE,
                                                 (WIDTH / 2 - 250, HEIGHT - 40, 500 * boss_health_ratio, 25))
        for i in range(player.max_dash_charges): pygame.draw.rect(screen,
                                                                  BLUE if i < player.dash_charges else (50, 50, 50),
                                                                  (10 + i * 25, 110, 20, 20))
        if player.has_plasma_ball: pygame.draw.circle(screen, BLUE, (120, 120), 15); pygame.draw.circle(screen, WHITE,
                                                                                                        (120, 120), 8)
        btn_menu.draw(screen)

    elif game_state == "game_over":
        screen.fill(BLACK)
        for f, t, c, y in [(title_font, "GAME OVER", RED, HEIGHT // 3),
                           (font, f"Final Score: {score}", WHITE, HEIGHT // 2),
                           (font, "Press R to restart or M for menu", WHITE, HEIGHT // 2 + 50)]:
            surf = f.render(t, True, c);
            screen.blit(surf, surf.get_rect(center=(WIDTH // 2, y)))
        keys = pygame.key.get_pressed()
        if keys[pygame.K_r]:
            start_game()
        elif keys[pygame.K_m]:
            show_main_menu()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
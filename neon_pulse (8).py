"""
NEON PULSE
==========
A neon-colored survival shooter game.

HOW TO PLAY
-----------
- Move:        WASD or Arrow Keys
- Attack:      Automatic (your gun always shoots the closest enemy)
- Level Up:    Press 1, 2, or 3 to pick a new power or weapon
- Pause:       ESC
- Restart:     R (after Game Over)
- Quit:        Close the window

GOAL
----
Stay alive through as many waves as you can. Enemies get stronger every
wave, and a BOSS shows up every 5th wave. Kill enemies to get XP orbs,
level up, and pick new powers or weapons (Spinning Blades, Chasing
Rocket, Laser, Shock Wave) to get stronger and stronger. Weapons can be
leveled up all the way to Level 10.

ENEMIES
-------
- Grunt     : fast but weak, runs straight at you
- Brute     : slow but has a lot of health
- Shooter   : stays far away and shoots at you
- Swarm     : tiny and very fast, comes in groups
- Splitter  : splits into 2 smaller weak enemies when killed
- Sniper    : shows a red aiming line, then fires one strong, exact shot
- Bomber    : rushes at you and explodes when it dies, hurting you and
              anything else nearby (even other enemies)
- Shielder  : turns invincible for a few seconds at a time, then drops
              its shield - time your hits
- Boss      : shows up every 5th wave, 4 different bosses take turns

BOSSES (one shows up every 5th wave, they rotate in this order)
------------------------------------------------------------------
- PULSAR : a spinning star. Fires rings of bullets that get faster and
           faster as it loses health, adds a spinning bullet stream,
           charges at you when low on health, and drops timed mines.
- WARDEN : a turret-like hexagon. Fires aimed 3-shot bursts, calls in
           small enemies to help it, sweeps a rotating laser beam across
           the room, and drops void zones on the ground.
- REAPER : a fast glass-cannon. Teleports next to you and fires a burst
           of bullets, throws a spread of blades, and chains 3 fast
           dashes at you in a row once it's below half health.
- HIVE   : a slow, tanky boss. Calls in groups of small enemies often,
           releases a wide ring of slow spore bullets, and slowly heals
           itself over time, so keep the pressure on.

WEAPONS (you pick these when you level up, up to Level 10 each)
--------------------------------------------------------------------
- Gun (Blaster)   : you always have this, shoots the closest enemy
- Spinning Blades : blades that spin around you and hurt anything they touch
- Chasing Rocket  : fires rockets that follow enemies and explode
- Laser           : a beam that hits the closest enemy and goes through them
- Shock Wave      : a wave of damage that bursts out from you now and then

INSTALL & RUN
--------------
    pip install pygame numpy
    python neon_pulse.py
"""
import pygame
import random
import math
import sys
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
WIDTH, HEIGHT = 960, 720
FPS = 60

BG_COLOR = (8, 8, 18)
GRID_COLOR = (24, 26, 48)

NEON_CYAN = (60, 240, 255)
NEON_PINK = (255, 60, 180)
NEON_PURPLE = (170, 90, 255)
NEON_YELLOW = (255, 230, 90)
NEON_GREEN = (110, 255, 140)
NEON_ORANGE = (255, 150, 60)
NEON_RED = (255, 70, 90)
NEON_TEAL = (90, 230, 190)
NEON_FLAME = (255, 100, 40)
NEON_MINT = (140, 255, 190)
WHITE = (245, 245, 255)

random.seed()


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def lerp(a, b, t):
    return a + (b - a) * t


def point_segment_distance(px, py, ax, ay, bx, by):
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    ab2 = abx * abx + aby * aby
    t = 0 if ab2 == 0 else clamp((apx * abx + apy * aby) / ab2, 0, 1)
    cx, cy = ax + abx * t, ay + aby * t
    return math.hypot(px - cx, py - cy)


def draw_glow_circle(surface, color, pos, radius, intensity=3):
    x, y = int(pos[0]), int(pos[1])
    for i in range(intensity, 0, -1):
        r = int(radius * (1 + i * 0.55))
        alpha = int(70 / i)
        glow_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, alpha), (r, r), r)
        surface.blit(glow_surf, (x - r, y - r), special_flags=pygame.BLEND_RGBA_ADD)
    pygame.draw.circle(surface, color, (x, y), int(radius))


def draw_glow_line(surface, color, p1, p2, width=2, intensity=2):
    for i in range(intensity, 0, -1):
        w = width + i * 3
        alpha = int(90 / i)
        line_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(line_surf, (*color, alpha), p1, p2, w)
        surface.blit(line_surf, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    pygame.draw.line(surface, color, p1, p2, width)


# ----------------------------------------------------------------------
# SOUND (procedurally synthesized, no external audio files needed)
# ----------------------------------------------------------------------
class SoundManager:
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        self.last_played = {}
        if not HAS_NUMPY:
            return
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2)
            pygame.mixer.set_num_channels(24)
            self.enabled = True
            self._build_sounds()
        except Exception:
            self.enabled = False

    def _tone(self, freq, duration, volume=0.4, wave="sine", freq_end=None, fade_out=True):
        sr = 44100
        n = max(1, int(sr * duration))
        t = np.linspace(0, duration, n, False)
        if freq_end is not None:
            freqs = np.linspace(freq, freq_end, n)
            phase = 2 * np.pi * np.cumsum(freqs) / sr
        else:
            phase = 2 * np.pi * freq * t
        if wave == "square":
            data = np.sign(np.sin(phase))
        elif wave == "saw":
            data = 2 * (phase / (2 * np.pi) - np.floor(0.5 + phase / (2 * np.pi)))
        elif wave == "noise":
            data = np.random.uniform(-1, 1, n)
        else:
            data = np.sin(phase)
        if fade_out:
            fade = np.linspace(1, 0, n) ** 1.4
            data = data * fade
        data = data * volume
        arr = np.zeros((n, 2), dtype=np.int16)
        vals = (data * 32767).astype(np.int16)
        arr[:, 0] = vals
        arr[:, 1] = vals
        return pygame.sndarray.make_sound(arr)

    def _arpeggio(self, freqs, note_dur=0.09, volume=0.3):
        sr = 44100
        chunks = []
        for f in freqs:
            n = int(sr * note_dur)
            t = np.linspace(0, note_dur, n, False)
            data = np.sin(2 * np.pi * f * t)
            fade = np.linspace(1, 0, n) ** 1.2
            chunks.append(data * fade * volume)
        full = np.concatenate(chunks)
        arr = np.zeros((len(full), 2), dtype=np.int16)
        vals = (full * 32767).astype(np.int16)
        arr[:, 0] = vals
        arr[:, 1] = vals
        return pygame.sndarray.make_sound(arr)

    def _build_sounds(self):
        s = self.sounds
        s["shoot"] = self._tone(950, 0.05, 0.22, "square", freq_end=1050)
        s["hit"] = self._tone(320, 0.035, 0.16, "square", freq_end=140)
        s["explode"] = self._tone(180, 0.22, 0.30, "noise")
        s["hurt"] = self._tone(220, 0.16, 0.32, "square", freq_end=80)
        s["missile"] = self._tone(500, 0.09, 0.22, "saw", freq_end=750)
        s["laser"] = self._tone(1300, 0.30, 0.18, "sine", freq_end=1500)
        s["nova"] = self._tone(160, 0.35, 0.28, "sine", freq_end=55)
        s["orbit_hit"] = self._tone(550, 0.03, 0.10, "square")
        s["wave"] = self._tone(440, 0.25, 0.22, "square", freq_end=440)
        s["boss"] = self._tone(110, 0.6, 0.32, "square", freq_end=90)
        s["boss_shot"] = self._tone(260, 0.08, 0.15, "square", freq_end=150)
        s["gameover"] = self._tone(320, 0.6, 0.28, "sine", freq_end=70)
        s["snipe"] = self._tone(1500, 0.07, 0.24, "square", freq_end=1900)
        s["enemy_shot"] = self._tone(420, 0.06, 0.14, "saw", freq_end=260)
        s["levelup"] = self._arpeggio([523, 659, 784, 1046])
        s["pickup"] = self._tone(900, 0.03, 0.10, "sine", freq_end=1200)

    def play(self, name, min_interval_ms=30):
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        now = pygame.time.get_ticks()
        last = self.last_played.get(name, -999999)
        if now - last < min_interval_ms:
            return
        self.last_played[name] = now
        try:
            snd.play()
        except Exception:
            pass


# ----------------------------------------------------------------------
# PARTICLES
# ----------------------------------------------------------------------
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x, y, color, speed_range=(1, 5), life=0.6, size=3):
        self.x, self.y = x, y
        ang = random.uniform(0, math.tau)
        spd = random.uniform(*speed_range)
        self.vx = math.cos(ang) * spd
        self.vy = math.sin(ang) * spd
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size

    def update(self, dt):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.94
        self.vy *= 0.94
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        t = clamp(self.life / self.max_life, 0, 1)
        r = max(1, int(self.size * t))
        alpha = int(255 * t)
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (r, r), r)
        surface.blit(s, (self.x - r, self.y - r), special_flags=pygame.BLEND_RGBA_ADD)


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, color, count=14, speed_range=(1, 6), life=0.6, size=3):
        for _ in range(count):
            self.particles.append(Particle(x, y, color, speed_range, life, size))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)


# ----------------------------------------------------------------------
# PROJECTILES
# ----------------------------------------------------------------------
class Bullet:
    def __init__(self, x, y, vx, vy, damage, color=NEON_CYAN, radius=5, pierce=0):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.damage = damage
        self.color = color
        self.radius = radius
        self.pierce = pierce
        self.alive = True
        self.trail = []

    def update(self, dt):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 5:
            self.trail.pop(0)
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < -50 or self.x > WIDTH + 50 or self.y < -50 or self.y > HEIGHT + 50:
            self.alive = False

    def draw(self, surface):
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(150 * (i + 1) / len(self.trail))
            s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color, alpha), (self.radius, self.radius), max(1, self.radius - 1))
            surface.blit(s, (tx - self.radius, ty - self.radius), special_flags=pygame.BLEND_RGBA_ADD)
        draw_glow_circle(surface, self.color, (self.x, self.y), self.radius, intensity=2)


class EnemyBullet:
    def __init__(self, x, y, vx, vy, damage, color=NEON_ORANGE, radius=6, life=None):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.damage = damage
        self.alive = True
        self.radius = radius
        self.color = color
        self.life = life
        self.pulse = random.uniform(0, math.tau)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.pulse += dt * 6
        if self.life is not None:
            self.life -= dt
            if self.life <= 0:
                self.alive = False
        if self.x < -50 or self.x > WIDTH + 50 or self.y < -50 or self.y > HEIGHT + 50:
            self.alive = False

    def draw(self, surface):
        r = self.radius
        if self.life is not None:
            r = self.radius * (1 + 0.15 * math.sin(self.pulse))
        draw_glow_circle(surface, self.color, (self.x, self.y), r, intensity=2)


class Missile:
    def __init__(self, x, y, target, speed, damage, aoe_radius):
        self.x, self.y = x, y
        self.target = target
        self.speed = speed
        self.damage = damage
        self.aoe_radius = aoe_radius
        ang = random.uniform(0, math.tau)
        self.vx = math.cos(ang) * speed * 0.4
        self.vy = math.sin(ang) * speed * 0.4
        self.alive = True
        self.age = 0
        self.trail = []

    def update(self, dt, enemies):
        self.age += dt
        if self.target is None or not self.target.alive:
            self.target = min(enemies, key=lambda e: (e.x - self.x) ** 2 + (e.y - self.y) ** 2) if enemies else None

        if self.target:
            dx, dy = self.target.x - self.x, self.target.y - self.y
            dist = math.hypot(dx, dy) or 1
            desired_vx, desired_vy = dx / dist * self.speed, dy / dist * self.speed
            turn = clamp(dt * 7, 0, 1)
            self.vx = lerp(self.vx, desired_vx, turn)
            self.vy = lerp(self.vy, desired_vy, turn)

        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x < -60 or self.x > WIDTH + 60 or self.y < -60 or self.y > HEIGHT + 60 or self.age > 4.5:
            self.alive = False

    def draw(self, surface):
        for i, (tx, ty) in enumerate(self.trail):
            alpha = int(140 * (i + 1) / max(1, len(self.trail)))
            s = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(s, (*NEON_ORANGE, alpha), (5, 5), 4)
            surface.blit(s, (tx - 5, ty - 5), special_flags=pygame.BLEND_RGBA_ADD)
        draw_glow_circle(surface, NEON_ORANGE, (self.x, self.y), 6, intensity=2)


class XPOrb:
    def __init__(self, x, y, value=1):
        self.x, self.y = x, y
        self.value = value
        self.alive = True
        self.t = random.uniform(0, math.tau)

    def update(self, dt, player, sound=None):
        self.t += dt * 4
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy)
        if dist < player.pickup_radius:
            pull = clamp(1 - dist / player.pickup_radius, 0.1, 1) * 480
            if dist > 1:
                self.x += dx / dist * pull * dt
                self.y += dy / dist * pull * dt
        if dist < 14:
            self.alive = False
            player.gain_xp(self.value)
            if sound:
                sound.play("pickup", 20)

    def draw(self, surface):
        bob = math.sin(self.t) * 2
        draw_glow_circle(surface, NEON_GREEN, (self.x, self.y + bob), 5, intensity=2)


# ----------------------------------------------------------------------
# ENEMIES
# ----------------------------------------------------------------------
ENEMY_TYPES = {
    "grunt": dict(hp=18, speed=95, radius=12, color=NEON_PINK, damage=8, xp=24, score=10),
    "brute": dict(hp=60, speed=55, radius=20, color=NEON_PURPLE, damage=16, xp=72, score=25),
    "shooter": dict(hp=22, speed=70, radius=13, color=NEON_YELLOW, damage=10, xp=48, score=20),
    "swarm": dict(hp=5, speed=155, radius=8, color=(255, 130, 190), damage=4, xp=24, score=5),
    "splitter": dict(hp=42, speed=62, radius=17, color=NEON_TEAL, damage=12, xp=48, score=18),
    "splitter_mini": dict(hp=10, speed=115, radius=9, color=NEON_TEAL, damage=6, xp=24, score=8),
    "sniper": dict(hp=16, speed=48, radius=13, color=NEON_RED, damage=22, xp=48, score=24),
    "bomber": dict(hp=26, speed=118, radius=14, color=(255, 120, 40), damage=14, xp=40, score=26),
    "shielder": dict(hp=36, speed=58, radius=15, color=(120, 210, 255), damage=10, xp=38, score=28),
}

KIND_SIDES = {
    "grunt": 3, "brute": 6, "shooter": 4, "swarm": 3,
    "splitter": 5, "splitter_mini": 5, "sniper": 4,
    "bomber": 4, "shielder": 8,
}


class Enemy:
    def __init__(self, kind, x, y, wave_mult=1.0):
        cfg = ENEMY_TYPES[kind]
        self.kind = kind
        self.x, self.y = x, y
        self.max_hp = cfg["hp"] * wave_mult
        self.hp = self.max_hp
        self.speed = cfg["speed"]
        self.radius = cfg["radius"]
        self.color = cfg["color"]
        self.damage = cfg["damage"]
        self.xp = cfg["xp"]
        self.score = cfg["score"]
        self.alive = True
        self.hit_flash = 0
        self.fire_cd = random.uniform(0.5, 1.5)
        self.spin = random.uniform(0, math.tau)
        self.orbit_hit_cd = 0.0
        self.charging = False
        self.charge_t = 0.0
        self.charge_target = (0.0, -1.0)
        self.shielded = False
        self.shield_timer = random.uniform(1.5, 2.5)

    def update(self, dt, player, enemy_bullets, sound=None):
        self.spin += dt * 2
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy) or 1

        if self.kind == "shielder":
            self.shield_timer -= dt
            if self.shield_timer <= 0:
                self.shielded = not self.shielded
                self.shield_timer = 1.5 if self.shielded else 2.2

        if self.kind == "shooter":
            desired = 260
            if dist < desired - 20:
                self.x -= dx / dist * self.speed * dt
                self.y -= dy / dist * self.speed * dt
            elif dist > desired + 20:
                self.x += dx / dist * self.speed * dt
                self.y += dy / dist * self.speed * dt
            self.fire_cd -= dt
            if self.fire_cd <= 0 and dist < 500:
                self.fire_cd = random.uniform(1.4, 2.0)
                spd = 260
                enemy_bullets.append(EnemyBullet(self.x, self.y, dx / dist * spd, dy / dist * spd, self.damage))
                if sound:
                    sound.play("enemy_shot", 90)

        elif self.kind == "sniper":
            desired = 340
            if not self.charging:
                if dist < desired - 20:
                    self.x -= dx / dist * self.speed * dt
                    self.y -= dy / dist * self.speed * dt
                elif dist > desired + 20:
                    self.x += dx / dist * self.speed * dt
                    self.y += dy / dist * self.speed * dt
                self.fire_cd -= dt
                if self.fire_cd <= 0 and dist < 620:
                    self.charging = True
                    self.charge_t = 0.85
                    self.charge_target = (dx / dist, dy / dist)
            else:
                self.charge_t -= dt
                if self.charge_t <= 0:
                    self.charging = False
                    self.fire_cd = random.uniform(2.0, 2.6)
                    spd = 540
                    cvx, cvy = self.charge_target
                    enemy_bullets.append(EnemyBullet(self.x, self.y, cvx * spd, cvy * spd, self.damage, color=NEON_RED, radius=7))
                    if sound:
                        sound.play("snipe", 100)
        else:
            self.x += dx / dist * self.speed * dt
            self.y += dy / dist * self.speed * dt

        if self.hit_flash > 0:
            self.hit_flash -= dt
        if self.orbit_hit_cd > 0:
            self.orbit_hit_cd -= dt

    def take_damage(self, amount):
        if self.shielded:
            self.hit_flash = 0.05
            return False
        self.hp -= amount
        self.hit_flash = 0.08
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    def draw(self, surface):
        col = WHITE if self.hit_flash > 0 else self.color
        if self.kind == "shielder" and self.shielded and self.hit_flash <= 0:
            col = (120, 210, 255)

        if self.kind == "sniper" and self.charging:
            t = 1 - clamp(self.charge_t / 0.85, 0, 1)
            fx = self.x + self.charge_target[0] * 900
            fy = self.y + self.charge_target[1] * 900
            alpha_intensity = 1 + int(t * 3)
            draw_glow_line(surface, NEON_RED, (self.x, self.y), (fx, fy), width=1, intensity=alpha_intensity)

        n = KIND_SIDES.get(self.kind, 4)
        pts = []
        for i in range(n):
            ang = self.spin + i * math.tau / n
            pts.append((self.x + math.cos(ang) * self.radius, self.y + math.sin(ang) * self.radius))
        glow = pygame.Surface((self.radius * 4, self.radius * 4), pygame.SRCALPHA)
        gc = (self.radius * 2, self.radius * 2)
        pygame.draw.circle(glow, (*col, 60), gc, self.radius * 2)
        surface.blit(glow, (self.x - self.radius * 2, self.y - self.radius * 2), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.polygon(surface, col, pts, width=0)
        pygame.draw.polygon(surface, WHITE, pts, width=1)

        if self.kind == "shielder" and self.shielded:
            pygame.draw.circle(surface, (120, 210, 255), (int(self.x), int(self.y)), self.radius + 8, width=3)

        if self.hp < self.max_hp:
            w = self.radius * 2
            ratio = clamp(self.hp / self.max_hp, 0, 1)
            bx, by = self.x - w / 2, self.y - self.radius - 10
            pygame.draw.rect(surface, (40, 40, 50), (bx, by, w, 4))
            pygame.draw.rect(surface, NEON_GREEN, (bx, by, w * ratio, 4))


class BossPulsar(Enemy):
    """Boss type 1: a spinning star that gets more aggressive as it loses health.
    Phase 1 (HP > 66%):  slow ring bursts of bullets.
    Phase 2 (33-66%):    faster ring bursts + a spinning stream of bullets.
    Phase 3 (< 33%):     fastest ring bursts + spinning stream + charges at you.
    All the while it drops timed mines that explode after a short delay.
    """

    def __init__(self, x, y, wave):
        self.kind = "boss"
        self.name = "PULSAR"
        self.x, self.y = x, y
        self.max_hp = 560 + wave * 85
        self.hp = self.max_hp
        self.speed = 46
        self.radius = 42
        self.color = NEON_ORANGE
        self.damage = 30
        self.base_damage = self.damage
        self.xp = 820
        self.score = 380
        self.alive = True
        self.hit_flash = 0
        self.spin = 0
        self.orbit_hit_cd = 0.0
        self.shielded = False

        self.ring_cd = 1.6
        self.spiral_cd = 0.0
        self.spiral_angle = 0.0

        self.dash_cd = random.uniform(3.0, 4.0)
        self.dash_telegraph = 0.0
        self.dashing = False
        self.dash_timer = 0.0
        self.dash_vx = 0.0
        self.dash_vy = 0.0

        self.mine_cd = random.uniform(2.0, 2.8)
        self.mines = []

    def update(self, dt, player, enemy_bullets, sound=None):
        self.spin += dt * 0.8
        hp_ratio = self.hp / self.max_hp
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy) or 1

        if self.dashing:
            self.dash_timer -= dt
            self.x += self.dash_vx * dt
            self.y += self.dash_vy * dt
            if self.dash_timer <= 0:
                self.dashing = False
                self.damage = self.base_damage
                self.dash_cd = random.uniform(3.0, 4.5)
        elif self.dash_telegraph > 0:
            self.dash_telegraph -= dt
            if self.dash_telegraph <= 0:
                self.dashing = True
                self.dash_timer = 0.4
                self.damage = self.base_damage * 1.7
                self.dash_vx = dx / dist * 560
                self.dash_vy = dy / dist * 560
                if sound:
                    sound.play("boss_shot", 100)
        else:
            desired = 220
            speed = self.speed
            if hp_ratio <= 0.33:
                speed = self.speed * 1.55
            elif hp_ratio <= 0.66:
                speed = self.speed * 1.25
            if dist < desired - 15:
                self.x -= dx / dist * speed * dt
                self.y -= dy / dist * speed * dt
            elif dist > desired + 15:
                self.x += dx / dist * speed * dt
                self.y += dy / dist * speed * dt

            self.ring_cd -= dt
            if self.ring_cd <= 0:
                self.ring_cd = 1.6 if hp_ratio > 0.66 else (1.3 if hp_ratio > 0.33 else 0.9)
                n = 10 if hp_ratio > 0.33 else 14
                for i in range(n):
                    ang = self.spin + i * math.tau / n
                    spd = 190
                    enemy_bullets.append(EnemyBullet(self.x, self.y, math.cos(ang) * spd, math.sin(ang) * spd, self.damage * 0.7))
                if sound:
                    sound.play("boss_shot", 400)

            if hp_ratio <= 0.66:
                self.spiral_cd -= dt
                if self.spiral_cd <= 0:
                    self.spiral_cd = 0.11
                    self.spiral_angle += 0.5
                    spd = 260
                    enemy_bullets.append(EnemyBullet(self.x, self.y, math.cos(self.spiral_angle) * spd,
                                                      math.sin(self.spiral_angle) * spd, self.damage * 0.45, color=NEON_YELLOW))

            if hp_ratio <= 0.33:
                self.dash_cd -= dt
                if self.dash_cd <= 0 and dist < 500:
                    self.dash_telegraph = 0.5

            self.mine_cd -= dt
            if self.mine_cd <= 0:
                self.mine_cd = random.uniform(2.2, 3.0)
                for _ in range(2):
                    ang = random.uniform(0, math.tau)
                    r = random.uniform(40, 160)
                    mx = clamp(self.x + math.cos(ang) * r, 30, WIDTH - 30)
                    my = clamp(self.y + math.sin(ang) * r, 30, HEIGHT - 30)
                    self.mines.append({"x": mx, "y": my, "radius": 55, "state": "arm", "timer": 1.0})
                if sound:
                    sound.play("missile", 150)

        if self.hit_flash > 0:
            self.hit_flash -= dt
        if self.orbit_hit_cd > 0:
            self.orbit_hit_cd -= dt

        self.x = clamp(self.x, self.radius, WIDTH - self.radius)
        self.y = clamp(self.y, self.radius, HEIGHT - self.radius)

    def draw(self, surface):
        col = WHITE if self.hit_flash > 0 else self.color
        if self.dash_telegraph > 0:
            flash = int(self.dash_telegraph * 20) % 2 == 0
            col = NEON_RED if flash else self.color

        n = 8
        pts_outer = []
        pts_inner = []
        for i in range(n):
            ang = self.spin + i * math.tau / n
            pts_outer.append((self.x + math.cos(ang) * self.radius, self.y + math.sin(ang) * self.radius))
            ang2 = ang + math.tau / (n * 2)
            pts_inner.append((self.x + math.cos(ang2) * self.radius * 0.6, self.y + math.sin(ang2) * self.radius * 0.6))
        star = []
        for a, b in zip(pts_outer, pts_inner):
            star.append(a)
            star.append(b)

        glow = pygame.Surface((self.radius * 5, self.radius * 5), pygame.SRCALPHA)
        gc = (self.radius * 2.5, self.radius * 2.5)
        pygame.draw.circle(glow, (*col, 50), gc, int(self.radius * 2.4))
        surface.blit(glow, (self.x - gc[0], self.y - gc[1]), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.polygon(surface, col, star)
        pygame.draw.polygon(surface, WHITE, star, width=2)

        for m in self.mines:
            if m["state"] == "arm":
                t = 1 - clamp(m["timer"] / 1.0, 0, 1)
                r = 10 + m["radius"] * t
                s = pygame.Surface((int(r * 2 + 8), int(r * 2 + 8)), pygame.SRCALPHA)
                pygame.draw.circle(s, (*NEON_RED, 170), (int(r + 4), int(r + 4)), int(r), width=3)
                surface.blit(s, (m["x"] - r - 4, m["y"] - r - 4), special_flags=pygame.BLEND_RGBA_ADD)
            else:
                draw_glow_circle(surface, WHITE, (m["x"], m["y"]), m["radius"] * 0.6, intensity=3)

        w = 220
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        bx, by = WIDTH / 2 - w / 2, 20
        pygame.draw.rect(surface, (30, 30, 40), (bx, by, w, 10))
        pygame.draw.rect(surface, NEON_ORANGE, (bx, by, w * ratio, 10))
        pygame.draw.rect(surface, WHITE, (bx, by, w, 10), width=1)


class BossWarden(Enemy):
    """Boss type 2: a hexagon that plays more like a turret.
    - Fires aimed 3-shot bursts at you.
    - Calls in small enemies to help it.
    - Every so often, sweeps a rotating laser beam across the room that you must dodge.
    - Drops void zones on the ground that hurt you if you stand in them.
    """

    def __init__(self, x, y, wave):
        self.kind = "boss"
        self.name = "WARDEN"
        self.x, self.y = x, y
        self.max_hp = 700 + wave * 105
        self.hp = self.max_hp
        self.speed = 50
        self.radius = 40
        self.color = NEON_PURPLE
        self.damage = 28
        self.xp = 900
        self.score = 400
        self.alive = True
        self.hit_flash = 0
        self.spin = 0
        self.orbit_hit_cd = 0.0
        self.shielded = False

        self.burst_cd = 1.8
        self.burst_shots_left = 0
        self.burst_timer = 0.0

        self.summon_cd = random.uniform(5.5, 7.0)
        self.wants_summon = False

        self.sweep_cd = random.uniform(6.5, 8.0)
        self.sweep_active = False
        self.sweep_timer = 0.0
        self.sweep_angle = 0.0
        self.sweep_dir = 1
        self.sweep_width = 26

        self.hazard_cd = random.uniform(5.0, 6.5)
        self.hazards = []

    def update(self, dt, player, enemy_bullets, sound=None):
        self.spin += dt * 1.0
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy) or 1

        if self.sweep_active:
            self.sweep_timer -= dt
            self.sweep_angle += self.sweep_dir * dt * 1.7
            if self.sweep_timer <= 0:
                self.sweep_active = False
                self.sweep_cd = random.uniform(7.0, 9.0)
        else:
            desired = 260
            if dist < desired - 15:
                self.x -= dx / dist * self.speed * dt
                self.y -= dy / dist * self.speed * dt
            elif dist > desired + 15:
                self.x += dx / dist * self.speed * dt
                self.y += dy / dist * self.speed * dt

            if self.burst_shots_left > 0:
                self.burst_timer -= dt
                if self.burst_timer <= 0:
                    spd = 300
                    enemy_bullets.append(EnemyBullet(self.x, self.y, dx / dist * spd, dy / dist * spd, self.damage, color=NEON_PURPLE))
                    self.burst_shots_left -= 1
                    self.burst_timer = 0.15
                    if sound:
                        sound.play("boss_shot", 80)
            else:
                self.burst_cd -= dt
                if self.burst_cd <= 0 and dist < 560:
                    self.burst_cd = random.uniform(1.5, 2.1)
                    self.burst_shots_left = 3
                    self.burst_timer = 0.0

            self.summon_cd -= dt
            if self.summon_cd <= 0:
                self.summon_cd = random.uniform(6.0, 8.0)
                self.wants_summon = True

            self.sweep_cd -= dt
            if self.sweep_cd <= 0 and dist < 700:
                self.sweep_active = True
                self.sweep_timer = 2.4
                self.sweep_angle = math.atan2(dy, dx)
                self.sweep_dir = random.choice([-1, 1])
                if sound:
                    sound.play("laser", 400)

            self.hazard_cd -= dt
            if self.hazard_cd <= 0:
                self.hazard_cd = random.uniform(6.0, 7.5)
                for _ in range(2):
                    ang = random.uniform(0, math.tau)
                    r = random.uniform(60, 220)
                    hx = clamp(player.x + math.cos(ang) * r, 30, WIDTH - 30)
                    hy = clamp(player.y + math.sin(ang) * r, 30, HEIGHT - 30)
                    self.hazards.append({"x": hx, "y": hy, "radius": 65, "state": "telegraph",
                                          "timer": 1.2, "live_time": 2.5, "damage": self.damage * 0.8})
                if sound:
                    sound.play("nova", 200)

        if self.hit_flash > 0:
            self.hit_flash -= dt
        if self.orbit_hit_cd > 0:
            self.orbit_hit_cd -= dt

        self.x = clamp(self.x, self.radius, WIDTH - self.radius)
        self.y = clamp(self.y, self.radius, HEIGHT - self.radius)

    def draw(self, surface):
        col = WHITE if self.hit_flash > 0 else self.color
        n = 6
        pts = []
        for i in range(n):
            ang = self.spin + i * math.tau / n
            pts.append((self.x + math.cos(ang) * self.radius, self.y + math.sin(ang) * self.radius))

        glow = pygame.Surface((self.radius * 5, self.radius * 5), pygame.SRCALPHA)
        gc = (self.radius * 2.5, self.radius * 2.5)
        pygame.draw.circle(glow, (*col, 50), gc, int(self.radius * 2.4))
        surface.blit(glow, (self.x - gc[0], self.y - gc[1]), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.polygon(surface, col, pts)
        pygame.draw.polygon(surface, WHITE, pts, width=2)

        if self.sweep_active:
            ex = self.x + math.cos(self.sweep_angle) * 800
            ey = self.y + math.sin(self.sweep_angle) * 800
            draw_glow_line(surface, NEON_PURPLE, (self.x, self.y), (ex, ey), width=self.sweep_width, intensity=3)

        for hz in self.hazards:
            if hz["state"] == "telegraph":
                t = 1 - clamp(hz["timer"] / 1.2, 0, 1)
                r = hz["radius"] * t
                s = pygame.Surface((int(hz["radius"] * 2 + 8), int(hz["radius"] * 2 + 8)), pygame.SRCALPHA)
                c = (hz["radius"] + 4, hz["radius"] + 4)
                pygame.draw.circle(s, (*NEON_PURPLE, 150), c, int(r), width=3)
                surface.blit(s, (hz["x"] - hz["radius"] - 4, hz["y"] - hz["radius"] - 4), special_flags=pygame.BLEND_RGBA_ADD)
            else:
                s = pygame.Surface((int(hz["radius"] * 2 + 8), int(hz["radius"] * 2 + 8)), pygame.SRCALPHA)
                c = (hz["radius"] + 4, hz["radius"] + 4)
                pygame.draw.circle(s, (*NEON_PURPLE, 90), c, int(hz["radius"]))
                pygame.draw.circle(s, (*NEON_PURPLE, 200), c, int(hz["radius"]), width=3)
                surface.blit(s, (hz["x"] - hz["radius"] - 4, hz["y"] - hz["radius"] - 4), special_flags=pygame.BLEND_RGBA_ADD)

        w = 220
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        bx, by = WIDTH / 2 - w / 2, 20
        pygame.draw.rect(surface, (30, 30, 40), (bx, by, w, 10))
        pygame.draw.rect(surface, NEON_PURPLE, (bx, by, w * ratio, 10))
        pygame.draw.rect(surface, WHITE, (bx, by, w, 10), width=1)


class BossReaper(Enemy):
    """Boss type 3: a fast, aggressive glass-cannon boss.
    - Teleports next to you and fires a burst of bullets.
    - Throws spinning blades in a spread toward you.
    - Below half health, chains 3 fast dashes at you in a row.
    """

    def __init__(self, x, y, wave):
        self.kind = "boss"
        self.name = "REAPER"
        self.x, self.y = x, y
        self.max_hp = 620 + wave * 95
        self.hp = self.max_hp
        self.speed = 66
        self.radius = 38
        self.color = NEON_PINK
        self.damage = 34
        self.base_damage = self.damage
        self.xp = 950
        self.score = 420
        self.alive = True
        self.hit_flash = 0
        self.spin = 0
        self.orbit_hit_cd = 0.0
        self.shielded = False

        self.teleport_cd = random.uniform(3.5, 4.5)
        self.teleport_flash = 0.0

        self.blade_cd = random.uniform(2.0, 2.6)

        self.dash_chain = 0
        self.dash_pause = 0.0
        self.dashing = False
        self.dash_timer = 0.0
        self.dash_vx = 0.0
        self.dash_vy = 0.0
        self.dash_cd = random.uniform(4.0, 5.0)

    def update(self, dt, player, enemy_bullets, sound=None):
        self.spin += dt * 1.4
        hp_ratio = self.hp / self.max_hp
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy) or 1

        if self.dashing:
            self.dash_timer -= dt
            self.x += self.dash_vx * dt
            self.y += self.dash_vy * dt
            if self.dash_timer <= 0:
                self.dashing = False
                self.damage = self.base_damage
                if self.dash_chain > 0:
                    self.dash_pause = 0.25
                else:
                    self.dash_cd = random.uniform(4.0, 5.5)
        elif self.dash_pause > 0:
            self.dash_pause -= dt
            if self.dash_pause <= 0 and self.dash_chain > 0:
                self.dash_chain -= 1
                self.dashing = True
                self.dash_timer = 0.3
                self.damage = self.base_damage * 1.4
                ddx, ddy = player.x - self.x, player.y - self.y
                dd = math.hypot(ddx, ddy) or 1
                self.dash_vx = ddx / dd * 620
                self.dash_vy = ddy / dd * 620
        else:
            desired = 200
            if dist < desired - 15:
                self.x -= dx / dist * self.speed * dt
                self.y -= dy / dist * self.speed * dt
            elif dist > desired + 15:
                self.x += dx / dist * self.speed * dt
                self.y += dy / dist * self.speed * dt

            self.teleport_cd -= dt
            if self.teleport_cd <= 0:
                self.teleport_cd = random.uniform(4.5, 6.0)
                ang = random.uniform(0, math.tau)
                r = random.uniform(130, 220)
                nx = clamp(player.x + math.cos(ang) * r, self.radius, WIDTH - self.radius)
                ny = clamp(player.y + math.sin(ang) * r, self.radius, HEIGHT - self.radius)
                self.x, self.y = nx, ny
                self.teleport_flash = 0.3
                n = 8
                for i in range(n):
                    a = i * math.tau / n
                    spd = 210
                    enemy_bullets.append(EnemyBullet(self.x, self.y, math.cos(a) * spd, math.sin(a) * spd, self.damage * 0.55))
                if sound:
                    sound.play("boss_shot", 200)

            self.blade_cd -= dt
            if self.blade_cd <= 0 and dist < 600:
                self.blade_cd = random.uniform(2.2, 2.8)
                base_ang = math.atan2(dy, dx)
                for off in (-0.28, 0.0, 0.28):
                    a = base_ang + off
                    spd = 210
                    enemy_bullets.append(EnemyBullet(self.x, self.y, math.cos(a) * spd, math.sin(a) * spd,
                                                      self.damage * 0.75, color=NEON_PINK, radius=9))
                if sound:
                    sound.play("missile", 150)

            if hp_ratio <= 0.5:
                self.dash_cd -= dt
                if self.dash_cd <= 0 and dist < 520:
                    self.dash_chain = 3
                    self.dash_pause = 0.05

        if self.teleport_flash > 0:
            self.teleport_flash -= dt
        if self.hit_flash > 0:
            self.hit_flash -= dt
        if self.orbit_hit_cd > 0:
            self.orbit_hit_cd -= dt

        self.x = clamp(self.x, self.radius, WIDTH - self.radius)
        self.y = clamp(self.y, self.radius, HEIGHT - self.radius)

    def draw(self, surface):
        col = WHITE if self.hit_flash > 0 else self.color
        if self.teleport_flash > 0:
            col = NEON_CYAN

        n = 5
        pts = []
        for i in range(n):
            ang = self.spin + i * math.tau / n
            pts.append((self.x + math.cos(ang) * self.radius, self.y + math.sin(ang) * self.radius))

        glow = pygame.Surface((self.radius * 5, self.radius * 5), pygame.SRCALPHA)
        gc = (self.radius * 2.5, self.radius * 2.5)
        pygame.draw.circle(glow, (*col, 50), gc, int(self.radius * 2.4))
        surface.blit(glow, (self.x - gc[0], self.y - gc[1]), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.polygon(surface, col, pts)
        pygame.draw.polygon(surface, WHITE, pts, width=2)

        w = 220
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        bx, by = WIDTH / 2 - w / 2, 20
        pygame.draw.rect(surface, (30, 30, 40), (bx, by, w, 10))
        pygame.draw.rect(surface, NEON_PINK, (bx, by, w * ratio, 10))
        pygame.draw.rect(surface, WHITE, (bx, by, w, 10), width=1)


class BossHive(Enemy):
    """Boss type 4: a slow, tanky boss that overwhelms you with numbers.
    - Calls in groups of small enemies often.
    - Releases a wide ring of slow drifting spore bullets.
    - Slowly heals itself over time, so you need to keep the pressure on.
    """

    def __init__(self, x, y, wave):
        self.kind = "boss"
        self.name = "HIVE"
        self.x, self.y = x, y
        self.max_hp = 900 + wave * 130
        self.hp = self.max_hp
        self.speed = 40
        self.radius = 46
        self.color = NEON_TEAL
        self.damage = 22
        self.xp = 1000
        self.score = 440
        self.alive = True
        self.hit_flash = 0
        self.spin = 0
        self.orbit_hit_cd = 0.0
        self.shielded = False

        self.summon_cd = random.uniform(4.5, 5.5)
        self.wants_summon = False
        self.summon_count = 3
        self.summon_kinds = ["swarm", "grunt"]

        self.spore_cd = random.uniform(3.0, 4.0)

        self.regen_cd = random.uniform(5.0, 6.0)
        self.wants_heal_fx = False

    def update(self, dt, player, enemy_bullets, sound=None):
        self.spin += dt * 0.6
        dx, dy = player.x - self.x, player.y - self.y
        dist = math.hypot(dx, dy) or 1
        desired = 280
        if dist < desired - 15:
            self.x -= dx / dist * self.speed * dt
            self.y -= dy / dist * self.speed * dt
        elif dist > desired + 15:
            self.x += dx / dist * self.speed * dt
            self.y += dy / dist * self.speed * dt

        self.summon_cd -= dt
        if self.summon_cd <= 0:
            self.summon_cd = random.uniform(5.0, 6.5)
            self.wants_summon = True

        self.spore_cd -= dt
        if self.spore_cd <= 0:
            self.spore_cd = random.uniform(3.8, 4.6)
            n = 12
            for i in range(n):
                a = self.spin + i * math.tau / n
                spd = 115
                enemy_bullets.append(EnemyBullet(self.x, self.y, math.cos(a) * spd, math.sin(a) * spd,
                                                  self.damage * 0.6, color=NEON_GREEN, radius=8))
            if sound:
                sound.play("nova", 300)

        self.regen_cd -= dt
        if self.regen_cd <= 0:
            self.regen_cd = random.uniform(5.0, 6.5)
            if self.hp < self.max_hp:
                self.hp = min(self.max_hp, self.hp + self.max_hp * 0.04)
                self.wants_heal_fx = True

        if self.hit_flash > 0:
            self.hit_flash -= dt
        if self.orbit_hit_cd > 0:
            self.orbit_hit_cd -= dt

        self.x = clamp(self.x, self.radius, WIDTH - self.radius)
        self.y = clamp(self.y, self.radius, HEIGHT - self.radius)

    def draw(self, surface):
        col = WHITE if self.hit_flash > 0 else self.color
        n = 7
        pts = []
        for i in range(n):
            ang = self.spin + i * math.tau / n
            pts.append((self.x + math.cos(ang) * self.radius, self.y + math.sin(ang) * self.radius))

        glow = pygame.Surface((self.radius * 5, self.radius * 5), pygame.SRCALPHA)
        gc = (self.radius * 2.5, self.radius * 2.5)
        pygame.draw.circle(glow, (*col, 50), gc, int(self.radius * 2.4))
        surface.blit(glow, (self.x - gc[0], self.y - gc[1]), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.polygon(surface, col, pts)
        pygame.draw.polygon(surface, WHITE, pts, width=2)

        w = 220
        ratio = clamp(self.hp / self.max_hp, 0, 1)
        bx, by = WIDTH / 2 - w / 2, 20
        pygame.draw.rect(surface, (30, 30, 40), (bx, by, w, 10))
        pygame.draw.rect(surface, NEON_TEAL, (bx, by, w * ratio, 10))
        pygame.draw.rect(surface, WHITE, (bx, by, w, 10), width=1)


BOSS_CLASSES = [BossPulsar, BossWarden, BossReaper, BossHive]


# ----------------------------------------------------------------------
# PLAYER
# ----------------------------------------------------------------------
class Player:
    def __init__(self):
        self.x, self.y = WIDTH / 2, HEIGHT / 2
        self.radius = 14
        self.speed = 250
        self.max_hp = 100
        self.hp = self.max_hp
        self.level = 1
        self.xp = 0
        self.xp_to_next = 6
        self.fire_cd = 0
        self.fire_rate = 0.35
        self.damage = 10
        self.bullet_speed = 520
        self.projectiles_count = 1
        self.spread = 8
        self.pierce = 0
        self.pickup_radius = 90
        self.invuln = 0
        self.spin = 0
        self.crit_chance = 0.05
        self.regen = 0

        # weapon system
        self.weapon_levels = {"orbit": 0, "missile": 0, "laser": 0, "nova": 0}
        self.weapon_cd = {"orbit": 0.0, "missile": 0.0, "laser": 0.0, "nova": 0.0}
        self.orbit_angle = 0.0
        self.laser_active = False
        self.laser_timer = 0.0
        self.laser_angle = 0.0

    def gain_xp(self, amount):
        self.xp += amount

    def try_level_up(self):
        leveled = False
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * 1.35 + 2)
            leveled = True
        return leveled

    def update(self, dt, keys):
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if dx or dy:
            mag = math.hypot(dx, dy)
            self.x += dx / mag * self.speed * dt
            self.y += dy / mag * self.speed * dt
        self.x = clamp(self.x, self.radius, WIDTH - self.radius)
        self.y = clamp(self.y, self.radius, HEIGHT - self.radius)

        if self.fire_cd > 0:
            self.fire_cd -= dt
        if self.invuln > 0:
            self.invuln -= dt
        self.spin += dt * 6

        if self.regen > 0:
            self.hp = clamp(self.hp + self.regen * dt, 0, self.max_hp)

    def take_damage(self, amount):
        if self.invuln > 0:
            return False
        self.hp -= amount
        self.invuln = 0.9
        return True

    def draw(self, surface):
        flicker = self.invuln > 0 and int(self.invuln * 20) % 2 == 0
        col = (255, 255, 255) if flicker else NEON_CYAN
        glow = pygame.Surface((80, 80), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*NEON_CYAN, 60), (40, 40), 34)
        surface.blit(glow, (self.x - 40, self.y - 40), special_flags=pygame.BLEND_RGBA_ADD)

        tri = [
            (self.x + math.cos(-math.pi / 2) * self.radius, self.y + math.sin(-math.pi / 2) * self.radius),
            (self.x + math.cos(-math.pi / 2 + 2.4) * self.radius, self.y + math.sin(-math.pi / 2 + 2.4) * self.radius),
            (self.x + math.cos(-math.pi / 2 - 2.4) * self.radius, self.y + math.sin(-math.pi / 2 - 2.4) * self.radius),
        ]
        pygame.draw.polygon(surface, col, tri)
        pygame.draw.polygon(surface, WHITE, tri, width=2)


# ----------------------------------------------------------------------
# UPGRADES
# ----------------------------------------------------------------------
STAT_UPGRADES = [
    ("Shoot Faster +18%", lambda p: setattr(p, "fire_rate", p.fire_rate * 0.82)),
    ("Hit Harder +25%", lambda p: setattr(p, "damage", p.damage * 1.25)),
    ("Move Faster +12%", lambda p: setattr(p, "speed", p.speed * 1.12)),
    ("More Health +20 & Full Heal", lambda p: (setattr(p, "max_hp", p.max_hp + 20), setattr(p, "hp", p.max_hp))),
    ("More Bullets +1", lambda p: setattr(p, "projectiles_count", p.projectiles_count + 1)),
    ("Bullets Go Through Enemies +1", lambda p: setattr(p, "pierce", p.pierce + 1)),
    ("Grab Items From Farther Away", lambda p: setattr(p, "pickup_radius", p.pickup_radius + 40)),
    ("Slowly Heal +1.5/sec", lambda p: setattr(p, "regen", p.regen + 1.5)),
    ("Big Hit Chance +10%", lambda p: setattr(p, "crit_chance", p.crit_chance + 0.10)),
]

WEAPON_INFO = {
    "orbit": {"name": "Spinning Blades", "max_level": 10},
    "missile": {"name": "Chasing Rocket", "max_level": 10},
    "laser": {"name": "Laser", "max_level": 10},
    "nova": {"name": "Shock Wave", "max_level": 10},
}

DEV_HOTKEYS = [
    (pygame.K_1, "XP Multiplier +1"),
    (pygame.K_2, "XP Multiplier -1"),
    (pygame.K_q, "Damage +50%"),
    (pygame.K_w, "Shoot Faster +50%"),
    (pygame.K_e, "Move Faster +50%"),
    (pygame.K_r, "Max HP +200 and Full Heal"),
    (pygame.K_a, "Level Up: Spinning Blades"),
    (pygame.K_s, "Level Up: Chasing Rocket"),
    (pygame.K_d, "Level Up: Laser"),
    (pygame.K_f, "Level Up: Shock Wave"),
    (pygame.K_g, "Full Heal"),
    (pygame.K_z, "GIVE ME EVERYTHING (max stats and weapons)"),
]


def make_unlock_fn(wid):
    def fn(p):
        p.weapon_levels[wid] = 1
        p.weapon_cd[wid] = 0.0
    return fn


def make_weapon_levelup_fn(wid):
    def fn(p):
        p.weapon_levels[wid] = p.weapon_levels.get(wid, 0) + 1
    return fn


def build_upgrade_pool(player):
    pool = list(STAT_UPGRADES)
    for wid, info in WEAPON_INFO.items():
        lvl = player.weapon_levels.get(wid, 0)
        if lvl == 0:
            pool.append((f"[NEW WEAPON] Get {info['name']}", make_unlock_fn(wid)))
        elif lvl < info["max_level"]:
            pool.append((f"Level Up {info['name']} (Lv.{lvl} -> {lvl + 1})", make_weapon_levelup_fn(wid)))
    return pool


# ----------------------------------------------------------------------
# GAME
# ----------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("NEON PULSE")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("arial", 56, bold=True)
        self.font_mid = pygame.font.SysFont("arial", 30, bold=True)
        self.font_small = pygame.font.SysFont("arial", 20)
        self.sound = SoundManager()
        self.xp_multiplier = 1.0
        self.dev_code_buffer = ""
        self.reset()

    def reset(self):
        self.player = Player()
        self.enemies = []
        self.bullets = []
        self.enemy_bullets = []
        self.missiles = []
        self.orbs = []
        self.nova_rings = []
        self.orbit_positions = []
        self.particles = ParticleSystem()
        self.wave = 0
        self.wave_timer = 2.0
        self.wave_active = False
        self.enemies_to_spawn = 0
        self.spawn_cd = 0
        self.score = 0
        self.game_time = 0
        self.state = "playing"  # playing, levelup, paused, devmenu, gameover
        self.level_choices = []
        self.shake = 0
        self.banner_text = ""
        self.banner_timer = 0
        self.combo = 0
        self.combo_timer = 0

    # ---------------- WAVE MANAGEMENT ----------------
    def start_wave(self):
        self.wave += 1
        is_boss_wave = self.wave % 5 == 0
        self.wave_active = True

        if is_boss_wave:
            boss_number = self.wave // 5
            boss_cls = BOSS_CLASSES[(boss_number - 1) % len(BOSS_CLASSES)]
            boss = boss_cls(WIDTH / 2, -60, self.wave)
            self.enemies.append(boss)
            self.enemies_to_spawn = 0
            self.banner_text = f"WAVE {self.wave}  \u26a0 BOSS: {boss.name}"
            self.sound.play("boss", 1000)
        else:
            base = 6 + self.wave * 2
            self.enemies_to_spawn = base
            self.banner_text = f"WAVE {self.wave}"
            self.sound.play("wave", 500)
        self.banner_timer = 2.2
        self.spawn_cd = 0

    def spawn_enemy(self):
        edge = random.choice(["top", "bottom", "left", "right"])
        x, y = self._edge_point(edge)
        kind = self._weighted_kind()
        wave_mult = 1 + (self.wave - 1) * 0.16
        self.enemies.append(Enemy(kind, x, y, wave_mult))

    def _weighted_kind(self):
        candidates = [("grunt", 1.0)]
        if self.wave >= 2:
            candidates.append(("brute", 0.55))
        if self.wave >= 3:
            candidates.append(("shooter", 0.5))
        if self.wave >= 4:
            candidates.append(("splitter", 0.4))
        if self.wave >= 5:
            candidates.append(("bomber", 0.42))
        if self.wave >= 6:
            candidates.append(("sniper", 0.32))
        if self.wave >= 8:
            candidates.append(("shielder", 0.3))
        kinds = [c[0] for c in candidates]
        weights = [c[1] for c in candidates]
        return random.choices(kinds, weights=weights, k=1)[0]

    def spawn_swarm_cluster(self):
        edge = random.choice(["top", "bottom", "left", "right"])
        bx, by = self._edge_point(edge)
        n = random.randint(3, 5)
        wave_mult = 1 + (self.wave - 1) * 0.16
        for _ in range(n):
            jx = bx + random.uniform(-30, 30)
            jy = by + random.uniform(-30, 30)
            self.enemies.append(Enemy("swarm", jx, jy, wave_mult))
        return n

    def _edge_point(self, edge):
        if edge == "top":
            return random.uniform(0, WIDTH), -30
        if edge == "bottom":
            return random.uniform(0, WIDTH), HEIGHT + 30
        if edge == "left":
            return -30, random.uniform(0, HEIGHT)
        return WIDTH + 30, random.uniform(0, HEIGHT)

    def handle_boss_specials(self, dt):
        """Handles boss abilities that need access to the full game state
        (spawning minions, damaging the player with a sweeping laser, mines,
        ground hazards, heal effects). Written generically with getattr so
        any boss type can opt into any of these by having the attribute."""
        for e in self.enemies:
            if not e.alive or getattr(e, "kind", None) != "boss":
                continue

            if getattr(e, "wants_summon", False):
                e.wants_summon = False
                count = getattr(e, "summon_count", 2)
                kinds = getattr(e, "summon_kinds", ["grunt", "swarm"])
                wave_mult = 1 + (self.wave - 1) * 0.16
                for _ in range(count):
                    ang = random.uniform(0, math.tau)
                    sx = e.x + math.cos(ang) * 60
                    sy = e.y + math.sin(ang) * 60
                    kind = random.choice(kinds)
                    self.enemies.append(Enemy(kind, sx, sy, wave_mult))
                self.sound.play("boss_shot", 200)

            if getattr(e, "wants_heal_fx", False):
                e.wants_heal_fx = False
                self.particles.burst(e.x, e.y, NEON_GREEN, count=22, speed_range=(1, 4), life=0.6)
                self.sound.play("pickup", 150)

            if getattr(e, "sweep_active", False):
                ex = e.x + math.cos(e.sweep_angle) * 800
                ey = e.y + math.sin(e.sweep_angle) * 800
                d = point_segment_distance(self.player.x, self.player.y, e.x, e.y, ex, ey)
                if d < e.sweep_width / 2 + self.player.radius:
                    if self.player.take_damage(e.damage * 0.6):
                        self.add_shake(6)
                        self.particles.burst(self.player.x, self.player.y, NEON_PURPLE, count=8, life=0.3)
                        self.sound.play("hurt", 150)

            mines = getattr(e, "mines", None)
            if mines:
                for m in list(mines):
                    m["timer"] -= dt
                    if m["state"] == "arm" and m["timer"] <= 0:
                        m["state"] = "explode"
                        m["timer"] = 0.15
                        d = math.hypot(self.player.x - m["x"], self.player.y - m["y"])
                        if d < m["radius"] + self.player.radius:
                            if self.player.take_damage(e.damage * 0.9):
                                self.add_shake(8)
                        self.particles.burst(m["x"], m["y"], NEON_RED, count=20, speed_range=(2, 7), life=0.4)
                        self.sound.play("explode", 30)
                    elif m["state"] == "explode" and m["timer"] <= 0:
                        mines.remove(m)

            hazards = getattr(e, "hazards", None)
            if hazards:
                for hz in list(hazards):
                    hz["timer"] -= dt
                    if hz["state"] == "telegraph" and hz["timer"] <= 0:
                        hz["state"] = "live"
                        hz["timer"] = hz["live_time"]
                    elif hz["state"] == "live":
                        d = math.hypot(self.player.x - hz["x"], self.player.y - hz["y"])
                        if d < hz["radius"] + self.player.radius:
                            if self.player.take_damage(hz["damage"]):
                                self.add_shake(4)
                        if hz["timer"] <= 0:
                            hazards.remove(hz)

    # ---------------- COMBAT: BLASTER ----------------
    def player_fire(self):
        if not self.enemies:
            return
        nearest = min(self.enemies, key=lambda e: (e.x - self.player.x) ** 2 + (e.y - self.player.y) ** 2)
        base_ang = math.atan2(nearest.y - self.player.y, nearest.x - self.player.x)
        n = self.player.projectiles_count
        spread_rad = math.radians(self.player.spread)
        for i in range(n):
            offset = (i - (n - 1) / 2) * spread_rad
            ang = base_ang + offset
            vx = math.cos(ang) * self.player.bullet_speed
            vy = math.sin(ang) * self.player.bullet_speed
            dmg = self.player.damage
            crit = random.random() < self.player.crit_chance
            if crit:
                dmg *= 2
            color = NEON_YELLOW if crit else NEON_CYAN
            self.bullets.append(Bullet(self.player.x, self.player.y, vx, vy, dmg, color, 5, self.player.pierce))
        self.sound.play("shoot", 55)

    # ---------------- COMBAT: SECONDARY WEAPONS ----------------
    def update_orbit_weapon(self, dt):
        p = self.player
        lvl = p.weapon_levels["orbit"]
        if lvl <= 0:
            self.orbit_positions = []
            return
        p.orbit_angle += dt * 3.2
        blade_count = 1 + lvl
        radius_orbit = 70
        dmg = p.damage * (0.35 + 0.12 * lvl)
        positions = []
        for i in range(blade_count):
            ang = p.orbit_angle + i * (math.tau / blade_count)
            bx = p.x + math.cos(ang) * radius_orbit
            by = p.y + math.sin(ang) * radius_orbit
            positions.append((bx, by))
            for e in self.enemies:
                if not e.alive or e.orbit_hit_cd > 0:
                    continue
                if math.hypot(bx - e.x, by - e.y) < e.radius + 10:
                    killed = e.take_damage(dmg)
                    e.orbit_hit_cd = 0.22
                    self.particles.burst(bx, by, NEON_CYAN, count=4, speed_range=(1, 2), life=0.2, size=2)
                    self.sound.play("orbit_hit", 55)
                    if killed:
                        self.on_enemy_killed(e)
        self.orbit_positions = positions
        self.enemies = [e for e in self.enemies if e.alive]

    def update_missile_weapon(self, dt):
        p = self.player
        lvl = p.weapon_levels["missile"]
        if lvl <= 0:
            return
        p.weapon_cd["missile"] -= dt
        if p.weapon_cd["missile"] <= 0 and self.enemies:
            p.weapon_cd["missile"] = max(0.4, 1.7 - lvl * 0.15)
            count = 1 + (lvl - 1) // 2
            targets = sorted(self.enemies, key=lambda e: (e.x - p.x) ** 2 + (e.y - p.y) ** 2)[:count]
            for tgt in targets:
                self.missiles.append(Missile(p.x, p.y, tgt, 340, p.damage * 1.3, 46 + lvl * 8))
            self.sound.play("missile", 90)

        for m in self.missiles:
            m.update(dt, self.enemies)
        for m in self.missiles:
            if not m.alive:
                continue
            for e in self.enemies:
                if not e.alive:
                    continue
                if math.hypot(m.x - e.x, m.y - e.y) < e.radius + 8:
                    self.explode_missile(m)
                    m.alive = False
                    break
        self.missiles = [m for m in self.missiles if m.alive]

    def explode_missile(self, m):
        self.particles.burst(m.x, m.y, NEON_ORANGE, count=26, speed_range=(2, 8), life=0.5, size=4)
        self.add_shake(6)
        self.sound.play("explode", 40)
        for e in self.enemies:
            if not e.alive:
                continue
            if math.hypot(m.x - e.x, m.y - e.y) < m.aoe_radius + e.radius:
                killed = e.take_damage(m.damage)
                if killed:
                    self.on_enemy_killed(e)
        self.enemies = [e for e in self.enemies if e.alive]

    def update_laser_weapon(self, dt):
        p = self.player
        lvl = p.weapon_levels["laser"]
        if lvl <= 0:
            return
        if p.laser_active:
            p.laser_timer -= dt
            dps = p.damage * (1.0 + 0.35 * lvl)
            width = 10 + lvl * 2
            ex = p.x + math.cos(p.laser_angle) * 750
            ey = p.y + math.sin(p.laser_angle) * 750
            for e in self.enemies:
                if not e.alive:
                    continue
                d = point_segment_distance(e.x, e.y, p.x, p.y, ex, ey)
                if d < width / 2 + e.radius:
                    killed = e.take_damage(dps * dt)
                    if killed:
                        self.on_enemy_killed(e)
            self.enemies = [e for e in self.enemies if e.alive]
            if p.laser_timer <= 0:
                p.laser_active = False
                p.weapon_cd["laser"] = max(1.0, 2.6 - lvl * 0.15)
        else:
            p.weapon_cd["laser"] -= dt
            if p.weapon_cd["laser"] <= 0 and self.enemies:
                nearest = min(self.enemies, key=lambda e: (e.x - p.x) ** 2 + (e.y - p.y) ** 2)
                p.laser_angle = math.atan2(nearest.y - p.y, nearest.x - p.x)
                p.laser_active = True
                p.laser_timer = 0.4
                self.sound.play("laser", 350)

    def update_nova_weapon(self, dt):
        p = self.player
        lvl = p.weapon_levels["nova"]
        if lvl <= 0:
            return
        p.weapon_cd["nova"] -= dt
        if p.weapon_cd["nova"] <= 0:
            radius = 90 + lvl * 22
            dmg = p.damage * (0.9 + 0.3 * lvl)
            p.weapon_cd["nova"] = max(1.3, 3.2 - lvl * 0.22)
            self.nova_rings.append({"x": p.x, "y": p.y, "t": 0.0, "life": 0.5, "max_r": radius})
            self.add_shake(6)
            self.sound.play("nova", 250)
            for e in self.enemies:
                if not e.alive:
                    continue
                if math.hypot(p.x - e.x, p.y - e.y) < radius + e.radius:
                    killed = e.take_damage(dmg)
                    self.particles.burst(e.x, e.y, NEON_PURPLE, count=8, life=0.3)
                    if killed:
                        self.on_enemy_killed(e)
            self.enemies = [e for e in self.enemies if e.alive]

    def add_shake(self, amount):
        self.shake = min(18, self.shake + amount)

    # ---------------- UPDATE ----------------
    def update(self, dt):
        self.game_time += dt

        if self.shake > 0:
            self.shake = max(0, self.shake - dt * 40)
        if self.banner_timer > 0:
            self.banner_timer -= dt
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 0

        for r in self.nova_rings:
            r["t"] += dt
        self.nova_rings = [r for r in self.nova_rings if r["t"] < r["life"]]

        if self.state != "playing":
            return

        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)

        # wave logic
        if not self.wave_active and not self.enemies:
            self.wave_timer -= dt
            if self.wave_timer <= 0:
                self.start_wave()
        elif self.wave_active:
            self.spawn_cd -= dt
            if self.enemies_to_spawn > 0 and self.spawn_cd <= 0:
                if self.wave >= 2 and random.random() < 0.18:
                    n = self.spawn_swarm_cluster()
                    self.enemies_to_spawn -= n
                else:
                    self.spawn_enemy()
                    self.enemies_to_spawn -= 1
                self.spawn_cd = max(0.15, 0.7 - self.wave * 0.02)
            if self.enemies_to_spawn <= 0 and not self.enemies:
                self.wave_active = False
                self.wave_timer = 3.0

        # blaster firing
        if self.player.fire_cd <= 0 and self.enemies:
            self.player.fire_cd = self.player.fire_rate
            self.player_fire()

        # secondary weapons
        self.update_orbit_weapon(dt)
        self.update_missile_weapon(dt)
        self.update_laser_weapon(dt)
        self.update_nova_weapon(dt)

        # bullets
        for b in self.bullets:
            b.update(dt)
        self.bullets = [b for b in self.bullets if b.alive]

        for eb in self.enemy_bullets:
            eb.update(dt)
        self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive]

        # enemies
        for e in self.enemies:
            e.update(dt, self.player, self.enemy_bullets, self.sound)
        self.handle_boss_specials(dt)

        # bullet-enemy collisions
        for b in self.bullets:
            if not b.alive:
                continue
            for e in self.enemies:
                if not e.alive:
                    continue
                dist = math.hypot(b.x - e.x, b.y - e.y)
                if dist < e.radius + b.radius:
                    killed = e.take_damage(b.damage)
                    self.particles.burst(b.x, b.y, e.color, count=6, speed_range=(1, 3), life=0.3, size=2)
                    self.sound.play("hit", 40)
                    if b.pierce > 0:
                        b.pierce -= 1
                    else:
                        b.alive = False
                    if killed:
                        self.on_enemy_killed(e)
                    if not b.alive:
                        break

        self.enemies = [e for e in self.enemies if e.alive]
        self.bullets = [b for b in self.bullets if b.alive]

        # enemy bullets vs player
        for eb in self.enemy_bullets:
            dist = math.hypot(eb.x - self.player.x, eb.y - self.player.y)
            if dist < self.player.radius + eb.radius:
                if self.player.take_damage(eb.damage):
                    self.add_shake(8)
                    self.particles.burst(self.player.x, self.player.y, NEON_ORANGE, count=10, life=0.35)
                    self.sound.play("hurt", 150)
                eb.alive = False
        self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.alive]

        # enemy-player contact
        for e in self.enemies:
            dist = math.hypot(e.x - self.player.x, e.y - self.player.y)
            if dist < e.radius + self.player.radius:
                if self.player.take_damage(e.damage * dt * 3):
                    self.add_shake(4)

        # orbs
        for o in self.orbs:
            o.update(dt, self.player, self.sound)
        self.orbs = [o for o in self.orbs if o.alive]

        self.particles.update(dt)

        # level up check
        if self.player.try_level_up():
            self.enter_levelup()

        if self.player.hp <= 0:
            self.state = "gameover"
            self.sound.play("gameover", 2000)

    def on_enemy_killed(self, e):
        self.particles.burst(e.x, e.y, e.color, count=22, speed_range=(2, 7), life=0.5, size=4)
        self.add_shake(5 if e.kind != "boss" else 16)
        self.orbs.append(XPOrb(e.x, e.y, e.xp * self.xp_multiplier))
        self.score += e.score
        self.combo += 1
        self.combo_timer = 2.0
        self.sound.play("explode", 35)

        if e.kind == "splitter":
            wave_mult = 1 + (self.wave - 1) * 0.16
            for _ in range(2):
                ang = random.uniform(0, math.tau)
                mx = e.x + math.cos(ang) * 14
                my = e.y + math.sin(ang) * 14
                self.enemies.append(Enemy("splitter_mini", mx, my, wave_mult * 0.85))

        elif e.kind == "bomber":
            aoe_r = 78
            self.add_shake(10)
            self.particles.burst(e.x, e.y, (255, 140, 60), count=30, speed_range=(2, 9), life=0.5, size=4)
            if math.hypot(e.x - self.player.x, e.y - self.player.y) < aoe_r + self.player.radius:
                if self.player.take_damage(e.damage * 2.3):
                    self.sound.play("hurt", 150)
            for other in list(self.enemies):
                if other is e or not other.alive:
                    continue
                if math.hypot(e.x - other.x, e.y - other.y) < aoe_r + other.radius:
                    killed2 = other.take_damage(e.damage * 1.4)
                    if killed2:
                        self.on_enemy_killed(other)

    def enter_levelup(self):
        self.state = "levelup"
        pool = build_upgrade_pool(self.player)
        self.level_choices = random.sample(pool, min(3, len(pool)))
        self.sound.play("levelup", 100)

    def apply_upgrade(self, idx):
        if idx >= len(self.level_choices):
            return
        _, fn = self.level_choices[idx]
        fn(self.player)
        self.state = "playing"

    # ---------------- DEV MODE (secret code: adminhack12, type it while paused) ----------------
    def dev_handle_key(self, key):
        p = self.player
        if key == pygame.K_1:
            self.xp_multiplier = round(self.xp_multiplier + 1, 1)
        elif key == pygame.K_2:
            self.xp_multiplier = max(0.5, round(self.xp_multiplier - 1, 1))
        elif key == pygame.K_q:
            p.damage *= 1.5
        elif key == pygame.K_w:
            p.fire_rate = max(0.03, p.fire_rate * 0.5)
        elif key == pygame.K_e:
            p.speed *= 1.5
        elif key == pygame.K_r:
            p.max_hp += 200
            p.hp = p.max_hp
        elif key == pygame.K_a:
            self.dev_weapon_up("orbit")
        elif key == pygame.K_s:
            self.dev_weapon_up("missile")
        elif key == pygame.K_d:
            self.dev_weapon_up("laser")
        elif key == pygame.K_f:
            self.dev_weapon_up("nova")
        elif key == pygame.K_g:
            p.hp = p.max_hp
        elif key == pygame.K_z:
            self.dev_max_all()
        self.sound.play("pickup", 20)

    def dev_weapon_up(self, wid):
        lvl = self.player.weapon_levels.get(wid, 0)
        self.player.weapon_levels[wid] = min(10, lvl + 1)
        if self.player.weapon_levels[wid] == 1:
            self.player.weapon_cd[wid] = 0.0

    def dev_max_all(self):
        p = self.player
        p.damage *= 3
        p.fire_rate = max(0.03, p.fire_rate * 0.3)
        p.speed *= 1.6
        p.max_hp += 500
        p.hp = p.max_hp
        p.pierce += 3
        p.projectiles_count += 3
        p.crit_chance = min(1.0, p.crit_chance + 0.3)
        for wid in p.weapon_levels:
            p.weapon_levels[wid] = 10
            p.weapon_cd[wid] = 0.0
        self.xp_multiplier = max(self.xp_multiplier, 5)

    # ---------------- DRAW ----------------
    def draw_background(self, surface):
        surface.fill(BG_COLOR)
        spacing = 48
        offset = int(self.game_time * 12) % spacing
        for x in range(-spacing, WIDTH + spacing, spacing):
            pygame.draw.line(surface, GRID_COLOR, (x - offset, 0), (x - offset, HEIGHT))
        for y in range(-spacing, HEIGHT + spacing, spacing):
            pygame.draw.line(surface, GRID_COLOR, (0, y - offset), (WIDTH, y - offset))

        cx, cy = WIDTH / 2, HEIGHT / 2
        pygame.draw.circle(surface, (14, 14, 26), (int(cx), int(cy)), 300, width=1)
        pygame.draw.circle(surface, (14, 14, 26), (int(cx), int(cy)), 200, width=1)

    def draw_weapons(self, surface):
        p = self.player
        # orbit blades
        for bx, by in self.orbit_positions:
            pts = []
            for i in range(4):
                ang = i * math.tau / 4 + self.game_time * 6
                pts.append((bx + math.cos(ang) * 8, by + math.sin(ang) * 8))
            pygame.draw.polygon(surface, NEON_CYAN, pts)
            draw_glow_circle(surface, NEON_CYAN, (bx, by), 4, intensity=2)

        # missiles
        for m in self.missiles:
            m.draw(surface)

        # laser beam
        if p.laser_active:
            lvl = p.weapon_levels["laser"]
            width = 10 + lvl * 2
            ex = p.x + math.cos(p.laser_angle) * 750
            ey = p.y + math.sin(p.laser_angle) * 750
            pulse = 1 + 0.3 * math.sin(self.game_time * 40)
            draw_glow_line(surface, NEON_PURPLE, (p.x, p.y), (ex, ey), width=max(1, int(width * pulse)), intensity=3)

        # nova rings
        for r in self.nova_rings:
            t = clamp(r["t"] / r["life"], 0, 1)
            radius = r["max_r"] * t
            alpha = int(200 * (1 - t))
            ring_surf = pygame.Surface((int(radius * 2 + 10), int(radius * 2 + 10)), pygame.SRCALPHA)
            pygame.draw.circle(ring_surf, (*NEON_PURPLE, alpha), (int(radius + 5), int(radius + 5)), int(radius), width=4)
            surface.blit(ring_surf, (r["x"] - radius - 5, r["y"] - radius - 5), special_flags=pygame.BLEND_RGBA_ADD)

    def draw_hud(self, surface):
        boss = next((e for e in self.enemies if getattr(e, "kind", None) == "boss"), None)
        if boss is not None:
            boss_colors = {"PULSAR": NEON_ORANGE, "WARDEN": NEON_PURPLE, "REAPER": NEON_PINK, "HIVE": NEON_TEAL}
            name_col = boss_colors.get(boss.name, WHITE)
            name_txt = self.font_small.render(boss.name, True, name_col)
            surface.blit(name_txt, (WIDTH / 2 - name_txt.get_width() / 2, 33))

        w = 260
        ratio = clamp(self.player.hp / self.player.max_hp, 0, 1)
        pygame.draw.rect(surface, (30, 30, 40), (20, 20, w, 18))
        hp_color = NEON_GREEN if ratio > 0.5 else (NEON_YELLOW if ratio > 0.25 else NEON_PINK)
        pygame.draw.rect(surface, hp_color, (20, 20, w * ratio, 18))
        pygame.draw.rect(surface, WHITE, (20, 20, w, 18), width=1)
        hp_txt = self.font_small.render(f"HP {int(max(0,self.player.hp))}/{int(self.player.max_hp)}", True, WHITE)
        surface.blit(hp_txt, (26, 22))

        ratio_xp = clamp(self.player.xp / self.player.xp_to_next, 0, 1)
        pygame.draw.rect(surface, (30, 30, 40), (20, 46, w, 10))
        pygame.draw.rect(surface, NEON_PURPLE, (20, 46, w * ratio_xp, 10))
        pygame.draw.rect(surface, WHITE, (20, 46, w, 10), width=1)
        lvl_txt = self.font_small.render(f"Lv.{self.player.level}", True, WHITE)
        surface.blit(lvl_txt, (20 + w + 10, 40))

        # weapon list
        parts = []
        for wid, info in WEAPON_INFO.items():
            lvl = self.player.weapon_levels.get(wid, 0)
            if lvl > 0:
                parts.append(f"{info['name']} Lv{lvl}")
        if parts:
            wep_txt = self.font_small.render(" | ".join(parts), True, NEON_TEAL)
            surface.blit(wep_txt, (20, 64))

        score_txt = self.font_mid.render(f"SCORE {self.score}", True, NEON_CYAN)
        surface.blit(score_txt, (WIDTH - score_txt.get_width() - 20, 18))
        wave_txt = self.font_small.render(f"WAVE {self.wave}", True, WHITE)
        surface.blit(wave_txt, (WIDTH - wave_txt.get_width() - 20, 56))

        if self.combo > 2:
            combo_txt = self.font_mid.render(f"COMBO x{self.combo}", True, NEON_YELLOW)
            surface.blit(combo_txt, (WIDTH / 2 - combo_txt.get_width() / 2, 70))

        if self.banner_timer > 0:
            alpha = clamp(self.banner_timer / 2.2, 0, 1)
            txt = self.font_big.render(self.banner_text, True, NEON_ORANGE)
            s = pygame.Surface(txt.get_size(), pygame.SRCALPHA)
            s.blit(txt, (0, 0))
            s.set_alpha(int(255 * alpha))
            surface.blit(s, (WIDTH / 2 - txt.get_width() / 2, HEIGHT / 2 - 140))

        if not self.wave_active and not self.enemies and self.state == "playing":
            t = self.font_small.render(f"Next wave in: {max(0,self.wave_timer):.1f}s", True, WHITE)
            surface.blit(t, (WIDTH / 2 - t.get_width() / 2, 100))

        if not self.sound.enabled:
            warn = self.font_small.render("(No sound found - the game is quiet)", True, (140, 140, 150))
            surface.blit(warn, (20, HEIGHT - 28))

    def draw_levelup(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        title = self.font_big.render("LEVEL UP!", True, NEON_YELLOW)
        surface.blit(title, (WIDTH / 2 - title.get_width() / 2, 90))
        sub = self.font_small.render("Press 1, 2, or 3 to pick one", True, WHITE)
        surface.blit(sub, (WIDTH / 2 - sub.get_width() / 2, 160))

        card_w, card_h = 260, 190
        gap = 30
        total_w = card_w * len(self.level_choices) + gap * (len(self.level_choices) - 1)
        start_x = WIDTH / 2 - total_w / 2
        y = 230
        colors = [NEON_CYAN, NEON_PINK, NEON_PURPLE]
        for i, (label, _) in enumerate(self.level_choices):
            x = start_x + i * (card_w + gap)
            card = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            pygame.draw.rect(card, (20, 20, 34, 230), (0, 0, card_w, card_h), border_radius=14)
            pygame.draw.rect(card, colors[i % len(colors)], (0, 0, card_w, card_h), width=2, border_radius=14)
            surface.blit(card, (x, y))

            num = self.font_big.render(str(i + 1), True, colors[i % len(colors)])
            surface.blit(num, (x + card_w / 2 - num.get_width() / 2, y + 16))

            words = label.split(" ")
            lines = []
            cur = ""
            for w_ in words:
                test = (cur + " " + w_).strip()
                if self.font_small.size(test)[0] > card_w - 30:
                    lines.append(cur)
                    cur = w_
                else:
                    cur = test
            lines.append(cur)
            for j, line in enumerate(lines):
                t = self.font_small.render(line, True, WHITE)
                surface.blit(t, (x + card_w / 2 - t.get_width() / 2, y + 100 + j * 24))

    def draw_gameover(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surface.blit(overlay, (0, 0))
        title = self.font_big.render("GAME OVER", True, NEON_PINK)
        surface.blit(title, (WIDTH / 2 - title.get_width() / 2, HEIGHT / 2 - 120))
        s1 = self.font_mid.render(f"SCORE: {self.score}", True, WHITE)
        surface.blit(s1, (WIDTH / 2 - s1.get_width() / 2, HEIGHT / 2 - 40))
        s2 = self.font_small.render(f"You reached wave: {self.wave}   |   Your level: {self.player.level}", True, WHITE)
        surface.blit(s2, (WIDTH / 2 - s2.get_width() / 2, HEIGHT / 2 + 10))
        s3 = self.font_small.render("Press R to restart", True, NEON_CYAN)
        surface.blit(s3, (WIDTH / 2 - s3.get_width() / 2, HEIGHT / 2 + 60))

    def draw_devmenu(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        surface.blit(overlay, (0, 0))

        title = self.font_big.render("DEV MODE", True, NEON_GREEN)
        surface.blit(title, (WIDTH / 2 - title.get_width() / 2, 36))
        sub = self.font_mid.render(f"XP Multiplier: x{self.xp_multiplier:.1f}", True, NEON_YELLOW)
        surface.blit(sub, (WIDTH / 2 - sub.get_width() / 2, 96))

        y = 150
        for key, label in DEV_HOTKEYS:
            key_name = pygame.key.name(key).upper()
            line = self.font_small.render(f"[{key_name}]   {label}", True, WHITE)
            surface.blit(line, (WIDTH / 2 - 210, y))
            y += 30

        hint = self.font_small.render("Press ESC to close Dev Mode", True, NEON_CYAN)
        surface.blit(hint, (WIDTH / 2 - hint.get_width() / 2, y + 20))

    def draw(self):
        shake_x = random.uniform(-self.shake, self.shake)
        shake_y = random.uniform(-self.shake, self.shake)

        world = pygame.Surface((WIDTH, HEIGHT))
        self.draw_background(world)

        for o in self.orbs:
            o.draw(world)
        for eb in self.enemy_bullets:
            eb.draw(world)
        for e in self.enemies:
            e.draw(world)
        for b in self.bullets:
            b.draw(world)
        self.draw_weapons(world)
        self.particles.draw(world)
        if self.state != "gameover":
            self.player.draw(world)

        self.screen.fill((0, 0, 0))
        self.screen.blit(world, (shake_x, shake_y))

        self.draw_hud(self.screen)

        if self.state == "levelup":
            self.draw_levelup(self.screen)
        elif self.state == "gameover":
            self.draw_gameover(self.screen)
        elif self.state == "devmenu":
            self.draw_devmenu(self.screen)
        elif self.state == "paused":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            t = self.font_big.render("PAUSED", True, WHITE)
            self.screen.blit(t, (WIDTH / 2 - t.get_width() / 2, HEIGHT / 2 - 30))

        pygame.display.flip()

    # ---------------- MAIN LOOP ----------------
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "playing":
                            self.state = "paused"
                        elif self.state == "paused":
                            self.state = "playing"
                        elif self.state == "devmenu":
                            self.state = "paused"
                    elif event.key == pygame.K_r and self.state == "gameover":
                        self.reset()
                    elif self.state == "levelup":
                        if event.key == pygame.K_1:
                            self.apply_upgrade(0)
                        elif event.key == pygame.K_2:
                            self.apply_upgrade(1)
                        elif event.key == pygame.K_3:
                            self.apply_upgrade(2)
                    elif self.state == "paused":
                        ch = event.unicode
                        if ch and ch.isalnum():
                            self.dev_code_buffer = (self.dev_code_buffer + ch.lower())[-20:]
                            if self.dev_code_buffer.endswith("adminhack12"):
                                self.state = "devmenu"
                                self.dev_code_buffer = ""
                    elif self.state == "devmenu":
                        self.dev_handle_key(event.key)

            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()

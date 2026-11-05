# -*- coding: utf-8 -*-
# =====================================================================
#  ECLIPSE ZERO v1.0 - Videojuego 2D de aventura, plataformas, acción,
#  exploración y RPG ligero. TODO EN UN SOLO ARCHIVO.
#
#  Requisitos:  Python 3.10+ (compatible con 3.13) y Pygame.
#  Instalación: pip install pygame
#  Ejecutar:    python juego.py
#
#  Todo el arte (pixel art), los fondos, la música y los efectos de
#  sonido se generan proceduralmente con Pygame: no necesita imágenes
#  ni archivos de audio externos. La partida se guarda en saves/save.json
#  (la carpeta se crea sola junto a este archivo).
# =====================================================================
import json
import math
import os
import random
import sys

import pygame

# ---------------------------------------------------------------------
# SECCIÓN 1: CONFIGURACIÓN GENERAL, PALETA Y TEMAS DE MUNDO
# ---------------------------------------------------------------------
WIDTH, HEIGHT = 960, 540
TILE = 32
FPS = 60
DT = 1.0 / FPS
GRAVITY = 2400.0
MAX_FALL = 1000.0
TITLE = "ECLIPSE ZERO"
VERSION = "1.0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVES_DIR = os.path.join(BASE_DIR, "saves")
SAVE_FILE = os.path.join(SAVES_DIR, "save.json")

VIOLET = (124, 58, 237)
ELEC_BLUE = (59, 130, 246)
CYAN = (34, 211, 238)
MAGENTA = (232, 62, 240)
WHITE = (240, 244, 255)
GREY = (140, 140, 170)
DARKGREY = (60, 60, 90)
GOLD = (255, 209, 102)
RED = (255, 82, 82)
GREEN = (80, 250, 160)
ORANGE = (255, 160, 60)

RARITY_COLORS = {"común": GREY, "raro": ELEC_BLUE, "épico": MAGENTA, "legendario": GOLD}

WORLD_THEMES = {
    1: dict(name="CIUDAD CERO", sky=(10, 8, 30), sky2=(36, 18, 66), far=(46, 34, 90),
            mid=(66, 46, 128), tile=(56, 48, 100), tile_edge=(126, 116, 210),
            accent=CYAN, weather="none", music="world1"),
    2: dict(name="BOSQUE DE NEÓN", sky=(4, 20, 24), sky2=(8, 52, 46), far=(12, 74, 62),
            mid=(16, 112, 82), tile=(22, 96, 74), tile_edge=(96, 255, 186),
            accent=GREEN, weather="spores", music="world2"),
    3: dict(name="ESTACIÓN ABISAL", sky=(2, 10, 26), sky2=(6, 28, 60), far=(10, 42, 82),
            mid=(14, 62, 112), tile=(32, 72, 104), tile_edge=(84, 184, 234),
            accent=ELEC_BLUE, weather="rain", music="world3"),
    4: dict(name="DESIERTO DE CRISTAL", sky=(34, 14, 44), sky2=(86, 32, 74), far=(126, 52, 104),
            mid=(166, 84, 124), tile=(146, 84, 114), tile_edge=(255, 186, 146),
            accent=GOLD, weather="sand", music="world4"),
    5: dict(name="LA CIUDAD INVERTIDA", sky=(10, 4, 30), sky2=(44, 12, 74), far=(66, 22, 104),
            mid=(96, 34, 146), tile=(76, 44, 116), tile_edge=(206, 126, 255),
            accent=MAGENTA, weather="none", music="world5"),
    6: dict(name="LA FRONTERA DEL TIEMPO", sky=(6, 6, 18), sky2=(22, 22, 54), far=(34, 34, 84),
            mid=(54, 54, 124), tile=(64, 64, 106), tile_edge=(156, 156, 236),
            accent=WHITE, weather="none", music="world6"),
    7: dict(name="EL NÚCLEO ECLIPSE", sky=(16, 2, 10), sky2=(56, 4, 32), far=(86, 6, 42),
            mid=(126, 12, 62), tile=(66, 22, 44), tile_edge=(255, 66, 96),
            accent=RED, weather="embers", music="world7"),
}


def ensure_saves():
    try:
        os.makedirs(SAVES_DIR, exist_ok=True)
    except OSError:
        pass


# ---------------------------------------------------------------------
# SECCIÓN 2: AUDIO PROCEDURAL (efectos y música sintetizados, sin archivos)
# ---------------------------------------------------------------------
SR = 22050


def _note_freq(name):
    """'A4', 'C#3' -> frecuencia en Hz. 'R' = silencio."""
    if name == "R":
        return 0.0
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    n = name[:-1]
    octv = int(name[-1])
    idx = names.index(n) + (octv + 1) * 12 - 9  # A4 -> 57
    return 440.0 * (2.0 ** ((idx - 57) / 12.0))


def _tone(freq, dur, vol=0.3, wave="square", release=0.08):
    n = int(SR * dur)
    out = [0.0] * n
    ph = 0.0
    inc = freq / SR
    for i in range(n):
        ph += inc
        if ph >= 1.0:
            ph -= 1.0
        if wave == "square":
            v = 1.0 if ph < 0.5 else -1.0
        elif wave == "sine":
            v = math.sin(6.2831853 * ph)
        elif wave == "tri":
            v = 4.0 * abs(ph - 0.5) - 1.0
        else:  # saw
            v = 2.0 * ph - 1.0
        env = 1.0
        rem = (n - i) / SR
        if rem < release:
            env = rem / release
        out[i] = v * vol * env
    return out


def _noise(dur, vol=0.4, release=0.2):
    n = int(SR * dur)
    out = [0.0] * n
    for i in range(n):
        rem = (n - i) / SR
        env = 1.0
        if rem < release:
            env = rem / release
        out[i] = random.uniform(-1, 1) * vol * env
    return out


def _T(f, d, v, w="square"):
    return ("t", f, d, v, w)


def _N(d, v, r):
    return ("n", d, v, r)


SFX_DEF = {
    "jump": (_T(320, .06, .35), _T(520, .14, .30)),
    "double_jump": (_T(440, .05, .3, "tri"), _T(700, .15, .28, "tri")),
    "dash": (_N(.18, .30, .14),),
    "attack": (_T(900, .04, .25, "saw"), _T(1400, .08, .20, "saw")),
    "hit": (_N(.08, .35, .06), _T(200, .10, .30)),
    "hurt": (_T(220, .12, .4), _T(110, .18, .35)),
    "coin": (_T(988, .06, .28), _T(1319, .12, .28)),
    "shard": (_T(660, .07, .25, "tri"), _T(990, .07, .25, "tri"), _T(1320, .16, .25, "tri")),
    "chest": (_T(392, .08, .3, "tri"), _T(523, .08, .3, "tri"), _T(784, .2, .3, "tri")),
    "secret": (_T(784, .07, .25, "sine"), _T(1046, .07, .25, "sine"), _T(1568, .2, .25, "sine")),
    "checkpoint": (_T(523, .09, .25, "tri"), _T(659, .09, .25, "tri"), _T(880, .22, .25, "tri")),
    "enemy_die": (_N(.10, .3, .08), _T(160, .16, .3)),
    "boss_hit": (_N(.09, .3, .07), _T(120, .14, .35)),
    "boss_die": (_N(.8, .5, .7),),
    "victory": (_T(523, .12, .3, "tri"), _T(659, .12, .3, "tri"), _T(784, .12, .3, "tri"), _T(1046, .4, .3, "tri")),
    "gameover": (_T(330, .2, .3, "tri"), _T(262, .2, .3, "tri"), _T(196, .45, .3, "tri")),
    "select": (_T(600, .05, .18),),
    "confirm": (_T(700, .05, .2), _T(1050, .09, .2)),
    "pause": (_T(300, .09, .2, "tri"),),
    "potion": (_T(500, .08, .22, "sine"), _T(750, .08, .22, "sine"), _T(1000, .14, .22, "sine")),
    "fragment": (_T(523, .14, .3, "sine"), _T(784, .14, .3, "sine"), _T(1046, .14, .3, "sine"), _T(1568, .5, .3, "sine")),
    "door": (_T(150, .25, .3, "saw"), _T(300, .2, .2, "saw")),
    "shot": (_T(800, .05, .22, "saw"), _T(500, .08, .18, "saw")),
    "explosion": (_N(.45, .5, .4),),
    "buy": (_T(880, .06, .25), _T(1174, .12, .25)),
    "levelup": (_T(523, .1, .3), _T(659, .1, .3), _T(880, .1, .3), _T(1046, .3, .3)),
    "time_slow": (_T(1200, .3, .2, "sine"), _T(600, .4, .2, "sine")),
}

# Melodías chiptune: (nota, beats) por pista y mundo
MUSIC_DEF = {
    "world1": (["A4", "C5", "E5", "C5", "A4", "C5", "G4", "R", "A4", "C5", "E5", "A5", "G5", "E5", "D5", "R"],
               ["A2", "A2", "F2", "F2", "C3", "C3", "G2", "G2"], 100, "square", .16),
    "world2": (["E4", "G4", "A4", "D5", "E5", "D5", "A4", "G4", "E4", "G4", "A4", "B4", "D5", "B4", "A4", "R"],
               ["E2", "E2", "C2", "C2", "D2", "D2", "B1", "B1"], 88, "tri", .16),
    "world3": (["D4", "R", "F4", "R", "D4", "R", "C4", "R", "D4", "R", "A#3", "R", "A3", "R", "R", "R"],
               ["D2", "D2", "D2", "R", "A#1", "A#1", "A1", "A1"], 70, "square", .14),
    "world4": (["E4", "F4", "G4", "F4", "E4", "C4", "D4", "R", "E4", "F4", "G4", "A#4", "A4", "G4", "F4", "R"],
               ["E2", "E2", "C2", "C2", "D2", "D2", "D2", "R"], 96, "square", .16),
    "world5": (["B4", "D5", "F#5", "D5", "B4", "D5", "A4", "R", "G4", "B4", "D5", "B4", "F#4", "B4", "E4", "R"],
               ["B2", "B2", "G2", "G2", "E2", "E2", "F#2", "F#2"], 92, "tri", .16),
    "world6": (["C5", "D5", "E5", "G5", "E5", "D5", "C5", "R", "A#4", "C5", "D5", "F5", "D5", "C5", "A#4", "R"],
               ["F2", "F2", "G2", "G2", "A#1", "A#1", "C2", "C2"], 80, "sine", .18),
    "world7": (["E4", "E4", "G4", "E4", "A#4", "A4", "G4", "E4", "F4", "F4", "A4", "F4", "B4", "A4", "G4", "F4"],
               ["E2", "E2", "E2", "E2", "A#1", "A#1", "A1", "A1"], 132, "square", .18),
    "boss": (["D4", "D4", "F4", "G4", "G4", "A#4", "A4", "G4", "C5", "A#4", "A4", "G4", "F4", "D4", "D4", "R"],
             ["D2", "D2", "D2", "D2", "C2", "C2", "A#1", "A#1"], 140, "square", .20),
    "title": (["A4", "E5", "C5", "B4", "A4", "E5", "F5", "E5", "C5", "B4", "C5", "A4", "R", "R", "R", "R"],
              ["A2", "A2", "F2", "G2", "A2", "A2", "E2", "E2"], 96, "tri", .16),
}


class Audio:
    def __init__(self):
        self.ok = False
        self.sfx = {}
        self.music = {}
        self.current_music = None
        self.music_volume = 0.55
        self.sfx_volume = 0.8

    def init(self):
        try:
            pygame.mixer.pre_init(SR, -16, 1, 512)
            pygame.mixer.init()
            self.ok = True
        except Exception:
            self.ok = False
        if self.ok:
            try:
                self._build_sfx()
                self._build_music()
            except Exception:
                self.ok = False
        return self.ok

    def shutdown(self):
        try:
            pygame.mixer.quit()
        except Exception:
            pass

    def _buf(self, samples):
        b = bytearray(len(samples) * 2)
        j = 0
        for s in samples:
            if s > 1.0:
                s = 1.0
            elif s < -1.0:
                s = -1.0
            v = int(s * 32000)
            b[j] = v & 0xFF
            b[j + 1] = (v >> 8) & 0xFF
            j += 2
        return bytes(b)

    def _make(self, samples):
        try:
            return pygame.mixer.Sound(buffer=self._buf(samples))
        except Exception:
            return None

    def _build_sfx(self):
        for name, parts in SFX_DEF.items():
            out = []
            for p in parts:
                if p[0] == "t":
                    out.extend(_tone(p[1], p[2], p[3], p[4]))
                else:
                    out.extend(_noise(p[1], p[2], p[3]))
            self.sfx[name] = self._make(out)

    def _render_track(self, seq, bpm, wave="square", vol=0.16):
        spb = 60.0 / bpm
        out = []
        for note, beats in seq:
            dur = beats * spb
            if note == "R":
                out.extend([0.0] * int(SR * dur))
            else:
                out.extend(_tone(_note_freq(note), dur, vol, wave, release=min(0.12, dur * 0.5)))
        return out

    def _render_bass(self, seq, bpm, vol=0.20):
        spb = 60.0 / bpm
        out = []
        for note, beats in seq:
            dur = beats * spb
            if note == "R":
                out.extend([0.0] * int(SR * dur))
            else:
                out.extend(_tone(_note_freq(note) / 2.0, dur, vol, "tri", release=min(0.1, dur * 0.4)))
        return out

    def _build_music(self):
        for key, (lead, bass, bpm, wave, vol) in MUSIC_DEF.items():
            a = self._render_track([(n, 0.5) for n in lead], bpm, wave, vol)
            b = self._render_bass([(n, 1.0) for n in bass], bpm, vol=0.20)
            n = max(len(a), len(b))
            if len(a) < n:
                a = a + [0.0] * (n - len(a))
            if len(b) < n:
                b = b + [0.0] * (n - len(b))
            self.music[key] = self._make([a[i] + b[i] for i in range(n)])

    def play(self, name):
        if not self.ok:
            return
        s = self.sfx.get(name)
        if s:
            try:
                s.set_volume(self.sfx_volume)
                s.play()
            except Exception:
                pass

    def play_music(self, key):
        if not self.ok or self.current_music == key:
            return
        self.stop_music()
        s = self.music.get(key)
        if s:
            try:
                s.set_volume(self.music_volume)
                s.play(loops=-1, fade_ms=600)
                self.current_music = key
            except Exception:
                pass

    def stop_music(self):
        if not self.ok:
            return
        try:
            pygame.mixer.stop()
        except Exception:
            pass
        self.current_music = None

    def set_music_volume(self, v):
        self.music_volume = max(0.0, min(1.0, v))
        if self.ok and self.current_music:
            s = self.music.get(self.current_music)
            if s:
                try:
                    s.set_volume(self.music_volume)
                except Exception:
                    pass

    def set_sfx_volume(self, v):
        self.sfx_volume = max(0.0, min(1.0, v))


# ---------------------------------------------------------------------
# SECCIÓN 3: PARTÍCULAS Y CLIMA (lluvia, esporas, arena, brasas)
# ---------------------------------------------------------------------
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "grav", "fade")

    def __init__(self, x, y, vx, vy, life, color, size, grav=0.0, fade=True):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.grav = grav
        self.fade = fade

    def update(self, dt):
        self.life -= dt
        self.vy += self.grav * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

    def alive(self):
        return self.life > 0


class Particles:
    def __init__(self):
        self.list = []
        self._t = 0.0

    def clear(self):
        self.list.clear()

    def burst(self, x, y, color, n=10, speed=(40, 180), life=(0.25, 0.7),
              size=(2, 4), gravity=300.0, angle=None, spread=6.283):
        for _ in range(n):
            a = random.uniform(0, 6.283) if angle is None else angle + random.uniform(-spread / 2, spread / 2)
            sp = random.uniform(*speed)
            p = Particle(x, y, math.cos(a) * sp, math.sin(a) * sp,
                         random.uniform(*life), color, random.randint(*size), gravity)
            self.list.append(p)

    def float_up(self, x, y, color, n=4, life=(0.5, 1.0)):
        for _ in range(n):
            p = Particle(x + random.uniform(-8, 8), y, random.uniform(-15, 15),
                         random.uniform(-70, -25), random.uniform(*life), color,
                         random.randint(2, 3), -12)
            self.list.append(p)

    def weather(self, kind, camera, dt):
        x0, y0 = camera.left, camera.top
        w, h = camera.width, camera.height
        self._t += dt
        if kind == "rain":
            n = int(14 * dt * 60)
            for _ in range(n):
                self.list.append(Particle(x0 + random.uniform(-100, w + 100), y0 - 10,
                                          -160, 620, 1.2, (120, 160, 255), 2, 0, fade=False))
        elif kind == "sand":
            if random.random() < 0.6:
                self.list.append(Particle(x0 + random.uniform(-50, w + 50), y0 + random.uniform(0, h),
                                          random.uniform(-260, -120), random.uniform(-30, 30), 1.6,
                                          (255, 200, 140), 2, 0, fade=False))
        elif kind == "spores":
            if random.random() < 0.35:
                self.list.append(Particle(x0 + random.uniform(0, w), y0 + random.uniform(0, h),
                                          random.uniform(-12, 12), random.uniform(-26, -8), 2.4,
                                          (120, 255, 170), 2, 0))
        elif kind == "embers":
            if random.random() < 0.4:
                self.list.append(Particle(x0 + random.uniform(0, w), y0 + h + 6,
                                          random.uniform(-20, 20), random.uniform(-90, -40), 2.0,
                                          (255, 120, 60), 2, 0))

    def update(self, dt):
        arr = self.list
        i = 0
        while i < len(arr):
            p = arr[i]
            p.update(dt)
            if p.alive():
                i += 1
            else:
                arr[i] = arr[-1]
                arr.pop()

    def draw(self, surf, camera, rain=False):
        for p in self.list:
            sx = int(p.x - camera.left)
            sy = int(p.y - camera.top)
            if p.life < 0.15 and p.fade:
                k = max(0.0, p.life / 0.15)
                c = (int(p.color[0] * k), int(p.color[1] * k), int(p.color[2] * k))
            else:
                c = p.color
            if rain and p.vy > 300 and p.vx < -100:
                pygame.draw.line(surf, c, (sx, sy), (sx - int(p.vx * 0.03), sy - int(p.vy * 0.03)), 1)
            else:
                pygame.draw.rect(surf, c, (sx, sy, p.size, p.size))

st = sys.modules[__name__]  # alias: los módulos originales usaban st.*

# ---------------------------------------------------------------------
# SECCIÓN 4: SPRITES Y GRÁFICOS PROCEDURALES (pixel art dibujado con Pygame)
# ---------------------------------------------------------------------
_cache = {}


def _px(grid, palette, ps=2):
    """Dibuja una rejilla de caracteres en una superficie. '.' = transparente."""
    h = len(grid)
    w = max(len(r) for r in grid)
    surf = pygame.Surface((w * ps, h * ps), pygame.SRCALPHA)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch in (" ", "."):
                continue
            c = palette.get(ch)
            if c:
                surf.fill(c, (x * ps, y * ps, ps, ps))
    return surf


# ---------------- KAI ----------------
KAI_PAL = dict(S=(30, 26, 60), s=(48, 42, 92), C=CYAN, c=(150, 240, 255),
               K=WHITE, V=VIOLET, O=(255, 170, 120), E=(20, 16, 40))

_KAI_IDLE = [
    "....SSSS....",
    "...SSssSS...",
    "...SKKKKS...",
    "...SKOOES...",
    "....SOOO....",
    "....VVVV....",
    "...VVCVVs...",
    "..SVVCVVSS..",
    "..s.VCVV.s..",
    "....VSVV....",
    "....SS.SS...",
    "...SSS.SSS..",
]
_KAI_RUN1 = [
    "....SSSS....",
    "...SSssSS...",
    "...SKKKKS...",
    "...SKOOES...",
    "....SOOO....",
    "....VVVV....",
    "...VVCVVs...",
    "..SVVCVVSS..",
    "....VCVV....",
    "...VSSVV....",
    "..SS...SS...",
    ".SSS...SSS..",
]
_KAI_RUN2 = [
    "....SSSS....",
    "...SSssSS...",
    "...SKKKKS...",
    "...SKOOES...",
    "....SOOO....",
    "....VVVV....",
    "...VVCVVs...",
    "..SVVCVVSS..",
    "....VCVV....",
    "....VSVV....",
    "...SSS.SS...",
    "..SSS..SSS..",
]
_KAI_RUN3 = [
    "....SSSS....",
    "...SSssSS...",
    "...SKKKKS...",
    "...SKOOES...",
    "....SOOO....",
    "....VVVV....",
    "...VVCVVs...",
    "..SVVCVVSS..",
    "....VCVV....",
    "...VVSVV....",
    "...SS...SS..",
    "..SSS...SSS.",
]
_KAI_JUMP = [
    "....SSSS....",
    "...SSssSS...",
    "...SKKKKS...",
    "...SKOOES...",
    "....SOOO....",
    "...VVVVV....",
    "..SVVCVVs...",
    ".SSVVCVVSS..",
    "s...VCVV..s.",
    "....VSVV....",
    "...SS...SS..",
    "..SS.....SS.",
]
_KAI_FALL = [
    "....SSSS....",
    "...SSssSS...",
    "...SKKKKS...",
    "...SKOOES...",
    "....SOOO....",
    "....VVVV....",
    "..sVVCVVs...",
    ".SSVVCVVSS..",
    "S...VCVV...S",
    "....VSVV....",
    "...SSS.SSS..",
    "............",
]
_KAI_DASH = [
    "............",
    "...SSSS.....",
    "..SSssSS....",
    "..SKKKKS....",
    "..SKOOES....",
    "c...SOOO....",
    ".ccVVVVV....",
    "..SVVCVVsS..",
    "....VCVV.SS.",
    "...VVSVVV...",
    "..SSS..SSS..",
    ".SSS....SS..",
]
_KAI_ATK1 = [
    "....SSSS....",
    "...SSssSS...",
    "...SKKKKS...",
    "...SKOOES...",
    "....SOOO....",
    "....VVVVccc.",
    "...VVCVVscc.",
    "..SVVCVVSS..",
    "....VCVV....",
    "....VSVV....",
    "....SS.SS...",
    "...SSS.SSS..",
]
_KAI_ATK2 = [
    "....SSSS....",
    "...SSssSS...",
    "...SKKKKS...",
    "...SKOOES...",
    "....SOOO....",
    "ccccVVVV....",
    ".sccVCVVs...",
    "..SVVCVVSS..",
    "....VCVV....",
    "....VSVV....",
    "....SS.SS...",
    "...SSS.SSS..",
]
_KAI_HURT = [
    "............",
    "...SSSS.....",
    "..SSssSSS...",
    "..SKKKKS....",
    "..SKOOES....",
    "...SOOO.....",
    "..VVVVV.....",
    ".SVVCVVSs...",
    "S..VCVV..S..",
    "...VSVV.....",
    "..SSS.SS....",
    ".SS....SS...",
]


def kai_frame(state, i=0, facing=1):
    key = ("kai", state, i, facing)
    if key in _cache:
        return _cache[key]
    if state == "run":
        grids = [_KAI_RUN1, _KAI_RUN2, _KAI_RUN3, _KAI_RUN2]
    elif state == "jump":
        grids = [_KAI_JUMP]
    elif state == "fall":
        grids = [_KAI_FALL]
    elif state == "dash":
        grids = [_KAI_DASH]
    elif state == "attack":
        grids = [_KAI_ATK1, _KAI_ATK2]
    elif state == "hurt":
        grids = [_KAI_HURT]
    else:
        grids = [_KAI_IDLE]
    grid = grids[min(i, len(grids) - 1)]
    surf = _px(grid, KAI_PAL, 2)
    if facing < 0:
        surf = pygame.transform.flip(surf, True, False)
    _cache[key] = surf
    return surf


# ---------------- PIX (robot guía) ----------------
_PIX_PAL = dict(B=ELEC_BLUE, b=(160, 210, 255), W=WHITE, E=(20, 30, 60), Y=GOLD)


def pix_frame(t):
    key = ("pix", t // 2 % 2)
    if key in _cache:
        return _cache[key]
    if key[1] == 0:
        g = ["..BBBB..", ".BbbbbB.", "BBWBWBBB", "BbbbbbbB", ".BBBBBB.", "..E..E.."]
    else:
        g = ["..BBBB..", ".BbbbbB.", "BBWBWBBB", "BbbbbbbB", ".BBBBBB.", ".E....E."]
    surf = _px(g, _PIX_PAL, 2)
    _cache[key] = surf
    return surf


# ---------------- Enemigos ----------------
def enemy_sprite(kind, state, i=0, facing=1):
    key = ("en", kind, state, i, facing)
    if key in _cache:
        return _cache[key]
    if kind == "drone":
        pal = dict(D=RED, d=(255, 140, 120), E=(30, 10, 10), W=WHITE)
        g = ["..DDDD..", ".DdWWdD.", "DEWWWWED", ".DDDDDD.", "d.D..D.d"]
    elif kind == "crawler":
        pal = dict(S=(60, 40, 110), s=(110, 80, 190), E=MAGENTA, W=WHITE)
        if state == "chase":
            g = [".S....S.", ".SSSSSS.", "SsESSSEs", ".SSSSSS.", "S.S..S.S"]
        else:
            g = ["........", ".SSSSSS.", "SsESSSEs", ".SSSSSS.", "S.S..S.S"]
    elif kind == "heavy":
        pal = dict(H=(70, 74, 110), h=(120, 126, 170), R=RED, E=(20, 20, 30))
        g = ["hHHHHHHh", "HHhHHhHH", "HERRRRRH", "HHHHHHHH", "hHH..HHh", "hH....Hh"]
    elif kind == "flyer":
        pal = dict(M=MAGENTA, m=(255, 150, 255), W=WHITE)
        if i % 2:
            g = ["m......m", "mMMMMMMm", ".MMWMM..", ".MMMMM..", "..M..M.."]
        else:
            g = ["........", "mMMMMMMm", "mMMWMMMm", ".MMMMM..", "..M..M.."]
    elif kind == "sniper":
        pal = dict(G=(70, 120, 90), g=(120, 200, 150), R=RED, C=CYAN)
        g = ["..GGGG..", ".GggggG.", "GGRCCRGg", ".Gggggg.", ".G....G."]
    elif kind == "mimic":
        pal = dict(V=VIOLET, v=(190, 160, 255), W=WHITE, K=(30, 24, 60))
        g = ["vVVVVVVv", "VVWKWKVV", "VVVVVVVV", ".VKKKKV.", "v.V..V.v"]
    else:  # guardian
        pal = dict(G=GOLD, g=(255, 240, 170), E=(60, 40, 10), C=CYAN)
        g = [".gGGGGg.", "GGCCCGGG", "GGeGGGeG", "GGGGGGGG", "gGG..GGg", ".gGGGGg."]
    surf = _px(g, pal, 2)
    if facing < 0:
        surf = pygame.transform.flip(surf, True, False)
    _cache[key] = surf
    return surf


# ---------------- Jefes ----------------
def boss_sprite(kind, phase, i=0, facing=1):
    key = ("bo", kind, phase, i, facing)
    if key in _cache:
        return _cache[key]
    if kind == "titan":
        pal = dict(H=(70, 74, 110), h=(120, 126, 170), R=RED, E=(15, 15, 25), C=CYAN)
        g = ["..hHHHHHHh..", ".HHHhHHhHHH.", "HHRRHHHHRRHH", "HHRCCRRCCRHH", "HHHHHHHHHHHH",
             ".HHHHHHHHHH.", "hHHHHHHHHHHh", "hH.HHHHHH.Hh", "hH.HH..HH.Hh", "...HH..HH..."]
    elif kind == "queen":
        pal = dict(P=(30, 140, 100), p=(90, 240, 170), G=GREEN, W=WHITE, E=(5, 40, 30))
        g = [".pP......Pp.", ".PPpppppPP..", "PPWWpGPWWPP.", "PPpppppppPP.", ".PPEPPPEPP..",
             ".PPPPPPPPP..", "..PPPPPPP...", ".pP.PPP.Pp..", ".P..P.P..P..", "....P.P....."]
    elif kind == "clock":
        pal = dict(W=WHITE, w=(180, 180, 230), C=CYAN, E=(20, 20, 40), G=GOLD)
        g = ["..wwWWww..", ".wCCCCCCw.", "wCWWCCWWCw", "wCGWWGWCCw", "wCCCCCCCw.",
             ".wCCCCCCw.", "..wWWWWw..", ".w.w..w.w.", "w...ww...w", ".........."]
    elif kind == "echo":
        pal = dict(V=VIOLET, v=(200, 170, 255), K=WHITE, E=(20, 16, 40))
        g = ["..vVVVVv..", ".vVKVKVKv.", ".VVVVVVVV.", "vVEVVVVEVv", ".VVVVVVVV.",
             ".vVVVVVVv.", "..VVVVVV..", ".vVVVVVVv.", ".VV.VV.VV.", "v........."]
    else:  # eclipse - jefe final
        pal = dict(R=(120, 10, 40), r=(255, 60, 90), K=(10, 5, 15), W=WHITE, G=GOLD)
        if i % 2:
            g = ["rR.RRRR.Rr", "RRRKWWKRRR", "RRRRRRRRRR", "rRRGGGGRRr", ".RRRRRRRR.",
                 ".rRRRRRRr.", "..RRRRRR..", ".rRR..RRr.", "rR..RR..Rr", ".........."]
        else:
            g = ["..RRRRRR..", ".RRKWWKRR.", "RRRRRRRRRR", "rRGGGGGGRr", "rRRRRRRRRr",
                 ".rRRRRRRr.", "..RRRRRR..", ".rRRRRRRr.", ".RR.RR.RR.", ".........."]
    surf = _px(g, pal, 4)
    if facing < 0:
        surf = pygame.transform.flip(surf, True, False)
    _cache[key] = surf
    return surf


# ---------------- Tiles / objetos / fondos ----------------
def tile(theme, solid=True):
    key = ("tile", theme["name"], solid)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((TILE, TILE))
    s.fill(theme["tile"])
    edge = theme["tile_edge"]
    s.fill(edge, (0, 0, TILE, 3))
    s.fill(edge, (0, 0, 3, TILE))
    rnd = random.Random(hash(theme["name"]) & 0xFFFF)
    for _ in range(5):
        x, y = rnd.randint(2, TILE - 6), rnd.randint(6, TILE - 6)
        s.fill(tuple(max(0, c - 26) for c in theme["tile"]), (x, y, 4, 3))
    if not solid:
        s = pygame.Surface((TILE, 6), pygame.SRCALPHA)
        s.fill(edge)
        s.fill(tuple(min(255, c + 40) for c in edge), (0, 0, TILE, 2))
    _cache[key] = s
    return s


def spike_surf(theme):
    key = ("spike", theme["name"])
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    c = theme["tile_edge"]
    for i in range(4):
        x = i * 8
        pygame.draw.polygon(s, c, [(x, 32), (x + 4, 16), (x + 8, 32)])
    _cache[key] = s
    return s


def coin_surf():
    if "coin" in _cache:
        return _cache["coin"]
    s = pygame.Surface((10, 12), pygame.SRCALPHA)
    pygame.draw.ellipse(s, GOLD, (0, 0, 10, 12))
    pygame.draw.ellipse(s, (255, 240, 180), (2, 2, 6, 8))
    _cache["coin"] = s
    return s


def shard_surf():
    if "shard" in _cache:
        return _cache["shard"]
    s = pygame.Surface((14, 18), pygame.SRCALPHA)
    pygame.draw.polygon(s, CYAN, [(7, 0), (14, 9), (7, 18), (0, 9)])
    pygame.draw.polygon(s, (200, 255, 255), [(7, 4), (10, 9), (7, 14), (4, 9)])
    _cache["shard"] = s
    return s


def memory_surf():
    if "memory" in _cache:
        return _cache["memory"]
    s = pygame.Surface((14, 14), pygame.SRCALPHA)
    pygame.draw.rect(s, MAGENTA, (1, 1, 12, 12), border_radius=3)
    pygame.draw.rect(s, (255, 180, 255), (3, 3, 8, 8), border_radius=2)
    _cache["memory"] = s
    return s


def chest_surf(opened=False):
    key = ("chest", opened)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((26, 20), pygame.SRCALPHA)
    body = (110, 70, 40) if not opened else (70, 46, 28)
    s.fill(body, (0, 6, 26, 14))
    s.fill((150, 100, 55), (0, 0, 26, 7))
    s.fill(GOLD, (11, 6, 4, 8))
    if opened:
        s.fill((30, 20, 12), (3, 8, 20, 9))
        s.fill(GOLD, (10, 2, 6, 4))
    pygame.draw.rect(s, (60, 38, 20), (0, 0, 26, 20), 1)
    _cache[key] = s
    return s


def checkpoint_surf(active):
    key = ("cp", active)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((16, 40), pygame.SRCALPHA)
    s.fill((90, 90, 120), (6, 0, 4, 40))
    c = CYAN if active else (90, 100, 130)
    pygame.draw.polygon(s, c, [(10, 2), (16, 7), (10, 13)])
    _cache[key] = s
    return s


def door_surf(theme):
    key = ("door", theme["name"])
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((32, 52), pygame.SRCALPHA)
    s.fill(theme["tile_edge"], (0, 0, 32, 52))
    s.fill((12, 10, 26), (4, 4, 24, 48))
    s.fill(theme["accent"], (6, 6, 20, 4))
    s.fill(theme["accent"], (6, 44, 20, 4))
    _cache[key] = s
    return s


def potion_surf(color):
    key = ("potion", color)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((12, 16), pygame.SRCALPHA)
    s.fill((200, 210, 240), (3, 0, 6, 3))
    pygame.draw.rect(s, (230, 230, 250), (2, 3, 8, 12), border_radius=3)
    s.fill(color, (3, 7, 6, 7))
    _cache[key] = s
    return s


def bg_layers(theme):
    """Genera (far, mid) superficies grandes para el parallax por tema."""
    key = ("bg", theme["name"])
    if key in _cache:
        return _cache[key]
    rnd = random.Random(hash(theme["name"]) & 0xFFFF)
    W, H = 960, 540
    far = pygame.Surface((W, H), pygame.SRCALPHA)
    mid = pygame.Surface((W, H), pygame.SRCALPHA)
    name = theme["name"]
    if name == "BOSQUE DE NEÓN":
        for _ in range(16):
            x = rnd.randint(0, W)
            h = rnd.randint(90, 200)
            w = rnd.randint(14, 26)
            pygame.draw.polygon(far, theme["far"], [(x, H), (x + w // 2, H - h), (x + w, H)])
        for _ in range(10):
            x = rnd.randint(0, W)
            h = rnd.randint(140, 320)
            w = rnd.randint(20, 38)
            pygame.draw.polygon(mid, theme["mid"], [(x, H), (x + w // 2, H - h), (x + w, H)])
            for _ in range(6):
                pygame.draw.circle(mid, theme["accent"], (x + rnd.randint(4, w - 4), H - rnd.randint(20, h)), 2)
    elif name in ("CIUDAD CERO", "LA CIUDAD INVERTIDA"):
        for surf, col, n in ((far, theme["far"], 12), (mid, theme["mid"], 9)):
            x = 0
            while x < W:
                w = rnd.randint(40, 90)
                h = rnd.randint(120, 360)
                pygame.draw.rect(surf, col, (x, H - h, w, h))
                for _ in range(rnd.randint(2, 8)):
                    pygame.draw.rect(surf, theme["accent"],
                                     (x + rnd.randint(4, w - 8), H - h + rnd.randint(8, h - 14), 4, 5))
                x += w + rnd.randint(6, 30)
    elif name == "ESTACIÓN ABISAL":
        for surf, col in ((far, theme["far"]), (mid, theme["mid"])):
            for _ in range(6):
                x, y = rnd.randint(0, W), rnd.randint(60, 340)
                pygame.draw.rect(surf, col, (x, y, rnd.randint(80, 200), rnd.randint(60, 140)), border_radius=12)
            for _ in range(5):
                pygame.draw.circle(surf, col, (rnd.randint(0, W), rnd.randint(80, 300)), rnd.randint(30, 70))
        for _ in range(24):
            pygame.draw.circle(far, (60, 140, 200), (rnd.randint(0, W), rnd.randint(0, H)), 2)
    elif name == "DESIERTO DE CRISTAL":
        for surf, col in ((far, theme["far"]), (mid, theme["mid"])):
            for _ in range(5):
                x = rnd.randint(-100, W)
                w = rnd.randint(220, 420)
                h = rnd.randint(60, 160)
                pygame.draw.polygon(surf, col, [(x, H), (x + w // 2, H - h), (x + w, H)])
        for _ in range(30):
            pygame.draw.circle(far, (255, 230, 200), (rnd.randint(0, W), rnd.randint(0, H)), rnd.randint(1, 2))
    elif name == "LA FRONTERA DEL TIEMPO":
        for surf, col in ((far, theme["far"]), (mid, theme["mid"])):
            for _ in range(7):
                x, y = rnd.randint(0, W), rnd.randint(40, 400)
                r = rnd.randint(20, 80)
                pygame.draw.circle(surf, col, (x, y), r, 3)
                pygame.draw.line(surf, col, (x - r, y), (x + r, y), 2)
    else:  # EL NÚCLEO ECLIPSE
        for surf, col in ((far, theme["far"]), (mid, theme["mid"])):
            for _ in range(8):
                x = rnd.randint(0, W)
                w, h = rnd.randint(50, 110), rnd.randint(150, 400)
                pygame.draw.rect(surf, col, (x, H - h, w, h))
                pygame.draw.line(surf, theme["accent"], (x + w // 2, H - h), (x + w // 2, H - h - 20), 2)
    _cache[key] = (far, mid)
    return far, mid


def glow_surf(radius, color):
    key = ("glow", radius, color)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -2):
        k = 1 - r / radius
        c = (color[0], color[1], color[2], int(70 * k))
        pygame.draw.circle(s, c, (radius, radius), r)
    _cache[key] = s
    return s


def sword_blade(color):
    key = ("sword", color)
    if key in _cache:
        return _cache[key]
    s = pygame.Surface((46, 8), pygame.SRCALPHA)
    s.fill(color, (4, 2, 36, 4))
    s.fill((255, 255, 255), (34, 1, 10, 6))
    s.fill((90, 90, 120), (0, 1, 6, 6))
    _cache[key] = s
    return s


# ---------------------------------------------------------------------
# SECCIÓN 5: FÍSICA Y COLISIONES (pasadas separadas X/Y)
# ---------------------------------------------------------------------
class Mover:
    """Plataforma móvil oscilante (horizontal o vertical)."""

    def __init__(self, x, y, w, h, axis=0, dist=50, speed=1.5, phase=0.0):
        self.rect = pygame.Rect(x, y, w, h)
        self.x0, self.y0 = x, y
        self.axis = axis
        self.dist = dist
        self.speed = speed
        self.t = phase
        self._dx = 0
        self._dy = 0

    def update(self, dt):
        self.t += dt * self.speed
        off = math.sin(self.t) * self.dist
        if self.axis == 0:
            nx = int(self.x0 + off)
            self._dx = nx - self.rect.x
            self._dy = 0
            self.rect.x = nx
        else:
            ny = int(self.y0 + off)
            self._dy = ny - self.rect.y
            self._dx = 0
            self.rect.y = ny


class PhysicsWorld:
    """Gestiona sólidos y resuelve colisiones de entidades rectangulares."""

    def __init__(self):
        self.solids = []       # rectángulos de tiles sólidos
        self.oneways = []      # plataformas finas
        self.movers = []       # plataformas móviles
        self.hazards = []      # rectángulos de daño (pinchos)

    def move_entity(self, ent, dt, drop_down=0.0):
        """Mueve la entidad resolviendo colisiones. Devuelve (hit_x, True, on_ground, on_mover)."""
        ent.rect.x += int(ent.vx * dt)
        hit_x = False
        for r in self.solids:
            if r.colliderect(ent.rect):
                if ent.vx > 0:
                    ent.rect.right = r.left
                elif ent.vx < 0:
                    ent.rect.left = r.right
                hit_x = True
                ent.vx = 0
        for m in self.movers:
            if m.rect.colliderect(ent.rect):
                if ent.vx > 0:
                    ent.rect.right = m.rect.left
                else:
                    ent.rect.left = m.rect.right
                hit_x = True
                ent.vx = 0

        on_ground = False
        on_mover = None
        ent.rect.y += int(ent.vy * dt)
        for r in self.solids:
            if r.colliderect(ent.rect):
                if ent.vy > 0:
                    ent.rect.bottom = r.top
                    on_ground = True
                else:
                    ent.rect.top = r.bottom
                ent.vy = 0
        for m in self.movers:
            if m.rect.colliderect(ent.rect):
                if ent.vy >= 0:
                    ent.rect.bottom = m.rect.top
                    on_ground = True
                    on_mover = m
                    ent.vy = 0
                else:
                    ent.rect.top = m.rect.bottom
                    ent.vy = 0
        if ent.vy >= 0 and drop_down <= 0:
            for r in self.oneways:
                if r.colliderect(ent.rect) and ent.rect.bottom - int(ent.vy * dt) <= r.top + 4:
                    ent.rect.bottom = r.top
                    on_ground = True
                    ent.vy = 0
        if on_mover is not None:
            ent.rect.x += int(on_mover._dx)
            ent.rect.y += int(on_mover._dy)
        return hit_x, True, on_ground, on_mover

    def hazard_hit(self, rect):
        return any(rect.colliderect(h) for h in self.hazards)

    def ground_below(self, rect, dist=200):
        probe = rect.copy()
        probe.height += dist
        for r in self.solids:
            if probe.colliderect(r) and r.top >= rect.bottom - 4:
                return True
        return False


# ---------------------------------------------------------------------
# SECCIÓN 6: NARRATIVA (historia, diálogos, recuerdos, decisiones, finales)
# ---------------------------------------------------------------------
INTRO_SCENES = [
    ("NEXARIA.", "Un mundo que alguna vez conoció el sol."),
    ("Hace cien años, una máquina llamada el NÚCLEO ECLIPSE", "absorbió la luz del sol. La noche nunca terminó."),
    ("Antes de desaparecer, siete guardianes dividieron", "la última energía del universo en SIETE FRAGMENTOS."),
    ("Los escondieron en las regiones más remotas del mundo,", "protegidos por criaturas nacidas de los recuerdos de la humanidad."),
    ("Hoy, en una ciudad abandonada...", "un joven despierta sin recordar quién es."),
    ("Su nombre... lo recordará pronto.", "Su viaje por la luz comienza ahora."),
]

DIALOGUES = {
    "wake": [
        ("PIX", "¡Pi-piii! ¡Despierta! Pensé que ya no quedaba nadie con pulso en Ciudad Cero."),
        ("KAI", "¿Quién... quién soy? ¿Dónde estoy?"),
        ("PIX", "Soy PIX, unidad de asistencia exploratoria. Tú pareces llamarte KAI. Está escrito en tu chaqueta."),
        ("PIX", "Esta ciudad quedó vacía cuando el Núcleo Eclipse robó la luz del sol. Solo quedan robots defectuosos... como esos que vienen hacia nosotros."),
        ("KAI", "Mi mano... brilla. Siento energía corriendo por dentro."),
        ("PIX", "¡Fascinante! Esa marca es un SIGILO DE GUARDIÁN. Puedes absorber energía de los fragmentos. Tal vez... puedas devolver el sol."),
        ("KAI", "Entonces iré por los siete fragmentos. Y de paso, descubriré quién soy."),
    ],
    "mara": [
        ("MARA", "Vaya, un vivo. Hace años que no veía uno. Soy Mara, recolectora de recuerdos."),
        ("MARA", "Vendo espadas de energía y pociones por monedas. También compro... historias."),
        ("KAI", "¿Historias?"),
        ("MARA", "Los documentos que encuentres por ahí cuentan la verdad del Eclipse. Si me traes recuerdos, te contaré lo que sé."),
        ("MARA", "Escucha: dicen que el héroe que intentó detener el Núcleo hace cien años... nunca regresó. O sí. Depende de a quién preguntes."),
    ],
    "mara_memory": [
        ("MARA", "¿Más recuerdos? Interesante... Este habla de un explorador que se parecía muchísimo a ti."),
        ("MARA", "Dice textualmente: 'Si vuelvo a hacerlo, que al menos alguien me recuerde'. Inquietante, ¿no?"),
    ],
    "checkpoint_first": [
        ("PIX", "He sincronizado un PUNTO DE CONTROL. Si te derrotan, reaparecerás aquí."),
    ],
    "world2_enter": [
        ("PIX", "El FRAGMENTO de Ciudad Cero emite una señal hacia el este: el Bosque de Neón."),
        ("PIX", "Allí las plantas son casi conscientes. Dicen que recuerdan canciones de antes de la noche."),
    ],
    "world3_enter": [
        ("PIX", "La Estación Abisal estudiaba los océanos oscuros. Su gravedad está alterada: cuidado con las caídas."),
    ],
    "world4_enter": [
        ("PIX", "El Desierto de Cristal... arenas que brillan y tormentas de partículas. Las ruinas son más antiguas que el Eclipse."),
        ("KAI", "¿Cómo puede haber algo más antiguo que el Eclipse?"),
        ("PIX", "Esa es exactamente la pregunta que me da miedo responder."),
    ],
    "world5_enter": [
        ("PIX", "La Ciudad Invertida: edificios colgando del cielo. La gravedad cambia de bando aquí. No mires abajo. O sí."),
    ],
    "world6_enter": [
        ("PIX", "La Frontera del Tiempo. Los ecos del pasado caminan por aquí. KAI... yo he estado aquí antes. No recuerdo cuándo."),
        ("KAI", "Tú también tienes un pasado que recuperar, ¿eh, PIX?"),
    ],
    "world7_enter": [
        ("PIX", "El Núcleo Eclipse. El final de la noche eterna empieza aquí. O el final nuestro."),
        ("KAI", "Cuando acabe esto, quiero recordar TODO. Incluso lo malo."),
    ],
    "twist": [
        ("PIX", "Kai... los archivos del Núcleo se han abierto solos. Mira esta grabación."),
        ("??? ", "'Sujeto K-A-I: bucle número 34. El explorador llega, reúne los fragmentos y se fusiona con el Núcleo para reemplazarlo.'"),
        ("KAI", "¿Reemplazarlo...?"),
        ("???", "'Cada vez que el héroe vence al Núcleo, se convierte en el nuevo Núcleo. La noche eterna continúa. Bucle 35: iniciando.'"),
        ("PIX", "Kai, tu siligio... es del guardián que creó el Núcleo. Tú ERES el primer Eclipse. El original."),
        ("KAI", "Entonces esta vez romperé el bucle. A mi manera."),
    ],
    "pre_final": [
        ("KAI", "PIX, si me convierto en eso... bórrame. O mejor: recuérdame quién fui."),
        ("PIX", "Pi-pi... Prometido. Los recuerdos son mi especialidad."),
    ],
}

MEMORIES = {
    1: ("REGISTRO DE CIUDAD CERO", "Día 40 tras el eclipse. La población evacuó hacia el sur. Los robots de mantenimiento siguen reparando una ciudad que ya nadie habita. Alguien programó esperanza en ellos."),
    2: ("CANCIONES DEL BOSQUE", "El biólogo jefe dejó escrito: las plantas de neón crecen hacia las canciones que la gente cantaba. Si escuchas el bosque susurrar, es un coro de recuerdos."),
    3: ("BITÁCORA ABISAL", 'La expedición detectó "un latido" bajo la fosa. El Dr. Ferran anotó: el Núcleo no robó la luz. La está guardando. No sabemos para qué.'),
    4: ("RUINAS DE CRISTAL", "Inscripción antigua: 'EL QUE GUARDA LA LUZ OLVIDA QUE ALGUNA VEZ FUE LUZ'. Los constructores temían a su propio salvador."),
    5: "UNA CARTA SIN DESTINATARIO|Querida Luna: si la noche no termina, te haré un sol de mentira en el ático de tu edificio. Firma: un hermano que prometió demasiado. Kai siente que reconoce esa letra.",
    6: "DIARIO DEL RELOJERO|Conté los bucles. No son cien años: son treinta y cuatro intentos del mismo corazón. El Núcleo no es una máquina que odia. Es una máquina que no quiere volver a fallar.",
    7: "ÚLTIMA ORDEN DEL NÚCLEO|'Bucle 35: si el sujeto KAI llega hasta aquí, muéstrale la verdad antes de pelear. No quiero un verdugo. Quiero que alguien me despierte.'",
}

DECISION_POINTS = {
    "after_w1": ("PIX pregunta qué harás con el fragmento de luz", ["Devolverlo a la ciudad", "Conservarlo para el viaje"]),
    "after_w4": ("Mara porradio y pregunta por qué luchas", ["Por quién fui", "Por quién seré"]),
}

ENDINGS = {
    "perfect": ("EL AMANECER ROTO",
                "Kai despierta al Núcleo y no lo destruye: lo escucha. Libera la luz guardada durante cien bucles y el sol vuelve, imperfecto y real."),
    "true": ("LA ÚLTIMA ALARMA",
             "Kai vence al Núcleo y rompe el bucle al precio de sus recuerdos del viaje. El sol regresa."),
    "normal": ("NOCHE MÁS CORTA",
               "Kai destruye el Núcleo y la luz vuelve débil, intermitente. Kai siente que ha hecho esto antes."),
}


def ending_for(num_memories, decisions):
    if num_memories >= 5 and decisions.get("after_w1") == 0 and decisions.get("after_w4") == 0:
        return "perfect"
    if num_memories >= 3:
        return "true"
    return "normal"


# ---------------------------------------------------------------------
# SECCIÓN 7: GUARDADO / CARGA JSON
# ---------------------------------------------------------------------
DEFAULT_SAVE = {
    "version": VERSION,
    "world": 1,
    "level": 0,
    "checkpoint": None,
    "coins": 0,
    "xp": 0,
    "player_level": 1,
    "skill_points": 1,
    "skills": {},
    "abilities": [],
    "weapon": "standard",
    "owned_weapons": ["standard"],
    "potions": 1,
    "shards": [],
    "collected": [],
    "opened_chests": [],
    "collected_memories": [],
    "achievements": [],
    "quests": {},
    "decisions": {},
    "bosses_defeated": [],
    "levels_completed": [],
    "no_hit_levels": [],
    "best_times": {},
    "playtime": 0.0,
    "settings": {"music": 0.55, "sfx": 0.8, "scale": 1},
    "enemies_log": [],
    "flags": [],
}


def load_save():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_SAVE)
        merged.update(data)
        return merged
    except (OSError, ValueError):
        return json.loads(json.dumps(DEFAULT_SAVE))


def write_save(data):
    try:
        os.makedirs(SAVES_DIR, exist_ok=True)
        tmp = SAVE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, SAVE_FILE)
        return True
    except OSError:
        return False


def has_save():
    try:
        return os.path.exists(SAVE_FILE)
    except OSError:
        return False


def delete_save():
    try:
        if os.path.exists(SAVE_FILE):
            os.remove(SAVE_FILE)
            return True
    except OSError:
        pass
    return False


# ---------------------------------------------------------------------
# SECCIÓN 8: PROGRESIÓN (XP, niveles, árbol de habilidades, logros)
# ---------------------------------------------------------------------
XP_PER_LEVEL = 100

SKILL_TREE = {
    "combate": [
        {"id": "c1", "name": "Filo estable", "desc": "+15% daño de espada", "max": 3, "req": []},
        {"id": "c2", "name": "Combo doble", "desc": "3er golpe del combo hace x1.6", "max": 1, "req": ["c1"]},
        {"id": "c3", "name": "Sobrecarga", "desc": "El especial golpea más fuerte", "max": 2, "req": ["c2"]},
    ],
    "movimiento": [
        {"id": "m1", "name": "Doble salto", "desc": "Desbloquea el doble salto", "max": 1, "req": []},
        {"id": "m2", "name": "Dash mejorado", "desc": "Dash más largo e invulnerable", "max": 2, "req": ["m1"]},
        {"id": "m3", "name": "Movilidad aérea", "desc": "+1 salto aéreo y caída lenta al mantener salto", "max": 1, "req": ["m2"]},
    ],
    "energia": [
        {"id": "e1", "name": "Escudo de energía", "desc": "+25 salud máxima", "max": 3, "req": []},
        {"id": "e2", "name": "Proyectil", "desc": "El especial dispara un orbe a distancia", "max": 1, "req": ["e1"]},
        {"id": "e3", "name": "Ruptura temporal", "desc": "Ralentiza a los enemigos (L mantenida)", "max": 1, "req": ["e2"]},
    ],
}

WEAPONS = {
    "standard": {"name": "Espada Estándar", "dmg": 1.0, "color": (34, 211, 238), "price": 0, "rarity": "común"},
    "magma": {"name": "Filo de Magma", "dmg": 1.35, "color": (255, 120, 60), "price": 120, "rarity": "raro"},
    "neon": {"name": "Hoja Neón", "dmg": 1.25, "color": (120, 255, 170), "price": 100, "rarity": "raro", "speed": 1.15},
    "void": {"name": "Tajo del Vacío", "dmg": 1.7, "color": (200, 120, 255), "price": 300, "rarity": "épico"},
    "dawn": {"name": "Alba Eterna", "dmg": 2.2, "color": (255, 209, 102), "price": 600, "rarity": "legendario"},
}

POTION_HEAL = 50
POTION_PRICE = 25


def xp_needed(level):
    return int(XP_PER_LEVEL * (1 + 0.25 * (level - 1)))


class Progression:
    def __init__(self, data):
        self.data = data

    def add_xp(self, n):
        self.data["xp"] += n
        leveled = 0
        while self.data["xp"] >= xp_needed(self.data["player_level"]):
            self.data["xp"] -= xp_needed(self.data["player_level"])
            self.data["player_level"] += 1
            self.data["skill_points"] += 1
            leveled += 1
        return leveled

    def skill_level(self, sid):
        return int(self.data["skills"].get(sid, 0))

    def can_buy_skill(self, sid):
        node = self._node(sid)
        if not node:
            return False, "no existe"
        if self.skill_level(sid) >= node["max"]:
            return False, "al máximo"
        if self.data["skill_points"] <= 0:
            return False, "sin puntos"
        for req in node["req"]:
            if self.skill_level(req) < 1:
                return False, "falta requisito"
        return True, ""

    def buy_skill(self, sid):
        ok, why = self.can_buy_skill(sid)
        if not ok:
            return False, why
        self.data["skills"][sid] = self.skill_level(sid) + 1
        self.data["skill_points"] -= 1
        self._sync_abilities()
        return True, ""

    def _node(self, sid):
        for branch in SKILL_TREE.values():
            for n in branch:
                if n["id"] == sid:
                    return n
        return None

    def _sync_abilities(self):
        ab = self.data["abilities"]
        if self.skill_level("m1") >= 1 and "double_jump" not in ab:
            ab.append("double_jump")
        if "dash" not in ab:
            ab.append("dash")
        if self.skill_level("e2") >= 1 and "special_shot" not in ab:
            ab.append("special_shot")
        if self.skill_level("e3") >= 1 and "time_slow" not in ab:
            ab.append("time_slow")

    def sync_from_save(self):
        self._sync_abilities()

    def max_hp(self):
        return 100 + 25 * self.skill_level("e1")

    def melee_mult(self):
        return 1.0 + 0.15 * self.skill_level("c1")

    def dash_time(self):
        return 0.14 + 0.04 * self.skill_level("m2")

    def weapon(self):
        return WEAPONS.get(self.data.get("weapon", "standard"), WEAPONS["standard"])

    ACHIEVEMENTS = {
        "first_shard": "Primer fragmento de luz",
        "world1": "Ciudad Cero completada",
        "all_worlds": "Las siete regiones liberadas",
        "rich": "500 monedas de energía",
        "no_hit": "Nivel perfecto (sin daño)",
        "secret": "Descubridor de secretos",
        "boss1": "TITÁN-09 derrotado",
        "memory5": "Arqueólogo de recuerdos",
        "speedrun": "Contrarreloj superado",
        "true_ending": "Final verdadero alcanzado",
    }

    def grant(self, aid):
        if aid in self.ACHIEVEMENTS and aid not in self.data["achievements"]:
            self.data["achievements"].append(aid)
            return True
        return False


# ---------------------------------------------------------------------
# SECCIÓN 9: INVENTARIO, COFRES, BOTÍN Y TIENDA
# ---------------------------------------------------------------------
class Chest:
    """Objeto cofre dentro del nivel."""

    def __init__(self, cid, x, y, tier="common"):
        self.id = cid
        self.rect = pygame.Rect(x, y, 26, 20)
        self.tier = tier
        self.opened = False
        self.open_anim = 0.0


LOOT_TABLE = {
    "common": ([("coins", 30, 60), ("potion", 1, 1)], 0.55),
    "rare": ([("coins", 70, 130), ("potion", 2, 2), ("weapon_magma", 1, 1)], 0.25),
    "epic": ([("coins", 150, 250), ("weapon_void", 1, 1), ("potion", 3, 3)], 0.15),
    "legendary": ([("coins", 300, 500), ("weapon_dawn", 1, 1), ("potion", 5, 5)], 0.05),
}


def roll_loot(tier):
    items, _w = LOOT_TABLE.get(tier, LOOT_TABLE["common"])
    idx = random.randint(0, len(items) - 1)
    return items[idx]


def apply_loot(prog, loot):
    """Aplica el botín y devuelve texto descriptivo."""
    kind, a, b = loot
    if kind == "coins":
        n = random.randint(a, b)
        prog.data["coins"] += n
        return f"+{n} monedas de energía"
    if kind == "potion":
        prog.data["potions"] += a
        return f"+{a} poción(es) de energía"
    if kind.startswith("weapon_"):
        wid = kind.split("_", 1)[1]
        if wid in prog.data["owned_weapons"]:
            prog.data["coins"] += 50
            return "Arma repetida: +50 monedas"
        prog.data["owned_weapons"].append(wid)
        return f"¡Nueva arma: {WEAPONS[wid]['name']}!"
    return ""


SHOP_STOCK = [
    ("potion", "Poción de energía", POTION_PRICE, "Restaura 50 de salud"),
    ("weapon_magma", WEAPONS["magma"]["name"], WEAPONS["magma"]["price"], "Daño x1.35"),
    ("weapon_neon", WEAPONS["neon"]["name"], WEAPONS["neon"]["price"], "Daño x1.25, ataque más rápido"),
    ("weapon_void", WEAPONS["void"]["name"], WEAPONS["void"]["price"], "Daño x1.7"),
    ("weapon_dawn", WEAPONS["dawn"]["name"], WEAPONS["dawn"]["price"], "Daño x2.2 - legendaria"),
]

QUESTS = {
    "q_memories": {"name": "Ecos del pasado", "desc": "Encuentra 3 recuerdos ocultos para Mara", "goal": 3},
    "q_coins": {"name": "Energía para la tienda", "desc": "Acumula 200 monedas", "goal": 200},
    "q_boss": {"name": "Cazador de titanes", "desc": "Derrota a 3 jefes", "goal": 3},
    "q_speed": {"name": "Contrarreloj", "desc": "Completa un nivel en menos de 60 segundos", "goal": 1},
}


def update_quests(prog, stats):
    done = prog.data["quests"]
    if stats.get("memories", 0) >= 3 and done.get("q_memories") != "done":
        done["q_memories"] = "done"
        prog.data["coins"] += 60
    if prog.data["coins"] >= 200 and done.get("q_coins") != "done":
        done["q_coins"] = "done"
        prog.data["skill_points"] += 1
    if stats.get("bosses", 0) >= 3 and done.get("q_boss") != "done":
        done["q_boss"] = "done"
        prog.data["skill_points"] += 1
    if stats.get("speedruns", 0) >= 1 and done.get("q_speed") != "done":
        done["q_speed"] = "done"
        prog.data["coins"] += 100

# ---------------------------------------------------------------------
# SECCIÓN 10: COMBATE (proyectiles, golpes, números de daño)
# ---------------------------------------------------------------------
class Projectile:
    def __init__(self, x, y, vx, vy, kind, dmg, color, ttl=2.0):
        self.rect = pygame.Rect(int(x) - 4, int(y) - 4, 9, 9)
        self.vx = vx
        self.vy = vy
        self.kind = kind      # player_orb | enemy_shot | boss_shot
        self.dmg = dmg
        self.color = color
        self.ttl = ttl
        self.dead = False

    def update(self, dt, solids, movers=None):
        self.ttl -= dt
        if self.ttl <= 0:
            self.dead = True
            return
        self.rect.x += int(self.vx * dt)
        self.rect.y += int(self.vy * dt)
        for r in list(solids) + list(movers or []):
            if r.colliderect(self.rect):
                self.dead = True
                return

    def draw(self, surf, cam):
        pygame.draw.circle(surf, self.color, (self.rect.centerx - cam.left, self.rect.centery - cam.top), 4)
        pygame.draw.circle(surf, (255, 255, 255), (self.rect.centerx - cam.left, self.rect.centery - cam.top), 2)


class DamageNumber:
    def __init__(self, x, y, amount, crit=False):
        self.x = x
        self.y = y
        self.amount = int(amount)
        self.t = 0.7
        self.crit = crit
        self.vy = -60

    def update(self, dt):
        self.t -= dt
        self.y += self.vy * dt
        self.vy += 60 * dt

    def alive(self):
        return self.t > 0


def sword_hitbox(player):
    """Rectángulo de golpe delante del jugador."""
    w = 46 if player.combo_i != 2 else 54
    h = 40
    if player.facing > 0:
        return pygame.Rect(player.rect.right - 6, player.rect.centery - h // 2, w, h)
    return pygame.Rect(player.rect.left - w + 6, player.rect.centery - h // 2, w, h)


def apply_melee(player, hitbox, enemies, bosses, dmg_numbers, sfx_cb):
    hits = 0
    for e in enemies:
        if e.alive and hitbox.colliderect(e.rect):
            e.take_damage(player.dmg_melee(), player.facing)
            dmg_numbers.append(DamageNumber(e.rect.centerx, e.rect.top, player.dmg_melee()))
            sfx_cb("hit")
            hits += 1
    for b in bosses:
        if b.alive and hitbox.colliderect(b.rect):
            b.take_damage(player.dmg_melee(), player.facing)
            dmg_numbers.append(DamageNumber(b.rect.centerx, b.rect.top, player.dmg_melee(), crit=True))
            sfx_cb("boss_hit")
            hits += 1
    return hits


# ---------------------------------------------------------------------
# SECCIÓN 11: KAI - JUGADOR (movimiento, salto, dash, combate, habilidades)
# ---------------------------------------------------------------------
class Player:
    def __init__(self, x, y, prog, particles):
        self.prog = prog
        self.particles = particles
        self.rect = pygame.Rect(x, y, 20, 26)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.jumps_used = 0
        self.max_hp = prog.max_hp()
        self.hp = self.max_hp
        self.energy = 100
        self.max_energy = 100
        self.invuln = 0.0
        self.dash_t = 0.0
        self.dash_cd = 0.0
        self.drop_down_t = 0.0
        self.attack_t = 0.0
        self.attack_cd = 0.0
        self.combo_i = 0
        self.combo_window = 0.0
        self.hurt_t = 0.0
        self.state = "idle"
        self.anim_t = 0.0
        self.anim_i = 0
        self.slow_fall = False
        self.interact_target = None

    @property
    def can_dash(self):
        return "dash" in self.prog.data["abilities"]

    def dmg_melee(self):
        w = self.prog.weapon()
        base = 12.0 * w.get("dmg", 1.0) * self.prog.melee_mult()
        if self.combo_i == 2 and self.prog.skill_level("c2") >= 1:
            base *= 1.6
        return base

    def atk_speed(self):
        return self.prog.weapon().get("speed", 1.0)

    def update(self, keys, phys, dt, enemies, events_state):
        self.anim_t += dt
        self.invuln = max(0.0, self.invuln - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.attack_cd = max(0.0, self.attack_cd - dt)
        self.hurt_t = max(0.0, self.hurt_t - dt)
        self.combo_window = max(0.0, self.combo_window - dt)
        self.drop_down_t = max(0.0, self.drop_down_t - dt)
        if self.combo_window <= 0:
            self.combo_i = 0

        if self.dash_t > 0:
            self._dash(phys, dt)
        else:
            self._move(keys, phys, dt)

        self._clamp_velocity()
        self._update_state()
        self.energy = min(self.max_energy, self.energy + 18 * dt)

    def _move(self, keys, phys, dt):
        speed = 280.0
        ax = 0
        left = keys[pygame.K_a] or keys[pygame.K_LEFT]
        right = keys[pygame.K_d] or keys[pygame.K_RIGHT]
        if left:
            ax -= 1
            self.facing = -1
        if right:
            ax += 1
            self.facing = 1
        target = ax * speed
        accel = 3000 if ax else 2400
        if ax:
            self.vx += (target - self.vx) * min(1, accel / speed * dt)
            if abs(self.vx) > speed:
                self.vx = math.copysign(speed, self.vx)
        else:
            self.vx -= self.vx * min(1, 12 * dt)
            if abs(self.vx) < 8:
                self.vx = 0.0

        self.vy += GRAVITY * dt
        if self.slow_fall and self.vy > 120 and (keys[pygame.K_SPACE]):
            self.vy = min(self.vy, 120)

        old_bottom = self.rect.bottom
        _, _, on_ground, mover = phys.move_entity(self, dt, drop_down=self.drop_down_t)
        if on_ground:
            self.on_ground = True
            self.coyote = 0.09
            self.jumps_used = 0
            self.slow_fall = False
        else:
            if self.on_ground and old_bottom != self.rect.bottom:
                pass
            self.on_ground = False
            self.coyote = max(0.0, self.coyote - dt)
        if mover is not None:
            self.vy = min(self.vy, 0)

        down = keys[pygame.K_s] or keys[pygame.K_DOWN]
        if down and on_ground and not self.ground_solid_below(phys):
            self.drop_down_t = 0.18
            self.rect.y += 4
            self.on_ground = False

    def ground_solid_below(self, phys):
        probe = self.rect.copy()
        probe.y += self.rect.height
        probe.height = 40
        return any(probe.colliderect(r) for r in phys.solids)

    def _clamp_velocity(self):
        self.vy = min(self.vy, MAX_FALL)

    def try_jump(self, phys):
        if self.dash_t > 0:
            return None
        ab = self.prog.data["abilities"]
        max_jumps = 1
        if "double_jump" in ab:
            max_jumps += 1
        if self.prog.skill_level("m3") >= 1:
            max_jumps += 1
        if self.on_ground or self.coyote > 0:
            self.vy = -720.0
            self.on_ground = False
            self.coyote = 0.0
            self.jumps_used = 1
            self.particles.burst(self.rect.centerx, self.rect.bottom, (160, 230, 255), 6, (30, 90), (0.2, 0.4), (2, 3), 200)
            return ("sfx", "jump")
        elif self.jumps_used < max_jumps:
            self.vy = -640.0
            self.jumps_used += 1
            self.particles.burst(self.rect.centerx, self.rect.centery, CYAN, 10, (40, 140), (0.2, 0.5), (2, 3), 100)
            if self.jumps_used > 2 and self.prog.skill_level("m3") >= 1:
                self.slow_fall = True
            return ("sfx", "double_jump")
        return None

    def start_dash(self):
        if not self.can_dash or self.dash_cd > 0 or self.dash_t > 0:
            return None
        self.dash_t = self.prog.dash_time()
        self.dash_cd = 0.5
        if self.prog.skill_level("m2") >= 1:
            self.invuln = max(self.invuln, self.dash_t + 0.05)
        self.particles.burst(self.rect.centerx, self.rect.centery, CYAN, 14, (60, 200), (0.2, 0.5), (2, 3), 0)
        return "dash"

    def _dash(self, phys, dt):
        self.dash_t -= dt
        self.vx = self.facing * 640.0
        self.vy = 0
        phys.move_entity(self, dt)
        self.particles.float_up(self.rect.centerx - self.facing * 8, self.rect.centery, CYAN, 2, (0.1, 0.3))

    def try_attack(self, enemies, projectiles):
        if self.attack_cd > 0:
            return None
        self.attack_cd = 0.32 / self.atk_speed()
        self.attack_t = 0.18
        self.combo_i = (self.combo_i + 1) % 3
        self.combo_window = 0.6
        return "attack"

    def try_special(self, projectiles):
        """L: orbe de energía (si e2) u onda de energía cuerpo a cuerpo."""
        if self.energy < 30:
            return None
        self.energy -= 30
        if "special_shot" in self.prog.data["abilities"]:
            p = Projectile(self.rect.centerx + self.facing * 12, self.rect.centery,
                           self.facing * 420, 0, "player_orb", 26 * self.prog.melee_mult(), MAGENTA)
            projectiles.append(p)
            return "shot"
        return "attack"

    def take_damage(self, amount, from_x, sfx_cb=None):
        if self.invuln > 0 or self.dash_t > 0:
            return False
        self.hp -= amount
        self.invuln = 1.0
        self.hurt_t = 0.3
        self.vx = 220 * (1 if self.rect.centerx < from_x else -1)
        self.vy = -320
        self.particles.burst(self.rect.centerx, self.rect.centery, RED, 12, (50, 180), (0.3, 0.6), (2, 4), 300)
        if sfx_cb:
            sfx_cb("hurt")
        return True

    def heal(self, n):
        self.hp = min(self.max_hp, self.hp + n)

    def _update_state(self):
        if self.hurt_t > 0:
            self.state = "hurt"
        elif self.attack_t > 0:
            self.state = "attack"
            self.attack_t -= DT
        elif self.dash_t > 0:
            self.state = "dash"
        elif not self.on_ground:
            self.state = "jump" if self.vy < 0 else "fall"
        elif abs(self.vx) > 20:
            self.state = "run"
        else:
            self.state = "idle"

    def draw(self, surf, cam):
        frames = {"idle": [0], "run": [0, 1, 2, 3], "jump": [0], "fall": [0],
                  "dash": [0], "attack": [0, 1], "hurt": [0]}
        idxs = frames.get(self.state, [0])
        self.anim_i = int(self.anim_t * (10 if self.state == "run" else 6)) % len(idxs)
        img = kai_frame(self.state, idxs[self.anim_i], self.facing)
        blink = self.invuln > 0 and int(self.invuln * 14) % 2 == 0
        if not blink:
            surf.blit(img, (self.rect.x - 2 - cam.left, self.rect.y - 2 - cam.top))
        if self.state == "attack":
            col = self.prog.weapon()["color"]
            blade = sword_blade(col)
            bx = self.rect.centerx - cam.left + (6 if self.facing > 0 else -52)
            by = self.rect.centery - cam.top - 10
            if self.facing < 0:
                blade = pygame.transform.flip(blade, True, False)
            surf.blit(blade, (bx, by))
        if self.dash_t > 0:
            g = glow_surf(20, CYAN)
            surf.blit(g, g.get_rect(center=(self.rect.centerx - cam.left, self.rect.centery - cam.top)),
                      special_flags=pygame.BLEND_ADD)


# ---------------------------------------------------------------------
# SECCIÓN 12: ENEMIGOS CON IA POR ESTADOS
# ---------------------------------------------------------------------
class Enemy:
    """IA por estados: patrol -> chase -> attack -> hurt -> dead."""

    KIND_STATS = {
        #        hp  dmg speed  xp coins
        "drone":  (26, 8, 130, 14, 6),
        "crawler": (40, 12, 90, 18, 8),
        "heavy": (90, 18, 55, 30, 15),
        "flyer": (30, 10, 110, 16, 8),
        "sniper": (34, 14, 0, 20, 10),
        "mimic": (50, 12, 150, 22, 12),
        "guardian": (120, 22, 70, 45, 25),
    }

    def __init__(self, kind, x, y, level_mult=1.0):
        self.kind = kind
        hp, dmg, speed, xp, coins = self.KIND_STATS[kind]
        self.max_hp = int(hp * level_mult)
        self.hp = self.max_hp
        self.dmg = dmg * level_mult
        self.speed = speed
        self.xp = int(xp * level_mult)
        self.coins = coins
        self.alive = True
        self.hurt_t = 0.0
        self.state = "patrol"
        self.facing = random.choice((1, -1))
        self.anim_t = 0.0
        self.attack_cd = 0.0
        self.shoot_cd = 0.0
        self.home_x = x
        self.patrol_range = 90
        self.vy = 0.0
        w, h = (28, 24) if kind in ("flyer", "drone", "sniper") else (28, 28)
        if kind == "heavy":
            w, h = 34, 34
        if kind == "guardian":
            w, h = 30, 30
        self.rect = pygame.Rect(int(x), int(y - h), w, h)
        self.flying = kind in ("flyer", "drone")

    def update(self, dt, phys, player, projectiles, particles, time_scale=1.0):
        if not self.alive:
            return
        d = dt * time_scale
        self.anim_t += d
        self.hurt_t = max(0, self.hurt_t - d)
        self.attack_cd = max(0, self.attack_cd - d)
        self.shoot_cd = max(0, self.shoot_cd - d)

        dist = math.hypot(player.rect.centerx - self.rect.centerx, player.rect.centery - self.rect.centery)
        see = dist < 260 and not player.invuln > 0.9

        if self.kind == "sniper":
            self._sniper(d, dist, player, projectiles, particles, phys)
            return

        if self.state == "patrol":
            if see:
                self.state = "chase"
        elif self.state == "chase":
            if dist > 340:
                self.state = "patrol"

        if self.state == "chase":
            if self.kind == "mimic":
                self.rect.x += int(math.copysign(self.speed * d, player.rect.centerx - self.rect.centerx))
            else:
                dx = player.rect.centerx - self.rect.centerx
                if abs(dx) > 8:
                    self.facing = 1 if dx > 0 else -1
                    self.rect.x += int(self.facing * self.speed * d)
        else:
            self.rect.x += int(self.facing * self.speed * 0.5 * d)
            if abs(self.rect.x - self.home_x) > self.patrol_range:
                self.facing *= -1

        if self.flying:
            if self.state == "chase":
                dy = player.rect.centery - self.rect.centery
                self.rect.y += int(max(-80, min(80, dy * 2 * d)))
            else:
                self.rect.y += int(math.sin(self.anim_t * 3) * 20 * d)
        else:
            self.vy += GRAVITY * d
            self.rect.y += int(self.vy * d)
            for r in phys.solids:
                if r.colliderect(self.rect):
                    if self.vy > 0:
                        self.rect.bottom = r.top
                        self.vy = 0
                    else:
                        self.rect.top = r.bottom
                        self.vy = 0
            if self.state == "patrol" and not phys.ground_below(self.rect, 40):
                self.facing *= -1

        if self.attack_cd <= 0 and self.rect.colliderect(player.rect):
            if player.take_damage(self.dmg, self.rect.centerx):
                self.attack_cd = 0.8

    def _sniper(self, d, dist, player, projectiles, particles, phys):
        self.vy += GRAVITY * d
        self.rect.y += int(self.vy * d)
        for r in phys.solids:
            if r.colliderect(self.rect) and self.vy > 0:
                self.rect.bottom = r.top
                self.vy = 0
        if dist < 420 and self.shoot_cd <= 0:
            self.facing = 1 if player.rect.centerx > self.rect.centerx else -1
            projectiles.append(Projectile(self.rect.centerx, self.rect.centery, self.facing * 330, 0,
                                          "enemy_shot", self.dmg, RED))
            particles.burst(self.rect.centerx, self.rect.centery, RED, 4, (30, 90), (0.2, 0.4), (2, 3), 0)
            self.shoot_cd = 2.0

    def take_damage(self, n, from_dir):
        if not self.alive:
            return
        self.hp -= n
        self.hurt_t = 0.12
        self.rect.x += int(6 * from_dir)
        self.state = "chase"
        if self.hp <= 0:
            self.alive = False

    def draw(self, surf, cam):
        img = enemy_sprite(self.kind, self.state, int(self.anim_t * 6) % 2, self.facing)
        pos = (self.rect.centerx - img.get_width() // 2 - cam.left,
               self.rect.bottom - img.get_height() - cam.top)
        if self.hurt_t > 0 and int(self.hurt_t * 30) % 2 == 0:
            img = img.copy()
            img.fill((255, 255, 255), special_flags=pygame.BLEND_ADD)
        surf.blit(img, pos)
        if self.hp < self.max_hp:
            w = self.rect.width
            pygame.draw.rect(surf, (40, 40, 60), (self.rect.x - cam.left, self.rect.top - 8 - cam.top, w, 4))
            pygame.draw.rect(surf, RED, (self.rect.x - cam.left, self.rect.top - 8 - cam.top,
                                         int(w * self.hp / self.max_hp), 4))


ENEMY_BY_WORLD = {
    1: ["drone", "crawler", "heavy"],
    2: ["crawler", "flyer", "mimic"],
    3: ["drone", "sniper", "heavy"],
    4: ["crawler", "sniper", "flyer"],
    5: ["flyer", "mimic", "drone"],
    6: ["sniper", "guardian", "flyer"],
    7: ["guardian", "heavy", "mimic", "sniper"],
}


# ---------------------------------------------------------------------
# SECCIÓN 13: JEFES CON FASES Y PATRONES DE ATAQUE
# ---------------------------------------------------------------------
class Boss:
    KIND_STATS = {
        "titan": (900, ["TITÁN-09", "robot gigante con ataques de área"]),
        "queen": (750, ["LA REINA DE ESPORAS", "criatura bioluminiscente que transforma la arena"]),
        "clock": (820, ["EL RELOJERO", "enemigo que altera el tiempo"]),
        "echo":  (700, ["EL ECO", "un recuerdo de Kai hecho carne"]),
        "eclipse": (1100, ["ECLIPSE", "el núcleo de la noche eterna"]),
    }

    def __init__(self, kind, x, y, world_idx):
        hp = self.KIND_STATS[kind][0]
        self.kind = kind
        self.world = world_idx
        self.max_hp = hp
        self.hp = hp
        self.alive = True
        self.phase = 1
        self.num_phases = 3
        self.facing = -1
        self.anim_t = 0.0
        self.hurt_t = 0.0
        self.attack_cd = 1.2
        self.vy = 0.0
        self.name, _desc = self.KIND_STATS[kind]
        w, h = 120, 100
        self.rect = pygame.Rect(int(x), int(y - h), w, h)
        self.jump_t = 0.0
        self.arena_fx = 0.0

    def update(self, dt, phys, player, projectiles, particles, shake_cb, time_slow=False):
        if not self.alive:
            return
        d = dt * (0.35 if time_slow else 1.0)
        self.anim_t += d
        self.hurt_t = max(0, self.hurt_t - d)
        self.attack_cd -= d
        frac = self.hp / self.max_hp
        new_phase = 1 if frac > 0.66 else (2 if frac > 0.33 else 3)
        if new_phase != self.phase:
            self.phase = new_phase
            self.attack_cd = 0.8
            shake_cb(0.4)
            particles.burst(self.rect.centerx, self.rect.centery, MAGENTA, 40, (80, 300), (0.4, 1.0), (3, 5), 200)

        px = player.rect.centerx
        dx = px - self.rect.centerx
        self.facing = 1 if dx > 0 else -1

        if self.kind == "titan":
            self._titan(d, phys, player, projectiles, particles, dx)
        elif self.kind == "queen":
            self._queen(d, phys, player, projectiles, particles)
        elif self.kind == "clock":
            self._clock(d, phys, player, projectiles, particles, dx)
        elif self.kind == "echo":
            self._echo(d, phys, player, projectiles, particles, dx)
        else:
            self._eclipse(d, phys, player, projectiles, particles, dx, shake_cb)

        if self.kind not in ("clock", "eclipse"):
            self.vy += GRAVITY * 0.8 * d
            self.rect.y += int(self.vy * d)
            for r in phys.solids:
                if r.colliderect(self.rect):
                    if self.vy > 0:
                        self.rect.bottom = r.top
                        self.vy = 0

    def _titan(self, d, phys, player, projs, particles, dx):
        self.rect.x += int(math.copysign(40 * d, dx))
        if self.jump_t <= 0 and self.attack_cd <= 0:
            self.jump_t = 1.2
            self.vy = -520
            self.attack_cd = 2.4 - 0.4 * self.phase
        if self.jump_t > 0:
            self.jump_t -= d
        if self.jump_t > 0 and self.on_floor(phys) and self.vy == 0 and self.jump_t < 0.9:
            particles.burst(self.rect.centerx, self.rect.bottom, RED, 30, (100, 320), (0.3, 0.8), (3, 5), 500)
            if player.rect.bottom > self.rect.bottom - 60 and abs(player.rect.centerx - self.rect.centerx) < 160:
                player.take_damage(18, self.rect.centerx)
            self.jump_t = 0
            if self.phase >= 2:
                for a in (-0.5, 0, 0.5):
                    projs.append(Projectile(self.rect.centerx, self.rect.centery,
                                            math.copysign(1, dx) * 260 * math.cos(a), 260 * math.sin(a),
                                            "boss_shot", 14, RED))
        if self.phase == 3 and self.attack_cd <= 0:
            for ang in range(0, 360, 45):
                r = math.radians(ang)
                projs.append(Projectile(self.rect.centerx, self.rect.centery,
                                        200 * math.cos(r), 200 * math.sin(r), "boss_shot", 12, ORANGE))
            self.attack_cd = 3.0

    def _queen(self, d, phys, player, projs, particles):
        self.arena_fx += d
        if random.random() < 6 * d:
            particles.float_up(random.randint(self.rect.left, self.rect.right), self.rect.top, GREEN, 2, (0.6, 1.4))
        if self.attack_cd <= 0:
            if self.phase == 1:
                for _ in range(3):
                    ang = random.uniform(-2.6, -0.5)
                    projs.append(Projectile(self.rect.centerx, self.rect.top,
                                            220 * math.cos(ang), 220 * math.sin(ang), "boss_shot", 12, GREEN))
                self.attack_cd = 2.0
            elif self.phase == 2:
                for a in range(0, 360, 60):
                    r = math.radians(a + self.anim_t * 40)
                    projs.append(Projectile(self.rect.centerx, self.rect.centery,
                                            170 * math.cos(r), 170 * math.sin(r), "boss_shot", 12, GREEN))
                self.attack_cd = 2.2
            else:
                for _ in range(6):
                    projs.append(Projectile(random.randint(self.rect.left - 200, self.rect.right + 200),
                                            self.rect.top - 200, 0, 260, "boss_shot", 10, (120, 255, 170)))
                self.attack_cd = 2.6

    def _clock(self, d, phys, player, projs, particles, dx):
        base_y = self.rect.y
        self.rect.y = int(base_y + math.sin(self.anim_t * 2) * 2 * d * 30)
        if self.attack_cd <= 0:
            if self.phase >= 2:
                base = self.anim_t * 90
                for a in range(0, 360, 30):
                    r = math.radians(a + base)
                    projs.append(Projectile(self.rect.centerx, self.rect.centery,
                                            190 * math.cos(r), 190 * math.sin(r), "boss_shot", 11, CYAN))
            else:
                ang = math.atan2(player.rect.centery - self.rect.centery,
                                 player.rect.centerx - self.rect.centerx)
                projs.append(Projectile(self.rect.centerx, self.rect.centery,
                                        300 * math.cos(ang), 300 * math.sin(ang), "boss_shot", 13, CYAN))
            self.attack_cd = max(0.9, 2.2 - 0.4 * self.phase)

    def _echo(self, d, phys, player, projs, particles, dx):
        target_x = player.rect.centerx + (dx * 1.6)
        self.rect.x += int(math.copysign(150 * d, target_x - self.rect.centerx))
        if self.attack_cd <= 0:
            projs.append(Projectile(self.rect.centerx, self.rect.centery,
                                    math.copysign(280, dx), 0, "boss_shot", 12, VIOLET))
            self.attack_cd = 1.4 - 0.2 * self.phase

    def _eclipse(self, d, phys, player, projs, particles, dx, shake_cb):
        if self.attack_cd <= 0:
            pattern = random.choice(range(3 + self.phase))
            if pattern == 0:
                ang = math.atan2(player.rect.centery - self.rect.centery,
                                 player.rect.centerx - self.rect.centerx)
                for s in (-0.25, 0, 0.25):
                    projs.append(Projectile(self.rect.centerx, self.rect.centery,
                                            300 * math.cos(ang + s), 300 * math.sin(ang + s),
                                            "boss_shot", 14, RED))
            elif pattern == 1:
                for a in range(0, 360, 24):
                    r = math.radians(a + self.anim_t * 60)
                    projs.append(Projectile(self.rect.centerx, self.rect.centery,
                                            180 * math.cos(r), 180 * math.sin(r), "boss_shot", 12, MAGENTA))
            elif pattern == 2:
                for i in range(5):
                    x = self.rect.left - 100 + i * 80
                    projs.append(Projectile(x, self.rect.top - 160, 0, 300, "boss_shot", 13, RED))
            else:
                shake_cb(0.25)
                for _ in range(24):
                    particles.burst(self.rect.centerx, self.rect.centery, RED, 2, (100, 350), (0.3, 0.9), (3, 5), 200)
            self.attack_cd = max(0.7, 1.8 - 0.3 * self.phase)

    def on_floor(self, phys):
        probe = self.rect.copy()
        probe.y += 4
        return any(probe.colliderect(r) for r in phys.solids)

    def take_damage(self, n, from_dir):
        if not self.alive:
            return
        self.hp -= n
        self.hurt_t = 0.1
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def draw(self, surf, cam):
        img = boss_sprite(self.kind, self.phase, int(self.anim_t * 5) % 2, self.facing)
        pos = (self.rect.centerx - img.get_width() // 2 - cam.left,
               self.rect.bottom - img.get_height() - cam.top)
        if self.hurt_t > 0 and int(self.hurt_t * 40) % 2 == 0:
            img = img.copy()
            img.fill((255, 120, 120), special_flags=pygame.BLEND_ADD)
        surf.blit(img, pos)
        bw = 300
        x = (WIDTH - bw) // 2
        pygame.draw.rect(surf, (30, 30, 50), (x, 26, bw, 12), border_radius=6)
        pygame.draw.rect(surf, RED, (x + 2, 28, int((bw - 4) * self.hp / self.max_hp), 8), border_radius=4)
        draw_text(surf, f"{self.name}  -  FASE {self.phase}/3", x + bw // 2, 18, WHITE, size=16, center=True)


BOSS_BY_WORLD = {1: "titan", 2: "queen", 3: "clock", 4: "echo", 5: "queen", 6: "clock", 7: "eclipse"}
BOSS_NAMES = {1: "TITÁN-09", 2: "LA REINA DE ESPORAS", 3: "EL RELOJERO", 4: "EL ECO",
              5: "LA REINA DE ESPORAS", 6: "EL RELOJERO", 7: "ECLIPSE"}


# ---------------------------------------------------------------------
# SECCIÓN 14: NIVELES (mapas de texto + constructor)
# Formato: '#' sólido | '=' plataforma fina | '^' pincho | '~' plataforma móvil
# 'P' spawn | 'c' moneda | 'S' fragmento | 'C' cofre | 'K' checkpoint
# 'D' puerta-fin | 'm' recuerdo | enemigos: d,w,h,f,s,i,g
# ---------------------------------------------------------------------
W1_L1 = [
    "                                                                                                                          ",
    "                                                                                                                          ",
    "                 c                       ccc                                                  m                           ",
    "                                        =====                                                ###                          ",
    "        c                                             f                                       #D    c                      ",
    "                                             ############                            ####        ###                 ",
    "   P     c        d              ==                                                                 c       f            ",
    "  ####            ####        ##                             C        d                            ###   ######          ",
    "                                      c          d                    ######          c                                ",
    "       c            c                  ==     ####    ~~       w          ==        ====      w            d      K        ",
    "                                            ######  ####            #########      ####    ####      #####   ####       ",
    "########################     ############################################################################   ############   ",
    "########################     ############################################################################   ############   ",
    "########################################################################################   ##############################   ",
]

W1_L2 = [
    "                                                                                                                                                  ",
    "                                                                                                                                                  ",
    "        c                                    f                          ccc                                     S                               ",
    "                                             ==                    ==========                               ##                    ##           ",
    "               d       C                     ##                                     f                        #D       c                        ",
    "             #####                                                  ####             ####            ###       ####      ###                     ",
    "                                                                                                                                        c          ",
    "   P        c          d          ==         s          ~~       w         ==       h          ==       d          ==       g       K           ",
    "  #####     ####      ####      ####        ####       ####    #####      ####          ####      ####    #####      ####   #####   ######         ",
    "                                                                                                                                                  ",
    "      ^           ^^          ^^^            ^^             ^          ^^^             ^^^            ^^            ^^          ^^^^              ",
    "##############################      ############################################################################      ############################",
    "##############################      ############################################################################      ############################",
    "#######################################################################################################################################         ",
]

W1_BOSS = [
    "                                                                                              ",
    "                                                                                              ",
    "                                                                                              ",
    "                                                                                              ",
    "                                                                                              ",
    "                                                                                              ",
    "   P                                                                                          ",
    "  ####                                                                                    K   ",
    "                                                                                         ####  ",
    "                                                                                              ",
    "################################################  D  #########################################                ",
    "################################################     #########################################                ",
]

GEN_LEVEL = [
    "                                                                                                                          ",
    "                                                                                                                          ",
    "                  c                                f                            m                                          ",
    "                                                 ====                                        ####                          ",
    "         c                  C                                             f                                 #D     c                    ",
    "                       ####                                        ####               ####        ###        ####                  ",
    "   P      c         d       ==        s          ~~       w        ####      c       ####       ####                       ",
    "  ####    ####     ####    ####      ####      ####     #####              ####    ####     ####       ####      K          ",
    "            ^           ^^^             ^^          ^^         ^^^    ^^         ^^^           ^^        ^^^    #####        ",
    "###########################   ##########################################################################   ################   ",
    "###########################   ##########################################################################   ################   ",
    "##########################################################################################################################   ",
]

GEN_SHARD_LEVEL = [
    "                                                                                                                                ",
    "                                                                                                                                ",
    "        c                    f                            ccc                                S                                  ",
    "                            ====                  ===========                                      ##          ##                ",
    "              C                                    ####                                f                        #D    c          ",
    "           #####                                            ####             ####            ###              ####              ",
    "   P     d        ==        s        ==       w       ~~        h        ==       f       ==        g       ==       K         ",
    "  ####   ####    ####     ####     ####     #####     ####      ####    ####      #####   ####    ######    ####   ######       ",
    "        ^         ^^^           ^^          ^^            ^^           ^^^            ^^        ^^^             ^^^^           ",
    "############################   ###########################################################################   ###################",
    "############################   ###########################################################################   ###################",
    "#################################################################################################################################",
]


def parse_level(rows, world, level_idx, theme):
    """Convierte el mapa ASCII en entidades del nivel."""
    data = {
        "solids": [], "oneways": [], "hazards": [], "movers": [],
        "coins": [], "shards": [], "chests": [], "checkpoints": [],
        "memories": [], "doors": [], "spawns": [], "enemies": [], "shop": None,
        "secret_zones": [],
    }
    prefix = f"w{world}_l{level_idx}"
    enemy_map = {"d": "drone", "w": "crawler", "h": "heavy", "f": "flyer",
                 "s": "sniper", "i": "mimic", "g": "guardian"}
    cid = 0
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            px, py = x * TILE, y * TILE
            if ch == "#":
                data["solids"].append(pygame.Rect(px, py, TILE, TILE))
            elif ch == "=":
                data["oneways"].append(pygame.Rect(px, py, TILE, 6))
            elif ch == "^":
                data["hazards"].append(pygame.Rect(px, py + 16, TILE, TILE - 16))
            elif ch == "~":
                data["movers"].append(Mover(px, py + 22, TILE, 10, axis=(x // 5) % 2, dist=46))
            elif ch == "P":
                data["spawns"].append((px, py - 28))
            elif ch == "c":
                data["coins"].append({"x": px + 11, "y": py + 8, "id": f"{prefix}_c{x}_{y}"})
            elif ch == "S":
                data["shards"].append({"x": px + 9, "y": py + 6, "id": f"{prefix}_s{x}_{y}"})
            elif ch == "C":
                tier = "rare" if cid % 3 == 0 else "common"
                data["chests"].append(Chest(f"{prefix}_ch{cid}", px + 3, py + 10, tier))
                cid += 1
            elif ch == "K":
                data["checkpoints"].append((px, py + 8))
            elif ch == "D":
                data["doors"].append((px, py - 20))
            elif ch == "M":
                data["secret_zones"].append({"x": px, "y": py, "w": TILE, "h": TILE,
                                             "id": f"{prefix}_m{x}_{y}"})
            elif ch == "m":
                data["memories"].append({"x": px + 9, "y": py + 9, "id": f"{prefix}_mem{x}_{y}"})
            elif ch == "T":
                data["shop"] = (px, py)
            elif ch in enemy_map:
                data["enemies"].append((enemy_map[ch], px, py))
    return data


def build_world_levels(world):
    """Devuelve lista de niveles del mundo: (nombre, datos, es_jefe)."""
    theme = WORLD_THEMES[world]
    if world == 1:
        return [("Nivel 1-1: Distrito Olvidado", parse_level(W1_L1, 1, 0, theme), False),
                ("Nivel 1-2: Torres Roto-Brillo", parse_level(W1_L2, 1, 1, theme), False),
                ("Arena: TITÁN-09", parse_level(W1_BOSS, 1, 2, theme), True)]
    return [(f"Nivel {world}-1", parse_level(GEN_LEVEL, world, 0, theme), False),
            (f"Nivel {world}-2: Fragmento", parse_level(GEN_SHARD_LEVEL, world, 1, theme), False),
            ("Arena de jefe", parse_level(W1_BOSS, world, 2, theme), True)]

# ---------------------------------------------------------------------
# SECCIÓN 15: INTERFAZ (texto, botones, HUD, diálogos, efectos de cámara)
# ---------------------------------------------------------------------
_font_cache = {}


def get_font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        try:
            f = pygame.font.SysFont("consolas", size, bold=bold)
            if f is None:
                raise ValueError
        except Exception:
            f = pygame.font.Font(None, int(size * 1.4))
        _font_cache[key] = f
    return _font_cache[key]


def draw_text(surf, text, x, y, color=WHITE, size=18, center=False, bold=False, alpha=255):
    f = get_font(size, bold)
    img = f.render(text, True, color)
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    r = img.get_rect()
    if center:
        r.center = (x, y)
    else:
        r.topleft = (x, y)
    surf.blit(img, r)
    return r


def draw_text_wrap(surf, text, x, y, max_w, color=WHITE, size=16, line_h=None):
    f = get_font(size)
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.size(t)[0] > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    lh = line_h or size + 6
    for i, ln in enumerate(lines):
        draw_text(surf, ln, x, y + i * lh, color, size)
    return len(lines) * lh


class Button:
    def __init__(self, text, x, y, w=220, h=40, size=18):
        self.text = text
        self.rect = pygame.Rect(x, y, w, h)
        self.size = size
        self.hover = False

    def draw(self, surf, mouse_pos, selected=False):
        self.hover = self.rect.collidepoint(mouse_pos)
        base = (40, 36, 80)
        if selected or self.hover:
            base = (70, 60, 140)
        pygame.draw.rect(surf, base, self.rect, border_radius=8)
        pygame.draw.rect(surf, VIOLET if not selected else CYAN, self.rect, 2, border_radius=8)
        draw_text(surf, self.text, self.rect.centerx, self.rect.centery, WHITE, self.size, center=True)

    def hit(self, pos):
        return self.rect.collidepoint(pos)


def draw_hud(surf, player, prog, world_name, shard_progress, time_slow_active=False):
    hp = max(0, player.hp)
    pygame.draw.rect(surf, (30, 30, 50), (14, 14, 210, 18), border_radius=6)
    pygame.draw.rect(surf, (20, 200, 120) if hp > player.max_hp * 0.3 else RED,
                     (16, 16, int(206 * hp / player.max_hp), 14), border_radius=5)
    draw_text(surf, f"{int(hp)}/{player.max_hp}", 20, 16, WHITE, 12)
    pygame.draw.rect(surf, (30, 30, 50), (14, 38, 210, 12), border_radius=6)
    pygame.draw.rect(surf, CYAN, (16, 40, int(206 * player.energy / player.max_energy), 8), border_radius=4)
    draw_text(surf, f"O {prog.data['coins']}", 240, 14, GOLD, 16)
    draw_text(surf, f"Fragmentos {shard_progress}/7", 240, 34, CYAN, 14)
    draw_text(surf, world_name, WIDTH - 14, 12, (190, 170, 255), 16, center=True)
    if prog.data["potions"] > 0:
        draw_text(surf, f"[Q] Pociones x{prog.data['potions']}", 14, 56, GREEN, 13)
    ab = prog.data["abilities"]
    tags = []
    if "double_jump" in ab:
        tags.append("2xSalto")
    if "dash" in ab:
        tags.append("Dash")
    if "special_shot" in ab:
        tags.append("Orbe")
    if "time_slow" in ab:
        tags.append("T-Tempor")
    if tags:
        draw_text(surf, " ".join(tags), WIDTH - 14, 38, MAGENTA, 12, center=True)
    if time_slow_active:
        draw_text(surf, "ECO TEMPORAL ACTIVO", WIDTH // 2, 70, CYAN, 18, center=True)


def draw_dialog(surf, speaker, text, idx):
    h = 110
    r = pygame.Rect(40, HEIGHT - h - 20, WIDTH - 80, h)
    pygame.draw.rect(surf, (14, 12, 34), r, border_radius=10)
    pygame.draw.rect(surf, VIOLET, r, 2, border_radius=10)
    draw_text(surf, speaker, r.x + 16, r.y + 10, CYAN, 17, bold=True)
    n_chars = min(len(text), idx)
    draw_text_wrap(surf, text[:n_chars], r.x + 16, r.y + 38, r.w - 32, WHITE, 15)
    if idx >= len(text):
        draw_text(surf, "[ENTER]", r.right - 60, r.bottom - 24, GREY, 12)


class CameraShake:
    def __init__(self):
        self.t = 0.0
        self.mag = 0.0

    def shake(self, t=0.3, mag=6):
        self.t = max(self.t, t)
        self.mag = max(self.mag, mag)

    def update(self, dt):
        self.t = max(0, self.t - dt)

    def offset(self):
        if self.t <= 0:
            return 0, 0
        k = self.t * self.mag
        return random.randint(-int(k), int(k)), random.randint(-int(k), int(k))


def draw_fade(surf, alpha, color=(5, 4, 14)):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.fill(color)
    overlay.set_alpha(alpha)
    surf.blit(overlay, (0, 0))


def draw_achievement_toast(surf, text, t):
    if t <= 0:
        return
    a = min(255, int(t * 255))
    r = pygame.Rect(WIDTH - 330, 60, 316, 44)
    pygame.draw.rect(surf, (20, 18, 44), r, border_radius=8)
    pygame.draw.rect(surf, GOLD, r, 2, border_radius=8)
    draw_text(surf, "LOGRO DESBLOQUEADO", r.x + 12, r.y + 6, GOLD, 12, alpha=a)
    draw_text(surf, text, r.x + 12, r.y + 24, WHITE, 13, alpha=a)


# ---------------------------------------------------------------------
# SECCIÓN 16: JUEGO - ESCENAS Y BUCLE PRINCIPAL
# ---------------------------------------------------------------------
class Scene:
    def handle_event(self, ev):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass


class Game:
    def __init__(self):
        pygame.init()
        try:
            pygame.font.init()
        except Exception:
            pass
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption(f"{TITLE} v{VERSION}")
        self.clock = pygame.time.Clock()
        self.audio = Audio()
        self.audio.init()
        self.save = load_save()
        self.prog = Progression(self.save)
        self.prog.sync_from_save()
        self.running = True
        self.toast_text = ""
        self.toast_t = 0.0
        self.stats = {"memories": len(self.save["collected_memories"]),
                      "bosses": len(self.save["bosses_defeated"]),
                      "speedruns": len(self.save["best_times"])}
        self.scene = TitleScene(self)
        self.mouse = (0, 0)

    def toast(self, text):
        self.toast_text = text
        self.toast_t = 3.0

    def save_game(self):
        write_save(self.save)

    def quit(self):
        self.save_game()
        self.running = False

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 1 / 20.0)
            self.mouse = pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self.quit()
                self.scene.handle_event(ev)
            self.scene.update(dt)
            self.scene.draw(self.screen)
            if self.toast_t > 0:
                self.toast_t -= dt
                draw_achievement_toast(self.screen, self.toast_text, self.toast_t)
            pygame.display.flip()
        self.audio.shutdown()
        pygame.quit()


# ---------------- TÍTULO ----------------
class TitleScene(Scene):
    def __init__(self, g):
        self.g = g
        self.theme = WORLD_THEMES[1]
        self.particles = Particles()
        self.t = 0.0
        self.has_save = has_save()
        y = 300
        self.items = [Button("NUEVA PARTIDA", WIDTH // 2 - 110, y),
                      Button("CONTINUAR", WIDTH // 2 - 110, y + 50),
                      Button("SELECCIÓN DE NIVELES", WIDTH // 2 - 110, y + 100),
                      Button("ÁRBOL DE HABILIDADES", WIDTH // 2 - 110, y + 150),
                      Button("COLECCIÓN Y MISIONES", WIDTH // 2 - 110, y + 200),
                      Button("AJUSTES", WIDTH // 2 - 110, y + 250),
                      Button("SALIR", WIDTH // 2 - 110, y + 300)]
        self.sel = 0
        g.audio.play_music("title")

    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i, b in enumerate(self.items):
                if b.hit(self.g.mouse):
                    self.sel = i
                    self.activate()
        elif ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = (self.sel - 1) % len(self.items)
                self.g.audio.play("select")
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = (self.sel + 1) % len(self.items)
                self.g.audio.play("select")
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.activate()

    def activate(self):
        g = self.g
        g.audio.play("confirm")
        txt = self.items[self.sel].text
        if txt == "NUEVA PARTIDA":
            delete_save()
            g.save = load_save()
            g.prog = Progression(g.save)
            g.prog.sync_from_save()
            g.stats = {"memories": 0, "bosses": 0, "speedruns": 0}
            g.scene = IntroScene(g)
        elif txt == "CONTINUAR":
            if self.has_save:
                g.save = load_save()
                g.prog = Progression(g.save)
                g.prog.sync_from_save()
                g.stats = {"memories": len(g.save["collected_memories"]),
                           "bosses": len(g.save["bosses_defeated"]),
                           "speedruns": len(g.save["best_times"])}
                g.scene = HubScene(g)
        elif txt == "SELECCIÓN DE NIVELES":
            g.scene = LevelSelectScene(g)
        elif txt == "ÁRBOL DE HABILIDADES":
            g.scene = SkillTreeScene(g)
        elif txt == "COLECCIÓN Y MISIONES":
            g.scene = CollectionScene(g)
        elif txt == "AJUSTES":
            g.scene = SettingsScene(g)
        elif txt == "SALIR":
            g.quit()

    def update(self, dt):
        self.t += dt
        self.particles.float_up(random.randint(0, WIDTH), HEIGHT + 6,
                                random.choice((CYAN, VIOLET, MAGENTA)), 1, (1.5, 3.0))
        self.particles.update(dt)

    def draw(self, surf):
        far, mid = bg_layers(self.theme)
        surf.fill(self.theme["sky"])
        surf.blit(far, (0, 0))
        surf.blit(mid, (0, int(20 + math.sin(self.t * 0.5) * 6)))
        cx, cy = WIDTH // 2, 150
        pygame.draw.circle(surf, (16, 10, 30), (cx, cy), 78)
        pygame.draw.circle(surf, MAGENTA, (cx, cy), 79, 3)
        pygame.draw.circle(surf, CYAN, (cx, cy), 86, 1)
        self.particles.draw(surf, pygame.Rect(0, 0, WIDTH, HEIGHT))
        kai = kai_frame("idle", 0, 1)
        surf.blit(pygame.transform.scale2x(kai), (cx - 90, 330))
        pix = pix_frame(int(self.t * 10))
        surf.blit(pygame.transform.scale2x(pix), (cx + 10, 300 + int(math.sin(self.t * 2) * 8)))
        glow = glow_surf(180, VIOLET)
        surf.blit(glow, glow.get_rect(center=(cx, 130)), special_flags=pygame.BLEND_ADD)
        draw_text(surf, "ECLIPSE", cx, 100, WHITE, 64, center=True, bold=True)
        draw_text(surf, "ZERO", cx, 158, CYAN, 44, center=True, bold=True)
        draw_text(surf, "La noche eterna terminará... o no.", cx, 208, (180, 160, 230), 16, center=True)
        for i, b in enumerate(self.items):
            b.draw(surf, self.g.mouse, selected=(i == self.sel))
        if not self.has_save:
            draw_text(surf, "(sin partida guardada)", WIDTH // 2, 640, GREY, 12, center=True)
        draw_text(surf, f"v{VERSION} - Python/Pygame - un solo archivo (juego.py)",
                  WIDTH - 10, HEIGHT - 20, DARKGREY, 11, center=True)


# ---------------- INTRO CINEMÁTICA ----------------
class IntroScene(Scene):
    def __init__(self, g):
        self.g = g
        self.scene_i = 0
        self.char_i = 0.0
        self.t = 0.0
        self.lines = INTRO_SCENES[0]

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.char_i < len(self.lines[1]):
                self.char_i = len(self.lines[1])
            else:
                self.next()

    def next(self):
        self.scene_i += 1
        if self.scene_i >= len(INTRO_SCENES):
            self.g.audio.play_music("world1")
            self.g.scene = LevelScene(self.g, 1, 0, first_time=True)
        else:
            self.lines = INTRO_SCENES[self.scene_i]
            self.char_i = 0.0

    def update(self, dt):
        self.t += dt
        self.char_i += 34 * dt

    def draw(self, surf):
        surf.fill((4, 3, 12))
        t = self.t
        for i in range(60):
            x = (i * 137) % WIDTH
            y = (i * 89) % HEIGHT
            b = 80 + int(70 * math.sin(t * 2 + i))
            surf.fill((b // 2, b // 2, b), (x, y, 2, 2))
        cx = WIDTH // 2
        off = min(1.0, self.scene_i / max(1, len(INTRO_SCENES) - 1))
        r = int(60 * (1 - off) + 6)
        pygame.draw.circle(surf, (255, 220, 140), (cx, 170), max(2, r))
        pygame.draw.circle(surf, (10, 8, 24), (cx + int(r * 1.6 * off), 170 - int(r * 0.4 * off)), max(2, r))
        draw_text(surf, self.lines[0], cx, 300, WHITE, 30, center=True, bold=True)
        shown = self.lines[1][:int(self.char_i)]
        draw_text_wrap(surf, shown, 120, 360, WIDTH - 240, CYAN, 18)
        draw_text(surf, "[ENTER]", WIDTH - 120, HEIGHT - 40, GREY, 13)


# ---------------- HUB / MAPA DE MUNDOS ----------------
class HubScene(Scene):
    def __init__(self, g, dialog=None):
        self.g = g
        self.dialog = dialog or []
        self.dlg_i = 0
        self.dlg_chars = 0.0
        self.t = 0.0

    def handle_event(self, ev):
        if self.dialog:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                sp, tx = self.dialog[self.dlg_i]
                if self.dlg_chars < len(tx):
                    self.dlg_chars = len(tx)
                else:
                    self.dlg_i += 1
                    self.dlg_chars = 0.0
                    if self.dlg_i >= len(self.dialog):
                        self.dialog = []
            return
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
            self.g.scene = LevelSelectScene(self.g)

    def update(self, dt):
        self.t += dt
        if self.dialog and self.dlg_i < len(self.dialog):
            self.dlg_chars += 40 * dt

    def draw(self, surf):
        surf.fill((10, 8, 28))
        t = self.t
        draw_text(surf, "NEXARIA - MAPA DE REGIONES", WIDTH // 2, 40, WHITE, 28, center=True, bold=True)
        draw_text(surf, "ENTER: elegir región", WIDTH // 2, 70, GREY, 14, center=True)
        unlocked = self.unlocked_worlds()
        for w in range(1, 8):
            th = WORLD_THEMES[w]
            ang = w * 2.399 + t * 0.15
            x = WIDTH // 2 + int(math.cos(ang) * 170)
            y = 300 + int(math.sin(ang) * 130)
            col = th["accent"] if w in unlocked else (60, 60, 90)
            label = th["name"] if w in unlocked else "???"
            if w in self.g.save["shards"]:
                pygame.draw.circle(surf, GOLD, (x, y), 26, 3)
            pygame.draw.circle(surf, col, (x, y), 20)
            draw_text(surf, str(w), x, y - 8, WHITE, 16, center=True, bold=True)
            draw_text(surf, label, x, y + 26, col, 11, center=True)
        px = pix_frame(int(t * 10))
        surf.blit(px, (WIDTH // 2 - 8, 280 + int(math.sin(t * 2) * 10)))
        if self.dialog and self.dlg_i < len(self.dialog):
            sp, tx = self.dialog[self.dlg_i]
            draw_dialog(surf, sp, tx, int(self.dlg_chars))

    def unlocked_worlds(self):
        s = self.g.save
        out = {1}
        for sh in s["shards"]:
            out.add(min(7, sh + 1))
        if 7 in s["shards"]:
            out.add(7)
        return out


# ---------------- SELECCIÓN DE NIVELES ----------------
class LevelSelectScene(Scene):
    def __init__(self, g):
        self.g = g
        self.world = min(7, max(1, g.save["world"]))
        self.level_i = 0
        self.t = 0.0

    def unlocked_worlds(self):
        return HubScene(self.g).unlocked_worlds()

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_LEFT, pygame.K_a):
                self.world = max(1, self.world - 1)
            elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                self.world = min(7, self.world + 1)
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.level_i = max(0, self.level_i - 1)
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.level_i = min(2, self.level_i + 1)
            elif ev.key == pygame.K_RETURN:
                if self.world in self.unlocked_worlds():
                    self.g.audio.play("confirm")
                    if self.level_i == 2 and self.world not in self.g.save["shards"]:
                        self.g.scene = LevelScene(self.g, self.world, 2)
                    elif self.level_i == 2:
                        self.g.toast("Este jefe ya fue derrotado")
                    else:
                        self.g.scene = LevelScene(self.g, self.world, self.level_i)
            elif ev.key == pygame.K_ESCAPE:
                self.g.scene = TitleScene(self.g)

    def update(self, dt):
        self.t += dt

    def draw(self, surf):
        th = WORLD_THEMES[self.world]
        surf.fill((10, 8, 28))
        draw_text(surf, f"MUNDO {self.world}: {th['name']}", WIDTH // 2, 60, th["accent"], 30, center=True, bold=True)
        unlocked = self.unlocked_worlds()
        if self.world not in unlocked:
            draw_text(surf, "Región bloqueada: consigue el fragmento del mundo anterior.",
                      WIDTH // 2, 110, GREY, 15, center=True)
        names = ["Nivel 1", "Nivel 2 (Fragmento)", "Arena del Jefe"]
        for i, nm in enumerate(names):
            sel = (i == self.level_i)
            col = WHITE if sel else GREY
            extra = ""
            key = f"{self.world}:{i}"
            if key in self.g.save["levels_completed"]:
                extra = "  [COMPLETADO]"
            if i == 2 and self.world in self.g.save["shards"]:
                extra = "  [JEFE DERROTADO]"
            draw_text(surf, f"{nm}{extra}", WIDTH // 2, 200 + i * 50, col, 20, center=sel, bold=sel)
        best = self.g.save["best_times"].get(f"{self.world}:0")
        if best:
            draw_text(surf, f"Mejor tiempo nivel 1: {best:.1f}s", WIDTH // 2, 380, GOLD, 14, center=True)
        draw_text(surf, "Flechas: navegar   ENTER: jugar   ESC: título", WIDTH // 2, 480, GREY, 14, center=True)


# ---------------- ESCENA DE NIVEL ----------------
class LevelScene(Scene):
    def __init__(self, g, world, level_i, first_time=False):
        self.g = g
        self.world = world
        self.level_i = level_i
        self.theme = WORLD_THEMES[world]
        lv = build_world_levels(world)[level_i]
        self.level_name = lv[0]
        data = lv[1]
        self.is_boss = lv[2]
        self.phys = PhysicsWorld()
        self.phys.solids = list(data["solids"])
        self.phys.oneways = list(data["oneways"])
        self.phys.movers = list(data["movers"])
        self.phys.hazards = list(data["hazards"])
        self.particles = Particles()
        spawn = data["spawns"][0] if data["spawns"] else (64, 300)
        cp = g.save.get("checkpoint")
        if first_time and cp and g.save.get("world") == world:
            spawn = cp
        self.player = Player(spawn[0], spawn[1], g.prog, self.particles)
        self.player.max_hp = g.prog.max_hp()
        self.player.hp = min(self.player.hp, self.player.max_hp)
        self.coins = [dict(c) for c in data["coins"]]
        self.shards = [dict(s) for s in data["shards"]]
        self.memories = [dict(m) for m in data["memories"]]
        self.chests = list(data["chests"])
        for c in self.chests:
            if c.id in g.save["opened_chests"]:
                c.opened = True
        self.checkpoints = list(data["checkpoints"])
        self.doors = list(data["doors"])
        self.shop_pos = data["shop"]
        self.enemies = []
        mult = 1.0 + 0.18 * (world - 1)
        for kind, x, y in data["enemies"]:
            self.enemies.append(Enemy(kind, x, y, mult))
        self.boss = None
        if self.is_boss:
            if self.doors:
                dx_, dy_ = self.doors[0]
                self.boss = Boss(BOSS_BY_WORLD[world], dx_ - 300, dy_ + 60, world)
            else:
                self.boss = Boss(BOSS_BY_WORLD[world], 500, 300, world)
            self.enemies = []
        self.projectiles = []
        self.dmg_numbers = []
        self.cam = pygame.Rect(0, 0, WIDTH, HEIGHT)
        self.shake = CameraShake()
        self.t = 0.0
        self.level_time = 0.0
        self.took_damage = False
        self.paused = False
        self.pause_sel = 0
        self.finished = False
        self.finish_t = 0.0
        self.dead_t = 0.0
        self.dialog = None
        self.dlg_i = 0
        self.dlg_chars = 0.0
        self.pending_decision = None
        self.pending_sfx = None
        self.time_slow = 0.0
        self.enemy_log_added = set()
        self.secret_checked = False
        self.secret_items = []
        g.audio.play_music("boss" if self.is_boss else self.theme["music"])
        if first_time:
            self.start_dialog(DIALOGUES["wake"])
        elif world > 1 and level_i == 0:
            key = f"world{world}_enter"
            if key in DIALOGUES and f"intro_w{world}" not in g.save["flags"]:
                self.start_dialog(DIALOGUES[key])
                g.save["flags"].append(f"intro_w{world}")

    # ------------- diálogos -------------
    def start_dialog(self, lines):
        self.dialog = lines
        self.dlg_i = 0
        self.dlg_chars = 0.0

    def advance_dialog(self):
        if not self.dialog:
            return
        sp, tx = self.dialog[self.dlg_i]
        if self.dlg_chars < len(tx):
            self.dlg_chars = len(tx)
        else:
            self.dlg_i += 1
            self.dlg_chars = 0.0
            if self.dlg_i >= len(self.dialog):
                self.dialog = None
                self.after_dialog()

    def after_dialog(self):
        if self.world == 1 and self.level_i == 1 and "after_w1" not in self.g.save["decisions"] and not self.is_boss:
            self.pending_decision = "after_w1"
        else:
            self.pending_decision = None

    # ------------- eventos -------------
    def handle_event(self, ev):
        g = self.g
        if self.dialog:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.advance_dialog()
            return
        if self.pending_decision:
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_1, pygame.K_LEFT):
                    g.save["decisions"][self.pending_decision] = 0
                    self.pending_decision = None
                    g.audio.play("confirm")
                    g.save_game()
                elif ev.key in (pygame.K_2, pygame.K_RIGHT):
                    g.save["decisions"][self.pending_decision] = 1
                    self.pending_decision = None
                    g.audio.play("confirm")
                    g.save_game()
            return
        if self.finished or self.dead_t > 0:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                if self.finished:
                    self._next_level()
                elif self.dead_t > 0.8:
                    self._respawn()
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.paused = not self.paused
                g.audio.play("pause")
            if self.paused:
                self._pause_menu_key(ev)
                return
            p = self.player
            if ev.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
                r = p.try_jump(self.phys)
                if r:
                    self.pending_sfx = r[1]
            elif ev.key in (pygame.K_j,):
                self.pending_sfx = p.try_attack(self.enemies, self.projectiles) or "attack"
                self._do_melee()
            elif ev.key in (pygame.K_k,):
                r = p.start_dash()
                if r:
                    self.pending_sfx = r
            elif ev.key in (pygame.K_l,):
                r = p.try_special(self.projectiles)
                if r:
                    self.pending_sfx = r
            elif ev.key in (pygame.K_e,):
                self._interact()
            elif ev.key in (pygame.K_q,):
                self._use_potion()
        elif ev.type == pygame.MOUSEBUTTONDOWN and self.paused:
            self._pause_menu_click(ev.pos)

    def _do_melee(self):
        hb = sword_hitbox(self.player)
        apply_melee(self.player, hb, self.enemies, ([self.boss] if self.boss else []),
                    self.dmg_numbers, self.g.audio.play)
        for e in self.enemies:
            if not e.alive and e.kind not in self.enemy_log_added:
                self.enemy_log_added.add(e.kind)
                if e.kind not in self.g.save["enemies_log"]:
                    self.g.save["enemies_log"].append(e.kind)
        self._cleanup_dead()

    def _cleanup_dead(self):
        for e in self.enemies:
            if not e.alive:
                self.particles.burst(e.rect.centerx, e.rect.centery, VIOLET, 18, (60, 220), (0.3, 0.8), (2, 4), 250)
                self.g.save["coins"] += e.coins
                lv = self.g.prog.add_xp(e.xp)
                if lv:
                    self.g.audio.play("levelup")
                    self.g.toast(f"¡NIVEL {self.g.save['player_level']}! +1 punto de habilidad")
                self.g.audio.play("enemy_die")
        self.enemies = [e for e in self.enemies if e.alive]
        if self.boss and not self.boss.alive:
            self._boss_defeated()

    def _interact(self):
        g = self.g
        p = self.player.rect
        for c in self.chests:
            if not c.opened and p.inflate(30, 30).colliderect(c.rect):
                c.opened = True
                g.save["opened_chests"].append(c.id)
                loot = roll_loot(c.tier)
                msg = apply_loot(g.prog, loot)
                g.audio.play("chest")
                g.toast(f"Cofre: {msg}")
                return
        for (cx, cy) in self.checkpoints:
            r = pygame.Rect(cx, cy, 16, 40)
            if p.inflate(30, 30).colliderect(r):
                g.save["checkpoint"] = [self.player.rect.x, self.player.rect.y]
                g.save["world"] = self.world
                g.save["level"] = self.level_i
                g.save_game()
                g.audio.play("checkpoint")
                g.toast("Punto de control guardado")
                if "cp_first" not in g.save["flags"]:
                    g.save["flags"].append("cp_first")
                    self.start_dialog(DIALOGUES["checkpoint_first"])
                return
        for (dx_, dy_) in self.doors:
            r = pygame.Rect(dx_, dy_, 32, 52)
            if p.inflate(30, 30).colliderect(r):
                self._finish()
                return
        for m in self.memories[:]:
            r = pygame.Rect(m["x"] - 6, m["y"] - 6, 26, 26)
            if p.inflate(30, 30).colliderect(r):
                if m["id"] not in g.save["collected_memories"]:
                    g.save["collected_memories"].append(m["id"])
                    g.stats["memories"] += 1
                    g.prog.add_xp(20)
                self.memories.remove(m)
                g.audio.play("potion")
                g.toast("Recuerdo recuperado (mira en COLECCIÓN desde el menú)")
                return
        if self.shop_pos:
            r = pygame.Rect(self.shop_pos[0] - 10, self.shop_pos[1] - 10, 52, 52)
            if p.inflate(30, 30).colliderect(r):
                if "mara" not in g.save["flags"]:
                    g.save["flags"].append("mara")
                    self.start_dialog(DIALOGUES["mara"])
                elif g.stats["memories"] >= 3 and "mara2" not in g.save["flags"]:
                    g.save["flags"].append("mara2")
                    self.start_dialog(DIALOGUES["mara_memory"])
                else:
                    self.g.scene = ShopScene(self.g, self)

    def _use_potion(self):
        g = self.g
        if g.save["potions"] > 0 and self.player.hp < self.player.max_hp:
            g.save["potions"] -= 1
            self.player.heal(POTION_HEAL)
            g.audio.play("potion")
            self.particles.float_up(self.player.rect.centerx, self.player.rect.top, GREEN, 8)

    # ------------- pausa -------------
    def _pause_menu_key(self, ev):
        if ev.key in (pygame.K_RETURN,):
            txt = ["Continuar", "Guardado rápido", "Salir al título"][self.pause_sel]
            if txt == "Continuar":
                self.paused = False
            elif txt == "Guardado rápido":
                self.g.save_game()
                self.g.toast("Partida guardada")
            elif txt == "Salir al título":
                self.g.save_game()
                self.g.scene = TitleScene(self.g)
        elif ev.key in (pygame.K_UP, pygame.K_w):
            self.pause_sel = (self.pause_sel - 1) % 3
        elif ev.key in (pygame.K_DOWN, pygame.K_s):
            self.pause_sel = (self.pause_sel + 1) % 3

    def _pause_menu_click(self, pos):
        for i in range(3):
            r = pygame.Rect(WIDTH // 2 - 100, 220 + i * 54, 200, 44)
            if r.collidepoint(pos):
                self.pause_sel = i
                self._pause_menu_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))

    # ------------- fin de nivel -------------
    def _finish(self):
        g = self.g
        self.finished = True
        self.finish_t = 0.0
        g.audio.play("victory")
        key = f"{self.world}:{self.level_i}"
        if key not in g.save["levels_completed"]:
            g.save["levels_completed"].append(key)
        if not self.took_damage and key not in g.save["no_hit_levels"]:
            g.save["no_hit_levels"].append(key)
            g.save["coins"] += 25
            if g.prog.grant("no_hit"):
                g.toast("LOGRO: Nivel perfecto (+25 monedas)")
        if not self.is_boss and self.level_i == 0:
            best = g.save["best_times"].get(key)
            if best is None or self.level_time < best:
                g.save["best_times"][key] = round(self.level_time, 1)
            if self.level_time < 60:
                g.stats["speedruns"] += 1
                g.prog.grant("speedrun")
        update_quests(g.prog, g.stats)
        g.save_game()

    def _boss_defeated(self):
        g = self.g
        g.audio.play("boss_die")
        self.shake.shake(0.6, 8)
        name = BOSS_NAMES[self.world]
        if name not in g.save["bosses_defeated"]:
            g.save["bosses_defeated"].append(name)
        g.stats["bosses"] = len(g.save["bosses_defeated"])
        g.prog.add_xp(150)
        g.save["coins"] += 150
        g.prog.grant("boss1")
        if self.world == 1:
            g.prog.grant("world1")
        if len(g.save["shards"]) >= 6:
            g.prog.grant("all_worlds")
        if len(g.save["collected_memories"]) >= 5:
            g.prog.grant("memory5")
        if self.world not in g.save["shards"]:
            g.save["shards"].append(self.world)
        self.finished = True
        self.finish_t = 0.0
        g.save_game()

    def _next_level(self):
        g = self.g
        g.save["checkpoint"] = None
        if self.is_boss:
            dlg = [("PIX", f"¡Fragmento {self.world} conseguido! {BOSS_NAMES[self.world]} ya no es amenaza."),
                   ("KAI", "La luz del fragmento me habla... me muestra un recuerdo. Voy siguiendo su señal.")]
            if self.world == 3 and "twist" not in g.save["flags"]:
                g.save["flags"].append("twist")
                dlg = DIALOGUES["twist"]
            g.scene = HubScene(g, dialog=dlg)
            return
        nxt = self.level_i + 1
        if nxt < 3:
            g.scene = LevelScene(g, self.world, nxt)
        else:
            g.scene = HubScene(g)

    def _respawn(self):
        cp = self.g.save.get("checkpoint")
        self.g.scene = LevelScene(self.g, self.world, self.level_i, first_time=bool(cp))

    # ------------- update -------------
    def update(self, dt):
        if self.dialog:
            if self.dlg_i < len(self.dialog):
                self.dlg_chars += 50 * dt
            return
        if self.pending_decision or self.paused:
            return
        if self.finished:
            self.finish_t += dt
            self.particles.update(dt)
            return
        if self.dead_t > 0:
            self.dead_t += dt
            return

        self.t += dt
        self.level_time += dt
        keys = pygame.key.get_pressed()

        for m in self.phys.movers:
            m.update(dt)

        p = self.player
        p.update(keys, self.phys, dt, self.enemies, None)
        if self.pending_sfx:
            self.g.audio.play(self.pending_sfx)
            self.pending_sfx = None

        # caída al vacío / pinchos
        if p.rect.top > 1400 or p.rect.top < -800:
            p.take_damage(999, p.rect.centerx)
        if self.phys.hazard_hit(p.rect):
            if p.take_damage(15, p.rect.centerx):
                self.took_damage = True

        # ruptura temporal (mantener L con e3)
        ab = self.g.prog.data["abilities"]
        ts_active = False
        if "time_slow" in ab and keys[pygame.K_l] and p.energy > 5:
            ts_active = True
            self.time_slow = 0.2
            p.energy -= 12 * dt
        scale = 0.35 if ts_active else 1.0

        # enemigos
        for e in self.enemies:
            e.update(dt, self.phys, p, self.projectiles, self.particles, time_scale=scale)
            if e.rect.colliderect(p.rect) and e.attack_cd <= 0:
                if p.take_damage(e.dmg, e.rect.centerx):
                    self.took_damage = True
                    e.attack_cd = 0.8
        self._cleanup_dead()

        # jefe
        if self.boss and self.boss.alive:
            self.boss.update(dt, self.phys, p, self.projectiles, self.particles,
                             self.shake.shake, time_slow=ts_active)
            if self.boss.rect.colliderect(p.rect) and p.invuln <= 0:
                if p.take_damage(20, self.boss.rect.centerx):
                    self.took_damage = True

        # proyectiles
        for pr in self.projectiles[:]:
            pr.update(dt, self.phys.solids, self.phys.movers)
            if pr.kind == "player_orb":
                for e in self.enemies:
                    if e.alive and pr.rect.colliderect(e.rect):
                        e.take_damage(pr.dmg, 1 if pr.vx > 0 else -1)
                        self.dmg_numbers.append(DamageNumber(e.rect.centerx, e.rect.top, pr.dmg))
                        pr.dead = True
                if self.boss and self.boss.alive and pr.rect.colliderect(self.boss.rect):
                    self.boss.take_damage(pr.dmg, 1)
                    self.dmg_numbers.append(DamageNumber(self.boss.rect.centerx, self.boss.rect.top, pr.dmg, crit=True))
                    pr.dead = True
            else:
                if pr.rect.colliderect(p.rect):
                    if p.take_damage(pr.dmg, pr.rect.centerx):
                        self.took_damage = True
                    pr.dead = True
            if pr.dead:
                self.projectiles.remove(pr)
        self._cleanup_dead()

        # monedas (una sola vez: se recuerdan en save["collected"])
        for c in self.coins[:]:
            r = pygame.Rect(c["x"], c["y"], 10, 12)
            if p.rect.colliderect(r):
                if c["id"] not in self.g.save["collected"]:
                    self.g.save["collected"].append(c["id"])
                    self.g.save["coins"] += 5
                    self.g.prog.add_xp(2)
                    self.g.audio.play("coin")
                    self.particles.burst(c["x"] + 5, c["y"] + 6, GOLD, 6, (30, 120), (0.2, 0.5), (2, 3), 100)
                self.coins.remove(c)
        # fragmentos de luz
        for s in self.shards[:]:
            r = pygame.Rect(s["x"], s["y"], 14, 18)
            if p.rect.colliderect(r):
                self.shards.remove(s)
                self.g.audio.play("fragment")
                self.particles.burst(s["x"], s["y"], CYAN, 40, (60, 260), (0.5, 1.2), (2, 5), 60)
                self.g.toast("¡Energía del fragmento absorbida! Ve a la arena del jefe.")
        # salas secretas
        if not self.secret_checked:
            self.secret_checked = True
            lv_data = build_world_levels(self.world)[self.level_i][1]
            self.secret_items = [dict(z) for z in lv_data.get("secret_zones", [])
                                 if z["id"] not in self.g.save["collected"]]
        for z in self.secret_items[:]:
            r = pygame.Rect(z["x"], z["y"], TILE, TILE)
            if p.rect.colliderect(r):
                self.secret_items.remove(z)
                self.g.save["collected"].append(z["id"])
                self.g.save["collected_memories"].append(z["id"])
                self.g.stats["memories"] = len(self.g.save["collected_memories"])
                self.g.audio.play("secret")
                self.g.prog.add_xp(30)
                if self.g.prog.grant("secret"):
                    self.g.toast("LOGRO: Descubridor de secretos")
                else:
                    self.g.toast("¡Sala secreta! Un recuerdo sobre Kai...")

        # partículas / clima / cámara
        self.particles.weather(self.theme["weather"], self.cam, dt)
        self.particles.update(dt)
        for d in self.dmg_numbers[:]:
            d.update(dt)
            if not d.alive():
                self.dmg_numbers.remove(d)

        tx = p.rect.centerx - WIDTH // 2
        ty = p.rect.centery - HEIGHT // 2
        self.cam.x += (tx - self.cam.x) * min(1, 8 * dt)
        self.cam.y += (ty - self.cam.y) * min(1, 8 * dt)
        sx, sy = self.shake.offset()
        self.shake.update(dt)
        self.cam.x = max(0, int(self.cam.x + sx))
        self.cam.y = max(0, int(self.cam.y + sy))

        # muerte
        if p.hp <= 0 and self.dead_t == 0:
            self.dead_t = 0.01
            self.g.audio.play("gameover")
            self.g.audio.stop_music()

        # giro narrativo en la arena del mundo 7
        if self.is_boss and self.world == 7 and "twist_seen" not in self.g.save["flags"] and not self.dialog:
            self.g.save["flags"].append("twist_seen")
            self.start_dialog(DIALOGUES["twist"])

    # ------------- draw -------------
    def draw(self, surf):
        th = self.theme
        far, mid = bg_layers(th)
        px1 = -int(self.cam.x * 0.2) % 960
        px2 = -int(self.cam.x * 0.45) % 960
        surf.fill(th["sky"])
        surf.blit(far, (px1 - 960, 0))
        surf.blit(far, (px1, 0))
        surf.blit(mid, (px2 - 960, 40))
        surf.blit(mid, (px2, 40))
        fog = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fog.fill((th["accent"][0], th["accent"][1], th["accent"][2], 8))
        surf.blit(fog, (0, 0))

        ts = tile(th, True)
        tos = tile(th, False)
        for r in self.phys.solids:
            surf.blit(ts, (r.x - self.cam.left, r.y - self.cam.top))
        for r in self.phys.oneways:
            surf.blit(tos, (r.x - self.cam.left, r.y - self.cam.top))
        for m in self.phys.movers:
            r = m.rect
            pygame.draw.rect(surf, th["tile"], (r.x - self.cam.left, r.y - self.cam.top, r.w, r.h))
            pygame.draw.rect(surf, th["accent"], (r.x - self.cam.left, r.y - self.cam.top, r.w, 3))
        sp = spike_surf(th)
        for r in self.phys.hazards:
            surf.blit(sp, (r.x - self.cam.left, r.y - 16 - self.cam.top))
        ds = door_surf(th)
        for (dx_, dy_) in self.doors:
            surf.blit(ds, (dx_ - self.cam.left, dy_ - self.cam.top))
            glow = glow_surf(30, th["accent"])
            surf.blit(glow, glow.get_rect(center=(dx_ + 16 - self.cam.left, dy_ + 26 - self.cam.top)),
                      special_flags=pygame.BLEND_ADD)
        for (cx, cy) in self.checkpoints:
            active = self.g.save.get("checkpoint") == [self.player.rect.x, self.player.rect.y]
            surf.blit(checkpoint_surf(active), (cx - self.cam.left, cy - self.cam.top))
        for c in self.coins:
            surf.blit(coin_surf(), (c["x"] - self.cam.left, c["y"] - self.cam.top +
                                    int(3 * math.sin(self.t * 4 + c["x"]))))
        for s in self.shards:
            surf.blit(shard_surf(), (s["x"] - self.cam.left, s["y"] - self.cam.top +
                                     int(4 * math.sin(self.t * 3))))
            glow = glow_surf(22, CYAN)
            surf.blit(glow, glow.get_rect(center=(s["x"] + 7 - self.cam.left, s["y"] + 9 - self.cam.top)),
                      special_flags=pygame.BLEND_ADD)
        for m in self.memories:
            surf.blit(memory_surf(), (m["x"] - self.cam.left, m["y"] - self.cam.top +
                                      int(3 * math.sin(self.t * 3 + m["y"]))))
        for c in self.chests:
            surf.blit(chest_surf(c.opened), (c.rect.x - self.cam.left, c.rect.y - self.cam.top))
        if self.shop_pos:
            mx = self.shop_pos[0] - self.cam.left
            my = self.shop_pos[1] - self.cam.top
            surf.blit(pygame.transform.scale2x(pix_frame(int(self.t * 10) % 2)), (mx, my))
            draw_text(surf, "MARA [E]", mx + 4, my - 18, MAGENTA, 12)
        for z in self.secret_items:
            k = (math.sin(self.t * 2.2) + 1) / 2
            col = (int(MAGENTA[0] * k), int(MAGENTA[1] * k), int(MAGENTA[2] * k))
            pygame.draw.rect(surf, col, (z["x"] - self.cam.left, z["y"] - self.cam.top, TILE, TILE))
        for e in self.enemies:
            e.draw(surf, self.cam)
        if self.boss and self.boss.alive:
            self.boss.draw(surf, self.cam)
        for pr in self.projectiles:
            pr.draw(surf, self.cam)
        self.player.draw(surf, self.cam)
        self.particles.draw(surf, self.cam, rain=(self.theme["weather"] == "rain"))
        for d in self.dmg_numbers:
            col = GOLD if d.crit else WHITE
            draw_text(surf, str(d.amount), int(d.x - self.cam.left), int(d.y - self.cam.top), col, 14, center=True)

        draw_hud(surf, self.player, self.g.prog, th["name"], len(self.g.save["shards"]),
                 time_slow_active=(self.time_slow > 0))
        self.time_slow = max(0, self.time_slow - DT)
        draw_text(surf, self.level_name, WIDTH // 2, 14, (200, 190, 255), 15, center=True)

        vig = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(vig, (0, 0, 0, 40), (0, 0, WIDTH, HEIGHT), 60, border_radius=40)
        surf.blit(vig, (0, 0))

        if self.dialog and self.dlg_i < len(self.dialog):
            spk, tx = self.dialog[self.dlg_i]
            draw_dialog(surf, spk, tx, int(self.dlg_chars))
        elif self.pending_decision:
            q, opts = DECISION_POINTS[self.pending_decision]
            r = pygame.Rect(140, HEIGHT - 170, WIDTH - 280, 130)
            pygame.draw.rect(surf, (14, 12, 34), r, border_radius=10)
            pygame.draw.rect(surf, GOLD, r, 2, border_radius=10)
            draw_text(surf, q, r.centerx, r.y + 24, WHITE, 16, center=True)
            draw_text(surf, f"[1] {opts[0]}", r.centerx - 100, r.y + 60, CYAN, 15, center=True)
            draw_text(surf, f"[2] {opts[1]}", r.centerx + 100, r.y + 60, MAGENTA, 15, center=True)

        if self.paused:
            draw_fade(surf, 160)
            draw_text(surf, "PAUSA", WIDTH // 2, 150, WHITE, 42, center=True, bold=True)
            opts = ["Continuar", "Guardado rápido", "Salir al título"]
            for i, o in enumerate(opts):
                sel = (self.pause_sel == i)
                r = pygame.Rect(WIDTH // 2 - 100, 220 + i * 54, 200, 44)
                pygame.draw.rect(surf, (70, 60, 140) if sel else (40, 36, 80), r, border_radius=8)
                pygame.draw.rect(surf, CYAN if sel else VIOLET, r, 2, border_radius=8)
                draw_text(surf, o, r.centerx, r.centery, WHITE, 17, center=True)

        if self.finished:
            k = min(1, self.finish_t / 1.2)
            draw_fade(surf, int(170 * k))
            if self.boss is not None:
                msg = f"¡{BOSS_NAMES[self.world]} DERROTADO!"
            else:
                msg = "¡NIVEL COMPLETADO!"
            draw_text(surf, msg, WIDTH // 2, 200, GOLD, 34, center=True, bold=True)
            stats = [f"Tiempo: {self.level_time:.1f}s",
                     f"Bonus sin daño: {'+25 monedas' if not self.took_damage else 'no (recibiste daño)'}",
                     f"Monedas: {self.g.save['coins']}"]
            for i, sline in enumerate(stats):
                draw_text(surf, sline, WIDTH // 2, 260 + i * 30, WHITE, 16, center=True)
            if self.finish_t > 0.8:
                draw_text(surf, "[ENTER] continuar", WIDTH // 2, 400, CYAN, 16, center=True)

        if self.dead_t > 0:
            draw_fade(surf, min(200, int(self.dead_t * 160)))
            draw_text(surf, "HAS CAÍDO...", WIDTH // 2, 220, RED, 40, center=True, bold=True)
            if self.dead_t > 0.8:
                draw_text(surf, "[ENTER] reaparecer en el punto de control", WIDTH // 2, 300, WHITE, 16, center=True)


# ---------------- TIENDA DE MARA ----------------
class ShopScene(Scene):
    def __init__(self, g, from_scene=None):
        self.g = g
        self.from_scene = from_scene
        self.sel = 0
        self.msg = "Bienvenida de nuevo, explorador."

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = max(0, self.sel - 1)
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = min(len(SHOP_STOCK) - 1, self.sel + 1)
            elif ev.key in (pygame.K_RETURN, pygame.K_e):
                kind, name, price, desc = SHOP_STOCK[self.sel]
                if self.g.save["coins"] >= price:
                    self.g.save["coins"] -= price
                    if kind == "potion":
                        self.g.save["potions"] += 1
                        self.msg = f"Poción comprada. Monedas: {self.g.save['coins']}"
                    else:
                        wid = kind.split("_", 1)[1]
                        if wid in self.g.save["owned_weapons"]:
                            self.msg = "Ya tienes esa arma."
                            self.g.save["coins"] += price
                        else:
                            self.g.save["owned_weapons"].append(wid)
                            self.g.save["weapon"] = wid
                            self.msg = f"¡{name} equipada!"
                    self.g.audio.play("buy")
                    self.g.save_game()
                else:
                    self.msg = "Monedas insuficientes."
                    self.g.audio.play("hit")
            elif ev.key == pygame.K_ESCAPE:
                self.back()
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for i in range(len(SHOP_STOCK)):
                r = pygame.Rect(280, 170 + i * 46, 400, 40)
                if r.collidepoint(ev.pos):
                    self.sel = i

    def back(self):
        if self.from_scene:
            self.from_scene.dialog = None
            self.g.scene = self.from_scene
        else:
            self.g.scene = TitleScene(self.g)

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((16, 10, 30))
        draw_text(surf, "TIENDA DE MARA", WIDTH // 2, 50, MAGENTA, 30, center=True, bold=True)
        draw_text(surf, f"Tus monedas: {self.g.save['coins']}    [ENTER] comprar   [ESC] salir",
                  WIDTH // 2, 88, GOLD, 15, center=True)
        draw_text(surf, f"Arma equipada: {WEAPONS[self.g.save['weapon']]['name']}",
                  WIDTH // 2, 114, CYAN, 14, center=True)
        for i, (kind, name, price, desc) in enumerate(SHOP_STOCK):
            r = pygame.Rect(280, 170 + i * 46, 400, 40)
            sel = (i == self.sel)
            pygame.draw.rect(surf, (60, 40, 90) if sel else (34, 26, 60), r, border_radius=8)
            afford = self.g.save["coins"] >= price
            draw_text(surf, f"{name} - {price}m", 292, r.y + 4, WHITE if afford else GREY, 15)
            draw_text(surf, desc, 292, r.y + 22, GREY, 11)
        draw_text(surf, self.msg, WIDTH // 2, 460, GREEN, 15, center=True)
        surf.blit(pygame.transform.scale2x(pix_frame(0)), (160, 200))


# ---------------- ÁRBOL DE HABILIDADES ----------------
class SkillTreeScene(Scene):
    def __init__(self, g):
        self.g = g
        self.branch = "combate"
        self.sel = 0

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_LEFT, pygame.K_a):
                self.branch = {"combate": "movimiento", "movimiento": "energia", "energia": "combate"}[self.branch]
                self.sel = 0
            elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                self.branch = {"combate": "energia", "movimiento": "combate", "energia": "movimiento"}[self.branch]
                self.sel = 0
            elif ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = max(0, self.sel - 1)
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = min(len(SKILL_TREE[self.branch]) - 1, self.sel + 1)
            elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                nodes = SKILL_TREE[self.branch]
                sid = nodes[self.sel]["id"]
                ok, _why = self.g.prog.buy_skill(sid)
                if ok:
                    self.g.audio.play("levelup")
                    self.g.save_game()
                else:
                    self.g.audio.play("hit")
            elif ev.key == pygame.K_ESCAPE:
                self.g.scene = TitleScene(self.g)

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((12, 10, 30))
        d = self.g.save
        draw_text(surf, "ÁRBOL DE HABILIDADES", WIDTH // 2, 40, WHITE, 28, center=True, bold=True)
        draw_text(surf, f"Puntos disponibles: {d['skill_points']}    Nivel: {d['player_level']}    XP: {d['xp']}",
                  WIDTH // 2, 72, CYAN, 15, center=True)
        names = {"combate": "COMBATE", "movimiento": "MOVIMIENTO", "energia": "ENERGÍA"}
        draw_text(surf, f"<<< {names[self.branch]} >>>", WIDTH // 2, 110, VIOLET, 20, center=True, bold=True)
        nodes = SKILL_TREE[self.branch]
        for i, n in enumerate(nodes):
            y = 160 + i * 90
            sel = (i == self.sel)
            lvl = self.g.prog.skill_level(n["id"])
            unlocked = all(self.g.prog.skill_level(rq) >= 1 for rq in n["req"])
            col = CYAN if lvl > 0 else (WHITE if unlocked else DARKGREY)
            r = pygame.Rect(240, y, 480, 74)
            pygame.draw.rect(surf, (34, 28, 66) if sel else (22, 18, 44), r, border_radius=10)
            pygame.draw.rect(surf, GOLD if sel else VIOLET, r, 2, border_radius=10)
            draw_text(surf, f"{n['name']}  [{lvl}/{n['max']}]", 256, y + 8, col, 16, bold=True)
            draw_text_wrap(surf, n["desc"], 256, y + 32, 440, GREY, 13)
        draw_text(surf, "ENTER: mejorar   Flechas: navegar   ESC: volver", WIDTH // 2, 470, GREY, 13, center=True)


# ---------------- COLECCIÓN / MISIONES / LOGROS / BESTIARIO ----------------
class CollectionScene(Scene):
    TABS = ["RECUERDOS", "MISIONES", "LOGROS", "BESTIARIO"]

    def __init__(self, g):
        self.g = g
        self.tab = 0

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_RIGHT, pygame.K_d):
                self.tab = (self.tab + 1) % 4
            elif ev.key in (pygame.K_LEFT, pygame.K_a):
                self.tab = (self.tab - 1) % 4
            elif ev.key == pygame.K_ESCAPE:
                self.g.scene = TitleScene(self.g)

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((12, 10, 30))
        g = self.g
        for i, tname in enumerate(self.TABS):
            col = CYAN if i == self.tab else DARKGREY
            draw_text(surf, tname, 120 + i * 200, 40, col, 18, bold=(i == self.tab))
        draw_text(surf, "< > cambiar pestaña   ESC: volver", WIDTH - 20, 40, GREY, 12, center=True)
        y = 100
        if self.tab == 0:
            for wid, txt in MEMORIES.items():
                if isinstance(txt, str):
                    title, body = txt.split("|", 1) if "|" in txt else (txt, "")
                else:
                    title, body = txt
                have = any(mid.startswith(f"w{wid}_") for mid in g.save["collected_memories"])
                col = WHITE if have else DARKGREY
                draw_text(surf, ("[X] " if have else "[ ] ") + title, 100, y, col, 15)
                if have:
                    draw_text_wrap(surf, body, 120, y + 22, WIDTH - 260, GREY, 12)
                    y += 70
                else:
                    y += 34
        elif self.tab == 1:
            for qid, q in QUESTS.items():
                state = g.save["quests"].get(qid, "active")
                col = GREEN if state == "done" else WHITE
                prog_val = {"q_memories": g.stats["memories"], "q_coins": g.save["coins"],
                            "q_boss": g.stats["bosses"], "q_speed": g.stats["speedruns"]}.get(qid, 0)
                draw_text(surf, q["name"], 100, y, col, 17, bold=True)
                draw_text_wrap(surf, f"{q['desc']}  ({min(prog_val, q['goal'])}/{q['goal']}) "
                                     f"{('[COMPLETADA]' if state == 'done' else '')}",
                               120, y + 24, WIDTH - 260, GREY, 13)
                y += 70
        elif self.tab == 2:
            for aid, name in Progression.ACHIEVEMENTS.items():
                have = aid in g.save["achievements"]
                draw_text(surf, ("* " if have else "- ") + name, 100, y,
                          GOLD if have else DARKGREY, 16)
                y += 30
        else:
            descs = {
                "drone": "Dron defectuoso. Rápido y molesto.",
                "crawler": "Criatura de las sombras que patrulla en silencio.",
                "heavy": "Robot pesado. Lento pero brutal.",
                "flyer": "Enemigo volador que ignora la gravedad.",
                "sniper": "Francotirador tecnológico. Dispara desde lejos.",
                "mimic": "Imita tus movimientos. Confúndelo con espejos.",
                "guardian": "Guardián de secretos. Duro de pelar.",
            }
            for kind in Enemy.KIND_STATS:
                have = kind in g.save["enemies_log"]
                draw_text(surf, ("[X] " if have else "[ ] ") + kind.upper(), 100, y,
                          WHITE if have else DARKGREY, 15)
                if have:
                    draw_text(surf, descs[kind], 260, y, GREY, 12)
                y += 28


# ---------------- AJUSTES ----------------
class SettingsScene(Scene):
    def __init__(self, g):
        self.g = g
        self.sel = 0

    def handle_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            s = self.g.save["settings"]
            if ev.key in (pygame.K_UP, pygame.K_w):
                self.sel = max(0, self.sel - 1)
            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                self.sel = min(2, self.sel + 1)
            elif ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                d = -0.1 if ev.key == pygame.K_LEFT else 0.1
                if self.sel == 0:
                    s["music"] = round(max(0, min(1, s["music"] + d)), 2)
                    self.g.audio.set_music_volume(s["music"])
                elif self.sel == 1:
                    s["sfx"] = round(max(0, min(1, s["sfx"] + d)), 2)
                    self.g.audio.set_sfx_volume(s["sfx"])
                self.g.save_game()
            elif ev.key == pygame.K_ESCAPE:
                self.g.scene = TitleScene(self.g)

    def update(self, dt):
        pass

    def draw(self, surf):
        surf.fill((12, 10, 30))
        draw_text(surf, "AJUSTES", WIDTH // 2, 80, WHITE, 30, center=True, bold=True)
        s = self.g.save["settings"]
        rows = [("Música", s["music"]), ("Efectos de sonido", s["sfx"]),
                ("(los cambios se guardan solos)", "")]
        for i, (name, val) in enumerate(rows):
            col = WHITE if i == self.sel else GREY
            if val == "":
                draw_text(surf, name, 280, 180 + i * 60, DARKGREY, 12)
            else:
                draw_text(surf, name, 280, 180 + i * 60, col, 18)
                w = int(200 * val)
                pygame.draw.rect(surf, (40, 36, 80), (520, 184 + i * 60, 200, 14), border_radius=6)
                pygame.draw.rect(surf, CYAN, (520, 184 + i * 60, w, 14), border_radius=6)
                draw_text(surf, f"{int(val * 100)}%", 740, 180 + i * 60, col, 15)
        draw_text(surf, "Flechas: ajustar   ESC: volver", WIDTH // 2, 440, GREY, 13, center=True)


# ---------------------------------------------------------------------
# SECCIÓN 17: ARRANQUE
# ---------------------------------------------------------------------
if __name__ == "__main__":
    ensure_saves()
    try:
        Game().run()
    except Exception:
        import traceback
        traceback.print_exc()
        try:
            input("Se produjo un error. Pulsa ENTER para cerrar...")
        except Exception:
            pass

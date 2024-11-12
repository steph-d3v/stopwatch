# ---------------------------------------------------------------------------
# Implémentation d'un chronomètre
# ---------------------------------------------------------------------------
# Auteur : Steph (https://github.com/steph-d3v/)
# Date   : 1er novembre 2024
# ---------------------------------------------------------------------------
# Affichage des chiffres sous forme de matrices de "pixels"
#
# ■ ■ ■ ■        ■  ■ ■ ■ ■  ■ ■ ■ ■  ■     ■  ■ ■ ■ ■  ■ ■ ■ ■  ■ ■ ■ ■  ■ ■ ■ ■  ■ ■ ■ ■
# ■     ■        ■        ■        ■  ■     ■  ■        ■              ■  ■     ■  ■     ■
# ■     ■        ■  ■ ■ ■ ■  ■ ■ ■ ■  ■ ■ ■ ■  ■ ■ ■ ■  ■ ■ ■ ■        ■  ■ ■ ■ ■  ■ ■ ■ ■
# ■     ■        ■  ■              ■        ■        ■  ■     ■        ■  ■     ■        ■
# ■ ■ ■ ■        ■  ■ ■ ■ ■  ■ ■ ■ ■        ■  ■ ■ ■ ■  ■ ■ ■ ■        ■  ■ ■ ■ ■  ■ ■ ■ ■
#
# Encodage hexadécimal des matrices de "pixels" pour chaque chiffre de 0 à 9
# => chaque digit hexadécimal encode les bits "allumés" d'une ligne de matrice
#
# 0: f999f
# 1: 11111
# 2: f1f8f
# 3: f1f1f
# 4: 99f11
# 5: f8f1f
# 6: f8f9f
# 7: f1111
# 8: f9f9f
# 9: f9f1f
# ---------------------------------------------------------------------------

import curses
from colorsys import hls_to_rgb as hls2rgb
from time import time

PALETTE_START_INDEX = 16
HELP = "[S]: START | STOP    [R]: RESET    [Q]: Quit"
DIGITS = "f999f11111f1f8ff1f1f99f11f8f1ff8f9ff1111f9f9ff9f1f"


class Timer:
    _started: bool
    _time_start: float
    _time_stop: float

    def __init__(self):
        self._started = False
        self.reset()

    @property
    def is_started(self) -> bool:
        return self._started

    @property
    def elapsed_time(self) -> float:
        return (time() if self._started else self._time_stop) - self._time_start

    def reset(self):
        self._time_start = self._time_stop = 0

    def start(self):
        if self._time_start:
            self._time_start += time() - self._time_stop
        else:
            self._time_start = time()
        self._started = True

    def stop(self):
        self._time_stop = time()
        self._started = False


class App:
    _instance = None  # singleton

    def __new__(cls, *args: object, **kwargs: object):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    _running: bool
    _hue: int
    _timer: Timer
    _digits: tuple[tuple[int, ...], ...]
    _screen: curses.window

    def __init__(self, screen: curses.window, *args: object, **kwargs: object):
        self._setup()
        self._unpack_digits()
        self._setup_screen(screen)
        self._init_colors()
        self._loop()
        self._end_screen()

    def _setup(self):
        self._running = True
        self._timer = Timer()

    def _unpack_digits(self):
        self._digits = tuple(
            map(lambda n: tuple(int(n[j], 16) for j in range(5)), (DIGITS[i : i + 5] for i in range(0, len(DIGITS), 5)))
        )

    def _setup_screen(self, screen: curses.window):
        curses.curs_set(0)
        screen.nodelay(True)
        self._screen = screen
        self._init_colors()

    def _end_screen(self):
        curses.curs_set(1)
        curses.endwin()

    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()
        self._set_hue(0)
        curses.init_color(PALETTE_START_INDEX + 1, 1000, 1000, 0)
        curses.init_pair(PALETTE_START_INDEX, -1, PALETTE_START_INDEX)
        curses.init_pair(PALETTE_START_INDEX + 1, PALETTE_START_INDEX + 1, -1)

    def _set_hue(self, hue: int):
        self._hue = hue
        curses.init_color(PALETTE_START_INDEX, *(round(1000 * k) for k in hls2rgb(hue / 360, 0.6, 1)))

    def _get_color(self, n: int) -> int:
        return curses.color_pair(PALETTE_START_INDEX + n)

    def _reset(self):
        self._set_hue(0)
        self._timer.reset()

    def _loop(self):
        while self._running:
            self._read_keys()
            self._update()
            self._draw()
            self._screen.timeout(10)

    def _read_keys(self):
        if (c := self._screen.getch()) in {ord("q"), ord("Q")}:
            self._running = False
        elif c in {ord("r"), ord("R")} and not self._timer.is_started:
            self._reset()
        elif c in {ord("s"), ord("S")}:
            self._timer.stop() if self._timer.is_started else self._timer.start()

    def _update(self):
        if self._timer.is_started:
            self._set_hue((self._hue + 1) % 360)

    def _draw(self):
        s, cs = f"{self._timer.elapsed_time:.2f}".split(".")
        ls, lcs = len(s), len(cs)
        h, w = self._screen.getmaxyx()
        x, y = (w - 2 * (5 * (ls + lcs) + 3) - 1) // 2, (h - 8) // 2
        self._screen.clear()
        self._draw_number(s, x, y)
        self._draw_number(cs, x + 10 * ls + 6, y)
        if self._timer.is_started or (int(time() * 2)) & 0b1:
            self._screen.addstr(y + 4, x + 10 * ls + 1, "  ", self._get_color(0))
        self._screen.addstr(y + 7, (w - len(HELP)) // 2, HELP, self._get_color(1))
        self._screen.refresh()

    def _draw_number(self, n: str, x: int, y: int):
        for i, c in enumerate(n):
            self._draw_digit(int(c), x + i * 10, y)

    def _draw_digit(self, n: int, x: int, y: int):
        for i, line in enumerate(self._digits[n]):
            for j in range(4):
                if line & (1 << (3 - j)):
                    self._screen.addstr(y + i, x + 2 * j, "  ", self._get_color(0))


if __name__ == "__main__":
    curses.wrapper(App)

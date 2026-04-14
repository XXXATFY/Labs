import sys
from dataclasses import dataclass, field

import pygame


WIDTH, HEIGHT = 1280, 780
FPS = 60

BG = (28, 32, 40)
PANEL = (40, 46, 58)
BUS = (83, 90, 105)
SEAT_FREE = (145, 160, 184)
SEAT_OCC = (112, 190, 132)
TEXT = (235, 238, 245)
BAD = (236, 92, 92)
OK = (120, 220, 140)
WINDOW = (122, 188, 255)

REQ_LABELS = {
    "window": "у окна",
    "alone": "сидеть один",
    "no_smell": "без запаха",
    "quiet": "в тишине",
}

PROP_LABELS = {
    "smelly": "пахнет",
    "music": "слушает музыку",
}


@dataclass
class Passenger:
    pid: str
    requirements: set[str] = field(default_factory=set)
    properties: set[str] = field(default_factory=set)
    seat_index: int | None = None


class BusSeatingGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Автобус: Идеальная рассадка")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("arial", 20)
        self.small_font = pygame.font.SysFont("arial", 16)
        self.big_font = pygame.font.SysFont("arial", 46, bold=True)

        self.state = "menu"
        self.running = True

        self.seats = self._build_seats()
        self.neighbors = self._build_neighbors()
        self.window_seats = {i for i, s in enumerate(self.seats) if s["is_window"]}

        self.passengers: list[Passenger] = []
        self.next_id = 1

        self.drag_pid: str | None = None
        self.drag_origin: int | str | None = None
        self.drag_pos = (0, 0)
        self.waiting_hitboxes: dict[str, pygame.Rect] = {}

        self.selected_bonus: str | None = None
        self.bonuses = {
            "earplugs": 1,
            "deodorant": 1,
            "relax_card": 1,
        }

        self.stop_index = 0
        self.stop_plans = self._build_stop_plans()
        self.message = ""

        self.menu_start_btn = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 10, 360, 68)
        self.menu_exit_btn = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 + 80, 360, 68)
        self.next_stop_btn = pygame.Rect(WIDTH - 300, HEIGHT - 100, 220, 56)

    def _build_seats(self):
        seats = []
        start_x = 250
        start_y = 120
        gap_x = 130
        gap_y = 115
        for row in range(4):
            y = start_y + row * gap_y
            for col in range(4):
                x = start_x + col * gap_x + (28 if col >= 2 else 0)
                is_window = col in (0, 3)
                seats.append({"row": row, "col": col, "rect": pygame.Rect(x, y, 92, 62), "is_window": is_window})
        return seats

    def _build_neighbors(self):
        neighbors = {i: [] for i in range(len(self.seats))}
        for i, seat_a in enumerate(self.seats):
            for j, seat_b in enumerate(self.seats):
                if i == j:
                    continue
                dist = abs(seat_a["row"] - seat_b["row"]) + abs(seat_a["col"] - seat_b["col"])
                if dist == 1:
                    neighbors[i].append(j)
        return neighbors

    def _build_stop_plans(self):
        return [
            {
                "arrivals": [
                    ({"window"}, set()),
                    ({"quiet"}, {"smelly"}),
                    ({"alone"}, {"music"}),
                    ({"no_smell"}, set()),
                    ({"quiet", "window"}, set()),
                    (set(), {"music"}),
                ],
                "departures": [],
            },
            {
                "arrivals": [
                    ({"no_smell"}, {"music"}),
                    ({"alone", "quiet"}, set()),
                    ({"window"}, {"smelly"}),
                    (set(), set()),
                    ({"quiet"}, set()),
                ],
                "departures": ["P2", "P4"],
            },
            {
                "arrivals": [
                    ({"window", "quiet"}, {"music"}),
                    ({"no_smell"}, {"smelly"}),
                    ({"alone"}, set()),
                    (set(), {"music"}),
                ],
                "departures": ["P1", "P3", "P6"],
            },
        ]

    def start_new_game(self):
        self.state = "playing"
        self.stop_index = 0
        self.passengers = []
        self.next_id = 1
        self.drag_pid = None
        self.drag_origin = None
        self.selected_bonus = None
        self.message = ""
        self.bonuses = {"earplugs": 1, "deodorant": 1, "relax_card": 1}
        self._apply_stop_plan(first=True)

    def _new_passenger(self, requirements, properties):
        p = Passenger(pid=f"P{self.next_id}", requirements=set(requirements), properties=set(properties), seat_index=None)
        self.next_id += 1
        return p

    def _apply_stop_plan(self, first=False):
        plan = self.stop_plans[self.stop_index]
        if not first:
            for pid in plan["departures"]:
                p = self._find_passenger(pid)
                if p:
                    self.passengers.remove(p)

        for reqs, props in plan["arrivals"]:
            self.passengers.append(self._new_passenger(reqs, props))

        if len(self.passengers) > len(self.seats):
            self.state = "lose"
            self.message = "В автобусе не хватает мест для всех пассажиров."

    def _find_passenger(self, pid):
        for p in self.passengers:
            if p.pid == pid:
                return p
        return None

    def _occupied_by_seat(self):
        occ = {}
        for p in self.passengers:
            if p.seat_index is not None:
                occ[p.seat_index] = p
        return occ

    def _is_passenger_happy(self, passenger: Passenger):
        if passenger.seat_index is None:
            return False, "не сидит"

        seat_index = passenger.seat_index
        if "window" in passenger.requirements and seat_index not in self.window_seats:
            return False, "не у окна"

        occ = self._occupied_by_seat()
        neigh = self.neighbors[seat_index]

        if "alone" in passenger.requirements:
            for n in neigh:
                if n in occ:
                    return False, "рядом есть сосед"

        if "quiet" in passenger.requirements:
            for n in neigh:
                other = occ.get(n)
                if other and "music" in other.properties:
                    return False, "рядом шумный"

        if "no_smell" in passenger.requirements:
            for n in neigh:
                other = occ.get(n)
                if other and "smelly" in other.properties:
                    return False, "рядом запах"

        return True, ""

    def _all_happy(self):
        if not self.passengers:
            return False
        for p in self.passengers:
            happy, _ = self._is_passenger_happy(p)
            if not happy:
                return False
        return True

    def _passenger_at_pos(self, pos):
        for p in self.passengers:
            if p.seat_index is None:
                rect = self.waiting_hitboxes.get(p.pid)
                if rect and rect.collidepoint(pos):
                    return p
            else:
                seat_rect = self.seats[p.seat_index]["rect"]
                if pygame.Rect(seat_rect.x + 16, seat_rect.y + 12, 56, 38).collidepoint(pos):
                    return p
        return None

    def _seat_at_pos(self, pos):
        for idx, seat in enumerate(self.seats):
            if seat["rect"].collidepoint(pos):
                return idx
        return None

    def _use_bonus(self, target: Passenger):
        if not self.selected_bonus:
            return

        if self.selected_bonus == "earplugs":
            if "music" in target.properties and self.bonuses["earplugs"] > 0:
                target.properties.remove("music")
                self.bonuses["earplugs"] -= 1
                self.message = f"Беруши применены к {target.pid}."
            else:
                self.message = "Беруши не сработали."

        elif self.selected_bonus == "deodorant":
            if "smelly" in target.properties and self.bonuses["deodorant"] > 0:
                target.properties.remove("smelly")
                self.bonuses["deodorant"] -= 1
                self.message = f"Дезодорант применён к {target.pid}."
            else:
                self.message = "Дезодорант не сработал."

        elif self.selected_bonus == "relax_card":
            if target.requirements and self.bonuses["relax_card"] > 0:
                removable = None
                for k in ("alone", "window", "quiet", "no_smell"):
                    if k in target.requirements:
                        removable = k
                        break
                if removable:
                    target.requirements.remove(removable)
                    self.bonuses["relax_card"] -= 1
                    self.message = f"Талон спокойствия снижает требования {target.pid}."
                else:
                    self.message = "Талон спокойствия не сработал."
            else:
                self.message = "Талон спокойствия не сработал."

        self.selected_bonus = None

    def _handle_menu_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.menu_start_btn.collidepoint(event.pos):
                self.start_new_game()
            elif self.menu_exit_btn.collidepoint(event.pos):
                self.running = False

    def _handle_play_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.next_stop_btn.collidepoint(event.pos):
                if self._all_happy():
                    if self.stop_index >= 2:
                        self.state = "win"
                        self.message = "Отлично! Все 3 остановки пройдены."
                    else:
                        self.stop_index += 1
                        self._apply_stop_plan(first=False)
                        self.message = f"Остановка {self.stop_index + 1}: новые пассажиры вошли."
                else:
                    self.message = "Нельзя ехать дальше: кто-то не доволен рассадкой."
                return

            bonus_rects = self._draw_bonus_buttons(draw=False)
            for key, rect in bonus_rects.items():
                if rect.collidepoint(event.pos):
                    if self.bonuses[key] > 0:
                        self.selected_bonus = key
                        self.message = "Выбери пассажира для бонуса."
                    else:
                        self.message = "Этот бонус уже использован."
                    return

            target = self._passenger_at_pos(event.pos)
            if self.selected_bonus and target:
                self._use_bonus(target)
                return

            if target:
                self.drag_pid = target.pid
                self.drag_origin = target.seat_index if target.seat_index is not None else "waiting"
                self.drag_pos = event.pos

        elif event.type == pygame.MOUSEMOTION and self.drag_pid:
            self.drag_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag_pid:
            p = self._find_passenger(self.drag_pid)
            if p:
                target_seat = self._seat_at_pos(event.pos)
                occ = self._occupied_by_seat()
                if target_seat is not None and target_seat not in occ:
                    p.seat_index = target_seat
                else:
                    waiting_rect = pygame.Rect(40, HEIGHT - 220, WIDTH - 360, 180)
                    if waiting_rect.collidepoint(event.pos):
                        p.seat_index = None
            self.drag_pid = None
            self.drag_origin = None

    def _draw_menu(self):
        self.screen.fill(BG)
        title = self.big_font.render("Автобус: Идеальная рассадка", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 190)))

        subtitle = self.font.render("Рассади пассажиров так, чтобы все были довольны за 3 остановки.", True, TEXT)
        self.screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 250)))

        pygame.draw.rect(self.screen, (72, 128, 210), self.menu_start_btn, border_radius=12)
        pygame.draw.rect(self.screen, (130, 78, 78), self.menu_exit_btn, border_radius=12)

        self.screen.blit(self.font.render("Играть", True, TEXT), (self.menu_start_btn.x + 145, self.menu_start_btn.y + 20))
        self.screen.blit(self.font.render("Выход", True, TEXT), (self.menu_exit_btn.x + 145, self.menu_exit_btn.y + 20))

    def _draw_bus(self):
        bus_rect = pygame.Rect(190, 70, 690, 565)
        pygame.draw.rect(self.screen, BUS, bus_rect, border_radius=14)

        pygame.draw.polygon(self.screen, (60, 66, 79), [(210, 80), (860, 80), (840, 610), (230, 610)])
        pygame.draw.rect(self.screen, (66, 74, 90), (475, 80, 120, 530), border_radius=8)

        for i, seat in enumerate(self.seats):
            seat_rect = seat["rect"]
            occ = any(p.seat_index == i for p in self.passengers)
            col = SEAT_OCC if occ else SEAT_FREE
            pygame.draw.rect(self.screen, col, seat_rect, border_radius=8)
            pygame.draw.rect(self.screen, (35, 40, 50), seat_rect, width=2, border_radius=8)
            if seat["is_window"]:
                pygame.draw.circle(self.screen, WINDOW, (seat_rect.x + seat_rect.w - 14, seat_rect.y + 10), 6)

    def _draw_waiting_panel(self):
        panel_rect = pygame.Rect(30, HEIGHT - 230, WIDTH - 340, 195)
        pygame.draw.rect(self.screen, PANEL, panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, (80, 90, 112), panel_rect, width=2, border_radius=12)
        self.screen.blit(self.font.render("Ожидают/доступны для перемещения", True, TEXT), (50, HEIGHT - 220))

        waiting = [p for p in self.passengers if p.seat_index is None and p.pid != self.drag_pid]
        self.waiting_hitboxes = {}
        start_x, start_y = 65, HEIGHT - 175
        for idx, p in enumerate(waiting):
            x = start_x + (idx % 10) * 90
            y = start_y + (idx // 10) * 80
            self._draw_passenger(p, (x, y), compact=True)
            self.waiting_hitboxes[p.pid] = pygame.Rect(x - 22, y - 22, 44, 44)

    def _draw_passenger(self, p: Passenger, center, compact=False):
        happy, reason = self._is_passenger_happy(p)
        color = OK if happy else BAD
        if p.seat_index is None:
            color = (243, 198, 110)

        pygame.draw.circle(self.screen, color, center, 20)
        pygame.draw.circle(self.screen, (20, 24, 30), center, 20, 2)
        pid_s = self.small_font.render(p.pid, True, (15, 15, 20))
        self.screen.blit(pid_s, pid_s.get_rect(center=center))

        if compact:
            return

        reqs = ", ".join(REQ_LABELS[r] for r in sorted(p.requirements)) if p.requirements else "нет"
        props = ", ".join(PROP_LABELS[r] for r in sorted(p.properties)) if p.properties else "нет"
        self.screen.blit(self.small_font.render(f"Треб: {reqs}", True, TEXT), (center[0] - 40, center[1] + 30))
        self.screen.blit(self.small_font.render(f"Свойства: {props}", True, TEXT), (center[0] - 40, center[1] + 47))
        if not happy and p.seat_index is not None and reason:
            self.screen.blit(self.small_font.render(reason, True, BAD), (center[0] - 40, center[1] + 63))

    def _draw_seated_passengers(self):
        for i, seat in enumerate(self.seats):
            p = next((x for x in self.passengers if x.seat_index == i), None)
            if not p or p.pid == self.drag_pid:
                continue
            center = (seat["rect"].x + 46, seat["rect"].y + 32)
            happy, _ = self._is_passenger_happy(p)
            col = OK if happy else BAD
            pygame.draw.circle(self.screen, col, center, 18)
            pygame.draw.circle(self.screen, (20, 24, 30), center, 18, 2)
            pid_s = self.small_font.render(p.pid, True, (10, 10, 18))
            self.screen.blit(pid_s, pid_s.get_rect(center=center))

    def _draw_bonus_buttons(self, draw=True):
        right_x = WIDTH - 320
        rects = {
            "earplugs": pygame.Rect(right_x, 145, 280, 60),
            "deodorant": pygame.Rect(right_x, 220, 280, 60),
            "relax_card": pygame.Rect(right_x, 295, 280, 60),
        }
        if draw:
            self.screen.blit(self.font.render("Бонусы (по 1 разу)", True, TEXT), (right_x, 105))
            labels = {
                "earplugs": "Беруши (убрать музыку)",
                "deodorant": "Дезодорант (убрать запах)",
                "relax_card": "Талон спокойствия (убрать треб.)",
            }
            for key, rect in rects.items():
                active = self.bonuses[key] > 0
                selected = self.selected_bonus == key
                color = (86, 154, 113) if active else (92, 92, 92)
                if selected:
                    color = (203, 151, 74)
                pygame.draw.rect(self.screen, color, rect, border_radius=9)
                pygame.draw.rect(self.screen, (20, 26, 32), rect, width=2, border_radius=9)
                label = self.small_font.render(f"{labels[key]} | осталось: {self.bonuses[key]}", True, TEXT)
                self.screen.blit(label, (rect.x + 10, rect.y + 20))
        return rects

    def _draw_side_info(self):
        x = WIDTH - 320
        self.screen.blit(self.font.render(f"Остановка: {self.stop_index + 1} / 3", True, TEXT), (x, 28))

        total = len(self.passengers)
        seated = len([p for p in self.passengers if p.seat_index is not None])
        happy = len([p for p in self.passengers if self._is_passenger_happy(p)[0]])

        self.screen.blit(self.small_font.render(f"Пассажиры: {total}", True, TEXT), (x, 60))
        self.screen.blit(self.small_font.render(f"Сидят: {seated}", True, TEXT), (x, 82))
        self.screen.blit(self.small_font.render(f"Довольны: {happy}", True, TEXT), (x, 104))

        pygame.draw.rect(self.screen, (80, 130, 200), self.next_stop_btn, border_radius=10)
        txt = "Финиш" if self.stop_index >= 2 else "След. остановка"
        self.screen.blit(self.font.render(txt, True, TEXT), (self.next_stop_btn.x + 40, self.next_stop_btn.y + 15))

        hint_lines = [
            "ЛКМ: перетаскивай пассажира",
            "Сажай в свободные места",
            "Чтобы ехать дальше —",
            "все должны быть довольны",
        ]
        for i, line in enumerate(hint_lines):
            self.screen.blit(self.small_font.render(line, True, TEXT), (x, 380 + i * 22))

        if self.message:
            msg = self.small_font.render(self.message[:68], True, (244, 220, 150))
            self.screen.blit(msg, (40, 22))

    def _draw_dragging(self):
        if not self.drag_pid:
            return
        p = self._find_passenger(self.drag_pid)
        if not p:
            return
        pygame.draw.circle(self.screen, (255, 221, 137), self.drag_pos, 22)
        pygame.draw.circle(self.screen, (20, 24, 30), self.drag_pos, 22, 2)
        label = self.small_font.render(p.pid, True, (20, 20, 20))
        self.screen.blit(label, label.get_rect(center=self.drag_pos))

    def _draw_game(self):
        self.screen.fill(BG)
        self._draw_bus()
        self._draw_waiting_panel()
        self._draw_seated_passengers()
        self._draw_bonus_buttons(draw=True)
        self._draw_side_info()
        self._draw_dragging()

    def _draw_end(self, win=True):
        self.screen.fill(BG)
        msg = "Победа!" if win else "Поражение"
        color = OK if win else BAD
        title = self.big_font.render(msg, True, color)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 220)))

        sub = self.font.render(self.message or "", True, TEXT)
        self.screen.blit(sub, sub.get_rect(center=(WIDTH // 2, 280)))

        retry = self.font.render("Нажми ENTER, чтобы вернуться в меню", True, TEXT)
        self.screen.blit(retry, retry.get_rect(center=(WIDTH // 2, 360)))

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_RETURN and self.state in ("win", "lose"):
                        self.state = "menu"
                if self.state == "menu":
                    self._handle_menu_events(event)
                elif self.state == "playing":
                    self._handle_play_events(event)

            if self.state == "menu":
                self._draw_menu()
            elif self.state == "playing":
                self._draw_game()
            elif self.state == "win":
                self._draw_end(win=True)
            elif self.state == "lose":
                self._draw_end(win=False)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit(0)


if __name__ == "__main__":
    BusSeatingGame().run()

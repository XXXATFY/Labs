import arcade
import arcade.gui
import math
import random
from dataclasses import dataclass
from pathlib import Path
from arcade.gui.widgets.buttons import UITextureButtonStyle
from PIL import Image, ImageDraw


Color = tuple[int, int, int, int]

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "BUSGAME"

ASSETS_DIR = Path("assets")
BUTTONS_DIR = ASSETS_DIR / "buttons"
ITEMS_DIR = ASSETS_DIR / "items"
SCREENS_DIR = ASSETS_DIR / "screens"

PASTEL_SKY_LIGHT: Color = (231, 244, 255, 255)
PASTEL_SKY: Color = (203, 227, 247, 255)
PASTEL_SKY_ACCENT: Color = (160, 198, 231, 255)
PASTEL_YELLOW: Color = (255, 231, 161, 255)
PASTEL_YELLOW_LIGHT: Color = (255, 242, 197, 255)
PASTEL_YELLOW_DARK: Color = (232, 197, 111, 255)
TEXT_DARK: Color = (49, 72, 93, 255)
SEAT_SMELLY_COLOR: Color = (176, 229, 182, 255)
SEAT_LOUD_COLOR: Color = (205, 181, 255, 255)
SEAT_SMELLY_LOUD_COLOR: Color = (195, 173, 233, 255)
PERSON_COLORS: tuple[Color, ...] = (
    (255, 182, 185, 255),
    (255, 223, 186, 255),
    (255, 255, 186, 255),
    (186, 255, 201, 255),
    (186, 225, 255, 255),
    (220, 198, 255, 255),
    (255, 204, 229, 255),
    (204, 255, 255, 255),
)
ITEM_ORDER = ("perfume", "headphones", "phone")
ITEM_LABELS = {
    "perfume": "Духи",
    "headphones": "Наушники",
    "phone": "Телефон",
}
ITEM_COLORS: dict[str, Color] = {
    "perfume": (255, 224, 234, 255),
    "headphones": (221, 235, 255, 255),
    "phone": (234, 255, 227, 255),
}


def load_texture_if_exists(
    path: Path, *, fix_transparent_rgb: bool = False
) -> arcade.Texture | None:
    if not path.exists():
        return None
    try:
        if fix_transparent_rgb:
            image = Image.open(path).convert("RGBA")
            pixels = list(image.getdata())
            visible_pixels = [pixel for pixel in pixels if pixel[3] > 0]
            if visible_pixels:
                avg_r = sum(pixel[0] for pixel in visible_pixels) // len(visible_pixels)
                avg_g = sum(pixel[1] for pixel in visible_pixels) // len(visible_pixels)
                avg_b = sum(pixel[2] for pixel in visible_pixels) // len(visible_pixels)
                corrected_pixels = [
                    (avg_r, avg_g, avg_b, pixel[3]) if pixel[3] <= 24 else pixel for pixel in pixels
                ]
                image.putdata(corrected_pixels)
            return arcade.Texture(image=image)
        return arcade.load_texture(str(path))
    except Exception:
        return None


def load_button_texture_set(name: str) -> dict[str, arcade.Texture | None]:
    normal = load_texture_if_exists(BUTTONS_DIR / f"{name}_defolt.png", fix_transparent_rgb=True)
    hover = load_texture_if_exists(BUTTONS_DIR / f"{name}_hover.png", fix_transparent_rgb=True) or normal
    active = load_texture_if_exists(BUTTONS_DIR / f"{name}_active.png", fix_transparent_rgb=True) or hover or normal
    return {"normal": normal, "hover": hover, "active": active}


def draw_texture_lbwh(
    texture: arcade.Texture,
    left: float,
    bottom: float,
    width: float,
    height: float,
    *,
    alpha: int = 255,
    color: Color | arcade.types.Color = (255, 255, 255, 255),
) -> None:
    arcade_color = color
    if not isinstance(arcade_color, arcade.types.Color):
        arcade_color = arcade.types.Color(*arcade_color)

    arcade.draw_texture_rect(
        texture=texture,
        rect=arcade.Rect.from_kwargs(
            left=left,
            bottom=bottom,
            width=width,
            height=height,
        ),
        alpha=alpha,
        color=arcade_color,
    )


def shift_color(color: Color, delta: int) -> Color:
    red = max(0, min(255, color[0] + delta))
    green = max(0, min(255, color[1] + delta))
    blue = max(0, min(255, color[2] + delta))
    return (red, green, blue, color[3])


def make_rounded_button_texture(
    width: int,
    height: int,
    fill_color: Color,
    border_color: Color,
    border_width: int,
    radius: int,
) -> arcade.Texture:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    inset = border_width // 2
    draw.rounded_rectangle(
        (inset, inset, width - 1 - inset, height - 1 - inset),
        radius=min(radius, width // 2, height // 2),
        fill=fill_color,
        outline=border_color,
        width=border_width,
    )
    return arcade.Texture(image=image)


@dataclass
class Person:
    name: str
    x: float
    y: float
    radius: float
    color: Color
    platform_slot: int
    avatar_color: str = "blue"
    stinks: bool = False
    listens_music: bool = False
    has_perfume: bool = False
    has_headphones: bool = False
    has_phone: bool = False
    wants_window: bool = False
    wants_sleep: bool = False
    wants_chat: bool = False
    wants_solitude: bool = False
    smell_sensitive: bool = False
    seat_index: int | None = None
    is_happy: bool | None = None

    def contains(self, px: float, py: float) -> bool:
        return math.hypot(self.x - px, self.y - py) <= self.radius

    @property
    def smells_good(self) -> bool:
        return self.has_perfume

    @property
    def in_headphones(self) -> bool:
        return self.has_headphones

    @property
    def plays_phone(self) -> bool:
        return self.has_phone

    @property
    def makes_loud_noise(self) -> bool:
        return self.listens_music and not self.in_headphones

    def active_property_lines(self) -> list[str]:
        lines: list[str] = []
        if self.stinks:
            lines.append("Воняет")
        if self.listens_music:
            lines.append("Слушает музыку")
        if self.smells_good:
            lines.append("Вкусно пахнет")
        if self.in_headphones:
            lines.append("В наушниках")
        if self.plays_phone:
            lines.append("Играет в телефон")
        return lines

    def active_requirement_lines(self) -> list[str]:
        lines: list[str] = []
        if self.wants_window:
            lines.append("Хочет сидеть у окна")
        if self.wants_sleep:
            lines.append("Хочет спать")
        if self.wants_chat:
            lines.append("Хочет болтать")
        if self.wants_solitude:
            lines.append("Хочет сидеть в одиночестве")
        if self.smell_sensitive:
            lines.append("Не терпит запахи")
        return lines


@dataclass
class Seat:
    row: int
    column: int
    center_x: float
    center_y: float
    size: float
    is_window: bool
    faces_right: bool = False
    is_smelly: bool = False
    is_loud: bool = False
    occupant: Person | None = None

    def contains(self, px: float, py: float) -> bool:
        half = self.size / 2
        return (
            self.center_x - half <= px <= self.center_x + half
            and self.center_y - half <= py <= self.center_y + half
        )


class GameView(arcade.View):
    BUS_HEIGHT_PIXELS = int(720 * 0.60)
    LEVEL_PLATFORM_COUNTS = (6, 8)
    TRAVEL_DURATION_SECONDS = 3.2
    FIXED_BOTTOM_AREA = (352.0, 0.0, 576.0, 144.0)
    FIXED_PLATFORM_SLOTS = (
        (409.6, 109.44),
        (501.76, 109.44),
        (593.92, 109.44),
        (686.08, 109.44),
        (778.24, 109.44),
        (870.4, 109.44),
        (409.6, 34.56),
        (501.76, 34.56),
    )
    FIXED_BUS_X = 266.0
    FIXED_BUS_Y = 243.0
    FIXED_TRAVEL_BUS_X = 267.0
    FIXED_TRAVEL_BUS_Y = 243.0
    FIXED_SEAT_SIZE = 36.0
    FIXED_ITEM_SLOT_RECTS = {
        "perfume": (1125.0, 590.0, 75.0, 75.0),
        "headphones": (1125.0, 499.0, 75.0, 75.0),
        "phone": (1125.0, 408.0, 75.0, 75.0),
    }
    FIXED_DEPART_BUTTON_X = 1084.0
    FIXED_DEPART_BUTTON_Y = 20.0
    FIXED_VICTORY_PANEL = (210.0, 220.0, 860.0, 280.0)
    FIXED_VICTORY_RESTART_X = 244.0
    FIXED_VICTORY_RESTART_Y = 260.0
    FIXED_VICTORY_EXIT_X = 676.0
    FIXED_VICTORY_EXIT_Y = 260.0
    FIXED_LEVEL_BADGE_X = 460.0
    FIXED_LEVEL_BADGE_Y = 665.0
    AVATAR_COLORS = ("blue", "orange", "red", "yellow")
    EFFECT_TAGS = ("headphones", "phone", "perfume", "stink", "noise")
    NAME_POOL = (
        "Анна",
        "Борис",
        "Вика",
        "Глеб",
        "Даша",
        "Егор",
        "Жанна",
        "Илья",
        "Кира",
        "Лев",
        "Маша",
        "Никита",
        "Оля",
        "Паша",
        "Рита",
        "Саша",
        "Таня",
        "Уля",
        "Федя",
        "Юля",
        "Яна",
    )

    def __init__(self) -> None:
        super().__init__()
        self.bottom_area: tuple[float, float, float, float] = (0, 0, 0, 0)
        self.bus_area: tuple[float, float, float, float] = (0, 0, 0, 0)
        self.platform_slots: list[tuple[float, float]] = []
        self.seats: list[Seat] = []
        self.people: list[Person] = []
        self.level_index = 0
        self.is_traveling = False
        self.travel_elapsed = 0.0
        self.is_victory = False
        self.name_index = 0
        self.item_counts: dict[str, int] = {key: 0 for key in ITEM_ORDER}
        self.dragged_person: Person | None = None
        self.drag_offset_x = 0.0
        self.drag_offset_y = 0.0
        self.dragged_item: str | None = None
        self.hovered_person: Person | None = None
        self.mouse_x = 0.0
        self.mouse_y = 0.0
        self.mouse_down_left = False
        self.rng = random.Random()
        self.background_texture = load_texture_if_exists(SCREENS_DIR / "levels.png")
        self.item_slots_overlay_texture = load_texture_if_exists(ITEMS_DIR / "background_1280_720.png")
        self.travel_texture = load_texture_if_exists(SCREENS_DIR / "level1_to_level2.png")
        self.bus_open_texture = (
            load_texture_if_exists(SCREENS_DIR / "bus_opendoor.png")
            or load_texture_if_exists(SCREENS_DIR / "bus.png")
            or load_texture_if_exists(SCREENS_DIR / "bus_1280_720.png")
        )
        self.bus_closed_texture = (
            load_texture_if_exists(SCREENS_DIR / "bus_closedoor.png") or self.bus_open_texture
        )
        self.item_icon_textures: dict[str, arcade.Texture | None] = {
            item_key: load_texture_if_exists(ITEMS_DIR / f"{item_key}.png")
            for item_key in ITEM_ORDER
        }
        self.game_button_textures: dict[str, dict[str, arcade.Texture | None]] = {
            "go": load_button_texture_set("go"),
            "play": load_button_texture_set("play"),
            "exit": load_button_texture_set("exit"),
        }
        self.level_badge_textures: list[arcade.Texture | None] = [
            load_texture_if_exists(BUTTONS_DIR / "level_1.png"),
            load_texture_if_exists(BUTTONS_DIR / "level_2.png"),
        ]
        self.flipped_texture_cache: dict[str, arcade.Texture] = {}
        self.guys_assets_root = Path("assets") / "guys"
        self.available_guy_textures: list[Path] = []
        self.guy_texture_cache: dict[tuple[str, str, str, str | None], arcade.Texture | None] = {}
        self._build_guy_texture_index()

    def _build_guy_texture_index(self) -> None:
        if not self.guys_assets_root.exists():
            self.available_guy_textures = []
            return
        self.available_guy_textures = [
            path for path in self.guys_assets_root.rglob("*.png") if path.is_file()
        ]

    def _color_aliases(self, color_key: str) -> tuple[str, ...]:
        aliases = {
            "blue": ("blue",),
            "orange": ("orange", "orenge"),
            "red": ("red",),
            "yellow": ("yellow", "yelllow"),
        }
        return aliases.get(color_key, (color_key,))

    def _mood_aliases(self, mood_key: str) -> tuple[str, ...]:
        if mood_key == "idle":
            return ("idle", "idel")
        return (mood_key,)

    def _find_guy_texture_path(
        self, color_key: str, orientation: str, mood: str, effect: str | None
    ) -> Path | None:
        if not self.available_guy_textures:
            return None

        color_tokens = self._color_aliases(color_key)
        mood_tokens = self._mood_aliases(mood)
        candidates: list[Path] = []

        for path in self.available_guy_textures:
            lowered = path.as_posix().lower()
            if orientation not in lowered:
                continue
            if not any(token in lowered for token in mood_tokens):
                continue
            if not any(token in lowered for token in color_tokens):
                continue
            if effect is None:
                if any(token in lowered for token in self.EFFECT_TAGS):
                    continue
            elif effect not in lowered:
                continue
            candidates.append(path)

        if candidates:
            return sorted(candidates, key=lambda value: len(value.as_posix()))[0]
        return None

    def _resolve_guy_texture_path(
        self, color_key: str, orientation: str, mood: str, effect: str | None
    ) -> Path | None:
        found = self._find_guy_texture_path(color_key, orientation, mood, effect)
        if found is not None:
            return found

        if effect is not None:
            found = self._find_guy_texture_path(color_key, orientation, mood, None)
            if found is not None:
                return found

        if mood != "idle":
            found = self._find_guy_texture_path(color_key, orientation, "idle", effect)
            if found is not None:
                return found
            return self._find_guy_texture_path(color_key, orientation, "idle", None)

        return None

    def _person_visual_effect(self, person: Person) -> str | None:
        if person.has_headphones:
            return "headphones"
        if person.has_phone:
            return "phone"
        if person.has_perfume:
            return "perfume"
        if person.stinks:
            return "stink"
        if person.listens_music:
            return "noise"
        return None

    def _person_visual_texture(self, person: Person) -> arcade.Texture | None:
        orientation = "front" if person.seat_index is None else "side"
        if person.seat_index is None:
            mood = "idle"
        elif person.is_happy:
            mood = "happy"
        else:
            mood = "sad"
        effect = self._person_visual_effect(person)
        cache_key = (person.avatar_color, orientation, mood, effect)

        if cache_key in self.guy_texture_cache:
            return self.guy_texture_cache[cache_key]

        texture_path = self._resolve_guy_texture_path(
            person.avatar_color, orientation, mood, effect
        )
        if texture_path is None:
            self.guy_texture_cache[cache_key] = None
            return None

        texture = arcade.load_texture(str(texture_path))
        self.guy_texture_cache[cache_key] = texture
        return texture

    def _flipped_texture(self, texture: arcade.Texture) -> arcade.Texture:
        cache_key = texture.cache_name
        if cache_key in self.flipped_texture_cache:
            return self.flipped_texture_cache[cache_key]
        flipped = texture.flip_horizontally()
        self.flipped_texture_cache[cache_key] = flipped
        return flipped

    def on_show_view(self) -> None:
        self.window.background_color = PASTEL_SKY
        self.window.set_mouse_visible(True)
        self._build_layout()
        if not self.people:
            self._start_new_game()
        else:
            self._restore_seated_people()
            self._reposition_waiting_people()
        self._refresh_state()

    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        self._build_layout()
        self._restore_seated_people()
        self._reposition_waiting_people()
        self._refresh_state()

    def _build_layout(self) -> None:
        self.bottom_area = self.FIXED_BOTTOM_AREA
        self._update_platform_slots(max(self.LEVEL_PLATFORM_COUNTS))

        bus_texture = self.bus_open_texture or self.bus_closed_texture
        if bus_texture is not None:
            bus_width = float(bus_texture.width)
            bus_height = float(bus_texture.height)
        else:
            bus_width = 748.0
            bus_height = 377.0
        self.bus_area = (self.FIXED_BUS_X, self.FIXED_BUS_Y, bus_width, bus_height)

        self._build_seats()

    def _update_platform_slots(self, slot_count: int) -> None:
        self.platform_slots.clear()
        if slot_count <= 0:
            return

        fixed_slots = list(self.FIXED_PLATFORM_SLOTS)
        if slot_count <= len(fixed_slots):
            self.platform_slots.extend(fixed_slots[:slot_count])
            return

        self.platform_slots.extend(fixed_slots)
        while len(self.platform_slots) < slot_count:
            self.platform_slots.append(fixed_slots[-1])

    def _platform_position(self, slot_index: int) -> tuple[float, float]:
        if not self.platform_slots:
            return self.FIXED_PLATFORM_SLOTS[0]
        if 0 <= slot_index < len(self.platform_slots):
            return self.platform_slots[slot_index]
        return self.platform_slots[-1]

    def _build_seats(self) -> None:
        self.seats.clear()

        seat_specs = [
            (0, 0, 321.0, 540.0, True, True),
            (0, 1, 396.0, 540.0, True, True),
            (0, 2, 471.0, 540.0, True, True),
            (0, 7, 751.0, 540.0, True, True),
            (0, 8, 821.0, 540.0, True, False),
            (1, 0, 321.0, 495.0, False, True),
            (1, 1, 396.0, 495.0, False, True),
            (1, 2, 471.0, 495.0, False, True),
            (1, 7, 751.0, 495.0, False, True),
            (1, 8, 821.0, 495.0, False, False),
            (2, 0, 321.0, 410.0, False, True),
            (2, 1, 396.0, 410.0, False, True),
            (2, 2, 471.0, 410.0, False, True),
            (2, 3, 546.0, 410.0, False, True),
            (3, 0, 321.0, 365.0, True, True),
            (3, 1, 396.0, 365.0, True, True),
            (3, 2, 471.0, 365.0, True, True),
            (3, 3, 546.0, 365.0, True, True),
            (3, 4, 616.0, 365.0, True, True),
            (3, 5, 686.0, 365.0, True, False),
        ]

        for row, column, seat_x, seat_y, is_window, faces_right in seat_specs:
            self.seats.append(
                Seat(
                    row=row,
                    column=column,
                    center_x=seat_x,
                    center_y=seat_y,
                    size=self.FIXED_SEAT_SIZE,
                    is_window=is_window,
                    faces_right=faces_right,
                )
            )

    def _restore_seated_people(self) -> None:
        for seat in self.seats:
            seat.occupant = None

        for person in self.people:
            if person.seat_index is None:
                continue
            if not (0 <= person.seat_index < len(self.seats)):
                person.seat_index = None
                continue
            seat = self.seats[person.seat_index]
            seat.occupant = person
            person.x = seat.center_x
            person.y = seat.center_y

    def _start_new_game(self) -> None:
        self.level_index = 0
        self.is_traveling = False
        self.travel_elapsed = 0.0
        self.is_victory = False
        self.name_index = 0
        self.people.clear()
        self.dragged_person = None
        self.dragged_item = None
        self.hovered_person = None
        self._build_layout()
        self._roll_items()
        self._spawn_new_passengers(self.LEVEL_PLATFORM_COUNTS[self.level_index])
        self._reposition_waiting_people()
        self._refresh_state()

    def _next_person_name(self) -> str:
        name = self.NAME_POOL[self.name_index % len(self.NAME_POOL)]
        if self.name_index >= len(self.NAME_POOL):
            name = f"{name}-{self.name_index // len(self.NAME_POOL) + 1}"
        self.name_index += 1
        return name

    def _generate_person_template(self) -> dict[str, bool]:
        level_bonus = self.level_index * 0.05
        template: dict[str, bool] = {
            "stinks": self.rng.random() < 0.16 + level_bonus,
            "listens_music": self.rng.random() < 0.20 + level_bonus,
            "wants_window": self.rng.random() < 0.24 + level_bonus,
            "wants_sleep": self.rng.random() < 0.18 + level_bonus,
            "wants_chat": self.rng.random() < 0.22 + level_bonus,
            "wants_solitude": self.rng.random() < 0.16 + level_bonus,
            "smell_sensitive": self.rng.random() < 0.18 + level_bonus,
            "has_perfume": False,
            "has_headphones": False,
            "has_phone": False,
        }
        return self._normalize_template_traits(template)

    def _spawn_new_passengers(self, count: int) -> None:
        if count <= 0:
            return
        if not self.platform_slots:
            self._update_platform_slots(max(self.LEVEL_PLATFORM_COUNTS))

        used_slots = {person.platform_slot for person in self.people if person.seat_index is None}
        free_slots = [slot for slot in range(len(self.platform_slots)) if slot not in used_slots]
        if not free_slots:
            free_slots = list(range(len(self.platform_slots)))

        # PIXEL_TUNE: радиус fallback-круга человека (если нет текстуры).
        person_radius = 28.0

        for index in range(count):
            slot_index = free_slots[index % len(free_slots)]
            slot_x, slot_y = self._platform_position(slot_index)
            template = self._generate_person_template()
            avatar_color = self.AVATAR_COLORS[index % len(self.AVATAR_COLORS)]
            person = Person(
                name=self._next_person_name(),
                x=slot_x,
                y=slot_y,
                radius=person_radius,
                color=PERSON_COLORS[(self.name_index - 1) % len(PERSON_COLORS)],
                platform_slot=slot_index,
                avatar_color=avatar_color,
                stinks=bool(template.get("stinks", False)),
                listens_music=bool(template.get("listens_music", False)),
                has_perfume=bool(template.get("has_perfume", False)),
                has_headphones=bool(template.get("has_headphones", False)),
                has_phone=bool(template.get("has_phone", False)),
                wants_window=bool(template.get("wants_window", False)),
                wants_sleep=bool(template.get("wants_sleep", False)),
                wants_chat=bool(template.get("wants_chat", False)),
                wants_solitude=bool(template.get("wants_solitude", False)),
                smell_sensitive=bool(template.get("smell_sensitive", False)),
            )
            self.people.append(person)

    def _roll_items(self) -> None:
        counts = {key: 1 if self.rng.random() < 0.65 else 0 for key in ITEM_ORDER}
        if not any(counts.values()):
            counts[self.rng.choice(ITEM_ORDER)] = 1
        self.item_counts = counts

    def _item_slot_rects(self) -> dict[str, tuple[float, float, float, float]]:
        return {item_key: self.FIXED_ITEM_SLOT_RECTS[item_key] for item_key in ITEM_ORDER}

    def _item_slot_at(self, x: float, y: float) -> str | None:
        for item_key, rect in self._item_slot_rects().items():
            if self._rect_contains(rect, x, y):
                return item_key
        return None

    def _apply_item_to_person(self, item_key: str, person: Person) -> bool:
        changed = False

        if item_key == "perfume":
            if person.stinks:
                person.stinks = False
                changed = True
            if not person.has_perfume:
                person.has_perfume = True
                changed = True
        elif item_key == "headphones":
            if not person.has_headphones:
                person.has_headphones = True
                changed = True
        elif item_key == "phone":
            if not person.has_phone:
                person.has_phone = True
                changed = True
            if person.wants_window:
                person.wants_window = False
                changed = True

        if changed:
            self._refresh_state()
        return changed

    def _reposition_waiting_people(self) -> None:
        for person in self.people:
            if person.seat_index is not None:
                continue
            if person is self.dragged_person:
                continue
            slot_x, slot_y = self._platform_position(person.platform_slot)
            person.x = slot_x
            person.y = slot_y

    def _normalize_template_traits(self, template: dict[str, bool | str]) -> dict[str, bool | str]:
        normalized = dict(template)

        if normalized.get("wants_sleep") and normalized.get("listens_music"):
            normalized["listens_music"] = False
        if normalized.get("stinks") and normalized.get("smell_sensitive"):
            normalized["smell_sensitive"] = False
        if normalized.get("wants_chat") and normalized.get("wants_solitude"):
            normalized["wants_solitude"] = False

        return normalized

    def _neighbor_indices(self, seat_index: int) -> list[int]:
        neighbors: list[int] = []
        seat = self.seats[seat_index]
        for index, other in enumerate(self.seats):
            if index == seat_index:
                continue
            if abs(other.row - seat.row) > 1 or abs(other.column - seat.column) > 1:
                continue
            if {seat.row, other.row} == {1, 2}:
                continue
            neighbors.append(index)
        return neighbors

    def _update_seat_effects(self) -> None:
        for seat in self.seats:
            seat.is_smelly = False
            seat.is_loud = False

        for seat_index, seat in enumerate(self.seats):
            if seat.occupant is None:
                continue
            affected_indices = [seat_index, *self._neighbor_indices(seat_index)]
            for target_index in affected_indices:
                target = self.seats[target_index]
                if seat.occupant.stinks:
                    target.is_smelly = True
                if seat.occupant.makes_loud_noise:
                    target.is_loud = True

    def _person_requirements_satisfied(self, person: Person) -> bool:
        if person.seat_index is None:
            return True
        if not (0 <= person.seat_index < len(self.seats)):
            return True

        seat = self.seats[person.seat_index]
        neighbor_people = [
            self.seats[index].occupant
            for index in self._neighbor_indices(person.seat_index)
            if self.seats[index].occupant is not None
        ]

        if person.wants_window and not person.has_phone and not seat.is_window:
            return False
        if person.wants_sleep and not person.has_headphones and any(
            neighbor.listens_music for neighbor in neighbor_people
        ):
            return False
        if person.wants_chat and not neighbor_people:
            return False
        if person.wants_solitude and neighbor_people:
            return False
        if person.smell_sensitive and any(neighbor.stinks for neighbor in neighbor_people):
            return False

        return True

    def _update_people_mood(self) -> None:
        for person in self.people:
            if person.seat_index is None:
                person.is_happy = None
            else:
                person.is_happy = self._person_requirements_satisfied(person)

    def _refresh_state(self) -> None:
        self._update_seat_effects()
        self._update_people_mood()

    def _try_place_in_seat(self, person: Person, seat_index: int) -> bool:
        if not (0 <= seat_index < len(self.seats)):
            return False

        target_seat = self.seats[seat_index]
        if target_seat.occupant is not None and target_seat.occupant is not person:
            return False

        if person.seat_index is not None and 0 <= person.seat_index < len(self.seats):
            self.seats[person.seat_index].occupant = None
        target_seat.occupant = person
        person.seat_index = seat_index
        person.x = target_seat.center_x
        person.y = target_seat.center_y
        self._refresh_state()
        return True

    def _can_depart(self) -> bool:
        if self.is_traveling or self.is_victory or not self.people:
            return False
        for person in self.people:
            if person.seat_index is None:
                return False
            if person.is_happy is not True:
                return False
        return True

    def _start_travel(self) -> None:
        if not self._can_depart():
            return
        self.is_traveling = True
        self.travel_elapsed = 0.0
        self.dragged_person = None
        self.dragged_item = None
        self.hovered_person = None
        self.mouse_down_left = False

    def _finish_travel(self) -> None:
        if self.level_index >= len(self.LEVEL_PLATFORM_COUNTS) - 1:
            self.is_victory = True
            return

        seated_people = [person for person in self.people if person.seat_index is not None]
        self.rng.shuffle(seated_people)
        leave_count = len(seated_people) // 2
        for person in seated_people[:leave_count]:
            if person.seat_index is not None and 0 <= person.seat_index < len(self.seats):
                self.seats[person.seat_index].occupant = None
            self.people.remove(person)

        self.level_index += 1
        self._roll_items()
        self._spawn_new_passengers(self.LEVEL_PLATFORM_COUNTS[self.level_index])
        self._reposition_waiting_people()
        self._refresh_state()

    def on_update(self, delta_time: float) -> None:
        if not self.is_traveling:
            return
        self.travel_elapsed += delta_time
        if self.travel_elapsed >= self.TRAVEL_DURATION_SECONDS:
            self.is_traveling = False
            self._finish_travel()

    def _send_to_platform(self, person: Person) -> None:
        if person.seat_index is not None and 0 <= person.seat_index < len(self.seats):
            self.seats[person.seat_index].occupant = None
        person.seat_index = None
        slot_x, slot_y = self._platform_position(person.platform_slot)
        person.x = slot_x
        person.y = slot_y
        self._refresh_state()

    def _person_under_cursor(self, x: float, y: float) -> Person | None:
        for person in reversed(self.people):
            if person.contains(x, y):
                return person
        return None

    def _seat_at_point(self, x: float, y: float) -> int | None:
        for index, seat in enumerate(self.seats):
            if seat.contains(x, y):
                return index
        return None

    def _rect_contains(self, rect: tuple[float, float, float, float], x: float, y: float) -> bool:
        rect_x, rect_y, rect_w, rect_h = rect
        return rect_x <= x <= rect_x + rect_w and rect_y <= y <= rect_y + rect_h

    def _depart_button_rect(self) -> tuple[float, float, float, float]:
        go_texture = self.game_button_textures.get("go", {}).get("normal")
        button_w = float(go_texture.width) if go_texture is not None else 170.0
        button_h = float(go_texture.height) if go_texture is not None else 55.0
        return (self.FIXED_DEPART_BUTTON_X, self.FIXED_DEPART_BUTTON_Y, button_w, button_h)

    def _victory_panel_rect(self) -> tuple[float, float, float, float]:
        return self.FIXED_VICTORY_PANEL

    def _victory_restart_rect(self) -> tuple[float, float, float, float]:
        play_texture = self.game_button_textures.get("play", {}).get("normal")
        button_w = float(play_texture.width) if play_texture is not None else 360.0
        button_h = float(play_texture.height) if play_texture is not None else 55.0
        return (self.FIXED_VICTORY_RESTART_X, self.FIXED_VICTORY_RESTART_Y, button_w, button_h)

    def _victory_exit_rect(self) -> tuple[float, float, float, float]:
        exit_texture = self.game_button_textures.get("exit", {}).get("normal")
        button_w = float(exit_texture.width) if exit_texture is not None else 360.0
        button_h = float(exit_texture.height) if exit_texture is not None else 55.0
        return (self.FIXED_VICTORY_EXIT_X, self.FIXED_VICTORY_EXIT_Y, button_w, button_h)

    def _button_texture_for_rect(
        self, texture_key: str, rect: tuple[float, float, float, float]
    ) -> arcade.Texture | None:
        texture_set = self.game_button_textures.get(texture_key)
        if not texture_set:
            return None

        hovered = self._rect_contains(rect, self.mouse_x, self.mouse_y)
        if hovered and self.mouse_down_left and texture_set.get("active") is not None:
            return texture_set["active"]
        if hovered and texture_set.get("hover") is not None:
            return texture_set["hover"]
        return texture_set.get("normal")

    def _draw_button(
        self,
        rect: tuple[float, float, float, float],
        text: str,
        fill: Color,
        border: Color,
        font_size: int = 28,
        texture_key: str | None = None,
    ) -> None:
        x, y, width, height = rect
        if texture_key is not None:
            texture = self._button_texture_for_rect(texture_key, rect)
            if texture is not None:
                draw_texture_lbwh(texture, x, y, width, height)
                return

        arcade.draw_lbwh_rectangle_filled(x, y, width, height, fill)
        arcade.draw_lbwh_rectangle_outline(x, y, width, height, border, 3)
        arcade.draw_text(
            text,
            x + width / 2,
            y + height / 2,
            TEXT_DARK,
            font_size,
            anchor_x="center",
            anchor_y="center",
        )

    def on_draw(self) -> None:
        self.clear()

        width = self.window.width
        height = self.window.height

        if self.is_traveling:
            if self.travel_texture is not None:
                travel_w = float(self.travel_texture.width)
                travel_h = float(self.travel_texture.height)
                # PIXEL_TUNE: скорость/длина прокрутки transition-фона.
                progress = min(1.0, self.travel_elapsed / self.TRAVEL_DURATION_SECONDS)
                offset = progress * travel_w
                draw_texture_lbwh(self.travel_texture, -offset, 0, travel_w, travel_h)
                draw_texture_lbwh(self.travel_texture, -offset + travel_w, 0, travel_w, travel_h)
            elif self.background_texture is not None:
                draw_texture_lbwh(
                    self.background_texture,
                    0,
                    0,
                    float(self.background_texture.width),
                    float(self.background_texture.height),
                )
            travel_bus = self.bus_closed_texture or self.bus_open_texture
            if travel_bus is not None:
                # PIXEL_TUNE: центрирование автобуса в режиме "едем".
                draw_texture_lbwh(
                    travel_bus,
                    self.FIXED_TRAVEL_BUS_X,
                    self.FIXED_TRAVEL_BUS_Y,
                    float(travel_bus.width),
                    float(travel_bus.height),
                )
            return

        if self.background_texture is not None:
            draw_texture_lbwh(
                self.background_texture,
                0,
                0,
                float(self.background_texture.width),
                float(self.background_texture.height),
            )
        if self.item_slots_overlay_texture is not None:
            draw_texture_lbwh(
                self.item_slots_overlay_texture,
                0,
                0,
                float(self.item_slots_overlay_texture.width),
                float(self.item_slots_overlay_texture.height),
            )

        bottom_x, bottom_y, bottom_width, bottom_height = self.bottom_area
        arcade.draw_lbwh_rectangle_filled(bottom_x, bottom_y, bottom_width, bottom_height, PASTEL_SKY_LIGHT)
        arcade.draw_lbwh_rectangle_outline(
            bottom_x, bottom_y, bottom_width, bottom_height, PASTEL_SKY_ACCENT, 2
        )

        bus_x, bus_y, bus_width, bus_height = self.bus_area
        bus_texture = self.bus_open_texture

        if bus_texture is not None:
            draw_texture_lbwh(bus_texture, bus_x, bus_y, bus_width, bus_height)

        for seat in self.seats:
            seat_left = seat.center_x - seat.size / 2
            seat_bottom = seat.center_y - seat.size / 2
            if seat.is_smelly and seat.is_loud:
                seat_fill = (*SEAT_SMELLY_LOUD_COLOR[:3], 185)
            elif seat.is_smelly:
                seat_fill = (*SEAT_SMELLY_COLOR[:3], 185)
            elif seat.is_loud:
                seat_fill = (*SEAT_LOUD_COLOR[:3], 185)
            elif seat.occupant is None:
                seat_fill = (244, 249, 255, 125)
            else:
                seat_fill = (189, 210, 232, 175)

            arcade.draw_lbwh_rectangle_filled(seat_left, seat_bottom, seat.size, seat.size, seat_fill)
            arcade.draw_lbwh_rectangle_outline(
                seat_left, seat_bottom, seat.size, seat.size, PASTEL_SKY_ACCENT, 3
            )
            if seat.is_window:
                arcade.draw_lbwh_rectangle_outline(
                    seat_left + 3,
                    seat_bottom + 3,
                    seat.size - 6,
                    seat.size - 6,
                    PASTEL_YELLOW_DARK,
                    2,
                )

        for item_key, rect in self._item_slot_rects().items():
            rect_x, rect_y, rect_w, rect_h = rect
            item_count = self.item_counts.get(item_key, 0)

            icon_texture = self.item_icon_textures.get(item_key)
            if icon_texture is not None:
                icon_w = float(icon_texture.width)
                icon_h = float(icon_texture.height)
                icon_left = rect_x + (rect_w - icon_w) / 2
                icon_bottom = rect_y + (rect_h - icon_h) / 2
                if item_count > 0:
                    draw_texture_lbwh(icon_texture, icon_left, icon_bottom, icon_w, icon_h)
                else:
                    draw_texture_lbwh(
                        icon_texture,
                        icon_left,
                        icon_bottom,
                        icon_w,
                        icon_h,
                        alpha=96,
                        color=(180, 180, 180, 255),
                    )

        level_texture: arcade.Texture | None = None
        if 0 <= self.level_index < len(self.level_badge_textures):
            level_texture = self.level_badge_textures[self.level_index]
        if level_texture is not None:
            badge_w = float(level_texture.width)
            badge_h = float(level_texture.height)
            # PIXEL_TUNE: верхний бейдж уровня (по центру, касается верхнего края).
            draw_texture_lbwh(level_texture, self.FIXED_LEVEL_BADGE_X, self.FIXED_LEVEL_BADGE_Y, badge_w, badge_h)
        else:
            arcade.draw_text(
                f'\u0423\u0440\u043e\u0432\u0435\u043d\u044c {self.level_index + 1}/{len(self.LEVEL_PLATFORM_COUNTS)}',
                width / 2,
                # PIXEL_TUNE: fallback-позиция текста уровня.
                height - 22,
                TEXT_DARK,
                24,
                anchor_x='center',
                anchor_y='center',
            )

        for person in self.people:
            texture = self._person_visual_texture(person)
            if texture is not None:
                if person.seat_index is not None and 0 <= person.seat_index < len(self.seats):
                    seat = self.seats[person.seat_index]
                    if seat.faces_right:
                        texture = self._flipped_texture(texture)
                texture_w = float(texture.width)
                texture_h = float(texture.height)
                draw_texture_lbwh(
                    texture,
                    person.x - texture_w / 2,
                    person.y - texture_h / 2,
                    texture_w,
                    texture_h,
                )
            else:
                arcade.draw_circle_filled(person.x, person.y, person.radius, person.color)
                arcade.draw_circle_outline(person.x, person.y, person.radius, TEXT_DARK, 2)

        if self.dragged_item is not None:
            icon_texture = self.item_icon_textures.get(self.dragged_item)
            if icon_texture is not None:
                preview_w = float(icon_texture.width)
                preview_h = float(icon_texture.height)
                # PIXEL_TUNE: позиция превью предмета под курсором.
                draw_texture_lbwh(
                    icon_texture,
                    self.mouse_x - preview_w / 2,
                    self.mouse_y - preview_h / 2,
                    preview_w,
                    preview_h,
                    alpha=220,
                )
            else:
                # PIXEL_TUNE: fallback-размер превью предмета.
                preview_w = 120
                preview_h = 46
                preview_x = self.mouse_x - preview_w / 2
                preview_y = self.mouse_y - preview_h / 2
                arcade.draw_lbwh_rectangle_filled(
                    preview_x,
                    preview_y,
                    preview_w,
                    preview_h,
                    (*ITEM_COLORS[self.dragged_item][:3], 220),
                )
                arcade.draw_lbwh_rectangle_outline(
                    preview_x, preview_y, preview_w, preview_h, PASTEL_SKY_ACCENT, 2
                )
                arcade.draw_text(
                    ITEM_LABELS[self.dragged_item],
                    preview_x + preview_w / 2,
                    preview_y + preview_h / 2,
                    TEXT_DARK,
                    18,
                    anchor_x='center',
                    anchor_y='center',
                )

        if self._can_depart():
            self._draw_button(
                self._depart_button_rect(),
                '\u041f\u043e\u0435\u0445\u0430\u0442\u044c',
                PASTEL_YELLOW,
                PASTEL_YELLOW_DARK,
                font_size=28,
                texture_key='go',
            )

        if self.hovered_person is not None and not self.is_traveling and not self.is_victory:
            tooltip_lines = [self.hovered_person.name]
            tooltip_lines.extend(self.hovered_person.active_property_lines())
            tooltip_lines.extend(self.hovered_person.active_requirement_lines())
            tooltip_lines.append('')
            if self.hovered_person.is_happy is None:
                tooltip_lines.append('\u041d\u0435\u0439\u0442\u0440\u0430\u043b\u044c\u043d\u044b\u0439')
            elif self.hovered_person.is_happy:
                tooltip_lines.append('\u0414\u043e\u0432\u043e\u043b\u0435\u043d')
            else:
                tooltip_lines.append('\u0413\u0440\u0443\u0441\u0442\u043d\u044b\u0439')

            font_size = 14
            line_height = 20
            max_line = max(len(line) for line in tooltip_lines)
            # PIXEL_TUNE: размеры тултипа и отступы от курсора.
            tooltip_width = min(520, max(280, max_line * 8 + 26))
            tooltip_height = len(tooltip_lines) * line_height + 16
            tooltip_x = self.mouse_x + 18
            tooltip_y = self.mouse_y + 18

            # PIXEL_TUNE: отступы тултипа от краев экрана.
            if tooltip_x + tooltip_width > width - 8:
                tooltip_x = width - tooltip_width - 8
            if tooltip_y + tooltip_height > height - 8:
                tooltip_y = height - tooltip_height - 8

            arcade.draw_lbwh_rectangle_filled(
                tooltip_x, tooltip_y, tooltip_width, tooltip_height, (250, 253, 255, 236)
            )
            arcade.draw_lbwh_rectangle_outline(
                tooltip_x, tooltip_y, tooltip_width, tooltip_height, PASTEL_SKY_ACCENT, 2
            )

            # PIXEL_TUNE: стартовая Y-позиция первой строки внутри тултипа.
            line_y = tooltip_y + tooltip_height - 24
            for line in tooltip_lines:
                arcade.draw_text(
                    line,
                    # PIXEL_TUNE: внутренний левый отступ текста тултипа.
                    tooltip_x + 10,
                    line_y,
                    TEXT_DARK,
                    font_size,
                    anchor_x='left',
                    anchor_y='center',
                )
                line_y -= line_height

        if self.is_victory:
            arcade.draw_lrbt_rectangle_filled(0, width, 0, height, (100, 100, 100, 180))
            panel_x, panel_y, panel_w, panel_h = self._victory_panel_rect()
            arcade.draw_lbwh_rectangle_filled(panel_x, panel_y, panel_w, panel_h, PASTEL_SKY_LIGHT)
            arcade.draw_lbwh_rectangle_outline(panel_x, panel_y, panel_w, panel_h, PASTEL_SKY_ACCENT, 4)
            arcade.draw_text(
                '\u041f\u043e\u0431\u0435\u0434\u0430',
                panel_x + panel_w / 2,
                panel_y + panel_h - 70,
                TEXT_DARK,
                54,
                anchor_x='center',
                anchor_y='center',
            )
            self._draw_button(
                self._victory_restart_rect(),
                '\u0417\u0430\u043d\u043e\u0432\u043e',
                PASTEL_YELLOW,
                PASTEL_YELLOW_DARK,
                font_size=28,
                texture_key='play',
            )
            self._draw_button(
                self._victory_exit_rect(),
                '\u0412\u044b\u0439\u0442\u0438',
                PASTEL_SKY,
                PASTEL_SKY_ACCENT,
                font_size=28,
                texture_key='exit',
            )


    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        self.mouse_x = x
        self.mouse_y = y
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        self.mouse_down_left = True

        if self.is_traveling:
            return

        if self.is_victory:
            if self._rect_contains(self._victory_restart_rect(), x, y):
                self._start_new_game()
            elif self._rect_contains(self._victory_exit_rect(), x, y):
                arcade.exit()
            return

        if self._can_depart() and self._rect_contains(self._depart_button_rect(), x, y):
            self._start_travel()
            return

        item_key = self._item_slot_at(x, y)
        if item_key is not None and self.item_counts.get(item_key, 0) > 0:
            self.dragged_item = item_key
            self.dragged_person = None
            self.hovered_person = self._person_under_cursor(x, y)
            return

        person = self._person_under_cursor(x, y)
        if person is None:
            return

        self.dragged_person = person
        self.dragged_item = None
        self.drag_offset_x = person.x - x
        self.drag_offset_y = person.y - y

        if person.seat_index is not None and 0 <= person.seat_index < len(self.seats):
            self.seats[person.seat_index].occupant = None
            person.seat_index = None
            self._refresh_state()

        self.people.remove(person)
        self.people.append(person)
        self.hovered_person = person

    def on_mouse_drag(
        self, x: float, y: float, dx: float, dy: float, buttons: int, modifiers: int
    ) -> None:
        self.mouse_x = x
        self.mouse_y = y
        if self.is_traveling or self.is_victory:
            return
        if self.dragged_person is None:
            if self.dragged_item is not None:
                self.hovered_person = self._person_under_cursor(x, y)
            return
        if not (buttons & arcade.MOUSE_BUTTON_LEFT):
            return

        radius = self.dragged_person.radius
        next_x = x + self.drag_offset_x
        next_y = y + self.drag_offset_y
        # PIXEL_TUNE: границы перемещения персонажа в пределах окна.
        self.dragged_person.x = max(radius, min(self.window.width - radius, next_x))
        self.dragged_person.y = max(radius, min(self.window.height - radius, next_y))

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> None:
        self.mouse_x = x
        self.mouse_y = y
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        self.mouse_down_left = False
        if self.is_traveling or self.is_victory:
            return

        if self.dragged_item is not None:
            item_key = self.dragged_item
            target_person = self._person_under_cursor(x, y)
            if target_person is not None and self.item_counts.get(item_key, 0) > 0:
                if self._apply_item_to_person(item_key, target_person):
                    self.item_counts[item_key] -= 1
            self.dragged_item = None
            self.hovered_person = self._person_under_cursor(x, y)
            return

        if self.dragged_person is None:
            return

        target_seat_index = self._seat_at_point(self.dragged_person.x, self.dragged_person.y)
        placed = False
        if target_seat_index is not None:
            placed = self._try_place_in_seat(self.dragged_person, target_seat_index)

        if not placed:
            self._send_to_platform(self.dragged_person)

        self.hovered_person = self._person_under_cursor(x, y)
        self.dragged_person = None

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        self.mouse_x = x
        self.mouse_y = y
        if self.is_traveling or self.is_victory:
            self.hovered_person = None
            return
        if self.dragged_item is not None:
            self.hovered_person = self._person_under_cursor(x, y)
            return
        if self.dragged_person is not None:
            self.hovered_person = self.dragged_person
        else:
            self.hovered_person = self._person_under_cursor(x, y)



class MainMenuView(arcade.View):
    def __init__(self) -> None:
        super().__init__()
        self.manager = arcade.gui.UIManager()
        self.menu_background_texture = load_texture_if_exists(SCREENS_DIR / 'entrance.png') or load_texture_if_exists(
            SCREENS_DIR / 'levels.png'
        )
        self.menu_button_textures: dict[str, dict[str, arcade.Texture | None]] = {
            'play': load_button_texture_set('play'),
            'exit': load_button_texture_set('exit'),
        }

    def on_show_view(self) -> None:
        self.window.background_color = PASTEL_SKY
        self.window.set_mouse_visible(True)
        self.manager.enable()
        self._build_ui()

    def on_hide_view(self) -> None:
        self.manager.disable()
        self.manager.clear()

    def _build_ui(self) -> None:
        self.manager.clear()

        # PIXEL_TUNE: размеры кнопок меню (берутся 1:1 из текстур, fallback ниже).
        play_texture_set = self.menu_button_textures['play']
        play_texture = play_texture_set.get('normal')
        play_texture_hover = play_texture_set.get('hover')
        play_texture_press = play_texture_set.get('active')
        play_text = ''
        play_style = None
        if play_texture is not None:
            play_width = int(play_texture.width)
            play_height = int(play_texture.height)
        else:
            play_width, play_height = 420, 120
            play_texture = make_rounded_button_texture(
                play_width, play_height, PASTEL_YELLOW, PASTEL_YELLOW_DARK, border_width=4, radius=26
            )
            play_texture_hover = make_rounded_button_texture(
                play_width,
                play_height,
                shift_color(PASTEL_YELLOW, 10),
                PASTEL_YELLOW_DARK,
                border_width=4,
                radius=26,
            )
            play_texture_press = make_rounded_button_texture(
                play_width,
                play_height,
                shift_color(PASTEL_YELLOW, -12),
                PASTEL_YELLOW_DARK,
                border_width=4,
                radius=26,
            )
            play_text = '\u0418\u0433\u0440\u0430\u0442\u044c'
            play_style = {
                'normal': UITextureButtonStyle(font_size=48, font_name=('Arial',), font_color=TEXT_DARK),
                'hover': UITextureButtonStyle(font_size=48, font_name=('Arial',), font_color=TEXT_DARK),
                'press': UITextureButtonStyle(font_size=48, font_name=('Arial',), font_color=TEXT_DARK),
                'disabled': UITextureButtonStyle(
                    font_size=48, font_name=('Arial',), font_color=shift_color(TEXT_DARK, 70)
                ),
            }

        exit_texture_set = self.menu_button_textures['exit']
        exit_texture = exit_texture_set.get('normal')
        exit_texture_hover = exit_texture_set.get('hover')
        exit_texture_press = exit_texture_set.get('active')
        exit_text = ''
        exit_style = None
        if exit_texture is not None:
            exit_width = int(exit_texture.width)
            exit_height = int(exit_texture.height)
        else:
            exit_width, exit_height = 280, 84
            exit_texture = make_rounded_button_texture(
                exit_width, exit_height, PASTEL_SKY_LIGHT, PASTEL_SKY_ACCENT, border_width=4, radius=22
            )
            exit_texture_hover = make_rounded_button_texture(
                exit_width,
                exit_height,
                shift_color(PASTEL_SKY_LIGHT, 10),
                PASTEL_SKY_ACCENT,
                border_width=4,
                radius=22,
            )
            exit_texture_press = make_rounded_button_texture(
                exit_width,
                exit_height,
                shift_color(PASTEL_SKY_LIGHT, -12),
                PASTEL_SKY_ACCENT,
                border_width=4,
                radius=22,
            )
            exit_text = '\u0412\u044b\u0445\u043e\u0434'
            exit_style = {
                'normal': UITextureButtonStyle(font_size=34, font_name=('Arial',), font_color=TEXT_DARK),
                'hover': UITextureButtonStyle(font_size=34, font_name=('Arial',), font_color=TEXT_DARK),
                'press': UITextureButtonStyle(font_size=34, font_name=('Arial',), font_color=TEXT_DARK),
                'disabled': UITextureButtonStyle(
                    font_size=34, font_name=('Arial',), font_color=shift_color(TEXT_DARK, 70)
                ),
            }

        play_kwargs: dict[str, object] = {
            'width': play_width,
            'height': play_height,
            'text': play_text,
            'texture': play_texture,
            'texture_hovered': play_texture_hover,
            'texture_pressed': play_texture_press,
        }
        if play_style is not None:
            play_kwargs['style'] = play_style
        play_button = arcade.gui.UITextureButton(**play_kwargs)

        exit_kwargs: dict[str, object] = {
            'width': exit_width,
            'height': exit_height,
            'text': exit_text,
            'texture': exit_texture,
            'texture_hovered': exit_texture_hover,
            'texture_pressed': exit_texture_press,
        }
        if exit_style is not None:
            exit_kwargs['style'] = exit_style
        exit_button = arcade.gui.UITextureButton(**exit_kwargs)

        @play_button.event('on_click')
        def _on_click_play(event: arcade.gui.UIOnClickEvent) -> None:
            self.window.show_view(GameView())

        @exit_button.event('on_click')
        def _on_click_exit(event: arcade.gui.UIOnClickEvent) -> None:
            arcade.exit()

        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(
            play_button,
            # PIXEL_TUNE: базовое центрирование кнопки "Играть".
            anchor_x='center_x',
            anchor_y='center_y',
        )
        anchor.add(
            exit_button,
            anchor_x='center_x',
            anchor_y='center_y',
            # PIXEL_TUNE: вертикальный сдвиг кнопки "Выход" относительно центра.
            align_y=-110,
        )
        self.manager.add(anchor)

    def on_draw(self) -> None:
        self.clear()
        width = self.window.width
        height = self.window.height

        if self.menu_background_texture is not None:
            draw_texture_lbwh(
                self.menu_background_texture,
                0,
                0,
                float(self.menu_background_texture.width),
                float(self.menu_background_texture.height),
            )
        else:
            arcade.draw_lrbt_rectangle_filled(0, width, 0, height, PASTEL_SKY)
            arcade.draw_lrbt_rectangle_filled(0, width, height * 0.58, height, PASTEL_SKY_LIGHT)
        self.manager.draw()


def main() -> None:
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.show_view(MainMenuView())
    arcade.run()


if __name__ == "__main__":
    main()

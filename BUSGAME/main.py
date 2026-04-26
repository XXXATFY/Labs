import arcade
import arcade.gui
import math
from dataclasses import dataclass
from pathlib import Path


# Базовый тип цвета в формате RGBA (красный, зеленый, синий, альфа).
Color = tuple[int, int, int, int]

# Фиксированное разрешение окна.
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "BUSGAME"

# Папки с ассетами игры.
ASSETS_DIR = Path("assets")
BUTTONS_DIR = ASSETS_DIR / "buttons"
ITEMS_DIR = ASSETS_DIR / "items"
SCREENS_DIR = ASSETS_DIR / "screens"

ITEM_ORDER = ("perfume", "headphones", "phone")


# Простая обертка над загрузкой текстур.
def load_texture(path: Path) -> arcade.Texture:
    return arcade.load_texture(str(path))


# Загружает комплект текстур одной кнопки: normal, hover, active.
def load_button_texture_set(name: str) -> dict[str, arcade.Texture]:
    normal_path = BUTTONS_DIR / f"{name}_default.png"
    normal_texture = load_texture(normal_path)
    return {
        "normal": normal_texture,
        "hover": load_texture(BUTTONS_DIR / f"{name}_hover.png"),
        "active": load_texture(BUTTONS_DIR / f"{name}_active.png"),
    }


# Рисует текстуру по координатам left/bottom и заданному размеру width/height.
def draw_texture_lbwh(
    texture: arcade.Texture,
    left: float,
    bottom: float,
    width: float,
    height: float,
    *,
    alpha: int = 255,
    color: Color = (255, 255, 255, 255),
) -> None:
    arcade.draw_texture_rect(
        texture=texture,
        rect=arcade.Rect.from_kwargs(
            left=left,
            bottom=bottom,
            width=width,
            height=height,
        ),
        alpha=alpha,
        color=arcade.types.Color(*color),
    )




@dataclass
class Person:
    # Имя персонажа для тултипа.
    name: str
    # Текущие координаты персонажа в игровом мире.
    x: float
    y: float
    # Радиус круга для проверки клика/перетаскивания.
    radius: float
    # Номер слота на платформе ожидания.
    platform_slot: int
    # Цветовая вариация текстуры персонажа.
    avatar_color: str = "blue"
    # Свойства персонажа.
    stinks: bool = False
    listens_music: bool = False
    has_perfume: bool = False
    has_headphones: bool = False
    has_phone: bool = False
    # Требования персонажа к посадке.
    wants_window: bool = False
    wants_sleep: bool = False
    wants_chat: bool = False
    wants_solitude: bool = False
    smell_sensitive: bool = False
    # Индекс места в автобусе (None = персонаж на платформе).
    seat_index: int | None = None
    # Настроение: True/False если сидит, None если пока не посажен.
    is_happy: bool | None = None

    # Проверка попадания точки мыши в круг персонажа.
    def contains(self, px: float, py: float) -> bool:
        return math.hypot(self.x - px, self.y - py) <= self.radius



@dataclass
class Seat:
    # Логические координаты места в сетке мест.
    row: int
    column: int
    # Центр места в пикселях.
    center_x: float
    center_y: float
    # Размер квадрата "зоны посадки".
    size: float
    # Находится ли это место у окна.
    is_window: bool
    # Должен ли персонаж смотреть вправо на этом месте.
    faces_right: bool = False
    # Эффекты места, которые пересчитываются каждый кадр логики.
    is_smelly: bool = False
    is_loud: bool = False
    # Кто сейчас занимает место.
    occupant: Person | None = None

    # Проверка попадания точки мыши внутрь квадрата места.
    def contains(self, px: float, py: float) -> bool:
        half = self.size / 2
        return (
            self.center_x - half <= px <= self.center_x + half
            and self.center_y - half <= py <= self.center_y + half
        )


# Основная игровая сцена: автобус, пассажиры, предметы, уровни.
class GameView(arcade.View):
    # Количество новых пассажиров на платформе по уровням.
    LEVEL_PLATFORM_COUNTS = (6, 8)
    # Время анимации переезда между уровнями.
    TRAVEL_DURATION_SECONDS = 3.2
    # Точки, где стоят люди на платформе.
    FIXED_PLATFORM_SLOTS = (
        (420, 150),
        (508, 150),
        (596, 150),
        (684, 150),
        (772, 150),
        (860, 150),
        (420, 53),
        (508, 53),
    )
    FIXED_BUS_X = 266
    FIXED_BUS_Y = 243
    FIXED_SEAT_SIZE = 40
    FIXED_ITEM_SLOT_RECTS = {
        "perfume": (1125, 590, 75, 75),
        "headphones": (1125, 499, 75, 75),
        "phone": (1125, 408, 75, 75),
    }
    FIXED_DEPART_BUTTON_X = 1084
    FIXED_DEPART_BUTTON_Y = 20
    FIXED_LEVEL_BADGE_X = 460
    FIXED_LEVEL_BADGE_Y = 665
    # Группы соседства для требований "болтать/одиночество".
    CHAT_GROUPS = (
        (0, 5),
        (1, 6),
        (2, 7),
        (3, 4, 8, 9),
        (10, 14),
        (11, 15),
        (12, 16),
        (13, 17),
        (18, 19),
    )
    # Варианты цвета персонажей для подбора текстур.
    AVATAR_COLORS = ("blue", "orange", "red", "yellow")
    # Наборы слов, которые используются в именах текстур персонажей.
    GUY_MOODS = ("idle", "happy", "sad")
    GUY_EFFECTS = ("headphones", "phone", "perfume", "stink", "noise")
    # Фиксированные шаблоны характеристик персонажей.
    FIXED_PERSON_TEMPLATES = (
        {
            "stinks": False,
            "listens_music": False,
            "wants_window": True,
            "wants_sleep": False,
            "wants_chat": False,
            "wants_solitude": False,
            "smell_sensitive": False,
        },
        {
            "stinks": False,
            "listens_music": False,
            "wants_window": False,
            "wants_sleep": True,
            "wants_chat": False,
            "wants_solitude": False,
            "smell_sensitive": False,
        },
        {
            "stinks": False,
            "listens_music": False,
            "wants_window": False,
            "wants_sleep": False,
            "wants_chat": True,
            "wants_solitude": False,
            "smell_sensitive": False,
        },
        {
            "stinks": False,
            "listens_music": False,
            "wants_window": False,
            "wants_sleep": False,
            "wants_chat": False,
            "wants_solitude": True,
            "smell_sensitive": False,
        },
        {
            "stinks": False,
            "listens_music": False,
            "wants_window": False,
            "wants_sleep": False,
            "wants_chat": False,
            "wants_solitude": False,
            "smell_sensitive": True,
        },
        {
            "stinks": True,
            "listens_music": False,
            "wants_window": False,
            "wants_sleep": False,
            "wants_chat": False,
            "wants_solitude": False,
            "smell_sensitive": False,
        },
        {
            "stinks": False,
            "listens_music": True,
            "wants_window": False,
            "wants_sleep": False,
            "wants_chat": False,
            "wants_solitude": False,
            "smell_sensitive": False,
        },
        {
            "stinks": False,
            "listens_music": False,
            "wants_window": True,
            "wants_sleep": False,
            "wants_chat": True,
            "wants_solitude": False,
            "smell_sensitive": False,
        },
        {
            "stinks": False,
            "listens_music": False,
            "wants_window": False,
            "wants_sleep": True,
            "wants_chat": False,
            "wants_solitude": False,
            "smell_sensitive": True,
        },
        {
            "stinks": True,
            "listens_music": False,
            "wants_window": False,
            "wants_sleep": False,
            "wants_chat": False,
            "wants_solitude": True,
            "smell_sensitive": False,
        },
        {
            "stinks": False,
            "listens_music": True,
            "wants_window": True,
            "wants_sleep": False,
            "wants_chat": False,
            "wants_solitude": False,
            "smell_sensitive": False,
        },
        {
            "stinks": False,
            "listens_music": False,
            "wants_window": False,
            "wants_sleep": False,
            "wants_chat": True,
            "wants_solitude": False,
            "smell_sensitive": True,
        },
    )
    # Фиксированный список имен.
    NAME_POOL = (
        "Аня",
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

    # Создает игровую сцену, подготавливает состояние и загружает все текстуры.
    def __init__(self) -> None:
        super().__init__()
        # Геометрия автобуса.
        self.bus_area: tuple[float, float, float, float] = (0, 0, 0, 0)
        # Контейнеры с логикой мест и персонажей.
        self.platform_slots: list[tuple[float, float]] = []
        self.seats: list[Seat] = []
        self.effect_neighbors: dict[int, list[int]] = {}
        self.chat_neighbors: dict[int, list[int]] = {}
        self.people: list[Person] = []
        # Состояние уровня/переходов.
        self.level_index = 0
        self.is_traveling = False
        self.travel_elapsed = 0
        self.name_index = 0
        # Предметы и drag&drop.
        self.item_counts: dict[str, int] = {key: 0 for key in ITEM_ORDER}
        self.dragged_person: Person | None = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.dragged_item: str | None = None
        # Текущее состояние мыши.
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_down_left = False
        # Текстуры игровых экранов.
        self.background_texture = load_texture(SCREENS_DIR / "levels.png")
        self.item_slots_overlay_texture = load_texture(ITEMS_DIR / "background_1280_720.png")
        self.travel_texture = load_texture(SCREENS_DIR / "level1_to_level2.png")
        self.bus_open_texture = load_texture(SCREENS_DIR / "bus_opendoor.png")
        self.bus_closed_texture = load_texture(SCREENS_DIR / "bus_closedoor.png")
        # Иконки предметов.
        self.item_icon_textures: dict[str, arcade.Texture] = {
            item_key: load_texture(ITEMS_DIR / f"{item_key}.png")
            for item_key in ITEM_ORDER
        }
        # Текстуры кнопок.
        self.game_button_textures: dict[str, dict[str, arcade.Texture]] = {
            "go": load_button_texture_set("go"),
        }
        # Текстуры бейджей уровней.
        self.level_badge_textures: list[arcade.Texture] = [
            load_texture(BUTTONS_DIR / "level_1.png"),
            load_texture(BUTTONS_DIR / "level_2.png"),
        ]
        self.guys_assets_root = Path("assets") / "guys"
        # Готовим таблицу всех текстур персонажей по ключу (цвет, ракурс, настроение, эффект).
        self.guy_textures: dict[tuple[str, str, str, str | None], arcade.Texture] = {}
        for orientation in ("front", "side"):
            for mood in self.GUY_MOODS:
                folder = self.guys_assets_root / f"all_{orientation}_guy_{mood}"
                for color in self.AVATAR_COLORS:
                    base_name = f"{color}_{orientation}_guy_{mood}"
                    self.guy_textures[(color, orientation, mood, None)] = load_texture(
                        folder / f"{base_name}.png"
                    )
                    for effect in self.GUY_EFFECTS:
                        self.guy_textures[(color, orientation, mood, effect)] = load_texture(
                            folder / f"{base_name}_{effect}.png"
                        )

    # Возвращает нужную текстуру персонажа по состоянию: ракурс, настроение, эффект.
    def _person_visual_texture(self, person: Person) -> arcade.Texture:
        # Ракурс зависит от того, сидит ли персонаж в автобусе.
        orientation = "front" if person.seat_index is None else "side"
        # Настроение используется для выбора idle/happy/sad текстуры.
        if person.seat_index is None:
            mood = "idle"
        elif person.is_happy:
            mood = "happy"
        else:
            mood = "sad"
        # Эффект выбирается по приоритету.
        effect = None
        if person.has_headphones:
            effect = "headphones"
        elif person.has_phone:
            effect = "phone"
        elif person.has_perfume:
            effect = "perfume"
        elif person.stinks:
            effect = "stink"
        elif person.listens_music:
            effect = "noise"
        return self.guy_textures[(person.avatar_color, orientation, mood, effect)]

    # Вызывается, когда окно показывает этот View.
    def on_show_view(self) -> None:
        self.window.set_mouse_visible(True)
        # Пересобираем layout, а затем восстанавливаем или создаем состояние игры.
        self._build_layout()
        if not self.people:
            self._start_new_game()
        else:
            self._restore_seated_people()
            self._reposition_waiting_people()
        self._refresh_state()

    # Вызывается при изменении размера окна.
    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        # В этой игре все позиции фиксированные, но мы все равно заново приводим состояние.
        self._build_layout()
        self._restore_seated_people()
        self._reposition_waiting_people()
        self._refresh_state()

    # Собирает геометрию всех игровых зон.
    def _build_layout(self) -> None:
        self._update_platform_slots(max(self.LEVEL_PLATFORM_COUNTS))

        # Ширину/высоту автобуса берем из самой текстуры.
        bus_width = float(self.bus_open_texture.width)
        bus_height = float(self.bus_open_texture.height)
        self.bus_area = (self.FIXED_BUS_X, self.FIXED_BUS_Y, bus_width, bus_height)

        self._build_seats()

    # Готовит список слотов платформы, где стоят ожидающие пассажиры.
    def _update_platform_slots(self, slot_count: int) -> None:
        self.platform_slots = list(self.FIXED_PLATFORM_SLOTS[:slot_count])

    # Возвращает координаты нужного слота платформы.
    def _platform_position(self, slot_index: int) -> tuple[float, float]:
        return self.platform_slots[slot_index]

    # Создает все места в автобусе и таблицы соседства.
    def _build_seats(self) -> None:
        self.seats.clear()

        # Каждая запись: row, column, x, y, is_window, faces_right.
        seat_specs = [
            (0, 0, 321, 540, True, True),
            (0, 1, 396, 540, True, True),
            (0, 2, 471, 540, True, True),
            (0, 7, 751, 540, True, True),
            (0, 8, 821, 540, True, False),
            (1, 0, 321, 495, False, True),
            (1, 1, 396, 495, False, True),
            (1, 2, 471, 495, False, True),
            (1, 7, 751, 495, False, True),
            (1, 8, 821, 495, False, False),
            (2, 0, 321, 410, False, True),
            (2, 1, 396, 410, False, True),
            (2, 2, 471, 410, False, True),
            (2, 3, 546, 410, False, True),
            (3, 0, 321, 365, True, True),
            (3, 1, 396, 365, True, True),
            (3, 2, 471, 365, True, True),
            (3, 3, 546, 365, True, True),
            (3, 4, 616, 365, True, True),
            (3, 5, 686, 365, True, False),
        ]

        # Превращаем спецификации в объекты Seat.
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

        # Соседи для распространения запаха/шума: почти вокруг по сетке.
        self.effect_neighbors = {}
        for i, seat in enumerate(self.seats):
            neighbors: list[int] = []
            for j, other in enumerate(self.seats):
                if i == j:
                    continue
                # Соседство по row/column в радиусе 1 клетки.
                if abs(other.row - seat.row) > 1 or abs(other.column - seat.column) > 1:
                    continue
                # Между 1 и 2 "рядом" не считаем, чтобы не перебрасывать эффекты через проход.
                if {seat.row, other.row} == {1, 2}:
                    continue
                neighbors.append(j)
            self.effect_neighbors[i] = neighbors

        # Соседи для общения/одиночества берутся из ручных групп.
        self.chat_neighbors = {i: [] for i in range(len(self.seats))}
        for group in self.CHAT_GROUPS:
            for i in group:
                self.chat_neighbors[i] = [j for j in group if j != i]

    # Восстанавливает связь "персонаж -> место", например после resize/перезапуска view.
    def _restore_seated_people(self) -> None:
        # Сначала считаем, что все места свободны.
        for seat in self.seats:
            seat.occupant = None

        # Затем для каждого сидящего пассажира снова проставляем occupant и позицию.
        for person in self.people:
            if person.seat_index is None:
                continue
            seat = self.seats[person.seat_index]
            seat.occupant = person
            person.x = seat.center_x
            person.y = seat.center_y

    # Полный старт нового прохождения с первого уровня.
    def _start_new_game(self) -> None:
        self.level_index = 0
        self.is_traveling = False
        self.travel_elapsed = 0
        self.name_index = 0
        self.people.clear()
        self.dragged_person = None
        self.dragged_item = None
        self._build_layout()
        self._roll_items()
        self._spawn_new_passengers(self.LEVEL_PLATFORM_COUNTS[self.level_index])
        self._reposition_waiting_people()
        self._refresh_state()

    # Возвращает следующее имя из фиксированного списка.
    def _next_person_name(self) -> str:
        name = self.NAME_POOL[self.name_index % len(self.NAME_POOL)]
        self.name_index += 1
        return name

    # Возвращает фиксированный шаблон свойств/требований без случайности.
    def _generate_person_template(self, template_index: int) -> dict[str, bool]:
        template = dict(self.FIXED_PERSON_TEMPLATES[template_index % len(self.FIXED_PERSON_TEMPLATES)])
        # Эффекты от предметов всегда стартуют с False.
        template["has_perfume"] = False
        template["has_headphones"] = False
        template["has_phone"] = False
        return template

    # Добавляет count новых пассажиров на платформу.
    def _spawn_new_passengers(self, count: int) -> None:
        # Ищем, какие слоты платформы еще свободны.
        used_slots = {person.platform_slot for person in self.people if person.seat_index is None}
        free_slots = [slot for slot in range(len(self.platform_slots)) if slot not in used_slots]

        # Общий радиус для drag&drop коллизии.
        person_radius = 28

        # Создаем каждого персонажа по очереди.
        for index in range(count):
            slot_index = free_slots[index % len(free_slots)]
            slot_x, slot_y = self._platform_position(slot_index)
            template = self._generate_person_template(self.name_index)
            avatar_color = self.AVATAR_COLORS[index % len(self.AVATAR_COLORS)]
            person = Person(
                name=self._next_person_name(),
                x=slot_x,
                y=slot_y,
                radius=person_radius,
                platform_slot=slot_index,
                avatar_color=avatar_color,
                stinks=template["stinks"],
                listens_music=template["listens_music"],
                has_perfume=template["has_perfume"],
                has_headphones=template["has_headphones"],
                has_phone=template["has_phone"],
                wants_window=template["wants_window"],
                wants_sleep=template["wants_sleep"],
                wants_chat=template["wants_chat"],
                wants_solitude=template["wants_solitude"],
                smell_sensitive=template["smell_sensitive"],
            )
            self.people.append(person)

    # Выдает предметы игроку: всегда по 1 каждого типа.
    def _roll_items(self) -> None:
        self.item_counts = {key: 1 for key in ITEM_ORDER}

    # Определяет, на какой слот предмета нажал игрок.
    def _item_slot_at(self, x: float, y: float) -> str | None:
        for item_key, rect in self.FIXED_ITEM_SLOT_RECTS.items():
            if self._rect_contains(rect, x, y):
                return item_key
        return None

    # Применяет выбранный предмет к персонажу.
    def _apply_item_to_person(self, item_key: str, person: Person) -> bool:
        changed = False

        # Духи убирают "воняет" и помечают, что духи применены.
        if item_key == "perfume":
            if person.stinks:
                person.stinks = False
                changed = True
            if not person.has_perfume:
                person.has_perfume = True
                changed = True
        # Наушники включают флаг has_headphones.
        elif item_key == "headphones":
            if not person.has_headphones:
                person.has_headphones = True
                changed = True
        # Телефон включает has_phone и снимает требование сидеть у окна.
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

    # Выравнивает всех ожидающих пассажиров по их платформенным слотам.
    def _reposition_waiting_people(self) -> None:
        for person in self.people:
            if person.seat_index is not None:
                continue
            if person is self.dragged_person:
                continue
            slot_x, slot_y = self._platform_position(person.platform_slot)
            person.x = slot_x
            person.y = slot_y

    # Главная функция логики: пересчет запаха/шума и настроения пассажиров.
    def _refresh_state(self) -> None:
        # Сбрасываем эффекты на всех местах.
        for seat in self.seats:
            seat.is_smelly = False
            seat.is_loud = False

        # Распространяем эффекты от занятых мест.
        for seat_index, seat in enumerate(self.seats):
            if seat.occupant is None:
                continue
            for target_index in [seat_index, *self.effect_neighbors[seat_index]]:
                if seat.occupant.stinks:
                    self.seats[target_index].is_smelly = True
                if seat.occupant.listens_music and not seat.occupant.has_headphones:
                    self.seats[target_index].is_loud = True

        # Проверяем удовлетворенность каждого пассажира.
        for person in self.people:
            if person.seat_index is None:
                person.is_happy = None
                continue

            seat_index = person.seat_index
            seat = self.seats[seat_index]
            # Соседи для запаха/музыки.
            near_people = [
                self.seats[i].occupant
                for i in self.effect_neighbors[seat_index]
                if self.seats[i].occupant is not None
            ]
            # Соседи для общения/одиночества.
            chat_people = [
                self.seats[i].occupant
                for i in self.chat_neighbors[seat_index]
                if self.seats[i].occupant is not None
            ]

            happy = True
            # Проверки требований и ограничений по очереди.
            if person.wants_window and not person.has_phone and not seat.is_window:
                happy = False
            if person.wants_sleep and not person.has_headphones and any(
                p.listens_music for p in near_people
            ):
                happy = False
            if person.wants_chat and not chat_people:
                happy = False
            if person.wants_solitude and chat_people:
                happy = False
            if person.smell_sensitive and any(p.stinks for p in near_people):
                happy = False
            person.is_happy = happy

    # Пытается посадить пассажира на выбранное место.
    def _try_place_in_seat(self, person: Person, seat_index: int) -> bool:
        target_seat = self.seats[seat_index]
        # Нельзя садить на уже занятое место другим персонажем.
        if target_seat.occupant is not None and target_seat.occupant is not person:
            return False

        # Если персонаж уже где-то сидел, освобождаем старое место.
        if person.seat_index is not None:
            self.seats[person.seat_index].occupant = None
        # Фиксируем новую посадку.
        target_seat.occupant = person
        person.seat_index = seat_index
        person.x = target_seat.center_x
        person.y = target_seat.center_y
        self._refresh_state()
        return True

    # Проверяет, можно ли уезжать на следующий уровень.
    def _can_depart(self) -> bool:
        if self.is_traveling or not self.people:
            return False
        return all(person.seat_index is not None and person.is_happy for person in self.people)

    # Запускает анимацию движения автобуса.
    def _start_travel(self) -> None:
        if not self._can_depart():
            return
        self.is_traveling = True
        self.travel_elapsed = 0
        self.dragged_person = None
        self.dragged_item = None
        self.mouse_down_left = False

    # Завершает этап движения: победа или переход на новый уровень.
    def _finish_travel(self) -> None:
        if self.level_index >= len(self.LEVEL_PLATFORM_COUNTS) - 1:
            self.window.show_view(MainMenuView())
            return

        # Половина сидящих выходит на новой остановке.
        seated_people = [person for person in self.people if person.seat_index is not None]
        seated_people.sort(key=lambda person: person.seat_index if person.seat_index is not None else -1)
        leave_count = len(seated_people) // 2
        for person in seated_people[:leave_count]:
            if person.seat_index is not None:
                self.seats[person.seat_index].occupant = None
            self.people.remove(person)

        self.level_index += 1
        self._roll_items()
        self._spawn_new_passengers(self.LEVEL_PLATFORM_COUNTS[self.level_index])
        self._reposition_waiting_people()
        self._refresh_state()

    # Обновление в каждом кадре (нужно для таймера переезда).
    def on_update(self, delta_time: float) -> None:
        if not self.is_traveling:
            return
        self.travel_elapsed += delta_time
        if self.travel_elapsed >= self.TRAVEL_DURATION_SECONDS:
            self.is_traveling = False
            self._finish_travel()

    # Отправляет персонажа обратно в его слот на платформе.
    def _send_to_platform(self, person: Person) -> None:
        if person.seat_index is not None:
            self.seats[person.seat_index].occupant = None
        person.seat_index = None
        slot_x, slot_y = self._platform_position(person.platform_slot)
        person.x = slot_x
        person.y = slot_y
        self._refresh_state()

    # Ищет персонажа под курсором мыши.
    def _person_under_cursor(self, x: float, y: float) -> Person | None:
        candidates = [person for person in self.people if person.contains(x, y)]
        if not candidates:
            return None
        # Перетаскиваемому персонажу всегда даем приоритет.
        if self.dragged_person in candidates:
            return self.dragged_person
        # Из совпавших выбираем того, кто визуально сверху по текущему порядку.
        candidates.sort(key=lambda person: person.y)
        return candidates[0]

    # Ищет индекс места по координатам мыши.
    def _seat_at_point(self, x: float, y: float) -> int | None:
        for index, seat in enumerate(self.seats):
            if seat.contains(x, y):
                return index
        return None

    # Универсальная проверка попадания точки в прямоугольник.
    def _rect_contains(self, rect: tuple[float, float, float, float], x: float, y: float) -> bool:
        rect_x, rect_y, rect_w, rect_h = rect
        return rect_x <= x <= rect_x + rect_w and rect_y <= y <= rect_y + rect_h

    # Возвращает прямоугольник кнопки "Поехать".
    def _depart_button_rect(self) -> tuple[float, float, float, float]:
        go_texture = self.game_button_textures["go"]["normal"]
        return (
            self.FIXED_DEPART_BUTTON_X,
            self.FIXED_DEPART_BUTTON_Y,
            float(go_texture.width),
            float(go_texture.height),
        )

    # Главная отрисовка кадра.
    def on_draw(self) -> None:
        self.clear()

        # Экран переезда: движущийся фон + автобус с закрытой дверью.
        if self.is_traveling:
            progress = min(1, self.travel_elapsed / self.TRAVEL_DURATION_SECONDS)
            travel_w = float(self.travel_texture.width)
            travel_h = float(self.travel_texture.height)
            offset = progress * travel_w
            draw_texture_lbwh(self.travel_texture, -offset, 0, travel_w, travel_h)
            draw_texture_lbwh(self.travel_texture, -offset + travel_w, 0, travel_w, travel_h)
            draw_texture_lbwh(
                self.bus_closed_texture,
                self.FIXED_BUS_X,
                self.FIXED_BUS_Y,
                float(self.bus_closed_texture.width),
                float(self.bus_closed_texture.height),
            )
            # Сидящие пассажиры продолжают быть видны в автобусе даже во время переезда.
            seated_people = [person for person in self.people if person.seat_index is not None]
            seated_people.sort(key=lambda person: person.y, reverse=True)
            for person in seated_people:
                texture = self._person_visual_texture(person)
                seat = self.seats[person.seat_index]
                if seat.faces_right:
                    texture = texture.flip_horizontally()
                texture_w = float(texture.width)
                texture_h = float(texture.height)
                draw_texture_lbwh(
                    texture,
                    person.x - texture_w / 2,
                    person.y - texture_h / 2,
                    texture_w,
                    texture_h,
                )
            return

        # Основной игровой экран.
        draw_texture_lbwh(
            self.background_texture,
            0,
            0,
            float(self.background_texture.width),
            float(self.background_texture.height),
        )
        draw_texture_lbwh(
            self.item_slots_overlay_texture,
            0,
            0,
            float(self.item_slots_overlay_texture.width),
            float(self.item_slots_overlay_texture.height),
        )

        # Автобус с открытой дверью в режиме стоянки.
        bus_x, bus_y, bus_width, bus_height = self.bus_area
        draw_texture_lbwh(self.bus_open_texture, bus_x, bus_y, bus_width, bus_height)

        # Отрисовка иконок предметов (серый, если предмет потрачен).
        for item_key, rect in self.FIXED_ITEM_SLOT_RECTS.items():
            rect_x, rect_y, rect_w, rect_h = rect
            icon_texture = self.item_icon_textures[item_key]
            icon_w = float(icon_texture.width)
            icon_h = float(icon_texture.height)
            icon_left = rect_x + (rect_w - icon_w) / 2
            icon_bottom = rect_y + (rect_h - icon_h) / 2
            if self.item_counts[item_key] > 0:
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

        # Бейдж текущего уровня.
        level_texture = self.level_badge_textures[self.level_index]
        draw_texture_lbwh(
            level_texture,
            self.FIXED_LEVEL_BADGE_X,
            self.FIXED_LEVEL_BADGE_Y,
            float(level_texture.width),
            float(level_texture.height),
        )

        # Рисуем всех пассажиров, кроме того, кого сейчас тащим мышью.
        people_to_draw = [person for person in self.people if person is not self.dragged_person]
        people_to_draw.sort(key=lambda person: person.y, reverse=True)
        for person in people_to_draw:
            texture = self._person_visual_texture(person)
            if person.seat_index is not None:
                seat = self.seats[person.seat_index]
                if seat.faces_right:
                    texture = texture.flip_horizontally()
            texture_w = float(texture.width)
            texture_h = float(texture.height)
            draw_texture_lbwh(
                texture,
                person.x - texture_w / 2,
                person.y - texture_h / 2,
                texture_w,
                texture_h,
            )

        # Перетаскиваемый пассажир рисуется последним, чтобы быть поверх всех.
        if self.dragged_person is not None:
            person = self.dragged_person
            texture = self._person_visual_texture(person)
            texture_w = float(texture.width)
            texture_h = float(texture.height)
            draw_texture_lbwh(
                texture,
                person.x - texture_w / 2,
                person.y - texture_h / 2,
                texture_w,
                texture_h,
            )

        # Тултип по персонажу или предмету под курсором.
        hovered = self._person_under_cursor(self.mouse_x, self.mouse_y)
        tooltip_lines = None

        if hovered is not None:
            tooltip_lines = [hovered.name]
            # Добавляем только те свойства/требования, которые реально активны.
            if hovered.stinks:
                tooltip_lines.append("Воняет")
            if hovered.listens_music:
                tooltip_lines.append("Слушает музыку")
            if hovered.has_perfume:
                tooltip_lines.append("Вкусно пахнет")
            if hovered.has_headphones:
                tooltip_lines.append("В наушниках")
            if hovered.has_phone:
                tooltip_lines.append("Играет в телефон")
            if hovered.wants_window:
                tooltip_lines.append("Хочет сидеть у окна")
            if hovered.wants_sleep:
                tooltip_lines.append("Хочет спать")
            if hovered.wants_chat:
                tooltip_lines.append("Хочет болтать")
            if hovered.wants_solitude:
                tooltip_lines.append("Хочет сидеть в одиночестве")
            if hovered.smell_sensitive:
                tooltip_lines.append("Не терпит запахи")

            # Нейтральное настроение не показываем, но happy/sad показываем.
            mood_line = None
            if hovered.is_happy is True:
                mood_line = "Доволен"
            elif hovered.is_happy is False:
                mood_line = "Грустный"
            if mood_line is not None:
                tooltip_lines.append("")
                tooltip_lines.append(mood_line)
        else:
            item_key = self._item_slot_at(self.mouse_x, self.mouse_y)
            if item_key is not None:
                item_info = {
                    "perfume": ("Духи", "Убирают свойство «Воняет»."),
                    "headphones": ("Наушники", "Позволяют спать даже рядом с музыкой."),
                    "phone": ("Телефон", "Снимает требование сидеть у окна."),
                }
                title, description = item_info[item_key]
                tooltip_lines = [title, description]
                if self.item_counts[item_key] <= 0:
                    tooltip_lines.append("")
                    tooltip_lines.append("Предмет закончился")

        if tooltip_lines is not None:
            # Расчет размеров/позиции тултипа.
            line_height = 22
            tip_w = 380
            tip_h = 14 + line_height * len(tooltip_lines)
            tip_x = self.mouse_x + 16
            tip_y = self.mouse_y + 16
            if tip_x + tip_w > self.window.width:
                tip_x = self.window.width - tip_w - 10
            if tip_y + tip_h > self.window.height:
                tip_y = self.window.height - tip_h - 10

            # Фон + рамка + текст тултипа.
            arcade.draw_lbwh_rectangle_filled(tip_x, tip_y, tip_w, tip_h, (250, 252, 255, 235))
            arcade.draw_lbwh_rectangle_outline(tip_x, tip_y, tip_w, tip_h, (90, 120, 150, 255), 2)
            text_y = tip_y + tip_h - 26
            for line in tooltip_lines:
                arcade.draw_text(line, tip_x + 12, text_y, (35, 52, 70, 255), 16)
                text_y -= line_height

        # Иконка перетаскиваемого предмета рядом с мышью.
        if self.dragged_item is not None:
            icon_texture = self.item_icon_textures[self.dragged_item]
            preview_w = float(icon_texture.width)
            preview_h = float(icon_texture.height)
            draw_texture_lbwh(
                icon_texture,
                self.mouse_x - preview_w / 2,
                self.mouse_y - preview_h / 2,
                preview_w,
                preview_h,
                alpha=220,
            )

        # Кнопка "Поехать" появляется, если все пассажиры посажены и довольны.
        if self._can_depart():
            rect = self._depart_button_rect()
            texture_set = self.game_button_textures["go"]
            texture = texture_set["normal"]
            if self._rect_contains(rect, self.mouse_x, self.mouse_y):
                texture = texture_set["active"] if self.mouse_down_left else texture_set["hover"]
            draw_texture_lbwh(texture, rect[0], rect[1], rect[2], rect[3])

    # Обработчик нажатия кнопки мыши.
    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int) -> None:
        self.mouse_x = x
        self.mouse_y = y
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        self.mouse_down_left = True

        # Во время переезда любые клики по игровым объектам игнорируем.
        if self.is_traveling:
            return

        # Нажатие кнопки "Поехать".
        if self._can_depart() and self._rect_contains(self._depart_button_rect(), x, y):
            self._start_travel()
            return

        # Попытка начать перетаскивание предмета.
        item_key = self._item_slot_at(x, y)
        if item_key is not None and self.item_counts[item_key] > 0:
            self.dragged_item = item_key
            self.dragged_person = None
            return

        # Попытка начать перетаскивание персонажа.
        person = self._person_under_cursor(x, y)
        if person is None:
            return

        self.dragged_person = person
        self.dragged_item = None
        self.drag_offset_x = person.x - x
        self.drag_offset_y = person.y - y

        # Если тянем уже сидящего, сразу освобождаем его место.
        if person.seat_index is not None:
            self.seats[person.seat_index].occupant = None
            person.seat_index = None
            self._refresh_state()

        # Переносим персонажа в конец списка (чтобы был поверх при рисовании).
        self.people.remove(person)
        self.people.append(person)

    # Обработчик движения мыши при зажатой кнопке.
    def on_mouse_drag(
        self, x: float, y: float, dx: float, dy: float, buttons: int, modifiers: int
    ) -> None:
        self.mouse_x = x
        self.mouse_y = y
        if self.is_traveling:
            return
        if self.dragged_person is None:
            return
        if not (buttons & arcade.MOUSE_BUTTON_LEFT):
            return

        # Двигаем персонажа и ограничиваем координаты границами окна.
        radius = self.dragged_person.radius
        next_x = x + self.drag_offset_x
        next_y = y + self.drag_offset_y
        self.dragged_person.x = max(radius, min(self.window.width - radius, next_x))
        self.dragged_person.y = max(radius, min(self.window.height - radius, next_y))

    # Обработчик отпускания кнопки мыши.
    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int) -> None:
        self.mouse_x = x
        self.mouse_y = y
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        self.mouse_down_left = False
        if self.is_traveling:
            return

        # Логика завершения перетаскивания предмета.
        if self.dragged_item is not None:
            item_key = self.dragged_item
            target_person = self._person_under_cursor(x, y)
            if target_person is not None and self.item_counts[item_key] > 0:
                if self._apply_item_to_person(item_key, target_person):
                    self.item_counts[item_key] -= 1
            self.dragged_item = None
            return

        # Если никого не тащили, ничего делать не нужно.
        if self.dragged_person is None:
            return

        # Пробуем посадить в место под персонажем.
        target_seat_index = self._seat_at_point(self.dragged_person.x, self.dragged_person.y)
        placed = False
        if target_seat_index is not None:
            placed = self._try_place_in_seat(self.dragged_person, target_seat_index)

        # Если посадить не вышло — возвращаем на платформу.
        if not placed:
            self._send_to_platform(self.dragged_person)

        # Сбрасываем состояние перетаскивания персонажа.
        self.dragged_person = None

    # Обработчик движения мыши без зажатых кнопок (нужен для hover-эффектов).
    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float) -> None:
        self.mouse_x = x
        self.mouse_y = y
        return



# Сцена главного меню.
class MainMenuView(arcade.View):
    # Создает сцену главного меню и загружает ее ресурсы.
    def __init__(self) -> None:
        super().__init__()
        # UIManager отвечает за кнопку "Играть/Выйти".
        self.manager = arcade.gui.UIManager()
        self.menu_background_texture = load_texture(SCREENS_DIR / 'entrance.png')
        self.menu_button_textures: dict[str, dict[str, arcade.Texture]] = {
            'play': load_button_texture_set('play'),
            'exit': load_button_texture_set('exit'),
        }

    # Вызывается, когда меню становится активным экраном.
    def on_show_view(self) -> None:
        self.window.set_mouse_visible(True)
        self.manager.enable()
        self._build_ui()

    # Вызывается, когда мы уходим с экрана меню.
    def on_hide_view(self) -> None:
        self.manager.disable()
        self.manager.clear()

    # Создает и размещает кнопки меню.
    def _build_ui(self) -> None:
        self.manager.clear()

        # Берем все состояния текстур для кнопки "Играть".
        play_texture_set = self.menu_button_textures['play']
        play_texture = play_texture_set['normal']
        play_texture_hover = play_texture_set['hover']
        play_texture_press = play_texture_set['active']

        # Берем все состояния текстур для кнопки "Выйти".
        exit_texture_set = self.menu_button_textures['exit']
        exit_texture = exit_texture_set['normal']
        exit_texture_hover = exit_texture_set['hover']
        exit_texture_press = exit_texture_set['active']

        # Кнопка старта игры.
        play_button = arcade.gui.UITextureButton(
            width=int(play_texture.width),
            height=int(play_texture.height),
            text='',
            texture=play_texture,
            texture_hovered=play_texture_hover,
            texture_pressed=play_texture_press,
        )

        # Кнопка выхода из приложения.
        exit_button = arcade.gui.UITextureButton(
            width=int(exit_texture.width),
            height=int(exit_texture.height),
            text='',
            texture=exit_texture,
            texture_hovered=exit_texture_hover,
            texture_pressed=exit_texture_press,
        )

        # Событие нажатия "Играть" — открываем GameView.
        @play_button.event('on_click')
        def _on_click_play(event: arcade.gui.UIOnClickEvent) -> None:
            self.window.show_view(GameView())

        # Событие нажатия "Выйти" — закрываем приложение.
        @exit_button.event('on_click')
        def _on_click_exit(event: arcade.gui.UIOnClickEvent) -> None:
            arcade.exit()

        # Расставляем кнопки слева/справа от центра на одной высоте.
        gap = 80
        play_align_x = int(play_texture.width / 2 + gap / 2)
        exit_align_x = -int(exit_texture.width / 2 + gap / 2)
        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(play_button, anchor_x='center_x', anchor_y='center_y', align_x=play_align_x)
        anchor.add(exit_button, anchor_x='center_x', anchor_y='center_y', align_x=exit_align_x)
        self.manager.add(anchor)

    # Отрисовка меню: сначала фон, затем UI-кнопки.
    def on_draw(self) -> None:
        self.clear()
        draw_texture_lbwh(
            self.menu_background_texture,
            0,
            0,
            float(self.menu_background_texture.width),
            float(self.menu_background_texture.height),
        )
        self.manager.draw()


# Точка входа: создаем окно и показываем главное меню.
def main() -> None:
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.show_view(MainMenuView())
    arcade.run()


# Стандартный запуск python-скрипта напрямую.
if __name__ == "__main__":
    main()

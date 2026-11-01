"""Main window."""

import math
import time
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QAction, QBrush, QColor, QGuiApplication, QPainter, QPainterPath, QPen,
                           QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QFileDialog, QGridLayout, QHBoxLayout,
                               QLabel, QMenu, QPushButton, QScrollArea, QSpinBox, QStackedWidget,
                               QSystemTrayIcon, QVBoxLayout, QWidget)

from . import __version__, macro, odds, settings as settings_store, theme, winapi
from .engine import ClickConfig, ClickEngine
from .icon import app_icon
from .picker import PointPicker
from .scene import SakuraScene, paint_cover_image
from .widgets import CLEAR, GlassCard, GlyphButton, HotkeyButton, OrbButton, Segmented, Toggle

HK_CLICKER, HK_RECORD, HK_PLAY, HK_STOP_PAUSE, HK_STOP_SCROLL = range(0x4741, 0x4746)
BUTTONS = ["left", "middle", "right"]
REPEAT_MODES = ["infinite", "count", "duration"]
POSITION_MODES = ["cursor", "points"]
MACRO_REPEAT = ["once", "count", "continuous"]
THEMES = ["system", "dark", "light", "anime", "noir"]
CHANCE_MODES = ["percent", "one_in"]
TAB_MACRO = 2
TAB_DROPS = 3
WINDOW_RADIUS = 8  # matches the Windows 11 rounded frame so the blur never peeks out
MACRO_FILTER = "Macros do Klicker (*.kmacro *.gcmacro);;Todos os arquivos (*.*)"
RESULT_ROWS = [
    ("chance", "Chance por fase"),
    ("mean", "Média até o drop"),
    ("q50", "Metade das vezes, até"),
    ("q90", "90% das vezes, até"),
    ("q99", "Azar extremo (99%)"),
    ("worst", "Pior cenário"),
    ("goal_mean", ""),
    ("goal_q90", ""),
    ("goal_worst", ""),
    ("farm_items", ""),
    ("farm_any", ""),
]


class _Bridge(QObject):
    """Carries worker-thread callbacks onto the GUI thread."""

    clicker_finished = Signal(str)
    macro_finished = Signal(str)


def _label(text, name=None):
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    return label


def _spin(maximum, width=None, suffix=""):
    spin = QSpinBox()
    spin.setRange(0, maximum)
    spin.setAlignment(Qt.AlignCenter)
    spin.setFixedHeight(36)
    spin.setSuffix(suffix)
    if width:
        spin.setFixedWidth(width)
    return spin


def _dspin(minimum, maximum, decimals, width=None, suffix=""):
    spin = QDoubleSpinBox()
    spin.setDecimals(decimals)
    spin.setRange(minimum, maximum)
    spin.setAlignment(Qt.AlignCenter)
    spin.setFixedHeight(36)
    spin.setSuffix(suffix)
    if width:
        spin.setFixedWidth(width)
    return spin


def _pill(text, slot):
    button = QPushButton(text)
    button.setObjectName("pill")
    button.setCursor(Qt.PointingHandCursor)
    button.clicked.connect(slot)
    return button


def _card(title=None, caption=None):
    card = GlassCard()
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 16)
    layout.setSpacing(10)
    if title:
        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(_label(title, "section"))
        if caption:
            cap = _label(caption, "caption")
            cap.setWordWrap(True)
            head.addWidget(cap)
        layout.addLayout(head)
    return card, layout


def _row(*items, stretch_at=None):
    row = QHBoxLayout()
    row.setSpacing(10)
    for i, item in enumerate(items):
        if i == stretch_at:
            row.addStretch(1)
        if isinstance(item, QWidget):
            row.addWidget(item)
        else:
            row.addLayout(item)
    if stretch_at == len(items):
        row.addStretch(1)
    return row


def _row_widget(*items, stretch_at=None):
    widget = QWidget()
    layout = _row(*items, stretch_at=stretch_at)
    layout.setContentsMargins(0, 0, 0, 0)
    widget.setLayout(layout)
    return widget


def _format_duration(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class TitleBar(QWidget):
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.window().windowHandle().startSystemMove()


class MainWindow(QWidget):
    def __init__(self, settings):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle("Klicker")
        self.setWindowIcon(app_icon())
        self.setFixedSize(440, 820)

        self.s = settings
        self._loading = False
        self._hwnd = 0
        self._hotkey_failures = []
        self._acrylic_on = False
        self._last_reason = None
        self._macro_reason = None
        self._bg_pixmap = None
        self._drop_report = None
        self._stopwatch_t0 = None
        self._scene = SakuraScene()
        self._scene_clock = time.perf_counter()

        self._bridge = _Bridge()
        self._bridge.clicker_finished.connect(self._on_clicker_finished)
        self._bridge.macro_finished.connect(self._on_macro_finished)
        self.engine = ClickEngine(on_finished=self._bridge.clicker_finished.emit)
        self.recorder = None
        self.player = macro.Player(on_finished=self._bridge.macro_finished.emit)
        self.macro_events = self._load_last_macro()
        self.picker = PointPicker(self)
        self.picker.picked.connect(self._add_point)
        self.picker.cancelled.connect(self._picker_closed)

        self._save_timer = QTimer(self, singleShot=True, interval=400, timeout=self._save)
        self._stats_timer = QTimer(self, interval=100, timeout=self._refresh)
        self._scene_timer = QTimer(self, interval=40, timeout=self._tick_scene)
        self._stopwatch_timer = QTimer(self, interval=100, timeout=self._tick_stopwatch)

        self._build()
        self._build_tray()
        self._load_background()
        self._load_into_ui()

        hints = QGuiApplication.styleHints()
        hints.colorSchemeChanged.connect(lambda _: self.s.theme == "system" and self._apply_theme())

    # ------------------------------------------------------------------ layout

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 8, 14, 14)
        root.setSpacing(12)

        title_bar = TitleBar()
        title_bar.setFixedHeight(40)
        tb = QHBoxLayout(title_bar)
        tb.setContentsMargins(4, 0, 0, 0)
        tb.setSpacing(8)
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(20, 20))
        tb.addWidget(logo)
        tb.addWidget(_label("Klicker", "appTitle"))
        self.kana = _label("クリッカー", "caption")
        tb.addWidget(self.kana)
        tb.addStretch(1)
        minimize = GlyphButton("minimize")
        minimize.setToolTip("Minimizar")
        minimize.clicked.connect(self.showMinimized)
        close = GlyphButton("close", danger_hover=True)
        close.setToolTip("Fechar")
        close.clicked.connect(self.close)
        tb.addWidget(minimize)
        tb.addWidget(close)
        root.addWidget(title_bar)

        root.addWidget(self._build_hero())

        self.tabs = Segmented(["Clique", "Posição", "Macro", "Drops", "Ajustes"])
        root.addWidget(self.tabs)

        self.stack = QStackedWidget()
        for page in (self._build_click_page(), self._build_position_page(), self._build_macro_page(),
                     self._build_drops_page(), self._build_settings_page()):
            self.stack.addWidget(self._scrollable(page))
        self.tabs.changed.connect(self._tab_changed)
        root.addWidget(self.stack, 1)

    def _scrollable(self, page):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(page)
        return scroll

    def _build_hero(self):
        card, layout = _card()
        layout.setContentsMargins(16, 8, 16, 12)
        layout.setSpacing(4)

        self.orb_stack = QStackedWidget()
        self.orb_stack.setFixedHeight(140)
        self.orb = OrbButton()
        self.orb.clicked.connect(self.toggle)
        clicker_page = QWidget()
        cl = QHBoxLayout(clicker_page)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.addWidget(self.orb, 0, Qt.AlignCenter)
        self.orb_stack.addWidget(clicker_page)

        macro_page = QWidget()
        ml = QHBoxLayout(macro_page)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(28)
        ml.addStretch(1)
        self.record_orb = OrbButton("record", "danger", 112)
        self.record_orb.setToolTip("Gravar / parar gravação")
        self.record_orb.clicked.connect(self.toggle_record)
        self.play_orb = OrbButton("play", "accent", 112)
        self.play_orb.setToolTip("Reproduzir / parar")
        self.play_orb.clicked.connect(self.toggle_play)
        self.record_caption = _label("", "caption")
        self.play_caption = _label("", "caption")
        for orb, caption in ((self.record_orb, self.record_caption), (self.play_orb, self.play_caption)):
            col = QVBoxLayout()
            col.setSpacing(0)
            col.addWidget(orb, 0, Qt.AlignHCenter)
            caption.setAlignment(Qt.AlignCenter)
            col.addWidget(caption)
            ml.addLayout(col)
        ml.addStretch(1)
        self.orb_stack.addWidget(macro_page)
        layout.addWidget(self.orb_stack)

        self.status = _label("", "status")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        stats = QHBoxLayout()
        stats.setContentsMargins(0, 6, 0, 0)
        self.stats = [self._stat(stats) for _ in range(3)]
        layout.addLayout(stats)
        return card

    def _stat(self, row):
        col = QVBoxLayout()
        col.setSpacing(0)
        value = _label("0", "statValue")
        value.setAlignment(Qt.AlignCenter)
        caption = _label("", "caption")
        caption.setAlignment(Qt.AlignCenter)
        col.addWidget(value)
        col.addWidget(caption)
        row.addLayout(col, 1)
        return value, caption

    def _page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        return page, layout

    def _build_click_page(self):
        page, layout = self._page()

        card, c = _card("Intervalo entre cliques")
        fields = QHBoxLayout()
        fields.setSpacing(8)
        self.spin_h = self._time_field(fields, 23, "horas")
        self.spin_m = self._time_field(fields, 59, "min")
        self.spin_s = self._time_field(fields, 59, "seg")
        self.spin_ms = self._time_field(fields, 999, "ms")
        c.addLayout(fields)
        self.jitter_toggle = Toggle()
        self.jitter_spin = _spin(5000, 104, " ms")
        self.jitter_spin.setPrefix("± ")
        c.addLayout(_row(self.jitter_toggle, _label("Variação aleatória"), self.jitter_spin, stretch_at=2))
        layout.addWidget(card)

        card, c = _card("Botão e tipo de clique")
        self.button_seg = Segmented(["Esquerdo", "Meio", "Direito"])
        self.clicks_seg = Segmented(["Simples", "Duplo", "Triplo"])
        c.addWidget(self.button_seg)
        c.addWidget(self.clicks_seg)
        layout.addWidget(card)

        card, c = _card("Repetição")
        self.repeat_seg = Segmented(["Até parar", "Vezes", "Duração"])
        c.addWidget(self.repeat_seg)
        self.repeat_label = _label("")
        self.repeat_spin = _spin(10_000_000, 140)
        self.repeat_row = _row_widget(self.repeat_label, self.repeat_spin, stretch_at=1)
        c.addWidget(self.repeat_row)
        layout.addWidget(card)

        layout.addStretch(1)
        for w in (self.spin_h, self.spin_m, self.spin_s, self.spin_ms, self.jitter_spin, self.repeat_spin):
            w.valueChanged.connect(self._changed)
        for w in (self.button_seg, self.clicks_seg, self.repeat_seg):
            w.changed.connect(self._changed)
        self.jitter_toggle.toggled.connect(self._changed)
        return page

    def _time_field(self, row, maximum, caption, spin=None):
        col = QVBoxLayout()
        col.setSpacing(4)
        spin = spin or _spin(maximum)
        spin.setMinimumWidth(56)  # the default size hint is wide enough to overflow the scroll area
        cap = _label(caption, "caption")
        cap.setAlignment(Qt.AlignCenter)
        col.addWidget(spin)
        col.addWidget(cap)
        row.addLayout(col, 1)
        return spin

    def _build_position_page(self):
        page, layout = self._page()

        card, c = _card("Onde clicar")
        self.position_seg = Segmented(["Cursor atual", "Pontos fixos"])
        self.position_caption = _label("", "caption")
        self.position_caption.setWordWrap(True)
        c.addWidget(self.position_seg)
        c.addWidget(self.position_caption)
        layout.addWidget(card)

        self.points_card, c = _card("Pontos", "Os pontos são clicados em ordem, em ciclo.")
        self.points_list = QWidget()
        self.points_layout = QVBoxLayout(self.points_list)
        self.points_layout.setContentsMargins(0, 0, 6, 0)
        self.points_layout.setSpacing(6)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.points_list)
        scroll.setFixedHeight(150)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        c.addWidget(scroll)
        c.addLayout(_row(_pill("＋  Escolher ponto", self._pick_point), _pill("Limpar", self._clear_points),
                         stretch_at=2))
        self.restore_toggle = Toggle()
        c.addLayout(_row(self.restore_toggle, _label("Devolver o cursor após cada clique"), stretch_at=2))
        layout.addWidget(self.points_card)

        layout.addStretch(1)
        self.position_seg.changed.connect(self._changed)
        self.restore_toggle.toggled.connect(self._changed)
        return page

    def _build_macro_page(self):
        page, layout = self._page()

        card, c = _card("Velocidade de reprodução")
        self.speed_seg = Segmented(["1x", "2x", "100x", "Outra"])
        c.addWidget(self.speed_seg)
        self.speed_spin = _spin(100, 110, "x")
        self.speed_spin.setRange(1, 100)
        self.speed_row = _row_widget(_label("Multiplicador (1–100)"), self.speed_spin, stretch_at=1)
        c.addWidget(self.speed_row)
        layout.addWidget(card)

        card, c = _card("Repetir a macro")
        self.macro_repeat_seg = Segmented(["Uma vez", "Vezes", "Contínuo"])
        c.addWidget(self.macro_repeat_seg)
        self.loops_spin = _spin(100_000, 110)
        self.loops_spin.setRange(1, 100_000)
        self.loops_row = _row_widget(_label("Número de repetições"), self.loops_spin, stretch_at=1)
        c.addWidget(self.loops_row)
        layout.addWidget(card)

        card, c = _card("Gravação", "Pause ou Scroll Lock interrompem a reprodução a qualquer momento.")
        self.moves_toggle = Toggle()
        self.keys_toggle = Toggle()
        c.addLayout(_row(_label("Gravar movimentos do mouse"), self.moves_toggle, stretch_at=1))
        c.addLayout(_row(_label("Gravar teclado"), self.keys_toggle, stretch_at=1))
        layout.addWidget(card)

        card, c = _card("Arquivo", "Compile para gerar um .exe independente que só reproduz esta macro.")
        self.compile_btn = _pill("Compilar .exe", self._compile_macro)
        c.addLayout(_row(_pill("Abrir…", self._open_macro), _pill("Salvar…", self._save_macro),
                         self.compile_btn, stretch_at=3))
        layout.addWidget(card)

        layout.addStretch(1)
        for w in (self.speed_seg, self.macro_repeat_seg):
            w.changed.connect(self._changed)
        for w in (self.speed_spin, self.loops_spin):
            w.valueChanged.connect(self._changed)
        for w in (self.moves_toggle, self.keys_toggle):
            w.toggled.connect(self._changed)
        return page

    def _build_drops_page(self):
        page, layout = self._page()

        card, c = _card("Drop", "Chance de o item cair em cada fase (ou ovo, baú, boss…).")
        self.chance_spin = _dspin(0, 100, 4, 160)
        self.chance_seg = Segmented(["%", "1 em N"])
        self.chance_seg.setFixedWidth(150)
        c.addLayout(_row(self.chance_spin, self.chance_seg, stretch_at=1))
        self.luck_spin = _dspin(0.01, 1000, 2, 110, "x")
        c.addLayout(_row(_label("Multiplicador de sorte"), self.luck_spin, stretch_at=1))
        self.items_spin = _spin(1_000_000, 110)
        self.items_spin.setRange(1, 1_000_000)
        c.addLayout(_row(_label("Itens por drop"), self.items_spin, stretch_at=1))
        layout.addWidget(card)

        card, c = _card("Fase", "Tempo de uma tentativa, contando o reinício. Use o cronômetro se não souber.")
        fields = QHBoxLayout()
        fields.setSpacing(8)
        self.run_min_spin = self._time_field(fields, 999, "min")
        self.run_sec_spin = self._time_field(fields, 0, "seg", _dspin(0, 59.9, 1))
        c.addLayout(fields)
        self.stopwatch_btn = _pill("", self._toggle_stopwatch)
        c.addLayout(_row(self.stopwatch_btn, stretch_at=1))
        self.pity_toggle = Toggle()
        self.pity_spin = _spin(odds.MAX_PITY, 120)
        self.pity_spin.setRange(1, odds.MAX_PITY)
        self.pity_spin.setPrefix("fase ")
        c.addLayout(_row(self.pity_toggle, _label("Pity garante na"), self.pity_spin, stretch_at=2))
        self.progress_spin = _spin(odds.MAX_PITY - 1, 120)
        self.progress_row = _row_widget(_label("Fases já feitas sem drop"), self.progress_spin, stretch_at=1)
        c.addWidget(self.progress_row)
        layout.addWidget(card)

        card, c = _card("Meta")
        self.goal_spin = _spin(1_000_000, 110)
        self.goal_spin.setRange(1, 1_000_000)
        c.addLayout(_row(_label("Quantos itens eu quero"), self.goal_spin, stretch_at=1))
        self.farm_h_spin = _spin(9999, 84, " h")
        self.farm_m_spin = _spin(59, 84, " min")
        c.addLayout(_row(_label("Tempo de farm"), self.farm_h_spin, self.farm_m_spin, stretch_at=1))
        layout.addWidget(card)

        card, c = _card("Resultado")
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        grid.setColumnStretch(1, 1)
        self.result_rows = {}
        for row, (key, text) in enumerate(RESULT_ROWS):
            name = _label(text, "caption")
            value = _label("", "resultValue")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value.setWordWrap(True)
            grid.addWidget(name, row, 0)
            grid.addWidget(value, row, 1)
            self.result_rows[key] = (name, value)
        c.addLayout(grid)
        self.result_note = _label("", "resultHint")
        self.result_note.setWordWrap(True)
        c.addWidget(self.result_note)
        layout.addWidget(card)

        layout.addStretch(1)
        for w in (self.chance_spin, self.luck_spin, self.items_spin, self.run_min_spin, self.run_sec_spin,
                  self.pity_spin, self.progress_spin, self.goal_spin, self.farm_h_spin, self.farm_m_spin):
            w.valueChanged.connect(self._changed)
        self.chance_seg.changed.connect(self._changed)
        self.pity_toggle.toggled.connect(self._changed)
        return page

    def _build_settings_page(self):
        page, layout = self._page()

        card, c = _card("Atalhos globais", "Funcionam mesmo com a janela minimizada ou em segundo plano.")
        self.hotkey_buttons = {}
        for hk_id, text in ((HK_CLICKER, "Auto clicker"), (HK_RECORD, "Gravar macro"),
                            (HK_PLAY, "Reproduzir macro")):
            button = HotkeyButton()
            button.captureStarted.connect(self._unregister_hotkeys)
            button.captureEnded.connect(lambda accepted, hk_id=hk_id: self._hotkey_captured(hk_id, accepted))
            self.hotkey_buttons[hk_id] = button
            c.addLayout(_row(_label(text), button, stretch_at=1))
        layout.addWidget(card)

        card, c = _card("Janela")
        self.top_toggle = Toggle()
        self.protect_toggle = Toggle()
        self.acrylic_toggle = Toggle()
        c.addLayout(_row(_label("Sempre no topo"), self.top_toggle, stretch_at=1))
        c.addLayout(_row(_label("Nunca clicar sobre o Klicker"), self.protect_toggle, stretch_at=1))
        c.addLayout(_row(_label("Vidro com desfoque do fundo"), self.acrylic_toggle, stretch_at=1))
        layout.addWidget(card)

        card, c = _card("Aparência")
        self.theme_seg = Segmented(["Sistema", "Escuro", "Claro", "Anime", "Noir"])
        c.addWidget(self.theme_seg)
        self.petals_toggle = Toggle()
        self.petals_row = _row_widget(_label("Pétalas de sakura animadas"), self.petals_toggle, stretch_at=1)
        c.addWidget(self.petals_row)
        self.bg_caption = _label("", "caption")
        self.bg_caption.setWordWrap(True)
        c.addLayout(_row(_label("Imagem de fundo"), _pill("Escolher…", self._choose_background),
                         _pill("Remover", self._clear_background), stretch_at=1))
        c.addWidget(self.bg_caption)
        layout.addWidget(card)

        about = _label(f"Klicker {__version__}  ·  código aberto, licença MIT", "caption")
        about.setAlignment(Qt.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(about)

        for w in (self.top_toggle, self.protect_toggle, self.acrylic_toggle, self.petals_toggle):
            w.toggled.connect(self._changed)
        self.theme_seg.changed.connect(self._changed)
        return page

    def _build_tray(self):
        self.tray = QSystemTrayIcon(app_icon(), self)
        menu = QMenu()
        self.tray_toggle = QAction("Iniciar auto clicker", menu, triggered=self.toggle)
        menu.addAction(self.tray_toggle)
        menu.addAction(QAction("Gravar / parar macro", menu, triggered=self.toggle_record))
        menu.addAction(QAction("Reproduzir / parar macro", menu, triggered=self.toggle_play))
        menu.addSeparator()
        menu.addAction(QAction("Mostrar janela", menu, triggered=self._show_from_tray))
        menu.addAction(QAction("Sair", menu, triggered=self.close))
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: reason == QSystemTrayIcon.Trigger and self._show_from_tray())
        self.tray.setToolTip("Klicker")
        self.tray.show()

    # ------------------------------------------------------------ settings <-> UI

    def _load_into_ui(self):
        s = self.s
        self._loading = True
        self.spin_h.setValue(s.hours)
        self.spin_m.setValue(s.minutes)
        self.spin_s.setValue(s.seconds)
        self.spin_ms.setValue(s.millis)
        self.jitter_toggle.setValue(s.jitter_enabled)
        self.jitter_spin.setValue(s.jitter_ms)
        self.button_seg.setIndex(BUTTONS.index(s.button) if s.button in BUTTONS else 0, False)
        self.clicks_seg.setIndex(s.clicks - 1, False)
        self.repeat_seg.setIndex(REPEAT_MODES.index(s.repeat_mode) if s.repeat_mode in REPEAT_MODES else 0, False)
        self.position_seg.setIndex(POSITION_MODES.index(s.position_mode) if s.position_mode in POSITION_MODES else 0, False)
        self.restore_toggle.setValue(s.restore_cursor)
        self.speed_seg.setIndex(s.speed_index, False)
        self.speed_spin.setValue(s.speed_custom)
        self.macro_repeat_seg.setIndex(MACRO_REPEAT.index(s.macro_repeat), False)
        self.loops_spin.setValue(s.macro_loops)
        self.moves_toggle.setValue(s.record_moves)
        self.keys_toggle.setValue(s.record_keys)
        for hk_id, button in self.hotkey_buttons.items():
            button.setHotkey(*self._hotkey(hk_id))
        self.top_toggle.setValue(s.always_on_top)
        self.protect_toggle.setValue(s.protect_self)
        self.acrylic_toggle.setValue(s.acrylic)
        self.petals_toggle.setValue(s.petals)
        self.theme_seg.setIndex(THEMES.index(s.theme) if s.theme in THEMES else 0, False)
        self.chance_seg.setIndex(CHANCE_MODES.index(s.drop_chance_mode), False)
        self.luck_spin.setValue(s.drop_luck)
        self.items_spin.setValue(s.drop_items)
        self.run_min_spin.setValue(s.run_minutes)
        self.run_sec_spin.setValue(s.run_seconds)
        self.pity_toggle.setValue(s.pity_enabled)
        self.pity_spin.setValue(s.pity_runs)
        self.progress_spin.setValue(s.pity_progress)
        self.goal_spin.setValue(s.goal_items)
        self.farm_h_spin.setValue(s.farm_hours)
        self.farm_m_spin.setValue(s.farm_minutes)
        self._sync_chance_spin()
        self._tick_stopwatch()
        self._sync_repeat_row()
        self._loading = False
        self._sync_dependents()
        self._render_points()

    def _changed(self, *_):
        if self._loading:
            return
        s = self.s
        previous_repeat = s.repeat_mode
        s.hours, s.minutes = self.spin_h.value(), self.spin_m.value()
        s.seconds, s.millis = self.spin_s.value(), self.spin_ms.value()
        s.jitter_enabled = self.jitter_toggle.isChecked()
        s.jitter_ms = self.jitter_spin.value()
        s.button = BUTTONS[self.button_seg.index()]
        s.clicks = self.clicks_seg.index() + 1
        s.repeat_mode = REPEAT_MODES[self.repeat_seg.index()]
        if s.repeat_mode != previous_repeat:
            self._sync_repeat_row()
        elif s.repeat_mode == "count":
            s.repeat_count = self.repeat_spin.value()
        elif s.repeat_mode == "duration":
            s.duration_s = self.repeat_spin.value()
        s.position_mode = POSITION_MODES[self.position_seg.index()]
        s.restore_cursor = self.restore_toggle.isChecked()
        s.speed_index = self.speed_seg.index()
        s.speed_custom = self.speed_spin.value()
        s.macro_repeat = MACRO_REPEAT[self.macro_repeat_seg.index()]
        s.macro_loops = self.loops_spin.value()
        s.record_moves = self.moves_toggle.isChecked()
        s.record_keys = self.keys_toggle.isChecked()

        chance_mode = CHANCE_MODES[self.chance_seg.index()]
        if chance_mode != s.drop_chance_mode:
            # Keep the same chance when switching between "0,5 %" and "1 em 200".
            if chance_mode == "one_in":
                s.drop_one_in = min(1e9, 100 / max(s.drop_chance_pct, 1e-7))
            else:
                s.drop_chance_pct = 100 / max(1.0, s.drop_one_in)
            s.drop_chance_mode = chance_mode
            self._sync_chance_spin()
        elif chance_mode == "percent":
            s.drop_chance_pct = self.chance_spin.value()
        else:
            s.drop_one_in = self.chance_spin.value()
        s.drop_luck = self.luck_spin.value()
        s.drop_items = self.items_spin.value()
        s.run_minutes = self.run_min_spin.value()
        s.run_seconds = self.run_sec_spin.value()
        s.pity_enabled = self.pity_toggle.isChecked()
        s.pity_runs = self.pity_spin.value()
        s.pity_progress = self.progress_spin.value()
        s.goal_items = self.goal_spin.value()
        s.farm_hours, s.farm_minutes = self.farm_h_spin.value(), self.farm_m_spin.value()

        theme_changed = THEMES[self.theme_seg.index()] != s.theme
        chrome_changed = (self.top_toggle.isChecked() != s.always_on_top
                          or self.acrylic_toggle.isChecked() != s.acrylic)
        s.always_on_top = self.top_toggle.isChecked()
        s.protect_self = self.protect_toggle.isChecked()
        s.acrylic = self.acrylic_toggle.isChecked()
        s.petals = self.petals_toggle.isChecked()
        s.theme = THEMES[self.theme_seg.index()]
        if theme_changed:
            self._apply_theme()
        elif chrome_changed:
            self._apply_chrome()
        self._sync_dependents()
        self._save_timer.start()

    def _sync_repeat_row(self):
        mode = self.s.repeat_mode
        self.repeat_row.setVisible(mode != "infinite")
        self.repeat_spin.blockSignals(True)
        if mode == "count":
            self.repeat_label.setText("Número de cliques")
            self.repeat_spin.setSuffix("")
            self.repeat_spin.setRange(1, 10_000_000)
            self.repeat_spin.setValue(self.s.repeat_count)
        elif mode == "duration":
            self.repeat_label.setText("Duração")
            self.repeat_spin.setSuffix(" s")
            self.repeat_spin.setRange(1, 86_400)
            self.repeat_spin.setValue(self.s.duration_s)
        self.repeat_spin.blockSignals(False)

    def _sync_chance_spin(self):
        s = self.s
        spin = self.chance_spin
        spin.blockSignals(True)
        if s.drop_chance_mode == "one_in":
            spin.setDecimals(1)
            spin.setRange(1, 1e9)
            spin.setPrefix("1 em ")
            spin.setSuffix("")
            spin.setValue(s.drop_one_in)
        else:
            spin.setDecimals(4)
            spin.setRange(0, 100)
            spin.setPrefix("")
            spin.setSuffix(" %")
            spin.setValue(s.drop_chance_pct)
        spin.blockSignals(False)

    def _sync_dependents(self):
        s = self.s
        self.jitter_spin.setEnabled(s.jitter_enabled)
        points_mode = s.position_mode == "points"
        self.points_card.setVisible(points_mode)
        self.position_caption.setText(
            "Clica em sequência nos pontos que você escolher na tela." if points_mode else
            "Clica onde o ponteiro do mouse estiver — você pode movê-lo enquanto clica.")
        self.speed_row.setVisible(s.speed_index == 3)
        self.loops_row.setVisible(s.macro_repeat == "count")
        anime = theme.palette().scene
        self.kana.setVisible(anime)
        self.petals_row.setVisible(anime)
        self.bg_caption.setText(
            f"Atual: {Path(s.background_image).name}" if s.background_image else
            "Use qualquer imagem — um wallpaper de anime fica ótimo sob o vidro.")
        self.pity_spin.setEnabled(s.pity_enabled)
        self.progress_row.setEnabled(s.pity_enabled)
        self.progress_spin.blockSignals(True)
        self.progress_spin.setMaximum(max(0, s.pity_runs - 1))
        self.progress_spin.blockSignals(False)
        s.pity_progress = self.progress_spin.value()
        self._update_drops()
        self._update_scene_timer()
        self._refresh()

    def _save(self):
        settings_store.save(self.s)

    def _hotkey(self, hk_id):
        s = self.s
        return {HK_CLICKER: (s.hotkey_vk, s.hotkey_mods), HK_RECORD: (s.record_vk, s.record_mods),
                HK_PLAY: (s.play_vk, s.play_mods)}[hk_id]

    def _hotkey_text(self, hk_id):
        return winapi.hotkey_text(*self._hotkey(hk_id))

    # ------------------------------------------------------------------ points

    def _render_points(self):
        while self.points_layout.count():
            item = self.points_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.s.points:
            empty = _label("Nenhum ponto ainda. Use “Escolher ponto” e clique em qualquer lugar da tela.",
                           "caption")
            empty.setWordWrap(True)
            self.points_layout.addWidget(empty)
        for i, (x, y) in enumerate(self.s.points):
            badge = _label(str(i + 1), "badge")
            badge.setAlignment(Qt.AlignCenter)
            remove = GlyphButton("close", size=24, danger_hover=True)
            remove.setToolTip("Remover ponto")
            remove.clicked.connect(lambda _=False, i=i: self._remove_point(i))
            self.points_layout.addWidget(_row_widget(badge, _label(f"X {x}    Y {y}"), remove, stretch_at=2))
        self.points_layout.addStretch(1)

    def _pick_point(self):
        self.picker.start()

    def _add_point(self, x, y):
        self.s.points.append((x, y))
        self._picker_closed()

    def _picker_closed(self):
        self._render_points()
        self._save_timer.start()
        self.activateWindow()

    def _remove_point(self, index):
        del self.s.points[index]
        self._render_points()
        self._save_timer.start()

    def _clear_points(self):
        self.s.points.clear()
        self._render_points()
        self._save_timer.start()

    # ------------------------------------------------------------ auto clicker

    def _busy(self):
        return self.engine.running or self.recorder is not None or self.player.playing

    def toggle(self):
        if self.engine.running:
            self.engine.stop()
        elif not self._busy():
            self.start()

    def start(self):
        s = self.s
        if s.position_mode == "points" and not s.points:
            self._go_to_tab(1)
            self.status.setText("Adicione pelo menos um ponto antes de iniciar.")
            return
        cfg = ClickConfig(
            interval_ms=max(1, s.interval_ms),
            jitter_ms=s.jitter_ms if s.jitter_enabled else 0,
            button=s.button,
            clicks=s.clicks,
            repeat_mode=s.repeat_mode,
            repeat_count=s.repeat_count,
            duration_s=s.duration_s,
            position_mode=s.position_mode,
            points=list(s.points),
            restore_cursor=s.restore_cursor,
            protect_hwnd=self._hwnd if s.protect_self else 0,
        )
        self._last_reason = None
        self.engine.start(cfg)
        self.orb.setRunning(True)
        self._set_busy_ui(True)
        self.tray_toggle.setText("Parar auto clicker")

    def _on_clicker_finished(self, reason):
        self._last_reason = reason
        self.orb.setRunning(False)
        self.tray_toggle.setText("Iniciar auto clicker")
        self._set_busy_ui(False)

    # ------------------------------------------------------------------- macro

    def _load_last_macro(self):
        try:
            return macro.load(settings_store.last_macro_path())[0]
        except ValueError:
            return []

    def toggle_record(self):
        if self.recorder is not None:
            self._stop_recording()
        elif not self._busy():
            self._start_recording()

    def _start_recording(self):
        self._go_to_tab(TAB_MACRO)
        recorder = macro.Recorder(self._hwnd, self.s.record_moves, self.s.record_keys)
        try:
            recorder.start()
        except OSError as exc:
            self._macro_reason = f"error:{exc}"
            self._refresh()
            return
        self.recorder = recorder
        self._macro_reason = None
        self.record_orb.setRunning(True)
        self._set_busy_ui(True)

    def _stop_recording(self):
        events = self.recorder.stop(drop_keys={winapi.VK_PAUSE, winapi.VK_SCROLL})
        self.recorder = None
        self.record_orb.setRunning(False)
        if events:
            self.macro_events = events
            self._macro_reason = "recorded"
            try:
                settings_store.data_dir().mkdir(parents=True, exist_ok=True)
                macro.save(settings_store.last_macro_path(), events)
            except OSError:
                pass
        else:
            self._macro_reason = "empty"
        self._set_busy_ui(False)

    def toggle_play(self):
        if self.player.playing:
            self.player.stop()
        elif not self._busy():
            if not self.macro_events:
                self._go_to_tab(TAB_MACRO)
                self._macro_reason = "empty"
                self._refresh()
                return
            self._macro_reason = None
            self.player.start(self.macro_events, self.s.macro_speed, self.s.macro_loop_count)
            # TinyTask convention: Pause or Scroll Lock aborts playback.
            winapi.register_hotkey(self._hwnd, HK_STOP_PAUSE, winapi.VK_PAUSE, 0)
            winapi.register_hotkey(self._hwnd, HK_STOP_SCROLL, winapi.VK_SCROLL, 0)
            self.play_orb.setRunning(True)
            self._set_busy_ui(True)

    def _on_macro_finished(self, reason):
        winapi.unregister_hotkey(self._hwnd, HK_STOP_PAUSE)
        winapi.unregister_hotkey(self._hwnd, HK_STOP_SCROLL)
        self._macro_reason = reason
        self.play_orb.setRunning(False)
        self._set_busy_ui(False)

    def _open_macro(self):
        path, _ = QFileDialog.getOpenFileName(self, "Abrir macro", "", MACRO_FILTER)
        if not path:
            return
        try:
            events, _speed, _loops = macro.load(path)
        except ValueError as exc:
            self._macro_reason = f"error:{exc}"
        else:
            self.macro_events = events
            self._macro_reason = f"opened:{Path(path).name}"
        self._refresh()

    def _save_macro(self):
        if not self.macro_events:
            self._macro_reason = "empty"
            self._refresh()
            return
        path, _ = QFileDialog.getSaveFileName(self, "Salvar macro", "minha-macro.kmacro", MACRO_FILTER)
        if not path:
            return
        if not path.lower().endswith(macro.FILE_SUFFIX):
            path += macro.FILE_SUFFIX
        try:
            macro.save(path, self.macro_events, self.s.macro_speed, self.s.macro_loop_count)
            self._macro_reason = f"saved:{Path(path).name}"
        except OSError as exc:
            self._macro_reason = f"error:{exc}"
        self._refresh()

    def _compile_macro(self):
        if not self.macro_events:
            self._macro_reason = "empty"
        elif not macro.can_compile():
            self._macro_reason = "error:Compilar .exe funciona a partir do Klicker.exe (versão compilada)."
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Compilar macro", "minha-macro.exe",
                                                  "Programas (*.exe)")
            if not path:
                return
            if not path.lower().endswith(".exe"):
                path += ".exe"
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                macro.compile_exe(path, self.macro_events, self.s.macro_speed, self.s.macro_loop_count)
                self._macro_reason = f"compiled:{Path(path).name}"
            except OSError as exc:
                self._macro_reason = f"error:{exc}"
            finally:
                QApplication.restoreOverrideCursor()
        self._refresh()

    # ------------------------------------------------------------------- drops

    def _farm_seconds(self):
        return (self.s.farm_hours * 60 + self.s.farm_minutes) * 60

    def _update_drops(self):
        s = self.s
        cfg = odds.DropConfig(
            chance=s.drop_chance,
            run_seconds=s.run_minutes * 60 + s.run_seconds,
            pity=s.pity_runs if s.pity_enabled else 0,
            pity_progress=s.pity_progress,
            items_per_drop=s.drop_items,
            luck=s.drop_luck,
        )
        r = odds.analyze(cfg, s.goal_items, self._farm_seconds())
        self._drop_report = r
        rows = self.result_rows
        if r.p <= 0:
            for name, value in rows.values():
                value.setText("—")
            self.result_note.setText("Informe a chance do drop para ver as contas.")
            return

        def put(key, value, name=None):
            rows[key][1].setText(value)
            if name is not None:
                rows[key][0].setText(name)

        put("chance", odds.format_chance(r.p))
        put("mean", self._runs_text(r.mean_runs))
        put("q50", self._runs_text(r.quantile_runs[0.5]))
        put("q90", self._runs_text(r.quantile_runs[0.9]))
        put("q99", self._runs_text(r.quantile_runs[0.99]))
        put("worst", f"garantido em {self._runs_text(r.worst_runs)}" if r.worst_runs is not None
            else "sem garantia (sem pity)")

        goal = r.goal_drops > 1
        for key in ("goal_mean", "goal_q90", "goal_worst"):
            for widget in rows[key]:
                widget.setVisible(goal)
        if goal:
            items = odds.format_number(r.goal_items)
            put("goal_mean", self._runs_text(r.goal_mean_runs), f"Média para {items} itens")
            put("goal_q90", "≈ " + self._runs_text(r.goal_quantile_runs[0.9]), "90% das vezes, até")
            put("goal_worst", self._runs_text(r.goal_worst_runs) if r.goal_worst_runs is not None
                else "sem garantia", f"Pior cenário p/ {items}")

        farm = r.farm_runs > 0
        for key in ("farm_items", "farm_any"):
            for widget in rows[key]:
                widget.setVisible(farm)
        if farm:
            farm_text = odds.format_time(self._farm_seconds())
            put("farm_items", f"~{odds.format_number(r.farm_expected_items, 1)} itens",
                f"Em {farm_text} ({odds.format_number(r.farm_runs)} fases)")
            put("farm_any", odds.format_percent(r.farm_chance_any), "Chance de vir ≥ 1 drop")

        if r.worst_runs is not None:
            note = (f"Com o pity, ninguém passa de {odds.format_number(r.worst_runs)} fases sem o drop. "
                    f"Depois de cada drop o pity zera: em média {odds.format_number(r.cycle_runs, 1)} "
                    "fases por drop.")
        else:
            note = (f"Sem pity não existe pior caso garantido: 1 em cada 1.000 jogadores leva mais de "
                    f"{self._runs_text(r.quantile_runs[0.999])}.")
        if s.drop_luck != 1:
            note += f" Sorte {odds.format_number(s.drop_luck, 2).rstrip('0').rstrip(',')}x já incluída."
        if r.run_seconds <= 0:
            note += " Informe o tempo de uma fase para ver os tempos."
        self.result_note.setText(note)

    def _runs_text(self, runs):
        r = self._drop_report
        if runs is None or runs == math.inf:
            return "sem garantia"
        whole = runs >= 10 or runs == int(runs)
        text = f"{odds.format_number(runs, 0 if whole else 1)} fase{'' if runs == 1 else 's'}"
        if r.run_seconds > 0:
            text += f" · {odds.format_time(r.seconds(runs))}"
        return text

    def _drop_stats(self):
        r = self._drop_report
        if r is None or r.p <= 0 or r.run_seconds <= 0:
            return [("—", "tempo médio"), ("—", "pior caso"), ("—", "itens no farm")]
        mean_caption = "tempo médio" if r.goal_drops == 1 else f"média p/ {odds.format_number(r.goal_items)}"
        if r.goal_worst_runs is not None:
            worst = (odds.format_time(r.seconds(r.goal_worst_runs)), "pior caso")
        else:
            worst = (odds.format_time(r.seconds(r.goal_quantile_runs[0.99])), "azar (99%)")
        farm = odds.format_time(self._farm_seconds())
        items = (odds.format_number(r.farm_expected_items, 1), f"itens em {farm}") if r.farm_runs else \
            (odds.format_time(r.seconds(r.quantile_runs[0.5])), "metade das vezes")
        return [(odds.format_time(r.seconds(r.goal_mean_runs)), mean_caption), worst, items]

    def _drop_status(self):
        r = self._drop_report
        if r is None or r.p <= 0:
            return "Informe a chance do drop para calcular"
        if r.run_seconds <= 0:
            return "Informe quanto tempo leva uma fase"
        if self._stopwatch_t0 is not None:
            return "Cronometrando… clique em Parar quando a fase terminar"
        if r.farm_runs:
            return (f"{odds.format_percent(r.farm_chance_any)} de chance de pegar pelo menos 1 em "
                    f"{odds.format_time(self._farm_seconds())} de farm")
        return f"Em média {odds.format_number(r.mean_runs, 1)} fases até o drop"

    def _toggle_stopwatch(self):
        if self._stopwatch_t0 is None:
            self._stopwatch_t0 = time.perf_counter()
            self._stopwatch_timer.start()
            self._tick_stopwatch()
            self._refresh()
            return
        total = round(time.perf_counter() - self._stopwatch_t0, 1)
        self._stopwatch_t0 = None
        self._stopwatch_timer.stop()
        minutes = int(total // 60)
        self._loading = True
        self.run_min_spin.setValue(min(minutes, self.run_min_spin.maximum()))
        self.run_sec_spin.setValue(round(total - minutes * 60, 1))
        self._loading = False
        self._tick_stopwatch()
        self._changed()

    def _tick_stopwatch(self):
        if self._stopwatch_t0 is None:
            self.stopwatch_btn.setText("⏱  Cronometrar uma fase")
        else:
            elapsed = time.perf_counter() - self._stopwatch_t0
            self.stopwatch_btn.setText(f"■  Parar  ·  {_format_duration(elapsed)}.{int(elapsed * 10) % 10}")

    # ------------------------------------------------------------- status/stats

    def _set_busy_ui(self, busy):
        self.stack.setEnabled(not busy)
        self.tabs.setEnabled(not busy)
        if busy:
            self._stats_timer.start()
        else:
            self._stats_timer.stop()
        self._refresh()

    def _go_to_tab(self, index):
        self.tabs.setIndex(index)
        self._tab_changed(index)

    def _tab_changed(self, index):
        self.stack.setCurrentIndex(index)
        self._refresh()

    def _macro_mode(self):
        if self.engine.running:
            return False
        return self.recorder is not None or self.player.playing or self.tabs.index() == TAB_MACRO

    def _refresh(self):
        macro_mode = self._macro_mode()
        self.orb_stack.setCurrentIndex(1 if macro_mode else 0)
        self.record_orb.setEnabled(not self.engine.running and not self.player.playing)
        self.play_orb.setEnabled(not self.engine.running and self.recorder is None)
        self.record_caption.setText(f"Gravar\n{self._hotkey_text(HK_RECORD)}")
        self.play_caption.setText(f"Reproduzir\n{self._hotkey_text(HK_PLAY)}")
        drop_mode = not macro_mode and not self._busy() and self.tabs.index() == TAB_DROPS
        if macro_mode:
            values, text = self._macro_stats(), self._macro_status()
        elif drop_mode:
            values, text = self._drop_stats(), self._drop_status()
        else:
            values, text = self._clicker_stats(), self._clicker_status()
        for (value_label, caption_label), (value, caption) in zip(self.stats, values):
            value_label.setText(value)
            caption_label.setText(caption)
        if self._hotkey_failures and not self._busy():
            text = (f"Atalho em uso por outro programa: {', '.join(self._hotkey_failures)}. "
                    "Troque em Ajustes.")
        self.status.setText(text)
        self.tray.setToolTip(f"Klicker — {text}"[:120])

    def _clicker_stats(self):
        clicks = self.engine.clicks
        elapsed = self.engine.elapsed()
        rate = clicks / elapsed if elapsed > 0.25 else 0.0
        return [(f"{clicks:,}".replace(",", "."), "cliques"),
                (_format_duration(elapsed), "tempo"),
                (f"{rate:.1f}".replace(".", ","), "cliques/s")]

    def _macro_stats(self):
        if self.recorder is not None:
            return [(str(self.recorder.event_count()), "eventos"),
                    (_format_duration(self.recorder.elapsed()), "gravando"),
                    ("REC", "estado")]
        total = macro.duration_ms(self.macro_events) / 1000
        loops = self.s.macro_loop_count
        if self.player.playing:
            loop_text = f"{self.player.loop}/{loops or '∞'}"
            return [(str(len(self.macro_events)), "eventos"),
                    (_format_duration(self.player.loop_elapsed()), f"de {_format_duration(total)}"),
                    (loop_text, "repetição")]
        return [(str(len(self.macro_events)), "eventos"),
                (_format_duration(total), "duração"),
                (f"{self.s.macro_speed}x · {loops or '∞'}", "velocidade · vezes")]

    def _clicker_status(self):
        key = self._hotkey_text(HK_CLICKER)
        reason = self._last_reason
        if self.engine.running:
            return f"Clicando…  {key} para parar"
        if reason == "done":
            return f"Concluído.  {key} para repetir"
        if reason == "stopped":
            return f"Parado.  {key} para retomar"
        if reason and reason.startswith("error:"):
            return "Erro: " + reason[6:]
        return f"Pressione {key} ou o botão para começar"

    def _macro_status(self):
        rec_key = self._hotkey_text(HK_RECORD)
        play_key = self._hotkey_text(HK_PLAY)
        reason = self._macro_reason or ""
        if self.recorder is not None:
            return f"● Gravando — {rec_key} para parar"
        if self.player.playing:
            return f"Reproduzindo — {play_key}, Pause ou Scroll Lock para parar"
        if reason.startswith("error:"):
            return "Erro: " + reason[6:]
        if not self.macro_events:
            return "Nada gravado — pressione o botão vermelho para gravar"
        messages = {
            "recorded": f"Gravação pronta!  {play_key} para reproduzir",
            "done": f"Reprodução concluída.  {play_key} para repetir",
            "stopped": f"Reprodução interrompida.  {play_key} para recomeçar",
            "empty": "Nada foi gravado — nenhum clique ou tecla capturado",
        }
        if reason in messages:
            return messages[reason]
        for prefix, text in (("opened:", "Macro aberta: "), ("saved:", "Salvo em "),
                             ("compiled:", "Compilado com sucesso: ")):
            if reason.startswith(prefix):
                return text + reason[len(prefix):]
        return f"Macro pronta  ·  {play_key} para reproduzir"

    # ----------------------------------------------------------------- hotkeys

    def _register_hotkeys(self):
        self._unregister_hotkeys()
        names = {HK_CLICKER: "auto clicker", HK_RECORD: "gravar", HK_PLAY: "reproduzir"}
        self._hotkey_failures = [names[hk_id] for hk_id in names
                                 if not winapi.register_hotkey(self._hwnd, hk_id, *self._hotkey(hk_id))]
        self._refresh()

    def _unregister_hotkeys(self):
        for hk_id in (HK_CLICKER, HK_RECORD, HK_PLAY):
            winapi.unregister_hotkey(self._hwnd, hk_id)

    def _hotkey_captured(self, hk_id, accepted):
        if accepted:
            button = self.hotkey_buttons[hk_id]
            s = self.s
            if hk_id == HK_CLICKER:
                s.hotkey_vk, s.hotkey_mods = button.vk, button.mods
            elif hk_id == HK_RECORD:
                s.record_vk, s.record_mods = button.vk, button.mods
            else:
                s.play_vk, s.play_mods = button.vk, button.mods
            self._save_timer.start()
        self._register_hotkeys()

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = winapi.wt.MSG.from_address(int(message))
            if msg.message == winapi.WM_HOTKEY:
                handler = {
                    HK_CLICKER: self.toggle,
                    HK_RECORD: self.toggle_record,
                    HK_PLAY: self.toggle_play,
                    HK_STOP_PAUSE: self.player.stop,
                    HK_STOP_SCROLL: self.player.stop,
                }.get(msg.wParam)
                if handler:
                    handler()
                    return True, 0
        return False, 0

    # ------------------------------------------------------------------ chrome

    def _apply_chrome(self):
        if not self._hwnd:
            return
        winapi.set_topmost(self._hwnd, self.s.always_on_top)
        tint = theme.palette().acrylic_tint
        rgba = (tint.red(), tint.green(), tint.blue(), tint.alpha())
        self._acrylic_on = winapi.set_acrylic(self._hwnd, self.s.acrylic, rgba) and self.s.acrylic
        self.update()

    def _apply_theme(self):
        theme.set_mode(self.s.theme)
        QApplication.instance().setStyleSheet(theme.stylesheet())
        self._apply_chrome()
        self._sync_dependents()
        for child in self.findChildren(QWidget):
            child.update()

    def _choose_background(self):
        path, _ = QFileDialog.getOpenFileName(self, "Escolher imagem de fundo", "",
                                              "Imagens (*.png *.jpg *.jpeg *.bmp *.webp *.gif)")
        if path:
            self.s.background_image = path
            self._load_background()
            self._sync_dependents()
            self._save_timer.start()

    def _clear_background(self):
        self.s.background_image = ""
        self._load_background()
        self._sync_dependents()
        self._save_timer.start()

    def _load_background(self):
        path = self.s.background_image
        pixmap = QPixmap(path) if path and Path(path).is_file() else None
        self._bg_pixmap = pixmap if pixmap is not None and not pixmap.isNull() else None
        self.update()

    def _update_scene_timer(self):
        if theme.palette().scene and self._bg_pixmap is None:
            if not self._scene_timer.isActive():
                self._scene_clock = time.perf_counter()
                self._scene_timer.start()
        else:
            self._scene_timer.stop()

    def _tick_scene(self):
        now = time.perf_counter()
        dt = min(now - self._scene_clock, 0.1)
        self._scene_clock = now
        if self.isVisible() and not self.isMinimized():
            self._scene.tick(dt, self.width(), self.height())
            self.update()

    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._hwnd:
            self._hwnd = int(self.winId())
            winapi.set_round_corners(self._hwnd)
            self._apply_chrome()
            self._register_hotkeys()

    def closeEvent(self, event):
        self.engine.stop()
        self.player.stop()
        if self.recorder is not None:
            self._stop_recording()
        self.engine.join(1.0)
        self.player.join(1.0)
        if self._hwnd:
            self._unregister_hotkeys()
        self._save_timer.stop()
        self._save()
        self.tray.hide()
        super().closeEvent(event)
        QApplication.instance().quit()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pal = theme.palette()
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, WINDOW_RADIUS, WINDOW_RADIUS)
        p.setClipPath(path)

        if self._bg_pixmap is not None:
            paint_cover_image(p, rect, self._bg_pixmap)
            veil = QColor(pal.window_tint)
            veil.setAlpha(min(255, veil.alpha() + 20))
            p.fillRect(rect, veil)
        elif pal.scene:
            self._scene.paint(p, rect, show_petals=self.s.petals)
        else:
            p.fillRect(rect, pal.window_tint if self._acrylic_on else pal.window_solid)
            # Colour pooling under the glass gives the panes something to refract.
            w, h = rect.width(), rect.height()
            for (cx, cy, r), color in (((w * 0.12, 150, 230), pal.blob1),
                                       ((w * 0.98, h * 0.45, 250), pal.blob2),
                                       ((w * 0.30, h * 1.02, 280), pal.blob3)):
                grad = QRadialGradient(QPointF(cx, cy), r)
                grad.setColorAt(0, color)
                grad.setColorAt(1, CLEAR)
                p.fillRect(rect, QBrush(grad))
        p.setClipping(False)
        p.setPen(QPen(pal.window_border, 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    def save_screenshot(self, path):
        """Capture the window as it appears on screen (blur included)."""
        geo = self.frameGeometry()
        shot = self.screen().grabWindow(0, geo.x(), geo.y(), geo.width(), geo.height())
        return shot.save(path)

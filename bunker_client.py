"""
╔══════════════════════════════════════════════════════╗
║   БУНКЕР — КЛИЕНТ v2.0                               ║
║   Установка: pip install PyQt6 websockets            ║
╚══════════════════════════════════════════════════════╝
"""

import sys, json, asyncio, threading, os, random
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QSpinBox, QScrollArea, QFrame,
    QGridLayout, QDialog, QProgressBar, QTextEdit, QMessageBox,
    QStackedWidget, QSizePolicy, QGraphicsDropShadowEffect,
    QListWidget, QListWidgetItem, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPen, QPainter

try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False

SERVER_URL = os.environ.get("BUNKER_SERVER", "ws://localhost:8765")

# ─────────────────────────────────────────
#  ПАЛИТРА: РЖАВЧИНА / МЕТАЛЛ
# ─────────────────────────────────────────
C_BG       = "#0f0a06"   # очень тёмный коричневый
C_SURFACE  = "#1a1108"   # поверхность
C_BORDER   = "#4a2e0a"   # бронзовая граница
C_ACCENT   = "#c87020"   # оранжевый акцент (ржавчина)
C_ACCENT2  = "#e8a030"   # золотой акцент
C_TEXT     = "#d4a060"   # тёплый текст
C_TEXT_DIM = "#6a4020"   # приглушённый
C_DANGER   = "#cc2a10"   # красная опасность
C_SUCCESS  = "#507030"   # тёмно-зелёный (выживание)
C_ACTIVE   = "#e8b050"   # активный игрок

STYLE = f"""
QMainWindow, QDialog, QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-family: 'Courier New', 'Consolas', monospace;
    font-size: 13px;
}}
QLabel {{
    color: {C_TEXT};
    background: transparent;
}}
QPushButton {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #2a1a08, stop:1 #1a0e04);
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 2px;
    padding: 8px 18px;
    font-size: 12px;
    font-weight: bold;
    font-family: 'Courier New', monospace;
    letter-spacing: 2px;
}}
QPushButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #3a2510, stop:1 #251508);
    border-color: {C_ACCENT};
    color: {C_ACCENT2};
}}
QPushButton:pressed {{
    background: #0f0803;
    border-color: {C_ACCENT2};
}}
QPushButton:disabled {{
    background: #120c05;
    color: {C_TEXT_DIM};
    border-color: #2a1a08;
}}
QPushButton#dangerBtn {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #2a0808, stop:1 #1a0505);
    color: #e04030;
    border-color: #6a1a10;
}}
QPushButton#dangerBtn:hover {{
    background: #3a0a08;
    color: #ff5040;
    border-color: {C_DANGER};
}}
QPushButton#accentBtn {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #3a2008, stop:1 #281505);
    color: {C_ACCENT2};
    border-color: #6a4010;
}}
QPushButton#accentBtn:hover {{
    background: #4a2a0a;
    color: #ffd060;
    border-color: {C_ACCENT2};
}}
QPushButton#successBtn {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #182510, stop:1 #0f1808);
    color: #80a040;
    border-color: #305020;
}}
QPushButton#successBtn:hover {{
    background: #223010;
    color: #a0c060;
    border-color: #507030;
}}
QLineEdit, QSpinBox, QTextEdit {{
    background-color: #14090402;
    border: 1px solid {C_BORDER};
    border-radius: 2px;
    padding: 8px 12px;
    color: {C_TEXT};
    font-size: 13px;
    font-family: 'Courier New', monospace;
    selection-background-color: #3a2010;
    background: #180f05;
}}
QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {{
    border-color: {C_ACCENT};
    background: #201408;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: #2a1808;
    border: none;
    width: 20px;
}}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: #140c05;
    width: 6px;
    border-radius: 0px;
}}
QScrollBar::handle:vertical {{
    background: {C_BORDER};
    border-radius: 0px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {C_ACCENT}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QProgressBar {{
    background: #140c05;
    border: 1px solid {C_BORDER};
    border-radius: 2px;
    text-align: center;
    color: {C_TEXT};
    font-weight: bold;
    font-size: 12px;
    font-family: 'Courier New', monospace;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #3a1808, stop:1 {C_ACCENT});
    border-radius: 1px;
}}
QFrame#card {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #1e1208, stop:1 #140c05);
    border: 1px solid {C_BORDER};
    border-radius: 3px;
}}
QFrame#active_card {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #2e1e08, stop:1 #1e1005);
    border: 2px solid {C_ACTIVE};
    border-radius: 3px;
}}
QFrame#glow {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #251808, stop:1 #1a1005);
    border: 1px solid {C_ACCENT};
    border-radius: 3px;
}}
QFrame#danger_frame {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #1e0808, stop:1 #140505);
    border: 1px solid #6a1a10;
    border-radius: 3px;
}}
QFrame#eliminated_frame {{
    background: #100a05;
    border: 1px solid #2a1a08;
    border-radius: 3px;
    opacity: 0.5;
}}
QFrame#bunker_bar {{
    background: #180f05;
    border: 1px solid {C_BORDER};
    border-radius: 2px;
}}
QListWidget {{
    background: #180f05;
    border: 1px solid {C_BORDER};
    border-radius: 2px;
    outline: none;
}}
QListWidget::item {{
    padding: 6px 12px;
    border-bottom: 1px solid #2a1808;
    color: {C_TEXT};
    font-family: 'Courier New', monospace;
}}
QListWidget::item:selected {{ background: #2a1808; color: {C_ACCENT2}; }}
QListWidget::item:hover {{ background: #201005; }}
QToolTip {{
    background: {C_SURFACE};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    font-family: 'Courier New', monospace;
}}
"""

FIELD_META = [
    ("profession", "⚙️", "Профессия"),
    ("health",     "🩺", "Здоровье"),
    ("hobby",      "🎯", "Хобби"),
    ("baggage",    "🎒", "Багаж"),
    ("bio",        "📋", "Биография"),
    ("fact1",      "📌", "Факт 1"),
    ("fact2",      "📌", "Факт 2"),
    ("phobia",     "⚠️", "Фобия"),
    ("skill",      "🔧", "Навык"),
]
SECRET_FIELD = ("secret", "🔒", "Секрет")


def lbl(text, size=13, bold=False, color=None, align=Qt.AlignmentFlag.AlignLeft):
    if color is None: color = C_TEXT
    w = QLabel(text)
    f = QFont("Courier New"); f.setPointSize(size); f.setBold(bold)
    w.setFont(f)
    w.setStyleSheet(f"color: {color}; background: transparent;")
    w.setAlignment(align)
    return w

def sep():
    l = QFrame(); l.setFrameShape(QFrame.Shape.HLine)
    l.setStyleSheet(f"background: {C_BORDER}; max-height: 1px; margin: 4px 0;")
    return l

def rust_btn(text, glow_color=None):
    btn = QPushButton(text)
    if glow_color:
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(0); sh.setColor(QColor(glow_color)); sh.setOffset(0,0)
        btn.setGraphicsEffect(sh); btn._shadow = sh
        def on_enter(e, b=btn): b._shadow.setBlurRadius(14)
        def on_leave(e, b=btn): b._shadow.setBlurRadius(0)
        btn.enterEvent = on_enter; btn.leaveEvent = on_leave
    return btn


# ─────────────────────────────────────────
#  WEBSOCKET WORKER
# ─────────────────────────────────────────

class WSWorker(QObject):
    message_received = pyqtSignal(dict)
    connected_signal = pyqtSignal()
    disconnected_signal = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self._ws = None
        self._send_queue = []
        self._loop = None

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect())

    async def _connect(self):
        try:
            async with websockets.connect(self.url, ping_interval=20) as ws:
                self._ws = ws
                self.connected_signal.emit()
                while self._send_queue:
                    await ws.send(self._send_queue.pop(0))
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                        self.message_received.emit(data)
                    except Exception:
                        pass
        except Exception as e:
            self.disconnected_signal.emit(str(e))
        finally:
            self._ws = None

    def send(self, data):
        raw = json.dumps(data, ensure_ascii=False)
        if self._ws and self._loop:
            asyncio.run_coroutine_threadsafe(self._ws.send(raw), self._loop)
        else:
            self._send_queue.append(raw)


# ─────────────────────────────────────────
#  ВСПЛЫВАЮЩИЙ СЮЖЕТ
# ─────────────────────────────────────────

class ScenarioDialog(QDialog):
    def __init__(self, scenario, bunker, catastrophe, special, parent=None):
        super().__init__(parent)
        self.setWindowTitle("☢ СВОДКА")
        self.setMinimumSize(650, 480)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 24, 28, 24)

        layout.addWidget(lbl("⚠  СВОДКА СИТУАЦИИ", 18, True, C_ACCENT, Qt.AlignmentFlag.AlignCenter))

        frame = QFrame(); frame.setObjectName("danger_frame")
        fl = QVBoxLayout(frame); fl.setSpacing(10)
        cat_l = lbl(catastrophe, 13, True, "#e05030", Qt.AlignmentFlag.AlignCenter)
        cat_l.setWordWrap(True); fl.addWidget(cat_l)
        layout.addWidget(frame)

        if special:
            sp_l = lbl(special, 12, False, C_ACCENT2, Qt.AlignmentFlag.AlignCenter)
            sp_l.setWordWrap(True); layout.addWidget(sp_l)

        layout.addWidget(sep())
        layout.addWidget(lbl("// СЦЕНАРИЙ //", 11, True, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        sw = QWidget(); sw.setStyleSheet("background:transparent;")
        sl = QVBoxLayout(sw)
        sc_l = lbl(scenario, 11, False, C_TEXT)
        sc_l.setWordWrap(True); sl.addWidget(sc_l)
        scroll.setWidget(sw); layout.addWidget(scroll, 1)

        layout.addWidget(sep())
        layout.addWidget(lbl("// БУНКЕР //", 11, True, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))
        bunk_l = lbl(bunker, 11, False, C_TEXT, Qt.AlignmentFlag.AlignCenter)
        bunk_l.setWordWrap(True); layout.addWidget(bunk_l)

        btn = rust_btn("[ ЗАКРЫТЬ И НАЧАТЬ ИГРУ ]", C_ACCENT)
        btn.setObjectName("accentBtn"); btn.setFixedHeight(42)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


# ─────────────────────────────────────────
#  ПОЛОСА БУНКЕРА (всегда видна)
# ─────────────────────────────────────────

class BunkerBar(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("bunker_bar")
        self.setFixedHeight(38)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(12, 4, 12, 4)
        self._layout.setSpacing(20)
        self._labels = {}
        for key in ["catastrophe", "bunker", "special", "capacity"]:
            l = lbl("", 10, False, C_TEXT_DIM)
            l.setWordWrap(False)
            self._layout.addWidget(l)
            self._labels[key] = l
        self._layout.addStretch()

    def update_state(self, state):
        cat = state.get("catastrophe", "")[:50]
        bunker = state.get("bunker", "")[:50]
        special = state.get("special", "")[:60]
        cap = state.get("bunker_capacity", 0)
        active = len(state.get("active_players", []))
        rnd = state.get("round", 1)
        self._labels["catastrophe"].setText(f"☢ {cat}")
        self._labels["bunker"].setText(f"🏗 {bunker[:40]}")
        self._labels["special"].setText(f"{special}" if special else "")
        self._labels["capacity"].setText(f"Р.{rnd} | Актив: {active} | Мест: {cap}")


# ─────────────────────────────────────────
#  ВИДЖЕТ КАРТОЧКИ ИГРОКА
# ─────────────────────────────────────────

class PlayerCardWidget(QFrame):
    reveal_field = pyqtSignal(str)
    end_turn = pyqtSignal()
    reveal_secret = pyqtSignal()
    get_boost_self = pyqtSignal()
    get_boost_group = pyqtSignal()
    activate_boost_self = pyqtSignal()
    activate_boost_group = pyqtSignal()

    def __init__(self, card, is_self=False, is_my_turn=False,
                 discussion_phase=0, first_phase_done=False,
                 compact=False):
        super().__init__()
        self.card = card
        self.is_self = is_self
        self.is_my_turn = is_my_turn
        self.discussion_phase = discussion_phase
        self.first_phase_done = first_phase_done
        self.compact = compact
        eliminated = card.get("eliminated", False)
        active_frame = is_my_turn and is_self and not eliminated
        if eliminated:
            self.setObjectName("eliminated_frame")
        elif active_frame:
            self.setObjectName("active_card")
        else:
            self.setObjectName("card")
        self._build(eliminated)

    def _build(self, eliminated):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Header
        hdr = QHBoxLayout()
        name_color = C_TEXT_DIM if eliminated else (C_ACTIVE if self.is_my_turn and self.is_self else C_TEXT)
        name_l = lbl(self.card.get("name","?"), 13, True, name_color)
        hdr.addWidget(name_l)
        if eliminated:
            tag = QLabel("ИЗГНАН")
            tag.setStyleSheet(f"color:{C_DANGER};background:#200808;border-radius:3px;padding:1px 6px;font-size:10px;font-weight:bold;")
            hdr.addWidget(tag)
        if self.is_self:
            you = QLabel("ВЫ")
            you.setStyleSheet(f"color:#6080a0;background:#101820;border-radius:3px;padding:1px 6px;font-size:10px;font-weight:bold;")
            hdr.addWidget(you)
        if self.is_my_turn and self.is_self and not eliminated:
            turn_tag = QLabel("ВАШ ХОД")
            turn_tag.setStyleSheet(f"color:{C_ACTIVE};background:#201808;border-radius:3px;padding:1px 6px;font-size:10px;font-weight:bold;")
            hdr.addWidget(turn_tag)
        hdr.addStretch()
        layout.addLayout(hdr)
        layout.addWidget(sep())

        # Если не свой и не изгнан — рубашка
        if not self.is_self and not eliminated:
            sleeve = lbl("[ ДОСЬЕ ЗАСЕКРЕЧЕНО ]", 11, True, C_TEXT_DIM,
                         Qt.AlignmentFlag.AlignCenter)
            sleeve.setContentsMargins(0, 20, 0, 20)
            layout.addWidget(sleeve)
            # Показываем раскрытые поля если есть
            for field, icon, label in FIELD_META:
                val = self.card.get(field)
                revealed = self.card.get("revealed", {}).get(field, False)
                if revealed and val:
                    row = QHBoxLayout(); row.setSpacing(6)
                    row.addWidget(lbl(icon, 11)); 
                    nm = lbl(f"{label}:", 9, False, C_TEXT_DIM); nm.setFixedWidth(80)
                    row.addWidget(nm)
                    vl = lbl(val, 10, False, C_TEXT); vl.setWordWrap(True)
                    row.addWidget(vl, 1)
                    layout.addLayout(row)
            # Секрет если раскрыт
            if self.card.get("secret_revealed") and self.card.get("secret"):
                row = QHBoxLayout(); row.setSpacing(6)
                row.addWidget(lbl("🔒", 11))
                nm = lbl("Секрет:", 9, False, C_TEXT_DIM); nm.setFixedWidth(80)
                row.addWidget(nm)
                vl = lbl(self.card.get("secret",""), 10, True, C_ACCENT); vl.setWordWrap(True)
                row.addWidget(vl, 1)
                layout.addLayout(row)
            return

        # Своя карточка или изгнанный — все поля
        fields = FIELD_META[:]
        if eliminated or self.card.get("secret_revealed"):
            fields.append(SECRET_FIELD)

        for field, icon, label in fields:
            row = QHBoxLayout(); row.setSpacing(5)
            row.addWidget(lbl(icon, 11))
            nm = lbl(f"{label}:", 9, False, C_TEXT_DIM); nm.setFixedWidth(82)
            row.addWidget(nm)

            val = self.card.get(field)
            revealed = self.card.get("revealed", {}).get(field, False) if field != "secret" else False

            if self.is_self and not eliminated:
                val_text = val or "???"
                color = C_TEXT if revealed or field == "secret" else C_ACCENT2
                vl = lbl(val_text, 10, False, color); vl.setWordWrap(True)
                row.addWidget(vl, 1)

                # Кнопка раскрыть — только в свой ход, не раскрыто, не секрет
                if (self.is_my_turn and not revealed and field != "secret"
                        and not self.card.get("eliminated")):
                    # В фазе 0 только profession
                    can_reveal = True
                    if self.discussion_phase == 0 and field != "profession":
                        can_reveal = False
                    if can_reveal:
                        rb = QPushButton("[ РАСКРЫТЬ ]")
                        rb.setFixedSize(100, 22)
                        rb.setStyleSheet(
                            f"QPushButton{{font-size:9px;padding:1px 4px;"
                            f"background:#201005;border:1px solid {C_BORDER};"
                            f"border-radius:2px;color:{C_TEXT_DIM};"
                            f"font-family:'Courier New',monospace;}}"
                            f"QPushButton:hover{{background:#301808;color:{C_ACCENT};"
                            f"border-color:{C_ACCENT};}}")
                        rb.clicked.connect(lambda _, f=field: self.reveal_field.emit(f))
                        row.addWidget(rb)
                elif revealed:
                    ok = QLabel("✓")
                    ok.setStyleSheet(f"color:{C_SUCCESS};font-size:11px;font-weight:bold;background:transparent;")
                    row.addWidget(ok)
            else:
                # Изгнанный — видно всё
                vl = lbl(val or "—", 10, False, C_TEXT_DIM if eliminated else C_TEXT)
                vl.setWordWrap(True)
                row.addWidget(vl, 1)

            layout.addLayout(row)

        # Секрет — только свой, не изгнан, показываем всегда себе
        if self.is_self and not eliminated:
            row = QHBoxLayout(); row.setSpacing(5)
            row.addWidget(lbl("🔒", 11))
            nm = lbl("Секрет:", 9, False, C_TEXT_DIM); nm.setFixedWidth(82)
            row.addWidget(nm)
            secret_val = self.card.get("secret", "???")
            vl = lbl(secret_val, 10, True, C_ACCENT); vl.setWordWrap(True)
            row.addWidget(vl, 1)
            # Кнопка раскрыть секрет — только в свой ход, не в фазе 0
            if self.is_my_turn and not self.card.get("secret_revealed") and self.discussion_phase > 0:
                rb = QPushButton("[ РАСКРЫТЬ ВСЕМ ]")
                rb.setFixedSize(130, 22)
                rb.setStyleSheet(
                    f"QPushButton{{font-size:9px;padding:1px 4px;"
                    f"background:#201005;border:1px solid #6a3010;"
                    f"border-radius:2px;color:{C_ACCENT};"
                    f"font-family:'Courier New',monospace;}}"
                    f"QPushButton:hover{{background:#301008;color:#ffa040;"
                    f"border-color:{C_ACCENT2};}}")
                rb.clicked.connect(self.reveal_secret.emit)
                row.addWidget(rb)
            layout.addLayout(row)

        # ── Бусты (только своя карточка) ──────────
        if self.is_self and not eliminated:
            layout.addWidget(sep())
            boost_row = QHBoxLayout(); boost_row.setSpacing(8)

            boost_self  = self.card.get("boost_self")
            boost_group = self.card.get("boost_group")
            bs_used     = self.card.get("boost_self_used", False)
            bg_used     = self.card.get("boost_group_used", False)

            # Личный буст
            if boost_self is None:
                btn = QPushButton("[ 🎲 Личный буст ]")
                btn.setStyleSheet(f"font-size:10px;background:#1a1005;border:1px solid {C_BORDER};color:{C_TEXT_DIM};font-family:'Courier New',monospace;")
                btn.clicked.connect(self.get_boost_self.emit)
                boost_row.addWidget(btn)
            elif not bs_used:
                btn = QPushButton(f"[ ✨ {boost_self['name']} ]")
                btn.setObjectName("accentBtn")
                btn.setToolTip(boost_self["desc"])
                btn.setStyleSheet(f"font-size:10px;")
                if self.is_my_turn:
                    btn.clicked.connect(self.activate_boost_self.emit)
                else:
                    btn.setEnabled(False)
                boost_row.addWidget(btn)
            else:
                used_l = lbl(f"✓ {boost_self['name']}", 9, False, C_TEXT_DIM)
                boost_row.addWidget(used_l)

            # Групповой буст
            if boost_group is None:
                btn2 = QPushButton("[ 🎲 Групповой буст ]")
                btn2.setStyleSheet(f"font-size:10px;background:#1a1005;border:1px solid {C_BORDER};color:{C_TEXT_DIM};font-family:'Courier New',monospace;")
                btn2.clicked.connect(self.get_boost_group.emit)
                boost_row.addWidget(btn2)
            elif not bg_used:
                btn2 = QPushButton(f"[ 💥 {boost_group['name']} ]")
                btn2.setObjectName("dangerBtn")
                btn2.setToolTip(boost_group["desc"])
                btn2.setStyleSheet(f"font-size:10px;")
                if self.is_my_turn:
                    btn2.clicked.connect(self.activate_boost_group.emit)
                else:
                    btn2.setEnabled(False)
                boost_row.addWidget(btn2)
            else:
                used_l2 = lbl(f"✓ {boost_group['name']}", 9, False, C_TEXT_DIM)
                boost_row.addWidget(used_l2)

            layout.addLayout(boost_row)

            # Кнопки хода
            if self.is_my_turn:
                layout.addWidget(sep())
                turn_row = QHBoxLayout()
                end_btn = rust_btn("[ ЗАВЕРШИТЬ ХОД → ]", C_ACCENT)
                end_btn.setObjectName("accentBtn"); end_btn.setFixedHeight(32)
                end_btn.clicked.connect(self.end_turn.emit)
                turn_row.addStretch(); turn_row.addWidget(end_btn)
                layout.addLayout(turn_row)


# ─────────────────────────────────────────
#  УВЕДОМЛЕНИЕ О БУСТЕ
# ─────────────────────────────────────────

class BoostNotifyDialog(QDialog):
    def __init__(self, activator, boost_name, boost_desc, boost_type, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ БУСТ АКТИВИРОВАН")
        self.setMinimumSize(420, 280)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setSpacing(16); layout.setContentsMargins(28, 24, 28, 24)
        t = "💥 ГРУППОВОЙ БУСТ" if boost_type == "group" else "✨ ЛИЧНЫЙ БУСТ"
        layout.addWidget(lbl(t, 14, True, C_ACCENT, Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(lbl(f"Активировал: {activator}", 11, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))
        frame = QFrame(); frame.setObjectName("glow")
        fl = QVBoxLayout(frame)
        fl.addWidget(lbl(f"[ {boost_name} ]", 16, True, C_ACCENT2, Qt.AlignmentFlag.AlignCenter))
        desc_l = lbl(boost_desc, 11, False, C_TEXT, Qt.AlignmentFlag.AlignCenter)
        desc_l.setWordWrap(True); fl.addWidget(desc_l)
        layout.addWidget(frame, 1)
        btn = rust_btn("[ ОК ]", C_ACCENT)
        btn.setObjectName("accentBtn"); btn.setFixedHeight(36)
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)


# ─────────────────────────────────────────
#  ЭКРАН: СТАРТОВЫЙ
# ─────────────────────────────────────────

class StartScreen(QWidget):
    do_create = pyqtSignal(str, int)
    do_join   = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)

        # Title
        tw = QVBoxLayout()
        tw.setContentsMargins(30, 50, 30, 30); tw.setSpacing(8)
        t = lbl("⚙  БУНКЕР", 44, True, C_ACCENT, Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(f"color:{C_ACCENT};background:transparent;letter-spacing:12px;font-family:'Courier New',monospace;")
        tw.addWidget(t)
        sub = lbl("// СИСТЕМА РАСПРЕДЕЛЕНИЯ ВЫЖИВШИХ //", 11, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color:{C_TEXT_DIM};background:transparent;letter-spacing:3px;font-family:'Courier New',monospace;")
        tw.addWidget(sub)
        root.addLayout(tw)

        # Blocks
        blocks = QHBoxLayout()
        blocks.setContentsMargins(40, 0, 40, 40); blocks.setSpacing(30)

        # LEFT: Create
        left = QFrame(); left.setObjectName("glow")
        ll = QVBoxLayout(left); ll.setContentsMargins(28, 24, 28, 24); ll.setSpacing(14)
        ll.addWidget(lbl("⚙", 28, False, C_ACCENT, Qt.AlignmentFlag.AlignCenter))
        ll.addWidget(lbl("[ СОЗДАТЬ ЛОББИ ]", 15, True, C_ACCENT2, Qt.AlignmentFlag.AlignCenter))
        ll.addWidget(lbl("ВЫ — ВЕДУЩИЙ\nИГРА ГЕНЕРИРУЕТ 3-ЗНАЧНЫЙ КОД", 10, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))
        ll.addWidget(sep())
        ll.addWidget(lbl("ИМЯ ВЕДУЩЕГО:", 10, True, C_TEXT_DIM))
        self.host_name = QLineEdit("Ведущий"); ll.addWidget(self.host_name)
        ll.addWidget(lbl("МЕСТ В БУНКЕРЕ:", 10, True, C_TEXT_DIM))
        cap_row = QHBoxLayout()
        self.cap_spin = QSpinBox(); self.cap_spin.setRange(1, 15); self.cap_spin.setValue(3)
        cap_row.addWidget(self.cap_spin)
        cap_row.addWidget(lbl("ЧЕЛ.", 10, False, C_TEXT_DIM)); cap_row.addStretch()
        ll.addLayout(cap_row); ll.addStretch()
        cb = rust_btn("[ ⚙ СОЗДАТЬ ]", C_ACCENT); cb.setObjectName("accentBtn"); cb.setFixedHeight(46)
        cb.clicked.connect(self._do_create); ll.addWidget(cb)
        blocks.addWidget(left, 1)

        # RIGHT: Join
        right = QFrame(); right.setObjectName("card")
        rl = QVBoxLayout(right); rl.setContentsMargins(28, 24, 28, 24); rl.setSpacing(14)
        rl.addWidget(lbl("🔑", 28, False, C_TEXT, Qt.AlignmentFlag.AlignCenter))
        rl.addWidget(lbl("[ ВОЙТИ ПО КОДУ ]", 15, True, C_TEXT, Qt.AlignmentFlag.AlignCenter))
        rl.addWidget(lbl("ВВЕДИТЕ КОД ОТ ВЕДУЩЕГО\nДОСТУП К ТЕРМИНАЛУ БУНКЕРА", 10, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))
        rl.addWidget(sep())
        rl.addWidget(lbl("ПОЗЫВНОЙ:", 10, True, C_TEXT_DIM))
        self.player_name = QLineEdit(); self.player_name.setPlaceholderText("введите имя")
        rl.addWidget(self.player_name)
        rl.addWidget(lbl("КОД ДОСТУПА:", 10, True, C_TEXT_DIM))
        self.code_input = QLineEdit(); self.code_input.setPlaceholderText("A1B"); self.code_input.setMaxLength(3)
        self.code_input.setStyleSheet(f"font-size:32px;font-weight:bold;letter-spacing:16px;padding:12px;color:{C_ACCENT2};background:#180f05;border:1px solid {C_BORDER};font-family:'Courier New',monospace;")
        rl.addWidget(self.code_input); rl.addStretch()
        jb = rust_btn("[ 🔑 ВОЙТИ ]", C_TEXT); jb.setObjectName("successBtn"); jb.setFixedHeight(46)
        jb.clicked.connect(self._do_join); rl.addWidget(jb)
        blocks.addWidget(right, 1)

        root.addLayout(blocks, 1)
        hint = lbl(f"СЕРВЕР: {SERVER_URL}", 9, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter)
        hint.setContentsMargins(0, 0, 0, 12); root.addWidget(hint)

    def _do_create(self):
        name = self.host_name.text().strip() or "Ведущий"
        self.do_create.emit(name, self.cap_spin.value())

    def _do_join(self):
        code = self.code_input.text().strip().upper()
        name = self.player_name.text().strip()
        if not code: QMessageBox.warning(self, "Ошибка", "Введите код!"); return
        if not name: QMessageBox.warning(self, "Ошибка", "Введите имя!"); return
        self.do_join.emit(code, name)


# ─────────────────────────────────────────
#  ЭКРАН: ЛОББИ (с управлением ботами)
# ─────────────────────────────────────────

class LobbyScreen(QWidget):
    start_clicked  = pyqtSignal()
    add_bot        = pyqtSignal()
    remove_bot     = pyqtSignal(str)

    def __init__(self, code, is_host):
        super().__init__()
        self.code = code; self.is_host = is_host
        self._state = {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 40, 50, 40); layout.setSpacing(16)
        layout.addStretch()

        # Code display
        cf = QFrame(); cf.setObjectName("glow")
        cfl = QVBoxLayout(cf); cfl.setContentsMargins(30, 16, 30, 16)
        cfl.addWidget(lbl("// КОД ДОСТУПА //", 12, True, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))
        code_lbl = lbl(self.code, 56, True, C_ACCENT, Qt.AlignmentFlag.AlignCenter)
        code_lbl.setStyleSheet(f"color:{C_ACCENT};background:transparent;letter-spacing:22px;font-family:'Courier New',monospace;")
        cfl.addWidget(code_lbl)
        cfl.addWidget(lbl("ПЕРЕДАЙ КОД ОСТАЛЬНЫМ ВЫЖИВШИМ", 10, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(cf)

        # Two columns: players list + settings
        cols = QHBoxLayout(); cols.setSpacing(24)

        # LEFT: player list
        left = QFrame(); left.setObjectName("card")
        ll = QVBoxLayout(left); ll.setContentsMargins(16, 12, 16, 12); ll.setSpacing(8)
        ll.addWidget(lbl("// ВЫЖИВШИЕ В СЕТИ //", 11, True, C_TEXT_DIM))
        self.players_list = QListWidget(); self.players_list.setFixedHeight(220)
        ll.addWidget(self.players_list)
        self.status_lbl = lbl("ОЖИДАНИЕ...", 10, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(self.status_lbl)
        cols.addWidget(left, 2)

        # RIGHT: host settings (only for host)
        if self.is_host:
            right = QFrame(); right.setObjectName("card")
            rl = QVBoxLayout(right); rl.setContentsMargins(16, 12, 16, 12); rl.setSpacing(10)
            rl.addWidget(lbl("// НАСТРОЙКИ ЛОББИ //", 11, True, C_TEXT_DIM))
            rl.addWidget(sep())

            rl.addWidget(lbl("Кол-во слотов (мест в бункере):", 10, False, C_TEXT_DIM))
            slots_row = QHBoxLayout()
            self.slots_spin = QSpinBox(); self.slots_spin.setRange(1, 15); self.slots_spin.setValue(3)
            self.slots_spin.setFixedWidth(70)
            self.slots_lbl_hint = lbl("", 9, False, C_TEXT_DIM)
            slots_row.addWidget(self.slots_spin); slots_row.addWidget(self.slots_lbl_hint); slots_row.addStretch()
            rl.addLayout(slots_row)

            rl.addWidget(sep())
            rl.addWidget(lbl("Тестовые боты:", 10, True, C_ACCENT2))
            rl.addWidget(lbl("Управляются ведущим во время игры", 9, False, C_TEXT_DIM))

            add_bot_btn = rust_btn("[ 🤖 + Добавить бота ]", C_ACCENT)
            add_bot_btn.setObjectName("accentBtn"); add_bot_btn.setFixedHeight(34)
            add_bot_btn.clicked.connect(self.add_bot.emit)
            rl.addWidget(add_bot_btn)

            rl.addWidget(lbl("Боты в лобби:", 10, False, C_TEXT_DIM))
            self.bots_list = QListWidget(); self.bots_list.setFixedHeight(100)
            self.bots_list.setStyleSheet("QListWidget{font-size:11px;} QListWidget::item{padding:4px 8px;}")
            rl.addWidget(self.bots_list)

            remove_bot_btn = rust_btn("[ ✕ Удалить выбранного ]")
            remove_bot_btn.setObjectName("dangerBtn"); remove_bot_btn.setFixedHeight(30)
            remove_bot_btn.clicked.connect(self._remove_selected_bot)
            rl.addWidget(remove_bot_btn)

            rl.addStretch()
            cols.addWidget(right, 1)

        layout.addLayout(cols)

        if self.is_host:
            start_row = QHBoxLayout()
            self.start_btn = rust_btn("[ ⚙ НАЧАТЬ ИГРУ ]", C_ACCENT)
            self.start_btn.setObjectName("accentBtn"); self.start_btn.setFixedHeight(46)
            self.start_btn.clicked.connect(self._do_start)
            start_row.addStretch(); start_row.addWidget(self.start_btn); start_row.addStretch()
            layout.addLayout(start_row)
        else:
            layout.addWidget(lbl("// ОЖИДАЙТЕ КОМАНДЫ ВЕДУЩЕГО //", 11, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))

        layout.addStretch()

    def _do_start(self):
        # Обновляем capacity из slots_spin перед стартом
        self.start_clicked.emit()

    def _remove_selected_bot(self):
        item = self.bots_list.currentItem()
        if item:
            name = item.text().replace("🤖 ", "").strip()
            self.remove_bot.emit(name)

    def get_slots(self):
        if self.is_host and hasattr(self, "slots_spin"):
            return self.slots_spin.value()
        return 3

    def update_state(self, state):
        self._state = state
        players = state.get("players", [])
        bots = state.get("bots", [])

        self.players_list.clear()
        for p in players:
            is_bot = p.get("is_bot", False) or p.get("name") in bots
            icon = "🤖" if is_bot else "►"
            color = C_ACCENT2 if is_bot else C_TEXT
            item = QListWidgetItem(f"{icon} {p.get('name','?')}")
            item.setForeground(QColor(color))
            self.players_list.addItem(item)

        n_real = sum(1 for p in players if not (p.get("is_bot") or p.get("name") in bots))
        n_bots = len(bots)
        self.status_lbl.setText(f"Игроков: {n_real}  |  Ботов: {n_bots}  |  Всего: {len(players)}")

        if self.is_host and hasattr(self, "bots_list"):
            self.bots_list.clear()
            for bname in bots:
                item = QListWidgetItem(f"🤖 {bname}")
                item.setForeground(QColor(C_ACCENT2))
                self.bots_list.addItem(item)

    # backwards compat
    def update_players(self, players):
        self.players_list.clear()
        for p in players:
            item = QListWidgetItem(f"► {p.get('name','?')}")
            item.setForeground(QColor(C_TEXT))
            self.players_list.addItem(item)
        self.status_lbl.setText(f"ПОДКЛЮЧЕНО: {len(players)}")


# ─────────────────────────────────────────
#  ДИАЛОГ: ГОЛОСОВАНИЕ ЗА БОТА
# ─────────────────────────────────────────

class BotVoteDialog(QDialog):
    def __init__(self, bot_name, active_players, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"🤖 Голос за {bot_name}")
        self.setMinimumSize(380, 320)
        self.setStyleSheet(STYLE)
        self.selected = None
        layout = QVBoxLayout(self)
        layout.setSpacing(14); layout.setContentsMargins(24, 20, 24, 20)

        layout.addWidget(lbl(f"Голос бота [ {bot_name} ]", 14, True, C_ACCENT2, Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(lbl("Выберите цель:", 11, False, C_TEXT_DIM))

        self.list = QListWidget()
        self.list.setFixedHeight(200)
        for name in active_players:
            if name != bot_name:
                item = QListWidgetItem(f"  {name}")
                item.setForeground(QColor(C_TEXT))
                self.list.addItem(item)
        layout.addWidget(self.list)

        btn_row = QHBoxLayout()
        cancel = rust_btn("[ ОТМЕНА ]"); cancel.clicked.connect(self.reject)
        confirm = rust_btn("[ ✓ ПРОГОЛОСОВАТЬ ]", C_ACCENT); confirm.setObjectName("accentBtn")
        confirm.clicked.connect(self._confirm)
        btn_row.addWidget(cancel); btn_row.addWidget(confirm)
        layout.addLayout(btn_row)

    def _confirm(self):
        item = self.list.currentItem()
        if not item:
            QMessageBox.warning(self, "Выбор", "Выберите цель!"); return
        self.selected = item.text().strip()
        self.accept()


# ─────────────────────────────────────────
#  ДИАЛОГ: УПРАВЛЕНИЕ БОТОМ (раскрытие карт)
# ─────────────────────────────────────────

class BotTurnDialog(QDialog):
    """Хост выбирает какую карту раскрыть за бота."""
    def __init__(self, bot_card, discussion_phase, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"🤖 Ход бота: {bot_card.get('name','?')}")
        self.setMinimumSize(400, 460)
        self.setStyleSheet(STYLE)
        self.field_choice = None
        self.reveal_secret = False
        layout = QVBoxLayout(self)
        layout.setSpacing(10); layout.setContentsMargins(20, 16, 20, 16)

        layout.addWidget(lbl(f"🤖 Бот: {bot_card.get('name','?')}", 14, True, C_ACCENT2))
        layout.addWidget(sep())

        FIELD_META_ALL = [
            ("profession","⚙️","Профессия"), ("health","🩺","Здоровье"),
            ("hobby","🎯","Хобби"), ("baggage","🎒","Багаж"),
            ("bio","📋","Биография"), ("fact1","📌","Факт 1"),
            ("fact2","📌","Факт 2"), ("phobia","⚠️","Фобия"), ("skill","🔧","Навык"),
        ]

        layout.addWidget(lbl("Выберите карту для раскрытия:", 11, False, C_TEXT_DIM))
        self.field_list = QListWidget(); self.field_list.setFixedHeight(230)
        revealed = bot_card.get("revealed", {})
        for field, icon, label in FIELD_META_ALL:
            if discussion_phase == 0 and field != "profession":
                continue
            val = bot_card.get(field, "?")
            is_rev = revealed.get(field, False)
            status = "✓ " if is_rev else "   "
            color = C_TEXT_DIM if is_rev else C_TEXT
            item = QListWidgetItem(f"{status}{icon} {label}: {val[:50]}")
            item.setForeground(QColor(color))
            item.setData(Qt.ItemDataRole.UserRole, field)
            if is_rev:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.field_list.addItem(item)
        layout.addWidget(self.field_list)

        # Secret reveal button (not available in phase 0)
        if discussion_phase > 0:
            secret_val = bot_card.get("secret", "?")
            secret_rev = bot_card.get("secret_revealed", False)
            if not secret_rev:
                sec_btn = rust_btn(f"[ 🔒 Раскрыть секрет: {secret_val[:40]} ]", C_ACCENT)
                sec_btn.setObjectName("accentBtn"); sec_btn.setFixedHeight(32)
                sec_btn.clicked.connect(self._do_secret)
                layout.addWidget(sec_btn)

        btn_row = QHBoxLayout()
        cancel = rust_btn("[ ОТМЕНА ]"); cancel.clicked.connect(self.reject)
        reveal_btn = rust_btn("[ ▶ РАСКРЫТЬ ВЫБРАННОЕ ]", C_ACCENT2); reveal_btn.setObjectName("accentBtn")
        reveal_btn.clicked.connect(self._do_reveal)
        skip_btn = rust_btn("[ → ПРОПУСТИТЬ ХОД ]"); skip_btn.setObjectName("successBtn")
        skip_btn.clicked.connect(self._do_skip)
        btn_row.addWidget(cancel); btn_row.addWidget(reveal_btn); btn_row.addWidget(skip_btn)
        layout.addLayout(btn_row)

        self._result = None  # "reveal", "secret", "skip"

    def _do_reveal(self):
        item = self.field_list.currentItem()
        if not item or not (item.flags() & Qt.ItemFlag.ItemIsEnabled):
            QMessageBox.warning(self, "Выбор", "Выберите нераскрытое поле!"); return
        self.field_choice = item.data(Qt.ItemDataRole.UserRole)
        self._result = "reveal"
        self.accept()

    def _do_secret(self):
        self.reveal_secret = True
        self._result = "secret"
        self.accept()

    def _do_skip(self):
        self._result = "skip"
        self.accept()


# ─────────────────────────────────────────
#  ЭКРАН: ОСНОВНОЙ ИГРОВОЙ (DISCUSSION)
# ─────────────────────────────────────────

class DiscussionScreen(QWidget):
    do_reveal         = pyqtSignal(str)
    do_end_turn       = pyqtSignal()
    do_reveal_secret  = pyqtSignal()
    do_get_boost      = pyqtSignal(str)
    do_activate_boost = pyqtSignal(str)
    # Bot signals (host only)
    bot_reveal        = pyqtSignal(str, str)   # bot_name, field
    bot_reveal_secret = pyqtSignal(str)         # bot_name
    bot_end_turn      = pyqtSignal(str)         # bot_name

    def __init__(self, state, is_host, my_name):
        super().__init__()
        self.is_host = is_host
        self.my_name = my_name
        self._last_state = {}
        self._build()
        self.refresh(state)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8); layout.setSpacing(8)

        # Top bar
        top = QHBoxLayout()
        self.phase_lbl = lbl("", 14, True, C_ACCENT)
        top.addWidget(self.phase_lbl)
        top.addStretch()
        self.turn_lbl = lbl("", 12, True, C_ACTIVE)
        top.addWidget(self.turn_lbl)
        layout.addLayout(top)

        self.status_lbl = lbl("", 10, False, C_TEXT_DIM)
        layout.addWidget(self.status_lbl)

        # Main content
        content = QHBoxLayout(); content.setSpacing(10)

        # Left: cards scroll
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.cards_container = QWidget(); self.cards_container.setStyleSheet("background:transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(10); self.cards_layout.setContentsMargins(0,0,0,0)
        scroll.setWidget(self.cards_container)
        content.addWidget(scroll, 3)

        # Right panel
        right = QVBoxLayout(); right.setSpacing(8)

        # Turn order
        order_f = QFrame(); order_f.setObjectName("card")
        ofl = QVBoxLayout(order_f); ofl.setContentsMargins(10, 8, 10, 8)
        ofl.addWidget(lbl("// ОЧЕРЕДЬ ХОДОВ //", 10, True, C_TEXT_DIM))
        self.order_list = QListWidget(); self.order_list.setFixedHeight(160)
        self.order_list.setStyleSheet("QListWidget{font-size:11px;} QListWidget::item{padding:4px 8px;}")
        ofl.addWidget(self.order_list)
        right.addWidget(order_f)

        # Host controls
        if self.is_host:
            hf = QFrame(); hf.setObjectName("card")
            hfl = QVBoxLayout(hf); hfl.setContentsMargins(10, 8, 10, 8); hfl.setSpacing(6)
            hfl.addWidget(lbl("// ВЕДУЩИЙ //", 10, True, C_TEXT_DIM))

            self.bot_turn_btn = rust_btn("[ 🤖 Ход бота ]", C_ACCENT2)
            self.bot_turn_btn.setObjectName("accentBtn")
            self.bot_turn_btn.setEnabled(False)
            self.bot_turn_btn.clicked.connect(self._open_bot_turn)
            hfl.addWidget(self.bot_turn_btn)

            right.addWidget(hf)

        right.addStretch()
        content.addLayout(right, 1)
        layout.addLayout(content, 1)

    def refresh(self, state):
        self._last_state = state
        players = state.get("players", [])
        bots = state.get("bots", [])
        cur_name = state.get("current_turn_name", "")
        disc_phase = state.get("discussion_phase", 0)
        first_done = state.get("first_phase_done", False)
        total = state.get("total_fields", 9)
        rnd = state.get("round", 1)
        turns_done = state.get("turns_done", [])

        self.phase_lbl.setText(f"Раунд {rnd}  |  Фаза {disc_phase + 1} из {total}")
        if cur_name:
            is_cur_bot = cur_name in bots
            bot_marker = " 🤖" if is_cur_bot else ""
            self.turn_lbl.setText(f"Ход: {cur_name}{bot_marker}")

        if disc_phase == 0:
            self.status_lbl.setText("Фаза 1: каждый раскрывает ПРОФЕССИЮ. Бусты недоступны.")
        elif disc_phase == total - 2:
            self.status_lbl.setText("⚠ Следующая фаза — ФИНАЛЬНОЕ ГОЛОСОВАНИЕ")
        elif disc_phase == 2:
            self.status_lbl.setText("⚠ После этой фазы — ОБЯЗАТЕЛЬНОЕ ГОЛОСОВАНИЕ")
        else:
            self.status_lbl.setText("")

        # Bot turn button — active when current player is a bot (host only)
        if self.is_host and hasattr(self, "bot_turn_btn"):
            is_bot_turn = cur_name in bots
            self.bot_turn_btn.setEnabled(is_bot_turn)
            self.bot_turn_btn.setText(f"[ 🤖 Ход бота: {cur_name} ]" if is_bot_turn else "[ 🤖 Ход бота ]")

        # Rebuild cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        my_card = None
        others = []
        for p in players:
            if p.get("name") == self.my_name:
                my_card = p
            else:
                others.append(p)

        # My card (if I'm a player)
        if my_card:
            is_my_turn = (my_card.get("name") == cur_name) and not self.is_host
            cw = PlayerCardWidget(
                my_card, is_self=True, is_my_turn=is_my_turn,
                discussion_phase=disc_phase, first_phase_done=first_done
            )
            cw.reveal_field.connect(self.do_reveal.emit)
            cw.end_turn.connect(self.do_end_turn.emit)
            cw.reveal_secret.connect(self.do_reveal_secret.emit)
            cw.get_boost_self.connect(lambda: self.do_get_boost.emit("self"))
            cw.get_boost_group.connect(lambda: self.do_get_boost.emit("group"))
            cw.activate_boost_self.connect(lambda: self.do_activate_boost.emit("self"))
            cw.activate_boost_group.connect(lambda: self.do_activate_boost.emit("group"))
            self.cards_layout.addWidget(cw)

        # Other players (compact)
        if others:
            others_row = QHBoxLayout(); others_row.setSpacing(8)
            for p in others:
                is_bot = p.get("is_bot", False) or p.get("name") in bots
                cw = PlayerCardWidget(p, is_self=False, is_my_turn=(p.get("name")==cur_name),
                                      discussion_phase=disc_phase)
                cw.setFixedWidth(185)
                # Bot label
                if is_bot:
                    cw.setToolTip("🤖 Бот — управляется ведущим")
                others_row.addWidget(cw)
            others_row.addStretch()
            self.cards_layout.addLayout(others_row)

        self.cards_layout.addStretch()

        # Order list
        self.order_list.clear()
        order = state.get("turn_order", [])
        cur_idx = state.get("current_turn_idx", 0)
        for i, name in enumerate(order):
            p_elim = any(p.get("name")==name and p.get("eliminated") for p in players)
            is_bot = name in bots
            bot_mark = " 🤖" if is_bot else ""
            if p_elim:
                status = "✗ "; color = C_TEXT_DIM
            elif i == cur_idx:
                status = "▶ "; color = C_ACTIVE
            elif name in turns_done:
                status = "✓ "; color = C_SUCCESS
            else:
                status = "  "; color = C_TEXT
            item = QListWidgetItem(f"{status}{name}{bot_mark}")
            item.setForeground(QColor(color))
            self.order_list.addItem(item)

    def _open_bot_turn(self):
        """Хост открывает диалог управления ходом текущего бота."""
        state = self._last_state
        cur_name = state.get("current_turn_name", "")
        bots = state.get("bots", [])
        if cur_name not in bots:
            return
        players = state.get("players", [])
        bot_card = next((p for p in players if p.get("name") == cur_name), None)
        if not bot_card:
            return
        disc_phase = state.get("discussion_phase", 0)
        dlg = BotTurnDialog(bot_card, disc_phase, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if dlg._result == "reveal" and dlg.field_choice:
                self.bot_reveal.emit(cur_name, dlg.field_choice)
            elif dlg._result == "secret":
                self.bot_reveal_secret.emit(cur_name)
            elif dlg._result == "skip":
                self.bot_end_turn.emit(cur_name)


# ─────────────────────────────────────────
#  ЭКРАН: ГОЛОСОВАНИЕ
# ─────────────────────────────────────────

class VoteScreen(QWidget):
    player_vote    = pyqtSignal(str)
    host_eliminate = pyqtSignal(str)
    start_timer    = pyqtSignal(int)
    bot_vote       = pyqtSignal(str, str)   # bot_name, target

    def __init__(self, state, is_host, my_name):
        super().__init__()
        self.state = state; self.is_host = is_host; self.my_name = my_name
        self._voted = False
        self._bots = state.get("bots", [])
        self._active = state.get("active_players", [])
        self._build(state)
        self._start_auto_timer()

    def _build(self, state):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 20, 30, 20); layout.setSpacing(14)

        layout.addWidget(lbl("[ 🗳  ГОЛОСОВАНИЕ ]", 26, True, C_ACCENT2, Qt.AlignmentFlag.AlignCenter))

        active = state.get("active_players", [])
        cap = state.get("bunker_capacity", 0)
        need = max(0, len(active) - cap)
        layout.addWidget(lbl(f"Нужно изгнать: {need}  |  Активных: {len(active)}  |  Мест: {cap}",
                             12, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))

        # Timer
        timer_row = QHBoxLayout()
        self.timer_lbl = lbl("02:00", 28, True, C_ACCENT, Qt.AlignmentFlag.AlignCenter)
        timer_row.addStretch(); timer_row.addWidget(self.timer_lbl); timer_row.addStretch()
        layout.addLayout(timer_row)
        self._secs = 120
        self._timer = QTimer(); self._timer.timeout.connect(self._tick)

        self.status_lbl = lbl("Голосуйте!", 11, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_lbl)
        self.votes_lbl = lbl("", 11, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.votes_lbl)

        # Player cards grid
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget(); container.setStyleSheet("background:transparent;")
        grid = QGridLayout(container); grid.setSpacing(10)
        scroll.setWidget(container)

        players = state.get("players", [])
        bots = state.get("bots", [])
        active_cards = [p for p in players if not p.get("eliminated", False)]
        for i, p in enumerate(active_cards):
            name = p.get("name","")
            is_bot = name in bots
            frame = QFrame()
            frame.setObjectName("active_card" if is_bot else "card")
            fl = QVBoxLayout(frame); fl.setContentsMargins(12, 10, 12, 10); fl.setSpacing(5)

            name_color = C_ACCENT2 if is_bot else C_TEXT
            hdr = QHBoxLayout()
            hdr.addWidget(lbl(("🤖 " if is_bot else "") + name, 13, True, name_color, Qt.AlignmentFlag.AlignCenter))
            fl.addLayout(hdr)

            revealed_lines = []
            for field, icon, label in FIELD_META[:5]:
                if p.get("revealed",{}).get(field) and p.get(field):
                    revealed_lines.append(f"{icon} {p.get(field,'')}")
            if revealed_lines:
                info = lbl("\n".join(revealed_lines[:4]), 9, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter)
                info.setWordWrap(True); fl.addWidget(info)

            if self.is_host:
                # Eliminate button for all
                elim_btn = rust_btn("[ ☠ ИЗГНАТЬ ]", C_DANGER)
                elim_btn.setObjectName("dangerBtn"); elim_btn.setFixedHeight(28)
                elim_btn.clicked.connect(lambda _, n=name: self._host_confirm(n))
                fl.addWidget(elim_btn)
                # Bot vote button
                if is_bot:
                    bot_btn = rust_btn("[ 🤖 Голос бота ]", C_ACCENT2)
                    bot_btn.setObjectName("accentBtn"); bot_btn.setFixedHeight(28)
                    bot_btn.clicked.connect(lambda _, bn=name: self._bot_vote_dialog(bn))
                    fl.addWidget(bot_btn)
            elif not self._voted and name != self.my_name and not is_bot:
                btn = rust_btn("[ ПРОГОЛОСОВАТЬ ]", C_ACCENT)
                btn.setObjectName("accentBtn"); btn.setFixedHeight(30)
                btn.clicked.connect(lambda _, n=name: self._do_vote(n))
                fl.addWidget(btn)

            row, col = divmod(i, 3)
            grid.addWidget(frame, row, col)
        layout.addWidget(scroll, 1)

        if self.is_host:
            self.start_timer.emit(120)

    def _start_auto_timer(self):
        self._timer.start(1000)

    def _tick(self):
        self._secs -= 1
        m, s = divmod(max(0, self._secs), 60)
        self.timer_lbl.setText(f"{m:02d}:{s:02d}")
        if self._secs <= 10:
            self.timer_lbl.setStyleSheet(f"color:{C_DANGER};background:transparent;font-weight:bold;")
        if self._secs <= 0:
            self._timer.stop()

    def update_votes(self, votes):
        if votes:
            parts = [f"{k}→{v}" for k, v in votes.items()]
            self.votes_lbl.setText("Проголосовали: " + ", ".join(parts))
        else:
            self.votes_lbl.setText("")

    def _do_vote(self, target):
        if self._voted: return
        self._voted = True
        self.player_vote.emit(target)
        self.status_lbl.setText(f"Вы проголосовали против {target}")

    def _host_confirm(self, name):
        reply = QMessageBox.question(self, "Подтверждение",
            f"Изгнать игрока «{name}»?\nЭто нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._timer.stop()
            self.host_eliminate.emit(name)

    def _bot_vote_dialog(self, bot_name):
        """Хост голосует за бота через диалог с выбором цели."""
        candidates = [n for n in self._active if n != bot_name]
        dlg = BotVoteDialog(bot_name, candidates, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected:
            self.bot_vote.emit(bot_name, dlg.selected)
            # Помечаем в UI
            self.votes_lbl.setText(f"Бот {bot_name} → {dlg.selected}")


# ─────────────────────────────────────────
#  ЭКРАН: ФИНАЛ
# ─────────────────────────────────────────

class GameOverScreen(QWidget):
    new_game = pyqtSignal()

    def __init__(self, state):
        super().__init__()
        self.state = state
        self._build(state)

    def _build(self, state):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 30, 50, 30); layout.setSpacing(16)

        layout.addWidget(lbl("[ ✓ ОТБОР ЗАВЕРШЁН ]", 30, True, C_ACCENT2, Qt.AlignmentFlag.AlignCenter))

        survivors = [p for p in state.get("players",[]) if not p.get("eliminated")]
        eliminated = [p for p in state.get("players",[]) if p.get("eliminated")]

        sf = QFrame(); sf.setObjectName("glow")
        sl = QVBoxLayout(sf); sl.setContentsMargins(24, 16, 24, 16)
        sl.addWidget(lbl("// ДОПУЩЕНЫ В БУНКЕР //", 13, True, C_ACCENT, Qt.AlignmentFlag.AlignCenter))
        for p in survivors:
            sl.addWidget(lbl(f"⚙ {p.get('name')}  —  {p.get('profession','?')}",
                             13, False, C_TEXT, Qt.AlignmentFlag.AlignCenter))
        layout.addWidget(sf)

        if eliminated:
            ef = QFrame(); ef.setObjectName("danger_frame")
            el = QVBoxLayout(ef); el.setContentsMargins(24, 12, 24, 12)
            el.addWidget(lbl("// ИЗГНАНЫ //", 12, True, C_DANGER, Qt.AlignmentFlag.AlignCenter))
            for p in eliminated:
                el.addWidget(lbl(f"✗ {p.get('name')}  —  {p.get('profession','?')} | Секрет: {p.get('secret','')}",
                                 10, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))
            layout.addWidget(ef)

        # AI финал
        self.story_frame = QFrame(); self.story_frame.setObjectName("card")
        sfl = QVBoxLayout(self.story_frame); sfl.setContentsMargins(20, 14, 20, 14)
        sfl.addWidget(lbl("// ФИНАЛЬНАЯ ИСТОРИЯ //", 11, True, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))
        self.story_lbl = QTextEdit()
        self.story_lbl.setReadOnly(True); self.story_lbl.setFixedHeight(180)
        self.story_lbl.setStyleSheet(f"background:#180f05;border:1px solid {C_BORDER};color:{C_TEXT};font-size:11px;font-family:'Courier New',monospace;")
        self.story_lbl.setPlainText("Генерация истории...")
        sfl.addWidget(self.story_lbl)
        layout.addWidget(self.story_frame, 1)

        gen_btn = rust_btn("[ 🤖 СГЕНЕРИРОВАТЬ ИСТОРИЮ (AI) ]", C_ACCENT)
        gen_btn.setObjectName("accentBtn"); gen_btn.setFixedHeight(38)
        gen_btn.clicked.connect(lambda: self._generate_story(state))
        layout.addWidget(gen_btn)

        btn = rust_btn("[ 🔄 НОВАЯ ИГРА ]"); btn.setObjectName("successBtn"); btn.setFixedHeight(42)
        btn.clicked.connect(self.new_game); layout.addWidget(btn)

    def _generate_story(self, state):
        self.story_lbl.setPlainText("Генерация... пожалуйста подождите...")
        survivors = [p for p in state.get("players",[]) if not p.get("eliminated")]
        eliminated = [p for p in state.get("players",[]) if p.get("eliminated")]
        catastrophe = state.get("catastrophe","")
        bunker = state.get("bunker","")
        special = state.get("special","")

        surv_desc = "; ".join([f"{p.get('name')} (проф: {p.get('profession','?')}, здоровье: {p.get('health','?')}, навык: {p.get('skill','?')})" for p in survivors])
        elim_desc = "; ".join([f"{p.get('name')} (проф: {p.get('profession','?')}, секрет: {p.get('secret','?')})" for p in eliminated])

        prompt = (
            f"Ты пишешь финальную историю постапокалиптической игры «Бункер».\n\n"
            f"Катастрофа: {catastrophe}\n"
            f"Бункер: {bunker}\n"
            f"Условие: {special}\n\n"
            f"Выжившие в бункере: {surv_desc}\n"
            f"Изгнанные: {elim_desc}\n\n"
            f"Напиши короткий (200-250 слов) эпилог на русском языке: что случилось с выжившими "
            f"после выхода из бункера, какой вклад внёс каждый, кто оказался полезен. "
            f"Упомяни тайно отомщённых или проигравших. Тон — мрачный, постапокалиптический, кинематографичный."
        )

        t = threading.Thread(target=self._call_api, args=(prompt,), daemon=True)
        t.start()

    def _call_api(self, prompt):
        try:
            import urllib.request
            body = json.dumps({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }).encode()
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                text = data["content"][0]["text"]
                QTimer.singleShot(0, lambda: self.story_lbl.setPlainText(text))
        except Exception as e:
            QTimer.singleShot(0, lambda: self.story_lbl.setPlainText(
                f"Не удалось сгенерировать историю.\n{e}\n\n"
                "Убедитесь что задан ANTHROPIC_API_KEY или воспользуйтесь другим способом."))


# ─────────────────────────────────────────
#  ГЛАВНОЕ ОКНО
# ─────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚙ БУНКЕР")
        self.resize(1200, 780)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(STYLE)

        self.ws = None
        self.is_host = False
        self.my_name = ""
        self.lobby_code = ""
        self._state = {}

        # Central widget with bunker bar at top
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)

        self.bunker_bar = BunkerBar()
        self.bunker_bar.setVisible(False)
        main_layout.addWidget(self.bunker_bar)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack, 1)

        self._build_statusbar()
        self._show_start()

        if not HAS_WS:
            QMessageBox.warning(self, "Зависимость",
                "Библиотека websockets не найдена!\nУстановите: pip install websockets")

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w, h = self.width(), self.height()

        # Горизонтальные сканлайны — ржавчина
        p.setPen(QPen(QColor(0, 0, 0, 28)))
        for y in range(0, h, 4):
            p.drawLine(0, y, w, y)

        # Тонкая металлическая сетка
        p.setPen(QPen(QColor(80, 45, 10, 12)))
        for x in range(0, w, 50):
            p.drawLine(x, 0, x, h)
        for y in range(0, h, 50):
            p.drawLine(0, y, w, y)

        # Угловые засечки — бронзовые
        c = QColor(200, 112, 32, 90)
        p.setPen(QPen(c, 1))
        sz = 20
        for cx, cy in [(0,0),(w,0),(0,h),(w,h)]:
            dx = 1 if cx == 0 else -1
            dy = 1 if cy == 0 else -1
            p.drawLine(cx, cy, cx+dx*sz, cy)
            p.drawLine(cx, cy, cx, cy+dy*sz)
        p.end()

    def _build_statusbar(self):
        self.statusBar().setStyleSheet(
            f"QStatusBar{{background:{C_SURFACE};color:{C_TEXT_DIM};font-size:11px;"
            f"font-family:'Courier New',monospace;border-top:1px solid {C_BORDER};}}")
        self.status_lbl = QLabel("// НЕ ПОДКЛЮЧЁН")
        self.status_lbl.setStyleSheet(f"color:{C_TEXT_DIM};padding:2px 8px;font-family:'Courier New',monospace;")
        self.statusBar().addPermanentWidget(self.status_lbl)

    def _set_status(self, text, color=None):
        if color is None: color = C_TEXT_DIM
        self.status_lbl.setText(f"// {text.upper()}")
        self.status_lbl.setStyleSheet(f"color:{color};padding:2px 8px;font-family:'Courier New',monospace;")

    def _connect_ws(self):
        if not HAS_WS: return
        self.ws = WSWorker(SERVER_URL)
        self.ws.message_received.connect(self._on_message)
        self.ws.connected_signal.connect(lambda: self._set_status(f"СОЕДИНЕНИЕ: {SERVER_URL}", C_ACCENT))
        self.ws.disconnected_signal.connect(self._on_disconnected)
        self.ws.start()

    def _on_disconnected(self, err):
        self._set_status(f"ПОТЕРЯНО СОЕДИНЕНИЕ: {err}", C_DANGER)
        QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться:\n{err}\n\nСервер: {SERVER_URL}")

    def _send(self, data):
        if self.ws: self.ws.send(data)

    def _on_message(self, msg):
        t = msg.get("type","")

        if t == "error":
            QMessageBox.warning(self, "Ошибка", msg.get("message",""))

        elif t == "lobby_created":
            self.lobby_code = msg.get("code","")
            self._show_lobby()

        elif t == "state_update":
            self._state = msg
            phase = msg.get("phase","")
            self.bunker_bar.setVisible(phase not in ("lobby",""))
            if phase not in ("", "lobby"):
                self.bunker_bar.update_state(msg)
            if phase == "lobby": self._refresh_lobby(msg)
            elif phase == "catastrophe": self._show_catastrophe(msg)
            elif phase == "discussion": self._refresh_discussion(msg)
            elif phase == "vote": self._show_vote(msg)
            elif phase == "gameover": self._show_gameover(msg)

        elif t == "secret_revealed":
            name = msg.get("name","")
            secret = msg.get("secret","")
            QMessageBox.information(self, "🔒 Секрет раскрыт!",
                f"Игрок «{name}» раскрыл свой секрет:\n\n{secret}")

        elif t == "boost_activated":
            dlg = BoostNotifyDialog(
                msg.get("activator",""),
                msg.get("boost_name",""),
                msg.get("boost_desc",""),
                msg.get("boost_type","self"),
                self
            )
            dlg.exec()

        elif t == "vote_tie":
            QMessageBox.information(self, "Ничья!", msg.get("message","Повторное голосование!"))

        elif t == "pong":
            pass

    # ── SCREENS ────────────────────────────────

    def _clear(self):
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

    def _show_start(self):
        self._clear(); self.bunker_bar.setVisible(False)
        scr = StartScreen()
        scr.do_create.connect(self._create_lobby)
        scr.do_join.connect(self._join_lobby)
        self.stack.addWidget(scr)
        self._set_status("Добро пожаловать в Бункер")

    def _create_lobby(self, host_name, capacity):
        self.is_host = True; self.my_name = host_name
        self._connect_ws()
        QTimer.singleShot(800, lambda: self._send({
            "action": "create_lobby", "host_name": host_name, "bunker_capacity": capacity}))

    def _join_lobby(self, code, name):
        self.is_host = False; self.my_name = name; self.lobby_code = code
        self._connect_ws()
        QTimer.singleShot(800, lambda: self._send({
            "action": "join_lobby", "code": code, "name": name}))

    def _show_lobby(self):
        self._clear()
        scr = LobbyScreen(self.lobby_code, self.is_host)
        scr.start_clicked.connect(self._do_start_game)
        scr.add_bot.connect(lambda: self._send({
            "action": "add_bot", "code": self.lobby_code}))
        scr.remove_bot.connect(lambda name: self._send({
            "action": "remove_bot", "code": self.lobby_code, "name": name}))
        self.stack.addWidget(scr)
        self._set_status(f"Лобби: {self.lobby_code}", C_ACCENT)

    def _do_start_game(self):
        w = self.stack.currentWidget()
        capacity = w.get_slots() if isinstance(w, LobbyScreen) else 3
        self._send({"action": "start_game", "code": self.lobby_code,
                    "bunker_capacity": capacity})

    def _refresh_lobby(self, state):
        w = self.stack.currentWidget()
        if isinstance(w, LobbyScreen):
            w.update_state(state)
        else:
            self._show_lobby()
            w = self.stack.currentWidget()
            if isinstance(w, LobbyScreen):
                w.update_state(state)

    def _show_catastrophe(self, state):
        self._clear()
        # Show scenario popup
        dlg = ScenarioDialog(
            state.get("scenario",""),
            state.get("bunker",""),
            state.get("catastrophe",""),
            state.get("special",""),
            self
        )
        # Store scenario for sidebar
        self._scenario_text = state.get("scenario","")

        # While dialog is open, show simple waiting screen
        wait = QWidget()
        wl = QVBoxLayout(wait)
        wl.addStretch()
        wl.addWidget(lbl("[ ☢ КАТАСТРОФА ]", 30, True, C_DANGER, Qt.AlignmentFlag.AlignCenter))
        wl.addWidget(lbl(state.get("catastrophe",""), 14, False, C_ACCENT, Qt.AlignmentFlag.AlignCenter))
        wl.addStretch()
        if self.is_host:
            proceed_btn = rust_btn("[ ▶ К ОБСУЖДЕНИЮ ]", C_ACCENT)
            proceed_btn.setObjectName("accentBtn"); proceed_btn.setFixedHeight(44)
            proceed_btn.clicked.connect(lambda: self._send({"action":"next_phase","code":self.lobby_code}))
            wl.addWidget(proceed_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        else:
            wl.addWidget(lbl("// ВЕДУЩИЙ УПРАВЛЯЕТ //", 11, False, C_TEXT_DIM, Qt.AlignmentFlag.AlignCenter))
        wl.addStretch()
        self.stack.addWidget(wait)
        self._set_status("Катастрофа", C_DANGER)

        dlg.exec()

    def _refresh_discussion(self, state):
        w = self.stack.currentWidget()
        if isinstance(w, DiscussionScreen):
            w.refresh(state)
        else:
            self._clear()
            scr = DiscussionScreen(state, self.is_host, self.my_name)
            scr.do_reveal.connect(lambda f: self._send({"action":"reveal_card","code":self.lobby_code,"field":f}))
            scr.do_end_turn.connect(lambda: self._send({"action":"end_turn","code":self.lobby_code}))
            scr.do_reveal_secret.connect(lambda: self._send({"action":"reveal_secret","code":self.lobby_code}))
            scr.do_get_boost.connect(lambda bt: self._send({"action":"get_boost","code":self.lobby_code,"boost_type":bt}))
            scr.do_activate_boost.connect(lambda bt: self._send({"action":"activate_boost","code":self.lobby_code,"boost_type":bt}))
            # Bot signals (host only)
            scr.bot_reveal.connect(lambda bn, f: self._send({"action":"bot_reveal_card","code":self.lobby_code,"bot_name":bn,"field":f}))
            scr.bot_reveal_secret.connect(lambda bn: self._send({"action":"bot_reveal_secret","code":self.lobby_code,"bot_name":bn}))
            scr.bot_end_turn.connect(lambda bn: self._send({"action":"bot_end_turn","code":self.lobby_code,"bot_name":bn}))
            self.stack.addWidget(scr)
        rnd = state.get("round",1)
        self._set_status(f"Раунд {rnd} — Обсуждение | {self.lobby_code}", C_ACCENT)

    def _show_vote(self, state):
        self._clear()
        scr = VoteScreen(state, self.is_host, self.my_name)
        scr.player_vote.connect(lambda t: self._send({"action":"player_vote","code":self.lobby_code,"target":t}))
        scr.host_eliminate.connect(lambda t: self._send({"action":"host_eliminate","code":self.lobby_code,"target":t}))
        scr.start_timer.connect(lambda s: self._send({"action":"start_vote_timer","code":self.lobby_code,"seconds":s}))
        scr.bot_vote.connect(lambda bn, t: self._send({"action":"bot_vote","code":self.lobby_code,"bot_name":bn,"target":t}))
        self.stack.addWidget(scr)
        self._set_status(f"Голосование | {self.lobby_code}", C_ACCENT2)

    def _refresh_vote(self, state):
        w = self.stack.currentWidget()
        if isinstance(w, VoteScreen):
            w.update_votes(state.get("votes",{}))

    def _show_gameover(self, state):
        self._clear()
        scr = GameOverScreen(state)
        scr.new_game.connect(self._show_start)
        self.stack.addWidget(scr)
        self.bunker_bar.setVisible(False)
        self._set_status("Игра завершена!", C_ACCENT2)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Бункер")
    app.setFont(QFont("Courier New", 11))
    win = MainWindow(); win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

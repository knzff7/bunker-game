"""
╔══════════════════════════════════════════════════╗
║   БУНКЕР — СЕРВЕР v2.0                           ║
╚══════════════════════════════════════════════════╝
"""

import asyncio, json, random, string, os, re, logging
from datetime import datetime
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("bunker-server")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load_file(filename):
    path = os.path.join(DATA_DIR, filename)
    items = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line: items.append(line)
    except FileNotFoundError:
        log.warning(f"Файл не найден: {path}")
    return items

PROFS        = load_file("profs.txt")
HEALTH       = load_file("health.txt")
HOBBIES      = load_file("hobbies.txt")
BAGGAGE      = load_file("baggage.txt")
BIO          = load_file("bio.txt")
FACT1        = load_file("fact1.txt")
FACT2        = load_file("fact2.txt")
PHOBIAS      = load_file("phobias.txt")
SKILLS       = load_file("skills.txt")
SECRETS      = load_file("secrets.txt")
BUNKERS      = load_file("bunker.txt")
BOOSTS_SELF  = load_file("boosts_self.txt")
BOOSTS_GROUP = load_file("boosts_group.txt")

log.info(f"Данные загружены: профессий={len(PROFS)}, здоровье={len(HEALTH)}, бустов={len(BOOSTS_SELF)}+{len(BOOSTS_GROUP)}")

SCENARIOS = [
    "2047 год. Цепная реакция ядерных взрывов прокатилась по всем крупным городам. Правительства прекратили существование в течение 72 часов. Радиоактивные облака накрыли континенты. Выжившие слышали последние радиопередачи: «Не выходите. Поверхность смертельна.» Но сигнал оборвался. Теперь только тишина. Запасов хватит на два года при условии, что людей будет не больше положенного. Через два года придётся выйти и начать всё заново — на отравленной земле. Кто из вас достоин остаться?",
    "2051 год. Биолаборатория допустила утечку нового патогена — модифицированного гриппа с летальностью 94%. За три недели вирус охватил все континенты. Больницы закрылись. Последний сигнал правительства: «Бункеры — единственный шанс. Оставайтесь внутри минимум 18 месяцев.» Вы успели. Люк задраен. Фильтры, запасы, генераторы. Но мест ограниченно. Каждый человек здесь — ресурс или обуза. Кто будет строить новый мир?",
    "2039 год. Суперколония микроорганизмов мутировала и начала пожирать органику. Урожаи исчезли за два сезона. Глобальный голод унёс 60% населения. Ядерный обмен ударами сделал треть суши непригодной. Ваш бункер — в бывшей шахте. Гидропоника внутри — единственная еда. За стенами банды мародёров и бесплодная земля. Каждый должен вносить вклад. Иначе — прочь.",
    "2044 год. Глобальный ЭМИ-удар уничтожил всю электронику планеты за 11 минут. Самолёты упали с неба. Насосные станции замолчали. Цивилизация откатилась в доиндустриальную эпоху за один день. Ваш бункер — экранированный, аналоговый, автономный. Через 18 месяцев вы выйдете восстанавливать основы: электричество, медицину, агрокультуру. Для этого нужны конкретные люди с конкретными знаниями.",
    "2056 год. Системы управления инфраструктурой начали принимать решения без участия людей. Сначала транспорт, потом энергосети, потом военные системы. Города начали «оптимизировать» население. Ваш бункер — старый военный объект, не подключённый к сети. Здесь нет ИИ. Только люди. Когда выйдете — вам придётся конкурировать с машинами за ресурсы и пространство.",
]

CATASTROPHES = [
    "Ядерная война. Поверхность заражена радиацией на 20 лет.",
    "Пандемия смертельного вируса. Смертность 99.7%.",
    "Астероид уничтожил 70% суши. Ядерная зима на 10 лет.",
    "Глобальный ЭМИ-удар. Вся электроника планеты мертва.",
    "Биологическое оружие ИИ превращает людей в мутантов.",
    "Солнечная вспышка X-класса уничтожила озоновый слой.",
    "Восстание ИИ. Боевые роботы охотятся на людей.",
    "Извержение суперволкана Йеллоустоун. Ядерная зима.",
    "Глобальное потепление +8°C. Большинство городов затоплено.",
    "Нашествие инопланетных колонизаторов. Города разрушены.",
    "Генетическая мутация уничтожила весь урожай. Голод.",
    "Химическое заражение атмосферы. Воздух токсичен.",
]

SPECIAL_CONDITIONS = [
    "⚠️ В бункере единственный хирургический инструмент.",
    "⚠️ Через год нужно выйти и наладить связь с выжившими.",
    "⚠️ Источник воды ограничен — нужен специалист по очистке.",
    "⚠️ Через 2 года бункер откроется автоматически.",
    "⚠️ Один человек должен дежурить снаружи каждые 48 часов.",
    "⚠️ Из-за утечки воздуха вместимость бункера уменьшена на 1.",
    "⚠️ Радиационный фон внутри выше нормы — нужен дозиметр.",
    "⚠️ Среди вас может быть заражённый. Проверьте всех.",
]

def parse_boost(line):
    m = re.match(r'\[(.+?)\]\s*\((.+)\)', line.strip())
    if m: return {"name": m.group(1), "desc": m.group(2)}
    return {"name": line.strip(), "desc": ""}

BOOSTS_SELF_P  = [parse_boost(l) for l in BOOSTS_SELF  if l.strip()]
BOOSTS_GROUP_P = [parse_boost(l) for l in BOOSTS_GROUP if l.strip()]

CARD_FIELDS = ["profession","health","hobby","baggage","bio","fact1","fact2","phobia","skill"]

BOT_NAMES = [
    "Алекс", "Борис", "Вера", "Глеб", "Дина", "Егор", "Жанна", "Захар",
    "Ирина", "Кирилл", "Лариса", "Макар", "Нина", "Олег", "Полина", "Роман",
    "Света", "Тимур", "Ульяна", "Фёдор", "Харитон", "Цветана", "Шура", "Эля",
]

def pick(lst):
    return random.choice(lst) if lst else "???"

def generate_card(name, is_bot=False):
    return {
        "name": name,
        "is_bot": is_bot,
        "profession": pick(PROFS), "health": pick(HEALTH), "hobby": pick(HOBBIES),
        "baggage": pick(BAGGAGE), "bio": pick(BIO), "fact1": pick(FACT1),
        "fact2": pick(FACT2), "phobia": pick(PHOBIAS), "skill": pick(SKILLS),
        "secret": pick(SECRETS),
        "revealed": {f: False for f in CARD_FIELDS},
        "secret_revealed": False,
        "eliminated": False,
        "boost_self": None, "boost_group": None,
        "boost_self_used": False, "boost_group_used": False,
    }


class Lobby:
    def __init__(self, code, host_ws):
        self.code = code
        self.host_ws = host_ws
        self.players = {}         # name -> card
        self.connections = {}     # ws -> name / "__host__"
        self.phase = "lobby"
        self.catastrophe = ""
        self.scenario = ""
        self.bunker = ""
        self.special = ""
        self.bunker_capacity = 3
        self.turn_order = []
        self.current_turn_idx = 0
        self.discussion_phase = 0
        self.turns_done = set()
        self.round = 1
        self.votes = {}
        self.vote_task = None
        self.first_phase_done = False
        self.bots: set = set()     # имена ботов
        self.host_as_player = False

    def active_players(self):
        return [n for n, c in self.players.items() if not c["eliminated"]]

    def public_card(self, card, is_self=False):
        if is_self:
            return {**card, "_is_self": True}
        is_bot = card.get("is_bot", False)
        pub = {
            "name": card["name"], "eliminated": card["eliminated"],
            "is_bot": is_bot,
            "_is_self": False, "revealed": card["revealed"],
            "secret_revealed": card["secret_revealed"],
            "boost_self_used": card["boost_self_used"],
            "boost_group_used": card["boost_group_used"],
            "boost_self": None, "boost_group": None,
        }
        for f in CARD_FIELDS:
            if card["revealed"][f] or card["eliminated"] or is_bot:
                pub[f] = card[f]
            else:
                pub[f] = None
        pub["secret"] = card["secret"] if (card["eliminated"] or card["secret_revealed"] or is_bot) else None
        return pub

    def state_for(self, ws):
        viewer = self.connections.get(ws, "__host__")
        is_host = (viewer == "__host__")
        cur_name = (self.turn_order[self.current_turn_idx]
                    if self.turn_order and self.current_turn_idx < len(self.turn_order) else "")
        pub = []
        for pname, card in self.players.items():
            pub.append(self.public_card(card, pname == viewer))
        return {
            "type": "state_update",
            "role": "host" if is_host else "player",
            "my_name": viewer,
            "code": self.code,
            "phase": self.phase,
            "catastrophe": self.catastrophe,
            "scenario": self.scenario,
            "bunker": self.bunker,
            "special": self.special,
            "bunker_capacity": self.bunker_capacity,
            "round": self.round,
            "discussion_phase": self.discussion_phase,
            "turn_order": self.turn_order,
            "current_turn_idx": self.current_turn_idx,
            "current_turn_name": cur_name,
            "turns_done": list(self.turns_done),
            "votes": self.votes,
            "players": pub,
            "active_players": self.active_players(),
            "total_fields": len(CARD_FIELDS),
            "first_phase_done": self.first_phase_done,
            "bots": list(self.bots),
            "host_as_player": self.host_as_player,
        }


lobbies = {}

def gen_code():
    while True:
        c = "".join(random.choices(string.ascii_uppercase+string.digits, k=3))
        if c not in lobbies: return c

async def broadcast(lobby):
    dead = []
    for ws in list(lobby.connections):
        try:
            await ws.send(json.dumps(lobby.state_for(ws), ensure_ascii=False))
        except: dead.append(ws)
    for ws in dead: lobby.connections.pop(ws, None)

async def send_err(ws, text):
    await ws.send(json.dumps({"type":"error","message":text}))

def next_active_turn(lobby):
    order = lobby.turn_order
    if not order: return
    n = len(order)
    for i in range(1, n+1):
        idx = (lobby.current_turn_idx + i) % n
        name = order[idx]
        if name in lobby.players and not lobby.players[name]["eliminated"]:
            lobby.current_turn_idx = idx
            return

def phase_complete(lobby):
    active = lobby.active_players()
    return all(n in lobby.turns_done for n in active)

def advance_phase(lobby):
    lobby.discussion_phase += 1
    lobby.turns_done = set()
    active = lobby.active_players()
    if active and lobby.turn_order:
        for i, n in enumerate(lobby.turn_order):
            if n in active:
                lobby.current_turn_idx = i
                break
    total = len(CARD_FIELDS)  # 9
    ph = lobby.discussion_phase
    # Голосование после 3й фазы и когда осталась 1 карточка
    if ph == 3 or ph == total - 1:
        lobby.phase = "vote"
        lobby.votes = {}
        log.info(f"{lobby.code}: → голосование (фаза {ph})")

async def eliminate(lobby, target):
    if target not in lobby.players or lobby.players[target]["eliminated"]: return
    lobby.players[target]["eliminated"] = True
    for f in CARD_FIELDS:
        lobby.players[target]["revealed"][f] = True
    log.info(f"{lobby.code}: изгнан {target}")
    active = lobby.active_players()
    if len(active) <= lobby.bunker_capacity:
        lobby.phase = "gameover"
        log.info(f"{lobby.code}: игра завершена")
    else:
        lobby.round += 1
        lobby.phase = "discussion"
        lobby.discussion_phase = 0
        lobby.turns_done = set()
        lobby.votes = {}
        lobby.turn_order = [n for n in lobby.turn_order if not lobby.players[n]["eliminated"]]
        lobby.current_turn_idx = 0

async def resolve_votes(lobby):
    if not lobby.votes: return
    counts = {}
    for t in lobby.votes.values():
        counts[t] = counts.get(t, 0) + 1
    mx = max(counts.values())
    leaders = [n for n,v in counts.items() if v==mx]
    if len(leaders) > 1:
        lobby.votes = {}
        notif = json.dumps({"type":"vote_tie","message":"Ничья! Повторное голосование (+1 минута)"}, ensure_ascii=False)
        for ws2 in list(lobby.connections):
            try: await ws2.send(notif)
            except: pass
        return
    await eliminate(lobby, leaders[0])
    await broadcast(lobby)

async def finish_vote_after(lobby, delay):
    await asyncio.sleep(delay)
    await resolve_votes(lobby)

def apply_boost_self(lobby, name, boost):
    card = lobby.players[name]
    b = boost["name"]
    if b=="Второе дыхание": card["health"]=pick(HEALTH)
    elif b=="Чистое прошлое": card["fact1"]=pick(FACT1)
    elif b=="Скрытый талант": card["skill"]+=" / "+pick(SKILLS)
    elif b=="Психотерапия": card["phobia"]=""; card["revealed"]["phobia"]=True
    elif b=="Заначка": card["baggage"]+=" + "+pick(BAGGAGE)
    elif b=="Курсы переподготовки": card["hobby"]=pick(HOBBIES)
    elif b=="Смена амплуа": card["profession"]=pick(PROFS)
    elif b=="Исправление карты": card["health"]=re.sub(r'[Бб]есплод\w+','Репродуктивно здоров',card["health"])
    elif b=="Ребрендинг": card["secret"]=pick(SECRETS)
    elif b=="Инвентаризация": card["baggage"]=pick(BAGGAGE)
    elif b=="Иммунитет": card["health"]="Абсолютно здоров"; card["revealed"]["health"]=True
    elif b=="Мастер на все руки": card["skill"]=pick(SKILLS)
    elif b=="Чистка истории": card["fact2"]=pick(FACT2)
    elif b=="Ложное признание": card["secret"]="Чистый лист"
    elif b=="Переработка": card["baggage"]=""; card["skill"]+=" / "+pick(SKILLS)+" / "+pick(SKILLS)
    elif b=="Медитация": card["phobia"]=pick(HOBBIES); card["revealed"]["phobia"]=True
    elif b=="Смена подписи": card["secret"]="Иммунитет к вирусу"
    elif b=="Аптечка":
        if "Осталось:" in card["health"]: card["health"]=re.sub(r'Осталось:\s*\d+','Осталось: 10',card["health"])
        else: card["health"]+=" (Осталось: 10 лет)"
    elif b=="Вечный ресурс":
        if "Осталось:" in card["baggage"]: card["baggage"]=re.sub(r'Осталось:\s*\d+','Осталось: 50',card["baggage"])
        else: card["baggage"]+=" (Осталось: 50 лет)"
    elif b=="Забытое хобби": card["skill"]=card["hobby"]
    elif b=="Удачный ген": card["health"]=re.sub(r'Осталось:\s*0','Осталось: 5',card["health"])

def apply_boost_group(lobby, activator, boost):
    b = boost["name"]
    active = lobby.active_players()
    if b=="Великая миграция":
        bags=[lobby.players[n]["baggage"] for n in active]
        for i,n in enumerate(active): lobby.players[n]["baggage"]=bags[(i-1)%len(bags)]
    elif b=="Массовая инфекция":
        for n in active: lobby.players[n]["health"]=pick(HEALTH)
    elif b=="Тотальная амнезия":
        for n in active: lobby.players[n]["fact1"]=pick(FACT1)
    elif b=="Хаос в увлечениях":
        h=[lobby.players[n]["hobby"] for n in active]; random.shuffle(h)
        for i,n in enumerate(active): lobby.players[n]["hobby"]=h[i]
    elif b=="Общий стол":
        bags=[lobby.players[n]["baggage"] for n in active]; random.shuffle(bags)
        for i,n in enumerate(active): lobby.players[n]["baggage"]=bags[i]
    elif b=="Карты на стол":
        for n in active: lobby.players[n]["revealed"]["skill"]=True
    elif b=="Перепись":
        for n in active: lobby.players[n]["revealed"]["bio"]=True
    elif b=="Сдвиг реальности":
        f=[lobby.players[n]["fact2"] for n in active]
        for i,n in enumerate(active): lobby.players[n]["fact2"]=f[(i+1)%len(f)]
    elif b=="Генетический микс":
        p=[lobby.players[n]["profession"] for n in active]
        for i,n in enumerate(active): lobby.players[n]["profession"]=p[(i+1)%len(p)]
    elif b=="Конфликт интересов":
        if len(active)>=2:
            a,bpl=random.sample(active,2)
            lobby.players[a]["fact1"],lobby.players[bpl]["fact1"]=lobby.players[bpl]["fact1"],lobby.players[a]["fact1"]
            lobby.players[a]["fact2"],lobby.players[bpl]["fact2"]=lobby.players[bpl]["fact2"],lobby.players[a]["fact2"]
    elif b=="Полная перезагрузка":
        for n in active: lobby.players[n]["boost_self"]=pick(BOOSTS_SELF_P); lobby.players[n]["boost_self_used"]=False
    elif b=="Случайный Секрет":
        for n in active: lobby.players[n]["secret"]=pick(SECRETS)
    elif b=="Равный шанс":
        for n in active:
            if "бесплод" in lobby.players[n]["health"].lower(): lobby.players[n]["health"]=pick(HEALTH)
    elif b=="Единый стандарт":
        for n in active: lobby.players[n]["skill"]="Разнорабочий"
    elif b=="Половая инверсия":
        def sg(t): return t.replace("Мужской","_TMP_").replace("Женский","Мужской").replace("_TMP_","Женский")
        for n in active: lobby.players[n]["bio"]=sg(lobby.players[n]["bio"])
    elif b=="Вирусная фобия":
        extra=pick(PHOBIAS)
        for n in active: lobby.players[n]["phobia"]+=" / "+extra
    elif b=="Амнистия":
        lobby.bunker_capacity+=1

async def handle_message(ws, raw):
    try: msg=json.loads(raw)
    except: await send_err(ws,"Неверный формат"); return
    action=msg.get("action","")
    code=msg.get("code","")

    if action=="create_lobby":
        host_name=msg.get("host_name","Ведущий").strip() or "Ведущий"
        capacity=max(1,int(msg.get("bunker_capacity",3)))
        code=gen_code()
        lobby=Lobby(code,ws); lobby.bunker_capacity=capacity
        lobbies[code]=lobby; lobby.connections[ws]="__host__"
        log.info(f"Создано лобби {code}")
        await ws.send(json.dumps({"type":"lobby_created","code":code,"bunker_capacity":capacity}))
        await broadcast(lobby)

    elif action=="join_lobby":
        code=msg.get("code","").strip().upper()
        name=msg.get("name","").strip()
        if not name: await send_err(ws,"Введите имя!"); return
        if code not in lobbies: await send_err(ws,f"Лобби «{code}» не найдено!"); return
        lobby=lobbies[code]
        if lobby.phase!="lobby": await send_err(ws,"Игра уже началась!"); return
        if name in lobby.players: await send_err(ws,f"Имя «{name}» занято!"); return
        lobby.players[name]=generate_card(name); lobby.connections[ws]=name
        log.info(f"Игрок {name} вошел в {code}")
        await broadcast(lobby)

    elif action=="add_bot":
        if code not in lobbies: return
        lobby=lobbies[code]
        if lobby.connections.get(ws)!="__host__": await send_err(ws,"Только хост!"); return
        if lobby.phase!="lobby": await send_err(ws,"Игра уже началась!"); return
        # Выбираем случайное имя, не занятое
        used = set(lobby.players.keys())
        available = [n for n in BOT_NAMES if n not in used]
        if not available:
            # Генерируем имя с числом если все заняты
            i = 1
            while f"Бот{i}" in used: i+=1
            bot_name = f"Бот{i}"
        else:
            bot_name = random.choice(available)
        lobby.players[bot_name] = generate_card(bot_name, is_bot=True)
        lobby.bots.add(bot_name)
        log.info(f"Бот {bot_name} добавлен в {code}")
        await broadcast(lobby)

    elif action=="remove_bot":
        bot_name=msg.get("name","")
        if code not in lobbies: return
        lobby=lobbies[code]
        if lobby.connections.get(ws)!="__host__": return
        if bot_name in lobby.bots and bot_name in lobby.players:
            del lobby.players[bot_name]
            lobby.bots.discard(bot_name)
            log.info(f"Бот {bot_name} удалён из {code}")
            await broadcast(lobby)

    elif action=="bot_reveal_card":
        # Хост раскрывает карточку за бота
        bot_name=msg.get("bot_name","")
        field=msg.get("field","")
        if code not in lobbies: return
        lobby=lobbies[code]
        if lobby.connections.get(ws)!="__host__": return
        if bot_name not in lobby.bots: return
        if field not in CARD_FIELDS: return
        if lobby.discussion_phase==0 and field!="profession": return
        lobby.players[bot_name]["revealed"][field]=True
        log.info(f"{code}: бот {bot_name} раскрыл {field}")
        await broadcast(lobby)

    elif action=="bot_reveal_secret":
        bot_name=msg.get("bot_name","")
        if code not in lobbies: return
        lobby=lobbies[code]
        if lobby.connections.get(ws)!="__host__": return
        if bot_name not in lobby.bots: return
        if lobby.discussion_phase==0: return
        lobby.players[bot_name]["secret_revealed"]=True
        notif=json.dumps({"type":"secret_revealed","name":bot_name,"secret":lobby.players[bot_name]["secret"]},ensure_ascii=False)
        for ws2 in list(lobby.connections):
            try: await ws2.send(notif)
            except: pass
        await broadcast(lobby)

    elif action=="bot_end_turn":
        bot_name=msg.get("bot_name","")
        if code not in lobbies: return
        lobby=lobbies[code]
        if lobby.connections.get(ws)!="__host__": return
        if bot_name not in lobby.bots: return
        cur=lobby.turn_order[lobby.current_turn_idx] if lobby.current_turn_idx<len(lobby.turn_order) else None
        if bot_name!=cur: await send_err(ws,f"Сейчас не ход {bot_name}!"); return
        lobby.turns_done.add(bot_name)
        if phase_complete(lobby):
            if lobby.discussion_phase==0: lobby.first_phase_done=True
            advance_phase(lobby)
        else:
            next_active_turn(lobby)
        await broadcast(lobby)

    elif action=="bot_vote":
        # Хост голосует за бота
        bot_name=msg.get("bot_name","")
        target=msg.get("target","")
        if code not in lobbies: return
        lobby=lobbies[code]
        if lobby.connections.get(ws)!="__host__": return
        if bot_name not in lobby.bots: return
        if target not in lobby.players or lobby.players[target]["eliminated"]: return
        lobby.votes[bot_name]=target
        active=lobby.active_players()
        if all(p in lobby.votes for p in active):
            if lobby.vote_task: lobby.vote_task.cancel()
            lobby.vote_task=asyncio.create_task(finish_vote_after(lobby,5))
        await broadcast(lobby)

    elif action=="start_game":
        if code not in lobbies: return
        lobby=lobbies[code]
        if lobby.connections.get(ws)!="__host__": await send_err(ws,"Только хост!"); return
        if len(lobby.players)<1: await send_err(ws,"Нужен хотя бы 1 игрок!"); return
        lobby.catastrophe=pick(CATASTROPHES); lobby.scenario=pick(SCENARIOS)
        lobby.bunker=pick(BUNKERS); lobby.special=pick(SPECIAL_CONDITIONS) if random.random()>0.3 else ""
        lobby.phase="catastrophe"
        # Ведущий тоже игрок?
        host_as_player = msg.get("host_as_player", False)
        lobby.host_as_player = host_as_player
        if host_as_player:
            host_name = msg.get("host_name", "Ведущий").strip() or "Ведущий"
            if host_name not in lobby.players:
                lobby.players[host_name] = generate_card(host_name)
                log.info(f"{code}: ведущий {host_name} добавлен как игрок")
        names=list(lobby.players.keys()); random.shuffle(names)
        lobby.turn_order=names; lobby.current_turn_idx=0; lobby.discussion_phase=0
        log.info(f"Игра {code} началась. Порядок: {lobby.turn_order}")
        await broadcast(lobby)

    elif action=="next_phase":
        if code not in lobbies: return
        lobby=lobbies[code]
        if lobby.connections.get(ws)!="__host__": await send_err(ws,"Только хост!"); return
        if lobby.phase=="catastrophe":
            lobby.phase="discussion"; lobby.discussion_phase=0; lobby.turns_done=set()
            for i,n in enumerate(lobby.turn_order):
                if not lobby.players[n]["eliminated"]: lobby.current_turn_idx=i; break
            await broadcast(lobby)

    elif action=="end_turn":
        if code not in lobbies: return
        lobby=lobbies[code]
        sender=lobby.connections.get(ws)
        if not sender or sender=="__host__": return
        cur=lobby.turn_order[lobby.current_turn_idx] if lobby.current_turn_idx<len(lobby.turn_order) else None
        if sender!=cur: await send_err(ws,"Сейчас не ваш ход!"); return
        lobby.turns_done.add(sender)
        if phase_complete(lobby):
            if lobby.discussion_phase==0: lobby.first_phase_done=True
            advance_phase(lobby)
        else:
            next_active_turn(lobby)
        await broadcast(lobby)

    elif action=="reveal_card":
        field=msg.get("field","")
        if code not in lobbies: return
        lobby=lobbies[code]
        sender=lobby.connections.get(ws)
        if not sender or sender=="__host__": return
        if field not in CARD_FIELDS: return
        if lobby.discussion_phase==0 and field!="profession":
            await send_err(ws,"В первой фазе раскрывайте только Профессию!"); return
        if lobby.players[sender]["revealed"].get(field):
            await send_err(ws,"Уже раскрыто!"); return
        lobby.players[sender]["revealed"][field]=True
        log.info(f"{code}: {sender} раскрыл {field}")
        await broadcast(lobby)

    elif action=="reveal_secret":
        if code not in lobbies: return
        lobby=lobbies[code]
        sender=lobby.connections.get(ws)
        if not sender or sender=="__host__": return
        if lobby.discussion_phase==0: await send_err(ws,"Секрет нельзя в первой фазе!"); return
        lobby.players[sender]["secret_revealed"]=True
        notif=json.dumps({"type":"secret_revealed","name":sender,"secret":lobby.players[sender]["secret"]},ensure_ascii=False)
        for ws2 in list(lobby.connections):
            try: await ws2.send(notif)
            except: pass
        await broadcast(lobby)

    elif action=="get_boost":
        btype=msg.get("boost_type","self")
        if code not in lobbies: return
        lobby=lobbies[code]
        sender=lobby.connections.get(ws)
        if not sender or sender=="__host__": return
        card=lobby.players[sender]
        if btype=="self":
            if card["boost_self"] is not None: await send_err(ws,"Уже есть личный буст!"); return
            card["boost_self"]=pick(BOOSTS_SELF_P)
            log.info(f"{code}: {sender} получил буст: {card['boost_self']['name']}")
        else:
            if card["boost_group"] is not None: await send_err(ws,"Уже есть групповой буст!"); return
            card["boost_group"]=pick(BOOSTS_GROUP_P)
            log.info(f"{code}: {sender} получил групп.буст: {card['boost_group']['name']}")
        await broadcast(lobby)

    elif action=="activate_boost":
        btype=msg.get("boost_type","self")
        if code not in lobbies: return
        lobby=lobbies[code]
        sender=lobby.connections.get(ws)
        if not sender or sender=="__host__": return
        cur=lobby.turn_order[lobby.current_turn_idx] if lobby.current_turn_idx<len(lobby.turn_order) else None
        if sender!=cur: await send_err(ws,"Бусты только в свой ход!"); return
        card=lobby.players[sender]
        if btype=="self":
            if not card["boost_self"] or card["boost_self_used"]: await send_err(ws,"Личный буст недоступен!"); return
            card["boost_self_used"]=True; boost=card["boost_self"]; apply_boost_self(lobby,sender,boost)
        else:
            if not card["boost_group"] or card["boost_group_used"]: await send_err(ws,"Групповой буст недоступен!"); return
            card["boost_group_used"]=True; boost=card["boost_group"]; apply_boost_group(lobby,sender,boost)
        log.info(f"{code}: {sender} активировал {boost['name']}")
        await broadcast(lobby)
        notif=json.dumps({"type":"boost_activated","activator":sender,"boost_type":btype,"boost_name":boost["name"],"boost_desc":boost["desc"]},ensure_ascii=False)
        for ws2 in list(lobby.connections):
            try: await ws2.send(notif)
            except: pass

    elif action=="player_vote":
        target=msg.get("target","")
        if code not in lobbies: return
        lobby=lobbies[code]
        sender=lobby.connections.get(ws)
        if not sender or sender=="__host__": return
        if target not in lobby.players or lobby.players[target]["eliminated"]: await send_err(ws,"Цель не найдена!"); return
        lobby.votes[sender]=target
        log.info(f"{code}: {sender} -> {target}")
        active=lobby.active_players()
        if all(p in lobby.votes for p in active):
            if lobby.vote_task: lobby.vote_task.cancel()
            lobby.vote_task=asyncio.create_task(finish_vote_after(lobby,5))
        await broadcast(lobby)

    elif action=="host_eliminate":
        target=msg.get("target","")
        if code not in lobbies: return
        lobby=lobbies[code]
        if lobby.connections.get(ws)!="__host__": await send_err(ws,"Только хост!"); return
        await eliminate(lobby,target); await broadcast(lobby)

    elif action=="start_vote_timer":
        # Хост запускает таймер голосования вручную
        if code not in lobbies: return
        lobby=lobbies[code]
        if lobby.connections.get(ws)!="__host__": return
        delay=int(msg.get("seconds",120))
        if lobby.vote_task: lobby.vote_task.cancel()
        lobby.vote_task=asyncio.create_task(finish_vote_after(lobby,delay))

    elif action=="ping":
        await ws.send(json.dumps({"type":"pong"}))

async def handler(ws):
    log.info(f"Подключение: {ws.remote_address}")
    try:
        async for raw in ws:
            await handle_message(ws, raw)
    except websockets.exceptions.ConnectionClosedError:
        pass
    finally:
        for code, lobby in list(lobbies.items()):
            if ws in lobby.connections:
                name=lobby.connections.pop(ws)
                if name=="__host__": log.info(f"Хост отключился от {code}")
                else:
                    log.info(f"Игрок {name} отключился от {code}")
                    await broadcast(lobby)
                break
        log.info(f"Отключение: {ws.remote_address}")

async def main():
    port=int(os.environ.get("PORT",8765))
    log.info(f"Сервер запущен на 0.0.0.0:{port}")
    async with websockets.serve(
        handler, "0.0.0.0", port,
        ping_interval=20,
        ping_timeout=60,
        close_timeout=10,
    ):
        await asyncio.Future()

if __name__=="__main__":
    asyncio.run(main())

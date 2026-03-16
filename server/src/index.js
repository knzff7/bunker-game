import express from "express";
import { createServer } from "http";
import { Server } from "socket.io";
import cors from "cors";

const app = express();
app.use(cors());
app.use(express.json());

const httpServer = createServer(app);
const io = new Server(httpServer, {
  cors: { origin: "*", methods: ["GET", "POST"] },
});

function genCode() {
  return Math.random().toString(36).substring(2, 6).toUpperCase();
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

const rooms = new Map();


function createRoom(hostSocketId, hostName) {
  const code = genCode();
  const room = {
    code,
    host: hostSocketId,
    hostIsPlayer: true,
    maxPlayers: 6,
    bunkerSlots: 3,
    bots: 0,
    phase: "lobby",
    discussionPhase: 1,
    votingPending: false,
    players: [],
    cards: [],
    pickQueue: [],
    turnQueue: [],
    currentTurnIndex: 0,
    votes: {},
    votingOpen: false,
    votingTimer: null,
    disaster: null,
    bunkerItems: null,
    exiled: [],
  };
  addPlayer(room, hostSocketId, hostName, true);
  rooms.set(code, room);
  return room;
}

function addPlayer(room, socketId, name, isHost = false) {
  room.players.push({
    id: socketId,
    name,
    isHost,
    isBot: false,
    cardId: null,
    traits: null,
    revealed: [],
  });
}

function addBot(room) {
  const botId = "bot_" + Math.random().toString(36).slice(2, 8);
  const botNames = ["Артём","Виктор","Дмитрий","Сергей","Алексей","Николай","Андрей","Михаил","Игорь","Павел","Елена","Ольга","Наталья","Татьяна","Ирина","Марина","Анна","Светлана","Юлия","Екатерина"];
  const name = botNames[Math.floor(Math.random() * botNames.length)];
  room.players.push({
    id: botId,
    name,
    isHost: false,
    isBot: true,
    cardId: null,
    traits: null,
    revealed: [],
  });
}

function roomPublic(room) {
  return {
    code: room.code,
    host: room.host,
    hostIsPlayer: room.hostIsPlayer,
    maxPlayers: room.maxPlayers,
    bunkerSlots: room.bunkerSlots,
    bots: room.bots,
    phase: room.phase,
    discussionPhase: room.discussionPhase,
    players: room.players.map(p => ({
      id: p.id,
      name: p.name,
      isHost: p.isHost,
      isBot: p.isBot,
      cardId: p.cardId,
      revealed: p.revealed,
      revealedThisPhase: p.revealedThisPhase || 0,
      specialUsed:      p.specialUsed      || false,
      specialSelfUsed:  p.specialSelfUsed  || false,
      specialGroupUsed: p.specialGroupUsed || false,
      revealedTraits: p.traits
        ? Object.fromEntries(
            Object.entries(p.traits).filter(([k]) => p.revealed.includes(k))
          )
        : {},
    })),
    cards: room.cards.map(c => ({
      id: c.id,
      picked: c.picked,
      pickedBy: c.pickedBy,
      pickedByName: c.pickedByName,
      // traits intentionally omitted from public broadcast
    })),
    pickQueue: room.pickQueue,
    currentTurnIndex: room.currentTurnIndex,
    turnQueue: room.turnQueue,
    votingOpen: room.votingOpen,
    votingPending: room.votingPending || false,
    disaster: room.disaster,
    bunkerItems: room.bunkerItems,
    exiled: room.exiled.map(p => ({
      id: p.id,
      name: p.name,
      isBot: p.isBot,
      traits: p.traits,
      revealed: p.traits ? Object.keys(p.traits) : [],
      revealedTraits: p.traits || {},
    })),
  };
}

function broadcastRoom(room) {
  io.to(room.code).emit("room:update", roomPublic(room));
  for (const p of room.players) {
    if (!p.isBot && p.traits) {
      io.to(p.id).emit("player:traits", p.traits);
    }
  }
  const botTraits = {};
  for (const p of room.players) {
    if (p.isBot && p.traits) botTraits[p.id] = p.traits;
  }
  if (Object.keys(botTraits).length > 0) {
    io.to(room.host).emit("bot:traits", botTraits);
  }
}

function startVoting(room) {
  room.votingOpen = true;
  room.votes = {};
  broadcastRoom(room);
  io.to(room.code).emit("voting:start", { timeMs: 120000 });
  room.votingTimer = setTimeout(() => endVoting(room), 120000);
}

function endVoting(room) {
  if (room.votingTimer) { clearTimeout(room.votingTimer); room.votingTimer = null; }
  room.votingOpen = false;

  const tally = {};
  for (const targetId of Object.values(room.votes)) {
    tally[targetId] = (tally[targetId] || 0) + 1;
  }
  const sorted = Object.entries(tally).sort((a, b) => b[1] - a[1]);

  if (sorted.length === 0) {
    io.to(room.code).emit("voting:result", { tie: true, tally });
    broadcastRoom(room);
    return;
  }

  const maxVotes = sorted[0][1];
  const leaders = sorted.filter(([, v]) => v === maxVotes).map(([id]) => id);

  if (leaders.length > 1) {
    io.to(room.code).emit("voting:tie", { tally, timeMs: 60000 });
    room.votingOpen = true;
    room.votes = {};
    broadcastRoom(room);
    room.votingTimer = setTimeout(() => endVotingFinal(room, tally), 60000);
  } else {
    exilePlayer(room, leaders[0], tally);
  }
}

function endVotingFinal(room, prevTally) {
  if (room.votingTimer) { clearTimeout(room.votingTimer); room.votingTimer = null; }
  room.votingOpen = false;
  const tally = { ...prevTally };
  for (const targetId of Object.values(room.votes)) {
    tally[targetId] = (tally[targetId] || 0) + 1;
  }
  const sorted = Object.entries(tally).sort((a, b) => b[1] - a[1]);
  exilePlayer(room, sorted[0]?.[0], tally);
}

function exilePlayer(room, playerId, tally) {
  if (!playerId) { broadcastRoom(room); return; }
  const idx = room.players.findIndex(p => p.id === playerId);
  if (idx !== -1) {
    const [exiled] = room.players.splice(idx, 1);
    room.exiled.push(exiled);
  }
  // Убираем изгнанного из очереди ходов
  room.turnQueue = room.turnQueue.filter(id => id !== playerId);
  // Корректируем индекс чтобы не выйти за пределы
  if (room.currentTurnIndex >= room.turnQueue.length) {
    room.currentTurnIndex = 0;
  }
  io.to(room.code).emit("voting:result", { exiledId: playerId, tally });

  // Если после изгнания осталось <= мест в бункере — сразу финал
  if (room.players.length <= room.bunkerSlots) {
    room.phase = "final";
    for (const p of [...room.players, ...room.exiled]) {
      if (p.traits) p.revealed = Object.keys(p.traits);
    }
    broadcastRoom(room);
    return;
  }

  broadcastRoom(room);
}

// Продвигает очередь, пропуская игроков которых уже нет в комнате
function advanceTurn(room) {
  if (room.turnQueue.length === 0) return;
  room.currentTurnIndex++;
  if (room.currentTurnIndex >= room.turnQueue.length) {
    room.currentTurnIndex = 0;
  }
  // Пропускаем тех кого уже нет среди живых
  let safety = 0;
  while (safety++ < room.turnQueue.length) {
    const id = room.turnQueue[room.currentTurnIndex];
    const alive = room.players.find(p => p.id === id);
    if (alive) break;
    room.currentTurnIndex++;
    if (room.currentTurnIndex >= room.turnQueue.length) room.currentTurnIndex = 0;
  }
}

function startDiscussion(room) {
  room.phase = "discussion";
  room.discussionPhase = 1;
  room.turnQueue = shuffle(room.players.map(p => p.id));
  room.currentTurnIndex = 0;
  // Сбрасываем счётчики раскрытий
  for (const p of room.players) { p.revealedThisPhase = 0; }
  broadcastRoom(room);
}

io.on("connection", socket => {
  console.log("connect", socket.id);

  socket.on("lobby:list", (cb) => {
    const list = [];
    for (const [code, room] of rooms.entries()) {
      if (room.phase === "lobby" || room.phase === "discussion" || room.phase === "picking") {
        const host = room.players.find(p => p.id === room.host);
        list.push({
          code,
          hostName: host?.name || "Ведущий",
          players: room.players.length,
          maxPlayers: room.maxPlayers,
          phase: room.phase,
          bots: room.players.filter(p => p.isBot).length,
        });
      }
    }
    cb?.(list);
  });

  socket.on("lobby:create", ({ name }, cb) => {
    const room = createRoom(socket.id, name || "Хост");
    socket.join(room.code);
    cb?.({ ok: true, code: room.code, room: roomPublic(room) });
  });

  socket.on("lobby:join", ({ code, name }, cb) => {
    const room = rooms.get(code?.toUpperCase());
    if (!room) return cb?.({ ok: false, error: "Комната не найдена" });

    // В лобби — обычное подключение
    if (room.phase === "lobby") {
      if (room.players.filter(p => !p.isBot).length >= room.maxPlayers)
        return cb?.({ ok: false, error: "Комната заполнена" });
      addPlayer(room, socket.id, name || "Игрок");
      socket.join(room.code);
      cb?.({ ok: true, code: room.code, room: roomPublic(room) });
      broadcastRoom(room);
      return;
    }

    // В активной игре — только до 3й фазы включительно
    if (room.phase === "discussion" && room.discussionPhase <= 3) {
      // Создаём игрока и назначаем ему карточку из оставшихся
      const availableCard = room.cards?.find(c => !c.picked);
      if (!availableCard) return cb?.({ ok: false, error: "Нет свободных карточек" });

      availableCard.picked = true;
      availableCard.pickedBy = socket.id;
      availableCard.pickedByName = name || "Игрок";

      const newPlayer = {
        id: socket.id,
        name: name || "Игрок",
        isBot: false,
        cardId: availableCard.id,
        traits: availableCard.traits || null,
        specialSelf:  availableCard.specialSelf  || null,
        specialGroup: availableCard.specialGroup || null,
        specialSelfUsed: false,
        specialGroupUsed: false,
        specialUsed: false,
        // Автоматически раскрываем карточки согласно текущей фазе
        // Фаза 1 = 1 карточка, фаза 2 = 2 карточки и т.д.
        revealed: [],
        revealedThisPhase: 1, // уже "сходил" в текущей фазе
      };

      // Раскрываем карточки за прошедшие фазы
      const keysToReveal = ["profession","biology","health","phobia","hobby","fact1","fact2","baggage"];
      const phasesCompleted = room.discussionPhase - 1; // сколько фаз уже прошло
      for (let i = 0; i < Math.min(phasesCompleted, keysToReveal.length); i++) {
        newPlayer.revealed.push(keysToReveal[i]);
      }

      room.players.push(newPlayer);
      // Добавляем в конец очереди ходов
      room.turnQueue.push(socket.id);

      socket.join(code.toUpperCase());
      cb?.({ ok: true, code: code.toUpperCase(), room: roomPublic(room) });

      // Отправляем traits новому игроку
      if (newPlayer.traits) {
        socket.emit("player:traits", {
          ...newPlayer.traits,
          _specialSelf:  newPlayer.specialSelf,
          _specialGroup: newPlayer.specialGroup,
        });
      }

      broadcastRoom(room);
      return;
    }

    // После 3й фазы — нельзя войти
    if (room.phase === "discussion" && room.discussionPhase > 3) {
      return cb?.({ ok: false, error: "Игра уже прошла 3 фазу, вход закрыт" });
    }

    return cb?.({ ok: false, error: "Нельзя войти в игру сейчас" });
  });

  socket.on("lobby:rejoin", ({ code, name }, cb) => {
    const room = rooms.get(code?.toUpperCase());
    if (!room) return cb?.({ ok: false, error: "Комната не найдена" });

    const existingPlayer = room.players.find(p => p.name === name && !p.isBot)
      || room.exiled?.find(p => p.name === name && !p.isBot);

    if (!existingPlayer) return cb?.({ ok: false, error: "Игрок не найден" });

    const oldId = existingPlayer.id;
    existingPlayer.id = socket.id;
    if (room.host === oldId) room.host = socket.id;

    room.turnQueue = room.turnQueue.map(id => id === oldId ? socket.id : id);
    if (room.pickQueue) room.pickQueue = room.pickQueue.map(id => id === oldId ? socket.id : id);

    if (room.votes?.[oldId] !== undefined) {
      room.votes[socket.id] = room.votes[oldId];
      delete room.votes[oldId];
    }
    for (const [voterId, targetId] of Object.entries(room.votes || {})) {
      if (targetId === oldId) room.votes[voterId] = socket.id;
    }

    socket.join(code.toUpperCase());
    cb?.({ ok: true, code: code.toUpperCase(), room: roomPublic(room) });

    if (existingPlayer.traits) {
      socket.emit("player:traits", {
        ...existingPlayer.traits,
        _specialSelf:  existingPlayer.specialSelf,
        _specialGroup: existingPlayer.specialGroup,
      });
    }

    broadcastRoom(room);
  });

  socket.on("lobby:settings", ({ code, settings }) => {
    const room = rooms.get(code);
    if (!room || room.host !== socket.id) return;
    if (settings.maxPlayers !== undefined) room.maxPlayers = Math.max(2, Math.min(12, settings.maxPlayers));
    if (settings.bunkerSlots !== undefined) room.bunkerSlots = Math.max(1, Math.min(room.maxPlayers - 1, settings.bunkerSlots));
    if (settings.hostIsPlayer !== undefined) room.hostIsPlayer = settings.hostIsPlayer;
    broadcastRoom(room);
  });

  socket.on("lobby:addBot", ({ code }) => {
    const room = rooms.get(code);
    if (!room || room.host !== socket.id) return;
    if (room.players.length >= room.maxPlayers) return;
    addBot(room);
    room.bots++;
    broadcastRoom(room);
  });

  socket.on("lobby:removeBot", ({ code }) => {
    const room = rooms.get(code);
    if (!room || room.host !== socket.id) return;
    const idx = room.players.findLastIndex(p => p.isBot);
    if (idx !== -1) { room.players.splice(idx, 1); room.bots = Math.max(0, room.bots - 1); }
    broadcastRoom(room);
  });

  socket.on("game:start", ({ code, cards, disaster, bunkerItems }) => {
    const room = rooms.get(code);
    if (!room || room.host !== socket.id) return;
    room.phase = "picking";
    room.cards = cards;
    room.disaster = disaster;
    room.bunkerItems = bunkerItems;
    room.pickQueue = shuffle(room.players.map(p => p.id));
    room.currentTurnIndex = 0;

    // Назначаем карточки ВСЕМ игрокам (и ботам и людям) сразу при старте
    const availableAtStart = [...room.cards];
    for (const p of room.players) {
      const pool = availableAtStart.filter(c => !c.picked);
      if (pool.length === 0) break;
      const bc = pool[Math.floor(Math.random() * pool.length)];
      bc.picked = true;
      bc.pickedBy = p.id;
      bc.pickedByName = p.name;
      p.cardId = bc.id;
      p.traits = bc.traits || null;
      // Две особые карточки — только людям, не ботам
      p.specialSelf  = p.isBot ? null : (bc.specialSelf  || null);
      p.specialGroup = p.isBot ? null : (bc.specialGroup || null);
      p.specialSelfUsed  = false;
      p.specialGroupUsed = false;
      p.specialUsed = false;
      p.revealed = [];
    }

    // Убираем всех из pickQueue (карточки уже розданы)
    // Но оставляем очередь для "выбора на столе" — это теперь просто анимация подтверждения
    room.pickQueue = room.pickQueue.filter(id => !room.players.find(p => p.id === id && p.isBot));

    broadcastRoom(room);

    // Отправляем каждому человеку его traits сразу
    for (const p of room.players) {
      if (!p.isBot && p.traits) {
        io.to(p.id).emit("player:traits", {
          ...p.traits,
          _specialSelf:  p.specialSelf,
          _specialGroup: p.specialGroup,
        });
      }
    }
    // Хосту — traits всех ботов
    const botTraits = {};
    for (const p of room.players) {
      if (p.isBot && p.traits) botTraits[p.id] = p.traits;
    }
    if (Object.keys(botTraits).length > 0) {
      io.to(room.host).emit("bot:traits", botTraits);
    }

    // Сразу переходим в discussion — экран выбора карточек убран
    startDiscussion(room);
  });

  socket.on("game:pickCard", ({ code, cardId }) => {
    const room = rooms.get(code);
    if (!room || room.phase !== "picking") return;
    const currentTurn = room.pickQueue[room.currentTurnIndex];
    if (currentTurn !== socket.id) return;

    // Карточка уже назначена при старте — просто двигаем очередь
    room.currentTurnIndex++;
    broadcastRoom(room);
    // Переотправляем traits на случай если потерялись
    const player = room.players.find(p => p.id === socket.id);
    if (player?.traits) socket.emit("player:traits", player.traits);
  });

  socket.on("game:reveal", ({ code, traitKey, targetId }) => {
    const room = rooms.get(code);
    if (!room || room.phase !== "discussion") return;
    const currentTurn = room.turnQueue[room.currentTurnIndex];
    const currentPlayer = room.players.find(p => p.id === currentTurn);
    const isMyTurn = currentTurn === socket.id;
    const isBotTurn = currentPlayer?.isBot && room.host === socket.id && currentTurn === targetId;
    if (!isMyTurn && !isBotTurn) return;
    const player = room.players.find(p => p.id === currentTurn);
    if (!player || player.revealed.includes(traitKey)) return;

    // Фаза 1 — только профессия
    if (room.discussionPhase === 1 && traitKey !== "profession") return;

    // Каждый игрок может раскрыть максимум 1 карточку за фазу
    if (!player.revealedThisPhase) player.revealedThisPhase = 0;
    if (player.revealedThisPhase >= 1) return;

    player.revealed.push(traitKey);
    player.revealedThisPhase++;
    advanceTurn(room);
    broadcastRoom(room);
  });

  socket.on("game:skipTurn", ({ code, targetId }) => {
    const room = rooms.get(code);
    if (!room || room.phase !== "discussion") return;
    const currentTurn = room.turnQueue[room.currentTurnIndex];
    const currentPlayer = room.players.find(p => p.id === currentTurn);
    const isMyTurn = currentTurn === socket.id;
    const isBotTurn = currentPlayer?.isBot && room.host === socket.id;
    if (!isMyTurn && !isBotTurn) return;
    advanceTurn(room);
    broadcastRoom(room);
  });

  socket.on("game:botVote", ({ code, botId, targetId }) => {
    const room = rooms.get(code);
    if (!room || !room.votingOpen || room.host !== socket.id) return;
    const bot = room.players.find(p => p.id === botId && p.isBot);
    if (!bot) return;
    room.votes[botId] = targetId;
    // Никогда не заканчиваем досрочно — всегда ждём таймер
    io.to(room.code).emit("voting:progress", {
      count: Object.keys(room.votes).length,
      total: room.players.length,
    });
  });

  socket.on("game:nextPhase", ({ code }) => {
    const room = rooms.get(code);
    if (!room || room.host !== socket.id) return;

    if (room.phase === "picking") {
      startDiscussion(room);
      return;
    }

    if (room.phase === "discussion") {
      // Блокируем если не все игроки раскрыли карточку в этой фазе
      const notReady = room.players.filter(p => (p.revealedThisPhase || 0) < 1);
      if (notReady.length > 0) return;

      room.discussionPhase++;
      // Очередь НЕ пересоздаём — она остаётся с начала игры
      // Просто сбрасываем индекс на начало
      room.currentTurnIndex = 0;
      for (const p of room.players) { p.revealedThisPhase = 0; }

      const phase = room.discussionPhase;
      const alive = room.players.length;
      const slots = room.bunkerSlots;

      // Финал после фазы 8 (все фазы пройдены)
      if (phase > 7) {
        // Если ещё остались лишние — ожидаем старта голосования
        if (alive > slots) {
          room.votingPending = true;
          broadcastRoom(room);
          return;
        }
        room.phase = "final";
        for (const p of [...room.players, ...room.exiled]) {
          if (p.traits) p.revealed = Object.keys(p.traits);
        }
        broadcastRoom(room);
        return;
      }

      // Финал — если игроков ровно столько сколько мест (или меньше)
      if (alive <= slots) {
        room.phase = "final";
        for (const p of [...room.players, ...room.exiled]) {
          if (p.traits) p.revealed = Object.keys(p.traits);
        }
        broadcastRoom(room);
        return;
      }

      // Обязательное голосование в конце фазы 3
      if (phase === 4) {
        room.votingPending = true;
        broadcastRoom(room);
        return;
      }

      // Обязательное голосование в конце фазы 7
      if (phase === 8) {
        room.votingPending = true;
        broadcastRoom(room);
        return;
      }

      // Доп. голосования в фазах 4-6:
      if (phase >= 5 && phase <= 7) {
        const targetBeforeFinal = slots + 1;
        const kicksNeeded = alive - targetBeforeFinal;
        const phasesLeft = 8 - phase;
        if (kicksNeeded > 0 && kicksNeeded >= phasesLeft) {
          room.votingPending = true;
          broadcastRoom(room);
          return;
        }
      }

      broadcastRoom(room);
    }
  });

  socket.on("game:startVoting", ({ code }) => {
    const room = rooms.get(code);
    if (!room || room.host !== socket.id || !room.votingPending) return;
    room.votingPending = false;
    startVoting(room);
  });

  socket.on("game:endVoting", ({ code }) => {
    const room = rooms.get(code);
    if (!room || !room.votingOpen || room.host !== socket.id) return;
    endVoting(room);
  });

  socket.on("game:vote", ({ code, targetId }) => {
    const room = rooms.get(code);
    if (!room || !room.votingOpen) return;
    const voter = room.players.find(p => p.id === socket.id);
    if (!voter) return;
    room.votes[socket.id] = targetId;
    // Никогда не заканчиваем досрочно — всегда ждём таймер
    const humanPlayers = room.players.filter(p => !p.isBot);
    io.to(room.code).emit("voting:progress", {
      count: Object.keys(room.votes).filter(id => !room.players.find(p=>p.id===id&&p.isBot)).length,
      total: humanPlayers.length,
    });
  });

  socket.on("lobby:close", ({ code }) => {
    const room = rooms.get(code);
    if (!room || room.host !== socket.id) return;
    io.to(code).emit("lobby:closed");
    rooms.delete(code);
  });

  socket.on("game:useSpecial", ({ code, effect, targetId }, cb) => {
    const room = rooms.get(code);
    if (!room || room.phase !== "discussion") return cb?.({ ok: false });
    const currentTurn = room.turnQueue[room.currentTurnIndex];
    if (currentTurn !== socket.id) return cb?.({ ok: false, error: "Не ваш ход" });
    const player = room.players.find(p => p.id === socket.id);
    if (!player) return cb?.({ ok: false });

    // Определяем тип карточки
    const isSelf  = player.specialSelf?.effect  === effect;
    const isGroup = player.specialGroup?.effect === effect;
    if (!isSelf && !isGroup) return cb?.({ ok: false, error: "Нет такой карточки" });
    if (isSelf  && player.specialSelfUsed)  return cb?.({ ok: false, error: "Уже использована" });
    if (isGroup && player.specialGroupUsed) return cb?.({ ok: false, error: "Уже использована" });

    const result = applySpecialEffect(room, socket.id, effect, targetId);
    if (!result.ok) return cb?.(result);

    if (isSelf)  player.specialSelfUsed  = true;
    if (isGroup) player.specialGroupUsed = true;
    player.specialUsed = player.specialSelfUsed && player.specialGroupUsed;

    broadcastRoom(room);
    if (player.traits) {
      io.to(player.id).emit("player:traits", {
        ...player.traits,
        _specialSelf:  player.specialSelf,
        _specialGroup: player.specialGroup,
      });
    }
    cb?.({ ok: true, msg: result.msg });
  });

  socket.on("disconnect", () => {
    for (const [code, room] of rooms.entries()) {
      const idx = room.players.findIndex(p => p.id === socket.id);
      if (idx !== -1) {
        if (room.host === socket.id) {
          io.to(code).emit("lobby:closed");
          if (room.votingTimer) clearTimeout(room.votingTimer);
          rooms.delete(code);
        } else {
          room.players.splice(idx, 1);
          broadcastRoom(room);
        }
        break;
      }
    }
  });
});

// ── Прокси для Claude API (обход CORS) ──
app.post("/api/narrative", async (req, res) => {
  try {
    const response = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": process.env.ANTHROPIC_API_KEY || "",
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify(req.body),
    });
    const data = await response.json();
    res.json(data);
  } catch (err) {
    console.error("[narrative]", err.message);
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3001;
httpServer.listen(PORT, () => console.log(`Bunker server :${PORT}`));

// ── Обработка особых карточек ──
function applySpecialEffect(room, playerId, effect, targetId) {
  const player = room.players.find(p => p.id === playerId);
  if (!player) return { ok: false };

  const others = room.players.filter(p => p.id !== playerId && !p.isBot);
  const allPlayers = room.players.filter(p => !p.isBot);

  function randTrait(arr) {
    return arr[Math.floor(Math.random() * arr.length)];
  }

  switch (effect) {
    case "reroll_health": {
      if (!player.revealed.includes("health")) return { ok: false, error: "Сначала раскройте карточку Здоровье" };
      const pool = room.cards.map(c => c.traits?.health).filter(Boolean);
      player.traits.health = randTrait(pool);
      return { ok: true, msg: "Здоровье изменено" };
    }
    case "reroll_profession": {
      if (!player.revealed.includes("profession")) return { ok: false, error: "Сначала раскройте карточку Профессия" };
      const pool = room.cards.map(c => c.traits?.profession).filter(Boolean);
      player.traits.profession = randTrait(pool);
      return { ok: true, msg: "Профессия изменена" };
    }
    case "reroll_phobia": {
      if (!player.revealed.includes("phobia")) return { ok: false, error: "Сначала раскройте карточку Фобия" };
      const pool = room.cards.map(c => c.traits?.phobia).filter(Boolean);
      player.traits.phobia = randTrait(pool);
      return { ok: true, msg: "Фобия изменена" };
    }
    case "reroll_baggage": {
      if (!player.revealed.includes("baggage")) return { ok: false, error: "Сначала раскройте карточку Багаж" };
      const pool = room.cards.map(c => c.traits?.baggage).filter(Boolean);
      player.traits.baggage = randTrait(pool);
      return { ok: true, msg: "Багаж заменён" };
    }
    case "reroll_hobby": {
      if (!player.revealed.includes("hobby")) return { ok: false, error: "Сначала раскройте карточку Хобби" };
      const pool = room.cards.map(c => c.traits?.hobby).filter(Boolean);
      player.traits.hobby = randTrait(pool);
      return { ok: true, msg: "Хобби изменено" };
    }
    case "reroll_fact1": {
      if (!player.revealed.includes("fact1")) return { ok: false, error: "Сначала раскройте карточку Факт I" };
      const pool = room.cards.map(c => c.traits?.fact1).filter(Boolean);
      player.traits.fact1 = randTrait(pool);
      return { ok: true, msg: "Навык изменён" };
    }
    case "reroll_fact2": {
      if (!player.revealed.includes("fact2")) return { ok: false, error: "Сначала раскройте карточку Факт II" };
      const pool = room.cards.map(c => c.traits?.fact2).filter(Boolean);
      player.traits.fact2 = randTrait(pool);
      return { ok: true, msg: "Секрет изменён" };
    }
    case "shuffle_health_others": {
      // Перемешиваем здоровье только тех у кого оно раскрыто
      const targets = others.filter(p => p.revealed.includes("health") && p.traits?.health);
      if (targets.length < 1) return { ok: false, error: "Ни у кого не раскрыто Здоровье" };
      const pool = targets.map(p => p.traits.health);
      const shuffled = [...pool].sort(() => Math.random() - 0.5);
      targets.forEach((p, i) => { p.traits.health = shuffled[i]; });
      return { ok: true, msg: `Здоровье перемешано у ${targets.length} игроков` };
    }
    case "shuffle_profession_others": {
      // Перемешиваем профессии только тех у кого раскрыта профессия
      const targets = others.filter(p => p.revealed.includes("profession") && p.traits?.profession);
      if (targets.length < 1) return { ok: false, error: "Ни у кого не раскрыта Профессия" };
      const pool = targets.map(p => p.traits.profession);
      const shuffled = [...pool].sort(() => Math.random() - 0.5);
      targets.forEach((p, i) => { p.traits.profession = shuffled[i]; });
      return { ok: true, msg: `Профессии перемешаны у ${targets.length} игроков` };
    }
    case "shuffle_hobby_others": {
      // Перемешиваем хобби только тех у кого раскрыто хобби
      const targets = others.filter(p => p.revealed.includes("hobby") && p.traits?.hobby);
      if (targets.length < 1) return { ok: false, error: "Ни у кого не раскрыто Хобби" };
      const pool = targets.map(p => p.traits.hobby);
      const shuffled = [...pool].sort(() => Math.random() - 0.5);
      targets.forEach((p, i) => { p.traits.hobby = shuffled[i]; });
      return { ok: true, msg: `Хобби перемешано у ${targets.length} игроков` };
    }
    case "reveal_health_all": {
      // Временное раскрытие — только через событие, не в revealed
      return { ok: true, msg: "Здоровье всех раскрыто", temporary: true,
        tempData: { type: "reveal_all_health", players: room.players.map(p => ({ id: p.id, name: p.name, health: p.traits?.health })) }
      };
    }
    case "reveal_random_other": {
      const target = targetId ? room.players.find(p => p.id === targetId)
        : others[Math.floor(Math.random() * others.length)];
      if (!target) return { ok: false, error: "Нет цели" };
      const keys = ["profession","biology","health","phobia","hobby","fact1","fact2","baggage"];
      const hidden = keys.filter(k => !target.revealed.includes(k));
      if (hidden.length === 0) return { ok: false, error: "Все карточки уже раскрыты" };
      const key = hidden[Math.floor(Math.random() * hidden.length)];
      const traitVal = target.traits?.[key];
      // Временное раскрытие — только для использующего игрока, не навсегда
      return { ok: true, msg: `Временно раскрыта карточка у ${target.name}`, temporary: true,
        tempData: { type: "reveal_single", targetName: target.name, key, trait: traitVal }
      };
    }
    case "swap_bag_neighbor": {
      const tgt = targetId ? room.players.find(p => p.id === targetId)
        : room.players[(room.players.indexOf(player) + 1) % room.players.length];
      if (!tgt || tgt.id === player.id) return { ok: false, error: "Нет цели" };
      if (!player.revealed.includes("baggage")) return { ok: false, error: "Сначала раскройте свой Багаж" };
      if (!tgt.revealed.includes("baggage")) return { ok: false, error: `У ${tgt.name} ещё не раскрыт Багаж` };
      const tmp = player.traits.baggage;
      player.traits.baggage = tgt.traits?.baggage || tmp;
      if (tgt.traits) tgt.traits.baggage = tmp;
      return { ok: true, msg: `Багаж обменян с ${tgt.name}` };
    }
    case "copy_trait": {
      const target = targetId ? room.players.find(p => p.id === targetId) : null;
      if (!target || !target.traits) return { ok: false, error: "Нет цели" };
      const keys = ["profession","biology","health","phobia","hobby","fact1","fact2","baggage"];
      const revealedKeys = keys.filter(k => target.revealed.includes(k));
      if (revealedKeys.length === 0) return { ok: false, error: "Нет раскрытых карточек" };
      const key = revealedKeys[Math.floor(Math.random() * revealedKeys.length)];
      player.traits[key] = target.traits[key];
      return { ok: true, msg: `Скопирована характеристика у ${target.name}` };
    }
    default:
      return { ok: false, error: "Неизвестный эффект" };
  }
}

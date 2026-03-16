import { create } from 'zustand';
import { io } from 'socket.io-client';
import { professions, biologies, healths, hobbies, phobias, baggages, facts1, facts2 } from '../data/traits.js';
import { disasters, bunkerItems as bunkerItemSets } from '../data/scenarios.js';
import { specialCards } from '../data/special_cards.js';

const SERVER = import.meta.env.VITE_SERVER_URL || 'http://localhost:3001';



function pickRandom(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

function pickUnique(arr, used) {
  const available = arr.filter(x => !used.has(x.value));
  if (available.length === 0) return arr[Math.floor(Math.random() * arr.length)];
  const picked = available[Math.floor(Math.random() * available.length)];
  used.add(picked.value);
  return picked;
}

function buildCards(playerCount = 12) {
  const used = {
    profession: new Set(), biology: new Set(), health: new Set(),
    hobby: new Set(), phobia: new Set(), baggage: new Set(),
    fact1: new Set(), fact2: new Set(),
  };

  // Перемешиваем self и group карточки отдельно
  const selfCards  = specialCards.filter(c => c.type === "self") .sort(() => Math.random() - 0.5);
  const groupCards = specialCards.filter(c => c.type === "group").sort(() => Math.random() - 0.5);

  const count = Math.max(playerCount, 8);
  return Array.from({ length: count }, (_, i) => ({
    id: `card_${i}`,
    picked: false,
    pickedBy: null,
    pickedByName: null,
    // Каждому — одна personal + одна group карточка
    specialSelf:  selfCards [i % selfCards.length],
    specialGroup: groupCards[i % groupCards.length],
    traits: {
      profession: pickUnique(professions, used.profession),
      biology:    pickUnique(biologies,   used.biology),
      health:     pickUnique(healths,     used.health),
      hobby:      pickUnique(hobbies,     used.hobby),
      phobia:     pickUnique(phobias,     used.phobia),
      baggage:    pickUnique(baggages,    used.baggage),
      fact1:      pickUnique(facts1,      used.fact1),
      fact2:      pickUnique(facts2,      used.fact2),
    },
  }));
}

let _socket = null;
function getSocket() {
  if (!_socket) _socket = io(SERVER, { autoConnect: false });
  return _socket;
}

// ── Session persistence ────────────────────────────────
const SESSION_KEY = 'bunker_session';

function _saveSession(data) {
  try { localStorage.setItem(SESSION_KEY, JSON.stringify(data)); } catch {}
}

function _loadSession() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY)); } catch { return null; }
}

function _clearSession() {
  try { localStorage.removeItem(SESSION_KEY); } catch {}
}

// Определяем начальную страницу — если есть сессия, показываем "reconnecting"
function _getInitialPage() {
  const session = _loadSession();
  return session?.code && session?.name ? 'reconnecting' : 'home';
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export const useGameStore = create((set, get) => ({
  // connection
  socket: null,
  connected: false,
  page: _getInitialPage(),
  playerName: '',
  roomCode: null,

  // identity
  playerId: null,
  isHost: false,

  // room
  players: [],
  roomSettings: { maxPlayers: 6, bunkerSlots: 3, hostIsPlayer: true, bots: 0 },

  // card picking
  pickQueue: [],
  availableCards: null,
  myDossier: null,
  mySpecialSelf: null,
  mySpecialGroup: null,
  allDossiers: {},
  currentTurnIndex: 0,

  // game
  catastrophe: null,
  bunkerContents: [],
  exiledPlayers: [],
  currentPhase: 1,
  turnQueue: [],
  votingActive: false,
  votes: {},
  votingTimeLeft: 120,
  gameLog: [],
  notification: null,
  finalData: null,
  _votingInterval: null,

  setPage: (page) => set({ page }),
  setPlayerName: (name) => set({ playerName: name }),
  clearNotification: () => set({ notification: null }),
  updateRoomSettings: (s) => set({ roomSettings: s }),

  // ── Init socket & bind ALL server events ──────────────
  initSocket() {
    const s = getSocket();
    set({ socket: s });

    // Снимаем старые обработчики (защита от StrictMode)
    s.off('connect');
    s.off('disconnect');
    s.off('connect_error');
    s.off('room:update');
    s.off('player:traits');
    s.off('lobby:closed');
    s.off('voting:start');
    s.off('voting:tie');
    s.off('voting:result');
    s.off('voting:progress');
    s.off('bot:traits');

    s.on('connect', () => {
      set({ connected: true, playerId: s.id });

      // Пробуем восстановить сессию после реконнекта
      const session = _loadSession();
      if (session?.code && session?.name) {
        set({ page: 'reconnecting' });
        s.emit('lobby:rejoin', { code: session.code, name: session.name }, (res) => {
          if (res?.ok) {
            set({
              roomCode: res.code,
              isHost: res.room?.host === s.id,
              players: res.room?.players || [],
              myDossier: session.myDossier || null,
              mySpecialSelf: session.mySpecialSelf || null,
              mySpecialGroup: session.mySpecialGroup || null,
            });
          } else {
            // Комната уже не существует
            _clearSession();
            set({ page: 'home' });
          }
        });
      }
    });

    if (s.connected) {
      set({ connected: true, playerId: s.id });
    } else {
      s.connect();
    }

    s.on('disconnect', () => {
      console.log('[socket] disconnected');
      set({ connected: false });
    });

    s.on('connect_error', (err) => {
      console.error('[socket] connect error', err.message);
      set({ notification: { type: 'error', text: `Нет связи с сервером: ${err.message}` } });
    });

    s.on('room:update', (room) => {
      const myId = s.id;

      // Определяем страницу только если мы в комнате
      // (если нас нет — rejoin ещё не обработан, не трогаем страницу)
      const meInRoom = room.players.find(p => p.id === myId)
                    || room.exiled?.find(p => p.id === myId);

      let page = get().page;
      if (meInRoom || page === 'reconnecting') {
        if (room.phase === 'lobby')      page = 'lobby';
        if (room.phase === 'picking')    page = 'discussion';
        if (room.phase === 'discussion') page = 'discussion';
        if (room.phase === 'voting')     page = 'discussion';
        if (room.phase === 'final')      page = 'final';
      }

      const allDossiers = {};
      for (const p of [...room.players, ...room.exiled]) {
        allDossiers[p.id] = p.revealedTraits || {};
      }

      // Сохраняем сессию при каждом апдейте комнаты
      const { playerName, myDossier, mySpecialSelf, mySpecialGroup } = get();
      const myPlayer = room.players.find(p => p.id === myId);
      const nameToSave = playerName || myPlayer?.name;
      if (room.code && nameToSave) {
      }

      set({
        roomCode: room.code,
        players: room.players,
        isHost: room.host === myId,
        roomSettings: {
          maxPlayers: room.maxPlayers,
          bunkerSlots: room.bunkerSlots,
          hostIsPlayer: room.hostIsPlayer,
          bots: room.bots,
        },
        pickQueue: room.pickQueue || [],
        availableCards: room.cards?.length ? room.cards : get().availableCards,
        currentTurnIndex: room.currentTurnIndex ?? 0,
        turnQueue: room.turnQueue || [],
        currentPhase: room.discussionPhase || 1,
        catastrophe: room.disaster,
        bunkerContents: room.bunkerItems || [],
        exiledPlayers: room.exiled || [],
        votingActive: room.votingOpen || false,
        allDossiers,
        page,
      });
    });

    s.on('player:traits', (traits) => {
      if (traits) {
        const { _specialSelf, _specialGroup, _specialCard, ...purTraits } = traits;
        set({ myDossier: purTraits });
        if (_specialSelf)  set({ mySpecialSelf:  _specialSelf  });
        if (_specialGroup) set({ mySpecialGroup: _specialGroup });
        // legacy single card
        if (_specialCard && !_specialSelf) set({ mySpecialSelf: _specialCard });
        const { roomCode, playerName } = get();
        if (roomCode) _saveSession({
          code: roomCode, name: playerName, playerId: s.id,
          myDossier: purTraits,
          mySpecialSelf:  _specialSelf  || get().mySpecialSelf,
          mySpecialGroup: _specialGroup || get().mySpecialGroup,
        });
      }
    });

    s.on('lobby:closed', () => {
      _clearSession();
      set({ page: 'home', roomCode: null, notification: { type: 'error', text: 'Лобби закрыто' } });
    });

    s.on('voting:start', ({ timeMs }) => {
      set({ votingActive: true, votes: {}, votingTimeLeft: Math.round(timeMs / 1000) });
      get()._startCountdown(Math.round(timeMs / 1000));
    });

    s.on('voting:tie', ({ timeMs }) => {
      set({ votes: {}, votingTimeLeft: Math.round(timeMs / 1000),
        notification: { type: 'warning', text: 'Ничья! Переголосование — 60 сек' } });
      get()._startCountdown(Math.round(timeMs / 1000));
    });

    s.on('voting:result', ({ exiledId, tally, tie }) => {
      const exiledPlayer = get().players.find(p => p.id === exiledId);
      const name = exiledPlayer?.name || 'Игрок';
      set(st => ({
        votingActive: false,
        notification: exiledId
          ? { type: 'error', text: `${name} изгнан из бункера` }
          : { type: 'info', text: 'Голосование завершено' },
        gameLog: [...st.gameLog, {
          type: 'exile',
          text: exiledId ? `⚰ ${name} изгнан(а) из бункера` : '⚖ Голосование без результата',
        }],
      }));
    });

    s.on('bot:traits', (botTraits) => {
      // Merge bot full traits into allDossiers so host can see them
      set(st => {
        const allDossiers = { ...st.allDossiers };
        for (const [botId, traits] of Object.entries(botTraits)) {
          allDossiers[botId] = { ...allDossiers[botId], ...traits };
        }
        // Also store on player objects so GamePage can access them
        const players = st.players.map(p =>
          p.isBot && botTraits[p.id] ? { ...p, traits: botTraits[p.id] } : p
        );
        return { allDossiers, players };
      });
    });

    s.on('voting:progress', ({ count, total }) => {
      console.log(`[voting] ${count}/${total} проголосовали`);
    });
  },

  _startCountdown(seconds) {
    const prev = get()._votingInterval;
    if (prev) clearInterval(prev);
    set({ votingTimeLeft: seconds });
    const interval = setInterval(() => {
      const t = get().votingTimeLeft;
      if (t <= 1) { clearInterval(interval); set({ votingTimeLeft: 0 }); return; }
      set({ votingTimeLeft: t - 1 });
    }, 1000);
    set({ _votingInterval: interval });
  },

  // ── Actions ────────────────────────────────────────────
  listRooms(cb) {
    const s = getSocket();
    s.emit('lobby:list', cb);
  },

  createRoom(cb) {
    const s = getSocket();
    const { playerName } = get();
    console.log('[action] createRoom name=', playerName);
    s.emit('lobby:create', { name: playerName || 'Хост' }, (res) => {
      console.log('[action] createRoom response', res);
      if (res?.ok) {
        const room = res.room;
        set({
          roomCode: res.code, isHost: true, page: 'lobby',
          players: room?.players || [],
          roomSettings: {
            maxPlayers: room?.maxPlayers || 6,
            bunkerSlots: room?.bunkerSlots || 3,
            hostIsPlayer: room?.hostIsPlayer ?? true,
            bots: room?.bots || 0,
          },
        });
        _saveSession({ code: res.code, name: playerName || 'Хост' });
        cb?.({ success: true });
      } else {
        cb?.({ success: false, error: res?.error || 'Ошибка создания комнаты' });
      }
    });
  },

  joinRoom(code, cb) {
    const s = getSocket();
    const { playerName } = get();
    console.log('[action] joinRoom code=', code, 'name=', playerName);
    s.emit('lobby:join', { code: code.toUpperCase(), name: playerName || 'Игрок' }, (res) => {
      console.log('[action] joinRoom response', res);
      if (res?.ok) {
        const room = res.room;
        set({
          roomCode: res.code, isHost: false, page: 'lobby',
          players: room?.players || [],
          roomSettings: {
            maxPlayers: room?.maxPlayers || 6,
            bunkerSlots: room?.bunkerSlots || 3,
            hostIsPlayer: room?.hostIsPlayer ?? true,
            bots: room?.bots || 0,
          },
        });
        _saveSession({ code: res.code, name: playerName || 'Игрок' });
        cb?.({ success: true });
      } else {
        cb?.({ success: false, error: res?.error || 'Комната не найдена' });
      }
    });
  },

  updateSettings(settings) {
    const { socket, roomCode } = get();
    socket?.emit('lobby:settings', { code: roomCode, settings });
  },

  addBot() {
    const { socket, roomCode } = get();
    socket?.emit('lobby:addBot', { code: roomCode });
  },

  removeBot() {
    const { socket, roomCode } = get();
    socket?.emit('lobby:removeBot', { code: roomCode });
  },

  startGame() {
    const { socket, roomCode, players } = get();
    const cards = buildCards(players.length);
    const disaster = pickRandom(disasters);
    const bunkerSet = pickRandom(bunkerItemSets);
    set({ catastrophe: disaster, bunkerContents: bunkerSet.items });
    socket?.emit('game:start', {
      code: roomCode,
      cards,
      disaster,
      bunkerItems: bunkerSet.items,
    });
  },

  pickCard(cardId) {
    const { socket, roomCode } = get();
    // Traits уже есть в myDossier (пришли при game:start), просто подтверждаем выбор
    socket?.emit('game:pickCard', { code: roomCode, cardId });
  },

  revealTrait(traitKey, targetId) {
    const { socket, roomCode } = get();
    socket?.emit('game:reveal', { code: roomCode, traitKey, targetId });
  },

  skipTurn(targetId) {
    const { socket, roomCode } = get();
    socket?.emit('game:skipTurn', { code: roomCode, targetId });
  },

  useSpecial(effect, targetId, cb) {
    const { socket, roomCode } = get();
    socket?.emit('game:useSpecial', { code: roomCode, effect, targetId }, cb);
  },

  endVoting() {
    const { socket, roomCode } = get();
    socket?.emit('game:endVoting', { code: roomCode });
  },

  botVote(botId, targetId) {
    const { socket, roomCode } = get();
    socket?.emit('game:botVote', { code: roomCode, botId, targetId });
  },

  nextPhase() {
    const { socket, roomCode } = get();
    socket?.emit('game:nextPhase', { code: roomCode });
  },

  vote(targetId) {
    const { socket, roomCode } = get();
    socket?.emit('game:vote', { code: roomCode, targetId });
    set(st => ({ votes: { ...st.votes, [st.playerId]: targetId } }));
  },

  closeLobby() {
    const { socket, roomCode } = get();
    socket?.emit('lobby:close', { code: roomCode });
  },

  // ── Helpers ────────────────────────────────────────────
  isMyTurn() {
    const { room, playerId, currentTurnIndex, page, pickQueue, turnQueue } = get();
    const queue = page === 'card_pick' ? pickQueue : turnQueue;
    return queue[currentTurnIndex] === playerId;
  },

  getMe() {
    const { players, playerId } = get();
    return players.find(p => p.id === playerId) || null;
  },

  _buildCards() {
    // Dynamic import not possible here - use pre-imported data
    return get()._cards || [];
  },
}));

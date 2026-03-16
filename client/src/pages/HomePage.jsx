import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGameStore } from '../store/gameStore';
import './HomePage.css';

export default function HomePage() {
  const [mode, setMode] = useState(null); // null | 'create' | 'join'
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [rooms, setRooms] = useState([]);

  const { setPlayerName, createRoom, joinRoom, connected, listRooms } = useGameStore();

  useEffect(() => {
    if (!connected) return;
    const load = () => listRooms(list => setRooms(list || []));
    load();
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [connected]);

  const handleCreate = () => {
    if (!name.trim()) return setError('Введи своё имя');
    setLoading(true);
    setPlayerName(name.trim());
    createRoom((r) => {
      setLoading(false);
      if (!r.success) setError(r.error || 'Ошибка');
    });
  };

  const handleJoin = (prefillCode) => {
    const c = prefillCode || code;
    if (!name.trim()) return setError('Введи своё имя');
    if (!c.trim()) return setError('Введи код комнаты');
    setLoading(true);
    setPlayerName(name.trim());
    joinRoom(c.trim(), (r) => {
      setLoading(false);
      if (!r.success) setError(r.error || 'Ошибка');
    });
  };

  return (
    <div className="home">
      {/* Фоновая картинка с затемнением */}
      <div className="home__bg" />
      <div className="home__bg-overlay" />
      <div className="home__scanlines" />
      <div className="home__vignette" />

      {/* Content */}
      <div className="home__content">

        {/* Logo */}
        <motion.div className="home__logo-wrap"
          initial={{ opacity: 0, y: -30 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}>
          <h1 className="home__title">БУНКЕР</h1>
          <p className="home__subtitle">— выжить любой ценой —</p>
          <div className="home__status">
            <span className={`home__status-dot ${connected ? 'on' : 'off'}`} />
            {connected ? 'сервер онлайн' : 'подключение...'}
          </div>
        </motion.div>

        {/* Main panel */}
        <motion.div className="home__panel"
          initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.3 }}>

          <AnimatePresence mode="wait">
            {!mode ? (
              <motion.div key="main"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>

                <button className="btn btn-primary home__create-btn"
                  onClick={() => { setMode('create'); setError(''); }}
                  disabled={!connected}>
                  + Создать игру
                </button>

                <div className="home__rooms">
                  <div className="home__rooms-title">
                    Активные игры
                    <span className="home__rooms-count">{rooms.length}</span>
                  </div>

                  {rooms.length === 0 ? (
                    <div className="home__rooms-empty">Нет активных игр</div>
                  ) : (
                    <div className="home__rooms-list">
                      {rooms.map(r => (
                        <motion.div key={r.code} className="home__room-item"
                          initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}>
                          <div className="home__room-info">
                            <span className="home__room-host">{r.hostName}</span>
                            <span className="home__room-meta">
                              {r.players}/{r.maxPlayers} игроков
                              {r.bots > 0 && ` · ${r.bots} 🤖`}
                              · {r.phase === 'lobby' ? 'лобби' : 'в игре'}
                            </span>
                          </div>
                          <div className={`home__room-phase home__room-phase--${r.phase}`}>
                            {r.phase === 'lobby' ? 'ожидание' : 'идёт игра'}
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  )}
                </div>

                <button className="btn btn-primary home__join-code-btn"
                  onClick={() => { setMode('join'); setError(''); }}
                  disabled={!connected}>
                  Войти по коду
                </button>

                {error && <p className="home__error">{error}</p>}
              </motion.div>

            ) : mode === 'create' ? (
              <motion.div key="create" className="home__form"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <div className="home__form-title">// Создать игру</div>
                <input className="input" placeholder="Твоё имя (ведущий)" value={name}
                  onChange={e => { setName(e.target.value); setError(''); }}
                  onKeyDown={e => e.key === 'Enter' && handleCreate()}
                  maxLength={20} autoFocus />
                {error && <p className="home__error">{error}</p>}
                <button className="btn btn-primary" onClick={handleCreate} disabled={loading}>
                  {loading ? '...' : 'Создать комнату'}
                </button>
                <button className="btn btn-ghost" onClick={() => { setMode(null); setError(''); }}>
                  ← Назад
                </button>
              </motion.div>

            ) : (
              <motion.div key="join" className="home__form"
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <div className="home__form-title">// Войти в игру</div>
                <input className="input" placeholder="Твоё имя" value={name}
                  onChange={e => { setName(e.target.value); setError(''); }}
                  onKeyDown={e => e.key === 'Enter' && handleJoin()}
                  maxLength={20} autoFocus />
                <input className="input" placeholder="Код комнаты" value={code}
                  onChange={e => { setCode(e.target.value.toUpperCase()); setError(''); }}
                  onKeyDown={e => e.key === 'Enter' && handleJoin()}
                  maxLength={4} style={{ letterSpacing: '0.3em', textAlign: 'center' }} />
                {error && <p className="home__error">{error}</p>}
                <button className="btn btn-primary" onClick={() => handleJoin()} disabled={loading}>
                  {loading ? '...' : 'Войти'}
                </button>
                <button className="btn btn-ghost" onClick={() => { setMode(null); setError(''); }}>
                  ← Назад
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        <div className="home__footer">
          до 16 игроков · 8 характеристик · судьба решается голосованием
        </div>
      </div>
    </div>
  );
}

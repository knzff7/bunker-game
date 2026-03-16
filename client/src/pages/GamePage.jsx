import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useGameStore } from "../store/gameStore";
import "./GamePage.css";

const CHAR_KEYS = ["profession","biology","health","phobia","hobby","fact1","fact2","baggage"];
const CHAR_LABELS = {
  profession:"Профессия", biology:"Биология", health:"Здоровье", phobia:"Фобия",
  hobby:"Хобби", fact1:"Факт I", fact2:"Факт II", baggage:"Багаж",
};
const CHAR_ICONS = {
  profession:"💼", biology:"🧬", health:"❤️", phobia:"😨",
  hobby:"🎯", fact1:"⭐", fact2:"🔒", baggage:"🎒",
};
const BUNKER_ICONS = ["🏥","🥫","⚡","🔫","📚","🔧","🌱","💧","📡","🌾","🏋️","💊","☢️","🧬","👕","🎓","🚗","🛠️","🍺","🧪"];

function getAllowedKeys(phase) {
  return phase === 1 ? ["profession"] : CHAR_KEYS;
}

// ── Карточка характеристики ──
function TraitCard({ cardKey, label, icon, value, desc, isRevealed, isOwn, canReveal, onReveal, isNew }) {
  const [hovered, setHovered] = useState(false);
  const [flipping, setFlipping] = useState(false);

  // Своя — всегда лицом. Чужая — только если раскрыта.
  const showFace = isOwn || isRevealed;
  // Hover-флип ТОЛЬКО для чужих нераскрытых
  const flippedByHover = !isOwn && !isRevealed && hovered;
  const isFlipped = showFace || flippedByHover;

  function handleClick() {
    if (!canReveal || isRevealed) return;
    setFlipping(true);
    setTimeout(() => { onReveal(cardKey); setFlipping(false); }, 300);
  }

  // Описание показываем: своим всегда, чужим только после раскрытия
  const showDesc = desc && (isOwn || isRevealed);

  return (
    <div
      className={`tcard ${isOwn?"tcard--own":"tcard--other"} ${isRevealed?"tcard--revealed":""} ${canReveal?"tcard--can-reveal":""} ${isNew?"tcard--new":""}`}
      onClick={handleClick}
      onMouseEnter={() => !isOwn && setHovered(true)}
      onMouseLeave={() => !isOwn && setHovered(false)}
    >
      <div className={`tcard__inner ${isFlipped?"tcard__inner--show-face":""} ${flipping?"tcard__inner--flipping":""}`}>

        {/* Рубашка */}
        <div className="tcard__back">
          <div className="tcard__back-pattern" />
          <span className="tcard__back-icon">{icon}</span>
          <span className="tcard__back-label">{label}</span>
          {canReveal && <span className="tcard__back-hint">нажмите</span>}
        </div>

        {/* Лицо */}
        <div className={`tcard__face ${isOwn&&!isRevealed?"tcard__face--private":""}`}>
          <div className="tcard__face-header">
            <span className="tcard__face-icon">{icon}</span>
            <span className="tcard__face-label">{label}</span>
            {isOwn && !isRevealed && <span className="tcard__face-lock">🔒</span>}
            {isOwn && isRevealed && <span className="tcard__face-check">✓</span>}
          </div>
          {(!isOwn && !isRevealed)
            ? <div className="tcard__face-value tcard__face-value--unknown">?</div>
            : <div className="tcard__face-value">{value ?? "—"}</div>
          }
          {showDesc && <div className="tcard__face-desc">{desc}</div>}
        </div>
      </div>
    </div>
  );
}

// ── Карточка предмета бункера ──
function BunkerCard({ item, index, isNew }) {
  // Парсим название и описание из строки вида "Название — описание"
  const dashIdx = item.indexOf(" — ");
  const title = dashIdx > -1 ? item.slice(0, dashIdx) : item;
  const desc  = dashIdx > -1 ? item.slice(dashIdx + 3) : null;
  const icon  = BUNKER_ICONS[index % BUNKER_ICONS.length];

  return (
    <motion.div
      className={`bunker-card ${isNew ? "bunker-card--new" : ""}`}
      initial={isNew ? { opacity:0, scale:0.8, y:-10 } : { opacity:1 }}
      animate={{ opacity:1, scale:1, y:0 }}
      transition={{ type:"spring", stiffness:280, damping:22 }}
    >
      <div className="bunker-card__header">
        <span className="bunker-card__icon">{icon}</span>
        <span className="bunker-card__title">{title}</span>
      </div>
      {desc && <div className="bunker-card__desc">{desc}</div>}
    </motion.div>
  );
}

export default function GamePage() {
  const {
    players, playerId, isHost,
    myDossier, mySpecialSelf, mySpecialGroup, currentPhase, turnQueue, currentTurnIndex,
    votingActive, votes, votingTimeLeft, catastrophe, bunkerContents,
    exiledPlayers, gameLog,
    revealTrait, skipTurn, nextPhase: nextPhaseAction, vote, closeLobby, endVoting, useSpecial,
  } = useGameStore();

  const allDossiers = useGameStore(s => s.allDossiers) || {};
  const botVote = useGameStore(s => s.botVote);
  const [showCatastrophe, setShowCatastrophe] = useState(false);
  const [botVoteTarget, setBotVoteTarget] = useState({});
  const [newlyRevealed, setNewlyRevealed] = useState({});
  const [specialMsg, setSpecialMsg] = useState(null);
  const [showSpecialTarget, setShowSpecialTarget] = useState(false);
  const [tempReveal, setTempReveal] = useState(null); // временное раскрытие только для себя
  const prevRevealedRef = useRef({});
  const prevVotingRef = useRef(false);

  // Сбрасываем голоса ботов при каждом новом голосовании
  useEffect(() => {
    if (votingActive && !prevVotingRef.current) {
      setBotVoteTarget({});
    }
    prevVotingRef.current = votingActive;
  }, [votingActive]);

  const me = players.find(p => p.id === playerId);
  const myRevealedKeys = me?.revealed || [];
  const currentTurnId = turnQueue[currentTurnIndex];
  const currentTurnPlayer = players.find(p => p.id === currentTurnId);
  const isMyTurn = currentTurnId === playerId;
  const isBotTurn = currentTurnPlayer?.isBot && isHost;
  const allowedKeys = getAllowedKeys(currentPhase);
  const canRevealThisTurn = isMyTurn && !votingActive && (me?.revealedThisPhase || 0) < 1;

  // Отслеживаем новые раскрытия
  useEffect(() => {
    const fresh = {};
    for (const p of players) {
      for (const key of (p.revealed || [])) {
        const id = `${p.id}_${key}`;
        if (!prevRevealedRef.current[id]) fresh[id] = true;
      }
    }
    if (Object.keys(fresh).length) {
      setNewlyRevealed(prev => ({ ...prev, ...fresh }));
      setTimeout(() => setNewlyRevealed(prev => {
        const next = { ...prev };
        for (const k of Object.keys(fresh)) delete next[k];
        return next;
      }), 1800);
    }
    const all = {};
    for (const p of players) for (const key of (p.revealed || [])) all[`${p.id}_${key}`] = true;
    prevRevealedRef.current = all;
  }, [players]);

  function revealChar(key) {
    if (!canRevealThisTurn) return;
    if (currentPhase === 1 && key !== "profession") return;
    revealTrait(key, playerId);
  }

  function doBotTurn() {
    if (!isBotTurn || !currentTurnPlayer) return;
    const botRevealed = currentTurnPlayer.revealed || [];
    const available = getAllowedKeys(currentPhase).filter(k => !botRevealed.includes(k));
    if (available.length === 0) return;
    // Случайная карточка из доступных
    const randomKey = available[Math.floor(Math.random() * available.length)];
    revealTrait(randomKey, currentTurnId);
  }

  function skipBotTurn() {
    if (!isBotTurn) return;
    skipTurn(currentTurnId);
  }

  const myVote = votes?.[playerId];
  const alivePlayers = players;
  const mins = String(Math.floor(votingTimeLeft / 60)).padStart(2, "0");
  const secs = String(votingTimeLeft % 60).padStart(2, "0");

  // Все ли проголосовали (люди + боты через хоста)
  const humanVoted = !me?.isBot ? !!myVote : true;
  const botsVoted = alivePlayers.filter(p => p.isBot).every(bot => !!botVoteTarget[bot.id]);
  const allVoted = humanVoted && botsVoted;

  // Фаза завершена когда ВСЕ живые игроки (люди И боты) раскрыли по 1 карточке
  const phaseComplete = !votingActive && alivePlayers.length > 0 &&
    alivePlayers.every(p => (p.revealedThisPhase || 0) >= 1);

  // Для блокировки карточек — только люди (боты не блокируют возможность раскрытия)
  const humanPhaseComplete = !votingActive && alivePlayers.filter(p => !p.isBot).length > 0 &&
    alivePlayers.filter(p => !p.isBot).every(p => (p.revealedThisPhase || 0) >= 1);

  return (
    <div className="game">
      <div className="noise-overlay" />

      {/* ── Topbar ── */}
      <div className="game__topbar">
        <div className="game__topbar-left">
          <span className="game__topbar-logo">БУНКЕР</span>
          <div className="game__phase-badge">
            <span>Фаза</span><strong>{currentPhase}</strong>
            {currentPhase === 1 && <span className="game__phase-note">только профессии</span>}
          </div>
        </div>
        <div className="game__topbar-center">
          <AnimatePresence mode="wait">
            {isBotTurn && isHost && !votingActive && !phaseComplete ? (
              <motion.div key="bot" className="game__bot-turn-bar"
                initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}>
                <span>🤖 Ход бота: <strong>{currentTurnPlayer?.name}</strong></span>
                <button className="btn game__bot-move-btn" onClick={doBotTurn}>Сделать ход</button>
                <button className="btn game__bot-skip-btn" onClick={skipBotTurn}>Пропуск</button>
              </motion.div>
            ) : isBotTurn && !isHost && !phaseComplete ? (
              <motion.div key="bot-wait" className="game__other-turn"
                initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}>
                🤖 Ход бота: <strong>{currentTurnPlayer?.name}</strong> — ведущий управляет
              </motion.div>
            ) : phaseComplete && !votingActive ? (
              <motion.div key="phase-done" className="game__phase-done"
                initial={{opacity:0,scale:0.9}} animate={{opacity:1,scale:1}} exit={{opacity:0}}>
                ✓ Фаза {currentPhase} завершена — ведущий запускает следующую
              </motion.div>
            ) : isMyTurn && !votingActive ? (
              <motion.div key="my" className="game__your-turn"
                initial={{opacity:0,scale:0.9}} animate={{opacity:1,scale:1}} exit={{opacity:0,scale:0.9}}>
                <span className="game__turn-pulse" /> ВАШ ХОД — нажмите карточку
              </motion.div>
            ) : votingActive ? (
              <motion.div key="vote" className="game__voting-indicator"
                initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}>
                ⚖ ГОЛОСОВАНИЕ — {mins}:{secs}
              </motion.div>
            ) : currentTurnPlayer ? (
              <motion.div key="other" className="game__other-turn"
                initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}>
                Ход: <strong>{currentTurnPlayer.name}</strong>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>
        <div className="game__topbar-right">
          {catastrophe && (
            <button className="btn game__cat-btn" onClick={() => setShowCatastrophe(true)}>
              {catastrophe.icon} О катастрофе
            </button>
          )}
          {isHost && !votingActive && (
            <>
              <motion.button
                className={`btn btn-success${phaseComplete ? " game__next-phase-pulse" : ""}`}
                onClick={nextPhaseAction}
                animate={phaseComplete ? { boxShadow: ["0 0 0px rgba(45,180,90,0)", "0 0 20px rgba(45,180,90,0.6)", "0 0 0px rgba(45,180,90,0)"] } : {}}
                transition={{ duration: 1.2, repeat: Infinity }}
              >
                След. фаза
              </motion.button>
              <button className="btn btn-danger" onClick={closeLobby}>Завершить</button>
            </>
          )}
        </div>
      </div>

      {/* ── Body ── */}
      <div className="game__layout">

        {/* LEFT sidebar */}
        <aside className="game__sidebar">
          {/* Бункер — красивые карточки */}
          <div className="game__bunker-block">
            <div className="game__block-title"><span>🏰</span>Бункер — фаза {currentPhase}</div>
            <div className="game__bunker-cards">
              {bunkerContents.slice(0, currentPhase).map((item, i) => (
                <BunkerCard key={i} item={item} index={i} isNew={i === currentPhase-1} />
              ))}
              {bunkerContents.length > currentPhase && (
                <div className="game__bunker-unknown">
                  +{bunkerContents.length - currentPhase} предметов скрыто
                </div>
              )}
            </div>
          </div>

          <div className="game__turn-queue">
            <div className="game__block-title"><span>↻</span>Очередь</div>
            {turnQueue.map((id, i) => {
              const p = players.find(pl => pl.id === id);
              const active = i === currentTurnIndex && !votingActive;
              return (
                <div key={id} className={`game__turn-item${active?" active":""}`}>
                  <span className="game__turn-num">{i+1}</span>
                  <span>{p?.name ?? id}{p?.isBot?" 🤖":""}</span>
                  {active && <span className="game__turn-arrow">→</span>}
                </div>
              );
            })}
          </div>

          <div className="game__log">
            <div className="game__block-title"><span>📋</span>Лог</div>
            <div className="game__log-entries">
              {gameLog.slice(-10).reverse().map((e,i) => (
                <div key={i} className={`game__log-entry game__log-entry--${e.type}`}>{e.text}</div>
              ))}
            </div>
          </div>
        </aside>

        {/* CENTER */}
        <main className={`game__center${phaseComplete ? " game__center--locked" : ""}`}>
          <div className="game__dossiers">
            {alivePlayers.map((p, pi) => {
              const isMe = p.id === playerId;
              const isActive = p.id === currentTurnId && !votingActive;
              const pRevealed = p.revealed || [];

              return (
                <motion.div key={p.id}
                  className={`player-row ${isActive?"player-row--active":""} ${isMe?"player-row--me":""}`}
                  initial={{opacity:0,y:8}} animate={{opacity:1,y:0}}
                  transition={{delay:pi*0.05}}>

                  <div className="player-row__name">
                    <span className="player-row__name-text">
                      {p.name}{p.isBot&&" 🤖"}{isMe&&" (вы)"}
                    </span>
                    {isActive && (
                      <span className="player-row__turn-tag">
                        <span className="player-row__turn-pulse"/>ход
                      </span>
                    )}
                    <span className="player-row__revealed-count">{pRevealed.length}/{CHAR_KEYS.length}</span>
                  </div>

                  <div className="player-row__cards">
                    {CHAR_KEYS.map(key => {
                      const revealed = pRevealed.includes(key);
                      const isNew = !!newlyRevealed[`${p.id}_${key}`];

                      if (isMe) {
                        const char = myDossier?.[key];
                        const canReveal = canRevealThisTurn && allowedKeys.includes(key) && !revealed && !humanPhaseComplete;
                        return (
                          <TraitCard key={key} cardKey={key}
                            label={CHAR_LABELS[key]} icon={CHAR_ICONS[key]}
                            value={char?.value} desc={char?.desc}
                            isRevealed={revealed} isOwn={true}
                            canReveal={canReveal} onReveal={revealChar}
                            isNew={isNew} />
                        );
                      } else {
                        const val = allDossiers[p.id]?.[key];
                        return (
                          <TraitCard key={key} cardKey={key}
                            label={CHAR_LABELS[key]} icon={CHAR_ICONS[key]}
                            value={val?.value ?? (typeof val==="string"?val:null)}
                            desc={val?.desc ?? null}
                            isRevealed={revealed} isOwn={false}
                            canReveal={false} onReveal={()=>{}}
                            isNew={isNew} />
                        );
                      }
                    })}

                    {/* Особые карточки — только для своей строки */}
                    {isMe && (mySpecialSelf || mySpecialGroup) && (() => {
                      const me2 = players.find(p2 => p2.id === playerId);
                      const selfUsed  = me2?.specialSelfUsed;
                      const groupUsed = me2?.specialGroupUsed;

                      const renderSpecial = (card, used, label) => {
                        if (!card) return null;
                        const canUse = isMyTurn && !votingActive && !used;
                        const needsTarget = ["reveal_random_other","swap_bag_neighbor","copy_trait"].includes(card.effect);
                        return (
                          <div
                            key={card.id}
                            className={`tcard tcard--special ${used?"tcard--special-used":""} ${canUse?"tcard--can-reveal":""}`}
                            onClick={() => {
                              if (!canUse) return;
                              if (needsTarget) { setShowSpecialTarget(card.effect); return; }
                              useSpecial(card.effect, null, (res) => {
                                if (res.ok && res.temporary && res.tempData) {
                                  setTempReveal(res.tempData);
                                  setTimeout(() => setTempReveal(null), 5000);
                                  setSpecialMsg(res.msg);
                                } else {
                                  setSpecialMsg(res.msg || res.error);
                                }
                                setTimeout(() => setSpecialMsg(null), 3000);
                              });
                            }}
                          >
                            <div className="tcard__inner tcard__inner--show-face">
                              <div className="tcard__back" />
                              <div className="tcard__face">
                                <div className="tcard__face-header" style={{background: card.type==="self"?"#1a3a5c":"#5c1a1a"}}>
                                  <span className="tcard__face-icon">{card.icon}</span>
                                  <span className="tcard__face-label">{label}</span>
                                  {used && <span style={{marginLeft:"auto",fontSize:"0.6rem",color:"#888"}}>✓</span>}
                                </div>
                                <div className="tcard__face-value" style={{fontSize:"0.68rem",fontWeight:700}}>{card.title}</div>
                                <div className="tcard__face-desc">{card.desc}</div>
                                {canUse && <div className="tcard__back-hint" style={{color:"#4a9ec8",position:"static",bottom:"auto",border:"none",background:"none",padding:"0.2rem 0.4rem"}}>нажмите</div>}
                              </div>
                            </div>
                          </div>
                        );
                      };

                      return <>
                        <div className="special-divider" />
                        {renderSpecial(mySpecialSelf,  selfUsed,  "🧍 Личная")}
                        {renderSpecial(mySpecialGroup, groupUsed, "👥 Групповая")}
                      </>;
                    })()}
                  </div>
                </motion.div>
              );
            })}

            {exiledPlayers.length > 0 && (
              <div className="game__exiled">
                <span className="game__exiled-label">✕ Изгнаны:</span>
                {exiledPlayers.map(p => (
                  <span key={p.id} className="game__exiled-name">{p.name}</span>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>

      {/* ── Уведомление об особой карточке ── */}
      <AnimatePresence>
        {specialMsg && (
          <motion.div className="special-toast"
            initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} exit={{opacity:0,y:20}}>
            ✨ {specialMsg}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Модал выбора цели для групповых карточек ── */}
      <AnimatePresence>
        {showSpecialTarget && (
          <motion.div className="modal-overlay"
            initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}
            onClick={() => setShowSpecialTarget(false)}>
            <motion.div className="special-target-modal"
              initial={{opacity:0,scale:0.9}} animate={{opacity:1,scale:1}} exit={{opacity:0}}
              onClick={e => e.stopPropagation()}>
              <div className="special-target-modal__title">Выберите игрока</div>
              <div className="special-target-modal__players">
                {alivePlayers.filter(p => p.id !== playerId).map(p => (
                  <button key={p.id} className="special-target-modal__btn"
                    onClick={() => {
                      setShowSpecialTarget(false);
                      useSpecial(showSpecialTarget, p.id, (res) => {
                        if (res.ok && res.temporary && res.tempData) {
                          setTempReveal(res.tempData);
                          setTimeout(() => setTempReveal(null), 5000);
                          setSpecialMsg(res.msg);
                        } else {
                          setSpecialMsg(res.msg || res.error);
                        }
                        setTimeout(() => setSpecialMsg(null), 3000);
                      });
                    }}>
                    {p.name}{p.isBot && " 🤖"}
                  </button>
                ))}
              </div>
              <button className="btn" style={{marginTop:"1rem",width:"100%"}}
                onClick={() => setShowSpecialTarget(false)}>Отмена</button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Голосование — правая панель, выезжает сбоку ── */}
      <AnimatePresence>
        {votingActive && (
          <motion.div
            className="voting-overlay"
            initial={{ x: 300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 300, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
          >
            <div className="voting-modal">
              <div className="voting-modal__header">
                <span className="voting-modal__title">⚖ Голосование</span>
                <span className={`voting-modal__timer${votingTimeLeft<30?" urgent":""}`}>{mins}:{secs}</span>
              </div>
              <p className="voting-modal__desc">Кого изгнать? Все голосуют, итог — по таймеру или кнопке хоста.</p>

              {!me?.isBot && (
                <div className="voting-modal__section">
                  <div className="voting-modal__section-label">ВАШ ГОЛОС</div>
                  <div className="voting-modal__players">
                    {alivePlayers.filter(p => p.id !== playerId).map(p => (
                      <button key={p.id}
                        className={`voting-modal__vote-btn${myVote===p.id?" voted":""}`}
                        onClick={() => !myVote && vote(p.id)} disabled={!!myVote}>
                        {p.name}{myVote===p.id&&" ✓"}
                      </button>
                    ))}
                  </div>
                  {myVote && <p className="voting-modal__voted">✓ Голос учтён</p>}
                </div>
              )}

              {isHost && alivePlayers.some(p => p.isBot) && (
                <div className="voting-modal__section">
                  <div className="voting-modal__section-label" style={{color:"#4a7ec8"}}>🤖 ГОЛОСА БОТОВ</div>
                  {alivePlayers.filter(p => p.isBot).map(bot => (
                    <div key={bot.id} className="voting-modal__bot-row">
                      <span className="voting-modal__bot-name">{bot.name}:</span>
                      <div className="voting-modal__players">
                        {alivePlayers.filter(p => p.id !== bot.id).map(p => (
                          <button key={p.id}
                            className={`voting-modal__vote-btn${botVoteTarget[bot.id]===p.id?" voted":""}`}
                            onClick={() => {
                              if (!botVoteTarget[bot.id]) {
                                setBotVoteTarget(prev => ({...prev, [bot.id]: p.id}));
                                botVote(bot.id, p.id);
                              }
                            }}
                            disabled={!!botVoteTarget[bot.id]}>
                            {p.name}{botVoteTarget[bot.id]===p.id&&" ✓"}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {isHost && (
                <div className="voting-modal__section">
                  <button
                    className={`voting-modal__end-btn${allVoted ? " ready" : ""}`}
                    onClick={endVoting}
                    disabled={!allVoted}
                  >
                    {allVoted ? "✓ Завершить голосование" : `Ждём голосов... (${
                      Object.keys(votes || {}).length
                    }/${alivePlayers.length})`}
                  </button>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Временное раскрытие (только для использующего) ── */}
      <AnimatePresence>
        {tempReveal && (
          <motion.div className="modal-overlay" style={{zIndex:200}}
            initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}}
            onClick={() => setTempReveal(null)}>
            <motion.div className="special-target-modal"
              initial={{opacity:0,scale:0.9}} animate={{opacity:1,scale:1}} exit={{opacity:0}}
              onClick={e => e.stopPropagation()}
              style={{maxWidth:400, textAlign:'center'}}>
              <div style={{fontSize:28, marginBottom:8}}>👁</div>
              <div className="special-target-modal__title" style={{marginBottom:16}}>
                Временное раскрытие — только вы видите это
              </div>
              {tempReveal.type === 'reveal_single' && (
                <div style={{padding:'12px 16px', border:'1px solid var(--accent-dim)', background:'rgba(200,169,110,0.06)', borderRadius:6}}>
                  <div style={{fontSize:12, color:'var(--text-muted)', marginBottom:6}}>{tempReveal.targetName}</div>
                  <div style={{fontSize:13, fontWeight:600, color:'var(--accent)', textTransform:'uppercase', letterSpacing:'0.1em', marginBottom:4}}>
                    {tempReveal.key}
                  </div>
                  <div style={{fontSize:15, color:'var(--text-primary)'}}>
                    {tempReveal.trait?.value || tempReveal.trait || '—'}
                  </div>
                  {tempReveal.trait?.desc && (
                    <div style={{fontSize:11, color:'var(--text-dim)', marginTop:4, fontStyle:'italic'}}>{tempReveal.trait.desc}</div>
                  )}
                </div>
              )}
              {tempReveal.type === 'reveal_all_health' && (
                <div style={{display:'flex', flexDirection:'column', gap:8}}>
                  {(tempReveal.players || []).map(p => (
                    <div key={p.id} style={{padding:'8px 14px', border:'1px solid var(--accent-dim)', background:'rgba(200,169,110,0.06)', borderRadius:6, display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                      <span style={{fontSize:13, color:'var(--text-muted)'}}>{p.name}</span>
                      <span style={{fontSize:13, fontWeight:600, color:'var(--text-primary)'}}>
                        {p.health?.value || p.health || '—'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <div style={{marginTop:16, fontSize:11, color:'var(--text-dim)'}}>
                Исчезнет через 5 сек · нажмите чтобы закрыть
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Катастрофа ── */}
      <AnimatePresence>
        {showCatastrophe && catastrophe && (
          <motion.div className="modal-overlay" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} onClick={()=>setShowCatastrophe(false)}>
            <motion.div className="catastrophe-modal" initial={{opacity:0,scale:0.9}} animate={{opacity:1,scale:1}} exit={{opacity:0}} onClick={e=>e.stopPropagation()}>
              <div className="catastrophe-modal__icon">{catastrophe.icon}</div>
              <h2 className="catastrophe-modal__title">{catastrophe.title}</h2>
              <div className="glow-line" />
              <p className="catastrophe-modal__desc">{catastrophe.description}</p>
              <div className="catastrophe-modal__stats">
                <div className="catastrophe-modal__stat"><span>Срок в бункере</span><strong>{catastrophe.duration||catastrophe.bunkerDuration||"—"}</strong></div>
                <div className="catastrophe-modal__stat"><span>Население</span><strong>{catastrophe.population||catastrophe.populationLeft||"—"}</strong></div>
                <div className="catastrophe-modal__stat" style={{gridColumn:"1/-1"}}><span>Угрозы снаружи</span><strong>{catastrophe.extra||catastrophe.threats?.join(" · ")||catastrophe.surfaceCondition||"—"}</strong></div>
              </div>
              <button className="btn" onClick={()=>setShowCatastrophe(false)}>Закрыть</button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

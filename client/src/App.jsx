import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useGameStore } from './store/gameStore';
import HomePage from './pages/HomePage';
import LobbyPage from './pages/LobbyPage';
import CardPickPage from './pages/CardPickPage';
import GamePage from './pages/GamePage';
import FinalPage from './pages/FinalPage';
import Notification from './components/Notification';

const SCROLLABLE_PAGES = ['card_pick', 'final', 'discussion'];


export default function App() {
  const { initSocket, page, notification, clearNotification } = useGameStore();

  useEffect(() => { initSocket(); }, []);

  const isScrollable = SCROLLABLE_PAGES.includes(page);

  const renderPage = () => {
    switch (page) {
      case 'home':          return <HomePage />;
      case 'lobby':         return <LobbyPage />;
      case 'card_pick':     return <CardPickPage />;
      case 'discussion':
      case 'voting':        return <GamePage />;
      case 'final':         return <FinalPage />;
      case 'reconnecting':  return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: '#fff', fontSize: 24 }}>
          Восстанавливаем соединение...
        </div>
      );
      default:              return <HomePage />;
    }
  };

  return (
    <div className="noise" style={{
      width: '100vw', height: '100vh', position: 'relative',
      overflowY: isScrollable ? 'auto' : 'hidden', overflowX: 'hidden',
    }}>
      <AnimatePresence mode="wait">
        <motion.div key={page}
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          style={{ width: '100%', minHeight: '100%', height: isScrollable ? 'auto' : '100%' }}>
          {renderPage()}
        </motion.div>
      </AnimatePresence>
      <AnimatePresence>
        {notification && <Notification key="notif" notification={notification} onClose={clearNotification} />}
      </AnimatePresence>
    </div>
  );
}

import type React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import HomePage from './pages/HomePage';
import NotFoundPage from './pages/NotFoundPage';
import './App.css';

// 侧边导航图标
const HomeIcon: React.FC<{ active?: boolean }> = ({ active }) => (
  <svg className="w-6 h-6" fill={active ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
);

const SettingsIcon: React.FC = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

// 侧边栏导航
const Sidebar: React.FC = () => {
  return (
    <aside className="sidebar-nav fixed left-0 top-0 h-full z-50">
      {/* Logo */}
      <NavLink 
        to="/" 
        className="nav-icon !bg-cyan mb-6"
        style={{ background: 'linear-gradient(135deg, #00d4ff 0%, #00a8cc 100%)' }}
      >
        <svg className="w-5 h-5 text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
        </svg>
      </NavLink>

      {/* 导航项 - 单页设计，只有首页 */}
      <nav className="flex flex-col gap-2 flex-1">
        <NavLink to="/" className="nav-icon active">
          <HomeIcon active />
        </NavLink>
      </nav>

      {/* 底部设置 */}
      <div className="mt-auto">
        <button type="button" className="nav-icon" title="设置">
          <SettingsIcon />
        </button>
      </div>
    </aside>
  );
};

const App: React.FC = () => {
  return (
    <Router>
      <div className="flex min-h-screen bg-base">
        {/* 侧边导航 */}
        <Sidebar />

        {/* 主内容区 */}
        <main className="flex-1 ml-16 md:ml-16">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;

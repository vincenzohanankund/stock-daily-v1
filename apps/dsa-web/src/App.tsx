import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Shell from './components/Shell';
import { ToastProvider } from './components/common/Toast';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Spinner } from './components/common/Spinner';
import HomePage from './pages/HomePage';
import BacktestPage from './pages/BacktestPage';
import SettingsPage from './pages/SettingsPage';
import NotFoundPage from './pages/NotFoundPage';
import LoginPage from './pages/LoginPage';
import SetupPasswordPage from './pages/SetupPasswordPage';

function AppLayout() {
  const { status, isLoading, error } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Spinner size="lg" />
      </div>
    );
  }

  // If status check failed completely
  if (error && !status) {
      return (
          <div className="min-h-screen flex flex-col items-center justify-center bg-background gap-4">
              <p className="text-destructive">无法连接鉴权服务: {error}</p>
              <button 
                onClick={() => window.location.reload()} 
                className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors"
              >
                重试
              </button>
          </div>
      );
  }

  if (!status) {
     return <div className="min-h-screen flex items-center justify-center bg-background">未知错误</div>;
  }

  // Not initialized -> Setup
  if (!status.initialized) {
    return <SetupPasswordPage />;
  }

  // Not authenticated -> Login
  if (!status.authenticated) {
    return <LoginPage />;
  }

  return (
    <Shell>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/backtest" element={<BacktestPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Shell>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <ToastProvider>
          <AppLayout />
        </ToastProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;

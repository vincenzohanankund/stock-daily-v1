import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { 
  Home, 
  FlaskConical, 
  Settings, 
  Zap, 
  Menu, 
  X,
  PanelLeftClose,
  PanelLeftOpen,
  LogOut,
  KeyRound
} from 'lucide-react';
import ThemeToggle from './ThemeToggle';
import { useAuth } from '../contexts/AuthContext';
import ChangePasswordModal from './auth/ChangePasswordModal';

interface ShellProps {
  children: React.ReactNode;
}

const Shell: React.FC<ShellProps> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);

  const navigation = [
    { name: '个股分析', href: '/', icon: Home, key: 'home' },
    { name: '模型回测', href: '/backtest', icon: FlaskConical, key: 'backtest' },
    { name: '系统设置', href: '/settings', icon: Settings, key: 'settings' },
  ];

  const currentPath = location.pathname;
  const isCurrent = (href: string) => {
    if (href === '/') return currentPath === '/';
    return currentPath.startsWith(href);
  };

  const handleNavClick = (href: string) => {
    navigate(href);
    setMobileMenuOpen(false);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground font-sans">
      {/* Sidebar for Desktop */}
      <div 
        className={`hidden md:flex md:flex-col border-r border-border bg-muted/10 transition-all duration-300 ${
          collapsed ? 'md:w-20' : 'md:w-64'
        }`}
      >
        <div className={`flex items-center h-16 bg-background ${collapsed ? 'justify-center px-0' : 'px-6'}`}>
          <div className="flex items-center gap-2 overflow-hidden whitespace-nowrap">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-foreground shadow-sm flex-shrink-0">
              <Zap size={20} />
            </div>
            {!collapsed && <span className="text-lg font-bold tracking-tight transition-opacity duration-300">DSA Pro</span>}
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
          {navigation.map((item) => (
            <button
              key={item.name}
              onClick={() => handleNavClick(item.href)}
              className={`flex items-center w-full py-2.5 text-sm font-medium rounded-md transition-all duration-200 ${
                collapsed ? 'justify-center px-0' : 'px-3'
              } ${
                isCurrent(item.href)
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
              title={collapsed ? item.name : undefined}
            >
              <item.icon size={18} className={`${collapsed ? '' : 'mr-3'} ${isCurrent(item.href) ? 'text-primary-foreground' : 'text-muted-foreground'}`} />
              {!collapsed && <span>{item.name}</span>}
            </button>
          ))}

          <div className="pt-4 mt-4 border-t border-border">
            <button
              onClick={() => setChangePasswordOpen(true)}
              className={`flex items-center w-full py-2.5 text-sm font-medium rounded-md transition-all duration-200 text-muted-foreground hover:bg-muted hover:text-foreground ${
                collapsed ? 'justify-center px-0' : 'px-3'
              }`}
              title={collapsed ? '修改密码' : undefined}
            >
              <KeyRound size={18} className={`${collapsed ? '' : 'mr-3'} text-muted-foreground`} />
              {!collapsed && <span>修改密码</span>}
            </button>
            
            <button
              onClick={logout}
              className={`flex items-center w-full py-2.5 text-sm font-medium rounded-md transition-all duration-200 text-muted-foreground hover:text-destructive hover:bg-destructive/10 ${
                collapsed ? 'justify-center px-0' : 'px-3'
              }`}
              title={collapsed ? '退出登录' : undefined}
            >
              <LogOut size={18} className={`${collapsed ? '' : 'mr-3'}`} />
              {!collapsed && <span>退出登录</span>}
            </button>
          </div>
        </nav>
        <div className={`p-4 border-t border-border bg-background flex items-center ${collapsed ? 'justify-center flex-col gap-4' : 'justify-between'}`}>
          <ThemeToggle />
          <button 
            onClick={() => setCollapsed(!collapsed)}
            className="text-muted-foreground hover:text-foreground transition-colors p-1 rounded-md hover:bg-muted"
            title={collapsed ? "展开" : "收起"}
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>
      </div>

      {/* Mobile Header */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 flex items-center justify-between h-16 px-4 border-b border-border bg-background">
        <div className="flex items-center gap-2">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Zap size={20} />
          </div>
          <span className="text-lg font-bold">DSA Pro</span>
        </div>
        <button onClick={() => setMobileMenuOpen(true)} className="p-2 rounded-md hover:bg-muted">
          <Menu size={24} />
        </button>
      </div>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden bg-background/80 backdrop-blur-sm" onClick={() => setMobileMenuOpen(false)} />
      )}

      {/* Mobile Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-64 bg-background border-r border-border shadow-lg transform transition-transform duration-300 ease-in-out md:hidden ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between h-16 px-6 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Zap size={20} />
            </div>
            <span className="text-lg font-bold">DSA Pro</span>
          </div>
          <button onClick={() => setMobileMenuOpen(false)} className="p-1 rounded-md hover:bg-muted">
            <X size={24} />
          </button>
        </div>
        <nav className="px-3 py-4 space-y-1">
          {navigation.map((item) => (
            <button
              key={item.name}
              onClick={() => handleNavClick(item.href)}
              className={`flex items-center w-full px-3 py-2.5 text-sm font-medium rounded-md transition-all duration-200 ${
                isCurrent(item.href)
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <item.icon size={18} className={`mr-3 ${isCurrent(item.href) ? 'text-primary-foreground' : 'text-muted-foreground'}`} />
              {item.name}
            </button>
          ))}

          <div className="pt-4 mt-4 border-t border-border">
             <button
              onClick={() => {
                setMobileMenuOpen(false);
                setChangePasswordOpen(true);
              }}
              className="flex items-center w-full px-3 py-2.5 text-sm font-medium rounded-md transition-all duration-200 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <KeyRound size={18} className="mr-3 text-muted-foreground" />
              修改密码
            </button>
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                logout();
              }}
              className="flex items-center w-full px-3 py-2.5 text-sm font-medium rounded-md transition-all duration-200 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
            >
              <LogOut size={18} className="mr-3" />
              退出登录
            </button>
          </div>
        </nav>
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-border bg-muted/10">
          <div className="flex items-center justify-between">
            <ThemeToggle />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden pt-16 md:pt-0 bg-muted/5">
        {children}
      </main>
      
      <ChangePasswordModal 
        isOpen={changePasswordOpen}
        onClose={() => setChangePasswordOpen(false)}
      />
    </div>
  );
};

export default Shell;

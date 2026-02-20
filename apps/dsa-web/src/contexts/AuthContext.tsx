import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { authApi } from '../api/auth';
import type { AuthStatus, ChangePasswordRequest } from '../types/auth';

interface AuthContextType {
  status: AuthStatus | null;
  isLoading: boolean;
  error: string | null;
  checkStatus: () => Promise<void>;
  login: (password: string) => Promise<boolean>;
  setupPassword: (password: string) => Promise<boolean>;
  changePassword: (data: ChangePasswordRequest) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkStatus = useCallback(async () => {
    try {
      // Don't set global loading true here to avoid flickering if we just want to refresh
      // But for initial load it's fine.
      // Let's manage loading inside component for specific actions, but global loading for init.
      const data = await authApi.getStatus();
      
      // Map API response to internal state
      const hasToken = !!localStorage.getItem('auth_token');
      setStatus({
        initialized: data.password_initialized,
        authenticated: hasToken,
        user: data.username
      });
    } catch (err: any) {
      console.error('Check auth status failed:', err);
      // If unauthorized, api interceptor might trigger event, but here we just catch error
      // Maybe network error or server down.
      // We should probably allow retry or show error.
      // 优先显示后端返回的错误信息
      const message = err.response?.data?.detail || err.response?.data?.message || err.message || 'Check status failed';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkStatus();

    const handleUnauthorized = () => {
      setStatus((prev) => prev ? { ...prev, authenticated: false } : null);
      localStorage.removeItem('auth_token');
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, [checkStatus]);

  const login = async (password: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await authApi.login({ password });
      if (response.success) {
        // Support both token and access_token fields
        const token = response.access_token || response.token;
        if (token) {
          localStorage.setItem('auth_token', token);
        }
        await checkStatus();
        return true;
      } else {
        setError(response.message || '登录失败，请检查密码');
        return false;
      }
    } catch (err: any) {
      // 优先显示后端返回的错误信息
      const message = err.response?.data?.detail || err.response?.data?.message || err.message || '登录失败';
      setError(message);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const setupPassword = async (password: string): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);
      // 构造符合后端要求的参数结构
      const response = await authApi.setupPassword({ 
        username: 'admin',
        password: password,
        confirm_password: password
      });
      if (response.success) {
        // 乐观更新状态，假设初始化成功
        setStatus((prev) => ({ 
          initialized: true, 
          authenticated: false, 
          user: prev?.user 
        }));
        
        await checkStatus();
        return true;
      } else {
        setError(response.message || '设置密码失败');
        return false;
      }
    } catch (err: any) {
      // 优先显示后端返回的错误信息
      const message = err.response?.data?.detail || err.response?.data?.message || err.message || '设置密码失败';
      setError(message);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setStatus((prev) => prev ? { ...prev, authenticated: false } : null);
    // window.location.href = '/'; // Let router handle it
  };

  const changePassword = async (data: ChangePasswordRequest): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await authApi.changePassword(data);
      if (response.success) {
        return true;
      } else {
        setError(response.message || '修改密码失败');
        return false;
      }
    } catch (err: any) {
      const message = err.response?.data?.detail?.message || err.response?.data?.message || err.message || '修改密码失败';
      setError(message);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider value={{ status, isLoading, error, checkStatus, login, setupPassword, logout, changePassword }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

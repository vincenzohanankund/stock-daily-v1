import React, { createContext, useContext, useState, useCallback, useRef } from 'react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastMessage {
  id: string;
  type: ToastType;
  content: React.ReactNode;
  duration?: number;
}

interface ToastContextType {
  addToast: (message: Omit<ToastMessage, 'id'>) => void;
  removeToast: (id: string) => void;
  success: (content: React.ReactNode, duration?: number) => void;
  error: (content: React.ReactNode, duration?: number) => void;
  info: (content: React.ReactNode, duration?: number) => void;
  warning: (content: React.ReactNode, duration?: number) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const toastTimeouts = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
    if (toastTimeouts.current[id]) {
      clearTimeout(toastTimeouts.current[id]);
      delete toastTimeouts.current[id];
    }
  }, []);

  const addToast = useCallback(
    ({ type, content, duration = 3000 }: Omit<ToastMessage, 'id'>) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast: ToastMessage = { id, type, content, duration };

      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        toastTimeouts.current[id] = setTimeout(() => {
          removeToast(id);
        }, duration);
      }
    },
    [removeToast]
  );

  const success = useCallback((content: React.ReactNode, duration?: number) => addToast({ type: 'success', content, duration }), [addToast]);
  const error = useCallback((content: React.ReactNode, duration?: number) => addToast({ type: 'error', content, duration }), [addToast]);
  const info = useCallback((content: React.ReactNode, duration?: number) => addToast({ type: 'info', content, duration }), [addToast]);
  const warning = useCallback((content: React.ReactNode, duration?: number) => addToast({ type: 'warning', content, duration }), [addToast]);

  return (
    <ToastContext.Provider value={{ addToast, removeToast, success, error, info, warning }}>
      {children}
      <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
};

const ToastItem: React.FC<{ toast: ToastMessage; onClose: () => void }> = ({ toast, onClose }) => {
  const icons = {
    success: <CheckCircle className="w-5 h-5" />,
    error: <AlertCircle className="w-5 h-5" />,
    info: <Info className="w-5 h-5" />,
    warning: <AlertTriangle className="w-5 h-5" />,
  };

  const styles = {
    success: 'bg-background border-border',
    error: 'bg-destructive text-destructive-foreground border-destructive',
    info: 'bg-background border-border',
    warning: 'bg-background border-border',
  };

  const iconColors = {
    success: 'text-green-500',
    error: 'text-destructive-foreground',
    info: 'text-blue-500',
    warning: 'text-yellow-500',
  };

  return (
    <div
      className={`pointer-events-auto flex items-start w-80 p-4 rounded-lg shadow-lg border ${styles[toast.type]} transform transition-all duration-300 ease-in-out animate-in slide-in-from-right-full`}
      role="alert"
    >
      <div className={`flex-shrink-0 mr-3 ${toast.type === 'error' ? 'text-destructive-foreground' : iconColors[toast.type]}`}>
        {icons[toast.type]}
      </div>
      <div className={`flex-1 text-sm font-medium ${toast.type === 'error' ? 'text-destructive-foreground' : 'text-foreground'}`}>
        {toast.content}
      </div>
      <button
        onClick={onClose}
        className={`flex-shrink-0 ml-2 hover:opacity-80 focus:outline-none ${toast.type === 'error' ? 'text-destructive-foreground' : 'text-muted-foreground hover:text-foreground'}`}
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};

export default ToastProvider;

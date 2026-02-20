import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import Button from './Button';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  visible?: boolean; // For backward compatibility with Arco
  onOk?: () => void; // For backward compatibility
  onCancel?: () => void; // For backward compatibility
  autoFocus?: boolean; // Ignored but kept for compatibility
  focusLock?: boolean; // Ignored but kept for compatibility
  scrollableContent?: boolean; // Whether the content area should scroll (default: true)
}

const Modal: React.FC<ModalProps> = ({ 
  isOpen, 
  onClose, 
  title, 
  children, 
  footer,
  size = 'md',
  visible,
  onOk,
  onCancel,
  scrollableContent = true
}) => {
  // Handle backward compatibility
  const show = isOpen || visible || false;
  const handleClose = onClose || onCancel;

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') handleClose?.();
    };
    if (show) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [show, handleClose]);

  if (!show) return null;

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    '2xl': 'max-w-6xl',
    'full': 'max-w-[95vw]',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity" 
        onClick={handleClose}
        aria-hidden="true"
      />
      
      <div className={`relative w-full ${sizeClasses[size]} bg-background rounded-xl shadow-2xl ring-1 ring-border transform transition-all flex flex-col max-h-[90vh]`}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h3 className="text-lg font-semibold text-foreground leading-none tracking-tight">{title}</h3>
          <button
            onClick={handleClose}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <X size={18} />
            <span className="sr-only">Close</span>
          </button>
        </div>
        
        <div className={`flex-1 ${scrollableContent ? 'overflow-y-auto' : 'overflow-hidden'} px-6 py-4 text-foreground`}>
          {children}
        </div>
        
        {(footer || onOk) && (
          <div className="px-6 py-4 border-t border-border bg-muted/20 rounded-b-xl flex justify-end gap-3">
            {footer ? footer : (
              <>
                <Button 
                  variant="outline"
                  onClick={handleClose}
                >
                  取消
                </Button>
                <Button 
                  variant="primary"
                  onClick={onOk}
                >
                  确认
                </Button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Modal;

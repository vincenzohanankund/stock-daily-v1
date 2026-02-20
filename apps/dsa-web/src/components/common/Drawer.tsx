import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  width?: string | number;
  position?: 'left' | 'right';
  visible?: boolean; // For backward compatibility
  onCancel?: () => void; // For backward compatibility
  footer?: React.ReactNode; // Ignored for now or can be added
}

const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  children,
  width = '400px',
  position = 'right',
  visible,
  onCancel
}) => {
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

  const drawerWidth = typeof width === 'number' ? `${width}px` : width;
  
  return (
    <>
      {/* Backdrop */}
      <div 
        className={`fixed inset-0 z-40 bg-background/80 backdrop-blur-sm transition-opacity duration-300 ${
          show ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
        onClick={handleClose}
        aria-hidden="true"
      />
      
      {/* Drawer Panel */}
      <div
        className={`fixed inset-y-0 z-50 flex flex-col bg-background shadow-2xl transition-transform duration-300 ease-in-out ${
          position === 'right' ? 'right-0' : 'left-0'
        } ${
          show 
            ? 'translate-x-0' 
            : position === 'right' ? 'translate-x-full' : '-translate-x-full'
        }`}
        style={{ width: drawerWidth, maxWidth: '100vw' }}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h3 className="text-lg font-semibold text-foreground">{title}</h3>
          <button
            onClick={handleClose}
            className="p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors focus:outline-none focus:ring-2 focus:ring-ring"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto px-6 py-4 text-foreground">
          {children}
        </div>
      </div>
    </>
  );
};

export default Drawer;

import React from 'react';
import { AlertTriangle, Info, CheckCircle, XCircle } from 'lucide-react';
import Modal from './Modal';
import Button from './Button';

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  content: React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  type?: 'danger' | 'warning' | 'info' | 'success';
  isLoading?: boolean;
}

const ConfirmationModal: React.FC<ConfirmationModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  content,
  confirmText = '确认',
  cancelText = '取消',
  type = 'warning',
  isLoading = false,
}) => {
  const icons = {
    danger: <XCircle className="w-12 h-12 text-red-500 mb-4" />,
    warning: <AlertTriangle className="w-12 h-12 text-yellow-500 mb-4" />,
    info: <Info className="w-12 h-12 text-blue-500 mb-4" />,
    success: <CheckCircle className="w-12 h-12 text-green-500 mb-4" />,
  };

  const confirmButtonVariants: Record<string, 'danger' | 'primary' | 'secondary' | 'ghost' | 'outline'> = {
    danger: 'danger',
    warning: 'danger',
    info: 'primary',
    success: 'primary',
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <div className="flex justify-end gap-3 w-full">
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            {cancelText}
          </Button>
          <Button
            variant={confirmButtonVariants[type] || 'primary'}
            onClick={onConfirm}
            loading={isLoading}
          >
            {confirmText}
          </Button>
        </div>
      }
    >
      <div className="flex flex-col items-center text-center p-4">
        {icons[type]}
        <p className="text-muted-foreground">{content}</p>
      </div>
    </Modal>
  );
};

export default ConfirmationModal;

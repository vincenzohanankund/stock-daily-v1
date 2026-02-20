import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import Button from './Button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  public resetErrorBoundary = () => {
    if (this.props.onReset) {
      this.props.onReset();
    }
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="p-4 rounded-lg border border-destructive/20 bg-destructive/5 flex flex-col items-center justify-center gap-2 text-center h-full min-h-[120px]">
          <AlertTriangle className="text-destructive w-8 h-8" />
          <div className="text-sm font-medium text-destructive">组件渲染出错</div>
          <div className="text-xs text-muted-foreground max-w-[200px] truncate">
            {this.state.error?.message || '发生未知错误'}
          </div>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={this.resetErrorBoundary}
            className="mt-2 h-7 text-xs"
          >
            <RefreshCw size={12} className="mr-1" /> 重试
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

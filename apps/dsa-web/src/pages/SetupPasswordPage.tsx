import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { Card } from '../components/common/Card';
import { Spinner } from '../components/common/Spinner';
import { Lock, KeyRound } from 'lucide-react';

const SetupPasswordPage: React.FC = () => {
  const { setupPassword, isLoading, error } = useAuth();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (!password) return;
    if (password !== confirmPassword) {
      setLocalError('两次输入的密码不一致');
      return;
    }
    await setupPassword(password);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted/50 p-4 relative overflow-hidden">
      {/* Decorative background elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
        <div className="absolute -top-[20%] -right-[10%] w-[50%] h-[50%] rounded-full bg-primary/5 blur-[100px]" />
        <div className="absolute top-[40%] -left-[10%] w-[40%] h-[40%] rounded-full bg-green-500/5 blur-[100px]" />
      </div>

      <Card className="w-full max-w-md p-8 shadow-2xl border-border/50 bg-card/80 backdrop-blur-xl relative z-10">
        <div className="space-y-8">
          <div className="flex flex-col items-center">
            <div className="text-center space-y-2">
              <h1 className="text-2xl font-bold tracking-tight">系统初始化</h1>
              <p className="text-sm text-muted-foreground">请设置管理员密码以保护您的数据</p>
            </div>
          </div>
          
          {(error || localError) && (
            <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center justify-center font-medium">
              {error || localError}
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-4">
            <div className="space-y-1">
              <div className="relative">
                <div className="absolute left-3 top-3.5 text-muted-foreground z-10">
                  <KeyRound size={16} />
                </div>
                <Input
                  type="password"
                  placeholder="设置密码"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoFocus
                  className="pl-9 h-11"
                />
              </div>
            </div>

            <div className="space-y-1">
              <div className="relative">
                <div className="absolute left-3 top-3.5 text-muted-foreground z-10">
                  <Lock size={16} />
                </div>
                <Input
                  type="password"
                  placeholder="确认密码"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="pl-9 h-11"
                />
              </div>
            </div>
          </div>

          <Button 
            type="submit" 
            className="w-full h-11 text-base font-medium shadow-lg shadow-green-500/20 hover:shadow-green-500/30 bg-green-600 hover:bg-green-700 text-white border-green-600" 
            disabled={isLoading || !password}
          >
            {isLoading ? <span className="mr-2"><Spinner size="sm" /></span> : null}
            完成设置
          </Button>
        </form>
        
        <div className="text-center text-xs text-muted-foreground/60 pt-2">
           &copy; {new Date().getFullYear()} DSA Pro. All rights reserved.
        </div>
      </div>
      </Card>
    </div>
  );
};

export default SetupPasswordPage;

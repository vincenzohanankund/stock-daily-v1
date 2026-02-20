import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import Input from '../components/common/Input';
import Button from '../components/common/Button';
import { Card } from '../components/common/Card';
import { Spinner } from '../components/common/Spinner';
import { Lock } from 'lucide-react';

const LoginPage: React.FC = () => {
  const { login, isLoading, error } = useAuth();
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!password) return;
    await login(password);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted/50 p-4 relative overflow-hidden">
      {/* Decorative background elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
        <div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-primary/5 blur-[100px]" />
        <div className="absolute top-[40%] -right-[10%] w-[40%] h-[40%] rounded-full bg-blue-500/5 blur-[100px]" />
      </div>

      <Card className="w-full max-w-md p-8 shadow-2xl border-border/50 bg-card/80 backdrop-blur-xl relative z-10">
        <div className="space-y-8">
          <div className="flex flex-col items-center">
            <div className="text-center space-y-2">
              <h1 className="text-2xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary to-blue-600">Daily Stock Analysis</h1>
              <p className="text-sm text-muted-foreground font-medium">每日股票分析系统</p>
            </div>
          </div>
          
          {error && (
            <div className="p-4 rounded-xl bg-destructive/5 border border-destructive/20 text-destructive text-sm flex items-center justify-center font-medium animate-in fade-in slide-in-from-top-2">
              {error}
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-1">
            <div className="relative">
              <div className="absolute left-3 top-3.5 text-muted-foreground z-10">
                <Lock size={16} />
              </div>
              <Input
                type="password"
                placeholder="请输入管理员密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoFocus
                className="pl-9 h-11"
              />
            </div>
          </div>

          <Button 
            type="submit" 
            className="w-full h-11 text-base font-medium shadow-lg shadow-primary/20 transition-all hover:shadow-primary/30" 
            disabled={isLoading || !password}
          >
            {isLoading ? <span className="mr-2"><Spinner size="sm" /></span> : null}
            登录系统
          </Button>
        </form>
        
          <div className="text-center text-xs text-muted-foreground/60 pt-4 border-t border-border/30">
            &copy; {new Date().getFullYear()} DSA Pro. All rights reserved.
          </div>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;

export interface AuthStatus {
  initialized: boolean; // 是否已初始化密码
  authenticated: boolean; // 当前会话是否已认证
  user?: string; // 当前用户名
}

// 后端返回的状态接口
export interface AuthStatusResponse {
  username: string;
  password_initialized: boolean;
  requires_password_setup: boolean;
}

export interface LoginRequest {
  username?: string; // 默认为 admin
  password: string;
}

export interface SetupPasswordRequest {
  username: string;
  password: string;
  confirm_password: string;
}

export interface LoginResponse {
  success: boolean;
  access_token?: string; // 后端返回的是 access_token
  token_type?: string;
  expires_in?: number;
  username?: string;
  message?: string;
  // 兼容旧代码，可能用 token
  token?: string; 
}

export interface SetupPasswordResponse {
  success: boolean;
  message?: string;
  username?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface ChangePasswordResponse {
  success: boolean;
  message?: string;
  username?: string;
}

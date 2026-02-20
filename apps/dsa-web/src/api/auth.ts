import apiClient from './index';
import type {
  AuthStatusResponse,
  LoginRequest,
  LoginResponse,
  SetupPasswordRequest,
  SetupPasswordResponse,
  ChangePasswordRequest,
  ChangePasswordResponse,
} from '../types/auth';

export const authApi = {
  // Check auth status
  async getStatus(): Promise<AuthStatusResponse> {
    const response = await apiClient.get<AuthStatusResponse>(`/api/v1/auth/status?t=${Date.now()}`);
    return response.data;
  },

  // Setup password (first time)
  async setupPassword(data: SetupPasswordRequest): Promise<SetupPasswordResponse> {
    const response = await apiClient.post<SetupPasswordResponse>('/api/v1/auth/setup-password', data);
    return response.data;
  },

  // Login
  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/api/v1/auth/login', data);
    return response.data;
  },

  // Change password
  async changePassword(data: ChangePasswordRequest): Promise<ChangePasswordResponse> {
    const response = await apiClient.post<ChangePasswordResponse>('/api/v1/auth/change-password', data);
    return response.data;
  },
};

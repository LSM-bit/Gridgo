/**
 * 认证相关 API
 */

import request from './rest'

// ─── 类型定义 ───

export interface UserInfo {
  id: number
  username: string
  nickname: string
  avatar: string | null
  status: number
  created_at: string | null
}

export interface TokenData {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface AuthResponse {
  user: UserInfo
  token: TokenData
}

// ─── API 方法 ───

/** 用户注册 */
export function register(data: { username: string; password: string; nickname: string }) {
  return request.post<any, AuthResponse>('/auth/register', data)
}

/** 用户登录 */
export function login(data: { username: string; password: string }) {
  return request.post<any, AuthResponse>('/auth/login', data)
}

/** 刷新 Token */
export function refreshToken(refresh_token: string) {
  return request.post<any, TokenData>('/auth/refresh', { refresh_token })
}

/** 获取当前用户信息 */
export function getMe() {
  return request.get<any, UserInfo>('/auth/me')
}

/** 登出 */
export function logout() {
  return request.post<any, { code: number; message: string }>('/auth/logout')
}

import axios, { type AxiosError, type AxiosResponse } from 'axios';
import { message } from 'antd';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

interface BackendResponse<T = unknown> {
  code?: number;
  data: T;
  message?: string;
}

api.interceptors.response.use(
  (response: AxiosResponse<BackendResponse>) => {
    const res = response.data;
    if (res && res.code !== undefined) {
      if (res.code === 0 || res.code === 200) {
        // Mutate response.data to be the unwrapped payload
        response.data = res.data as BackendResponse;
        return response;
      }
      message.error(res.message || '请求失败');
      return Promise.reject(new Error(res.message || '请求失败'));
    }
    return response;
  },
  (error: AxiosError) => {
    if (error.response) {
      const { status } = error.response;
      if (status === 404) {
        message.error('请求的资源不存在');
      } else if (status === 500) {
        message.error('服务器内部错误');
      } else {
        message.error(`请求失败: ${status}`);
      }
    } else if (error.request) {
      message.error('网络连接失败，请检查网络');
    } else {
      message.error('请求配置错误');
    }
    return Promise.reject(error);
  }
);

/** Convenience wrapper: returns response.data typed as T */
export async function apiGet<T = unknown>(url: string, params?: Record<string, unknown>): Promise<T> {
  const res = await api.get(url, { params });
  return res.data as T;
}

export async function apiPost<T = unknown>(url: string, data?: unknown): Promise<T> {
  const res = await api.post(url, data);
  return res.data as T;
}

export default api;

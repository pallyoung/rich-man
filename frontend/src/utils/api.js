import axios from 'axios';
import { message } from 'antd';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.response.use(
  (response) => {
    const res = response.data;
    if (res && res.code !== undefined) {
      if (res.code === 0 || res.code === 200) {
        return res.data;
      }
      message.error(res.message || '请求失败');
      return Promise.reject(new Error(res.message || '请求失败'));
    }
    return res;
  },
  (error) => {
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

export default api;

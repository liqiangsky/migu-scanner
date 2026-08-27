const baseURL = import.meta.env.PROD ? '/proxy' : '/api';

// 通知来源标识（与后端 NOTIFICATION_SOURCE_* 对应）
const NOTIFICATION_SOURCE = {
  HOST_RETEST: 'HOST_RETEST',
  SUBSCRIPTION: 'SUBSCRIPTION',
};

export { baseURL, NOTIFICATION_SOURCE };
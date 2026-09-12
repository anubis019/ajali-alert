/* === CONFIG === */
const CONFIG = {
  API_BASE: localStorage.getItem('ajali_api_base') || 'https://ajali-api.onrender.com',
  AUTH_ENDPOINT: '/api/v1/auth/login',
  JARVIS: {
    TRIAGE: '/api/v1/jarvis/triage',
    DISPATCH: '/api/v1/jarvis/dispatch-suggest',
    BRIEF: '/api/v1/jarvis/brief/',
    PREDICT: '/api/v1/jarvis/predict',
    CHAT: '/api/v1/jarvis/chat',
  },
  TOKEN_KEY: 'ajali_jwt',
  USER_KEY: 'ajali_user',
  REFRESH_INTERVAL: 15000,
  USSD: { MAX_CHARS: 160, MAX_TURNS: 12, CODE: '*1233#' },
  COUNTIES: ['Nairobi','Mombasa','Kisumu','Nakuru','Kiambu','Eldoret'],
  SEVERITY_LEVELS: ['critical','high','medium','low'],
  TOAST_DURATION: 4000,
  GOLDEN_HOUR_MINUTES: 60,
};
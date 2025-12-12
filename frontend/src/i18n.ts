export type Lang = 'zh-CN' | 'zh-TW' | 'en';

type Translations = {
  [K in Lang]: Record<string, string>;
};

const TRANSLATIONS: Translations = {
  'zh-CN': {
    app_name: 'Lecture Note AI',
    slogan: '听得懂,记得住',
    access_code: '访问码 / 账号',
    password: '密码',
    enter_class: '进入课堂',
    verifying: '验证中...',
    my_lectures: '我的讲座',
    welcome: '欢迎回来,同学',
    start_new: '开始新讲座',
    processing: 'AI 处理中',
    transcript: '逐字稿',
    ai_summary: 'AI 总结',
    export: '导出',
    edit_title: '修改标题',
    save: '保存',
    cancel: '取消',
    live_sync: '实时同步',
    // Error states
    loading: '加载中...',
    error_network: '网络错误,请重试',
    error_auth: '用户名或密码错误',
    error_forbidden: '无权限访问',
    error_not_found: '讲座不存在',
    empty_lectures: '暂无讲座',
    retry: '重试',
    logout: '登出',
  },
  'zh-TW': {
    app_name: 'Lecture Note AI',
    slogan: '聽得懂,記得住',
    access_code: '訪問碼 / 賬號',
    password: '密碼',
    enter_class: '進入課堂',
    verifying: '驗證中...',
    my_lectures: '我的講座',
    welcome: '歡迎回來,同學',
    start_new: '開始新講座',
    processing: 'AI 處理中',
    transcript: '逐字稿',
    ai_summary: 'AI 總結',
    export: '導出',
    edit_title: '修改標題',
    save: '保存',
    cancel: '取消',
    live_sync: '實時同步',
    loading: '加載中...',
    error_network: '網絡錯誤,請重試',
    error_auth: '用戶名或密碼錯誤',
    error_forbidden: '無權限訪問',
    error_not_found: '講座不存在',
    empty_lectures: '暫無講座',
    retry: '重試',
    logout: '登出',
  },
  en: {
    app_name: 'Lecture Note AI',
    slogan: 'Understand Better, Remember More',
    access_code: 'Access Code / ID',
    password: 'Password',
    enter_class: 'Enter Class',
    verifying: 'Verifying...',
    my_lectures: 'My Lectures',
    welcome: 'Welcome back, Student',
    start_new: 'Start New',
    processing: 'Processing',
    transcript: 'Transcript',
    ai_summary: 'AI Summary',
    export: 'Export',
    edit_title: 'Edit Title',
    save: 'Save',
    cancel: 'Cancel',
    live_sync: 'Live Sync',
    loading: 'Loading...',
    error_network: 'Network error, please retry',
    error_auth: 'Invalid username or password',
    error_forbidden: 'Access forbidden',
    error_not_found: 'Lecture not found',
    empty_lectures: 'No lectures yet',
    retry: 'Retry',
    logout: 'Logout',
  },
};

let currentLang: Lang = (localStorage.getItem('echo_lang') as Lang) || 'zh-CN';

export function getLang(): Lang {
  return currentLang;
}

export function setLang(lang: Lang) {
  currentLang = lang;
  localStorage.setItem('echo_lang', lang);
  window.dispatchEvent(new Event('lang-change'));
  window.location.reload();
}

export function t(key: string): string {
  return TRANSLATIONS[currentLang][key] || TRANSLATIONS['zh-CN'][key] || key;
}

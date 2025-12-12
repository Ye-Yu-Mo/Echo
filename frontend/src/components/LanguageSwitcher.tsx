import { useState, useEffect } from 'react';
import { Globe } from 'lucide-react';
import { getLang, setLang, type Lang } from '../i18n';

export function LanguageSwitcher({ className = '' }: { className?: string }) {
  const [currentLang, setCurrentLang] = useState<Lang>(getLang());

  useEffect(() => {
    const handler = () => setCurrentLang(getLang());
    window.addEventListener('lang-change', handler);
    return () => window.removeEventListener('lang-change', handler);
  }, []);

  const toggleLang = () => {
    if (currentLang === 'zh-CN') setLang('zh-TW');
    else if (currentLang === 'zh-TW') setLang('en');
    else setLang('zh-CN');
  };

  const getLabel = (lang: Lang) => {
    switch (lang) {
      case 'zh-CN':
        return '简';
      case 'zh-TW':
        return '繁';
      case 'en':
        return 'EN';
    }
  };

  return (
    <button
      onClick={toggleLang}
      className={`flex items-center space-x-1 px-3 py-1.5 rounded-full bg-slate-100 text-slate-600 text-xs font-medium hover:bg-slate-200 transition ${className}`}
    >
      <Globe size={14} />
      <span>{getLabel(currentLang)}</span>
    </button>
  );
}

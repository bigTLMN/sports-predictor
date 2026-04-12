'use client';

import { useI18n, type Locale } from '@/lib/i18n';

export default function Footer() {
  const { locale, setLocale, t } = useI18n();

  return (
    <footer className="mt-12 py-8 border-t border-slate-200 bg-white">
      <div className="max-w-3xl mx-auto px-4 text-center">
        <div className="flex justify-center gap-2 mb-4">
          {(['en', 'zh-TW'] as Locale[]).map((loc) => (
            <button
              key={loc}
              type="button"
              onClick={() => setLocale(loc)}
              className={`text-[10px] font-black px-2.5 py-1 rounded-full border transition-colors ${
                locale === loc
                  ? 'bg-slate-900 text-white border-slate-900'
                  : 'bg-white text-slate-400 border-slate-200 hover:border-slate-400'
              }`}
            >
              {loc === 'en' ? t('footer.lang.en') : t('footer.lang.zh')}
            </button>
          ))}
        </div>
        <h3 className="text-sm font-black text-slate-800 tracking-tight mb-2">{t('footer.title')}</h3>
        <p className="text-[10px] text-slate-400 leading-relaxed max-w-md mx-auto mb-4">{t('footer.disclaimer')}</p>
        <div className="text-[10px] font-bold text-slate-300">
          © {new Date().getFullYear()} {t('footer.built')}
        </div>
      </div>
    </footer>
  );
}

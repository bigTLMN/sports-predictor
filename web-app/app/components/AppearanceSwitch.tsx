'use client';

import { useI18n } from '@/lib/i18n';
import { useTheme } from '@/lib/theme';

const chip =
  'text-[11px] font-bold px-3 py-1.5 rounded-full border backdrop-blur-md transition-colors ' +
  'bg-white/90 text-slate-800 border-white/50 shadow-sm hover:bg-white ' +
  'dark:bg-black/40 dark:text-white/90 dark:border-white/20 dark:shadow-none dark:hover:bg-black/55 dark:hover:text-white';

export default function AppearanceSwitch() {
  const { locale, setLocale, t } = useI18n();
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex items-center gap-1.5">
      <button
        type="button"
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        className={chip}
      >
        {theme === 'dark' ? t('footer.theme.dark') : t('footer.theme.light')}
      </button>
      <button
        type="button"
        onClick={() => setLocale(locale === 'en' ? 'zh-TW' : 'en')}
        className={chip}
      >
        {locale === 'en' ? t('footer.lang.en') : t('footer.lang.zh')}
      </button>
    </div>
  );
}

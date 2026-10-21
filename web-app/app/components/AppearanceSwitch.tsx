'use client';

import { useI18n } from '@/lib/i18n';
import { useTheme } from '@/lib/theme';

const chip =
  'font-bold rounded-full border backdrop-blur-md transition-colors ' +
  'bg-white/90 text-slate-800 border-white/50 shadow-sm hover:bg-white ' +
  'dark:bg-black/40 dark:text-white/90 dark:border-white/20 dark:shadow-none dark:hover:bg-black/55 dark:hover:text-white';

export default function AppearanceSwitch({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale, t } = useI18n();
  const { theme, setTheme } = useTheme();
  const size = compact ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1.5';

  return (
    <div className={`flex items-center ${compact ? 'gap-1' : 'gap-1.5'}`}>
      <button
        type="button"
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        className={`${chip} ${size}`}
      >
        {theme === 'dark' ? t('footer.theme.dark') : t('footer.theme.light')}
      </button>
      <button
        type="button"
        onClick={() => setLocale(locale === 'en' ? 'zh-TW' : 'en')}
        className={`${chip} ${size}`}
      >
        {locale === 'en' ? t('footer.lang.en') : t('footer.lang.zh')}
      </button>
    </div>
  );
}

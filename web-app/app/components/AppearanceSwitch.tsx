'use client';

import { useI18n } from '@/lib/i18n';
import { useTheme } from '@/lib/theme';

const chip =
  'font-bold rounded-full border backdrop-blur-md transition-colors ' +
  'bg-white/90 text-slate-800 border-white/50 shadow-sm hover:bg-white ' +
  'dark:bg-black/40 dark:text-white/90 dark:border-white/20 dark:shadow-none dark:hover:bg-black/55 dark:hover:text-white';

export default function AppearanceSwitch({ compact = false }: { compact?: boolean }) {
  const { locale, setLocale, t } = useI18n();
  const { theme, setTheme, fontSize, setFontSize } = useTheme();
  const size = compact ? 'text-[12px] px-2 py-0.5' : 'text-[13px] px-3 py-1.5';
  const type = compact ? 'text-[12px] py-0.5' : 'text-[13px] py-1.5';

  return (
    <div className={`flex items-center ${compact ? 'gap-1' : 'gap-1.5'}`}>
      <div className={`${chip} ${type} flex items-center gap-0.5 px-1`}>
        <button
          type="button"
          aria-label={t('footer.fontSmaller')}
          disabled={fontSize <= 12}
          onClick={() => setFontSize(fontSize - 1)}
          className="px-1 disabled:opacity-30"
        >
          −
        </button>
        <span className="min-w-[1.25rem] text-center tabular-nums">{fontSize}</span>
        <button
          type="button"
          aria-label={t('footer.fontLarger')}
          disabled={fontSize >= 18}
          onClick={() => setFontSize(fontSize + 1)}
          className="px-1 disabled:opacity-30"
        >
          +
        </button>
      </div>
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

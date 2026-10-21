'use client';

import { useI18n } from '@/lib/i18n';

export default function Footer() {
  const { t } = useI18n();

  return (
    <footer className="mt-12 py-8 border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-[#0D1117]">
      <div className="max-w-3xl mx-auto px-4 text-center">
        <h3 className="text-base font-black text-slate-800 tracking-tight mb-2 dark:text-slate-100">{t('footer.title')}</h3>
        <p className="text-sm text-slate-400 leading-relaxed max-w-md mx-auto mb-4">{t('footer.disclaimer')}</p>
        <div className="text-sm font-bold text-slate-300 dark:text-slate-600">
          © {new Date().getFullYear()} {t('footer.built')}
        </div>
      </div>
    </footer>
  );
}

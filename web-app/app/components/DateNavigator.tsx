'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { format, addDays, subDays, isValid, parseISO } from 'date-fns';
import { useTransition } from 'react';

export default function DateNavigator() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition(); // 🪄 魔法就在這裡
  
  // 1. 取得並解析目前日期
  const dateParam = searchParams.get('date');
  let currentDate = new Date();
  if (dateParam) {
    const parsed = parseISO(dateParam);
    if (isValid(parsed)) {
      currentDate = parsed;
    }
  }

  // 2. 處理導航函數
  const handleNavigation = (direction: 'prev' | 'next') => {
    const newDate = direction === 'prev' 
      ? subDays(currentDate, 1) 
      : addDays(currentDate, 1);
    
    const dateStr = format(newDate, 'yyyy-MM-dd');

    // 啟動轉場：這會讓 React 知道這是一個背景任務
    startTransition(() => {
      router.push(`/?date=${dateStr}`);
    });
  };

  return (
    <div className="flex items-center justify-center gap-12 my-8">
      {/* 左箭頭 */}
      <button 
        onClick={() => handleNavigation('prev')}
        disabled={isPending}
        className={`group flex items-center justify-center w-10 h-10 bg-white/10 backdrop-blur-md rounded-full border border-white/20 shadow-xl transition-all active:scale-90
          ${isPending ? 'opacity-30 cursor-wait' : 'hover:bg-white/20 hover:border-blue-400/50'}
        `}
        aria-label="Previous Day"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" 
          className={`text-indigo-300 transition-colors ${!isPending && 'group-hover:text-indigo-600'}`}>
          <path d="m15 18-6-6 6-6"/>
        </svg>
      </button>
      
      {/* 中間日期顯示 */}
      <div className={`flex flex-col items-center select-none transition-opacity duration-200 ${isPending ? 'opacity-50' : 'opacity-100'}`}>
        <span className="text-[14px] font-bold tracking-widest bg-gradient-to-r from-[#dfbd69] via-[#855e23] to-[#dfbd69] bg-clip-text text-transparent uppercase mb-3">
          Game Schedule
        </span>
        <div className="flex items-baseline gap-2">
          {isPending ? (
            <div className="flex items-center gap-4 h-8">
                <span className="animate-spin h-5 w-5 border-3 border-slate-100 border-t-slate-800 rounded-full"></span>
                <span className="text-sm font-bold text-slate-600 uppercase transition-opacity duration-1000">UPDATING...</span>
            </div>
          ) : (
            <>
              <span className="text-2xl font-black text-slate-400/80 tracking-tight [text-shadow:_-1px_-1px_1px_white,_1px_1px_1px_rgba(0,0,0,0.2)]">
                {format(currentDate, 'MMMM d')}
              </span>
              <span className="text-base font-black text-slate-400/80 tracking-tight [text-shadow:_-1px_-1px_1px_white,_1px_1px_1px_rgba(0,0,0,0.2)]">
                {format(currentDate, ', yyyy')}
              </span>
            </>
          )}
        </div>
      </div>

      {/* 右箭頭 */}
      <button 
        onClick={() => handleNavigation('next')}
        disabled={isPending}
        className={`group flex items-center justify-center w-10 h-10 bg-white/10 backdrop-blur-md rounded-full border border-white/20 shadow-xl transition-all active:scale-90
          ${isPending ? 'opacity-30 cursor-wait' : 'hover:bg-white/20 hover:border-blue-400/50'}
        `}
        aria-label="Next Day"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" 
          className={`text-indigo-300 transition-colors ${!isPending && 'group-hover:text-indigo-600'}`}>
          <path d="m9 18 6-6-6-6"/>
        </svg>
      </button>
    </div>
  );
}
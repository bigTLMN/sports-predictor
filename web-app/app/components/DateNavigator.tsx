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
    <div className="flex items-center justify-center gap-6 my-8">
      {/* 左箭頭 */}
      <button 
        onClick={() => handleNavigation('prev')}
        disabled={isPending}
        className={`group flex items-center justify-center w-10 h-10 bg-white rounded-full shadow-sm border border-gray-200 transition-all active:scale-95
          ${isPending ? 'opacity-50 cursor-wait' : 'hover:bg-blue-50 hover:border-blue-200'}
        `}
        aria-label="Previous Day"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`text-gray-500 transition-colors ${!isPending && 'group-hover:text-blue-600'}`}>
          <path d="m15 18-6-6 6-6"/>
        </svg>
      </button>
      
      {/* 中間日期顯示 */}
      <div className={`flex flex-col items-center select-none transition-opacity duration-200 ${isPending ? 'opacity-50' : 'opacity-100'}`}>
        <span className="text-[10px] font-bold tracking-widest text-gray-400 uppercase mb-1">
          Game Schedule
        </span>
        <div className="flex items-baseline gap-2">
          {isPending ? (
            // 讀取時顯示轉圈圈或 Loading 文字
            <div className="flex items-center gap-2 h-8">
                <span className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-blue-600 rounded-full"></span>
                <span className="text-sm font-bold text-gray-400">UPDATING...</span>
            </div>
          ) : (
            <>
              <span className="text-2xl font-black text-gray-800 tracking-tight">
                {format(currentDate, 'MMMM d')}
              </span>
              <span className="text-sm font-semibold text-gray-400">
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
        className={`group flex items-center justify-center w-10 h-10 bg-white rounded-full shadow-sm border border-gray-200 transition-all active:scale-95
          ${isPending ? 'opacity-50 cursor-wait' : 'hover:bg-blue-50 hover:border-blue-200'}
        `}
        aria-label="Next Day"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`text-gray-500 transition-colors ${!isPending && 'group-hover:text-blue-600'}`}>
          <path d="m9 18 6-6-6-6"/>
        </svg>
      </button>
    </div>
  );
}
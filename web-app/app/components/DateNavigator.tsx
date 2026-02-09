'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { format, addDays, subDays, isValid, parseISO } from 'date-fns';
import { useTransition, useRef } from 'react'; // 🔥 1. 引入 useRef

export default function DateNavigator() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition(); 
  const dateInputRef = useRef<HTMLInputElement>(null); // 🔥 2. 建立 Ref
  
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

    startTransition(() => {
      router.push(`/?date=${dateStr}`);
    });
  };

  // 3. 處理日期選擇器變更
  const handleDateSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const dateStr = e.target.value;
    if (dateStr) {
        startTransition(() => {
            router.push(`/?date=${dateStr}`);
        });
    }
  };

  // 🔥 4. 新增：強制開啟日曆的函數
  const openDatePicker = () => {
    try {
      // showPicker 是現代瀏覽器 API，能直接叫出日曆
      if (dateInputRef.current && 'showPicker' in dateInputRef.current) {
        dateInputRef.current.showPicker();
      } else {
        // 舊瀏覽器 fallback (雖然現在很少見了)
        dateInputRef.current?.focus();
      }
    } catch (error) {
      console.error("Browser doesn't support showPicker", error);
    }
  };

  return (
    <div className="flex items-center justify-between px-4 py-4 bg-[#0D1117] rounded-xl border border-slate-800 relative">
      
      {/* 左箭頭: 前一天 */}
      <button 
        onClick={() => handleNavigation('prev')}
        disabled={isPending}
        className={`p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-all ${isPending ? 'opacity-30' : ''}`}
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7"></path></svg>
      </button>

      {/* 中間：日期顯示區塊 */}
      {/* 🔥 5. 在父層 Div 加上 onClick，點擊整個區域都能觸發 */}
      <div 
        onClick={openDatePicker} 
        className={`relative group cursor-pointer text-center select-none transition-opacity duration-200 ${isPending ? 'opacity-50' : 'opacity-100'}`}
      >
        
        {/* 星期幾 (小字) */}
        <div className="text-sm font-bold text-slate-400 uppercase tracking-widest group-hover:text-orange-500 transition-colors">
            {format(currentDate, 'EEEE')}
        </div>
        
        {/* 日期 (大字) */}
        <div className="text-xl font-black text-white tracking-tight flex items-center justify-center gap-2">
            {format(currentDate, 'MMM dd, yyyy')}
            <svg className="w-4 h-4 text-slate-500 group-hover:text-orange-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
        </div>
        
        {/* 🔥 6. Input 修改： */}
        {/* - 加入 ref={dateInputRef} */}
        {/* - 加入 pointer-events-none：讓滑鼠點擊可以直接穿透 input 打到下方的 div，觸發 onClick */}
        {/* - 這樣我們就不依賴 input 自己的點擊判定，而是由我們手動控制 */}
        <input 
            ref={dateInputRef}
            type="date" 
            value={format(currentDate, 'yyyy-MM-dd')}
            onChange={handleDateSelect}
            className="absolute inset-0 w-full h-full opacity-0 pointer-events-none"
        />
      </div>

      {/* 右箭頭: 後一天 */}
      <button 
        onClick={() => handleNavigation('next')}
        disabled={isPending}
        className={`p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-all ${isPending ? 'opacity-30' : ''}`}
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
      </button>
    </div>
  );
}
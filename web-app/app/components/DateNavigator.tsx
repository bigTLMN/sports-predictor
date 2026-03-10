'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { format, addDays, subDays, isValid, parseISO } from 'date-fns';
import { useTransition, useRef } from 'react';

export default function DateNavigator() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition(); 
  const dateInputRef = useRef<HTMLInputElement>(null);
  
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

  // 4. (備用) 強制開啟日曆
  // 雖然這段在 Mobile 沒用，但在 PC 某些舊瀏覽器可能還是有輔助效果
  const openDatePicker = () => {
    const input = dateInputRef.current;
    if (!input) return;

    try {
      if (typeof (input as any).showPicker === 'function') {
        (input as any).showPicker();
      } else {
        input.focus();
      }
    } catch (error) {
      console.error("Browser doesn't support showPicker", error);
    }
  };

  return (
    <div className="flex items-center justify-between px-4 py-4 bg-[#0D1117] rounded-xl border border-slate-800 relative">
      
      {/* 左箭頭: 前一天 */}
      {/* 加上 z-20 確保箭頭浮在 input 之上，不然會按不到箭頭 */}
      <button 
        onClick={() => handleNavigation('prev')}
        disabled={isPending}
        className={`relative z-20 p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-all ${isPending ? 'opacity-30' : ''}`}
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7"></path></svg>
      </button>

      {/* 中間：日期顯示區塊 */}
      {/* 這裡的 onClick 變成 PC 的輔助，Mobile 主要靠 input 自己 */}
      <div 
        onClick={openDatePicker}
        className={`relative group cursor-pointer text-center select-none transition-opacity duration-200 flex-1 ${isPending ? 'opacity-50' : 'opacity-100'}`}
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
        
        {/* 🔥 關鍵修正：
            1. 移除 pointer-events-none (讓手指能真正點到它)
            2. 加入 z-10 (確保它覆蓋在文字上面)
            3. 加入 cursor-pointer (PC 滑鼠變手指)
        */}
        <input 
            ref={dateInputRef}
            type="date" 
            value={format(currentDate, 'yyyy-MM-dd')}
            onChange={handleDateSelect}
            // 修改這裡：不再強制 w-full，而是給它一個適中的寬度並 mx-auto 置中
            className="absolute inset-0 w-[200px] mx-auto opacity-0 z-10 cursor-pointer"
        />
      </div>

      {/* 右箭頭: 後一天 */}
      {/* 加上 z-20 確保箭頭浮在 input 之上 */}
      <button 
        onClick={() => handleNavigation('next')}
        disabled={isPending}
        className={`relative z-20 p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-all ${isPending ? 'opacity-30' : ''}`}
      >
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7"></path></svg>
      </button>
    </div>
  );
}
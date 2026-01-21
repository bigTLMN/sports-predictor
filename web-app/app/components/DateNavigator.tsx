'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { format, addDays, subDays } from 'date-fns';

export default function DateNavigator() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // 1. 取得目前選中的日期
  const dateParam = searchParams.get('date');
  
  // --- 修改重點 ---
  // 如果沒有參數，預設使用「今天」，而不是明天
  const currentDate = dateParam ? new Date(dateParam) : new Date();

  const handlePrev = () => {
    const prevDate = subDays(currentDate, 1);
    router.push(`/?date=${format(prevDate, 'yyyy-MM-dd')}`);
  };

  const handleNext = () => {
    const nextDate = addDays(currentDate, 1);
    router.push(`/?date=${format(nextDate, 'yyyy-MM-dd')}`);
  };

  return (
    <div className="flex items-center justify-center gap-4 my-6 bg-white p-3 rounded-lg shadow-sm border border-gray-100 max-w-xs mx-auto">
      <button 
        onClick={handlePrev}
        className="p-2 hover:bg-gray-100 rounded-full text-gray-600 transition"
      >
        ←
      </button>
      
      <div className="text-center">
        <div className="text-xs text-gray-400 uppercase font-bold">Game Date</div>
        <div className="text-lg font-bold text-gray-800">
          {format(currentDate, 'yyyy-MM-dd')}
        </div>
      </div>

      <button 
        onClick={handleNext}
        className="p-2 hover:bg-gray-100 rounded-full text-gray-600 transition"
      >
        →
      </button>
    </div>
  );
}
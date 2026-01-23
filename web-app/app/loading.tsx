export default function Loading() {
  return (
    <main className="min-h-screen bg-gray-50 p-4 md:p-8 font-sans">
      <div className="max-w-3xl mx-auto">
        {/* 標題骨架 (Title Skeleton) */}
        <div className="h-10 bg-gray-200 rounded w-48 mx-auto mb-2 animate-pulse"></div>
        <div className="h-4 bg-gray-200 rounded w-32 mx-auto mb-6 animate-pulse"></div>

        {/* 日期導航器骨架 (Date Navigator Skeleton) */}
        <div className="flex items-center justify-center gap-6 my-8">
          {/* 左箭頭圓圈 */}
          <div className="w-10 h-10 bg-gray-200 rounded-full animate-pulse"></div>
          
          {/* 中間日期文字 */}
          <div className="flex flex-col items-center gap-2">
            <div className="h-3 w-24 bg-gray-200 rounded animate-pulse"></div>
            <div className="h-8 w-40 bg-gray-200 rounded animate-pulse"></div>
          </div>
          
          {/* 右箭頭圓圈 */}
          <div className="w-10 h-10 bg-gray-200 rounded-full animate-pulse"></div>
        </div>

        {/* 戰績儀表板骨架 (Stats Dashboard Skeleton) */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 mb-6 h-32 animate-pulse">
          {/* 上方切換按鈕 */}
          <div className="flex justify-center gap-2 mb-4">
            <div className="h-6 w-20 bg-gray-200 rounded-full"></div>
            <div className="h-6 w-20 bg-gray-200 rounded-full"></div>
            <div className="h-6 w-20 bg-gray-200 rounded-full"></div>
          </div>
          {/* 下方數據區塊 */}
          <div className="grid grid-cols-2 gap-4 h-16">
            <div className="bg-gray-100 rounded"></div>
            <div className="bg-gray-100 rounded"></div>
          </div>
        </div>

        {/* 預測卡片列表骨架 (Cards Skeleton) */}
        <div className="grid gap-4 md:grid-cols-2">
          {/* 產生 4 張假卡片 */}
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-200 h-48 animate-pulse p-4 flex flex-col justify-between">
              {/* 卡片頭部 */}
              <div className="flex justify-between mb-4">
                <div className="h-4 w-20 bg-gray-200 rounded"></div>
                <div className="h-4 w-12 bg-gray-200 rounded"></div>
              </div>
              
              {/* 隊伍與 Logo 區 */}
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-gray-200 rounded-full"></div>
                <div className="flex-1">
                   <div className="h-6 w-3/4 bg-gray-200 rounded mb-2"></div>
                   <div className="h-3 w-1/2 bg-gray-200 rounded"></div>
                </div>
              </div>

              {/* 底部數據 */}
              <div className="h-8 w-full bg-gray-100 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
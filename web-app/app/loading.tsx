export default function Loading() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#1F2937] to-[#030712] font-sans flex flex-col text-white">
      
      {/* 1. 頂部裝飾條 (保持與首頁一致，避免視覺跳動) */}
      <div className="h-[3px] w-full bg-gradient-to-r from-[#855e23] via-[#dfbd69] to-[#855e23] shadow-[0_0_12px_#dfbd69] brightness-110" />

      <main className="flex-1 p-4 md:p-8 flex flex-col items-center justify-start pt-12">
        <div className="w-full max-w-3xl mx-auto px-4 md:px-0 space-y-12">
          
          {/* 2. Hero Banner Skeleton (閃爍的骨架) */}
          <div className="relative w-full h-48 md:h-60 overflow-hidden rounded-2xl border border-white/10 bg-[#0D1117]">
            {/* 掃光動畫 */}
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full animate-[shimmer_1.5s_infinite]" />
            
            <div className="absolute inset-0 flex flex-col justify-center p-8 md:p-12 space-y-4">
              <div className="h-12 w-3/4 bg-slate-800/50 rounded-lg animate-pulse" />
              <div className="flex gap-3">
                <div className="h-6 w-24 bg-slate-800/50 rounded animate-pulse" />
                <div className="h-6 w-32 bg-slate-800/50 rounded animate-pulse" />
              </div>
            </div>
          </div>

          {/* 3. Date Navigator Skeleton */}
          <div className="h-16 w-full bg-[#0D1117] rounded-xl border border-white/5 animate-pulse flex items-center justify-between px-4">
            <div className="w-8 h-8 bg-slate-800 rounded-lg" />
            <div className="flex flex-col items-center gap-2">
                <div className="w-20 h-3 bg-slate-800 rounded" />
                <div className="w-32 h-6 bg-slate-800 rounded" />
            </div>
            <div className="w-8 h-8 bg-slate-800 rounded-lg" />
          </div>

          {/* 4. Loading Text & Spinner */}
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <div className="relative">
                {/* 外圈旋轉 */}
                <div className="w-12 h-12 rounded-full border-4 border-slate-800 border-t-orange-500 animate-spin" />
                {/* 內圈發光 */}
                <div className="absolute inset-0 rounded-full blur-md bg-orange-500/20" />
            </div>
            <div className="text-center space-y-1">
                <p className="text-sm font-bold text-orange-500 tracking-widest uppercase animate-pulse">
                    Analyzing Market Data
                </p>
                <p className="text-xs text-slate-500 font-mono">
                    Locating latest schedule & odds...
                </p>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}
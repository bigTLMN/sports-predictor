import { supabase } from '@/lib/supabase';

// 設定不快取，確保每次重整都抓新資料
export const revalidate = 0;

// 定義資料庫回傳的型別 (TypeScript 專用)
interface Team {
  code: string;
  full_name?: string;
  logo_url?: string;
}

interface Match {
  date: string;
  home_team: Team;
  away_team: Team;
}

interface Pick {
  confidence_score: number;
  consensus_logic: string;
  matches: Match;
  recommended_team: Team;
}

export default async function Home() {
  // 1. 從 Supabase 抓取資料
  const { data, error } = await supabase
    .from('aggregated_picks')
    .select(`
      confidence_score,
      consensus_logic,
      matches (
        date,
        home_team: teams!matches_home_team_id_fkey (code, full_name),
        away_team: teams!matches_away_team_id_fkey (code, full_name)
      ),
      recommended_team: teams!aggregated_picks_recommended_team_id_fkey (code, logo_url)
    `)
    .order('confidence_score', { ascending: false });

  if (error) {
    console.error("Error fetching data:", error);
    return <div className="p-10 text-red-500">讀取資料發生錯誤，請檢查終端機。</div>;
  }

  // 強制轉型：告訴 TypeScript "我相信回傳的資料符合 Pick[] 結構"
  // 在正式專案中我們會用 Zod 做驗證，但 MVP 這樣最快
  const picks = data as any as Pick[];

  return (
    <main className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-8 text-center">
          🏀 AI 賽事預測聚合平台
        </h1>

        <div className="grid gap-6 md:grid-cols-2">
          {picks?.map((pick, index) => (
            <div key={index} className="bg-white rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow border border-gray-200">
              {/* 卡片頭部：比賽隊伍 */}
              <div className="bg-gray-50 px-6 py-4 border-b border-gray-100 flex justify-between items-center">
                <span className="text-sm text-gray-500 font-mono">
                  {new Date(pick.matches.date).toLocaleDateString()}
                </span>
                <span className="font-bold text-gray-700">
                  {pick.matches.away_team.code} vs {pick.matches.home_team.code}
                </span>
              </div>

              {/* 卡片內容：推薦結果 */}
              <div className="p-6 flex items-center justify-between">
                <div>
                  <p className="text-xs text-gray-400 uppercase tracking-wide">System Pick</p>
                  <div className="flex items-center gap-3 mt-1">
                    <div className="text-2xl font-black text-blue-600">
                      {pick.recommended_team.code}
                    </div>
                    <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                      WIN
                    </span>
                  </div>
                </div>

                {/* 信心指數 */}
                <div className="text-right">
                  <div className="text-3xl font-bold text-green-600">
                    {pick.confidence_score}%
                  </div>
                  <p className="text-xs text-gray-400">Confidence</p>
                </div>
              </div>

              {/* 底部邏輯 */}
              <div className="px-6 py-3 bg-gray-50 text-xs text-gray-500 border-t border-gray-100">
                💡 Logic: {pick.consensus_logic}
              </div>
            </div>
          ))}

          {(!picks || picks.length === 0) && (
            <div className="col-span-2 text-center text-gray-500 py-10">
              目前沒有推薦賽事，請先執行 Python 爬蟲。
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
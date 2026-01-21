import { supabase } from '@/lib/supabase';

export const revalidate = 0;

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
  spread_logic?: string;
  line_info?: string;
  ou_pick?: string;      // 新增
  ou_line?: number;      // 新增
  ou_confidence?: number;// 新增
  matches: Match;
  recommended_team: Team;
}

export default async function Home() {
  const { data, error } = await supabase
    .from('aggregated_picks')
    .select(`
      confidence_score,
      consensus_logic,
      spread_logic,
      line_info,
      ou_pick,
      ou_line,
      ou_confidence,
      matches (
        date,
        home_team: teams!matches_home_team_id_fkey (code, full_name),
        away_team: teams!matches_away_team_id_fkey (code, full_name)
      ),
      recommended_team: teams!aggregated_picks_recommended_team_id_fkey (code, logo_url)
    `)
    .order('confidence_score', { ascending: false });

  if (error) {
    console.error(error);
    return <div className="p-10 text-red-500">讀取資料發生錯誤</div>;
  }

  const picks = data as any as Pick[];

  return (
    <main className="min-h-screen bg-gray-100 p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-8 text-center">
          🏀 AI 賽事預測 (Next Day)
        </h1>

        <div className="grid gap-6 md:grid-cols-2">
          {picks?.map((pick, index) => (
            <div key={index} className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-200">
              
              {/* Header */}
              <div className="bg-gray-50 px-6 py-3 border-b border-gray-100 flex justify-between items-center">
                <span className="text-sm text-gray-500 font-mono">
                  {new Date(pick.matches.date).toLocaleDateString()}
                </span>
                <span className="font-bold text-gray-700">
                  {pick.matches.away_team.code} @ {pick.matches.home_team.code}
                </span>
              </div>

              {/* Spread Pick Section */}
              <div className="p-5 border-b border-gray-100">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-bold text-gray-400 uppercase">Spread Pick</span>
                  <span className="text-xs bg-gray-200 px-2 py-1 rounded text-gray-600 font-mono">
                    {pick.line_info || 'PK'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                   <div className="flex items-center gap-3">
                      {pick.recommended_team.logo_url && (
                        <img src={pick.recommended_team.logo_url} className="w-10 h-10 object-contain" alt="" />
                      )}
                      <div>
                        <div className="text-2xl font-black text-blue-600 leading-none">
                          {pick.recommended_team.code}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">{pick.spread_logic}</div>
                      </div>
                   </div>
                   <div className="text-right">
                      <div className="text-2xl font-bold text-green-600">{pick.confidence_score}%</div>
                   </div>
                </div>
              </div>

              {/* O/U Pick Section (New!) */}
              {pick.ou_pick && (
                <div className="px-5 py-3 bg-blue-50 flex justify-between items-center">
                   <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-blue-400 uppercase">Total</span>
                      <span className={`text-lg font-bold ${pick.ou_pick === 'OVER' ? 'text-red-500' : 'text-blue-600'}`}>
                        {pick.ou_pick} {pick.ou_line}
                      </span>
                   </div>
                   <div className="text-sm font-semibold text-gray-600">
                     {pick.ou_confidence}% Conf.
                   </div>
                </div>
              )}

            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
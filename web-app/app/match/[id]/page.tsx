import { supabase } from '@/lib/supabase';
import { notFound } from 'next/navigation';
import MatchDetailView from './MatchDetailView';

export const revalidate = 0;

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function MatchDetail({ params }: PageProps) {
  const { id } = await params;

  const { data: pick } = await supabase
    .from('aggregated_picks')
    .select(
      `
      *,
      matches!inner (
        *,
        home_team: teams!matches_home_team_id_fkey (*),
        away_team: teams!matches_away_team_id_fkey (*)
      ),
      recommended_team: teams!aggregated_picks_recommended_team_id_fkey (*)
    `
    )
    .eq('match_id', id)
    .single();

  if (!pick) {
    return notFound();
  }

  return <MatchDetailView pick={pick} />;
}

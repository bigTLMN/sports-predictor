import { loadSnapshot, pickForMatch } from '@/lib/snapshot.mjs';
import { notFound } from 'next/navigation';
import MatchDetailView from './MatchDetailView';

export const revalidate = 0;

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function MatchDetail({ params }: PageProps) {
  const { id } = await params;

  const snapshot = await loadSnapshot();
  const pick = pickForMatch(snapshot, id);

  if (!pick) {
    return notFound();
  }

  return <MatchDetailView pick={pick} />;
}

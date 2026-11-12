import { getGuide } from '../../../../lib/counterGuide';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const normalize = (text: string) => text.toLocaleLowerCase('ko-KR').replace(/\s+/gu, '');

export function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const lane = searchParams.get('lane') ?? '';
  const q = searchParams.get('q') ?? '';
  const data = getGuide();
  if (!Object.prototype.hasOwnProperty.call(data.lanes, lane) || lane.length > 10 || q.length > 100) {
    return Response.json({ detail: 'Unknown lane or invalid query' }, { status: 422 });
  }
  const query = normalize(q);
  const items = data.champions.filter(champion => champion.lanes.includes(lane) &&
    [champion.name, champion.initials, ...(champion.aliases ?? [])].some(value => normalize(value).includes(query)));
  return Response.json({ items });
}

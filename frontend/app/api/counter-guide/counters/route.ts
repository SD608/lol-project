import { getGuide, getCounterRows } from '../../../../lib/counterGuide';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const lane = searchParams.get('lane') ?? '';
  const opponent = searchParams.get('opponent') ?? '';
  const data = getGuide();

  if (!Object.prototype.hasOwnProperty.call(data.lanes, lane) ||
      lane.length > 10 || opponent.length > 100) {
    return Response.json({ detail: 'Unknown lane or invalid query' }, { status: 422 });
  }
  if (!data.lanes[lane].includes(opponent)) {
    return Response.json({ detail: 'Opponent not registered in lane' }, { status: 404 });
  }
  return Response.json({
    patch: data.patch,
    lane,
    opponent,
    groups: getCounterRows(lane, opponent),
    note: '통계 확인은 제공 엑셀의 승률·표본 확인 분류입니다. 이론 참고는 검증 전 가설이며 실제 승률이 아닙니다.',
  });
}

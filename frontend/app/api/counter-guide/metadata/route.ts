import { getGuide } from '../../../../lib/counterGuide';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export function GET() {
  const { patch, ddragon_version, counts, lanes } = getGuide();
  return Response.json({ patch, ddragon_version, counts, lanes: Object.keys(lanes) });
}

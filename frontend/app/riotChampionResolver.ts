/**
 * Resolve Riot Data Dragon champion IDs using the official localized roster.
 *
 * PICKOU's existing PostgreSQL champions table contains NULL riot_id values;
 * guessing an English filename from a Korean name would be unreliable.
 * This resolver uses the official Korean roster for the same Data Dragon build.
 * Failed requests are removed from the cache so retries remain possible.
 */
export type RiotChampion = { name: string; riot_id?: string | null };
type RosterEntry = { id?: string; name?: string };
type RosterResponse = { data?: Record<string, RosterEntry> };

const CDN = "https://ddragon.leagueoflegends.com";
const rosterCache = new Map<string, Promise<Record<string, RosterEntry>>>();

export function normalizeChampionName(name: string): string {
  return name.normalize("NFKC").toLocaleLowerCase("ko-KR").replace(/[\s\p{P}\p{S}]/gu, "");
}

export async function fetchOfficialRoster(version: string): Promise<Record<string, RosterEntry>> {
  if (!/^\d+\.\d+\.\d+$/.test(version)) throw new Error("공식 데이터 버전 형식이 올바르지 않습니다.");
  const cached = rosterCache.get(version);
  if (cached) return cached;

  const pending = (async () => {
    const url = `${CDN}/cdn/${encodeURIComponent(version)}/data/ko_KR/champion.json`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`공식 챔피언 목록을 불러오지 못했습니다 (HTTP ${response.status}).`);
    const body = await response.json() as RosterResponse;
    if (!body.data || !Object.keys(body.data).length) throw new Error("공식 챔피언 목록이 비어 있습니다.");
    return body.data;
  })();
  rosterCache.set(version, pending);
  pending.catch(() => { if (rosterCache.get(version) === pending) rosterCache.delete(version); });
  return pending;
}

export function resolveOfficialChampionId(
  champion: RiotChampion,
  roster: Record<string, RosterEntry>,
): string {
  const wanted = normalizeChampionName(champion.name);
  const matching = Object.entries(roster).filter(([, row]) =>
    typeof row.name === "string" && normalizeChampionName(row.name) === wanted
  );

  if (matching.length === 1) {
    const [key, row] = matching[0];
    const id = row.id || key;
    if (/^[a-zA-Z0-9]+$/.test(id)) return id;
  }
  if (matching.length > 1) throw new Error(`${champion.name}: 공식 챔피언 이름이 중복되어 ID를 확정할 수 없습니다.`);

  // When the Korean labels differ, accept a DB ID only if it is an exact
  // registered ID in the SAME official roster (not a fabricated filename).
  const supplied = champion.riot_id;
  if (supplied && /^[a-zA-Z0-9]+$/.test(supplied)) {
    const official = roster[supplied];
    if (official?.id === supplied) return supplied;
  }
  throw new Error(`${champion.name}: 공식 챔피언 명단에서 영문 ID를 찾지 못했습니다. 라이엇 한글 명칭을 확인해 주세요.`);
}

export async function resolveChampionId(version: string, champion: RiotChampion): Promise<string> {
  const roster = await fetchOfficialRoster(version);
  return resolveOfficialChampionId(champion, roster);
}

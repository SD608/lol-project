"use client";

type Champion = { name: string; riot_id?: string | null };
const OP_GG_LANES: Record<string, string> = {
  "탑": "top", "정글": "jungle", "미드": "mid", "바텀": "adc", "서폿": "support",
};

/**
 * Only generate an external navigation URL; never fetch or scrape third-party stats.
 * Riot IDs are controlled by the champions API rather than user-entered strings.
 */
export function opggCounterUrl(champion: Champion | undefined, lane: string): string | null {
  const id = champion?.riot_id;
  const position = OP_GG_LANES[lane];
  if (!id || !position || !/^[a-zA-Z0-9]+$/.test(id)) return null;
  return `https://op.gg/lol/champions/${id.toLowerCase()}/counters/${position}`;
}

export default function ExternalStatsLink({
  champion, lane,
}: { champion: Champion | undefined; lane: string }) {
  const url = opggCounterUrl(champion, lane);
  const destination = url || "https://op.gg/lol/champions";
  return <section className="box external-reference">
    <div>
      <h2>OP.GG에서 상성 확인</h2>
      <p className="muted">
        {champion?.name || "선택한 챔피언"} · {lane}의 OP.GG 통계를 확인하세요.
        {url ? "해당 챔피언의 상성 페이지로 연결됩니다." : "챔피언 ID를 확인할 수 없어 OP.GG 챔피언 목록으로 연결됩니다. 해당 챔피언과 라인을 직접 선택하세요."}
      </p>
      <p className="muted reference-note">
        외부 통계는 PICKOU의 검증된 추천 등급이 아닙니다.
        OP.GG에서 표시되는 지역·티어·패치·표본 수를 직접 확인하세요.
        비주류 라인은 통계가 부족하거나 표시되지 않을 수 있습니다.
      </p>
    </div>
    <a className="external-reference-link" href={destination} target="_blank" rel="noopener noreferrer">
      {url ? "OP.GG 상성 열기 ↗" : "OP.GG 챔피언 목록 열기 ↗"}
    </a>
  </section>;
}

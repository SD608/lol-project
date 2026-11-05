"use client";

import { useCallback, useEffect, useState } from "react";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const LANES = ["전체", "탑", "정글", "미드", "바텀", "서폿"];
type LaneStat = { lane: string; matchups: number };
type Match = {
  id: string; lane: string; champion: string; opponent: string;
  position: "pick" | "enemy"; review_status: "potential_review";
  actual_effect_verified: false;
};
type Impact = {
  champion: string; lane: string | null; total: number; limit: number; offset: number;
  lanes: LaneStat[]; items: Match[]; note: string;
};

export default function PatchImpact({ champion, patch }: { champion: string; patch: string }) {
  const [lane, setLane] = useState("전체");
  const [page, setPage] = useState(0);
  const [impact, setImpact] = useState<Impact | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const limit = 20;

  const load = useCallback(async (signal: AbortSignal) => {
    setLoading(true);
    setError("");
    setImpact(null);
    try {
      const query = new URLSearchParams({ champion, limit: String(limit), offset: String(page * limit) });
      if (lane !== "전체") query.set("lane", lane);
      const response = await fetch(API_BASE + "/api/v1/patch-impact?" + query.toString(), { signal, cache: "no-store" });
      if (!response.ok) throw new Error(response.status === 503 ? "백엔드의 데이터베이스 연결을 확인해 주세요." : "API 응답 오류 (" + response.status + ")");
      const payload = await response.json() as Impact;
      if (!signal.aborted) setImpact(payload);
    } catch (e: unknown) {
      if (!signal.aborted) setError(e instanceof Error ? e.message : "조회 실패");
    } finally {
      if (!signal.aborted) setLoading(false);
    }
  }, [champion, lane, page]);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return <section className="patch-impact-panel" aria-label={champion + " 관련 대진"}>
    <h3>패치 {patch} · 관련 대진 재검토 후보</h3>
    <p className="muted">기존 PostgreSQL에 등록된 {champion} 포함 대진을 찾았어. <strong>관련 대진이라는 사실만 확인한 것이며, 실제 상성 변화가 발생했다는 뜻은 아니야.</strong></p>
    <div className="patch-impact-controls">
      <label>라인 필터
        <select value={lane} onChange={(e) => { setLane(e.target.value); setPage(0); }}>
          {LANES.map((value) => <option key={value} value={value}>{value}</option>)}
        </select>
      </label>
      <button type="button" onClick={() => void load(new AbortController().signal)} disabled={loading}>다시 조회</button>
    </div>
    {loading ? <p className="muted" role="status">관련 대진 조회 중…</p> : error ?
      <p className="error-message" role="alert">{error} FastAPI 서버를 실행 중인지 확인해 줘.</p> :
      impact ? <>
        <p className="patch-impact-summary">등록된 방향성 대진 <strong>{impact.total.toLocaleString("ko-KR")}개</strong> · 실제 효과 <strong>미검증</strong></p>
        {impact.lanes.length > 0 && <div className="patch-impact-lanes">
          {impact.lanes.map((row) => <span key={row.lane}>{row.lane} {row.matchups}건</span>)}
        </div>}
        {impact.items.length ? <div className="patch-impact-list">
          {impact.items.map((row) => <div className="patch-impact-row" key={row.id}>
            <span>{row.lane}</span>
            <strong>{row.champion} → {row.opponent}</strong>
            <span>{row.position === "pick" ? "변경 챔피언이 내 픽" : "변경 챔피언이 상대 픽"}</span>
            <span>재검토 후보</span>
          </div>)}
        </div> : <p className="muted">현재 해당 라인에 등록된 관련 대진이 없어. 오프메타 경기는 아직 별도 수집 대상이야.</p>}
        {impact.total > limit && <div className="patch-impact-pagination">
          <button type="button" disabled={page === 0} onClick={() => setPage((value) => Math.max(0, value - 1))}>이전</button>
          <span>{page + 1} / {Math.ceil(impact.total / limit)} 페이지</span>
          <button type="button" disabled={(page + 1) * limit >= impact.total} onClick={() => setPage((value) => value + 1)}>다음</button>
        </div>}
      </> : null}
    <p className="muted patch-impact-footnote">챔피언 변경만 직접 연결해. 아이템 변경은 실제 사용 챔피언·빌드 데이터가 없어서 특정 매치업의 영향으로 연결하지 않아.</p>
  </section>;
}

"use client";

import { useEffect, useState } from "react";
import ChampionSearch from "./ChampionSearch";

type Champion = { name: string; riot_id?: string | null; aliases?: string[]; initials?: string | null };
type Lane = { lane: string; champion_count: number };
type Matchup = { id: string; lane: string; champion: string; opponent: string; rating: string | null; status: string };
type MatchupDetail = Matchup & {
  patch?: string | null;
  statistics?: { sample_size?: number; metrics?: unknown; sources?: unknown } | null;
  decision?: { status?: string; rating?: string | null; evidence?: unknown } | null;
  validation_history?: unknown[];
};
type Page = "홈" | "상성 조회" | "조합 분석" | "패치 노트" | "통계" | "즐겨찾기" | "설정";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const MENUS: Page[] = ["홈", "상성 조회", "조합 분석", "패치 노트", "통계", "즐겨찾기", "설정"];
const LANES = ["탑", "정글", "미드", "바텀", "서폿"];

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(API_BASE + path, { cache: "no-store" });
  if (!response.ok) throw new Error(response.status === 503 ? "데이터베이스 연결을 확인해 주세요." : `API 응답 오류 (${response.status})`);
  return response.json() as Promise<T>;
}

function Nav({ active, onSelect }: { active: Page; onSelect: (page: Page) => void }) {
  return <nav className="nav-list" aria-label="기본 메뉴">
    {MENUS.map((item) => <button key={item} type="button" className={active === item ? "nav-link is-active" : "nav-link"} onClick={() => onSelect(item)} aria-current={active === item ? "page" : undefined}>{item}</button>)}
  </nav>;
}

export default function Home() {
  const [page, setPage] = useState<Page>("상성 조회");
  const [menuOpen, setMenuOpen] = useState(false);
  const [champions, setChampions] = useState<Champion[]>([]);
  const [lanes, setLanes] = useState<Lane[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [optionsError, setOptionsError] = useState("");
  const [myChampion, setMyChampion] = useState("");
  const [opponent, setOpponent] = useState("");
  const [lane, setLane] = useState("탑");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [result, setResult] = useState<MatchupDetail | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [recent, setRecent] = useState<Array<{ lane: string; mine: string; versus: string }>>([]);

  useEffect(() => {
    let active = true;
    Promise.all([
      readJson<{ items: Champion[] }>("/api/v1/champions?limit=200"),
      readJson<{ items: Lane[] }>("/api/v1/lanes"),
    ]).then(([cs, ls]) => {
      if (!active) return;
      setChampions(cs.items);
      setLanes(ls.items);
      setLoadingOptions(false);
    }).catch((error: unknown) => {
      if (!active) return;
      setOptionsError(error instanceof Error ? error.message : "API에 연결할 수 없습니다.");
      setLoadingOptions(false);
    });
    return () => { active = false; };
  }, []);

  const isReady = !!myChampion && !!opponent && myChampion !== opponent && !!lane && !searching;

  function go(next: Page) {
    setPage(next);
    setMenuOpen(false);
  }

  async function runSearch() {
    if (!isReady) return;
    setSearching(true);
    setSearchError("");
    setResult(null);
    setHasSearched(true);
    try {
      const list = await readJson<{ items: Matchup[] }>(
        `/api/v1/matchups?lane=${encodeURIComponent(lane)}&champion=${encodeURIComponent(myChampion)}&limit=200`
      );
      const pair = list.items.find((m) => m.opponent === opponent);
      if (!pair) {
        setSearchError("선택한 라인에 이 챔피언 조합이 등록되어 있지 않습니다.");
        return;
      }
      const details = await readJson<MatchupDetail>(`/api/v1/matchups/${encodeURIComponent(pair.id)}`);
      setResult(details);
      setRecent((prev) => [{ lane, mine: myChampion, versus: opponent }, ...prev.filter((x) => x.lane !== lane || x.mine !== myChampion || x.versus !== opponent)].slice(0, 5));
    } catch (error: unknown) {
      setSearchError(error instanceof Error ? error.message : "조회 중 오류가 발생했습니다.");
    } finally {
      setSearching(false);
    }
  }

  const form = <section className="box search-box" aria-labelledby="search-title">
    <h2 id="search-title">챔피언 상성 조회</h2>
    <div className="search-grid">
      <ChampionSearch label="내 챔피언" value={myChampion} items={champions} disabled={loadingOptions} onChange={(name) => { setMyChampion(name); setResult(null); setHasSearched(false); }} />
      <ChampionSearch label="상대 챔피언" value={opponent} items={champions} disabled={loadingOptions} onChange={(name) => { setOpponent(name); setResult(null); setHasSearched(false); }} />
      <label className="field"><span>라인</span><select value={lane} onChange={(e) => { setLane(e.target.value); setResult(null); setHasSearched(false); }} aria-label="라인 선택">
        {LANES.map((item) => <option key={item} value={item}>{item}{lanes.length ? ` (${lanes.find((x) => x.lane === item)?.champion_count ?? 0})` : ""}</option>)}
      </select></label>
      <button className="action-button" disabled={!isReady} onClick={runSearch}>{searching ? "조회 중…" : "조회"}</button>
    </div>
    {optionsError && <p className="error-message" role="alert">챔피언을 불러오지 못했어. {optionsError} 백엔드 서버가 실행 중인지 확인해 줘.</p>}
    {myChampion && opponent && myChampion === opponent && <p className="error-message">같은 챔피언끼리는 비교할 수 없어.</p>}
  </section>;

  return <div className="shell">
    <header className="topbar">
      <span className="brand">PICKOU</span>
      <button type="button" className="menu-toggle" aria-label="메뉴 열기" aria-expanded={menuOpen} onClick={() => setMenuOpen((v) => !v)}>{menuOpen ? "닫기" : "☰ 메뉴"}</button>
      <nav className="tablet-nav" aria-label="태블릿 메뉴">{MENUS.slice(0, 4).map((item) => <button key={item} type="button" onClick={() => go(item)} aria-current={page === item ? "page" : undefined}>{item}</button>)}</nav>
    </header>
    <div className="layout">
      <aside className="sidebar"><Nav active={page} onSelect={go}/></aside>
      {menuOpen && <div className="mobile-nav"><Nav active={page} onSelect={go}/></div>}
      <main className="main">
        {page === "상성 조회" || page === "홈" ? <>
          <div className="page-heading"><h1>{page === "홈" ? "PICKOU" : "상성 조회"}</h1><p>챔피언과 라인을 선택해 등록된 상성을 확인하세요.</p></div>
          {form}
          <div className="results-grid">
            <section className="box result-panel" aria-labelledby="result-title">
              <h2 id="result-title">상성 결과</h2>
              {searchError ? <p className="error-message" role="alert">{searchError}</p> :
                searching ? <p className="muted">실제 데이터를 조회하고 있어요.</p> :
                result ? <div className="result-content">
                  <p className="matchup-label">{result.champion} <span>VS</span> {result.opponent} <small>· {result.lane}</small></p>
                  <p className="result-status">{result.status === "verified" && result.rating != null ? result.rating : "검증 대기"}</p>
                  <p className="muted">{result.status === "verified" ? "검토·승인된 판정입니다." : "아직 승인된 상성 근거가 없습니다. 승률이나 5:5 판정을 임의로 표시하지 않습니다."}</p>
                  <p className="muted">확인 패치: {result.patch ?? "미확정"}</p>
                </div> : <p className="muted">{hasSearched ? "결과가 없습니다." : "조회할 챔피언을 선택해 주세요."}</p>}
            </section>
            <section className="box details-panel" aria-labelledby="detail-title">
              <h2 id="detail-title">세부 정보</h2>
              {result ? <div className="details-rows">
                <div><strong>근거</strong><span>{result.decision?.status === "manual_approved" ? "수동 검증 완료" : "미등록"}</span></div>
                <div><strong>경기 표본</strong><span>{result.statistics?.sample_size ?? "데이터 없음"}</span></div>
                <div><strong>검증 이력</strong><span>{result.validation_history?.length ?? 0}건</span></div>
                <div><strong>주요 아이템</strong><span>분석 준비 중</span></div>
                <div><strong>주의사항</strong><span>통계·근거가 확인되면 표시</span></div>
              </div> : <div className="details-rows"><div><strong>근거</strong><span>—</span></div><div><strong>주요 아이템</strong><span>—</span></div><div><strong>주의사항</strong><span>—</span></div></div>}
            </section>
          </div>
          <section className="box recent-panel" aria-labelledby="recent-title">
            <h2 id="recent-title">최근 조회</h2>
            {recent.length ? <div className="recent-list">{recent.map((entry) => <button key={entry.lane + entry.mine + entry.versus} type="button" onClick={() => { setLane(entry.lane);setMyChampion(entry.mine);setOpponent(entry.versus);setResult(null);setHasSearched(false); }}>{entry.mine} vs {entry.versus} <span>{entry.lane}</span></button>)}</div> : <p className="muted">이번 세션에서 조회한 기록이 없습니다.</p>}
          </section>
        </> : <section className="box placeholder"><h1>{page}</h1><p>이 메뉴는 다음 개발 단계에서 구현할 예정입니다.</p><p className="muted">실제 데이터가 준비되지 않은 분석 결과를 미리 생성하지 않습니다.</p><button className="text-button" onClick={() => go("상성 조회")}>상성 조회로 돌아가기</button></section>}
      </main>
    </div>
  </div>;
}

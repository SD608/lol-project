"use client";

import { useEffect, useState } from "react";
import ChampionSearch from "./ChampionSearch";

type Champion = { name: string; riot_id?: string | null; aliases?: string[]; initials?: string | null };
type Lane = { lane: string; champion_count: number };
type Pick = { champion: string; rating: string };
type Counters = {
  lane: string; opponent: string; patch: string | null; region: string; tier: string;
  hard_counters: Pick[]; counters: Pick[]; even: Pick[];
  unknown_count: number; total: number; note: string;
};
type Page = "홈" | "상성 조회" | "조합 분석" | "패치 노트" | "통계" | "즐겨찾기" | "설정";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const MENUS: Page[] = ["홈", "상성 조회", "조합 분석", "패치 노트", "통계", "즐겨찾기", "설정"];
const LANES = ["탑", "정글", "미드", "바텀", "서폿"];

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(API_BASE + path, { cache: "no-store" });
  if (!response.ok) {
    if (response.status === 503) throw new Error("데이터베이스 연결을 확인해 주세요.");
    if (response.status === 404) throw new Error("해당 라인에 상대 챔피언이 등록되어 있지 않습니다.");
    throw new Error(`API 응답 오류 (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function Nav({ active, onSelect }: { active: Page; onSelect: (page: Page) => void }) {
  return <nav className="nav-list" aria-label="기본 메뉴">
    {MENUS.map((item) => <button key={item} type="button" className={active === item ? "nav-link is-active" : "nav-link"} onClick={() => onSelect(item)} aria-current={active === item ? "page" : undefined}>{item}</button>)}
  </nav>;
}

function CounterGroup({ title, picks, empty }: { title: string; picks: Pick[]; empty: string }) {
  return <section className="box counter-group">
    <div className="group-heading"><h2>{title}</h2><span>{picks.length}명</span></div>
    {picks.length ? <div className="pick-list">{picks.map((pick) => <div className="pick-card" key={pick.champion}>
      <strong>{pick.champion}</strong><span>{pick.rating}</span>
    </div>)}</div> : <p className="muted">{empty}</p>}
  </section>;
}

export default function Home() {
  const [page, setPage] = useState<Page>("상성 조회");
  const [menuOpen, setMenuOpen] = useState(false);
  const [champions, setChampions] = useState<Champion[]>([]);
  const [lanes, setLanes] = useState<Lane[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [optionsError, setOptionsError] = useState("");
  const [opponent, setOpponent] = useState("");
  const [lane, setLane] = useState("탑");
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [result, setResult] = useState<Counters | null>(null);
  const [recent, setRecent] = useState<Array<{ lane: string; opponent: string }>>([]);

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

  const canSearch = !!opponent && !!lane && !searching && !loadingOptions;
  function go(next: Page) { setPage(next); setMenuOpen(false); }

  async function runSearch() {
    if (!canSearch) return;
    setSearching(true);
    setSearchError("");
    setResult(null);
    try {
      const data = await readJson<Counters>(
        `/api/v1/counters?lane=${encodeURIComponent(lane)}&opponent=${encodeURIComponent(opponent)}`
      );
      setResult(data);
      setRecent((prev) => [{ lane, opponent }, ...prev.filter((x) => x.lane !== lane || x.opponent !== opponent)].slice(0, 5));
    } catch (error: unknown) {
      setSearchError(error instanceof Error ? error.message : "조회 중 오류가 발생했습니다.");
    } finally {
      setSearching(false);
    }
  }

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
          <div className="page-heading">
            <h1>상대 픽 카운터 찾기</h1>
            <p>상대가 선택한 챔피언과 라인을 입력하면 유리한 픽을 찾아줘요.</p>
          </div>
          <section className="box search-box" aria-labelledby="search-title">
            <h2 id="search-title">상대 챔피언 선택</h2>
            <div className="search-grid enemy-search-grid">
              <ChampionSearch label="상대 챔피언" value={opponent} items={champions} disabled={loadingOptions}
                onChange={(name) => { setOpponent(name); setResult(null); setSearchError(""); }} />
              <label className="field"><span>상대 라인</span><select value={lane} onChange={(e) => { setLane(e.target.value); setResult(null); setSearchError(""); }} aria-label="상대 라인 선택">
                {LANES.map((item) => <option key={item} value={item}>{item}{lanes.length ? ` (${lanes.find((x) => x.lane === item)?.champion_count ?? 0})` : ""}</option>)}
              </select></label>
              <button className="action-button" disabled={!canSearch} onClick={runSearch}>{searching ? "분석 중…" : "카운터 찾기"}</button>
            </div>
            {optionsError && <p className="error-message" role="alert">챔피언 목록을 불러오지 못했습니다. {optionsError}</p>}
          </section>
          {searchError && <section className="box" role="alert"><p className="error-message">{searchError}</p><p className="muted">백엔드가 업데이트된 상태인지 확인해 주세요.</p></section>}
          {searching && <section className="box" aria-live="polite">카운터 근거를 조회하고 있습니다.</section>}
          {!searchError && !searching && !result && <section className="box empty-results">
            <h2>카운터 추천 결과</h2>
            <p className="muted">상대 챔피언을 선택하고 ‘카운터 찾기’를 눌러주세요.</p>
          </section>}
          {result && !searching && <>
            <section className="box summary-box">
              <h2>{result.opponent} 상대 추천 픽 <span className="summary-lane">{result.lane}</span></h2>
              <p className="muted">패치: {result.patch ?? "공식 적용 확인 대기"} · 검증된 추천: {result.hard_counters.length + result.counters.length + result.even.length}명</p>
              {result.unknown_count > 0 && <p className="unknown-note">등록된 후보 {result.total}명 중 {result.unknown_count}명은 승인된 상성 판정이 없어 분류하지 않았습니다.</p>}
            </section>
            <div className="counter-results">
              <CounterGroup title="하드카운터" picks={result.hard_counters} empty="검증된 하드카운터가 아직 없습니다." />
              <CounterGroup title="카운터" picks={result.counters} empty="검증된 카운터가 아직 없습니다." />
              <CounterGroup title="반반" picks={result.even} empty="검증된 반반 픽이 아직 없습니다." />
            </div>
            <p className="muted classification-note">9:1·8:2는 하드카운터, 7:3·6:4는 카운터, 5:5는 반반으로 분류합니다. 최신 확인 패치에서 수동 승인된 등급만 사용합니다. 미검증 픽은 추천하지 않습니다.</p>
          </>}
          <section className="box recent-panel">
            <h2>최근 조회</h2>
            {recent.length ? <div className="recent-list">{recent.map((entry) => <button key={entry.lane + entry.opponent} type="button" onClick={() => { setLane(entry.lane); setOpponent(entry.opponent); setResult(null); setSearchError(""); }}>
              상대: {entry.opponent}<span>{entry.lane}</span>
            </button>)}</div> : <p className="muted">이번 세션에서 조회한 기록이 없습니다.</p>}
          </section>
        </> : <section className="box placeholder">
          <h1>{page}</h1><p>이 메뉴는 다음 개발 단계에서 구현할 예정입니다.</p>
          <p className="muted">근거가 없는 분석 결과는 생성하지 않습니다.</p>
          <button className="text-button" onClick={() => go("상성 조회")}>카운터 찾기로 돌아가기</button>
        </section>}
      </main>
    </div>
  </div>;
}

"use client";

import { useEffect, useRef, useState } from "react";
import ChampionSearch from "./ChampionSearch";
import PatchNotes from "./PatchNotes";
import ExternalStatsLink from "./ExternalStatsLink";
import SheetReference from "./SheetReference";
import AllMatchupResearch from "./AllMatchupResearch";
import ProvisionalMatchups from "./ProvisionalMatchups";

type Champion = { name: string; riot_id?: string | null; aliases?: string[]; initials?: string | null; lanes?: string[] };
type Lane = { lane: string; champion_count: number };
type Pick = { champion: string; rating: string };
type Counters = {
  lane: string; opponent: string; patch: string | null; region: string; tier: string;
  lane_registered: boolean; coverage_status: "registered" | "off_meta_unregistered";
  data_status: "no_verified_matchups" | "partially_verified";
  hard_counters: Pick[]; counters: Pick[]; even: Pick[];
  unknown_count: number; total: number; note: string;
};
type Favorite = { lane: string; opponent: string };
const FAVORITES_KEY = "pickou:favorites:v1";
type Page = "홈" | "상성 조회" | "조합 분석" | "패치 노트" | "통계" | "즐겨찾기" | "설정";

const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const MENUS: Page[] = ["홈", "상성 조회", "조합 분석", "패치 노트", "통계", "즐겨찾기", "설정"];
const LANES = ["탑", "정글", "미드", "바텀", "서폿"];

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(API_BASE + path, { cache: "no-store" });
  if (!response.ok) {
    if (response.status === 503) throw new Error("데이터베이스 연결을 확인해 주세요.");
    if (response.status === 404) throw new Error("등록되지 않은 챔피언입니다.");
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
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [storageReady, setStorageReady] = useState(false);
  const requestSequence = useRef(0);

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

  useEffect(() => {
    try {
      const stored = JSON.parse(window.localStorage.getItem(FAVORITES_KEY) || "[]");
      if (Array.isArray(stored)) {
        setFavorites(stored.filter((item): item is Favorite =>
          !!item && typeof item.opponent === "string" && typeof item.lane === "string" &&
          LANES.includes(item.lane) && item.opponent.length <= 100
        ).slice(0, 50));
      }
    } catch {
      // Browser storage can be unavailable; the current session still works.
    }
    setStorageReady(true);
  }, []);

  function saveFavorites(next: Favorite[]) {
    setFavorites(next);
    try {
      window.localStorage.setItem(FAVORITES_KEY, JSON.stringify(next));
    } catch {
      // Keep in-memory favorites when storage is restricted.
    }
  }

  function toggleFavorite(target: Favorite) {
    const exists = favorites.some((x) => x.opponent === target.opponent && x.lane === target.lane);
    saveFavorites(exists
      ? favorites.filter((x) => x.opponent !== target.opponent || x.lane !== target.lane)
      : [target, ...favorites].slice(0, 50));
  }

  function openFavorite(target: Favorite) {
    setPage("상성 조회");
    setMenuOpen(false);
    setOpponent(target.opponent);
    setLane(target.lane);
    void runSearch(target.opponent, target.lane);
  }

  const canSearch = !!opponent && !!lane && !searching && !loadingOptions;
  function go(next: Page) { setPage(next); setMenuOpen(false); }

  async function runSearch(target = opponent, selectedLane = lane) {
    if (!target || !selectedLane) return;
    const requestId = ++requestSequence.current;
    setSearching(true);
    setSearchError("");
    setResult(null);
    try {
      const data = await readJson<Counters>(
        `/api/v1/counters?lane=${encodeURIComponent(selectedLane)}&opponent=${encodeURIComponent(target)}`
      );
      if (requestId !== requestSequence.current) return;
      setResult(data);
      setRecent((prev) => [{ lane: selectedLane, opponent: target }, ...prev.filter((x) => x.lane !== selectedLane || x.opponent !== target)].slice(0, 5));
    } catch (error: unknown) {
      if (requestId !== requestSequence.current) return;
      setSearchError(error instanceof Error ? error.message : "조회 중 오류가 발생했습니다.");
    } finally {
      if (requestId === requestSequence.current) setSearching(false);
    }
  }

  function changeOpponent(name: string) {
    setOpponent(name);
    setResult(null);
    setSearchError("");
    if (name) void runSearch(name, lane);
    else { requestSequence.current += 1; setSearching(false); }
  }

  function changeLane(next: string) {
    setLane(next);
    setResult(null);
    setSearchError("");
    if (opponent) void runSearch(opponent, next);
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
            <p>상대 챔피언을 선택하면 해당 라인의 카운터 픽을 바로 조회해요.</p>
          </div>
          <section className="box search-box" aria-labelledby="search-title">
            <h2 id="search-title">상대 챔피언 선택</h2>
            <div className="search-grid enemy-search-grid">
              <ChampionSearch label="상대 챔피언" value={opponent} items={champions} selectedLane={lane} disabled={loadingOptions}
                onChange={changeOpponent} />
              <label className="field"><span>상대 라인</span><select value={lane} onChange={(e) => changeLane(e.target.value)} aria-label="상대 라인 선택">
                {LANES.map((item) => <option key={item} value={item}>{item}{lanes.length ? ` (${lanes.find((x) => x.lane === item)?.champion_count ?? 0})` : ""}</option>)}
              </select></label>
              <button className="action-button" disabled={!canSearch} onClick={() => void runSearch()}>{searching ? "분석 중…" : "다시 조회"}</button>
            </div>
            {optionsError && <p className="error-message" role="alert">챔피언 목록을 불러오지 못했습니다. {optionsError}</p>}
          </section>
          {opponent && <div className="favorite-actions">
            <button type="button" className="text-button favorite-button" onClick={() => toggleFavorite({ opponent, lane })}
              aria-pressed={favorites.some((x) => x.opponent === opponent && x.lane === lane)}>
              {favorites.some((x) => x.opponent === opponent && x.lane === lane) ? "★ 즐겨찾기 해제" : "☆ 이 픽 즐겨찾기"}
            </button>
          </div>}
          {searchError && <section className="box" role="alert"><p className="error-message">{searchError}</p><p className="muted">백엔드가 업데이트된 상태인지 확인해 주세요.</p></section>}
          {searching && <section className="box" aria-live="polite">카운터 근거를 조회하고 있습니다.</section>}
          {!searchError && !searching && !result && <section className="box empty-results">
            <h2>카운터 추천 결과</h2>
            <p className="muted">상대 챔피언을 선택하면 자동으로 조회합니다.</p>
          </section>}
          {result && !searching && <>
            <section className="box summary-box">
              <h2>{result.opponent} 상대 추천 픽 <span className="summary-lane">{result.lane}</span></h2>
              {result.coverage_status === "off_meta_unregistered" && <div className="offmeta-notice" role="status">
                <strong>비주류 라인 픽 · 별도 데이터 부족</strong>
                <p>이 챔피언은 {result.lane}의 기본 등록 명단에 없지만 검색은 지원해요. 다른 라인의 상성을 가져오지 않고, 검증된 {result.lane} 경기 데이터가 쌓일 때까지 추천을 보류합니다.</p>
              </div>}
              <p className="muted">패치: {result.patch ?? "공식 적용 확인 대기"} · 검증된 추천: {result.hard_counters.length + result.counters.length + result.even.length}명</p>
              {result.data_status === "no_verified_matchups" && <p className="muted">해당 라인의 승인된 상성 판정이 아직 없습니다. 데이터가 없다는 뜻이지, 카운터가 없다는 뜻은 아닙니다.</p>}
              {result.unknown_count > 0 && <p className="unknown-note">해당 라인의 선택 가능 후보 {result.total}명 중 {result.unknown_count}명은 검증된 상대 상성 정보가 없어 분류하지 않았습니다.</p>}
            </section>
            <ProvisionalMatchups enemy={result.opponent} lane={result.lane} />
            <AllMatchupResearch enemy={result.opponent} lane={result.lane} champions={champions} />
            <SheetReference enemy={result.opponent} lane={result.lane} />
            <ExternalStatsLink champion={champions.find((item) => item.name === opponent)} lane={result.lane} />
            <div className="counter-results">
              <CounterGroup title="하드카운터" picks={result.hard_counters} empty="검증된 하드카운터가 아직 없습니다." />
              <CounterGroup title="카운터" picks={result.counters} empty="검증된 카운터가 아직 없습니다." />
              <CounterGroup title="반반" picks={result.even} empty="검증된 반반 픽이 아직 없습니다." />
            </div>
            <p className="muted classification-note">9:1·8:2는 하드카운터, 7:3·6:4는 카운터, 5:5는 반반으로 분류합니다. 최신 확인 패치에서 수동 승인된 등급만 사용합니다. 미검증 픽은 추천하지 않습니다.</p>
          </>}
          <section className="box recent-panel">
            <h2>최근 조회</h2>
            {recent.length ? <div className="recent-list">{recent.map((entry) => <button key={entry.lane + entry.opponent} type="button" onClick={() => { setLane(entry.lane); setOpponent(entry.opponent); void runSearch(entry.opponent, entry.lane); }}>
              상대: {entry.opponent}<span>{entry.lane}</span>
            </button>)}</div> : <p className="muted">이번 세션에서 조회한 기록이 없습니다.</p>}
          </section>
        </> : page === "패치 노트" ? <PatchNotes /> : page === "즐겨찾기" ? <section className="box favorites-panel">
          <h1>즐겨찾기</h1>
          <p className="muted">자주 상대하는 챔피언과 라인을 저장해서 바로 다시 조회할 수 있어요.</p>
          {!storageReady ? <p className="muted">저장된 목록을 불러오는 중…</p> :
            favorites.length ? <div className="favorite-list">
              {favorites.map((entry) => <div key={entry.lane + ":" + entry.opponent} className="favorite-row">
                <button type="button" className="favorite-open" onClick={() => openFavorite(entry)}>
                  <strong>{entry.opponent}</strong><span>{entry.lane} · 카운터 찾기</span>
                </button>
                <button type="button" className="text-button favorite-remove" aria-label={entry.opponent + " " + entry.lane + " 즐겨찾기 삭제"}
                  onClick={() => toggleFavorite(entry)}>삭제</button>
              </div>)}
            </div> : <p className="muted">저장된 픽이 없어요. 상성 조회에서 상대 챔피언과 라인을 선택한 뒤 즐겨찾기에 추가해 보세요.</p>}
          <p className="muted favorite-storage-note">즐겨찾기는 현재 브라우저에만 저장돼요. 다른 기기와 동기화되지 않으며, 브라우저 데이터를 삭제하면 사라질 수 있습니다.</p>
        </section> : <section className="box placeholder">
          <h1>{page}</h1><p>이 메뉴는 다음 개발 단계에서 구현할 예정입니다.</p>
          <p className="muted">근거가 없는 분석 결과는 생성하지 않습니다.</p>
          <button className="text-button" onClick={() => go("상성 조회")}>카운터 찾기로 돌아가기</button>
        </section>}
      </main>
    </div>
  </div>;
}

"use client";

import { useEffect, useMemo, useState } from "react";

type Champion = { name: string; riot_id?: string | null };
type Matchup = { opponent: string; enemyWinRate: number; games: number };
type Saved = { patch: string; tier: string; region: string; observedAt: string; sourceUrl: string; matchups: Matchup[] };
const KEY = "pickou:external-matchups:v1";
const POSITIONS: Record<string, string> = { "탑": "top", "정글": "jungle", "미드": "mid", "바텀": "adc", "서폿": "support" };

export function opggCounterUrl(champion: Champion | undefined, lane: string): string {
  const id = champion?.riot_id;
  const position = POSITIONS[lane];
  if (!id || !position || !/^[a-zA-Z0-9]+$/.test(id)) return "https://op.gg/ko/lol/champions";
  return `https://op.gg/ko/lol/champions/${id.toLowerCase()}/counters/${position}`;
}

function storageKey(name: string, lane: string) { return name + "|" + lane; }
function isSaved(input: unknown): input is Saved {
  if (!input || typeof input !== "object") return false;
  const x = input as Partial<Saved>;
  return typeof x.patch === "string" && typeof x.tier === "string" && typeof x.region === "string" &&
    typeof x.observedAt === "string" && typeof x.sourceUrl === "string" &&
    Array.isArray(x.matchups) && x.matchups.length <= 200 && x.matchups.every((r) =>
      !!r && typeof r.opponent === "string" && r.opponent.length <= 100 &&
      Number.isFinite(r.enemyWinRate) && r.enemyWinRate >= 0 && r.enemyWinRate <= 100 &&
      Number.isSafeInteger(r.games) && r.games > 0);
}

export function parseMatchups(text: string): Matchup[] {
  const lines = text.trim().split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (!lines.length || lines.length > 200) throw new Error("1~200개의 상성 행을 입력해 주세요.");
  const parsed: Matchup[] = [];
  const known = new Set<string>();
  for (const [index, line] of lines.entries()) {
    const fields = line.split(/[\t,]/).map((v) => v.trim());
    if (fields.length !== 3) throw new Error(`${index + 1}행: 상대 챔피언, 상대 챔피언 승률(%), 경기 수를 입력해 주세요.`);
    const [opponent, rawRate, rawGames] = fields;
    const rate = Number(rawRate.replace("%", ""));
    const games = Number(rawGames.replace(/,/g, ""));
    if (!opponent || opponent.length > 100 || !Number.isFinite(rate) || rate < 0 || rate > 100 ||
        !Number.isSafeInteger(games) || games <= 0 || !rawRate || !rawGames) {
      throw new Error(`${index + 1}행: 챔피언 이름, 0~100% 승률, 1 이상의 정수 표본을 확인해 주세요.`);
    }
    if (known.has(opponent.toLowerCase())) throw new Error(`${index + 1}행: 같은 상대 챔피언이 중복됐어요.`);
    known.add(opponent.toLowerCase());
    parsed.push({ opponent, enemyWinRate: rate, games });
  }
  return parsed.sort((a, b) => a.enemyWinRate - b.enemyWinRate || b.games - a.games);
}

export default function ExternalStatsLink({ champion, lane }: { champion: Champion | undefined; lane: string }) {
  const [ready, setReady] = useState(false);
  const [saved, setSaved] = useState<Saved | null>(null);
  const [editing, setEditing] = useState(false);
  const [raw, setRaw] = useState("");
  const [patch, setPatch] = useState("");
  const [tier, setTier] = useState("");
  const [region, setRegion] = useState("KR");
  const [error, setError] = useState("");
  const name = champion?.name || "";
  const url = opggCounterUrl(champion, lane);

  useEffect(() => {
    setReady(false); setSaved(null); setEditing(false); setError(""); setRaw("");
    try {
      const all = JSON.parse(window.localStorage.getItem(KEY) || "{}") as Record<string, unknown>;
      const item = all[storageKey(name, lane)];
      if (isSaved(item)) setSaved(item);
    } catch { /* browser-local storage is optional */ }
    setReady(true);
  }, [name, lane]);

  const displayed = useMemo(() => saved?.matchups || [], [saved]);
  function save() {
    setError("");
    try {
      if (!name) throw new Error("챔피언을 먼저 선택해 주세요.");
      if (!patch.trim() || !tier.trim() || !region.trim()) throw new Error("자료의 패치·티어·지역을 적어 주세요.");
      const data: Saved = {
        patch: patch.trim().slice(0, 30), tier: tier.trim().slice(0, 50),
        region: region.trim().slice(0, 30), observedAt: new Date().toISOString(),
        sourceUrl: url, matchups: parseMatchups(raw),
      };
      const all = JSON.parse(window.localStorage.getItem(KEY) || "{}") as Record<string, unknown>;
      const next = all && typeof all === "object" && !Array.isArray(all) ? all : {};
      next[storageKey(name, lane)] = data;
      window.localStorage.setItem(KEY, JSON.stringify(next));
      setSaved(data); setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "입력 데이터 저장 중 오류가 발생했어요.");
    }
  }
  function clear() {
    try {
      const all = JSON.parse(window.localStorage.getItem(KEY) || "{}") as Record<string, unknown>;
      if (all && typeof all === "object" && !Array.isArray(all)) {
        delete all[storageKey(name, lane)];
        window.localStorage.setItem(KEY, JSON.stringify(all));
      }
    } catch { /* session clear remains available */ }
    setSaved(null); setEditing(false); setRaw("");
  }

  return <section className="box external-reference-panel">
    <div className="external-reference-head">
      <div><h2>외부 통계 기반 상대 상성</h2>
        <p className="muted">PICKOU 화면에서 직접 확인하는 개인용 통계 기록 · 공식 승인 상성 등급과 별도</p>
      </div>
      <a className="external-reference-link" href={url} target="_blank" rel="noopener noreferrer">OP.GG 원본 확인 ↗</a>
    </div>
    {ready && saved && <>
      <p className="muted reference-note">출처: OP.GG (수동 입력) · {saved.region} · {saved.tier} · 패치 {saved.patch} · 입력일 {new Date(saved.observedAt).toLocaleDateString("ko-KR")}</p>
      <div className="external-stat-list">
        {displayed.map((item) => <div className="external-stat-row" key={item.opponent}>
          <strong>{item.opponent}</strong>
          <span>상대 챔피언 승률 <b>{item.enemyWinRate.toFixed(2)}%</b></span>
          <span>표본 {item.games.toLocaleString("ko-KR")}판</span>
        </div>)}
      </div>
      <p className="muted reference-note">낮은 상대 챔피언 승률순으로 표시합니다. 승률은 카운터 등급이나 라인전 우위 판정을 뜻하지 않습니다. 패치가 바뀌면 다시 확인해 주세요.</p>
    </>}
    {!ready && <p className="muted">저장된 통계를 불러오는 중…</p>}
    {ready && !saved && <p className="muted">저장된 통계가 없습니다. OP.GG에서 확인한 상대별 승률과 표본 수를 아래에서 입력하면 이 화면에 표시됩니다.</p>}
    {ready && <div className="external-stat-actions">
      <button type="button" className="text-button" onClick={() => {setEditing((v) => !v); setError("");}}>
        {editing ? "입력창 닫기" : saved ? "통계 다시 입력" : "통계 입력하기"}
      </button>
      {saved && <button type="button" className="text-button" onClick={clear}>저장된 통계 삭제</button>}
    </div>}
    {editing && <div className="external-stat-editor">
      <p className="muted reference-note">OP.GG에서 조회한 상대 챔피언별 수치를 직접 옮겨 적으세요. 예: 징크스,48.50,120 (상대 챔피언 승률 기준). 숫자는 실제 확인한 값만 입력해 주세요.</p>
      <div className="external-stat-fields">
        <label>패치<input value={patch} maxLength={30} onChange={(e) => setPatch(e.target.value)} placeholder="예: 16.22" /></label>
        <label>티어<input value={tier} maxLength={50} onChange={(e) => setTier(e.target.value)} placeholder="예: 에메랄드+" /></label>
        <label>지역<input value={region} maxLength={30} onChange={(e) => setRegion(e.target.value)} placeholder="예: KR" /></label>
      </div>
      <label className="external-stat-paste-label">상대 챔피언, 상대 챔피언 승률(%), 경기 수
        <textarea rows={6} value={raw} onChange={(e) => setRaw(e.target.value)} placeholder={"징크스,48.50,120\n진,51.20,100"} />
      </label>
      {error && <p className="error-message" role="alert">{error}</p>}
      <button type="button" className="action-button" onClick={save}>브라우저에 통계 저장</button>
    </div>}
    <p className="muted reference-note">이 통계는 브라우저에만 저장되며 서버·Supabase·OP.GG로 전송되지 않습니다. 자동 수집 기능은 포함하지 않습니다.</p>
  </section>;
}

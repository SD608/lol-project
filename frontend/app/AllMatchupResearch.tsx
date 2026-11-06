"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { resolveChampionId } from "./riotChampionResolver";
import top from "../data/sheets-reference-top.json";
import jungle from "../data/sheets-reference-jungle.json";
import mid from "../data/sheets-reference-mid.json";
import bot from "../data/sheets-reference-bot.json";
import support from "../data/sheets-reference-support.json";

type Champion = { name: string; riot_id?: string | null; lanes?: string[] };
type Ref = { champion: string; opponent: string; reference: string; skill: string; timing: string; row: number };
type Detail = { name: string; title: string; stats: { attackrange?: number }; passive?: { name: string; description: string }; spells: Array<{ name: string; description: string }> };
const REFS: Record<string, Ref[]> = { "탑": top.entries, "정글": jungle.entries, "미드": mid.entries, "바텀": bot.entries, "서폿": support.entries };
const TABS: Record<string, number> = { "탑": 700001, "정글": 700002, "미드": 700003, "바텀": 700004, "서폿": 700005 };
const SHEET = "https://docs.google.com/spreadsheets/d/1uitjfV_owbxUrPZRZm-Q0KdarZaiSQFTGyG2IZjEVcU/edit";
const CDN = "https://ddragon.leagueoflegends.com";

function plain(text: string | undefined): string {
  return (text || "").replace(/<[^>]*>/g, " ").replace(/\{\{[^}]+\}\}/g, "[변수]")
    .replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/\s+/g, " ").trim();
}
async function loadDetail(version: string, champion: Champion): Promise<Detail> {
  const id = await resolveChampionId(version, champion);
  const url = `${CDN}/cdn/${encodeURIComponent(version)}/data/ko_KR/champion/${id}.json`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(champion.name + ": 공식 스킬 정보를 불러올 수 없습니다 (" + response.status + ").");
  const body = await response.json() as { data?: Record<string, Detail> };
  const value = body.data?.[id];
  if (!value || !Array.isArray(value.spells)) throw new Error(champion.name + ": 공식 스킬 데이터 형식이 예상과 다릅니다.");
  return value;
}

function AbilityList({ champ, detail }: { champ: Champion; detail: Detail }) {
  const abilities = [{ key: "P", name: detail.passive?.name || "패시브", text: detail.passive?.description || "" },
    ...detail.spells.map((spell, index) => ({ key: ["Q", "W", "E", "R"][index] || "?", name: spell.name, text: spell.description }))];
  return <div className="all-evidence-champion">
    <h4>{champ.name} <small>{detail.title}</small></h4>
    <p className="muted">기본 공격 사거리: {typeof detail.stats?.attackrange === "number" ? detail.stats.attackrange : "확인 불가"} (사거리만으로 유불리를 결정하지 않음)</p>
    {abilities.map((a) => <div className="all-evidence-ability" key={a.key}><strong>{a.key} · {a.name}</strong><p>{plain(a.text) || "설명 데이터 없음"}</p></div>)}
  </div>;
}

export default function AllMatchupResearch({ enemy, lane, champions }: { enemy: string; lane: string; champions: Champion[] }) {
  const [query, setQuery] = useState("");
  const [scope, setScope] = useState<"all" | "registered" | "offmeta">("all");
  const [selected, setSelected] = useState("");
  const [version, setVersion] = useState("");
  const [details, setDetails] = useState<{ enemy: Detail; mine: Detail } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showAll, setShowAll] = useState(false);
  const lookupSequence = useRef(0);

  const enemyRecord = champions.find((item) => item.name === enemy);
  const references = useMemo(() => new Map((REFS[lane] || []).filter((r) => r.opponent === enemy).map((r) => [r.champion, r])), [enemy, lane]);
  const options = useMemo(() => champions.filter((c) => c.name !== enemy)
    .filter((c) => scope === "all" || (scope === "registered" ? c.lanes?.includes(lane) : !c.lanes?.includes(lane)))
    .filter((c) => !query || c.name.toLocaleLowerCase().includes(query.toLocaleLowerCase()) || (c.riot_id || "").toLocaleLowerCase().includes(query.toLocaleLowerCase()))
    .sort((a, b) => Number(Boolean(references.get(b.name))) - Number(Boolean(references.get(a.name))) || a.name.localeCompare(b.name, "ko")), [champions, enemy, scope, lane, query, references]);
  const chosen = champions.find((c) => c.name === selected);
  const reference = chosen && references.get(chosen.name);
  useEffect(() => { lookupSequence.current += 1; setDetails(null); setSelected(""); setError(""); setShowAll(false); setLoading(false); }, [enemy, lane]);

  async function inspect(champ: Champion) {
    const lookupId = ++lookupSequence.current;
    setSelected(champ.name); setDetails(null); setLoading(true); setError("");
    try {
      if (!enemyRecord) throw new Error("상대 챔피언을 찾을 수 없습니다.");
      const versionsRes = await fetch(CDN + "/api/versions.json", { cache: "no-store" });
      if (!versionsRes.ok) throw new Error("공식 Data Dragon 버전 확인에 실패했습니다.");
      const versions = await versionsRes.json() as string[];
      const latest = versions[0];
      if (!latest || !/^\d+\.\d+\.\d+$/.test(latest)) throw new Error("공식 데이터 버전이 올바르지 않습니다.");
      const [mine, opponent] = await Promise.all([loadDetail(latest, champ), loadDetail(latest, enemyRecord)]);
      if (lookupId === lookupSequence.current) { setVersion(latest); setDetails({ mine, enemy: opponent }); }
    } catch (e) { if (lookupId === lookupSequence.current) setError(e instanceof Error ? e.message : "공식 데이터 조회 실패"); }
    finally { if (lookupId === lookupSequence.current) setLoading(false); }
  }

  return <section className="box all-evidence-panel">
    <h2>전체 챔피언 상성 근거 조사</h2>
    <p className="muted">상대 <strong>{enemy} · {lane}</strong> 기준. 등록 라인과 무관하게 나머지 {Math.max(0, champions.length - 1)}명 모두 확인할 수 있습니다. 비주류 픽도 제외하지 않습니다.</p>
    <p className="sheet-reference-warning"><strong>분석 범위와 판정의 차이:</strong> 모든 조합을 열람할 수 있지만, 공식 스킬 설명만으로 승패나 9:1·7:3 등급을 확정할 수 없습니다. 시트에 있는 기존 의견은 미검증 참고, 나머지는 판정 보류입니다.</p>
    <div className="all-evidence-filters">
      <input type="search" value={query} onChange={(e) => { setQuery(e.target.value); setShowAll(false); }} placeholder="내가 사용할 챔피언 검색" aria-label="내 챔피언 검색" />
      <select value={scope} onChange={(e) => { setScope(e.target.value as typeof scope); setShowAll(false); }} aria-label="라인 등록 필터">
        <option value="all">전체 챔피언</option>
        <option value="registered">해당 라인 등록</option>
        <option value="offmeta">비주류 · 미등록</option>
      </select>
      <span>{options.length}명</span>
    </div>
    <div className="all-evidence-list">
      {(showAll ? options : options.slice(0, 30)).map((champ) => {
        const ref = references.get(champ.name);
        return <button key={champ.name} type="button" className={selected === champ.name ? "all-evidence-option selected" : "all-evidence-option"}
          onClick={() => void inspect(champ)}>
          <strong>{champ.name}</strong>
          <span>{champ.lanes?.includes(lane) ? "등록 라인" : "비주류 가능"}</span>
          <span>{ref?.reference || "직접 상성 판정 보류"}</span>
          <span>공식 스킬 확인 ›</span>
        </button>;
      })}
    </div>
    {!showAll && options.length > 30 && <button type="button" className="text-button" onClick={() => setShowAll(true)}>나머지 {options.length - 30}명도 보기</button>}
    {selected && <div className="all-evidence-inspection" aria-live="polite">
      <h3>{selected} vs {enemy} · {lane}</h3>
      <p className="muted">{chosen?.lanes?.includes(lane) ? "기본 등록 라인" : "비주류 픽"} · {reference?.reference || "기존 상성 판정 자료 없음"}</p>
      {reference?.skill && <p><strong>기존 시트 스킬 근거:</strong> {reference.skill}</p>}
      {reference?.timing && <p><strong>기존 시트 교전 시점:</strong> {reference.timing}</p>}
      {reference && <a href={`${SHEET}#gid=${TABS[lane]}&range=A${reference.row}:Q${reference.row}`} target="_blank" rel="noopener noreferrer">기존 시트 원본 근거 ↗</a>}
      {loading && <p className="muted">Riot 공식 스킬 데이터를 확인 중…</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {details && chosen && <><p className="muted">출처: Riot Data Dragon {version} · 스킬 설명은 기본 동작을 확인하기 위한 자료이며 실제 맞상대 승률이나 승패 근거는 아닙니다.</p>
        <div className="all-evidence-columns"><AbilityList champ={chosen} detail={details.mine}/><AbilityList champ={enemyRecord!} detail={details.enemy}/></div>
        <p className="sheet-reference-warning">판정: {reference ? "기존 시트 참고 의견 · 최신 패치 검증 대기" : "상성 판단 보류 · 추가 메커니즘 검증과 실전 근거 필요"}. 특히 사거리, CC, 돌진, 보호막 무력화 여부는 스킬 설명만으로 상호작용 전체를 확인할 수 없습니다.</p>
      </>}
    </div>}
  </section>;
}

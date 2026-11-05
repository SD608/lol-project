"use client";

import { useMemo, useState } from "react";
import top from "../data/sheets-reference-top.json";
import jungle from "../data/sheets-reference-jungle.json";
import mid from "../data/sheets-reference-mid.json";
import bot from "../data/sheets-reference-bot.json";
import support from "../data/sheets-reference-support.json";

type Reference = {
  lane: string; champion: string; opponent: string; reference: string;
  grade: string; ratio: string; skill: string; timing: string;
  evidenceStatus: string; patchStatus: string; row: number;
};
const SOURCE_URL = "https://docs.google.com/spreadsheets/d/1uitjfV_owbxUrPZRZm-Q0KdarZaiSQFTGyG2IZjEVcU/edit";
const DATA: Record<string, { entries: Reference[]; rowCount: number; gradedCount: number }> = {
  "탑": top, "정글": jungle, "미드": mid, "바텀": bot, "서폿": support,
};
const TAB_IDS: Record<string, number> = {
  "탑": 700001, "정글": 700002, "미드": 700003, "바텀": 700004, "서폿": 700005,
};

function ReferenceGroup({ heading, items, lane }: { heading: string; items: Reference[]; lane: string }) {
  if (!items.length) return null;
  return <div className="sheet-reference-group">
    <h3>{heading} <small>{items.length}건</small></h3>
    <div className="sheet-reference-list">
      {items.map((item) => <details className="sheet-reference-item" key={item.champion + ":" + item.opponent}>
        <summary><strong>{item.champion}</strong><span>{item.reference}</span></summary>
        <div className="sheet-reference-details">
          {item.skill && <p><strong>스킬 상성:</strong> {item.skill}</p>}
          {item.timing && <p><strong>유불리 시점:</strong> {item.timing}</p>}
          <p className="muted">근거: {item.evidenceStatus || "추가 검증 대기"} · 패치 검증: {item.patchStatus || "미확인"}</p>
          <a href={`${SOURCE_URL}#gid=${TAB_IDS[lane]}&range=A${item.row}:Q${item.row}`} target="_blank" rel="noopener noreferrer">시트 원본 행 확인 ↗</a>
        </div>
      </details>)}
    </div>
  </div>;
}

export default function SheetReference({ enemy, lane }: { enemy: string; lane: string }) {
  const [expanded, setExpanded] = useState(false);
  const entries = useMemo(() => (DATA[lane]?.entries || []).filter((item) => item.opponent === enemy), [enemy, lane]);
  const favorable = entries.filter((item) => item.reference.includes("기존 유리"));
  const unfavorable = entries.filter((item) => item.reference.includes("기존 불리"));
  const other = entries.filter((item) => !item.reference.includes("기존 유리") && !item.reference.includes("기존 불리"));
  return <section className="box sheet-reference-panel">
    <div className="sheet-reference-head">
      <div>
        <h2>우리가 만든 시트의 기존 상성 평가</h2>
        <p className="muted">{enemy} · {lane} 기준, 내가 선택할 챔피언 입장에서 본 기존 참고 자료</p>
      </div>
      <a className="external-reference-link" href={SOURCE_URL + "#gid=" + TAB_IDS[lane]} target="_blank" rel="noopener noreferrer">원본 Google Sheets ↗</a>
    </div>
    <p className="sheet-reference-warning">
      시트에 기록된 <strong>기존 참고 의견</strong>이며 최신 패치 검증·승인된 등급이 아닙니다.
      9:1·7:3 등급이나 실제 게임 승률로 해석하지 마세요.
    </p>
    {entries.length ? <>
      <div className="sheet-reference-summary">
        <span>기존 유리 참고 <strong>{favorable.length}건</strong></span>
        <span>기존 불리 참고 <strong>{unfavorable.length}건</strong></span>
        <span>추가 검토 <strong>{other.length}건</strong></span>
      </div>
      <button className="text-button" type="button" onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}>{expanded ? "참고 평가 접기" : "기존 참고 평가 펼치기"}</button>
      {expanded && <div className="sheet-reference-groups">
        <ReferenceGroup heading="내 챔피언 기준 기존 유리 · 미검증" items={favorable} lane={lane}/>
        <ReferenceGroup heading="내 챔피언 기준 기존 불리 · 미검증" items={unfavorable} lane={lane}/>
        <ReferenceGroup heading="별도 조사 기록" items={other} lane={lane}/>
      </div>}
    </> : <p className="muted">이 상대의 기존 분류 기록은 아직 없습니다. 시트에 대진표만 존재하거나 참고 평가가 입력되지 않은 상태입니다.</p>}
    <p className="muted reference-note">원본 시트를 읽어 보관한 스냅샷입니다. 시트를 수정해도 이 화면에는 자동 동기화되지 않습니다. 시트 원본은 변경하지 않았습니다.</p>
  </section>;
}

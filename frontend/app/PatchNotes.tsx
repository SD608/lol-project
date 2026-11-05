"use client";

import { useState } from "react";
import snapshot from "../data/official-patch-snapshot.json";
import detailSnapshot from "../data/official-patch-details.json";

type Category = "전체" | "챔피언" | "아이템" | "룬";
const categories: Category[] = ["전체", "챔피언", "아이템", "룬"];
const entries = detailSnapshot.entries;

export default function PatchNotes() {
  const [category, setCategory] = useState<Category>("전체");
  const [query, setQuery] = useState("");
  const filtered = entries.filter((entry) =>
    (category === "전체" || entry.category === category) &&
    entry.name.replace(/\s/g, "").includes(query.replace(/\s/g, "").trim())
  );
  const checked = new Date(snapshot.checked_at);
  return <div className="patch-notes">
    <div className="page-heading">
      <h1>패치 노트</h1>
      <p>공식 기록을 확인하고, 카운터 분석에 영향을 줄 수 있는 변경 대상을 살펴보세요.</p>
    </div>
    <section className="box">
      <div className="patch-summary-head">
        <div><h2>패치 {snapshot.patch}</h2>
          <p className="muted">공식 패치 노트 수집 기록 · {Number.isNaN(checked.getTime()) ? "확인 일시 미상" : checked.toLocaleString("ko-KR", {timeZone: "Asia/Seoul"}) + " KST"} 확인</p>
        </div>
        <a className="patch-official-link" href={snapshot.official_url} target="_blank" rel="noopener noreferrer">라이엇 공식 원문 보기 ↗</a>
      </div>
      <div className="offmeta-notice" role="status">
        <strong>한국 서버 적용 확인 대기</strong>
        <p>이 화면은 GitHub에 저장된 공식 패치 노트 수집 스냅샷입니다. 현재 라이브 서버에 적용됐다는 뜻은 아니며, 실시간으로 갱신되지 않습니다.</p>
      </div>
      <div className="patch-metrics">
        <span>변경 대상으로 추출된 챔피언 <strong>{snapshot.champions.length}명</strong></span>
        <span>아이템 <strong>{snapshot.items.length}개</strong></span>
        <span>룬 <strong>{snapshot.runes.length}개</strong></span>
      </div>
    </section>
    <section className="box">
      <h2>변경 대상 목록</h2>
      <p className="muted">변경 대상을 클릭하면 공식 패치 노트에서 추출한 변경 전·후 수치를 바로 볼 수 있어요. 전체 패치 적용 여부는 별도로 확인해야 합니다.</p>
      <div className="patch-filters">
        <div className="patch-tabs" role="group" aria-label="변경 대상 종류">
          {categories.map((item) => <button type="button" key={item} className={category === item ? "patch-tab active" : "patch-tab"} onClick={() => setCategory(item)} aria-pressed={category === item}>{item}</button>)}
        </div>
        <label className="patch-filter-label">변경 대상 검색
          <input type="search" placeholder="챔피언 또는 아이템 이름" value={query} onChange={(e) => setQuery(e.target.value)} />
        </label>
      </div>
      {filtered.length ? <div className="patch-detail-list">
        {filtered.map((entry) => <details key={entry.category + entry.name} className="patch-detail-card">
          <summary className="patch-detail-trigger">
            <strong>{entry.name}</strong>
            <span>{entry.category} · 변경 항목 {entry.rows.length}개 · 눌러서 펼치기</span>
          </summary>
          <div className="patch-detail-content">
            {entry.rows.map((change, index) => <div className="patch-change" key={entry.name + index}>
              <strong>{change.label}</strong>
              {"before" in change && "after" in change ? <div className="patch-before-after">
                <div><span className="patch-column-label">변경 전</span><p>{change.before}</p></div>
                <div><span className="patch-column-label">변경 후</span><p>{change.after}</p></div>
              </div> : <p className="muted">{"note" in change ? change.note : "세부 변경 확인 필요"}</p>}
            </div>)}
            <p className="muted patch-detail-disclaimer">공식 수집 기록을 정리한 내용이며, 자유서술식 추가 효과나 변경 내용 전체를 빠짐없이 포함한다고 보장하지 않습니다.</p>
            <a className="patch-inline-source" href={detailSnapshot.official_url} target="_blank" rel="noopener noreferrer">공식 패치 노트 원문 확인 ↗</a>
          </div>
        </details>)}
      </div> : <p className="muted">조건에 맞는 변경 대상이 없습니다.</p>}
    </section>
    <p className="muted classification-note">출처: PICKOU 공식 패치 수집 보고서. 이 목록만으로 상성 등급이나 승률이 변경되지는 않습니다.</p>
  </div>;
}

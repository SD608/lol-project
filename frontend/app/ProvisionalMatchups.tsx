"use client";

import data from "../data/provisional-matchup-reviews.json";

type Review = (typeof data.entries)[number];

function ReviewCard({ review }: { review: Review }) {
  return <article className="mechanic-review-card">
    <div className="mechanic-review-heading">
      <strong>{review.champion}</strong>
      <span>{review.assessment} · 잠정 평가</span>
    </div>
    <p><strong>주요 시점:</strong> {review.phase}</p>
    <ol>{review.mechanisms.map((reason) => <li key={reason}>{reason}</li>)}</ol>
    <p><strong>대응 방법:</strong> {review.counterplay}</p>
    <p className="muted"><strong>판단 한계:</strong> {review.limitations}</p>
    <div className="mechanic-review-sources">
      {review.sources.map((source) => <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer">{source.label} ↗</a>)}
    </div>
  </article>;
}

export default function ProvisionalMatchups({ enemy, lane }: { enemy: string; lane: string }) {
  const reviewed = (data.entries as Review[]).filter((entry) => entry.lane === lane && entry.opponent === enemy);
  return <section className="box mechanic-review-panel">
    <h2>근거 기반 잠정 상성 분석</h2>
    <p className="muted">{enemy} · {lane} · 실제 확인한 스킬 상호작용을 중심으로 분석한 초기 사례</p>
    <p className="sheet-reference-warning">여기에 표시하는 것은 <strong>전투 메커니즘에 대한 예비 평가</strong>입니다. 9:1·7:3 등급이나 실측 승률, 최신 패치 검증 완료 판정이 아닙니다. 상대 챔피언과 라인이 일치하는 분석만 표시합니다.</p>
    {reviewed.length ? <div className="mechanic-review-list">{reviewed.map((review) => <ReviewCard key={review.lane + review.champion + review.opponent} review={review}/>)}</div> :
      <p className="muted">이 조합에 대해 출처와 교전 근거를 정리한 잠정 평가가 아직 없습니다. 아래 전체 챔피언 조사에서 양쪽 공식 스킬을 비교할 수 있으며, 미조사 조합에는 임의 등급을 붙이지 않습니다.</p>}
    <p className="muted reference-note">초기 검토 기록 {data.entries.length}개 방향성 대진 · 나머지 챔피언과 비주류 픽도 조사 대상이나 모두 평가 완료된 것은 아닙니다.</p>
  </section>;
}

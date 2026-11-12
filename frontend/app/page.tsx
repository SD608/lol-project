"use client";
import { useEffect, useMemo, useRef, useState } from 'react';
import { matchRank, type SearchChampion } from './ChampionSearch';
import { FAVORITES_KEY, emptyFavorites, parseFavorites, toggleFavorite, saveFavorites, favoriteFirst, type Favorites } from './favorites';
import { fetchOfficialRoster, resolveOfficialChampionId } from './riotChampionResolver';

type Row = {champion:string; opponent:string; verdict:string; evidence:'statistical'|'theoretical'; advantage:string; caution:string; power_window:string; basis:string};
type Result = {patch:string;lane:string;opponent:string;groups:Record<string,Row[]>;note:string};
const LANES=['탑','정글','미드','바텀','서폿'];
const LABELS=[['hard','하드카운터','강한 유리'],['counter','카운터','유리'],['even','반반','비슷한 상성']];
function Portrait({name,ids,version}:{name:string;ids:Record<string,string>;version:string}) {
 const src=ids[name]?`https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${ids[name]}.png`:'/champion-fallback.svg';
 return <img key={src} src={src} width={64} height={64} alt={name} loading="lazy" onError={e=>{if(!e.currentTarget.src.endsWith('/champion-fallback.svg'))e.currentTarget.src='/champion-fallback.svg';}}/>;
}
export default function Home(){
 const [lane,setLane]=useState('탑');const [query,setQuery]=useState('');const [opponent,setOpponent]=useState('');
 const [champions,setChampions]=useState<SearchChampion[]>([]);const [result,setResult]=useState<Result|null>(null);const [ids,setIds]=useState<Record<string,string>>({});
 const [version,setVersion]=useState('16.22.1');const [error,setError]=useState('');const [loading,setLoading]=useState(false);const [listLoading,setListLoading]=useState(true);const [portraitFailed,setPortraitFailed]=useState(false);
 const [favorites,setFavorites]=useState<Favorites>(emptyFavorites);const [favoritesReady,setFavoritesReady]=useState(false);const [favoritesOnly,setFavoritesOnly]=useState(false);const [storageFailed,setStorageFailed]=useState(false);
 const resultsRef=useRef<HTMLElement>(null);
 useEffect(()=>{try{setFavorites(parseFavorites(window.localStorage.getItem(FAVORITES_KEY)));}catch{setStorageFailed(true);}setFavoritesReady(true);},[]);
 useEffect(()=>{if(!favoritesReady)return;try{setStorageFailed(!saveFavorites(window.localStorage,favorites));}catch{setStorageFailed(true);}},[favorites,favoritesReady]);
 useEffect(()=>{const controller=new AbortController();let active=true;setChampions([]);setListLoading(true);setError('');
  fetch(`/api/counter-guide/champions?lane=${encodeURIComponent(lane)}`,{signal:controller.signal}).then(async r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{if(active)setChampions(d.items);}).catch(e=>{if(active&&e.name!=='AbortError')setError('챔피언 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.');}).finally(()=>{if(active)setListLoading(false);});
  return()=>{active=false;controller.abort();};
 },[lane]);
 useEffect(()=>{let active=true;fetch('/api/counter-guide/metadata').then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{if(active)setVersion(d.ddragon_version);}).catch(()=>{});return()=>{active=false;};},[]);
 useEffect(()=>{let active=true;fetchOfficialRoster(version).then(roster=>{if(!active)return;const mapped:Record<string,string>={};for(const entry of Object.values(roster)){if(entry.name){try{mapped[entry.name]=resolveOfficialChampionId({name:entry.name},roster);}catch{}}}setIds(mapped);}).catch(()=>{if(active)setPortraitFailed(true);});return()=>{active=false;};},[version]);
 useEffect(()=>{setResult(null);if(!opponent)return;const controller=new AbortController();let active=true;setLoading(true);setError('');
  fetch(`/api/counter-guide/counters?lane=${encodeURIComponent(lane)}&opponent=${encodeURIComponent(opponent)}`,{signal:controller.signal}).then(async r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{if(active)setResult(d);}).catch(e=>{if(active&&e.name!=='AbortError')setError('상성 데이터를 불러오지 못했습니다. 챔피언을 다시 선택해 주세요.');}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;controller.abort();};
 },[lane,opponent]);
 useEffect(()=>{if(result&&window.matchMedia('(max-width:640px)').matches)resultsRef.current?.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});},[result]);
 const options=useMemo(()=>favoriteFirst(champions.filter(c=>c.lanes?.includes(lane)&&matchRank(c,query)<99).sort((a,b)=>matchRank(a,query)-matchRank(b,query)||a.name.localeCompare(b.name,'ko')),favorites[lane]||[],favoritesOnly),[champions,query,lane,favorites,favoritesOnly]);
 function selectLane(next:string){setLane(next);setOpponent('');setQuery('');setResult(null);setLoading(false);}
 function selectOpponent(name:string){setOpponent(name);if(name===opponent&&error){setOpponent('');setTimeout(()=>setOpponent(name),0);}}
 function cards(rows:Row[],label:string){return rows.map(row=><article className="cg-card" key={row.champion} data-champion={row.champion}>
  <div className="cg-card-top"><Portrait name={row.champion} ids={ids} version={version}/><div><h3>{row.champion}</h3><span className="cg-grade">{label}</span></div><span className={`cg-evidence ${row.evidence}`} title={row.basis}>{row.evidence==='statistical'?'통계 확인':'이론 참고'}</span></div>
  <p>{row.advantage} {row.caution}</p><div className="cg-window">유리한 구간 <span>{row.power_window}</span></div>
 </article>);}
 return <main className="cg-shell"><header className="cg-header"><a href="/" aria-label="PICKOU 홈">PICKOU<span aria-hidden="true">.</span></a></header>
  <nav className="cg-lanes" aria-label="포지션 선택">{LANES.map((name,i)=><button key={name} aria-pressed={lane===name} onClick={()=>selectLane(name)}><span aria-hidden="true">{['↖','♧','◇','⌁','✧'][i]}</span>{name}</button>)}</nav>
  <section className="cg-picker" aria-labelledby="picker-title"><div className="cg-eyebrow">COUNTER GUIDE <span>PATCH 26.22</span></div><h1 id="picker-title">상대의 픽, <span>나의 기회.</span></h1><p className="cg-intro">{lane}에서 만날 상대를 고르세요. 카운터와 그 이유를 바로 확인하세요.</p>
   <div className="cg-search"><span aria-hidden="true">⌕</span><input aria-label="상대 챔피언 검색" value={query} onChange={e=>setQuery(e.target.value)} placeholder="상대 챔피언 검색 · 이름, 약어, 초성" autoComplete="off"/>{query&&<button aria-label="검색어 지우기" onClick={()=>setQuery('')}>×</button>}</div>
   <div className="cg-favorite-tools"><label><input type="checkbox" checked={favoritesOnly} disabled={!favoritesReady} onChange={e=>setFavoritesOnly(e.target.checked)}/>즐겨찾기만 보기</label><span>포지션별 · 이 브라우저에 저장</span></div>
   {storageFailed&&<p className="cg-storage-note" role="status">브라우저에 저장할 수 없어 즐겨찾기가 현재 화면에서만 유지됩니다.</p>}
   <div className="cg-list-title"><span>{opponent?`선택한 상대 · ${opponent}`:'상대 챔피언 선택'}</span><span>{options.length}명</span></div>
   {listLoading?<p role="status">챔피언을 불러오는 중…</p>:<div className="cg-champions" aria-label={`${lane} 상대 챔피언 목록`}>{options.map(c=>{const favorite=(favorites[lane]||[]).includes(c.name);return <div className="cg-champion-tile" key={c.name}><button className="cg-champion-select" aria-label={c.name} aria-pressed={opponent===c.name} onClick={()=>selectOpponent(c.name)}><Portrait name={c.name} ids={ids} version={version}/><span>{c.name}</span></button><button className="cg-favorite" aria-label={`${c.name} 즐겨찾기 ${favorite?'해제':'등록'}`} title={`${c.name} 즐겨찾기 ${favorite?'해제':'등록'}`} aria-pressed={favorite} disabled={!favoritesReady} onClick={e=>{e.stopPropagation();setFavorites(previous=>toggleFavorite(previous,lane,c.name));}}><span aria-hidden="true">{favorite?'★':'☆'}</span></button></div>;})}{!options.length&&<p className="cg-no-search">{favoritesOnly&&!(favorites[lane]||[]).some(name=>champions.some(c=>c.name===name))?'이 포지션에 즐겨찾기한 챔피언이 없습니다.':'일치하는 챔피언이 없습니다.'}</p>}</div>}
  </section>
  {error&&<p className="cg-error" role="alert">{error}<button onClick={()=>window.location.reload()}>새로고침</button></p>}
  <section className="cg-results" ref={resultsRef} aria-label="카운터 조회 결과" aria-live="polite" aria-busy={loading}>
   {loading?<p className="cg-empty" role="status">카운터를 불러오는 중…</p>:result?<><div className="cg-result-title"><Portrait name={opponent} ids={ids} version={version}/><div><span>{lane} · 상대 챔피언</span><h2>{opponent}<small> 상대하기</small></h2></div><span className="cg-patch">26.22</span></div>
    <p className="cg-source-note">통계 확인은 제공 상성표의 승률·표본 확인 분류입니다. 이론 참고는 검증 전 가설이며 실제 승률을 뜻하지 않습니다.</p>
    {LABELS.map(([key,label,description])=><section key={key} className={`cg-group ${key}`}><div className="cg-group-title"><h2>{label} <span>{result.groups[key].length}</span></h2><p>{description}</p></div>{result.groups[key].length?<div className="cg-cards">{cards(result.groups[key],label)}</div>:<p className="cg-none">제공 상성표에 해당 분류가 없습니다.</p>}</section>)}
    {!!result.groups.unfavorable.length&&<details className="cg-unfavorable"><summary>불리한 상성도 보기 · {result.groups.unfavorable.length}명</summary><div className="cg-cards">{cards(result.groups.unfavorable,'불리')}</div></details>}
   </>:!error&&<div className="cg-empty"><span aria-hidden="true">◇</span><h2>다음 픽의 이유를 찾아보세요.</h2><p>상대 챔피언을 선택하면 카운터가 여기에 나타납니다.</p></div>}
  </section><footer className="cg-footer">PICKOU · 제공 상성표 26.22 기준{portraitFailed&&<span>초상화를 불러오지 못해 대체 이미지를 표시합니다.</span>}</footer>
 </main>;
}

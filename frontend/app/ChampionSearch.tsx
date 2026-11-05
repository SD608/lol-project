"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";

export type SearchChampion = {
  name: string;
  riot_id?: string | null;
  aliases?: string[];
  initials?: string | null;
  lanes?: string[];
};

type Props = {
  label: string;
  value: string;
  items: SearchChampion[];
  selectedLane?: string;
  disabled?: boolean;
  onChange: (name: string) => void;
};

// Common Korean nicknames. The API also supplies canonical aliases.
const EXTRA_ALIASES: Record<string, string[]> = {
  "케이틀린": ["케틀", "케틀린"],
  "미스 포츈": ["미포"],
  "트위스티드 페이트": ["트페"],
  "아우렐리온 솔": ["아우솔"],
  "이즈리얼": ["이즈"],
  "블리츠크랭크": ["블츠", "블리츠"],
  "말파이트": ["말파"],
  "리 신": ["리신"],
  "아펠리오스": ["아펠"],
  "카시오페아": ["카시"],
  "렐": ["렐"],
};

const JAMO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ";
const normalize = (text: string) => text.toLocaleLowerCase().replace(/\s/g, "");
function initials(text: string) {
  return [...text].map((c) => {
    const cp = c.codePointAt(0) ?? 0;
    return cp >= 0xac00 && cp <= 0xd7a3 ? JAMO[Math.floor((cp - 0xac00) / 588)] : c;
  }).join("").replace(/\s/g, "");
}

function matchRank(item: SearchChampion, query: string) {
  const q = normalize(query);
  if (!q) return 1;
  const name = normalize(item.name);
  const id = normalize(item.riot_id || "");
  const initial = normalize(item.initials || initials(item.name));
  const aliases = [...(item.aliases || []), ...(EXTRA_ALIASES[item.name] || [])].map(normalize);
  if (name === q || id === q || aliases.includes(q)) return 0;
  if (name.startsWith(q) || id.startsWith(q) || aliases.some((a) => a.startsWith(q))) return 1;
  if (initial === q || initial.startsWith(q)) return 2;
  if ([name, id, initial, ...aliases].some((candidate) => candidate.includes(q))) return 3;
  return 99;
}

export default function ChampionSearch({ label, value, items, selectedLane, disabled, onChange }: Props) {
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const id = useId();

  useEffect(() => { if (value) setQuery(value); }, [value]);
  useEffect(() => {
    const closeOutside = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, []);

  const options = useMemo(() => {
    const q = query.trim();
    const ranked = items.map((item) => ({
      item, rank: matchRank(item, q),
      isRegistered: !selectedLane || (item.lanes || []).includes(selectedLane),
    })).filter((candidate) => candidate.rank < 99);
    ranked.sort((a, b) =>
      a.rank - b.rank ||
      Number(b.isRegistered) - Number(a.isRegistered) ||
      a.item.name.localeCompare(b.item.name, "ko")
    );
    return ranked.slice(0, 30);
  }, [items, query, selectedLane]);

  const choose = (name: string) => {
    onChange(name);
    setQuery(name);
    setOpen(false);
    setHighlight(0);
  };

  return <div className="field champion-field" ref={root}>
    <label htmlFor={id}>{label}</label>
    <input
      id={id}
      className="champion-input"
      type="text"
      role="combobox"
      autoComplete="off"
      aria-autocomplete="list"
      aria-expanded={open && !disabled}
      aria-controls={open && !disabled ? id + "-list" : undefined}
      aria-activedescendant={open && options.length ? id + "-option-" + Math.min(highlight, options.length - 1) : undefined}
      placeholder="이름 · 초성 · 별칭 · 영문 검색"
      disabled={disabled}
      value={query}
      onFocus={() => { setOpen(true); setHighlight(0); }}
      onChange={(e) => {
        setQuery(e.target.value);
        setOpen(true);
        setHighlight(0);
        if (value) onChange("");
      }}
      onKeyDown={(e) => {
        if (e.key === "Escape") { setOpen(false); return; }
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setOpen(true);
          setHighlight((i) => Math.min(i + 1, Math.max(options.length - 1, 0)));
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          setOpen(true);
          setHighlight((i) => Math.max(i - 1, 0));
        }
        if (e.key === "Enter" && open && options.length) {
          e.preventDefault();
          choose(options[Math.min(highlight, options.length - 1)].item.name);
        }
      }}
    />
    {open && !disabled && <div className="champion-options" id={id + "-list" role="listbox" aria-label={label + " 검색 결과"}>
      {options.length ? options.map(({ item, isRegistered }, i) => <button
        type="button"
        role="option"
        aria-selected={i === highlight}
        id={id + "-option-" + i}
        key={item.name}
        className={"champion-option" + (i === highlight ? " highlighted" : "")}
        onMouseDown={(e) => e.preventDefault()}
        onMouseEnter={() => setHighlight(i)}
        onClick={() => choose(item.name)}
      >
        <span className="champion-option-primary"><strong>{item.name}</strong>
          {item.riot_id && <small>{item.riot_id}</small>}
        </span>
        <span className="champion-lane-tags">
          {item.lanes?.length ? item.lanes.map((lane) => <small key={lane} className={lane === selectedLane ? "champion-lane-tag is-selected" : "champion-lane-tag"}>{lane}</small>) : <small>등록 라인 없음</small>}
          {selectedLane && !isRegistered && <small className="champion-offmeta-tag">{selectedLane} 비주류</small>}
        </span>
      </button>) : <div className="champion-empty">검색 결과가 없습니다. 다른 이름이나 초성으로 검색해 보세요.</div>}
    </div>}
    {value && selectedLane && items.some((champ) => champ.name === value && champ.lanes && !champ.lanes.includes(selectedLane)) &&
      <small className="champion-selection">선택한 챔피언은 {selectedLane} 등록 명단에 없어. 비주류 픽으로 조회할 수 있어.</small>}
  </div>;
}

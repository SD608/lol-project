"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";

export type SearchChampion = {
  name: string;
  riot_id?: string | null;
  aliases?: string[];
  initials?: string | null;
};

type Props = {
  label: string;
  value: string;
  items: SearchChampion[];
  disabled?: boolean;
  onChange: (name: string) => void;
};

const JAMO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ";
const normalize = (text: string) => text.toLocaleLowerCase().replace(/\s/g, "");
function initials(text: string) {
  return [...text].map((c) => {
    const cp = c.codePointAt(0) ?? 0;
    return cp >= 0xac00 && cp <= 0xd7a3 ? JAMO[Math.floor((cp - 0xac00) / 588)] : c;
  }).join("").replace(/\s/g, "");
}
function matches(item: SearchChampion, query: string) {
  const q = normalize(query);
  return [item.name, item.initials || initials(item.name), item.riot_id || "", ...(item.aliases || [])]
    .some((candidate) => normalize(candidate).includes(q));
}

export default function ChampionSearch({ label, value, items, disabled, onChange }: Props) {
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
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
    if (!q) return items.slice(0, 30);
    return items.filter((item) => matches(item, q)).slice(0, 30);
  }, [items, query]);

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
      ref={input}
      className="champion-input"
      type="text"
      role="combobox"
      autoComplete="off"
      aria-autocomplete="list"
      aria-expanded={open && !disabled}
      aria-controls={id + "-list"}
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
          setHighlight((i) => Math.min(i + 1, options.length - 1));
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          setOpen(true);
          setHighlight((i) => Math.max(i - 1, 0));
        }
        if (e.key === "Enter" && open && options.length) {
          e.preventDefault();
          choose(options[Math.min(highlight, options.length - 1)].name);
        }
      }}
    />
    {open && !disabled && <div className="champion-options" id={id + "-list"} role="listbox" aria-label={label + " 검색 결과"}>
      {options.length ? options.map((item, i) => <button
        type="button"
        role="option"
        aria-selected={i === highlight}
        id={id + "-option-" + i}
        key={item.name}
        className={"champion-option" + (i === highlight ? " highlighted" : "")}
        onMouseDown={(e) => e.preventDefault()}
        onMouseEnter={() => setHighlight(i)}
        onClick={() => choose(item.name)}
      ><span>{item.name}</span>{item.riot_id && <small>{item.riot_id}</small>}</button>) :
        <div className="champion-empty">검색 결과가 없습니다.</div>}
    </div>}

  </div>;
}

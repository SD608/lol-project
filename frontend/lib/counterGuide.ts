import { readFileSync } from 'node:fs';
import { join } from 'node:path';

export interface GuideChampion {
  name: string;
  aliases: string[];
  initials: string;
  lanes: string[];
}

export interface GuideRow {
  lane: string;
  champion: string;
  opponent: string;
  group: 'hard' | 'counter' | 'even' | 'unfavorable';
  evidence: 'statistical' | 'theoretical';
  [key: string]: unknown;
}

interface GuideData {
  patch: string;
  ddragon_version: string;
  counts: Record<string, number>;
  lanes: Record<string, string[]>;
  champions: GuideChampion[];
  rows: GuideRow[];
}

let cached: GuideData | undefined;
let byOpponent: Map<string, GuideRow[]> | undefined;

export function getGuide(): GuideData {
  if (!cached) {
    const source = join(process.cwd(), 'data', 'counter-guide-26.22.json');
    const parsed = JSON.parse(readFileSync(source, 'utf8')) as GuideData;
    if (parsed.patch !== '26.22' ||
        parsed.champions.length !== 173 ||
        Object.values(parsed.lanes).reduce((n, names) => n + names.length, 0) !== 266 ||
        parsed.rows.length !== 14468) {
      throw new Error('Unexpected PICKOU guide dataset');
    }
    cached = parsed;
  }
  return cached;
}

export function getCounterRows(lane: string, opponent: string) {
  const data = getGuide();
  if (!byOpponent) {
    byOpponent = new Map();
    for (const row of data.rows) {
      const key = JSON.stringify([row.lane, row.opponent]);
      if (!byOpponent.has(key)) byOpponent.set(key, []);
      byOpponent.get(key)!.push(row);
    }
  }
  const groups: Record<string, GuideRow[]> = { hard: [], counter: [], even: [], unfavorable: [] };
  const entries = byOpponent.get(JSON.stringify([lane, opponent])) ?? [];
  for (const entry of entries) {
    if (Object.prototype.hasOwnProperty.call(groups, entry.group)) {
      groups[entry.group].push(entry);
    }
  }
  for (const rows of Object.values(groups)) {
    rows.sort((a, b) => Number(a.evidence !== 'statistical') - Number(b.evidence !== 'statistical') ||
      a.champion.localeCompare(b.champion, 'ko'));
  }
  return groups;
}

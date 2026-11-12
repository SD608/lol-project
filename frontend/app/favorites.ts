/** Browser-only preferences. Never sent to the API or used as matchup evidence. */
export const FAVORITES_KEY = 'pickou.favorites.v1';
const LANES = ['탑', '정글', '미드', '바텀', '서폿'];
export type Favorites = Record<string, string[]>;
export function emptyFavorites(): Favorites {
  return Object.fromEntries(LANES.map(lane => [lane, []]));
}
export function parseFavorites(raw: string | null): Favorites {
  const result = emptyFavorites();
  if (!raw || raw.length > 100_000) return result;
  try {
    const value = JSON.parse(raw);
    if (value?.version !== 1 || !value.lanes || typeof value.lanes !== 'object') return result;
    for (const lane of LANES) {
      const names = value.lanes[lane];
      if (Array.isArray(names)) {
        result[lane] = [...new Set(names.filter((name): name is string =>
          typeof name === 'string' && name.length > 0 && name.length <= 100
        ))].slice(0, 173);
      }
    }
  } catch { /* Corrupt browser data must not prevent counter lookup. */ }
  return result;
}
export function toggleFavorite(current: Favorites, lane: string, name: string): Favorites {
  if (!LANES.includes(lane)) return current;
  const names = current[lane] || [];
  return { ...current, [lane]: names.includes(name) ? names.filter(n => n !== name) : [...names, name] };
}
export function saveFavorites(storage: Pick<Storage, 'setItem'>, favorites: Favorites): boolean {
  try {
    storage.setItem(FAVORITES_KEY, JSON.stringify({ version: 1, lanes: favorites }));
    return true;
  } catch { return false; }
}
export function favoriteFirst<T extends { name: string }>(items: T[], names: string[], only: boolean): T[] {
  const favorites = new Set(names);
  // Stable sort preserves the existing search rank within each group.
  return items.filter(item => !only || favorites.has(item.name))
    .sort((a, b) => Number(favorites.has(b.name)) - Number(favorites.has(a.name)));
}

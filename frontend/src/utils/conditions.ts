// Mirrors backend/services/ebay/metadata.py (severity order + text mapping).
// The backend remains authoritative; this keeps the UI consistent with it.

export interface ConditionOption {
  enum: string;
  label: string;
}

// Best -> worst.
const SEVERITY = [
  'NEW', 'NEW_OTHER', 'NEW_WITH_DEFECTS', 'CERTIFIED_REFURBISHED',
  'EXCELLENT_REFURBISHED', 'VERY_GOOD_REFURBISHED', 'GOOD_REFURBISHED',
  'SELLER_REFURBISHED', 'LIKE_NEW', 'USED_EXCELLENT', 'USED_VERY_GOOD',
  'USED_GOOD', 'USED_ACCEPTABLE', 'FOR_PARTS_OR_NOT_WORKING',
];

// Shown until a category is chosen (or if eBay's list can't be fetched).
export const GENERIC_CONDITION_OPTIONS: ConditionOption[] = [
  { enum: 'NEW', label: 'New' },
  { enum: 'LIKE_NEW', label: 'Like New' },
  { enum: 'USED_EXCELLENT', label: 'Used - Excellent' },
  { enum: 'USED_GOOD', label: 'Used - Good' },
  { enum: 'USED_ACCEPTABLE', label: 'Used - Acceptable' },
  { enum: 'FOR_PARTS_OR_NOT_WORKING', label: 'For Parts or Not Working' },
];

const TEXT_TO_ENUM: Record<string, string> = {
  'NEW': 'NEW',
  'BRAND NEW': 'NEW',
  'LIKE NEW': 'LIKE_NEW',
  'USED - LIKE NEW': 'LIKE_NEW',
  'USED - EXCELLENT': 'USED_EXCELLENT',
  'EXCELLENT': 'USED_EXCELLENT',
  'USED - VERY GOOD': 'USED_VERY_GOOD',
  'VERY GOOD': 'USED_VERY_GOOD',
  'USED - GOOD': 'USED_GOOD',
  'GOOD': 'USED_GOOD',
  'USED': 'USED_GOOD',
  'PRE-OWNED': 'USED_GOOD',
  'USED - FAIR': 'USED_ACCEPTABLE',
  'USED - ACCEPTABLE': 'USED_ACCEPTABLE',
  'FAIR': 'USED_ACCEPTABLE',
  'ACCEPTABLE': 'USED_ACCEPTABLE',
  'FOR PARTS': 'FOR_PARTS_OR_NOT_WORKING',
  'FOR PARTS OR NOT WORKING': 'FOR_PARTS_OR_NOT_WORKING',
  'REFURBISHED': 'SELLER_REFURBISHED',
  'OPEN BOX': 'NEW_OTHER',
};

/** Free text (Claude output, legacy drafts) or enum -> eBay condition enum, or null. */
export function normalizeCondition(raw?: string | null): string | null {
  if (!raw) return null;
  const key = raw.trim().toUpperCase();
  if (SEVERITY.includes(key)) return key;
  return TEXT_TO_ENUM[key] ?? TEXT_TO_ENUM[key.replace(/_/g, ' ')] ?? null;
}

/** Same value if allowed, else nearest equal-or-worse (never silently upgrade). */
export function snapCondition(value: string, allowed: string[]): string | null {
  if (allowed.includes(value)) return value;
  const idx = SEVERITY.indexOf(value);
  if (idx === -1) return null;
  for (const c of SEVERITY.slice(idx + 1)) if (allowed.includes(c)) return c;
  for (const c of [...SEVERITY.slice(0, idx)].reverse()) if (allowed.includes(c)) return c;
  return null;
}

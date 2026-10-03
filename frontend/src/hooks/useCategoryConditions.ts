import { useEffect, useState } from 'react';
import { getCategoryConditions } from '../services/api';
import { ConditionOption, GENERIC_CONDITION_OPTIONS, normalizeCondition, snapCondition } from '../utils/conditions';

/**
 * Loads the conditions eBay allows for a category and keeps `condition`
 * valid: free text is normalized to an enum, and a value the category
 * doesn't allow is snapped to the nearest allowed one (with a notice).
 */
export function useCategoryConditions(
  categoryId: string | undefined,
  condition: string,
  setCondition: (value: string) => void,
) {
  const [options, setOptions] = useState<ConditionOption[]>(GENERIC_CONDITION_OPTIONS);
  const [fromEbay, setFromEbay] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  // Fetch options when the category changes
  useEffect(() => {
    let cancelled = false;
    setNotice(null);
    if (!categoryId) {
      setOptions(GENERIC_CONDITION_OPTIONS);
      setFromEbay(false);
      return;
    }
    getCategoryConditions(categoryId)
      .then((res) => {
        if (cancelled) return;
        if (res.conditions.length > 0) {
          setOptions(res.conditions.map((c) => ({ enum: c.enum, label: c.label })));
          setFromEbay(true);
        } else {
          setOptions(GENERIC_CONDITION_OPTIONS);
          setFromEbay(false);
        }
      })
      .catch(() => {
        if (cancelled) return;
        setOptions(GENERIC_CONDITION_OPTIONS);
        setFromEbay(false);
      });
    return () => { cancelled = true; };
  }, [categoryId]);

  // Keep the current value valid for the available options
  useEffect(() => {
    const normalized = normalizeCondition(condition);
    const allowed = options.map((o) => o.enum);
    if (!normalized) return;
    const target = fromEbay ? snapCondition(normalized, allowed) : normalized;
    if (target && target !== condition) {
      setCondition(target);
      if (fromEbay && target !== normalized) {
        const label = options.find((o) => o.enum === target)?.label ?? target;
        setNotice(`Condition changed to "${label}" — the original isn't available in this category.`);
      }
    }
  }, [options, fromEbay, condition, setCondition]);

  return { options, fromEbay, notice };
}

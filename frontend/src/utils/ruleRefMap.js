/**
 * Nirikshan Rule Ref Map & Helper
 * Guarantees a bare rule id never appears without its rule_ref next to it.
 */
export const RULE_REF_MAP = {
  R01: 'Rule 6(1)(a)',
  R02: 'Rule 10(1) Expl. I',
  R03: 'Rule 6(1)(a) Expl. I–II',
  R04: 'Rule 6(1)(aa)',
  R05: 'Rule 6(1)(b)',
  R06: 'Rule 6(1)(c) read with Rule 12 & 13',
  R07: 'Rule 13(4)',
  R08: 'Rule 13(5)',
  R09: 'Rule 12(6)',
  R10: 'Rule 6(1)(d)',
  R11: 'Rule 6(1)(da)',
  R12: 'Rule 6(1)(e) read with Rule 2(m)',
  R14: 'Rule 6(11)',
  R15: 'Rule 6(2)',
  R17: 'Rule 18(2A)',
  R19: 'Rule 7(3)',
  R20: 'Rule 8(1)',
  R21: 'Rule 9(1)(a)',
  R22: 'Rule 9(1)(b)',
  R23: 'Rule 9(4)',
  R25: 'Rule 26(a)',
  R26: 'Rule 3',
  R27: 'Rule 24',
  R31: 'First Schedule MPE / Rule 22',
  R32: 'Rules 19–21',
  R35: 'Rule 7(5) / Rule 6(1)(a) Expl. III',
};

/**
 * Returns formatted rule reference with rule id.
 * e.g. "Rule 6(1)(a) · R01" or "Rule 6(1)(a) (R01)"
 */
export function getFullRuleRef(findingOrRule) {
  if (!findingOrRule) return '';
  const id = typeof findingOrRule === 'string' ? findingOrRule : (findingOrRule.rule_id || findingOrRule.id);
  const ref = typeof findingOrRule === 'object' && findingOrRule.rule_ref && findingOrRule.rule_ref !== id
    ? findingOrRule.rule_ref
    : (RULE_REF_MAP[id] || '');

  if (ref && id) {
    return `${ref} · ${id}`;
  }
  return ref || id || '';
}

import { describe, it, expect } from 'vitest';
import en from './en.json';
import hi from './hi.json';

describe('i18n key set completeness', () => {
  it('en.json and hi.json have identical key sets', () => {
    const enKeys = Object.keys(en).sort();
    const hiKeys = Object.keys(hi).sort();
    expect(enKeys).toEqual(hiKeys);
  });
});

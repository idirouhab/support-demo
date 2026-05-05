import { describe, expect, it } from 'vitest';

import { getStatusLabel } from './status';

describe('getStatusLabel', () => {
  it('formats known frontend statuses', () => {
    expect(getStatusLabel('open')).toBe('Open');
    expect(getStatusLabel('pending')).toBe('Pending');
    expect(getStatusLabel('in-progress')).toBe('In progress');
    expect(getStatusLabel('resolved')).toBe('Resolved');
  });

  it('falls back for unknown statuses', () => {
    expect(getStatusLabel('blocked')).toBe('Unknown');
  });
});

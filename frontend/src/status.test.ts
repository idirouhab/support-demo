import { describe, expect, it } from 'vitest';

import { getStatusClassName, getStatusLabel } from './status';

describe('getStatusLabel', () => {
  it('formats canonical API statuses', () => {
    expect(getStatusLabel('open')).toBe('Open');
    expect(getStatusLabel('pending')).toBe('Pending');
    expect(getStatusLabel('in_progress')).toBe('In progress');
    expect(getStatusLabel('resolved')).toBe('Resolved');
  });

  it('falls back for unknown statuses', () => {
    expect(getStatusLabel('blocked')).toBe('Unknown');
    expect(getStatusLabel('toString')).toBe('Unknown');
    expect(getStatusClassName('blocked')).toBe('status status-unknown');
    expect(getStatusClassName('in_progress')).toBe('status status-in_progress');
  });

  it.each([
    ['open', 'Open'],
    ['pending', 'Pending'],
    ['in_progress', 'In progress'],
    ['resolved', 'Resolved'],
  ])('formats the label and badge class for %s', (status, label) => {
    expect(getStatusLabel(status)).toBe(label);
    expect(getStatusClassName(status)).toBe(`status status-${status}`);
  });

  it.each(['blocked', 'in-progress', '', 'toString', '__proto__'])('uses a safe fallback for %j', (status) => {
    expect(getStatusLabel(status)).toBe('Unknown');
    expect(getStatusClassName(status)).toBe('status status-unknown');
  });
});

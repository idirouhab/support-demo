import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import { fetchTickets } from './api';
import type { Ticket } from './types';

const tickets: Ticket[] = [
  {
    id: 'T-201',
    title: 'Cannot download invoice',
    requester: 'Maya Patel',
    priority: 'high',
    status: 'open',
    created_at: '2026-05-01T09:15:00Z',
  },
  {
    id: 'T-202',
    title: 'Refund request needs manager approval',
    requester: 'Owen Chen',
    priority: 'medium',
    status: 'in-progress',
    created_at: '2026-05-02T14:40:00Z',
  },
  {
    id: 'T-203',
    title: 'Login issue resolved after password reset',
    requester: 'Leo Martin',
    priority: 'medium',
    status: 'resolved',
    created_at: '2026-05-04T16:20:00Z',
  },
];

function mockTicketResponse(nextTickets: Ticket[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(nextTickets),
      }),
    ),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('fetchTickets', () => {
  it.each([400, 500])('rejects HTTP %s without parsing the error body', async (status) => {
    const json = vi.fn().mockRejectedValue(new SyntaxError('Unexpected token <'));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status, json }));

    await expect(fetchTickets()).rejects.toThrow(`Ticket request failed (HTTP ${status})`);
    expect(json).not.toHaveBeenCalled();
  });

  it('accepts a successful empty ticket list', async () => {
    mockTicketResponse([]);

    await expect(fetchTickets()).resolves.toEqual([]);
  });
});

describe('App', () => {
  it('renders the ticket dashboard from the API', async () => {
    mockTicketResponse(tickets);

    render(<App />);

    expect(screen.getByText('Loading tickets...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText('Cannot download invoice')).toBeInTheDocument();
    });

    expect(screen.getByText(/compact support workflow/)).toBeInTheDocument();
    expect(screen.getByText('Refund request needs manager approval')).toBeInTheDocument();
    expect(screen.getByText('In progress')).toBeInTheDocument();
    expect(screen.getByText('GitLab CI ready')).toBeInTheDocument();
  });

  it('shows an error when the API fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 500,
        }),
      ),
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Could not load tickets/)).toBeInTheDocument();
    });
  });
});

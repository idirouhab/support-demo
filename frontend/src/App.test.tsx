import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import { fetchTickets } from './api';
import type { Ticket } from './types';

const tickets: Ticket[] = [
  {
    id: 'T-201',
    title: 'Cannot download invoice',
    description: 'The invoice download stops with an error.',
    requester: 'Maya Patel',
    priority: 'high',
    status: 'open',
    created_at: '2026-05-01T09:15:00Z',
  },
  {
    id: 'T-202',
    title: 'Refund request needs manager approval',
    description: 'Please review the refund request.',
    requester: 'Owen Chen',
    priority: 'medium',
    status: 'in_progress',
    created_at: '2026-05-02T14:40:00Z',
  },
  {
    id: 'T-203',
    title: 'Login issue resolved after password reset',
    description: '',
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
  it('renders an accessible ticket queue with the right data in each entry', async () => {
    const queue = [
      ...tickets,
      { ...tickets[0], id: 'T-204', status: 'pending', priority: 'low' },
      { ...tickets[0], id: 'T-205', status: 'blocked' },
    ] as Ticket[];
    const labels = ['Open', 'In progress', 'Resolved', 'Pending', 'Unknown'];
    mockTicketResponse(queue);
    render(<App />);

    const list = await screen.findByRole('navigation', { name: 'Current tickets' });
    expect(within(list).getAllByRole('listitem')).toHaveLength(queue.length);
    for (const [index, ticket] of queue.entries()) {
      const entry = within(list).getByRole('button', { name: `View details for ${ticket.id}` });
      expect(within(entry).getByText(ticket.title)).toBeInTheDocument();
      expect(within(entry).getByText(ticket.requester)).toBeInTheDocument();
      expect(within(entry).getByText(labels[index])).toBeInTheDocument();
      expect(within(entry).getByText(ticket.priority)).toBeInTheDocument();
      fireEvent.click(entry);
      const details = screen.getByRole('region', { name: 'Ticket details' });
      const created = new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(ticket.created_at));
      expect(within(details).getByText(created)).toHaveAttribute('datetime', ticket.created_at);
    }
  });

  it('shows an empty queue message after a successful empty response', async () => {
    mockTicketResponse([]);
    render(<App />);

    expect(await screen.findByText('No tickets to display.')).toBeInTheDocument();
    expect(screen.queryByText('Loading tickets...')).not.toBeInTheDocument();
    expect(screen.queryByText(/Could not load tickets/)).not.toBeInTheDocument();
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
  });

  it.each([
    {
      name: 'mixed statuses and priorities',
      queue: [...tickets, { ...tickets[0], id: 'T-204', status: 'pending', priority: 'low' }] as Ticket[],
      total: 4, active: 3, highPriority: 1,
    },
    {
      name: 'an all-resolved queue',
      queue: tickets.map((ticket) => ({ ...ticket, status: 'resolved' as const })),
      total: 3, active: 0, highPriority: 1,
    },
    { name: 'an empty queue', queue: [], total: 0, active: 0, highPriority: 0 },
    {
      name: 'only medium and low priorities',
      queue: tickets.slice(1), total: 2, active: 1, highPriority: 0,
    },
    {
      name: 'an unknown API status',
      queue: [{ ...tickets[0], status: 'blocked' }] as unknown as Ticket[],
      total: 1, active: 0, highPriority: 1,
    },
  ])('counts summary values for $name', async ({ queue, total, active, highPriority }) => {
    mockTicketResponse(queue);
    render(<App />);

    await waitFor(() => expect(screen.queryByText('Loading tickets...')).not.toBeInTheDocument());
    for (const [label, count] of [['Total tickets', total], ['Active', active], ['High priority', highPriority]] as const) {
      expect(within(screen.getByRole('group', { name: label })).getByText(String(count))).toBeInTheDocument();
    }
  });

  it('renders an unknown API status with a consistent fallback badge', async () => {
    mockTicketResponse([{ ...tickets[0], status: 'blocked' }] as unknown as Ticket[]);
    render(<App />);
    const queue = await screen.findByRole('navigation', { name: 'Current tickets' });
    expect(within(queue).getByText('Unknown')).toHaveClass('status', 'status-unknown');
  });

  it('selects tickets and cancels without saving draft edits', async () => {
    mockTicketResponse(tickets);
    render(<App />);

    const buttons = await screen.findAllByRole('button', { name: /View details for/ });
    expect(buttons).toHaveLength(tickets.length);
    expect(buttons[0]).toHaveAttribute('aria-current', 'true');
    const details = screen.getByRole('region', { name: 'Ticket details' });
    expect(buttons[0]).toHaveAttribute('aria-controls', details.id);
    expect(screen.getByLabelText('Title')).toHaveValue(tickets[0].title);
    expect(screen.getByLabelText('Description')).toHaveValue(tickets[0].description);
    expect(screen.getByLabelText('Status')).toHaveValue('open');
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Unsaved title' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByLabelText('Title')).toHaveValue(tickets[0].title);
    expect(buttons[0]).toHaveAttribute('aria-current', 'true');
    expect(buttons[0]).toHaveFocus();
    fireEvent.click(buttons[1]);
    expect(screen.getAllByRole('region', { name: 'Ticket details' })).toHaveLength(1);
    expect(buttons[0]).not.toHaveAttribute('aria-current');
    expect(buttons[1]).toHaveAttribute('aria-current', 'true');
    expect(screen.getAllByLabelText('Title')).toHaveLength(1);
    expect(screen.getByLabelText('Title')).toHaveFocus();
    expect(screen.getByLabelText('Description')).toHaveValue(tickets[1].description);
    expect(screen.getByLabelText('Status')).toHaveValue('in_progress');
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('saves title, description and canonical status and updates only that ticket', async () => {
    const updatedTicket = { ...tickets[0], title: 'Invoice fixed', description: 'Download restored.', status: 'resolved' };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => tickets })
      .mockResolvedValueOnce({ ok: true, json: async () => updatedTicket });
    vi.stubGlobal('fetch', fetchMock);
    render(<App />);

    fireEvent.click(await screen.findByRole('button', { name: /View details for T-201/ }));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: '  Invoice fixed  ' } });
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Download restored.' } });
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'resolved' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));

    expect(await screen.findByRole('status')).toHaveTextContent('Ticket T-201 saved.');
    expect(fetchMock).toHaveBeenLastCalledWith('http://localhost:8000/api/tickets/T-201', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Invoice fixed', description: 'Download restored.', status: 'resolved' }),
    });
    const queue = screen.getByRole('navigation', { name: 'Current tickets' });
    expect(within(queue).getByText('Invoice fixed')).toBeInTheDocument();
    expect(within(queue).getByText(tickets[1].title)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View details for T-201' })).toHaveFocus();
    const active = screen.getByRole('group', { name: 'Active' });
    expect(within(active).getByText('1')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /View details for T-201/ }));
    expect(screen.getByLabelText('Description')).toHaveValue('Download restored.');
    expect(screen.getByLabelText('Status')).toHaveValue('resolved');
  });

  it.each([422, 500])('preserves the draft after HTTP %s and lets the user retry', async (status) => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => tickets })
      .mockResolvedValueOnce({ ok: false, status })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ ...tickets[0], title: 'Retry title' }) });
    vi.stubGlobal('fetch', fetchMock);
    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: /View details for T-201/ }));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Retry title' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(`HTTP ${status}`);
    expect(screen.getByLabelText('Title')).toHaveValue('Retry title');
    expect(within(screen.getByRole('navigation', { name: 'Current tickets' })).getByText(tickets[0].title)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Ticket T-201 saved.');
  });

  it('blocks blank titles and disables duplicate submissions while saving', async () => {
    let finishSave!: (response: unknown) => void;
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => tickets })
      .mockImplementationOnce(() => new Promise((resolve) => { finishSave = resolve; }));
    vi.stubGlobal('fetch', fetchMock);
    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: /View details for T-201/ }));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: '   ' } });
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Saved once' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(screen.getByRole('button', { name: 'Saving…' })).toBeDisabled();
    expect(screen.getByLabelText('Title')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
    expect(screen.getByRole('button', { name: /View details for T-202/ })).toBeDisabled();
    finishSave({ ok: true, json: async () => ({ ...tickets[0], title: 'Saved once' }) });
    expect(await screen.findByRole('status')).toHaveTextContent('Ticket T-201 saved.');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('requires a known status before saving an unexpected API status', async () => {
    mockTicketResponse([{ ...tickets[0], status: 'blocked' } as unknown as Ticket]);
    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: /View details for T-201/ }));
    expect(within(screen.getByRole('navigation', { name: 'Current tickets' })).getByText('Unknown')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'pending' } });
    expect(screen.getByRole('button', { name: 'Save changes' })).toBeEnabled();
  });

  it('renders the ticket dashboard from the API', async () => {
    mockTicketResponse(tickets);

    render(<App />);

    expect(screen.getByText('Loading tickets...')).toBeInTheDocument();

    await waitFor(() => {
      expect(within(screen.getByRole('navigation', { name: 'Current tickets' })).getByText('Cannot download invoice')).toBeInTheDocument();
    });

    expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toHaveTextContent('Workspace/Tickets');
    expect(screen.getByText('Refund request needs manager approval')).toBeInTheDocument();
    const queue = screen.getByRole('navigation', { name: 'Current tickets' });
    expect(within(queue).getByText('In progress')).toBeInTheDocument();
    expect(within(queue).getByText('In progress')).toHaveClass('status', 'status-in_progress');
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

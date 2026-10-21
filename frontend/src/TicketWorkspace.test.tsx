import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import App from './App';
import type { Ticket } from './types';

const tickets: Ticket[] = [
  { id: 'T-301', title: 'Invoice download', description: 'Download fails.', requester: 'Maya Patel', priority: 'high', status: 'open', created_at: '2026-10-21T09:15:00Z' },
  { id: 'T-302', title: 'Billing email', description: 'Use the new address.', requester: 'Sofia Garcia', priority: 'low', status: 'pending', created_at: '2026-10-20T11:05:00Z' },
];

afterEach(() => vi.unstubAllGlobals());

function loadTickets() {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => tickets });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

function useMobileViewport() {
  vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
    matches: query.includes('max-width'), media: query, onchange: null,
    addEventListener: vi.fn(), removeEventListener: vi.fn(),
    addListener: vi.fn(), removeListener: vi.fn(), dispatchEvent: vi.fn(),
  })));
}

describe('ticket workspace', () => {
  it('shows unsaved changes for a restored draft and clears the indicator after cancel or save', async () => {
    const fetchMock = loadTickets();
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => ({ ...tickets[0], title: 'Saved invoice' }) });
    render(<App />);
    await screen.findByLabelText('Title');
    expect(screen.queryByText('Unsaved changes')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Invoice draft' } });
    fireEvent.click(screen.getByRole('button', { name: 'Next ticket' }));
    expect(screen.queryByText('Unsaved changes')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Previous ticket' }));
    expect(screen.getByText('Unsaved changes')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByText('Unsaved changes')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Saved invoice' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    await screen.findByRole('status');
    expect(screen.queryByText('Unsaved changes')).not.toBeInTheDocument();
  });

  it('points the mobile skip link at the visible pane', async () => {
    useMobileViewport();
    loadTickets();
    render(<App />);
    await screen.findByLabelText('Title');
    expect(screen.getByRole('link', { name: 'Skip to ticket details' })).toHaveAttribute('href', '#ticket-workspace');
    fireEvent.click(screen.getByRole('button', { name: 'Back to tickets' }));
    const queue = screen.getByRole('complementary', { name: 'Current tickets' });
    expect(screen.getByRole('link', { name: 'Skip to tickets' })).toHaveAttribute('href', `#${queue.id}`);
    expect(queue).toHaveAttribute('tabindex', '-1');
    expect(queue).toBeVisible();
  });

  it('focuses mobile ticket navigation on Back so reading does not focus an editable field', async () => {
    useMobileViewport();
    loadTickets();
    render(<App />);
    await screen.findByLabelText('Title');
    fireEvent.click(screen.getByRole('button', { name: 'Next ticket' }));
    expect(screen.getByRole('button', { name: 'Back to tickets' })).toHaveFocus();
    fireEvent.click(screen.getByRole('button', { name: 'Back to tickets' }));
    fireEvent.click(screen.getByRole('button', { name: 'View details for T-301' }));
    expect(screen.getByRole('button', { name: 'Back to tickets' })).toHaveFocus();
  });

  it('moves focus out of the queue when a resize hides it on mobile', async () => {
    let matches = false;
    let onChange: (() => void) | undefined;
    vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
      get matches() { return matches; }, media: query, onchange: null,
      addEventListener: (_type: string, listener: () => void) => { onChange = listener; },
      removeEventListener: vi.fn(),
    })));
    loadTickets();
    render(<App />);
    const queueEntry = await screen.findByRole('button', { name: 'View details for T-301' });
    queueEntry.focus();
    act(() => { matches = true; onChange?.(); });
    expect(screen.queryByRole('navigation', { name: 'Current tickets' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back to tickets' })).toHaveFocus();
  });

  it('keeps focus in Description when a breakpoint change leaves the field visible', async () => {
    let matches = false;
    let onChange: (() => void) | undefined;
    vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
      get matches() { return matches; }, media: query, onchange: null,
      addEventListener: (_type: string, listener: () => void) => { onChange = listener; },
      removeEventListener: vi.fn(),
    })));
    loadTickets();
    render(<App />);
    await screen.findByLabelText('Title');
    fireEvent.click(screen.getByRole('button', { name: 'Next ticket' }));
    screen.getByLabelText('Description').focus();
    act(() => { matches = true; onChange?.(); });
    expect(screen.getByLabelText('Description')).toHaveFocus();
  });

  it('focuses the selected queue ticket when narrowing hides the editor', async () => {
    let matches = true;
    let onChange: (() => void) | undefined;
    vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
      get matches() { return matches; }, media: query, onchange: null,
      addEventListener: (_type: string, listener: () => void) => { onChange = listener; },
      removeEventListener: vi.fn(),
    })));
    loadTickets();
    render(<App />);
    await screen.findByLabelText('Title');
    fireEvent.click(screen.getByRole('button', { name: 'Back to tickets' }));
    act(() => { matches = false; onChange?.(); });
    screen.getByLabelText('Description').focus();
    act(() => { matches = true; onChange?.(); });
    expect(screen.queryByRole('form', { name: 'Edit ticket T-301' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View details for T-301' })).toHaveFocus();
  });

  it('shows one mobile pane and reopens the selected ticket without losing its draft', async () => {
    useMobileViewport();
    loadTickets();
    render(<App />);
    fireEvent.change(await screen.findByLabelText('Title'), { target: { value: 'Mobile invoice draft' } });
    expect(screen.queryByRole('navigation', { name: 'Current tickets' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Back to tickets' }));
    expect(screen.queryByRole('form', { name: 'Edit ticket T-301' })).not.toBeInTheDocument();
    const selected = screen.getByRole('button', { name: 'View details for T-301' });
    expect(selected).toHaveFocus();
    fireEvent.click(selected);
    expect(screen.getByRole('textbox', { name: 'Title' })).toHaveValue('Mobile invoice draft');
    expect(screen.queryByRole('navigation', { name: 'Current tickets' })).not.toBeInTheDocument();
  });

  it('keeps mobile save and cancel focus visible and locks Back during a pending save', async () => {
    useMobileViewport();
    const fetchMock = loadTickets();
    let finishSave!: (response: unknown) => void;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { finishSave = resolve; }));
    render(<App />);
    fireEvent.change(await screen.findByLabelText('Title'), { target: { value: 'Cancelled draft' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus();
    expect(screen.getByLabelText('Title')).toHaveValue(tickets[0].title);
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Saved mobile draft' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(screen.getByRole('button', { name: 'Back to tickets' })).toBeDisabled();
    finishSave({ ok: true, json: async () => ({ ...tickets[0], title: 'Saved mobile draft' }) });
    await screen.findByRole('status');
    expect(screen.getByRole('button', { name: 'Save changes' })).toHaveFocus();
    expect(screen.getByLabelText('Title')).toHaveValue('Saved mobile draft');
    expect(screen.queryByRole('navigation', { name: 'Current tickets' })).not.toBeInTheDocument();
  });

  it('preserves independent unsaved drafts while switching tickets and clears only the cancelled draft', async () => {
    const fetchMock = loadTickets();
    render(<App />);
    fireEvent.change(await screen.findByLabelText('Title'), { target: { value: 'Invoice draft' } });
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Draft investigation notes' } });
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'pending' } });
    fireEvent.click(screen.getByRole('button', { name: 'View details for T-302' }));
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Billing draft' } });
    fireEvent.click(screen.getByRole('button', { name: 'View details for T-301' }));
    expect(screen.getByLabelText('Title')).toHaveValue('Invoice draft');
    expect(screen.getByLabelText('Description')).toHaveValue('Draft investigation notes');
    expect(screen.getByLabelText('Status')).toHaveValue('pending');
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByLabelText('Title')).toHaveValue(tickets[0].title);
    fireEvent.click(screen.getByRole('button', { name: 'View details for T-302' }));
    expect(screen.getByLabelText('Title')).toHaveValue('Billing draft');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('describes queue buttons with the ticket title, requester, status and priority', async () => {
    loadTickets();
    render(<App />);
    const entry = await screen.findByRole('button', { name: 'View details for T-301' });
    expect(entry).toHaveAccessibleDescription('Invoice download Maya Patel Open high');
  });

  it('clears a previous success message when the next save fails', async () => {
    const fetchMock = loadTickets();
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => tickets[0] });
    fetchMock.mockResolvedValueOnce({ ok: false, status: 500 });
    render(<App />);
    await screen.findByLabelText('Title');
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Ticket T-301 saved.');
    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Second draft' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('HTTP 500');
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Title')).toHaveValue('Second draft');
  });

  it('selects the first ticket and navigates a single editor with disabled end controls', async () => {
    loadTickets();
    render(<App />);

    expect(await screen.findByLabelText('Title')).toHaveValue('Invoice download');
    expect(screen.getByRole('button', { name: 'View details for T-301' })).toHaveAttribute('aria-current', 'true');
    expect(screen.getByRole('button', { name: 'Previous ticket' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Next ticket' }));
    expect(screen.getByLabelText('Title')).toHaveValue('Billing email');
    expect(screen.getAllByRole('region', { name: 'Ticket details' })).toHaveLength(1);
    expect(screen.getByRole('button', { name: 'Next ticket' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'View details for T-302' })).toHaveAttribute('aria-current', 'true');
    expect(screen.getByLabelText('Title')).toHaveFocus();
    fireEvent.click(screen.getByRole('button', { name: 'Previous ticket' }));
    expect(screen.getByLabelText('Title')).toHaveValue('Invoice download');
  });

  it('cancels draft fields without closing the selected ticket or sending a request', async () => {
    const fetchMock = loadTickets();
    render(<App />);
    fireEvent.change(await screen.findByLabelText('Title'), { target: { value: 'Unsaved title' } });
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Unsaved details' } });
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'resolved' } });
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(screen.getByLabelText('Title')).toHaveValue('Invoice download');
    expect(screen.getByLabelText('Description')).toHaveValue('Download fails.');
    expect(screen.getByLabelText('Status')).toHaveValue('open');
    expect(screen.getByRole('button', { name: 'View details for T-301' })).toHaveFocus();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('keeps the selected ticket open after saving and updates its queue entry only', async () => {
    const fetchMock = loadTickets();
    fetchMock.mockResolvedValueOnce({ ok: true, json: async () => ({ ...tickets[0], title: 'Invoice restored', description: 'Working now.', status: 'pending' }) });
    render(<App />);
    fireEvent.change(await screen.findByLabelText('Title'), { target: { value: ' Invoice restored ' } });
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Working now.' } });
    fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'pending' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Ticket T-301 saved.');
    expect(fetchMock).toHaveBeenLastCalledWith('http://localhost:8000/api/tickets/T-301', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: 'Invoice restored', description: 'Working now.', status: 'pending' }),
    });
    expect(screen.getByLabelText('Title')).toHaveValue('Invoice restored');
    const queue = screen.getByRole('navigation', { name: 'Current tickets' });
    expect(within(queue).getByText('Invoice restored')).toBeInTheDocument();
    expect(within(queue).getByText('Billing email')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View details for T-301' })).toHaveAttribute('aria-current', 'true');
  });

  it('blocks navigation and duplicate submissions while a save is pending', async () => {
    const fetchMock = loadTickets();
    let finishSave!: (response: unknown) => void;
    fetchMock.mockImplementationOnce(() => new Promise((resolve) => { finishSave = resolve; }));
    render(<App />);
    await screen.findByLabelText('Title');
    fireEvent.click(screen.getByRole('button', { name: 'Save changes' }));
    expect(screen.getByRole('button', { name: 'Next ticket' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'View details for T-302' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
    fireEvent.submit(screen.getByRole('form', { name: 'Edit ticket T-301' }));
    expect(fetchMock).toHaveBeenCalledTimes(2);
    finishSave({ ok: true, json: async () => tickets[0] });
    await screen.findByRole('status');
    expect(screen.getByRole('button', { name: 'Next ticket' })).toBeEnabled();
  });

  it('announces transport failures without leaving stale editable controls', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network unavailable')));
    render(<App />);
    expect(screen.getByText('Loading tickets...')).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toHaveTextContent('Network unavailable');
    expect(screen.queryByLabelText('Title')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Save changes' })).not.toBeInTheDocument();
  });
});

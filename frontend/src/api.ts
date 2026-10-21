import type { Ticket, TicketUpdate } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export async function fetchTickets(): Promise<Ticket[]> {
  const response = await fetch(`${API_BASE_URL}/api/tickets`);

  if (!response.ok) {
    return [];
  }

  return response.json();
}

export async function updateTicket(id: string, changes: TicketUpdate): Promise<Ticket> {
  const response = await fetch(`${API_BASE_URL}/api/tickets/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  });

  if (!response.ok) {
    throw new Error(`Could not save ticket (HTTP ${response.status}). Please try again.`);
  }

  return response.json();
}

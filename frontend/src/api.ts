import type { Ticket } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export async function fetchTickets(): Promise<Ticket[]> {
  const response = await fetch(`${API_BASE_URL}/api/tickets`);

  if (!response.ok) {
    return [];
  }

  return response.json();
}

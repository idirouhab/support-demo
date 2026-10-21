export const TICKET_STATUSES = ['open', 'pending', 'in_progress', 'resolved'] as const;
export type TicketStatus = (typeof TICKET_STATUSES)[number];
export type TicketPriority = 'low' | 'medium' | 'high';

export interface Ticket {
  id: string;
  title: string;
  description: string;
  requester: string;
  priority: TicketPriority;
  status: TicketStatus;
  created_at: string;
}

export type TicketUpdate = Pick<Ticket, 'title' | 'description' | 'status'>;

export type TicketStatus = 'open' | 'pending' | 'in-progress' | 'resolved';
export type TicketPriority = 'low' | 'medium' | 'high';

export interface Ticket {
  id: string;
  title: string;
  requester: string;
  priority: TicketPriority;
  status: TicketStatus;
  created_at: string;
}

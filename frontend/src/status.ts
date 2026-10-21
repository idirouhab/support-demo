import { TICKET_STATUSES, type TicketStatus } from './types';

const STATUS_LABELS: Record<string, string> = {
  open: 'Open',
  pending: 'Pending',
  'in-progress': 'In progress',
  resolved: 'Resolved',
};

export function getStatusLabel(status: string): string {
  return STATUS_LABELS[status] ?? 'Unknown';
}

export function getStatusClassName(status: string): string {
  return `status status-${status}`;
}

export function isTicketStatus(status: string): status is TicketStatus {
  return TICKET_STATUSES.some((value) => value === status);
}

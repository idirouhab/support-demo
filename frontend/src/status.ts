import type { TicketStatus } from './types';

const STATUS_LABELS: Record<TicketStatus, string> = {
  open: 'Open',
  pending: 'Pending',
  'in-progress': 'In progress',
  resolved: 'Resolved',
};

export function getStatusLabel(status: string): string {
  return STATUS_LABELS[status as TicketStatus] ?? 'Unknown';
}

export function getStatusClassName(status: string): string {
  return `status status-${status}`;
}

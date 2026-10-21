import { ChartBar, CheckCircle, Circle, CircleHalf, Clock, Flag, Question } from '@phosphor-icons/react';
import type { TicketPriority } from './types';

export function StatusIcon({ status }: { status: string }) {
  const Icon = status === 'open' ? Circle : status === 'in_progress' ? CircleHalf : status === 'pending' ? Clock : status === 'resolved' ? CheckCircle : Question;
  return <Icon size={24} weight={status === 'in_progress' ? 'fill' : 'regular'} aria-hidden="true" />;
}

export function PriorityIcon({ priority }: { priority: TicketPriority }) {
  const Icon = priority === 'high' ? Flag : ChartBar;
  return <Icon className={`priority-icon priority-icon-${priority}`} size={23} weight="fill" aria-hidden="true" />;
}

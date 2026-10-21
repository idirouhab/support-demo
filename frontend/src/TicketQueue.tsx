import { getStatusClassName, getStatusLabel } from './status';
import { PriorityIcon, StatusIcon } from './TicketIndicators';
import type { Ticket } from './types';

interface TicketQueueProps {
  tickets: Ticket[];
  selectedTicketId: string | null;
  isSaving: boolean;
  onSelect: (id: string) => void;
  onButtonRef: (id: string, button: HTMLButtonElement | null) => void;
}

export default function TicketQueue({ tickets, selectedTicketId, isSaving, onSelect, onButtonRef }: TicketQueueProps) {
  if (!tickets.length) return <p className="queue-state">No tickets to display.</p>;

  return (
    <nav className="ticket-queue" aria-labelledby="tickets-heading">
      <ul>
        {tickets.map((ticket) => (
          <li key={ticket.id}>
            <button type="button" className="queue-ticket" ref={(button) => onButtonRef(ticket.id, button)}
              aria-label={`View details for ${ticket.id}`} aria-current={selectedTicketId === ticket.id ? 'true' : undefined}
              aria-describedby={`queue-title-${ticket.id} queue-requester-${ticket.id} queue-status-${ticket.id} queue-priority-${ticket.id}`}
              aria-controls="ticket-details" disabled={isSaving} onClick={() => onSelect(ticket.id)}>
              <span className="ticket-id">{ticket.id}</span>
              <span className="queue-ticket-title" id={`queue-title-${ticket.id}`}>{ticket.title}</span>
              <span className="ticket-requester" id={`queue-requester-${ticket.id}`}>{ticket.requester}</span>
              <span className="ticket-indicators">
                <span className={getStatusClassName(ticket.status)} id={`queue-status-${ticket.id}`}><StatusIcon status={ticket.status} />{getStatusLabel(ticket.status)}</span>
                <span className={`priority priority-${ticket.priority}`} id={`queue-priority-${ticket.id}`}><PriorityIcon priority={ticket.priority} />{ticket.priority}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}

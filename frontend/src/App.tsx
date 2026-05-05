import { useEffect, useMemo, useState } from 'react';

import { fetchTickets } from './api';
import { getStatusClassName, getStatusLabel } from './status';
import type { Ticket } from './types';

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value));
}

function summarizeTickets(tickets: Ticket[]) {
  return {
    total: tickets.length,
    highPriority: tickets.filter((ticket) => ticket.priority !== 'low').length,
    active: tickets.length,
  };
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;

    fetchTickets()
      .then((nextTickets) => {
        if (isMounted) {
          setTickets(nextTickets);
          setError(null);
        }
      })
      .catch((nextError: Error) => {
        if (isMounted) {
          setError(nextError.message);
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const summary = useMemo(() => summarizeTickets(tickets), [tickets]);

  return (
    <main className="page-shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Support Operations</p>
          <h1>Ticket dashboard</h1>
          <p className="hero-copy">
            A compact support workflow for tracing API contracts, frontend rendering, tests, and CI checks.
          </p>
        </div>
        <div className="summary-grid" aria-label="Ticket summary">
          <div>
            <span>{summary.total}</span>
            <p>Total tickets</p>
          </div>
          <div>
            <span>{summary.active}</span>
            <p>Active</p>
          </div>
          <div>
            <span>{summary.highPriority}</span>
            <p>High priority</p>
          </div>
        </div>
      </section>

      <section className="panel" aria-labelledby="tickets-heading">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Queue</p>
            <h2 id="tickets-heading">Current tickets</h2>
          </div>
          <span className="pipeline-pill">GitLab CI ready</span>
        </div>

        {isLoading && <p className="state-message">Loading tickets...</p>}
        {error && <p className="state-message error">Could not load tickets: {error}</p>}

        {!isLoading && !error && (
          <div className="ticket-list">
            {tickets.map((ticket) => (
              <article className="ticket-card" key={ticket.id}>
                <div>
                  <div className="ticket-meta">
                    <span>{ticket.id}</span>
                    <span>{formatDate(ticket.created_at)}</span>
                  </div>
                  <h3>{ticket.title}</h3>
                  <p>Requester: {ticket.requester}</p>
                </div>
                <div className="ticket-actions">
                  <span className={getStatusClassName(ticket.status)}>{getStatusLabel(ticket.status)}</span>
                  <span className={`priority priority-${ticket.priority}`}>{ticket.priority}</span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

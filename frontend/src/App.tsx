import { CaretRight, Circle } from '@phosphor-icons/react';
import { useEffect, useMemo, useRef, useState } from 'react';

import { fetchTickets } from './api';
import TicketDetails, { type EditorFocus, type TicketDraft } from './TicketDetails';
import TicketQueue from './TicketQueue';
import type { Ticket } from './types';

const MOBILE_QUERY = '(max-width: 760px)';

function isMobileViewport() {
  return typeof window.matchMedia === 'function' && window.matchMedia(MOBILE_QUERY).matches;
}

function draftFromTicket(ticket: Ticket): TicketDraft {
  return { title: ticket.title, description: ticket.description ?? '', status: ticket.status };
}

function summarizeTickets(tickets: Ticket[]) {
  // Original demo predicates are intentionally restored for the bug exercises.
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
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);
  const [editorRevision, setEditorRevision] = useState(0);
  const [editorFocus, setEditorFocus] = useState<EditorFocus>(null);
  const [drafts, setDrafts] = useState(() => new Map<string, TicketDraft>());
  const [isMobile, setIsMobile] = useState(isMobileViewport);
  const [mobileView, setMobileView] = useState<'queue' | 'details'>('details');
  const queuePane = useRef<HTMLElement>(null);
  const queueButtons = useRef(new Map<string, HTMLButtonElement>());
  const focusAfterSave = useRef<string | null>(null);

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const media = window.matchMedia(MOBILE_QUERY);
    const update = () => {
      const focused = document.activeElement;
      if (media.matches && mobileView === 'details' && queuePane.current?.contains(focused)) {
        setEditorFocus({ target: 'back' });
      } else if (!media.matches && focused?.classList.contains('mobile-back-button')) {
        setEditorFocus({ target: 'title' });
      } else if (!media.matches && focused?.classList.contains('mobile-queue-return') && selectedTicketId) {
        queueButtons.current.get(selectedTicketId)?.focus();
      }
      setIsMobile(media.matches);
    };
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [mobileView, selectedTicketId]);

  useEffect(() => {
    if (!isSaving && savedMessage && focusAfterSave.current) {
      if (!isMobile) queueButtons.current.get(focusAfterSave.current)?.focus();
      focusAfterSave.current = null;
    }
  }, [isSaving, savedMessage, isMobile]);

  useEffect(() => {
    if (isMobile && mobileView === 'queue' && selectedTicketId) {
      queueButtons.current.get(selectedTicketId)?.focus();
    }
  }, [isMobile, mobileView, selectedTicketId]);

  useEffect(() => {
    let isMounted = true;
    fetchTickets()
      .then((nextTickets) => {
        if (!isMounted) return;
        setTickets(nextTickets);
        setSelectedTicketId(nextTickets[0]?.id ?? null);
        setError(null);
      })
      .catch((nextError: Error) => {
        if (isMounted) setError(nextError.message);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => { isMounted = false; };
  }, []);

  const summary = useMemo(() => summarizeTickets(tickets), [tickets]);
  const selectedIndex = tickets.findIndex((ticket) => ticket.id === selectedTicketId);
  const selectedTicket = tickets[selectedIndex];
  const showMobileQueue = isMobile && (mobileView === 'queue' || !selectedTicket);

  function selectTicket(id: string) {
    if (isSaving) return;
    setMobileView('details');
    setEditorFocus({ target: isMobileViewport() ? 'back' : 'title' });
    if (id === selectedTicketId) return;
    setSavedMessage(null);
    setSelectedTicketId(id);
  }

  function openQueue() {
    if (isSaving) return;
    setEditorFocus(null);
    setMobileView('queue');
  }

  function updateDraft(ticket: Ticket, patch: Partial<TicketDraft>) {
    setDrafts((current) => {
      const next = new Map(current);
      next.set(ticket.id, { ...(current.get(ticket.id) ?? draftFromTicket(ticket)), ...patch });
      return next;
    });
  }

  function clearDraft(id: string) {
    setDrafts((current) => {
      const next = new Map(current);
      next.delete(id);
      return next;
    });
  }

  function cancelEdits() {
    if (!selectedTicketId) return;
    clearDraft(selectedTicketId);
    setEditorRevision((revision) => revision + 1);
    setEditorFocus(isMobileViewport() ? { target: 'cancel' } : null);
    setSavedMessage(null);
    if (!isMobileViewport()) queueButtons.current.get(selectedTicketId)?.focus();
  }

  function handleSaved(updated: Ticket) {
    setTickets((current) => current.map((ticket) => ticket.id === updated.id ? updated : ticket));
    clearDraft(updated.id);
    setEditorFocus(isMobileViewport() ? { target: 'save' } : null);
    setEditorRevision((revision) => revision + 1);
    focusAfterSave.current = updated.id;
    setSavedMessage(`Ticket ${updated.id} saved.`);
  }

  function handleSavingChange(saving: boolean) {
    if (saving) setSavedMessage(null);
    setIsSaving(saving);
  }

  return (
    <div className="workspace-shell">
      <a className="skip-link" href={showMobileQueue ? '#ticket-queue' : '#ticket-workspace'}>{showMobileQueue ? 'Skip to tickets' : 'Skip to ticket details'}</a>
      <header className="workspace-header">
        <div className="header-main">
          <nav className="breadcrumb" aria-label="Breadcrumb">
            <span>Workspace</span><span className="breadcrumb-divider" aria-hidden="true">/</span><span aria-current="page">Tickets</span>
          </nav>
          <div className="ticket-summary" aria-label="Ticket summary">
            <Circle className="summary-indicator" weight="fill" size={12} aria-hidden="true" />
            <div className="summary-item" role="group" aria-label="Total tickets"><span>{summary.total}</span><span>total</span></div>
            <span aria-hidden="true">·</span>
            <div className="summary-item" role="group" aria-label="Active"><span>{summary.active}</span><span>active</span></div>
            <span aria-hidden="true">·</span>
            <div className="summary-item" role="group" aria-label="High priority"><span>{summary.highPriority}</span><span>high priority</span></div>
          </div>
        </div>
      </header>

      <aside ref={queuePane} className="queue-pane" id="ticket-queue" tabIndex={-1} aria-labelledby="tickets-heading" hidden={isMobile && !showMobileQueue}>
        <div className="queue-header">
          <div className="queue-heading-row"><h1 id="tickets-heading">Current tickets</h1><span className="queue-count">{String(tickets.length).padStart(2, '0')}</span></div>
          {isMobile && selectedTicket && <button className="mobile-queue-return" type="button" disabled={isSaving} onClick={() => selectTicket(selectedTicket.id)} aria-label="Return to selected ticket">Return to ticket<CaretRight size={16} aria-hidden="true" /></button>}
        </div>
        {isLoading && <p className="queue-state">Loading tickets...</p>}
        {error && <p className="queue-state queue-error" role="alert">Could not load tickets: {error}</p>}
        {!isLoading && !error && (
          <TicketQueue tickets={tickets} selectedTicketId={selectedTicketId} isSaving={isSaving} onSelect={selectTicket}
            onButtonRef={(id, button) => {
              if (button) queueButtons.current.set(id, button);
              else queueButtons.current.delete(id);
            }}
          />
        )}
      </aside>

      <main className="ticket-workspace" id="ticket-workspace" tabIndex={-1} hidden={showMobileQueue}>
        {selectedTicket ? (
          <TicketDetails key={`${selectedTicket.id}-${editorRevision}`} ticket={selectedTicket}
            draft={drafts.get(selectedTicket.id) ?? draftFromTicket(selectedTicket)}
            onDraftChange={(patch) => updateDraft(selectedTicket, patch)}
            isSaving={isSaving} focusTarget={editorFocus} savedMessage={savedMessage}
            hasPrevious={selectedIndex > 0} hasNext={selectedIndex < tickets.length - 1}
            onPrevious={() => selectTicket(tickets[selectedIndex - 1].id)}
            onNext={() => selectTicket(tickets[selectedIndex + 1].id)}
            onBackToTickets={isMobile ? openQueue : undefined}
            onSavingChange={handleSavingChange} onSaved={handleSaved} onCancel={cancelEdits}
          />
        ) : (
          <div className="workspace-empty">
            <p className="eyebrow">Ticket workspace</p>
            <h2>{isLoading ? 'Getting your queue ready' : error ? 'Your queue is unavailable' : 'Your queue is clear'}</h2>
            <p>{isLoading ? 'Tickets will appear here when they have loaded.' : error ? 'Reload the page to try again.' : 'There are no tickets to review right now.'}</p>
          </div>
        )}
      </main>
    </div>
  );
}

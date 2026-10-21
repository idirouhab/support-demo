import { CaretDown, CaretLeft, CaretRight, PencilSimple } from '@phosphor-icons/react';
import { useLayoutEffect, useRef, useState, type FormEvent } from 'react';

import { updateTicket } from './api';
import { getStatusLabel, isTicketStatus } from './status';
import { PriorityIcon, StatusIcon } from './TicketIndicators';
import { TICKET_STATUSES, type Ticket } from './types';

export interface TicketDraft {
  title: string;
  description: string;
  status: string;
}

export type EditorFocus = { target: 'title' | 'save' | 'cancel' | 'back' } | null;

interface TicketDetailsProps {
  ticket: Ticket;
  draft: TicketDraft;
  onDraftChange: (patch: Partial<TicketDraft>) => void;
  isSaving: boolean;
  focusTarget: EditorFocus;
  savedMessage: string | null;
  hasPrevious: boolean;
  hasNext: boolean;
  onPrevious: () => void;
  onNext: () => void;
  onBackToTickets?: () => void;
  onSavingChange: (value: boolean) => void;
  onSaved: (ticket: Ticket) => void;
  onCancel: () => void;
}

export default function TicketDetails({ ticket, draft, onDraftChange, isSaving, focusTarget, savedMessage, hasPrevious, hasNext, onPrevious, onNext, onBackToTickets, onSavingChange, onSaved, onCancel }: TicketDetailsProps) {
  const { title, description, status } = draft;
  const [error, setError] = useState<string | null>(null);
  const titleInput = useRef<HTMLTextAreaElement>(null);
  const saveButton = useRef<HTMLButtonElement>(null);
  const cancelButton = useRef<HTMLButtonElement>(null);
  const backButton = useRef<HTMLButtonElement>(null);
  const saving = useRef(false);
  const hasUnsavedChanges = title !== ticket.title || description !== (ticket.description ?? '') || status !== ticket.status;

  useLayoutEffect(() => {
    if (focusTarget?.target === 'title') titleInput.current?.focus();
    if (focusTarget?.target === 'save') saveButton.current?.focus();
    if (focusTarget?.target === 'cancel') cancelButton.current?.focus();
    if (focusTarget?.target === 'back') backButton.current?.focus();
  }, [focusTarget]);

  useLayoutEffect(() => {
    const input = titleInput.current;
    if (!input) return;
    const resize = () => {
      input.style.height = '0px';
      input.style.height = `${input.scrollHeight}px`;
    };
    resize();
    if (typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(resize);
    observer.observe(input);
    return () => observer.disconnect();
  }, [title]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving.current || !title.trim() || !isTicketStatus(status)) return;
    saving.current = true;
    onSavingChange(true);
    setError(null);
    try {
      const updated = await updateTicket(ticket.id, { title: title.trim(), description, status });
      onSaved(updated);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save ticket. Please try again.');
    } finally {
      saving.current = false;
      onSavingChange(false);
    }
  }

  return (
    <section className="ticket-details" id="ticket-details" aria-labelledby="details-heading">
      <div className="details-header">
        {onBackToTickets && <button ref={backButton} className="mobile-back-button" type="button" disabled={isSaving} onClick={onBackToTickets} aria-label="Back to tickets"><CaretLeft size={16} aria-hidden="true" />Tickets</button>}
        <div className="details-heading"><span className="ticket-id">{ticket.id}</span><h2 id="details-heading">Ticket details</h2></div>
        <nav className="ticket-navigation" aria-label="Ticket navigation">
          <button type="button" aria-label="Previous ticket" disabled={isSaving || !hasPrevious} onClick={onPrevious}><CaretLeft size={24} weight="light" aria-hidden="true" /></button>
          <button type="button" aria-label="Next ticket" disabled={isSaving || !hasNext} onClick={onNext}><CaretRight size={24} weight="light" aria-hidden="true" /></button>
        </nav>
      </div>
      <form onSubmit={handleSubmit} aria-label={`Edit ticket ${ticket.id}`} aria-busy={isSaving}>
        <fieldset disabled={isSaving}>
          <div className="title-field">
            <label className="field-label" htmlFor={`title-${ticket.id}`}>Title</label>
            <div className="title-input-wrap">
              <textarea id={`title-${ticket.id}`} ref={titleInput} className="title-input" value={title}
                onChange={(event) => onDraftChange({ title: event.target.value.replace(/\n/g, ' ') })} required maxLength={200} rows={1} />
              <PencilSimple className="edit-indicator" size={25} weight="light" aria-hidden="true" />
            </div>
          </div>
          <div className="ticket-properties">
            <div className="property status-property">
              <label className="field-label" htmlFor={`status-${ticket.id}`}>Status</label>
              <div className="status-select-wrap">
                <StatusIcon status={status} />
                <select id={`status-${ticket.id}`} value={status} onChange={(event) => onDraftChange({ status: event.target.value })}>
                  {!isTicketStatus(status) && <option value={status} disabled>Unknown status — choose a status</option>}
                  {TICKET_STATUSES.map((value) => <option key={value} value={value}>{getStatusLabel(value)}</option>)}
                </select>
                <CaretDown className="select-caret" size={17} weight="light" aria-hidden="true" />
              </div>
            </div>
            <dl className="ticket-metadata">
              <div><dt>Priority</dt><dd className="property-value"><PriorityIcon priority={ticket.priority} /><span className="priority-label">{ticket.priority}</span></dd></div>
              <div><dt>Requester</dt><dd className="property-value">{ticket.requester}</dd></div>
              <div><dt>Created</dt><dd className="property-value"><time dateTime={ticket.created_at}>{new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(ticket.created_at))}</time></dd></div>
            </dl>
          </div>
          <div className="description-field">
            <label className="field-label" htmlFor={`description-${ticket.id}`}>Description</label>
            <textarea id={`description-${ticket.id}`} value={description} onChange={(event) => onDraftChange({ description: event.target.value })}
              rows={4} maxLength={10000} placeholder="Add details about this ticket" />
          </div>
          {error && <p className="save-error" role="alert">{error}</p>}
          {savedMessage && <p className="save-feedback" role="status">{savedMessage}</p>}
          <div className="form-actions">
            <button ref={saveButton} className="button button-primary" type="submit" disabled={isSaving || !title.trim() || !isTicketStatus(status)}>{isSaving ? 'Saving…' : 'Save changes'}</button>
            <button ref={cancelButton} className="button button-quiet" type="button" onClick={onCancel}>Cancel</button>
            {hasUnsavedChanges && <span className="draft-indicator">Unsaved changes</span>}
          </div>
        </fieldset>
      </form>
    </section>
  );
}

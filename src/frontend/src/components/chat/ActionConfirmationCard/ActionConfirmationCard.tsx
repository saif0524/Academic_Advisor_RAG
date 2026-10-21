import Badge from '../../shared/Badge/Badge';
import Button from '../../shared/Button/Button';
import type { ProposedAction } from '../../../api/types';
import './ActionConfirmationCard.css';

export type ProposalStatus = 'pending' | 'confirmed' | 'declined';

const STATUS_LABELS: Record<Exclude<ProposalStatus, 'pending'>, string> = {
  confirmed: 'Confirmed',
  declined: 'Cancelled',
};

interface ActionConfirmationCardProps {
  /** What the advisor proposes to do. */
  action: ProposedAction;
  status?: ProposalStatus;
  onConfirm?: () => void;
  onDecline?: () => void;
  busy?: boolean;
}

/**
 * Explicit confirmation gate inside the chat (FC22/FC23): the advisor's
 * proposed action on the student's behalf renders here and only fires after
 * the user presses Confirm — Declined never executes. The deterministic
 * backend owns the actual effect; this surface is the UI half of the gate.
 */
export default function ActionConfirmationCard({
  action,
  status = 'pending',
  onConfirm,
  onDecline,
  busy = false,
}: ActionConfirmationCardProps) {
  const decided = status === 'confirmed' || status === 'declined';
  return (
    <div
      className={`action-confirmation-card action-confirmation-card--${status}`}
      role="group"
      aria-label="Confirm advisor action"
    >
      <Badge variant={status === 'confirmed' ? 'success' : status === 'declined' ? 'neutral' : 'warning'} dot>
        {decided ? STATUS_LABELS[status] : 'Needs your approval'}
      </Badge>
      <p className="action-confirmation-card-summary">{action.summary}</p>
      {action.detail ? <p className="action-confirmation-card-detail">{action.detail}</p> : null}
      {!decided ? (
        <div className="action-confirmation-card-actions">
          <Button variant="secondary" onClick={onDecline} disabled={busy}>
            No thanks
          </Button>
          <Button variant="primary" onClick={onConfirm} disabled={busy}>
            {busy ? 'Applying…' : 'Confirm'}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
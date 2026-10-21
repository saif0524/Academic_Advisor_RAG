import Badge from '../../shared/Badge/Badge';
import Icon from '../../shared/Icon/Icon';
import './PlanCheckBanner.css';

interface PlanCheckBannerProps {
  status: 'ok' | 'issues';
  issues?: string[];
  okMessage?: string;
}

/**
 * Engine-verdict banner for the edited plan/semester (wireframe 02's green
 * "Prerequisites and credit hours check out" and wireframe 03's issue list;
 * FC29/FC31/FC32 display surfaces). Verdicts arrive from the api layer —
 * this component never computes constraints.
 */
export default function PlanCheckBanner({
  status = 'ok',
  issues = [],
  okMessage = 'Prerequisites and credit hours check out',
}: PlanCheckBannerProps) {
  if (status !== 'issues') {
    return (
      <p className="plan-check-banner plan-check-banner--ok" role="status">
        <Icon name="checkCircle" size={16} /> {okMessage}
      </p>
    );
  }
  return (
    <div className="plan-check-banner plan-check-banner--issues" role="alert">
      <Icon name="warning" size={16} />
      <div className="plan-check-banner-text">
        <span className="plan-check-banner-title">
          <Badge variant="warning">
            {issues.length} issue{issues.length === 1 ? '' : 's'} with this draft
          </Badge>
        </span>
        <ul className="plan-check-banner-list">
          {issues.map((issue) => (
            <li key={issue}>{issue}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
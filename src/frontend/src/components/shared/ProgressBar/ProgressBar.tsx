import './ProgressBar.css';

export interface ProgressSegment {
  key: string;
  value: number;
  /** CSS modifier: 'completed' | 'in-progress' | 'planned' | 'success' | 'primary' */
  variant: string;
  label?: string;
}

interface ProgressBarProps {
  /** Single-fill mode (per-semester cap — FC32). */
  value?: number;
  max?: number;
  /** Stacked mode (degree progress legend — FC19). */
  segments?: ProgressSegment[];
  showLegend?: boolean;
  /** Accessible description, e.g. 'Degree progress'. */
  label?: string;
}

/**
 * Shared primitive: credit-progress bar (FC19 degree progress, FC32
 * per-semester cap display). Single fill for `value/max`, stacked segments
 * when `segments` is given. Percentages clamped 0–100.
 */
export default function ProgressBar({ value = 0, max = 100, segments, showLegend = false, label }: ProgressBarProps) {
  const isStacked = Array.isArray(segments) && segments.length > 0;

  const fills = isStacked
    ? (segments ?? []).map((segment) => {
        const total = (segments ?? []).reduce((sum, seg) => sum + (seg.value ?? 0), 0);
        return {
          ...segment,
          pct: total > 0 ? Math.min(100, Math.max(0, ((segment.value ?? 0) / total) * 100)) : 0,
        };
      })
    : [
        {
          key: 'single',
          value,
          variant: 'primary',
          pct: max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0,
        },
      ];

  return (
    <div className="progress-bar" role="img" aria-label={label ?? 'Progress'}>
      <div className="progress-bar-track">
        {fills.map((fill) => (
          <div
            key={fill.key}
            className={`progress-bar-fill progress-bar-fill--${fill.variant}`}
            style={{ width: `${fill.pct}%` }}
          />
        ))}
      </div>
      {isStacked && showLegend ? (
        <ul className="progress-bar-legend">
          {(segments ?? []).map((segment) => (
            <li
              key={segment.key}
              className={`progress-bar-legend-item progress-bar-legend-item--${segment.variant}`}
            >
              <span className="progress-bar-legend-dot" aria-hidden="true" />
              {segment.label ?? 'segment'} {segment.value}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
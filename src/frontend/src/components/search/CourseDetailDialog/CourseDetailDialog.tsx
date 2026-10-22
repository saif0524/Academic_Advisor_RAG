import { useEffect, useRef } from 'react';
import Badge from '../../shared/Badge/Badge';
import Button from '../../shared/Button/Button';
import Icon from '../../shared/Icon/Icon';
import { toTitleCase } from '../../shared/textCase';
import type { CourseDetail as CourseDetailData } from '../../../api/types';
import './CourseDetailDialog.css';

const PREREQ_LABELS: Record<CourseDetailData['prereqs'][number]['status'], { label: string; variant: 'success' | 'warning' | 'danger' }> = {
  met: { label: 'Met', variant: 'success' },
  'in-progress': { label: 'In progress', variant: 'warning' },
  missing: { label: 'Not met', variant: 'danger' },
};

interface CourseDetailDialogProps {
  open: boolean;
  detail: CourseDetailData | null;
  onClose?: () => void;
  loading?: boolean;
  error?: string | null;
}

/**
 * Minimal course-detail dialog (wireframe 04 "Details"; FC11 fields +
 * FC12 section/meeting line). Prereq statuses come from the
 * student's class records; when no prereq records exist the dialog says so explicitly
 * instead of inventing requirements (grounded-UI rule).
 */
export default function CourseDetailDialog({ open, detail, onClose, loading = false, error = null }: CourseDetailDialogProps) {
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return undefined;
    // Focus the close action when the dialog opens; Escape closes.
    dialogRef.current?.querySelector<HTMLButtonElement>('[aria-label="Close course details"]')?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="course-detail-dialog-overlay" onMouseDown={onClose}>
      <div
        ref={dialogRef}
        className="course-detail-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={detail ? `Course details: ${detail.title}` : 'Course details'}
        onMouseDown={(event) => event.stopPropagation()}
      >
        {loading ? (
          <p className="course-detail-dialog-state">Loading course details…</p>
        ) : error ? (
          <p className="course-detail-dialog-state course-detail-dialog-state--error">
            Could not load details: {error}
          </p>
        ) : !detail ? (
          <p className="course-detail-dialog-state">Course details are unavailable.</p>
        ) : (
          <>
            <header className="course-detail-dialog-header">
              <h2 className="course-detail-dialog-title">
                <span className="course-detail-dialog-code">{detail.id}</span> {toTitleCase(detail.title)}
              </h2>
              <Button
                variant="ghost"
                iconOnly
                onClick={onClose}
                aria-label="Close course details"
              >
                <Icon name="close" size={14} />
              </Button>
            </header>
            <p className="course-detail-dialog-meta">
              {detail.creditHours} credit hours
              {detail.meeting ? ` · ${detail.meeting}` : ''}
            </p>
            <p className="course-detail-dialog-description">{detail.description}</p>
            <section className="course-detail-dialog-prereqs" aria-label="Prerequisites">
              <h3 className="course-detail-dialog-prereqs-title">
                <Icon name="checkCircle" size={14} /> Prerequisites
              </h3>
              {detail.prereqs.length === 0 ? (
                <p className="course-detail-dialog-state">No prerequisite records on file.</p>
              ) : (
                <ul className="course-detail-dialog-prereq-list">
                  {detail.prereqs.map((prereq) => (
                    <li key={prereq.id} className="course-detail-dialog-prereq-row">
                      <span className="course-detail-dialog-prereq-id">CSE {prereq.id}</span>
                      <span className="course-detail-dialog-prereq-name">
                        {prereq.title ? toTitleCase(prereq.title) : 'Course details unavailable'}
                      </span>
                      <Badge variant={PREREQ_LABELS[prereq.status].variant} dot>
                        {PREREQ_LABELS[prereq.status].label}
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
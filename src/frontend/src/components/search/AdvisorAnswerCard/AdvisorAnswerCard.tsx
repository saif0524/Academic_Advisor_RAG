import Badge from '../../shared/Badge/Badge';
import Icon from '../../shared/Icon/Icon';
import Markdown from '../../shared/Markdown/Markdown';
import './AdvisorAnswerCard.css';

interface AdvisorAnswerCardProps {
  answer: { text: string; matchCount: number } | null;
  loading?: boolean;
  error?: string | null;
}

/**
 * The advisor's answer to a search query (wireframe 04; FC22/FC24 answer
 * surface). The answer text + match count come from the advisor agent;
 * the deterministic engine owns all verdicts.
 */
export default function AdvisorAnswerCard({ answer, loading = false, error = null }: AdvisorAnswerCardProps) {
  if (loading) {
    return (
      <section className="advisor-answer-card" aria-busy="true">
        <p className="advisor-answer-card-state">Advisor is reviewing your plan…</p>
      </section>
    );
  }
  if (error) {
    return (
      <section className="advisor-answer-card">
        <p className="advisor-answer-card-state advisor-answer-card-state--error">
          The advisor could not answer: {error}
        </p>
      </section>
    );
  }
  if (!answer) {
    return (
      <section className="advisor-answer-card">
        <p className="advisor-answer-card-state">
          Ask a question above to get an advisor answer grounded in your plan and the CSE catalog.
        </p>
      </section>
    );
  }
  return (
    <section className="advisor-answer-card" aria-label="Advisor answer">
      <header className="advisor-answer-card-header">
        <span className="advisor-answer-card-brand">
          <Icon name="cap" size={16} /> Advisor answer
        </span>
        {answer.matchCount > 0 ? (
          <Badge variant="primary">
            {answer.matchCount} matching course{answer.matchCount === 1 ? '' : 's'}
          </Badge>
        ) : null}
      </header>
      <Markdown className="advisor-answer-card-text" text={answer.text} />
    </section>
  );
}
import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';
import './Markdown.css';

interface MarkdownProps {
  /** Markdown source — e.g. the advisor's summarized answer (FC22/FC24). */
  text: string;
  className?: string;
}

/**
 * Renders advisor (LLM-summarized) text as markdown: headings, lists, bold,
 * code, links, GFM tables. Single newlines become line breaks (chat-style,
 * e.g. canned FC27 plan-shift replies). Raw HTML is not rendered (react-markdown default),
 * so model output can't inject markup. Links open in a new tab.
 */
export default function Markdown({ text, className }: MarkdownProps) {
  return (
    <div className={className ? `markdown ${className}` : 'markdown'}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}

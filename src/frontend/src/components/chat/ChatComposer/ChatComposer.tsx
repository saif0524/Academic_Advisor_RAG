import { useState } from 'react';
import Button from '../../shared/Button/Button';
import Icon from '../../shared/Icon/Icon';
import TextArea from '../../shared/TextArea/TextArea';
import './ChatComposer.css';

interface ChatComposerProps {
  /** Fired with the trimmed draft; the parent appends the turn. */
  onSend?: (text: string) => void;
  busy?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

/**
 * Prompt composer (FC35 prompt-based queries, FC22 chat input). Enter sends;
 * Shift+Enter inserts a newline. Empty drafts disable the send action; the
 * busy flag pins it while the (mock) turn resolves.
 */
export default function ChatComposer({
  onSend,
  busy = false,
  disabled = false,
  placeholder = 'Ask about your plan, classes, or degrees…',
}: ChatComposerProps) {
  const [draft, setDraft] = useState('');

  const send = () => {
    const text = draft.trim();
    if (text === '' || busy || disabled) return;
    onSend?.(text);
    setDraft('');
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLTextAreaElement> = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault(); // Enter = send (Shift+Enter = newline)
      send();
    }
  };

  return (
    <div className="chat-composer">
      <TextArea
        value={draft}
        onChange={setDraft}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        rows={2}
        ariaLabel="Message to the advisor"
      />
      <div className="chat-composer-actions">
        <Button onClick={send} disabled={disabled || busy || draft.trim() === ''}>
          <Icon name="send" size={14} /> Send
        </Button>
      </div>
    </div>
  );
}
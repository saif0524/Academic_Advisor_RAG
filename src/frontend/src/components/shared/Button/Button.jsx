import './Button.css';

/**
 * Shared primitive: reference example of the component anatomy
 * (.jsx + .css + story) for the shared/ domain. Used by forms and
 * confirmation surfaces (e.g. the FC2 planner, FC20–FC23 dialogs).
 *
 * Props: children (label), onClick (handler), variant ('primary'|'secondary'), disabled (bool).
 */
export default function Button({ children, onClick, variant = 'primary', disabled = false }) {
  return (
    <button
      type="button"
      className={`button button--${variant}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}
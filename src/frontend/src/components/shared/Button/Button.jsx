import './Button.css';

/**
 * Shared primitive: the one reference example of the component anatomy
 * (.jsx + .css + story) for the shared/ domain (buttons/cards/dialogs live
 * here per the react-component skill). Will be reused by FC20–FC21/F23
 * confirmation dialogs as features land.
 *
 * Props: children (label), onClick (handler), variant ('primary'|'secondary').
 */
export default function Button({ children, onClick, variant = 'primary' }) {
  return (
    <button type="button" className={`button button--${variant}`} onClick={onClick}>
      {children}
    </button>
  );
}
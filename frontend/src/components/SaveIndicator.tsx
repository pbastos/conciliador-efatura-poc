import React, { useEffect, useState } from 'react';
import './SaveIndicator.css';

export type SaveState = 'idle' | 'saving' | 'saved' | 'error';

interface SaveIndicatorProps {
  state: SaveState;
  className?: string;
  position?: 'inline' | 'absolute';
}

const SaveIndicator: React.FC<SaveIndicatorProps> = ({ 
  state, 
  className = '', 
  position = 'inline' 
}) => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (state === 'saving' || state === 'saved' || state === 'error') {
      setVisible(true);
    }

    if (state === 'saved') {
      const timer = setTimeout(() => {
        setVisible(false);
      }, 2500);
      return () => clearTimeout(timer);
    }
  }, [state]);

  if (!visible && state !== 'saving') return null;

  return (
    <span 
      className={`save-indicator ${state} ${position} ${visible ? 'visible' : ''} ${className}`}
    >
      {state === 'saving' && (
        <>
          <span className="save-spinner"></span>
          <span className="save-text">A guardar...</span>
        </>
      )}
      {state === 'saved' && (
        <>
          <svg className="save-checkmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          <span className="save-text">Guardado</span>
        </>
      )}
      {state === 'error' && (
        <>
          <svg className="save-error" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span className="save-text">Erro ao guardar</span>
        </>
      )}
    </span>
  );
};

export default SaveIndicator;
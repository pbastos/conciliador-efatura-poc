import React, { useState, useRef, useEffect } from 'react';
import './MatchStatusDropdown.css';

export type MatchStatus = 'unmatched' | 'proposed' | 'confirmed' | 'rejected';

interface MatchStatusDropdownProps {
  status: MatchStatus;
  confidence?: number;
  onStatusChange: (newStatus: MatchStatus) => void;
  disabled?: boolean;
}

const MatchStatusDropdown: React.FC<MatchStatusDropdownProps> = ({
  status,
  confidence,
  onStatusChange,
  disabled = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getStatusLabel = () => {
    switch (status) {
      case 'confirmed':
        return 'Confirmado';
      case 'proposed':
        return `Proposto${confidence ? ` (${Math.round(confidence * 100)}%)` : ''}`;
      case 'rejected':
        return 'Rejeitado';
      default:
        return 'Não reconciliado';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'confirmed':
        return '✓';
      case 'proposed':
        return '?';
      case 'rejected':
        return '✗';
      default:
        return '○';
    }
  };

  const handleStatusSelect = (newStatus: MatchStatus) => {
    if (newStatus !== status) {
      onStatusChange(newStatus);
    }
    setIsOpen(false);
  };

  return (
    <div className="match-status-dropdown" ref={dropdownRef}>
      <button
        className={`status-button ${status}`}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
      >
        <span className="status-icon">{getStatusIcon()}</span>
        <span className="status-label">{getStatusLabel()}</span>
        <svg 
          className="dropdown-arrow" 
          width="12" 
          height="12" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {isOpen && (
        <div className="dropdown-menu">
          <button
            className="dropdown-item confirmed"
            onClick={() => handleStatusSelect('confirmed')}
          >
            <span className="item-icon">✓</span>
            <span>Confirmar reconciliação</span>
          </button>
          <button
            className="dropdown-item rejected"
            onClick={() => handleStatusSelect('rejected')}
          >
            <span className="item-icon">✗</span>
            <span>Rejeitar proposta</span>
          </button>
          <button
            className="dropdown-item unmatched"
            onClick={() => handleStatusSelect('unmatched')}
          >
            <span className="item-icon">○</span>
            <span>Marcar como não reconciliado</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default MatchStatusDropdown;
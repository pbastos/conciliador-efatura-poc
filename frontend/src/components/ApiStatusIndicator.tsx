import React, { useEffect, useState } from 'react';
import './ApiStatusIndicator.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const ApiStatusIndicator: React.FC = () => {
  const [isOnline, setIsOnline] = useState<boolean | null>(null);

  const checkApiStatus = async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3000);
      
      const response = await fetch(`${API_URL}/health`, {
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      setIsOnline(response.ok);
    } catch (error) {
      setIsOnline(false);
    }
  };

  useEffect(() => {
    checkApiStatus();
    const interval = setInterval(checkApiStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  if (isOnline === null || isOnline === true) return null;

  return (
    <div className="api-status-banner">
      <div className="api-status-content">
        <svg className="warning-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <span>API offline - As funcionalidades podem estar limitadas</span>
      </div>
    </div>
  );
};

export default ApiStatusIndicator;
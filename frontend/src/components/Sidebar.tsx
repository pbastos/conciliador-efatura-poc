import React, { useState, useEffect } from 'react';
import './Sidebar.css';
import { apiService } from '../services/api';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  uploadCount: {
    efatura: number;
    bank: number;
  };
}

const Sidebar: React.FC<SidebarProps> = ({ activeTab, onTabChange }) => {
  const [isApiHealthy, setIsApiHealthy] = useState(true);

  useEffect(() => {
    // Check API health immediately
    checkApiHealth();

    // Check API health every 5 seconds
    const interval = setInterval(checkApiHealth, 5000);

    return () => clearInterval(interval);
  }, []);

  const checkApiHealth = async () => {
    const healthy = await apiService.checkHealth();
    setIsApiHealthy(healthy);
  };
  const menuItems = [
    {
      id: 'dashboard',
      title: 'Dashboard',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" />
        </svg>
      )
    },
    {
      id: 'upload',
      title: 'Carregar Ficheiros',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      )
    },
    {
      id: 'settings',
      title: 'Configurações',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M12 1v6m0 6v6m4.22-10.22l4.24 4.24m-4.24 4.24l4.24 4.24M20 12h-6m-6 0H2m10.22-4.22L7.98 3.54m4.24 4.24L7.98 20.46" />
        </svg>
      )
    }
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-circle">C</div>
        <div className="logo-text">
          <h2>Conciliador</h2>
          <p>E-fatura</p>
        </div>
      </div>

      <nav className="sidebar-nav">
        {menuItems.map(item => (
          <button
            key={item.id}
            className={`sidebar-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => onTabChange(item.id)}
          >
            <span className="sidebar-icon">{item.icon}</span>
            <span className="sidebar-text">{item.title}</span>
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="system-status">
          <span className={`status-dot ${isApiHealthy ? '' : 'error'}`}></span>
          <span className="status-text">
            {isApiHealthy ? 'Sistema ativo' : 'API desligada'}
          </span>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
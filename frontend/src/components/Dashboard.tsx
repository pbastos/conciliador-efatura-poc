import React from 'react';
import './Dashboard.css';

interface DashboardProps {
  onNavigate: (tab: string) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">Conciliador E-fatura</h1>
      <p className="dashboard-subtitle">
        Reconciliação automática entre faturas eletrónicas e movimentos bancários
      </p>

      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-icon-container">
            <svg className="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <div className="stat-value">94.8%</div>
          <div className="stat-label">Taxa de Reconciliação</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-container green">
            <svg className="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <div className="stat-value">1,234</div>
          <div className="stat-label">Documentos Processados</div>
        </div>
      </div>

      <div className="upload-section">
        <div className="upload-row">
          <div className="upload-card">
            <div className="upload-card-header">
              <div className="upload-icon blue">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <h3>Ficheiro E-fatura</h3>
            </div>
            <div className="upload-area" onClick={() => onNavigate('upload')}>
              <div className="upload-icon-large">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <p className="upload-text">Arraste o ficheiro E-fatura aqui</p>
              <p className="upload-formats">XML, XLSX ou CSV</p>
              <p className="upload-hint">Clique ou arraste para carregar</p>
            </div>
          </div>

          <div className="upload-card">
            <div className="upload-card-header">
              <div className="upload-icon green">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                  <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
                </svg>
              </div>
              <h3>Movimentos Bancários</h3>
            </div>
            <div className="upload-area" onClick={() => onNavigate('upload')}>
              <div className="upload-icon-large">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <p className="upload-text">Arraste o ficheiro bancário aqui</p>
              <p className="upload-formats">XLSX, CSV ou OFX</p>
              <p className="upload-hint">Clique ou arraste para carregar</p>
            </div>
          </div>
        </div>

        <div className="upload-footer">
          <h3>Carregue os Ficheiros</h3>
          <p>Carregue o ficheiro E-fatura e os movimentos bancários para continuar.</p>
          <button className="start-button" onClick={() => onNavigate('upload')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="9 11 12 14 22 4" />
              <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
            </svg>
            Iniciar Reconciliação
          </button>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
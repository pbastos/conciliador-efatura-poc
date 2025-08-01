import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import { apiService, EfaturaRecord, ReconciliationStats } from '../services/api';

interface DashboardProps {
  onNavigate: (tab: string) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [records, setRecords] = useState<EfaturaRecord[]>([]);
  const [stats, setStats] = useState<ReconciliationStats>({
    total_efatura: 0,
    total_bank: 0,
    matched: 0,
    unmatched_efatura: 0,
    unmatched_bank: 0,
    match_rate: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [recordsData, statsData] = await Promise.all([
          apiService.getRecordsWithMatches(50, 0),
          apiService.getReconciliationStats()
        ]);
        setRecords(recordsData);
        setStats(statsData);
        setError(null);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Erro ao carregar dados');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-PT');
  };

  const getStatusBadge = (status: string, confidence?: number) => {
    switch (status) {
      case 'matched':
      case 'confirmed':
        return <span className="status-badge matched">Reconciliado</span>;
      case 'proposed':
        return <span className="status-badge proposed">Proposto ({Math.round((confidence || 0) * 100)}%)</span>;
      case 'unmatched':
        return <span className="status-badge unmatched">Não Reconciliado</span>;
      default:
        return <span className="status-badge unmatched">Não Reconciliado</span>;
    }
  };

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
          <div className="stat-value">{stats.match_rate.toFixed(1)}%</div>
          <div className="stat-label">Taxa de Reconciliação</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-container green">
            <svg className="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
          <div className="stat-value">{stats.total_efatura}</div>
          <div className="stat-label">Documentos E-fatura</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-container blue">
            <svg className="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
              <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2-2v16" />
            </svg>
          </div>
          <div className="stat-value">{stats.total_bank}</div>
          <div className="stat-label">Movimentos Bancários</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon-container success">
            <svg className="stat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <div className="stat-value">{stats.matched}</div>
          <div className="stat-label">Reconciliados</div>
        </div>
      </div>

      {loading ? (
        <div className="loading-section">
          <div className="loading-spinner"></div>
          <p>A carregar dados...</p>
        </div>
      ) : error ? (
        <div className="error-section">
          <p>{error}</p>
          <button className="start-button" onClick={() => onNavigate('upload')}>
            Carregar Ficheiros
          </button>
        </div>
      ) : records.length === 0 ? (
        <div className="empty-section">
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
      ) : (
        <div className="reconciliation-section">
          <div className="section-header">
            <h2>Reconciliação de Documentos</h2>
            <div className="section-actions">
              <button className="btn-secondary" onClick={() => onNavigate('upload')}>
                Carregar Mais Ficheiros
              </button>
              <button className="btn-primary" onClick={() => onNavigate('matching')}>
                Fazer Reconciliação
              </button>
            </div>
          </div>
          
          <div className="reconciliation-table-container">
            <table className="reconciliation-table">
              <thead>
                <tr>
                  <th colSpan={5} className="section-divider">E-fatura</th>
                  <th colSpan={4} className="section-divider">Movimento Bancário</th>
                  <th className="section-divider">Estado</th>
                </tr>
                <tr>
                  <th>Nº Documento</th>
                  <th>Data</th>
                  <th>Fornecedor</th>
                  <th>NIF</th>
                  <th>Valor</th>
                  <th>Data</th>
                  <th>Descrição</th>
                  <th>Valor</th>
                  <th>Referência</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr key={record.efatura_id} className={record.match_id ? 'matched' : 'unmatched'}>
                    <td>{record.document_number}</td>
                    <td>{formatDate(record.document_date)}</td>
                    <td>{record.supplier_name}</td>
                    <td>{record.supplier_nif}</td>
                    <td className="amount">{formatCurrency(record.total_amount)}</td>
                    
                    <td>{record.movement_date ? formatDate(record.movement_date) : '-'}</td>
                    <td>{record.bank_description || '-'}</td>
                    <td className="amount">
                      {record.bank_amount ? formatCurrency(record.bank_amount) : '-'}
                    </td>
                    <td>{record.bank_reference || '-'}</td>
                    <td>
                      {getStatusBadge(record.match_status || record.efatura_status, record.confidence_score)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {records.length >= 50 && (
            <div className="table-footer">
              <p>Mostrando os primeiros 50 registos. <button className="link-button" onClick={() => onNavigate('matching')}>Ver todos na reconciliação</button></p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
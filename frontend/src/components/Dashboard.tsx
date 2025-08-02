import React, { useState, useEffect } from 'react';
import './Dashboard.css';
import { apiService, EfaturaRecord, ReconciliationStats } from '../services/api';
import MatchStatusDropdown, { MatchStatus } from './MatchStatusDropdown';

interface DashboardProps {
  onNavigate: (tab: string) => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [records, setRecords] = useState<EfaturaRecord[]>([]);
  const [bankRecords, setBankRecords] = useState<any[]>([]);
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
  const [currentPage, setCurrentPage] = useState(1);
  const [recordsPerPage] = useState(20);
  const [totalRecords, setTotalRecords] = useState(0);
  const [activeView, setActiveView] = useState<'efatura' | 'bank'>('efatura');

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const offset = (currentPage - 1) * recordsPerPage;
        
        if (activeView === 'efatura') {
          const [recordsData, statsData] = await Promise.all([
            apiService.getRecordsWithMatches(recordsPerPage, offset),
            apiService.getReconciliationStats()
          ]);
          setRecords(recordsData.records);
          setTotalRecords(recordsData.total);
          setStats(statsData);
        } else {
          const [bankData, statsData] = await Promise.all([
            apiService.getBankRecordsWithMatches(recordsPerPage, offset),
            apiService.getReconciliationStats()
          ]);
          setBankRecords(bankData.records);
          setTotalRecords(bankData.total);
          setStats(statsData);
        }
        
        setError(null);
      } catch (err: any) {
        if (err.message === 'Failed to fetch') {
          setError('API offline - Não é possível carregar os dados');
          // Não fazer console.error porque é esperado quando a API está offline
        } else {
          console.error('Error fetching dashboard data:', err);
          setError('Erro ao carregar dados');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [currentPage, recordsPerPage, activeView]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-PT');
  };

  const handleStatusChange = async (recordId: string, newStatus: MatchStatus) => {
    const record = records.find(r => r.efatura_id === recordId);
    if (!record) return;

    // Update local state optimistically
    setRecords(prevRecords => 
      prevRecords.map(r => 
        r.efatura_id === recordId 
          ? { ...r, match_status: newStatus as any }
          : r
      )
    );

    try {
      if (record.match_id) {
        // Update existing match status
        await apiService.updateMatchStatus(record.match_id, newStatus as any);
      } else if (newStatus === 'rejected') {
        // Nothing to do for unmatched records being rejected
        return;
      }
      
      // Refresh data to get updated state
      const offset = (currentPage - 1) * recordsPerPage;
      const updatedData = await apiService.getRecordsWithMatches(recordsPerPage, offset);
      setRecords(updatedData.records);
    } catch (error: any) {
      if (error.message !== 'Failed to fetch') {
        console.error('Error updating match status:', error);
      }
      // Revert optimistic update on error
      const offset = (currentPage - 1) * recordsPerPage;
      const originalData = await apiService.getRecordsWithMatches(recordsPerPage, offset);
      setRecords(originalData.records);
    }
  };

  const getMatchStatus = (record: EfaturaRecord): MatchStatus => {
    if (record.match_status === 'confirmed') return 'confirmed';
    if (record.match_status === 'rejected') return 'rejected';
    if (record.match_status === 'proposed') return 'proposed';
    if (record.match_id) return 'proposed';
    return 'unmatched';
  };

  // Calculate pagination values
  const totalPages = Math.ceil(totalRecords / recordsPerPage);
  const startRecord = totalRecords === 0 ? 0 : (currentPage - 1) * recordsPerPage + 1;
  const endRecord = Math.min(currentPage * recordsPerPage, totalRecords);

  const handlePageChange = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  const handleViewChange = (view: 'efatura' | 'bank') => {
    setActiveView(view);
    setCurrentPage(1); // Reset to first page when changing views
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
        <div className={`error-section ${error.includes('API offline') ? 'api-offline' : ''}`}>
          {error.includes('API offline') && (
            <svg className="warning-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          )}
          <p>{error}</p>
          <button className="start-button" onClick={() => onNavigate('upload')}>
            Carregar Ficheiros
          </button>
        </div>
      ) : records.length === 0 ? (
        <div className="empty-section">
          <div className="empty-message">
            <svg className="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="12" y1="12" x2="12" y2="18" />
              <line x1="9" y1="15" x2="15" y2="15" />
            </svg>
            <h3>Sem dados para reconciliar</h3>
            <p>Não existem registos E-fatura ou movimentos bancários carregados.</p>
            <button className="start-button" onClick={() => onNavigate('upload')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              Carregar Ficheiros
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
            </div>
          </div>
          
          {/* Tab navigation */}
          <div className="tab-navigation">
            <button 
              className={`tab-button ${activeView === 'efatura' ? 'active' : ''}`}
              onClick={() => handleViewChange('efatura')}
            >
              E-fatura → Banco
            </button>
            <button 
              className={`tab-button ${activeView === 'bank' ? 'active' : ''}`}
              onClick={() => handleViewChange('bank')}
            >
              Banco → E-fatura
            </button>
          </div>
          
          <div className="reconciliation-table-container">
            {activeView === 'efatura' ? (
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
                  {records.map((record, index) => (
                    <tr key={`efatura-${record.efatura_id}-${index}`} className={`match-row ${getMatchStatus(record)}`}>
                      <td>
                        <div className="document-info">
                          <div className="document-number">{record.document_number}</div>
                          {record.document_type && (
                            <span 
                              className="document-type-pill" 
                              data-type={record.document_type.toLowerCase().replace(/\s+/g, '-')}
                            >
                              {record.document_type}
                            </span>
                          )}
                        </div>
                      </td>
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
                        <MatchStatusDropdown
                          status={getMatchStatus(record)}
                          confidence={record.confidence_score}
                          onStatusChange={(newStatus) => handleStatusChange(record.efatura_id, newStatus)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <table className="reconciliation-table">
                <thead>
                  <tr>
                    <th colSpan={4} className="section-divider">Movimento Bancário</th>
                    <th colSpan={5} className="section-divider">E-fatura</th>
                    <th className="section-divider">Estado</th>
                  </tr>
                  <tr>
                    <th>Data</th>
                    <th>Descrição</th>
                    <th>Valor</th>
                    <th>Referência</th>
                    <th>Nº Documento</th>
                    <th>Data</th>
                    <th>Fornecedor</th>
                    <th>NIF</th>
                    <th>Valor</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {bankRecords.map((record, index) => (
                    <tr key={`bank-${record.bank_id}-${index}`} className={`match-row ${record.match_status || 'unmatched'}`}>
                      <td>{formatDate(record.movement_date)}</td>
                      <td>{record.bank_description}</td>
                      <td className="amount">{formatCurrency(record.bank_amount)}</td>
                      <td>{record.bank_reference || '-'}</td>
                      
                      <td>
                        {record.document_number ? (
                          <div className="document-info">
                            <div className="document-number">{record.document_number}</div>
                            {record.document_type && (
                              <span 
                                className="document-type-pill" 
                                data-type={record.document_type.toLowerCase().replace(/\s+/g, '-')}
                              >
                                {record.document_type}
                              </span>
                            )}
                          </div>
                        ) : '-'}
                      </td>
                      <td>{record.document_date ? formatDate(record.document_date) : '-'}</td>
                      <td>{record.supplier_name || '-'}</td>
                      <td>{record.supplier_nif || '-'}</td>
                      <td className="amount">
                        {record.total_amount ? formatCurrency(record.total_amount) : '-'}
                      </td>
                      <td>
                        <MatchStatusDropdown
                          status={record.match_status || 'unmatched'}
                          confidence={record.confidence_score}
                          onStatusChange={(newStatus) => handleStatusChange(record.efatura_id || '', newStatus)}
                          disabled={!record.match_id}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination Controls */}
          <div className="pagination-container">
            <div className="pagination-info">
              Mostrando {startRecord} a {endRecord} de {totalRecords} registos
            </div>
            
            <div className="pagination-controls">
              <button 
                className="pagination-btn"
                onClick={() => handlePageChange(1)}
                disabled={currentPage === 1}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="11 17 6 12 11 7" />
                  <polyline points="18 17 13 12 18 7" />
                </svg>
              </button>
              
              <button 
                className="pagination-btn"
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="15 18 9 12 15 6" />
                </svg>
              </button>
              
              {/* Page numbers */}
              <div className="pagination-numbers">
                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                  let pageNum: number;
                  if (totalPages <= 5) {
                    pageNum = i + 1;
                  } else if (currentPage <= 3) {
                    pageNum = i + 1;
                  } else if (currentPage >= totalPages - 2) {
                    pageNum = totalPages - 4 + i;
                  } else {
                    pageNum = currentPage - 2 + i;
                  }
                  
                  return (
                    <button
                      key={pageNum}
                      className={`pagination-number ${currentPage === pageNum ? 'active' : ''}`}
                      onClick={() => handlePageChange(pageNum)}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>
              
              <button 
                className="pagination-btn"
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
              
              <button 
                className="pagination-btn"
                onClick={() => handlePageChange(totalPages)}
                disabled={currentPage === totalPages}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="13 17 18 12 13 7" />
                  <polyline points="6 17 11 12 6 7" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
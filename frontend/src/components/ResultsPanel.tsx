import React, { useState, useEffect } from 'react';
import './ResultsPanel.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface ResultsPanelProps {
  refreshKey: number;
}

interface MatchResult {
  id: number;
  efatura_id: number;
  bank_movement_id: number;
  confidence_score: number;
  status: string;
  efatura_date: string;
  efatura_amount: number;
  efatura_nif: string;
  efatura_merchant: string;
  bank_date: string;
  bank_amount: number;
  bank_description: string;
}

const ResultsPanel: React.FC<ResultsPanelProps> = ({ refreshKey }) => {
  const [results, setResults] = useState<MatchResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchResults();
  }, [refreshKey, filter]);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const url = filter === 'all' 
        ? `${API_URL}/api/v1/matching/matches`
        : `${API_URL}/api/v1/matching/matches?status=${filter}`;
      
      const response = await fetch(url);
      if (response.ok) {
        const data = await response.json();
        setResults(data.matches || []);
      }
    } catch (error) {
      console.error('Error fetching results:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (resultId: number, newStatus: string) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/matching/matches/${resultId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (response.ok) {
        setResults(prev => 
          prev.map(r => r.id === resultId ? { ...r, status: newStatus } : r)
        );
      }
    } catch (error) {
      console.error('Error updating status:', error);
    }
  };

  const exportResults = async () => {
    // Export functionality not yet implemented in backend
    alert('Funcionalidade de exportação será implementada em breve');
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-PT');
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  };

  const getConfidenceClass = (score: number) => {
    if (score >= 0.8) return 'confidence-high';
    if (score >= 0.6) return 'confidence-medium';
    return 'confidence-low';
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'confirmed': return 'status-confirmed';
      case 'rejected': return 'status-rejected';
      default: return 'status-proposed';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'confirmed': return 'Confirmado';
      case 'rejected': return 'Rejeitado';
      default: return 'Proposto';
    }
  };

  return (
    <div className="results-container">
      <div className="results-header">
        <h2>📊 Resultados da Reconciliação</h2>
        <div className="results-actions">
          <select 
            className="filter-select"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          >
            <option value="all">Todos os resultados</option>
            <option value="proposed">Propostos</option>
            <option value="confirmed">Confirmados</option>
            <option value="rejected">Rejeitados</option>
          </select>
          <button className="export-button" onClick={exportResults}>
            📥 Exportar Excel
          </button>
        </div>
      </div>

      <div className="results-card">
        {loading ? (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>A carregar resultados...</p>
          </div>
        ) : results.length === 0 ? (
          <div className="no-results">
            <p>Nenhum resultado encontrado</p>
            <p className="no-results-hint">Execute a reconciliação para ver os resultados</p>
          </div>
        ) : (
          <div className="results-table">
            <table>
              <thead>
                <tr>
                  <th>Data E-fatura</th>
                  <th>Comerciante</th>
                  <th>Valor E-fatura</th>
                  <th>Data Banco</th>
                  <th>Descrição</th>
                  <th>Valor Banco</th>
                  <th>Confiança</th>
                  <th>Estado</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {results.map(result => (
                  <tr key={result.id}>
                    <td>{formatDate(result.efatura_date)}</td>
                    <td>
                      <div>{result.efatura_merchant}</div>
                      <div className="nif-info">NIF: {result.efatura_nif}</div>
                    </td>
                    <td className="amount">{formatCurrency(result.efatura_amount)}</td>
                    <td>{formatDate(result.bank_date)}</td>
                    <td className="description">{result.bank_description}</td>
                    <td className="amount">{formatCurrency(result.bank_amount)}</td>
                    <td>
                      <span className={`confidence-badge ${getConfidenceClass(result.confidence_score)}`}>
                        {Math.round(result.confidence_score * 100)}%
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge ${getStatusClass(result.status)}`}>
                        {getStatusText(result.status)}
                      </span>
                    </td>
                    <td>
                      {result.status === 'proposed' && (
                        <div className="action-buttons">
                          <button 
                            className="action-btn confirm-btn"
                            onClick={() => updateStatus(result.id, 'confirmed')}
                            title="Confirmar correspondência"
                          >
                            ✓
                          </button>
                          <button 
                            className="action-btn reject-btn"
                            onClick={() => updateStatus(result.id, 'rejected')}
                            title="Rejeitar correspondência"
                          >
                            ✗
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="results-summary">
        <h3>📈 Resumo</h3>
        <div className="summary-grid">
          <div className="summary-item">
            <span className="summary-label">Total de correspondências:</span>
            <span className="summary-value">{results.length}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Confirmadas:</span>
            <span className="summary-value success">
              {results.filter(r => r.status === 'confirmed').length}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Propostas:</span>
            <span className="summary-value warning">
              {results.filter(r => r.status === 'proposed').length}
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Rejeitadas:</span>
            <span className="summary-value danger">
              {results.filter(r => r.status === 'rejected').length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ResultsPanel;
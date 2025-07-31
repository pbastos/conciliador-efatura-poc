import React, { useState, useEffect } from 'react';
import './MatchingPanel.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface MatchingPanelProps {
  refreshKey: number;
  onMatchingComplete: () => void;
}

interface Stats {
  total_efatura: number;
  total_bank: number;
  matched: number;
  pending: number;
}

const MatchingPanel: React.FC<MatchingPanelProps> = ({ refreshKey, onMatchingComplete }) => {
  const [isMatching, setIsMatching] = useState(false);
  const [matchComplete, setMatchComplete] = useState(false);
  const [confidenceThreshold, setConfidenceThreshold] = useState(70);
  const [stats, setStats] = useState<Stats>({
    total_efatura: 0,
    total_bank: 0,
    matched: 0,
    pending: 0
  });

  useEffect(() => {
    fetchStats();
  }, [refreshKey]);

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/matching/summary`);
      if (response.ok) {
        const data = await response.json();
        setStats({
          total_efatura: data.total_efatura_records || 0,
          total_bank: data.total_bank_records || 0,
          matched: data.total_matches || 0,
          pending: data.unmatched_efatura_records || 0
        });
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleMatch = async () => {
    setIsMatching(true);
    setMatchComplete(false);

    try {
      const response = await fetch(`${API_URL}/api/v1/matching/auto-match`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          confidence_threshold: confidenceThreshold / 100
        }),
      });

      if (response.ok) {
        const result = await response.json();
        setStats(prev => ({
          ...prev,
          matched: result.matches_created,
          pending: result.total_efatura - result.matches_created
        }));
        setMatchComplete(true);
        setTimeout(() => {
          onMatchingComplete();
        }, 2000);
      } else {
        alert('Erro ao executar correspondência');
      }
    } catch (error) {
      console.error('Matching error:', error);
      alert('Erro ao executar correspondência');
    } finally {
      setIsMatching(false);
    }
  };

  const canMatch = stats.total_efatura > 0 && stats.total_bank > 0;

  return (
    <div className="matching-container">
      <div className="stats-grid">
        <div className="stat-card">
          <h3>E-faturas</h3>
          <p className="stat-value primary">{stats.total_efatura}</p>
          <p className="stat-subtitle">registos carregados</p>
        </div>
        <div className="stat-card">
          <h3>Movimentos</h3>
          <p className="stat-value primary">{stats.total_bank}</p>
          <p className="stat-subtitle">registos bancários</p>
        </div>
        <div className="stat-card">
          <h3>Correspondências</h3>
          <p className="stat-value success">{stats.matched}</p>
          <p className="stat-subtitle">encontradas</p>
        </div>
      </div>

      <div className="matching-card">
        <h2>🔄 Configurar Reconciliação</h2>
        
        <div className="confidence-control">
          <label htmlFor="confidence">
            Confiança Mínima: <strong>{confidenceThreshold}%</strong>
          </label>
          <input
            id="confidence"
            type="range"
            min="50"
            max="95"
            step="5"
            value={confidenceThreshold}
            onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
            className="confidence-slider"
            disabled={isMatching}
          />
          <div className="confidence-marks">
            <span>50%</span>
            <span>70%</span>
            <span>85%</span>
            <span>95%</span>
          </div>
          <p className="confidence-hint">
            Valores mais altos resultam em menos correspondências, mas com maior precisão
          </p>
        </div>

        <button
          className="match-button"
          onClick={handleMatch}
          disabled={!canMatch || isMatching}
        >
          {isMatching ? (
            <>
              <div className="loading-spinner small"></div>
              A processar...
            </>
          ) : (
            <>
              🔍 Executar Reconciliação
            </>
          )}
        </button>

        {!canMatch && (
          <p className="warning-message">
            ⚠️ Por favor carregue os ficheiros E-fatura e movimentos bancários primeiro
          </p>
        )}

        {matchComplete && (
          <div className="success-message">
            ✅ Reconciliação concluída! {stats.matched} correspondências encontradas.
          </div>
        )}
      </div>

      <div className="info-card">
        <h3>ℹ️ Como funciona a reconciliação</h3>
        <ul>
          <li>O sistema compara datas, valores e descrições</li>
          <li>Correspondências são sugeridas com base na confiança</li>
          <li>Pode rever e confirmar as correspondências nos resultados</li>
          <li>Ajuste o nível de confiança para controlar a precisão</li>
        </ul>
      </div>
    </div>
  );
};

export default MatchingPanel;
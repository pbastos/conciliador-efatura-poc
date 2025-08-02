import React, { useState, useEffect, useRef } from 'react';
import './Settings.css';
import { apiService } from '../services/api';
import SaveIndicator, { SaveState } from './SaveIndicator';

const Settings: React.FC = () => {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteSuccess, setDeleteSuccess] = useState(false);
  const [confidenceThreshold, setConfidenceThreshold] = useState(70);
  const [thresholdSaveState, setThresholdSaveState] = useState<SaveState>('idle');
  const [bankColumns, setBankColumns] = useState({
    date: '',
    description: '',
    amount: ''
  });
  const [columnSaveStates, setColumnSaveStates] = useState<Record<string, SaveState>>({
    date: 'idle',
    description: 'idle',
    amount: 'idle'
  });
  
  // Refs for debouncing
  const thresholdTimeoutRef = useRef<NodeJS.Timeout>();
  const columnTimeoutsRef = useRef<Record<string, NodeJS.Timeout>>({});

  // Load settings on component mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const settings = await apiService.getSettings();
        if (settings.confidence_threshold) {
          setConfidenceThreshold(Number(settings.confidence_threshold));
        }
        if (settings.bank_column_date) {
          setBankColumns(prev => ({ ...prev, date: settings.bank_column_date }));
        }
        if (settings.bank_column_description) {
          setBankColumns(prev => ({ ...prev, description: settings.bank_column_description }));
        }
        if (settings.bank_column_amount) {
          setBankColumns(prev => ({ ...prev, amount: settings.bank_column_amount }));
        }
      } catch (error) {
        console.error('Error loading settings:', error);
      }
    };
    loadSettings();
  }, []);

  // Save threshold when it changes (with debouncing)
  useEffect(() => {
    // Skip the initial load effect
    const isInitialMount = confidenceThreshold === 70;
    if (isInitialMount) return;

    // Clear existing timeout
    if (thresholdTimeoutRef.current) {
      clearTimeout(thresholdTimeoutRef.current);
    }

    // Show saving state immediately when value changes
    setThresholdSaveState('saving');

    // Debounce the actual save
    thresholdTimeoutRef.current = setTimeout(() => {
      saveConfidenceThreshold();
    }, 300); // Wait 300ms after user stops sliding

    return () => {
      if (thresholdTimeoutRef.current) {
        clearTimeout(thresholdTimeoutRef.current);
      }
    };
  }, [confidenceThreshold]);

  const saveConfidenceThreshold = async () => {
    try {
      await apiService.updateSetting('confidence_threshold', confidenceThreshold);
      setThresholdSaveState('saved');
    } catch (error) {
      console.error('Error saving confidence threshold:', error);
      setThresholdSaveState('error');
    }
  };

  const handleDeleteClick = () => {
    setShowConfirmDialog(true);
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    try {
      await apiService.deleteAllData();
      setDeleteSuccess(true);
      setShowConfirmDialog(false);
      
      // Limpar mensagem de sucesso após 3 segundos
      setTimeout(() => {
        setDeleteSuccess(false);
        // Recarregar a página para limpar todos os dados em cache
        window.location.reload();
      }, 3000);
    } catch (error) {
      console.error('Erro ao apagar dados:', error);
      alert('Erro ao apagar dados. Por favor, tente novamente.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleCancelDelete = () => {
    setShowConfirmDialog(false);
  };

  const handleColumnChange = (columnType: 'date' | 'description' | 'amount', value: string) => {
    setBankColumns(prev => ({ ...prev, [columnType]: value }));
    
    // Clear existing timeout for this column
    if (columnTimeoutsRef.current[columnType]) {
      clearTimeout(columnTimeoutsRef.current[columnType]);
    }

    // Show saving state immediately
    setColumnSaveStates(prev => ({ ...prev, [columnType]: 'saving' }));

    // Debounce the actual save
    columnTimeoutsRef.current[columnType] = setTimeout(() => {
      saveColumnSetting(columnType, value);
    }, 500); // Wait 500ms after user stops typing
  };

  const saveColumnSetting = async (columnType: 'date' | 'description' | 'amount', value: string) => {
    try {
      await apiService.updateSetting(`bank_column_${columnType}`, value);
      setColumnSaveStates(prev => ({ ...prev, [columnType]: 'saved' }));
    } catch (error) {
      console.error(`Error saving ${columnType} column:`, error);
      setColumnSaveStates(prev => ({ ...prev, [columnType]: 'error' }));
    }
  };

  return (
    <div className="settings-container">
      <h1 className="settings-title">Configurações</h1>
      <p className="settings-subtitle">
        Gerir configurações e dados da aplicação
      </p>

      <div className="settings-sections">
        {/* Secção de Configuração de Reconciliação */}
        <section className="settings-section">
          <h2 className="section-title">Configuração de Reconciliação</h2>
          <div className="section-content">
            <div className="setting-item">
              <div className="setting-info">
                <h4>Confiança Mínima para Correspondências</h4>
                <p>Define o nível mínimo de confiança para criar correspondências automáticas. Valores mais altos resultam em menos correspondências, mas com maior precisão.</p>
              </div>
              <div className="confidence-control">
                <div className="confidence-value">
                  <span className="label">Confiança atual:</span>
                  <span className="value">{confidenceThreshold}%</span>
                  <SaveIndicator state={thresholdSaveState} />
                </div>
                <input
                  type="range"
                  min="50"
                  max="95"
                  step="5"
                  value={confidenceThreshold}
                  onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
                  className="confidence-slider"
                />
                <div className="confidence-marks">
                  <span>50%</span>
                  <span>70%</span>
                  <span>85%</span>
                  <span>95%</span>
                </div>
                <div className="confidence-descriptions">
                  <div className={`description ${confidenceThreshold <= 60 ? 'active' : ''}`}>
                    <strong>Baixa (50-60%):</strong> Mais correspondências, menor precisão
                  </div>
                  <div className={`description ${confidenceThreshold > 60 && confidenceThreshold <= 80 ? 'active' : ''}`}>
                    <strong>Média (65-80%):</strong> Equilíbrio entre quantidade e precisão
                  </div>
                  <div className={`description ${confidenceThreshold > 80 ? 'active' : ''}`}>
                    <strong>Alta (85-95%):</strong> Apenas correspondências muito prováveis
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Secção de Mapeamento de Colunas Bancárias */}
        <section className="settings-section">
          <h2 className="section-title">Mapeamento de Colunas - Ficheiro Bancário</h2>
          <div className="section-content">
            <div className="column-mapping-info">
              <p>Configure os nomes das colunas do seu ficheiro bancário Excel/CSV. Estes nomes devem corresponder exatamente aos cabeçalhos no seu ficheiro.</p>
            </div>
            
            <div className="column-mappings">
              <div className="column-mapping-item">
                <label htmlFor="bank-date-column">
                  <h4>Coluna de Data</h4>
                  <p>Nome da coluna que contém a data do movimento</p>
                </label>
                <div className="column-input-wrapper">
                  <input
                    id="bank-date-column"
                    type="text"
                    value={bankColumns.date}
                    onChange={(e) => handleColumnChange('date', e.target.value)}
                    className="column-input has-indicator"
                    placeholder="Ex: Data, Data Movimento, Date"
                  />
                  <SaveIndicator state={columnSaveStates.date} position="absolute" />
                </div>
              </div>

              <div className="column-mapping-item">
                <label htmlFor="bank-description-column">
                  <h4>Coluna de Descrição</h4>
                  <p>Nome da coluna que contém a descrição do movimento</p>
                </label>
                <div className="column-input-wrapper">
                  <input
                    id="bank-description-column"
                    type="text"
                    value={bankColumns.description}
                    onChange={(e) => handleColumnChange('description', e.target.value)}
                    className="column-input has-indicator"
                    placeholder="Ex: Descrição, Descricao, Description"
                  />
                  <SaveIndicator state={columnSaveStates.description} position="absolute" />
                </div>
              </div>

              <div className="column-mapping-item">
                <label htmlFor="bank-amount-column">
                  <h4>Coluna de Valor</h4>
                  <p>Nome da coluna que contém o valor do movimento</p>
                </label>
                <div className="column-input-wrapper">
                  <input
                    id="bank-amount-column"
                    type="text"
                    value={bankColumns.amount}
                    onChange={(e) => handleColumnChange('amount', e.target.value)}
                    className="column-input has-indicator"
                    placeholder="Ex: Valor, Montante, Amount"
                  />
                  <SaveIndicator state={columnSaveStates.amount} position="absolute" />
                </div>
              </div>
            </div>

            <div className="column-mapping-help">
              <h4>💡 Dica</h4>
              <p>Se o upload do ficheiro bancário falhar, verifique se os nomes das colunas aqui configurados correspondem exatamente aos do seu ficheiro Excel/CSV.</p>
            </div>
          </div>
        </section>

        {/* Secção de Gestão de Dados */}
        <section className="settings-section">
          <h2 className="section-title">Gestão de Dados</h2>
          <div className="section-content">
            <div className="danger-zone">
              <h3 className="danger-title">Zona de Perigo</h3>
              <p className="danger-description">
                As ações nesta secção são irreversíveis. Por favor, tenha cuidado.
              </p>
              
              <div className="action-item">
                <div className="action-info">
                  <h4>Apagar Todos os Dados</h4>
                  <p>Remove permanentemente todos os registos E-fatura, movimentos bancários e reconciliações.</p>
                </div>
                <button 
                  className="btn-danger"
                  onClick={handleDeleteClick}
                  disabled={isDeleting}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    <line x1="10" y1="11" x2="10" y2="17" />
                    <line x1="14" y1="11" x2="14" y2="17" />
                  </svg>
                  Apagar Todos os Dados
                </button>
              </div>
            </div>

            {deleteSuccess && (
              <div className="success-message">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
                Todos os dados foram apagados com sucesso!
              </div>
            )}
          </div>
        </section>

        {/* Outras secções de configurações podem ser adicionadas aqui */}
      </div>

      {/* Dialog de Confirmação */}
      {showConfirmDialog && (
        <>
          <div className="modal-backdrop" onClick={handleCancelDelete} />
          <div className="confirm-dialog">
            <div className="dialog-icon danger">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <h3 className="dialog-title">Confirmar Eliminação</h3>
            <p className="dialog-message">
              Tem a certeza que deseja apagar <strong>todos os dados</strong>? Esta ação é irreversível e irá remover:
            </p>
            <ul className="data-list">
              <li>Todos os registos E-fatura</li>
              <li>Todos os movimentos bancários</li>
              <li>Todas as reconciliações</li>
            </ul>
            <div className="dialog-actions">
              <button 
                className="btn-secondary"
                onClick={handleCancelDelete}
                disabled={isDeleting}
              >
                Cancelar
              </button>
              <button 
                className="btn-danger"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? (
                  <>
                    <span className="spinner"></span>
                    A apagar...
                  </>
                ) : (
                  'Sim, apagar tudo'
                )}
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Settings;
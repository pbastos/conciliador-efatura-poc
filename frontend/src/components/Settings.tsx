import React, { useState } from 'react';
import './Settings.css';
import { apiService } from '../services/api';

const Settings: React.FC = () => {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteSuccess, setDeleteSuccess] = useState(false);

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

  return (
    <div className="settings-container">
      <h1 className="settings-title">Configurações</h1>
      <p className="settings-subtitle">
        Gerir configurações e dados da aplicação
      </p>

      <div className="settings-sections">
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
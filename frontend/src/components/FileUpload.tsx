import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import './FileUpload.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface FileUploadProps {
  onUploadSuccess: (type: 'efatura' | 'bank') => void;
}

const FileUpload: React.FC<FileUploadProps> = ({ onUploadSuccess }) => {
  const [efaturaFile, setEfaturaFile] = useState<File | null>(null);
  const [bankFile, setBankFile] = useState<File | null>(null);
  const [uploadingEfatura, setUploadingEfatura] = useState(false);
  const [uploadingBank, setUploadingBank] = useState(false);
  const [efaturaSuccess, setEfaturaSuccess] = useState(false);
  const [bankSuccess, setBankSuccess] = useState(false);

  const uploadFile = async (file: File, type: 'efatura' | 'bank') => {
    const formData = new FormData();
    formData.append('file', file);

    const setUploading = type === 'efatura' ? setUploadingEfatura : setUploadingBank;
    const setSuccess = type === 'efatura' ? setEfaturaSuccess : setBankSuccess;

    setUploading(true);
    setSuccess(false);

    const endpoint = type === 'efatura' ? '/api/v1/efatura/upload' : '/api/v1/bank/upload';

    try {
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        setSuccess(true);
        onUploadSuccess(type);
        setTimeout(() => setSuccess(false), 3000);
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
        const errorMessage = errorData.detail || `Erro ao carregar ficheiro ${type}`;
        console.error('Upload error:', errorData);
        alert(`Erro: ${errorMessage}`);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Erro ao carregar ficheiro');
    } finally {
      setUploading(false);
    }
  };

  const onDropEfatura = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setEfaturaFile(file);
      uploadFile(file, 'efatura');
    }
  }, []);

  const onDropBank = useCallback((acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (file) {
      setBankFile(file);
      uploadFile(file, 'bank');
    }
  }, []);

  const {
    getRootProps: getEfaturaRootProps,
    getInputProps: getEfaturaInputProps,
    isDragActive: isEfaturaDragActive
  } = useDropzone({
    onDrop: onDropEfatura,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv']
    },
    maxFiles: 1
  });

  const {
    getRootProps: getBankRootProps,
    getInputProps: getBankInputProps,
    isDragActive: isBankDragActive
  } = useDropzone({
    onDrop: onDropBank,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
      'text/csv': ['.csv']
    },
    maxFiles: 1
  });

  return (
    <div className="file-upload-container">
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
          
          <div
            {...getEfaturaRootProps()}
            className={`upload-area ${isEfaturaDragActive ? 'drag-active' : ''}`}
          >
            <input {...getEfaturaInputProps()} />
            
            {uploadingEfatura ? (
              <div className="uploading-state">
                <div className="loading-spinner"></div>
                <p>A carregar...</p>
              </div>
            ) : efaturaSuccess ? (
              <div className="success-state">
                <div className="success-icon">✓</div>
                <p>Ficheiro carregado com sucesso!</p>
              </div>
            ) : (
              <>
                <div className="upload-icon-large">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <p className="upload-text">
                  {isEfaturaDragActive
                    ? 'Solte o ficheiro aqui...'
                    : 'Arraste o ficheiro E-fatura aqui'}
                </p>
                <p className="upload-formats">XML, XLSX ou CSV</p>
                <p className="upload-hint">Clique ou arraste para carregar</p>
              </>
            )}
          </div>
          
          {efaturaFile && !uploadingEfatura && !efaturaSuccess && (
            <div className="file-info-card">
              <span>📎</span>
              <span>{efaturaFile.name}</span>
            </div>
          )}
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
          
          <div
            {...getBankRootProps()}
            className={`upload-area ${isBankDragActive ? 'drag-active' : ''}`}
          >
            <input {...getBankInputProps()} />
            
            {uploadingBank ? (
              <div className="uploading-state">
                <div className="loading-spinner"></div>
                <p>A carregar...</p>
              </div>
            ) : bankSuccess ? (
              <div className="success-state">
                <div className="success-icon">✓</div>
                <p>Ficheiro carregado com sucesso!</p>
              </div>
            ) : (
              <>
                <div className="upload-icon-large">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>
                <p className="upload-text">
                  {isBankDragActive
                    ? 'Solte o ficheiro aqui...'
                    : 'Arraste o ficheiro bancário aqui'}
                </p>
                <p className="upload-formats">XLSX, CSV ou OFX</p>
                <p className="upload-hint">Clique ou arraste para carregar</p>
              </>
            )}
          </div>
          
          {bankFile && !uploadingBank && !bankSuccess && (
            <div className="file-info-card">
              <span>📎</span>
              <span>{bankFile.name}</span>
            </div>
          )}
        </div>
      </div>

      <div className="instructions-card">
        <div className="instructions-header">
          <svg className="instructions-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          <h3>Instruções</h3>
        </div>
        <ul>
          <li>Carregue o ficheiro exportado do portal E-fatura</li>
          <li>Carregue o extrato bancário em formato Excel</li>
          <li>O sistema irá automaticamente fazer a correspondência entre os registos</li>
          <li>Pode rever e ajustar as correspondências propostas</li>
        </ul>
      </div>
    </div>
  );
};

export default FileUpload;
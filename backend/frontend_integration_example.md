# Frontend Integration Example with Simplified SQLite Backend

## API Endpoints Overview

### 1. E-fatura Management
```typescript
// Upload E-fatura Excel file
POST /api/v1/efatura/upload
Content-Type: multipart/form-data
Body: file (Excel file)

// Get E-fatura records
GET /api/v1/efatura/records?limit=100&offset=0&status=unmatched

// Get E-fatura summary
GET /api/v1/efatura/summary
```

### 2. Bank Movements Management
```typescript
// Upload Bank movements Excel file
POST /api/v1/bank/upload
Content-Type: multipart/form-data
Body: file (Excel file)

// Get Bank movements
GET /api/v1/bank/movements?limit=100&offset=0&status=unmatched

// Get unmatched movements
GET /api/v1/bank/unmatched?limit=50
```

### 3. Matching Operations
```typescript
// Run automatic matching
POST /api/v1/matching/auto-match

// Get match suggestions for specific e-fatura
GET /api/v1/matching/suggestions/{efatura_id}

// Create manual match
POST /api/v1/matching/manual-match
Body: { efatura_id: number, bank_movement_id: number }

// Get all matches
GET /api/v1/matching/matches?limit=100&offset=0

// Get matching summary
GET /api/v1/matching/summary
```

## React Component Example

```typescript
// services/api.ts
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1';

export const efaturaApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return axios.post(`${API_BASE}/efatura/upload`, formData);
  },
  
  getRecords: (params?: { limit?: number; offset?: number; status?: string }) =>
    axios.get(`${API_BASE}/efatura/records`, { params }),
    
  getSummary: () => axios.get(`${API_BASE}/efatura/summary`)
};

export const bankApi = {
  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return axios.post(`${API_BASE}/bank/upload`, formData);
  },
  
  getMovements: (params?: { limit?: number; offset?: number; status?: string }) =>
    axios.get(`${API_BASE}/bank/movements`, { params }),
    
  getUnmatched: (limit: number = 50) =>
    axios.get(`${API_BASE}/bank/unmatched`, { params: { limit } })
};

export const matchingApi = {
  autoMatch: () => axios.post(`${API_BASE}/matching/auto-match`),
  
  getSuggestions: (efaturaId: number) =>
    axios.get(`${API_BASE}/matching/suggestions/${efaturaId}`),
    
  createManualMatch: (efaturaId: number, bankMovementId: number) =>
    axios.post(`${API_BASE}/matching/manual-match`, { 
      efatura_id: efaturaId, 
      bank_movement_id: bankMovementId 
    }),
    
  getMatches: (params?: { limit?: number; offset?: number }) =>
    axios.get(`${API_BASE}/matching/matches`, { params }),
    
  getSummary: () => axios.get(`${API_BASE}/matching/summary`)
};
```

## Simple Dashboard Component

```typescript
// components/Dashboard.tsx
import React, { useState, useEffect } from 'react';
import { efaturaApi, bankApi, matchingApi } from '../services/api';

export const Dashboard: React.FC = () => {
  const [summary, setSummary] = useState<any>({});
  const [loading, setLoading] = useState(false);

  const loadSummary = async () => {
    try {
      const [efaturaSummary, bankSummary, matchingSummary] = await Promise.all([
        efaturaApi.getSummary(),
        bankApi.getSummary(),
        matchingApi.getSummary()
      ]);
      
      setSummary({
        efatura: efaturaSummary.data,
        bank: bankSummary.data,
        matching: matchingSummary.data
      });
    } catch (error) {
      console.error('Error loading summary:', error);
    }
  };

  const handleAutoMatch = async () => {
    setLoading(true);
    try {
      const result = await matchingApi.autoMatch();
      alert(`Matching complete! Matched: ${result.data.matched}, Suggested: ${result.data.suggested}`);
      await loadSummary();
    } catch (error) {
      console.error('Error during auto-match:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary();
  }, []);

  return (
    <div className="dashboard">
      <h1>Conciliador E-fatura POC</h1>
      
      <div className="summary-cards">
        <div className="card">
          <h3>E-fatura Records</h3>
          <p>Total: {summary.efatura?.total_records || 0}</p>
          <p>Matched: {summary.efatura?.matched_records || 0}</p>
          <p>Unmatched: {summary.efatura?.unmatched_records || 0}</p>
        </div>
        
        <div className="card">
          <h3>Bank Movements</h3>
          <p>Total: {summary.bank?.total_movements || 0}</p>
          <p>Matched: {summary.bank?.matched_movements || 0}</p>
          <p>Unmatched: {summary.bank?.unmatched_movements || 0}</p>
        </div>
        
        <div className="card">
          <h3>Matching Rate</h3>
          <p>E-fatura: {summary.matching?.efatura_match_rate || 0}%</p>
          <p>Bank: {summary.matching?.bank_match_rate || 0}%</p>
        </div>
      </div>
      
      <button 
        onClick={handleAutoMatch} 
        disabled={loading}
        className="auto-match-button"
      >
        {loading ? 'Processing...' : 'Run Auto-Match'}
      </button>
    </div>
  );
};
```
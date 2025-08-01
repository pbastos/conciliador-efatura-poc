const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface EfaturaRecord {
  efatura_id: string;
  document_number: string;
  document_date: string;
  supplier_name: string;
  supplier_nif: string;
  total_amount: number;
  tax_amount: number;
  efatura_status: 'unmatched' | 'matched' | 'confirmed' | 'rejected';
  match_id?: string;
  confidence_score?: number;
  match_status?: 'proposed' | 'confirmed' | 'rejected';
  bank_id?: string;
  movement_date?: string;
  bank_description?: string;
  bank_amount?: number;
  bank_reference?: string;
}

export interface ReconciliationStats {
  total_efatura: number;
  total_bank: number;
  matched: number;
  unmatched_efatura: number;
  unmatched_bank: number;
  match_rate: number;
}

export const apiService = {
  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${API_URL}/health`);
      return response.ok;
    } catch (error) {
      return false;
    }
  },

  async getRecordsWithMatches(limit = 100, offset = 0): Promise<EfaturaRecord[]> {
    const response = await fetch(
      `${API_URL}/api/v1/efatura/records-with-matches?limit=${limit}&offset=${offset}`
    );
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return response.json();
  },

  async getReconciliationStats(): Promise<ReconciliationStats> {
    try {
      // Get counts from different endpoints
      const [efaturaResponse, bankResponse] = await Promise.all([
        fetch(`${API_URL}/api/v1/efatura/records`),
        fetch(`${API_URL}/api/v1/bank/records`)
      ]);

      const efaturaRecords = await efaturaResponse.json();
      const bankRecords = await bankResponse.json();

      const total_efatura = efaturaRecords.length;
      const total_bank = bankRecords.length;

      // Count matched records
      const matched = efaturaRecords.filter((record: any) => 
        record.matching_status === 'matched' || record.matching_status === 'confirmed'
      ).length;

      const unmatched_efatura = total_efatura - matched;
      const unmatched_bank = bankRecords.filter((record: any) => 
        record.matching_status === 'unmatched'
      ).length;

      const match_rate = total_efatura > 0 ? (matched / total_efatura) * 100 : 0;

      return {
        total_efatura,
        total_bank,
        matched,
        unmatched_efatura,
        unmatched_bank,
        match_rate
      };
    } catch (error) {
      console.error('Error fetching reconciliation stats:', error);
      // Return default stats if API fails
      return {
        total_efatura: 0,
        total_bank: 0,
        matched: 0,
        unmatched_efatura: 0,
        unmatched_bank: 0,
        match_rate: 0
      };
    }
  },

  async updateMatchStatus(matchId: string, status: 'proposed' | 'confirmed' | 'rejected'): Promise<void> {
    const response = await fetch(`${API_URL}/api/v1/matches/${matchId}/status`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  },

  async createManualMatch(efaturaId: string, bankId: string): Promise<void> {
    const response = await fetch(`${API_URL}/api/v1/matches`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ efatura_id: efaturaId, bank_id: bankId })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  },

  async deleteMatch(matchId: string): Promise<void> {
    const response = await fetch(`${API_URL}/api/v1/matches/${matchId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  },

  async deleteAllData(): Promise<void> {
    const response = await fetch(`${API_URL}/api/v1/data/all`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
  }
};
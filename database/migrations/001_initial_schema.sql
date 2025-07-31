-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Organizations table for multi-tenant support
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- File uploads tracking
CREATE TABLE file_uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL CHECK (file_type IN ('efatura', 'bank')),
    file_size INTEGER,
    records_count INTEGER DEFAULT 0,
    upload_status VARCHAR(50) DEFAULT 'pending' CHECK (upload_status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    uploaded_by UUID,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- E-fatura records
CREATE TABLE efatura_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    file_upload_id UUID REFERENCES file_uploads(id) ON DELETE SET NULL,
    
    -- E-fatura specific fields
    document_number VARCHAR(100),
    document_date DATE NOT NULL,
    supplier_nif VARCHAR(20),
    supplier_name VARCHAR(255),
    total_amount DECIMAL(10, 2) NOT NULL,
    tax_amount DECIMAL(10, 2),
    taxable_base DECIMAL(10, 2),
    description TEXT,
    document_type VARCHAR(50),
    
    -- Matching status
    matching_status VARCHAR(50) DEFAULT 'unmatched' CHECK (matching_status IN ('unmatched', 'matched', 'confirmed', 'rejected')),
    
    -- Metadata
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bank movements
CREATE TABLE bank_movements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    file_upload_id UUID REFERENCES file_uploads(id) ON DELETE SET NULL,
    
    -- Bank movement fields
    movement_date DATE NOT NULL,
    value_date DATE,
    description TEXT,
    amount DECIMAL(10, 2) NOT NULL,
    balance DECIMAL(10, 2),
    reference VARCHAR(255),
    movement_type VARCHAR(50),
    
    -- Matching status
    matching_status VARCHAR(50) DEFAULT 'unmatched' CHECK (matching_status IN ('unmatched', 'matched', 'confirmed', 'rejected')),
    
    -- Metadata
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Matching results
CREATE TABLE matching_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    efatura_id UUID REFERENCES efatura_records(id) ON DELETE CASCADE,
    bank_movement_id UUID REFERENCES bank_movements(id) ON DELETE CASCADE,
    
    -- Matching details
    confidence_score DECIMAL(3, 2) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    matching_method VARCHAR(50) CHECK (matching_method IN ('exact', 'fuzzy', 'manual')),
    date_difference INTEGER,
    amount_difference DECIMAL(10, 2),
    
    -- Matching criteria used
    matching_criteria JSONB,
    matched_fields TEXT[],
    
    -- Status
    status VARCHAR(50) DEFAULT 'proposed' CHECK (status IN ('proposed', 'confirmed', 'rejected')),
    confirmed_by UUID,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    rejected_by UUID,
    rejected_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(efatura_id, bank_movement_id)
);

-- Matching sessions
CREATE TABLE matching_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    total_efatura_records INTEGER DEFAULT 0,
    total_bank_movements INTEGER DEFAULT 0,
    matched_count INTEGER DEFAULT 0,
    unmatched_efatura_count INTEGER DEFAULT 0,
    unmatched_bank_count INTEGER DEFAULT 0,
    
    -- Matching parameters used
    parameters JSONB,
    
    created_by UUID,
    status VARCHAR(50) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed'))
);

-- Create indexes for better query performance
CREATE INDEX idx_efatura_org_date ON efatura_records(org_id, document_date);
CREATE INDEX idx_efatura_supplier ON efatura_records(supplier_nif);
CREATE INDEX idx_efatura_amount ON efatura_records(total_amount);
CREATE INDEX idx_efatura_status ON efatura_records(matching_status);

CREATE INDEX idx_bank_org_date ON bank_movements(org_id, movement_date);
CREATE INDEX idx_bank_amount ON bank_movements(amount);
CREATE INDEX idx_bank_reference ON bank_movements(reference);
CREATE INDEX idx_bank_status ON bank_movements(matching_status);

CREATE INDEX idx_matching_org ON matching_results(org_id);
CREATE INDEX idx_matching_status ON matching_results(status);
CREATE INDEX idx_matching_confidence ON matching_results(confidence_score);
CREATE INDEX idx_matching_efatura ON matching_results(efatura_id);
CREATE INDEX idx_matching_bank ON matching_results(bank_movement_id);

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update timestamp triggers
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_efatura_records_updated_at BEFORE UPDATE ON efatura_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_bank_movements_updated_at BEFORE UPDATE ON bank_movements
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_matching_results_updated_at BEFORE UPDATE ON matching_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
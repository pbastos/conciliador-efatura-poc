-- Insert test organization
INSERT INTO organizations (id, name) VALUES 
    ('550e8400-e29b-41d4-a716-446655440001', 'Test Organization');

-- Insert test e-fatura records
INSERT INTO efatura_records (org_id, document_number, document_date, supplier_nif, supplier_name, total_amount, tax_amount, taxable_base, description, document_type) VALUES
    ('550e8400-e29b-41d4-a716-446655440001', 'FT 2024/001', '2024-01-15', '123456789', 'Fornecedor ABC Lda', 1230.00, 230.00, 1000.00, 'Serviços de consultoria', 'Fatura'),
    ('550e8400-e29b-41d4-a716-446655440001', 'FT 2024/002', '2024-01-20', '987654321', 'Empresa XYZ SA', 615.00, 115.00, 500.00, 'Material de escritório', 'Fatura'),
    ('550e8400-e29b-41d4-a716-446655440001', 'FT 2024/003', '2024-01-25', '123456789', 'Fornecedor ABC Lda', 2460.00, 460.00, 2000.00, 'Licenças de software', 'Fatura'),
    ('550e8400-e29b-41d4-a716-446655440001', 'NC 2024/001', '2024-01-28', '987654321', 'Empresa XYZ SA', -123.00, -23.00, -100.00, 'Devolução de material', 'Nota de Crédito');

-- Insert test bank movements
INSERT INTO bank_movements (org_id, movement_date, value_date, description, amount, reference, movement_type) VALUES
    ('550e8400-e29b-41d4-a716-446655440001', '2024-01-16', '2024-01-16', 'TRF FORNECEDOR ABC LDA', -1230.00, 'REF123456', 'Débito'),
    ('550e8400-e29b-41d4-a716-446655440001', '2024-01-21', '2024-01-22', 'PAGAMENTO EMPRESA XYZ', -615.00, 'REF789012', 'Débito'),
    ('550e8400-e29b-41d4-a716-446655440001', '2024-01-26', '2024-01-26', 'TRF ABC LDA SOFTWARE', -2460.00, 'REF345678', 'Débito'),
    ('550e8400-e29b-41d4-a716-446655440001', '2024-01-29', '2024-01-29', 'DEV XYZ SA', 123.00, 'REF901234', 'Crédito'),
    ('550e8400-e29b-41d4-a716-446655440001', '2024-01-30', '2024-01-30', 'COMISSAO BANCARIA', -15.50, 'REF567890', 'Débito');
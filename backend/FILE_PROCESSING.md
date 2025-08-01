# Enhanced File Processing for E-fatura Reconciliation

## Overview

The backend now includes enhanced file processing capabilities based on patterns from MyConcierge projects. The improvements provide robust handling of various Excel and CSV formats commonly used in Portuguese financial documents.

## Key Features

### 1. **Multi-Format Support**
- Excel files (.xlsx, .xls)
- CSV files with automatic delimiter detection (semicolon or comma)
- Automatic encoding detection (UTF-8 with BOM support)

### 2. **Intelligent Header Detection**
- Automatically finds header rows in Excel files (not just first row)
- Searches up to 20 rows to locate headers
- Works with files that have metadata or empty rows before headers

### 3. **Comprehensive Column Mapping**
- Supports multiple variations of Portuguese column names
- Case-insensitive matching
- Handles both standard and alternative column names

### 4. **Robust Data Parsing**

#### Currency Parsing
- European format: 1.234,56 €
- US format: 1,234.56
- Handles currency symbols (€, EUR)
- Removes spaces and special characters

#### Date Parsing
- Multiple format support:
  - DD/MM/YYYY (Portuguese standard)
  - DD-MM-YYYY
  - YYYY-MM-DD
  - DD.MM.YYYY
  - And more...
- Automatic format detection

### 5. **Enhanced Error Handling**
- Detailed error messages for debugging
- Row-level error reporting
- Skips invalid rows without failing entire import
- Returns warnings for problematic data

## E-fatura File Processing

### Supported Columns
The system recognizes these E-fatura column variations:

| Portuguese | English Mapping | Description |
|------------|----------------|-------------|
| Setor | sector | Business sector |
| Emitente | supplier_name | Supplier/Issuer name |
| Nº Fatura / ATCUD | document_number | Invoice number |
| Tipo | document_type | Document type |
| Data Emissão | document_date | Issue date |
| Total | total_amount | Total amount |
| IVA | tax_amount | VAT/Tax amount |
| Base Tributável | taxable_base | Taxable base |
| Situação | status | Document status |
| NIF | supplier_nif | Supplier tax ID |

### Processing Rules
- Skips rows with zero or empty total amounts
- Extracts numeric NIF (removes non-numeric characters)
- Validates required fields before insertion

## Bank File Processing

### Supported Columns
The system recognizes these bank statement column variations:

| Portuguese | English Mapping | Description |
|------------|----------------|-------------|
| Data Movimento | movement_date | Transaction date |
| Data Lançamento | movement_date | Posting date |
| Data Valor | movement_date | Value date |
| Descrição | description | Transaction description |
| Histórico | description | Transaction history |
| Montante | amount | Amount |
| Valor | amount | Value |
| Débito | debit | Debit amount |
| Crédito | credit | Credit amount |
| Referência | reference | Reference number |
| Saldo | balance | Balance |

### Special Handling
- Automatically combines debit/credit columns into single amount field
- Negative values for debits, positive for credits
- Skips empty transactions

## API Response Format

### Successful Upload Response
```json
{
  "success": true,
  "filename": "efatura_export.xlsx",
  "file_type": "excel",
  "records_processed": 150,
  "records_skipped": 5,
  "total_rows": 155,
  "warnings": [
    "Row 10: Invalid date format",
    "Row 25: Missing supplier name"
  ]
}
```

### Error Response
```json
{
  "detail": "Missing required columns: ['total_amount']. Available columns: ['Data', 'Fornecedor', 'Valor']"
}
```

## Usage Examples

### Upload E-fatura File
```bash
curl -X POST "http://localhost:8000/api/v1/efatura/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@efatura_export.xlsx"
```

### Upload Bank Statement
```bash
curl -X POST "http://localhost:8000/api/v1/bank/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@bank_statement.csv"
```

## Troubleshooting

### Common Issues

1. **"Could not read file" Error**
   - Ensure file is not corrupted
   - Check file is actual Excel/CSV (not renamed)
   - Try saving in different format

2. **"Missing required columns" Error**
   - Check the error message for available columns
   - Verify column names match expected format
   - Column names are case-insensitive

3. **Date Parsing Issues**
   - Dates should be in DD/MM/YYYY format
   - System attempts multiple formats automatically
   - Check for mixed date formats in file

4. **Currency Parsing Issues**
   - Amounts should use comma as decimal separator
   - Period used as thousand separator
   - Currency symbol (€) is automatically removed

## Best Practices

1. **File Preparation**
   - Remove unnecessary header rows or metadata
   - Ensure consistent date formats
   - Use standard Portuguese column names when possible

2. **Data Quality**
   - Verify numeric fields contain valid numbers
   - Check for complete supplier information
   - Ensure invoice numbers are unique

3. **Testing**
   - Test with small file first
   - Review warnings in response
   - Check processed vs skipped counts
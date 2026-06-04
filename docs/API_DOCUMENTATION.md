# API Documentation - Release Dashboard CSV Upload Service

**Version**: 1.0
**Last Updated**: 2026-06-02
**Base URL**: `http://localhost:8000` (or configured backend URL)

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
4. [Error Handling](#error-handling)
5. [Error Codes Reference](#error-codes-reference)
6. [Response Examples](#response-examples)
7. [Rate Limiting](#rate-limiting)
8. [CORS Configuration](#cors-configuration)

---

## Overview

The Release Dashboard CSV Upload Service provides RESTful API endpoints for:
- ✅ Uploading CSV files with automatic validation
- ✅ Confirming file acceptance and moving to processing queue
- ✅ Retrieving health status
- ✅ Accessing error reports

### API Features

- **Multipart Form Upload**: Support for large file uploads (up to 500MB)
- **Smart Validation**: Automatic encoding, delimiter, and header detection
- **Rich Error Reporting**: Detailed, actionable error messages in Spanish
- **File Sanitization**: Prevents path traversal and injection attacks
- **Asynchronous Processing**: Non-blocking file conversion pipeline

---

## Authentication

Currently, the API does **not require authentication**. This may be added in future versions.

**Note**: For production deployment, implement authentication (JWT, OAuth2, or API keys).

---

## Endpoints

### 1. Health Check Endpoint

**Verify the API is running and responding.**

```http
GET /api/health
```

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-02T10:30:00Z",
  "version": "1.0"
}
```

**Use Case**: Monitor if the API is available before attempting uploads.

---

### 2. Upload File Endpoint

**Upload and validate a CSV file.**

```http
POST /api/upload
Content-Type: multipart/form-data

file: <CSV file>
```

**Request Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File (multipart) | Yes | CSV file, max 500MB |

**Request Headers**:
```
Content-Type: multipart/form-data
```

**Response (200 OK)** - Validation Passed:
```json
{
  "success": true,
  "temp_file_path": "/tmp/uploads/20260602_103000_145928.csv",
  "filename": "datos-masivas.csv",
  "validation_result": {
    "valid": true,
    "encoding_detected": "utf-8",
    "encoding_confidence": 0.95,
    "delimiter_detected": ",",
    "headers": [
      "ID de incidencia",
      "Descripción",
      "Estatus",
      "Fecha de envío",
      "Grupo asignado",
      "Urgencia",
      "Impacto"
    ],
    "row_count": 150,
    "preview": {
      "first_rows": [
        {
          "ID de incidencia": "INC000003884945",
          "Descripción": "LIVEPERSON ERROR",
          "Estatus": "Abierto",
          "Fecha de envío": "02/06/2026 8:40 AM",
          "Grupo asignado": "SOP_TEAM",
          "Urgencia": "Alta",
          "Impacto": "Masiva"
        }
      ],
      "file_size_mb": 3.5
    },
    "warnings": []
  },
  "metadata": {
    "upload_timestamp": "2026-06-02T10:30:00Z",
    "estimated_conversion_time_seconds": 15
  }
}
```

**Response (400 Bad Request)** - Validation Failed:
```json
{
  "detail": {
    "error": "ERR_005",
    "message": "Falta columnas requeridas: ['Urgencia']. Verifica que el archivo CSV incluya todas las columnas necesarias."
  }
}
```

**Response (413 Payload Too Large)** - File Too Big:
```json
{
  "detail": {
    "error": "ERR_003",
    "message": "Archivo demasiado grande: máximo 500 MB permitido",
    "help_url": "https://docs.example.com/es/errores/archivo-grande"
  }
}
```

**Status Codes**:
- `200 OK` - File validated successfully, ready for confirmation
- `400 Bad Request` - Validation error (missing headers, bad encoding, etc.)
- `413 Payload Too Large` - File exceeds 500MB limit
- `500 Internal Server Error` - Server error during validation

**Important**: The upload endpoint returns a `temp_file_path` which must be used in the confirm-upload endpoint. This path is valid for 1 hour.

---

### 3. Confirm Upload Endpoint

**Confirm file acceptance and trigger conversion.**

```http
POST /api/confirm-upload
Content-Type: application/json

{
  "temp_file_path": "/tmp/uploads/20260602_103000_145928.csv",
  "filename": "datos-masivas.csv"
}
```

**Request Body**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `temp_file_path` | String | Yes | Path returned by `/api/upload` |
| `filename` | String | Yes | Original filename (used for sanitization) |

**Response (200 OK)** - File Confirmed:
```json
{
  "success": true,
  "message": "Archivo confirmado y movido a cola de procesamiento",
  "file_info": {
    "original_filename": "datos-masivas.csv",
    "sanitized_filename": "datos-masivas_20260602_103000.csv",
    "destination": "data/input/datos-masivas_20260602_103000.csv",
    "file_size_bytes": 3670016
  },
  "processing": {
    "status": "queued",
    "estimated_completion_seconds": 20,
    "conversion_type": "massive_incidents"
  },
  "metadata": {
    "confirmed_timestamp": "2026-06-02T10:30:15Z",
    "upload_session_duration_seconds": 15
  }
}
```

**Response (404 Not Found)** - Temp File Expired:
```json
{
  "detail": {
    "error": "ERR_005",
    "message": "Archivo temporal no encontrado. La sesión de carga puede haber expirado. Por favor, intenta nuevamente."
  }
}
```

**Response (403 Forbidden)** - Permission Error:
```json
{
  "detail": {
    "error": "ERR_013",
    "message": "Permiso denegado: No se puede escribir en el directorio de procesamiento. Contacta al administrador."
  }
}
```

**Response (507 Insufficient Storage)** - Disk Full:
```json
{
  "detail": {
    "error": "ERR_014",
    "message": "Espacio en disco insuficiente (10 MB disponibles, 50 MB requeridos). Libera espacio y vuelve a intentar."
  }
}
```

**Status Codes**:
- `200 OK` - File successfully moved to processing queue
- `400 Bad Request` - Invalid request parameters
- `403 Forbidden` - Permission denied (disk write error)
- `404 Not Found` - Temp file not found or session expired
- `507 Insufficient Storage` - Not enough disk space
- `500 Internal Server Error` - Server error during file move

---

### 4. Error Report Endpoint

**Download detailed error report from failed upload.**

```http
GET /api/error-report/{report_id}
```

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `report_id` | String | Error report ID (provided in upload error response) |

**Response (200 OK)**:
```json
{
  "report_id": "err-20260602-103000-145928",
  "upload_id": "upload-20260602-103000-145928",
  "timestamp": "2026-06-02T10:30:00Z",
  "error_summary": {
    "error_code": "ERR_001",
    "error_message": "Falta columnas requeridas: ['Urgencia', 'Impacto']",
    "affected_rows": "All (header validation failed)"
  },
  "file_info": {
    "filename": "invalid-data.csv",
    "file_size_bytes": 2048,
    "encoding_detected": "utf-8",
    "delimiter_detected": ",",
    "row_count": 10
  },
  "detailed_errors": [
    {
      "type": "validation",
      "field": "headers",
      "issue": "Missing required header 'Urgencia'",
      "solution": "Add 'Urgencia' column with values: Alta, Media, Baja"
    },
    {
      "type": "validation",
      "field": "headers",
      "issue": "Missing required header 'Impacto'",
      "solution": "Add 'Impacto' column with values: Masiva, Normal, Mínima"
    }
  ],
  "troubleshooting": [
    "Verify that your CSV file has the required columns listed above",
    "Check that the first row contains column headers, not data",
    "Compare your headers with the example provided in the documentation",
    "If encoding shows as 'cp1252' or 'windows-1252', re-save your file as UTF-8"
  ],
  "next_steps": [
    "1. Download the template CSV from the documentation",
    "2. Add your data to the template (which has correct headers)",
    "3. Re-upload the file using the CSV Upload button"
  ],
  "support_resources": {
    "user_guide": "https://docs.example.com/guia-usuario",
    "faq": "https://docs.example.com/faq",
    "contact": "ops-support@example.com"
  }
}
```

**Response (404 Not Found)**:
```json
{
  "detail": "Error report not found or has expired"
}
```

**Status Codes**:
- `200 OK` - Error report found and returned
- `404 Not Found` - Report not found or expired (reports expire after 24 hours)

---

## Error Handling

### Error Response Format

All error responses follow this format:

```json
{
  "detail": {
    "error": "ERR_XXX",
    "message": "User-friendly message in Spanish",
    "help_url": "https://docs.example.com/es/errores/error-code"
  }
}
```

### Error Codes Reference

| Code | HTTP Status | Meaning | Solution |
|------|-------------|---------|----------|
| **ERR_001** | 400 | Missing required headers | Add missing columns to CSV |
| **ERR_002** | 400 | Unsupported file encoding | Save file as UTF-8 |
| **ERR_003** | 413 | File too large (>500MB) | Split file or contact admin |
| **ERR_004** | 400 | Invalid date format | Use format: DD/MM/YYYY HH:MM AM/PM |
| **ERR_005** | 400 | Validation failure / Session expired | Recheck file or re-upload |
| **ERR_006** | 400 | Invalid enum value | Use only allowed values |
| **ERR_007** | 400 | Field too long | Reduce field content length |
| **ERR_008** | 400 | Invalid field type | Check data format |
| **ERR_009** | 400 | No data rows | File must have data below headers |
| **ERR_010** | 400 | Delimiter not detected | Use comma, semicolon, or tab |
| **ERR_011** | 500 | Network error | Check connection and retry |
| **ERR_012** | 500 | Server error | Retry or contact support |
| **ERR_013** | 403 | Permission denied | Contact administrator |
| **ERR_014** | 507 | Disk full | Contact administrator |

---

## Response Examples

### Successful Upload and Confirmation Workflow

**Step 1: Upload**
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@datos.csv"
```

Response:
```json
{
  "success": true,
  "temp_file_path": "/tmp/uploads/20260602_103000_145928.csv",
  "validation_result": {
    "valid": true,
    "encoding_detected": "utf-8"
  }
}
```

**Step 2: Confirm Upload**
```bash
curl -X POST http://localhost:8000/api/confirm-upload \
  -H "Content-Type: application/json" \
  -d '{
    "temp_file_path": "/tmp/uploads/20260602_103000_145928.csv",
    "filename": "datos.csv"
  }'
```

Response:
```json
{
  "success": true,
  "processing": {
    "status": "queued",
    "estimated_completion_seconds": 20
  }
}
```

---

## Rate Limiting

Currently, there is **no rate limiting** implemented.

**For production use**, implement rate limiting:
- Limit uploads to **10 requests per minute per IP**
- Limit file size to **500 MB per upload**
- Limit total storage to **100 GB per day**

---

## CORS Configuration

The API allows requests from the frontend domain:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

For production, restrict to specific domains:
```
Access-Control-Allow-Origin: https://dashboard.example.com
```

---

## Integration Examples

### Python (requests library)

```python
import requests
from pathlib import Path

# Upload file
files = {'file': open('datos.csv', 'rb')}
response = requests.post('http://localhost:8000/api/upload', files=files)
upload_data = response.json()

if upload_data['success']:
    temp_path = upload_data['temp_file_path']

    # Confirm upload
    confirm_data = {
        'temp_file_path': temp_path,
        'filename': 'datos.csv'
    }
    response = requests.post(
        'http://localhost:8000/api/confirm-upload',
        json=confirm_data
    )

    if response.status_code == 200:
        print("✅ File uploaded successfully")
    else:
        print(f"❌ Error: {response.json()}")
```

### JavaScript (fetch)

```javascript
async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  // Upload
  const uploadResponse = await fetch('http://localhost:8000/api/upload', {
    method: 'POST',
    body: formData
  });

  const uploadData = await uploadResponse.json();

  if (uploadData.success) {
    // Confirm
    const confirmResponse = await fetch('http://localhost:8000/api/confirm-upload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        temp_file_path: uploadData.temp_file_path,
        filename: file.name
      })
    });

    const confirmData = await confirmResponse.json();
    console.log('✅ File uploaded:', confirmData);
  }
}
```

### cURL

```bash
# Upload
curl -X POST http://localhost:8000/api/upload \
  -F "file=@datos.csv" \
  -o response.json

# Extract temp_file_path
TEMP_PATH=$(jq -r '.temp_file_path' response.json)

# Confirm
curl -X POST http://localhost:8000/api/confirm-upload \
  -H "Content-Type: application/json" \
  -d "{
    \"temp_file_path\": \"$TEMP_PATH\",
    \"filename\": \"datos.csv\"
  }"
```

---

## Support

For API issues:
- 📧 Email: api-support@example.com
- 🐛 Report bugs with: file content, error response, and HTTP status code
- 📚 Full documentation: https://docs.example.com

---

**Last Updated**: 2 June 2026
**API Version**: 1.0

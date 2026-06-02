# CSV Upload API - Backend

Backend API for CSV file upload, validation, and automatic conversion pipeline.

## Quick Start

### Setup

1. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Create required directories**:
```bash
mkdir -p logs temp_uploads
```

### Running the Server

```bash
python -m app.main
```

Server will start on `http://localhost:8000`

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "CSV Upload API",
  "version": "1.0.0"
}
```

### API Documentation

Once server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Project Structure

```
backend/
├── app/                    # Application code
│   ├── main.py            # FastAPI app entry point
│   ├── routes/            # API endpoints (T003+)
│   ├── services/          # Business logic (T003+)
│   ├── models/            # Data models (T003+)
│   ├── utils/             # Utilities (validators, sanitizers, etc.)
│   └── logging/           # Logging configuration
├── tests/                  # Test files
├── logs/                   # Log files (git-ignored)
├── temp_uploads/          # Temporary upload storage (git-ignored)
├── requirements.txt       # Python dependencies
├── .env.example           # Configuration template
└── README.md              # This file
```

## Development

### Run Tests

```bash
pytest -v
```

### Run with Auto-Reload

Already configured in `main.py` - changes to files will trigger server reload.

### Logging

All requests and events are logged to:
- Console (during development)
- `logs/api.log` (if configured)

## Configuration

Edit `.env` file to configure:

- **HOST** / **PORT**: Server address
- **CORS_ORIGINS**: Allowed frontend domains
- **MAX_FILE_SIZE_MB**: Maximum upload file size (default 500MB)
- **TEMP_UPLOAD_DIR**: Where to temporarily store uploads
- **DATA_INPUT_DIR**: Where to move validated files (for cron)
- **DATA_OUTPUT_DIR**: Where converted JSON files are stored

## Next Steps

After T001 (Backend Setup), implement:

- **T003**: Create `/api/health` endpoint (already done in main.py)
- **T004**: Setup CORS (already done in main.py)
- **T005**: Create logging infrastructure
- **T006**: Setup error middleware
- **T007**: Create configuration handler
- **T021**: Implement POST `/api/upload` endpoint
- **T011-T020**: Implement validators (encoding, headers, delimiter)

## Troubleshooting

### "ModuleNotFoundError: No module named 'fastapi'"

Install dependencies:
```bash
pip install -r requirements.txt
```

### Server won't start

Check port is not in use:
```bash
# On Linux/Mac
lsof -i :8000

# On Windows
netstat -ano | findstr :8000
```

### CORS errors

Update `CORS_ORIGINS` in `.env` to include your frontend domain.

---

**Framework**: FastAPI 0.104.1
**Python**: 3.8+
**Status**: ✅ Ready for Phase 1 completion

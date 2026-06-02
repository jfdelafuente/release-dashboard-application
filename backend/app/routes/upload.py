"""
File Upload Routes
Handles CSV file upload, validation, and processing
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request
from fastapi.responses import JSONResponse
import logging
from pathlib import Path
from datetime import datetime

from app.config import Config
from app.validators.encoding import detect_encoding, is_encoding_supported
from app.validators.delimiter import detect_delimiter
from app.validators.headers import validate_headers
from app.validators.counter import count_csv_rows_with_header
from app.utils.error_messages import (
    get_error_message, file_not_csv_error, file_too_large_error,
    missing_headers_error, unsupported_encoding_error, no_data_rows_error
)
from app.utils.sanitizer import sanitize_filename
from app.utils.temp_files import TempFileManager
from app.utils.preview import generate_preview, format_file_size
from app.logging.upload_log import get_upload_logger

logger = logging.getLogger(__name__)
upload_logger = get_upload_logger()

router = APIRouter(prefix="/api", tags=["upload"])

# Initialize temp file manager
temp_manager = TempFileManager(Config.TEMP_UPLOAD_DIR)


@router.post("/upload", response_class=JSONResponse)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload and validate CSV file

    Args:
        file: CSV file from multipart/form-data

    Returns:
        JSON with validation results and metadata
    """
    original_filename = file.filename

    try:
        # Validate file extension
        if not original_filename.lower().endswith('.csv'):
            logger.warning(f"Non-CSV file upload attempted: {original_filename}")
            error = file_not_csv_error()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size
        if file_size > Config.MAX_FILE_SIZE_BYTES:
            logger.warning(
                f"File too large: {original_filename} ({file_size} bytes)"
            )
            error = file_too_large_error(Config.MAX_FILE_SIZE_MB)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=error
            )

        # Validate minimum file size (at least has headers)
        if file_size == 0:
            logger.warning(f"Empty file upload: {original_filename}")
            error = get_error_message('empty_file')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "ERR_008", "message": error}
            )

        # Log upload start
        upload_logger.log_upload_start(original_filename, file_size)

        # Create temporary file
        temp_file_path = temp_manager.create_temp_file(original_filename, file_content)
        logger.info(f"Temporary file created: {temp_file_path}")

        # Run validation pipeline
        validation_result = validate_upload(temp_file_path, original_filename)

        if not validation_result['success']:
            # Log validation error
            upload_logger.log_error(
                original_filename,
                validation_result.get('error', 'Validation failed'),
                'validation'
            )
            # Cleanup temp file on validation failure
            temp_manager.delete_temp_file(temp_file_path)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": validation_result.get('error_code', 'ERR_005'),
                    "message": validation_result.get('error', 'Validation failed'),
                    "errors": validation_result.get('errors', [])
                }
            )

        # Log successful validation
        upload_logger.log_validation(
            original_filename,
            validation_result['encoding'],
            validation_result['delimiter'],
            validation_result['row_counts']['data_count'],
            validation_result['headers_count'],
            True
        )

        # Return success response with metadata
        return {
            "success": True,
            "message": "File uploaded and validated successfully",
            "temp_file_path": temp_file_path,
            "metadata": {
                "filename": original_filename,
                "file_size": file_size,
                "file_size_formatted": format_file_size(file_size),
                "encoding_detected": validation_result['encoding'],
                "encoding_confidence": validation_result['encoding_confidence'],
                "delimiter_detected": validation_result['delimiter'],
                "headers": validation_result['headers'],
                "headers_count": validation_result['headers_count'],
                "record_count": validation_result['row_counts']['data_count'],
                "warnings": validation_result.get('warnings', [])
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in upload: {e}", exc_info=True)
        upload_logger.log_error(original_filename, str(e))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ERR_012",
                "message": "An unexpected error occurred during upload processing"
            }
        )


@router.post("/confirm-upload")
async def confirm_upload(data: dict):
    """
    Confirm upload and move file to input directory for conversion

    Args:
        data: Dict with temp_file_path and metadata

    Returns:
        JSON with confirmation and conversion status
    """
    try:
        temp_file_path = data.get('temp_file_path')
        original_filename = data.get('filename')

        if not temp_file_path or not original_filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields: temp_file_path, filename"
            )

        temp_file_path = Path(temp_file_path)

        if not temp_file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Temporary file not found"
            )

        # Sanitize filename
        safe_filename = sanitize_filename(original_filename)

        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{safe_filename}"

        # Move to input directory
        input_dir = Path(Config.DATA_INPUT_DIR)
        input_dir.mkdir(parents=True, exist_ok=True)

        target_path = input_dir / safe_filename

        try:
            temp_file_path.rename(target_path)
            logger.info(f"File moved to input directory: {target_path}")
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "ERR_013",
                    "message": "Failed to move file to processing directory"
                }
            )

        # Log file movement
        upload_logger.log_upload({
            'filename': original_filename,
            'final_filename': safe_filename,
            'status': 'moved_to_input',
            'timestamp': datetime.utcnow().isoformat()
        })

        return {
            "success": True,
            "message": "File confirmed and moved to processing queue",
            "final_filename": safe_filename,
            "status": "processing"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing upload confirmation"
        )


def validate_upload(file_path: str, original_filename: str) -> dict:
    """
    Run complete validation pipeline on uploaded file

    Args:
        file_path: Path to uploaded file
        original_filename: Original filename

    Returns:
        Dict with validation results and metadata
    """
    try:
        result = {
            'success': False,
            'error': None,
            'error_code': None,
            'errors': [],
            'warnings': []
        }

        # Detect encoding
        encoding, encoding_confidence = detect_encoding(file_path)
        result['encoding'] = encoding
        result['encoding_confidence'] = encoding_confidence

        if not is_encoding_supported(encoding):
            result['error'] = get_error_message(
                'unsupported_encoding',
                encoding=encoding
            )
            result['error_code'] = 'ERR_002'
            return result

        # Detect delimiter
        delimiter = detect_delimiter(file_path, encoding)
        result['delimiter'] = delimiter

        # Validate headers
        headers_result = validate_headers(file_path, encoding, delimiter)
        result['headers'] = headers_result['headers']
        result['headers_count'] = len(headers_result['headers'])

        if not headers_result['valid']:
            result['error'] = get_error_message(
                'missing_headers',
                columns=', '.join(headers_result['missing_headers'])
            )
            result['error_code'] = 'ERR_001'
            result['errors'] = headers_result['missing_headers']
            return result

        # Count rows
        row_counts = count_csv_rows_with_header(file_path, encoding, delimiter)
        result['row_counts'] = row_counts

        if row_counts['data_count'] == 0:
            result['error'] = get_error_message('no_data_rows')
            result['error_code'] = 'ERR_004'
            return result

        # Generate warnings
        warnings = []
        if encoding != 'utf-8':
            warnings.append(f"Unusual encoding detected: {encoding}")
        if row_counts['empty_count'] > 0:
            warnings.append(f"{row_counts['empty_count']} empty rows found")

        result['warnings'] = warnings
        result['success'] = True

        logger.info(f"Validation successful for: {original_filename}")
        return result

    except Exception as e:
        logger.error(f"Validation error: {e}")
        return {
            'success': False,
            'error': str(e),
            'error_code': 'ERR_005',
            'errors': [],
            'warnings': []
        }

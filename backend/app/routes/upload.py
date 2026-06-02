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
from app.utils.error_messages import file_not_csv_error, file_too_large_error
from app.utils.sanitizer import sanitize_filename
from app.utils.temp_files import TempFileManager
from app.utils.preview import format_file_size
from app.logging.upload_log import get_upload_logger
from app.services.validation_service import create_validation_service

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

        # Run validation pipeline using ValidationService
        validation_service = create_validation_service()
        validation_result = validation_service.validate_file(temp_file_path, original_filename)

        if not validation_result.is_valid:
            # Log validation error
            error_message = '; '.join(validation_result.all_errors) if validation_result.all_errors else 'Validation failed'
            upload_logger.log_error(
                original_filename,
                error_message,
                'validation'
            )
            # Cleanup temp file on validation failure
            temp_manager.delete_temp_file(temp_file_path)

            # Return first error to user
            first_error = validation_result.all_errors[0] if validation_result.all_errors else 'Validation failed'
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "ERR_005",
                    "message": first_error,
                    "errors": validation_result.all_errors
                }
            )

        # Log successful validation
        upload_logger.log_validation(
            original_filename,
            validation_result.encoding,
            validation_result.delimiter,
            validation_result.row_counts['data_count'],
            len(validation_result.headers),
            True,
            validation_result.warnings if validation_result.warnings else None
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
                "encoding_detected": validation_result.encoding,
                "encoding_confidence": validation_result.encoding_confidence,
                "delimiter_detected": validation_result.delimiter,
                "headers": validation_result.headers,
                "headers_count": len(validation_result.headers),
                "record_count": validation_result.row_counts['data_count'],
                "warnings": validation_result.warnings
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



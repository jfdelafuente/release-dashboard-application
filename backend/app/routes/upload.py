"""
File Upload Routes
Handles CSV file upload, validation, and processing
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request, Body
from fastapi.responses import JSONResponse
import logging
import json
from pathlib import Path
from datetime import datetime
import shutil
import sys
import uuid

from app.config import Config
from app.utils.error_messages import (
    file_not_csv_error, file_too_large_error, empty_file_error,
    permission_denied_error, disk_full_error, server_error
)
from app.utils.sanitizer import sanitize_filename
from app.utils.temp_files import TempFileManager
from app.utils.preview import format_file_size
from app.upload_logging.upload_log import get_upload_logger
from app.services.validation_service import create_validation_service
from app.services.conversion_service import create_conversion_service

logger = logging.getLogger(__name__)
upload_logger = get_upload_logger()

router = APIRouter(prefix="/api", tags=["upload"])

# Initialize temp file manager
temp_manager = TempFileManager(Config.TEMP_UPLOAD_DIR)

# Create error reports directory
ERROR_REPORTS_DIR = Path(__file__).parent.parent.parent / "logs" / "error_reports"
ERROR_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# In-memory storage of last error for download (limited to recent errors)
last_errors = {}


@router.post("/upload", response_class=JSONResponse)
async def upload_csv(file: UploadFile = File(...), request: Request = None):
    """
    Upload and validate CSV file

    Args:
        file: CSV file from multipart/form-data
        request: Request object to access headers

    Returns:
        JSON with validation results and metadata
    """
    original_filename = file.filename
    temp_file_path = None

    try:
        # Validate file extension
        if not original_filename.lower().endswith('.csv'):
            logger.warning(f"Non-CSV file upload attempted: {original_filename}")
            error = file_not_csv_error()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": error['code'], "message": error['message']}
            )

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate minimum file size (at least has headers) - check BEFORE Content-Length
        if file_size == 0:
            logger.warning(f"Empty file upload: {original_filename}")
            error = empty_file_error()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": error['code'], "message": error['message']}
            )

        # Validate file size
        if file_size > Config.MAX_FILE_SIZE_BYTES:
            logger.warning(
                f"File too large: {original_filename} ({file_size} bytes)"
            )
            error = file_too_large_error(Config.MAX_FILE_SIZE_MB)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={"error": error['code'], "message": error['message']}
            )

        # Note: Content-Length validation is unreliable with multipart/form-data
        # due to the way HTTP clients encode multipart boundaries. The validation
        # service will catch actual data corruption issues, so we skip this check.

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

    finally:
        # CRITICAL: Always cleanup temp file on error
        if temp_file_path is not None:
            # Check if we're in error state (exception was raised)
            exc_info = sys.exc_info()
            if exc_info[0] is not None:  # Exception occurred
                try:
                    if Path(temp_file_path).exists():
                        temp_manager.delete_temp_file(temp_file_path)
                        logger.info(f"Cleaned up temp file after error: {temp_file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup temp file {temp_file_path}: {cleanup_error}")


@router.post("/confirm-upload")
async def confirm_upload(data: dict = Body(...)):
    """
    Confirm upload, move file to input directory, and poll for conversion

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
                detail={
                    "error": "ERR_005",
                    "message": "Missing required fields: temp_file_path, filename"
                }
            )

        temp_file_path = Path(temp_file_path)

        if not temp_file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "ERR_005",
                    "message": "Temporary file not found. Upload session may have expired."
                }
            )

        # Sanitize filename
        safe_filename = sanitize_filename(original_filename)

        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        final_filename = f"{timestamp}_{safe_filename}"

        # Move to input directory
        input_dir = Path(Config.DATA_INPUT_DIR)
        input_dir.mkdir(parents=True, exist_ok=True)

        target_path = input_dir / final_filename

        try:
            # Check disk space before moving (prevent partial writes)
            stat = shutil.disk_usage(target_path.parent)
            required_space = temp_file_path.stat().st_size * 1.5  # 50% buffer for safety

            if stat.free < required_space:
                logger.error(f"Insufficient disk space: {stat.free} bytes available, {required_space} needed")
                upload_logger.log_error(original_filename, f"Disk full: {stat.free} bytes available")
                available = format_file_size(stat.free)
                required = format_file_size(int(required_space))
                error = disk_full_error(available_space=available, required_space=required)
                raise HTTPException(
                    status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
                    detail={"error": error['code'], "message": error['message']}
                )

            # Move file
            temp_file_path.rename(target_path)
            logger.info(f"File moved to input directory: {target_path}")

        except PermissionError as e:
            logger.error(f"Permission denied moving file: {e}")
            upload_logger.log_error(original_filename, f"Permission denied: {e}")
            error = permission_denied_error()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": error['code'], "message": error['message']}
            )

        except FileNotFoundError as e:
            logger.error(f"Temp file not found: {e}")
            upload_logger.log_error(original_filename, f"File not found: {e}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "ERR_005",
                    "message": "Temporary file not found. Upload session may have expired."
                }
            )

        except OSError as e:
            # Catch other OS errors (network drive issues, readonly filesystem, etc.)
            logger.error(f"OS error moving file: {e}")
            upload_logger.log_error(original_filename, f"OS error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "ERR_012",
                    "message": f"Error del sistema de archivos: {str(e)}"
                }
            )

        except HTTPException:
            # Re-raise HTTP exceptions (our custom ones from above)
            raise

        except Exception as e:
            # Fallback for truly unexpected errors
            logger.exception(f"Unexpected error moving file: {e}")
            upload_logger.log_error(original_filename, f"Unexpected error: {e}")
            error = server_error()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": error['code'], "message": error['message']}
            )

        # Log file movement
        upload_logger.log_upload({
            'filename': original_filename,
            'final_filename': final_filename,
            'status': 'moved_to_input',
            'timestamp': datetime.utcnow().isoformat()
        })

        logger.info(f"Starting conversion for: {final_filename}")

        # Execute conversion directly (synchronously)
        try:
            # Add converters/src to path so we can import csv_to_json
            # From: backend/app/routes/upload.py -> go up 3 levels to project root
            converters_src = Path(__file__).parent.parent.parent / "converters" / "src"
            if str(converters_src) not in sys.path:
                sys.path.insert(0, str(converters_src))

            from csv_to_json import CsvToJsonConverter

            converter = CsvToJsonConverter()
            input_path = target_path  # The file we just moved

            # Generate output filename
            output_filename = f"{final_filename.rsplit('.', 1)[0]}-massive.json"
            output_path = Path(Config.DATA_OUTPUT_DIR) / output_filename
            error_path = Path(Config.DATA_ERROR_DIR) / f"{final_filename.rsplit('.', 1)[0]}_errors.json"

            # Convert CSV to JSON
            success, report = converter.convert_file(
                str(input_path.resolve()),
                str(output_path.resolve()),
                str(error_path.resolve())
            )

            conversion_result = {
                'success': success,
                'output_file': str(output_path),
                'record_count': report['stats'].get('successful', 0),
                'message': 'Conversion completed successfully' if success else 'Conversion completed with warnings',
                'status': 'completed',
                'elapsed_seconds': 0
            }

            logger.info(f"Conversion completed: {output_filename}, records: {conversion_result['record_count']}")

        except Exception as e:
            logger.error(f"Error during conversion: {e}", exc_info=True)
            conversion_result = {
                'success': False,
                'output_file': None,
                'record_count': 0,
                'message': f"Conversion error: {str(e)}",
                'status': 'error',
                'elapsed_seconds': 0
            }

        # Log conversion result
        if conversion_result['success']:
            upload_logger.log_completion(
                original_filename,
                conversion_result.get('output_file', ''),
                conversion_result.get('record_count', 0)
            )

            # Update index.json to include the new file
            try:
                import importlib.util
                # Build absolute path from project root to build_index.py
                project_root = Path(__file__).parent.parent.parent.parent  # From backend/app/routes/upload.py to project root
                build_index_path = project_root / "converters" / "cli" / "build_index.py"

                logger.info(f"Loading build_index from: {build_index_path}")

                if not build_index_path.exists():
                    logger.error(f"build_index.py not found at: {build_index_path}")
                else:
                    spec = importlib.util.spec_from_file_location("build_index", str(build_index_path))
                    build_index_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(build_index_module)

                    # Use absolute path for output directory
                    output_dir_abs = project_root / "data" / "output"

                    logger.info(f"Calling build_index with: {output_dir_abs}")
                    result = build_index_module.build_index(str(output_dir_abs))

                    if result:
                        logger.info(f"[SUCCESS] index.json updated successfully")
                    else:
                        logger.error(f"[ERROR] build_index returned False")

            except Exception as e:
                logger.error(f"[ERROR] Could not update index.json: {e}", exc_info=True)

        else:
            upload_logger.log_error(
                original_filename,
                conversion_result.get('message', 'Conversion failed')
            )

        return {
            "success": conversion_result['success'],
            "message": conversion_result.get('message', 'Processing complete'),
            "final_filename": final_filename,
            "status": conversion_result['status'],
            "conversion": {
                "output_file": conversion_result.get('output_file'),
                "record_count": conversion_result.get('record_count', 0),
                "elapsed_seconds": conversion_result.get('elapsed_seconds', 0)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming upload: {e}", exc_info=True)
        error = server_error()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": error['code'], "message": error['message']}
        )


@router.get("/index-json")
async def get_index_json():
    """
    Get the index.json file with list of converted files
    Used by frontend to load latest data
    """
    try:
        index_path = Path(Config.DATA_OUTPUT_DIR) / "index.json"

        if not index_path.exists():
            # Return empty index if file doesn't exist yet
            return {
                "massive": {"files": []},
                "postmortem": {"files": []}
            }

        with open(index_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    except Exception as e:
        logger.error(f"Error reading index.json: {e}")
        return {
            "massive": {"files": []},
            "postmortem": {"files": []}
        }


@router.get("/data-json")
async def get_data_json(file: str):
    """
    Get a specific JSON data file from output directory
    Used by frontend to load incident data
    """
    try:
        # Sanitize filename to prevent path traversal
        safe_filename = file.split('/')[-1]  # Get only the filename
        if '..' in safe_filename or '/' in safe_filename or '\\' in safe_filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "ERR_005", "message": "Invalid filename"}
            )

        file_path = Path(Config.DATA_OUTPUT_DIR) / safe_filename

        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "ERR_005", "message": "File not found"}
            )

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading data file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "ERR_012", "message": "Error reading data file"}
        )


@router.get("/error-report/{report_id}")
async def download_error_report(report_id: str):
    """
    Download detailed error report for troubleshooting

    Args:
        report_id: Unique identifier for the error report

    Returns:
        JSON with error details and troubleshooting steps
    """
    try:
        # Try to find error report in memory first
        if report_id in last_errors:
            error_report = last_errors[report_id]
            return JSONResponse(
                content=error_report,
                headers={
                    "Content-Disposition": f"attachment; filename=error-report-{report_id}.json"
                }
            )

        # Try to find error report file
        report_file = ERROR_REPORTS_DIR / f"{report_id}.json"
        if report_file.exists():
            with open(report_file, 'r', encoding='utf-8') as f:
                error_report = json.load(f)
            return JSONResponse(
                content=error_report,
                headers={
                    "Content-Disposition": f"attachment; filename=error-report-{report_id}.json"
                }
            )

        # Report not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "ERR_999",
                "message": "Error report not found. The report may have expired."
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading error report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving error report"
        )


def generate_error_report(upload_id: str, error_code: str, error_message: str,
                         original_filename: str = None, technical_details: str = None) -> dict:
    """
    Generate a detailed error report for admin debugging

    Args:
        upload_id: Unique upload identifier
        error_code: Error code (ERR_XXX)
        error_message: User-friendly error message
        original_filename: Original filename that caused the error
        technical_details: Technical error details for debugging

    Returns:
        Dictionary with error report
    """
    report = {
        "upload_id": upload_id,
        "timestamp": datetime.utcnow().isoformat(),
        "error_details": {
            "error_code": error_code,
            "error_message": error_message,
            "original_filename": original_filename,
            "technical_details": technical_details or ""
        },
        "troubleshooting_steps": get_troubleshooting_steps(error_code),
        "system_info": {
            "temp_upload_dir": str(Config.TEMP_UPLOAD_DIR),
            "data_input_dir": str(Config.DATA_INPUT_DIR),
            "data_output_dir": str(Config.DATA_OUTPUT_DIR),
            "max_file_size_mb": Config.MAX_FILE_SIZE_MB,
            "timestamp": datetime.utcnow().isoformat()
        },
        "help_url": f"https://docs.example.com/es/errores/{error_code.lower()}"
    }

    # Store in memory (keep only last 50 errors)
    last_errors[upload_id] = report
    if len(last_errors) > 50:
        oldest_key = next(iter(last_errors))
        del last_errors[oldest_key]

    # Also save to file for persistence
    try:
        report_file = ERROR_REPORTS_DIR / f"{upload_id}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Failed to save error report to file: {e}")

    return report


def get_troubleshooting_steps(error_code: str) -> list:
    """
    Get troubleshooting steps for a specific error code

    Args:
        error_code: Error code (ERR_XXX)

    Returns:
        List of troubleshooting steps in Spanish
    """
    troubleshooting = {
        'ERR_001': [
            "Verifica que el archivo CSV incluye todas las columnas requeridas",
            "Compara la estructura de tu archivo con un archivo de ejemplo válido",
            "Asegúrate de que los nombres de las columnas coinciden exactamente (incluyendo mayúsculas)"
        ],
        'ERR_002': [
            "Convierte el archivo a UTF-8 usando Excel o tu editor de texto preferido",
            "En Excel: Guardar como > CSV UTF-8",
            "En Google Sheets: Descargar como CSV (automáticamente UTF-8)"
        ],
        'ERR_005': [
            "Verifica que el archivo no está corrompido",
            "Intenta abrir el archivo en un editor de texto",
            "Si el error persiste, descarga el archivo de nuevo desde la fuente original"
        ],
        'ERR_006': [
            f"El archivo excede el tamaño máximo permitido",
            "Divide el archivo en partes más pequeñas",
            "Comprime el archivo usando ZIP"
        ],
        'ERR_007': [
            "Verifica que el archivo tiene extensión .csv",
            "Si el archivo está guardado como .xlsx o .txt, cámbialo a .csv",
            "No uses formatos como Excel (.xlsx) o LibreOffice (.ods)"
        ],
        'ERR_008': [
            "Verifica que el archivo no está vacío",
            "Asegúrate de que el archivo contiene datos"
        ],
        'ERR_011': [
            "Verifica tu conexión a internet",
            "Intenta de nuevo en unos momentos",
            "Si el problema persiste, contacta con soporte técnico"
        ],
        'ERR_012': [
            "El servidor está experimentando problemas",
            "Intenta de nuevo en unos momentos",
            "Si el error persiste, contacta con el equipo de soporte"
        ],
        'ERR_013': [
            "El sistema no tiene permisos de escritura en el directorio de procesamiento",
            "Contacta con el administrador del sistema",
            "El administrador debe ejecutar: chmod 755 data/input/"
        ],
        'ERR_014': [
            "No hay espacio suficiente en el disco duro",
            "El administrador debe liberar espacio en el disco",
            "Contacta con el equipo de soporte técnico"
        ]
    }

    return troubleshooting.get(error_code, [
        "Verifica los detalles del error",
        "Contacta con el equipo de soporte técnico si el problema persiste"
    ])

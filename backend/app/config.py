"""
Configuration handler for CSV Upload API
Loads and validates environment variables
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load .env file
env_file = Path(__file__).parent.parent / ".env"
load_dotenv(env_file)


class Config:
    """Application configuration from environment variables"""

    # Server configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # CORS configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")

    # File upload configuration
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

    # Directory configuration
    TEMP_UPLOAD_DIR = os.getenv("TEMP_UPLOAD_DIR", "temp_uploads")
    DATA_INPUT_DIR = os.getenv("DATA_INPUT_DIR", "../data/input")
    DATA_OUTPUT_DIR = os.getenv("DATA_OUTPUT_DIR", "../data/output")
    DATA_ERROR_DIR = os.getenv("DATA_ERROR_DIR", "../data/errors")

    # Create directories if they don't exist
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        dirs = [cls.TEMP_UPLOAD_DIR, cls.DATA_INPUT_DIR, cls.DATA_OUTPUT_DIR, cls.DATA_ERROR_DIR]
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory ready: {dir_path}")

    # CSV Configuration
    SUPPORTED_ENCODINGS = os.getenv(
        "SUPPORTED_ENCODINGS",
        "utf-8,utf-8-sig,windows-1252,latin-1,iso-8859-15"
    ).split(",")

    SUPPORTED_DELIMITERS = os.getenv("SUPPORTED_DELIMITERS", ",;\\t").split(";")

    REQUIRED_HEADERS = os.getenv(
        "REQUIRED_HEADERS",
        "ID de incidencia,Estatus,Fecha de envío,Grupo asignado,Urgencia,Impacto,Descripción"
    ).split(",")

    # Temp file cleanup
    TEMP_FILE_CLEANUP_AGE_HOURS = int(os.getenv("TEMP_FILE_CLEANUP_AGE_HOURS", "1"))
    TEMP_FILE_CLEANUP_INTERVAL_MINUTES = int(os.getenv("TEMP_FILE_CLEANUP_INTERVAL_MINUTES", "30"))

    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """Validate critical configuration"""
        errors = []

        # Validate directories are writable
        for dir_path in [cls.TEMP_UPLOAD_DIR, cls.DATA_INPUT_DIR]:
            p = Path(dir_path)
            if not p.exists():
                try:
                    p.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create directory {dir_path}: {e}")
            elif not os.access(str(p), os.W_OK):
                errors.append(f"Directory not writable: {dir_path}")

        # Validate max file size
        if cls.MAX_FILE_SIZE_MB <= 0:
            errors.append("MAX_FILE_SIZE_MB must be > 0")

        if errors:
            logger.error(f"Configuration validation failed: {errors}")
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")

        logger.info("Configuration validated successfully")
        return True

    @classmethod
    def to_dict(cls):
        """Return configuration as dictionary (for logging/debugging)"""
        return {
            "HOST": cls.HOST,
            "PORT": cls.PORT,
            "DEBUG": cls.DEBUG,
            "CORS_ORIGINS": cls.CORS_ORIGINS,
            "MAX_FILE_SIZE_MB": cls.MAX_FILE_SIZE_MB,
            "TEMP_UPLOAD_DIR": cls.TEMP_UPLOAD_DIR,
            "DATA_INPUT_DIR": cls.DATA_INPUT_DIR,
            "DATA_OUTPUT_DIR": cls.DATA_OUTPUT_DIR,
            "SUPPORTED_ENCODINGS": cls.SUPPORTED_ENCODINGS,
            "REQUIRED_HEADERS": cls.REQUIRED_HEADERS,
        }


def get_config():
    """Get the global configuration instance"""
    return Config

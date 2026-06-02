"""
Error Message Generator
Creates user-friendly error messages in Spanish
"""

from typing import List, Optional, Dict
import logging

logger = logging.getLogger(__name__)

# Error message templates
ERROR_TEMPLATES = {
    'missing_headers': 'Columnas requeridas faltantes: {columns}. Por favor verifica que tu archivo CSV incluya estas columnas.',
    'unsupported_encoding': 'La codificación "{encoding}" no está soportada. Por favor convierte el archivo a UTF-8.',
    'delimiter_not_detected': 'No se pudo detectar el delimitador CSV. Por favor usa coma (,), punto y coma (;) o tabulación.',
    'no_data_rows': 'No se encontraron filas de datos en el archivo CSV. Asegúrate de que los datos comienzan debajo de los encabezados.',
    'invalid_file': 'El archivo no es un CSV válido.',
    'file_too_large': 'El archivo excede el tamaño máximo de {max_size}MB.',
    'file_not_csv': 'El archivo debe tener extensión .csv.',
    'empty_file': 'El archivo está vacío.',
    'invalid_date': 'La fecha "{value}" en la columna "{column}" tiene un formato inválido.',
    'invalid_enum': 'El valor "{value}" en la columna "{column}" no es válido. Valores permitidos: {allowed}.',
    'network_error': 'Error de conexión. Por favor verifica tu conexión a internet e intenta de nuevo.',
    'server_error': 'Error del servidor. Por favor intenta de nuevo más tarde.',
    'permission_denied': 'No tienes permisos de escritura en el directorio de procesamiento. Contacta con el administrador del sistema.',
    'disk_full': 'Espacio en disco insuficiente ({available_space} disponible). Se requieren {required_space}. Libera espacio e intenta de nuevo.',
}

# Error codes for frontend
ERROR_CODES = {
    'MISSING_HEADERS': 'ERR_001',
    'UNSUPPORTED_ENCODING': 'ERR_002',
    'DELIMITER_NOT_DETECTED': 'ERR_003',
    'NO_DATA_ROWS': 'ERR_004',
    'INVALID_FILE': 'ERR_005',
    'FILE_TOO_LARGE': 'ERR_006',
    'FILE_NOT_CSV': 'ERR_007',
    'EMPTY_FILE': 'ERR_008',
    'INVALID_DATE': 'ERR_009',
    'INVALID_ENUM': 'ERR_010',
    'NETWORK_ERROR': 'ERR_011',
    'SERVER_ERROR': 'ERR_012',
    'PERMISSION_DENIED': 'ERR_013',
    'DISK_FULL': 'ERR_014',
}

# Help documentation links (TODO: Update with actual documentation URLs)
ERROR_HELP_LINKS = {
    'ERR_001': 'https://docs.example.com/es/errores/columnas-faltantes',
    'ERR_002': 'https://docs.example.com/es/errores/encoding',
    'ERR_003': 'https://docs.example.com/es/errores/delimitador',
    'ERR_004': 'https://docs.example.com/es/errores/datos-vacios',
    'ERR_005': 'https://docs.example.com/es/errores/archivo-invalido',
    'ERR_006': 'https://docs.example.com/es/errores/tamaño-maximo',
    'ERR_007': 'https://docs.example.com/es/errores/no-csv',
    'ERR_008': 'https://docs.example.com/es/errores/archivo-vacio',
    'ERR_009': 'https://docs.example.com/es/errores/fecha-invalida',
    'ERR_010': 'https://docs.example.com/es/errores/valor-invalido',
    'ERR_011': 'https://docs.example.com/es/errores/conexion',
    'ERR_012': 'https://docs.example.com/es/errores/servidor',
    'ERR_013': 'https://docs.example.com/es/errores/permisos',
    'ERR_014': 'https://docs.example.com/es/errores/espacio-disco',
}


def get_error_message(error_key: str, **kwargs) -> str:
    """
    Get formatted error message

    Args:
        error_key: Key of error message template
        **kwargs: Parameters to format into message

    Returns:
        Formatted error message in Spanish
    """
    template = ERROR_TEMPLATES.get(error_key, 'Error desconocido.')
    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.warning(f"Missing parameter in error template '{error_key}': {e}")
        return template


def missing_headers_error(columns: List[str]) -> Dict[str, str]:
    """Generate missing headers error"""
    return {
        'code': ERROR_CODES['MISSING_HEADERS'],
        'message': get_error_message('missing_headers', columns=', '.join(columns))
    }


def unsupported_encoding_error(encoding: str) -> Dict[str, str]:
    """Generate unsupported encoding error"""
    return {
        'code': ERROR_CODES['UNSUPPORTED_ENCODING'],
        'message': get_error_message('unsupported_encoding', encoding=encoding)
    }


def delimiter_not_detected_error() -> Dict[str, str]:
    """Generate delimiter detection error"""
    return {
        'code': ERROR_CODES['DELIMITER_NOT_DETECTED'],
        'message': get_error_message('delimiter_not_detected')
    }


def no_data_rows_error() -> Dict[str, str]:
    """Generate no data rows error"""
    return {
        'code': ERROR_CODES['NO_DATA_ROWS'],
        'message': get_error_message('no_data_rows')
    }


def invalid_file_error(detail: Optional[str] = None) -> Dict[str, str]:
    """Generate invalid file error"""
    message = get_error_message('invalid_file')
    if detail:
        message += f' ({detail})'
    return {
        'code': ERROR_CODES['INVALID_FILE'],
        'message': message
    }


def file_too_large_error(max_size: int) -> Dict[str, str]:
    """Generate file too large error"""
    return {
        'code': ERROR_CODES['FILE_TOO_LARGE'],
        'message': get_error_message('file_too_large', max_size=max_size)
    }


def file_not_csv_error() -> Dict[str, str]:
    """Generate file not CSV error"""
    return {
        'code': ERROR_CODES['FILE_NOT_CSV'],
        'message': get_error_message('file_not_csv')
    }


def empty_file_error() -> Dict[str, str]:
    """Generate empty file error"""
    return {
        'code': ERROR_CODES['EMPTY_FILE'],
        'message': get_error_message('empty_file')
    }


def invalid_date_error(value: str, column: str) -> Dict[str, str]:
    """Generate invalid date error"""
    return {
        'code': ERROR_CODES['INVALID_DATE'],
        'message': get_error_message('invalid_date', value=value, column=column)
    }


def invalid_enum_error(value: str, column: str, allowed: List[str]) -> Dict[str, str]:
    """Generate invalid enum value error"""
    return {
        'code': ERROR_CODES['INVALID_ENUM'],
        'message': get_error_message(
            'invalid_enum',
            value=value,
            column=column,
            allowed=', '.join(allowed)
        )
    }


def network_error() -> Dict[str, str]:
    """Generate network error"""
    return {
        'code': ERROR_CODES['NETWORK_ERROR'],
        'message': get_error_message('network_error')
    }


def server_error() -> Dict[str, str]:
    """Generate server error"""
    return {
        'code': ERROR_CODES['SERVER_ERROR'],
        'message': get_error_message('server_error')
    }


def permission_denied_error() -> Dict[str, str]:
    """Generate permission denied error"""
    return {
        'code': ERROR_CODES['PERMISSION_DENIED'],
        'message': get_error_message('permission_denied')
    }


def disk_full_error(available_space: str = 'desconocido', required_space: str = 'desconocido') -> Dict[str, str]:
    """Generate disk full error with space information"""
    return {
        'code': ERROR_CODES['DISK_FULL'],
        'message': get_error_message(
            'disk_full',
            available_space=available_space,
            required_space=required_space
        )
    }


def format_error_response(error: Dict[str, str]) -> Dict:
    """
    Format error for API response

    Args:
        error: Error dict with code and message

    Returns:
        Formatted error response with help link
    """
    error_code = error.get('code', 'UNKNOWN')
    return {
        'error': error_code,
        'message': error.get('message', 'Error desconocido'),
        'help_url': ERROR_HELP_LINKS.get(error_code)
    }

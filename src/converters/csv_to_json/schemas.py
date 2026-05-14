"""
Field schemas and validation rules for incident records.

Defines the structure, validation rules, and allowed values for each incident field.
"""
from __future__ import annotations

# Required fields for all incident records
REQUIRED_FIELDS = {
    "ID de incidencia",
    "Descripción",
    "Estatus",
    "Fecha de envío",
    "Grupo asignado",
    "Urgencia",
    "Impacto"
}

# Allowed values for enum fields
ALLOWED_VALUES = {
    "Estatus": [
        "Abierto",
        "Pendiente",
        "En Progreso",
        "En Curso",
        "Asignado",
        "Resuelto",
        "Cerrado",
        "Cancelado"
    ],
    "Urgencia": [
        "Baja",
        "Medio",
        "Alta",
        "Crítica"
    ],
    "Impacto": [
        "Masiva"
    ]
}

# Field validation configuration
FIELD_VALIDATORS = {
    "ID de incidencia": {
        "required": True,
        "type": "text",
        "max_length": 50
    },
    "Prioridad": {
        "required": False,
        "type": "text",
        "max_length": 100
    },
    "Descripción": {
        "required": True,
        "type": "text",
        "max_length": 5000
    },
    "Estatus": {
        "required": True,
        "type": "enum",
        "allowed_values": ALLOWED_VALUES["Estatus"]
    },
    "Fecha de envío": {
        "required": True,
        "type": "datetime",
        "format": "%d/%m/%Y %I:%M %p"
    },
    "Grupo asignado": {
        "required": True,
        "type": "text",
        "max_length": 200
    },
    "Fecha de última resolución": {
        "required": False,
        "type": "datetime",
        "format": "%d/%m/%Y %I:%M %p"
    },
    "Grupo Resolutor": {
        "required": False,
        "type": "text",
        "max_length": 200
    },
    "Urgencia": {
        "required": True,
        "type": "enum",
        "allowed_values": ALLOWED_VALUES["Urgencia"]
    },
    "Impacto": {
        "required": True,
        "type": "enum",
        "allowed_values": ALLOWED_VALUES["Impacto"]
    },
    "Grupo Remitente": {
        "required": False,
        "type": "text",
        "max_length": 200
    }
}

# Date/time format for parsing and output
DATE_FORMAT = "%d/%m/%Y %I:%M %p"

# Fields that need normalization
NORMALIZE_FIELDS = {
    "Estatus": "title_case",
    "Urgencia": "extract_text_and_title_case",
    "Impacto": "title_case"
}

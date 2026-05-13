#!/usr/bin/env python3
"""
Script de validación de KPIs entre Dashboard Hub y Massive Incidents Dashboard.
Compara los valores calculados para asegurar que coinciden después del fix.
"""

import json
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta

# Fix Unicode encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_json(file_path):
    """Carga el archivo JSON."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both formats (with metadata and without)
    if isinstance(data, dict) and '_metadata' in data:
        return data['data']
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("Formato de JSON no reconocido")

def parse_date(date_str):
    """
    Convierte fecha en formato 'dd/mm/yyyy HH:mm a/p' a datetime.
    Usa la MISMA LÓGICA que el Dashboard de Masivas: solo extrae día/mes/año.
    """
    try:
        # Remove extra spaces
        date_str = date_str.strip()

        # Format: "17/03/2025 18:44 a" - only extract date part
        date_part = date_str.split()[0]  # Get "17/03/2025"
        day, month, year = date_part.split('/')

        dt = datetime(int(year), int(month), int(day))

        return dt
    except Exception as e:
        return None

def calculate_kpis(incidents):
    """Calcula los KPIs usando la misma lógica que ambos dashboards."""

    # Total incidents
    total_incidents = len(incidents)

    # Pending incidents (NOT closed/resolved/cancelled)
    # Using same logic as Massive Incidents Dashboard: check if status INCLUDES these words
    pending_incidents = [
        i for i in incidents
        if (i.get('Estatus', '').lower() not in ['cerrado', 'resuelto', 'cancelado'])
    ]
    pending_count = len(pending_incidents)

    print(f"Total incidencias: {total_incidents}")
    print(f"Incidencias pendientes (HOY): {pending_count}")

    # Calculate trends
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    dates_7_ago = today - timedelta(days=7)
    dates_15_ago = today - timedelta(days=15)
    dates_30_ago = today - timedelta(days=30)

    # Count pending incidents at different dates
    pending_7_days_ago = count_pending_at_date(incidents, dates_7_ago)
    pending_15_days_ago = count_pending_at_date(incidents, dates_15_ago)
    pending_30_days_ago = count_pending_at_date(incidents, dates_30_ago)

    # Calculate trend percentages
    trend_7_day = calculate_trend_percentage(pending_7_days_ago, pending_count)
    trend_15_day = calculate_trend_percentage(pending_15_days_ago, pending_count)
    trend_30_day = calculate_trend_percentage(pending_30_days_ago, pending_count)

    print(f"\nTendencia 7 días: {trend_7_day:.1f}%")
    print(f"Tendencia 15 días: {trend_15_day:.1f}%")
    print(f"Tendencia 30 días: {trend_30_day:.1f}%")

    return {
        'total': total_incidents,
        'pending': pending_count,
        'trend_7_day': trend_7_day,
        'trend_15_day': trend_15_day,
        'trend_30_day': trend_30_day
    }

def count_pending_at_date(incidents, target_date):
    """
    Cuenta incidencias que estaban ABIERTAS en una fecha específica.
    Usa MISMA lógica que Dashboard de Masivas:
    - Abierta si: fue creada antes de target_date Y (no está cerrada O se cerró después de target_date)
    """
    count = 0
    for i in incidents:
        date_str = i.get('Fecha de envío', '')
        incident_date = parse_date(date_str)

        if incident_date is None:
            continue

        # Solo contar si la incidencia fue creada en o antes de la fecha objetivo
        if incident_date > target_date:
            continue

        status = i.get('Estatus', '').lower()

        # Si está cerrada, verificar si se cerró DESPUÉS de la fecha objetivo
        if status in ['cerrado', 'resuelto', 'cancelado']:
            resolve_str = i.get('Fecha de última resolución', '')
            if resolve_str:
                resolve_date = parse_date(resolve_str)
                if resolve_date:
                    # Estaba abierta en target_date si se resolvió DESPUÉS
                    if resolve_date > target_date:
                        count += 1
            # Sin fecha de resolución = estaba cerrada
        else:
            # No está cerrada = estaba abierta en target_date
            count += 1

    return count

def calculate_trend_percentage(count_at_date, current_count):
    """Calcula porcentaje de cambio entre dos períodos."""
    if count_at_date == 0:
        if current_count == 0:
            return 0.0
        return 100.0

    return ((current_count - count_at_date) / count_at_date) * 100

if __name__ == '__main__':
    json_file = Path('data/output/CS_Masiva_20260513-massive.json')

    if not json_file.exists():
        print(f"❌ Archivo no encontrado: {json_file}")
        sys.exit(1)

    print("=" * 60)
    print("VALIDACIÓN DE KPIs - Dashboard Hub vs Massive Incidents")
    print("=" * 60)
    print(f"\nCargando: {json_file}")

    try:
        incidents = load_json(json_file)
        print(f"✓ Loaded {len(incidents)} incidents\n")

        kpis = calculate_kpis(incidents)

        print("\n" + "=" * 60)
        print("RESULTADOS CALCULADOS")
        print("=" * 60)
        print(f"Total:               {kpis['total']}")
        print(f"Pendientes:          {kpis['pending']}")
        print(f"Tendencia 7d:        {kpis['trend_7_day']:>7.1f}%")
        print(f"Tendencia 15d:       {kpis['trend_15_day']:>7.1f}%")
        print(f"Tendencia 30d:       {kpis['trend_30_day']:>7.1f}%")

        print("\n⚠️  PRÓXIMO PASO:")
        print("   1. Abre 'massive-incidents-dashboard.html' en el navegador")
        print("   2. Carga manualmente el archivo: CS_Masiva_20260513-massive.json")
        print("   3. Verifica que estos valores coinciden con los que aparecen en el dashboard")
        print("   4. Compara especialmente las TENDENCIAS (7d, 15d, 30d)")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

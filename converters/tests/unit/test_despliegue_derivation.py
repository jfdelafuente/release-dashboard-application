#!/usr/bin/env python3
"""
Unit tests for Despliegue derivation logic.

Tests derivateDespliegue() function with PAP/MESA assignment based on oldest date.
"""

import pytest
from csv_to_json.postmortem_schemas import PostmortemRecord, derivateDespliegue


class TestDespliegueDerivation:
    """Test Despliegue field derivation logic."""

    def test_simple_pap_mesa_assignment(self):
        """Test basic PAP/MESA assignment with two records."""
        records = [
            PostmortemRecord({
                'ID de incidencia': 'INC001',
                'Fecha de envío': '01/05/2026',
                'Fecha de notificación': '02/05/2026',
                'Fecha de última resolución': '03/05/2026'
            }),
            PostmortemRecord({
                'ID de incidencia': 'INC002',
                'Fecha de envío': '10/05/2026',
                'Fecha de notificación': '11/05/2026',
                'Fecha de última resolución': '12/05/2026'
            })
        ]

        despliegue = derivateDespliegue(records)

        # INC001 has earliest date (01/05) -> PAP
        assert despliegue['INC001'] == 'PAP'
        # INC002 has later dates -> MESA
        assert despliegue['INC002'] == 'MESA'

    def test_pap_from_multiple_dates(self):
        """Test PAP assignment based on earliest across all three date fields."""
        records = [
            PostmortemRecord({
                'ID de incidencia': 'INC001',
                'Fecha de envío': '10/05/2026',
                'Fecha de notificación': '01/05/2026',  # Earliest in second field
                'Fecha de última resolución': '15/05/2026'
            }),
            PostmortemRecord({
                'ID de incidencia': 'INC002',
                'Fecha de envío': '05/05/2026',
                'Fecha de notificación': '06/05/2026',
                'Fecha de última resolución': '07/05/2026'
            })
        ]

        despliegue = derivateDespliegue(records)

        # INC001 has earliest date across fields (01/05) -> PAP
        assert despliegue['INC001'] == 'PAP'
        assert despliegue['INC002'] == 'MESA'

    def test_identical_dates_first_gets_pap(self):
        """Test when all dates are identical, first record gets PAP."""
        records = [
            PostmortemRecord({
                'ID de incidencia': 'INC001',
                'Fecha de envío': '05/05/2026',
                'Fecha de notificación': '05/05/2026',
                'Fecha de última resolución': '05/05/2026'
            }),
            PostmortemRecord({
                'ID de incidencia': 'INC002',
                'Fecha de envío': '05/05/2026',
                'Fecha de notificación': '05/05/2026',
                'Fecha de última resolución': '05/05/2026'
            })
        ]

        despliegue = derivateDespliegue(records)

        # First record with identical dates should get PAP
        assert despliegue['INC001'] == 'PAP'
        assert despliegue['INC002'] == 'MESA'

    def test_missing_date_fields(self):
        """Test with missing/empty date fields."""
        records = [
            PostmortemRecord({
                'ID de incidencia': 'INC001',
                'Fecha de envío': '',  # Empty
                'Fecha de notificación': '02/05/2026',
                'Fecha de última resolución': '03/05/2026'
            }),
            PostmortemRecord({
                'ID de incidencia': 'INC002',
                'Fecha de envío': '05/05/2026',
                'Fecha de notificación': '06/05/2026',
                'Fecha de última resolución': '07/05/2026'
            })
        ]

        despliegue = derivateDespliegue(records)

        # INC001 still has 02/05 in notificación field -> PAP
        assert despliegue['INC001'] == 'PAP'
        assert despliegue['INC002'] == 'MESA'

    def test_unparseable_dates(self):
        """Test with unparseable date values."""
        records = [
            PostmortemRecord({
                'ID de incidencia': 'INC001',
                'Fecha de envío': 'INVALID_DATE',
                'Fecha de notificación': '02/05/2026',
                'Fecha de última resolución': '03/05/2026'
            }),
            PostmortemRecord({
                'ID de incidencia': 'INC002',
                'Fecha de envío': '05/05/2026',
                'Fecha de notificación': '06/05/2026',
                'Fecha de última resolución': '07/05/2026'
            })
        ]

        despliegue = derivateDespliegue(records)

        # INC001 still has 02/05 despite first field being unparseable -> PAP
        assert despliegue['INC001'] == 'PAP'
        assert despliegue['INC002'] == 'MESA'

    def test_all_dates_missing(self):
        """Test when all date fields are missing for all records."""
        records = [
            PostmortemRecord({
                'ID de incidencia': 'INC001',
                'Fecha de envío': '',
                'Fecha de notificación': '',
                'Fecha de última resolución': ''
            }),
            PostmortemRecord({
                'ID de incidencia': 'INC002',
                'Fecha de envío': '',
                'Fecha de notificación': '',
                'Fecha de última resolución': ''
            })
        ]

        despliegue = derivateDespliegue(records)

        # First record should get PAP if no dates exist
        assert despliegue['INC001'] == 'PAP'
        assert despliegue['INC002'] == 'MESA'

    def test_single_record(self):
        """Test with single record."""
        records = [
            PostmortemRecord({
                'ID de incidencia': 'INC001',
                'Fecha de envío': '05/05/2026',
                'Fecha de notificación': '06/05/2026',
                'Fecha de última resolución': '07/05/2026'
            })
        ]

        despliegue = derivateDespliegue(records)

        # Single record should always get PAP
        assert despliegue['INC001'] == 'PAP'

    def test_empty_records_list(self):
        """Test with empty records list."""
        records = []
        despliegue = derivateDespliegue(records)
        assert len(despliegue) == 0

    def test_three_records_pap_assigned_correctly(self):
        """Test PAP assigned correctly with three records."""
        records = [
            PostmortemRecord({
                'ID de incidencia': 'INC001',
                'Fecha de envío': '15/05/2026',
                'Fecha de notificación': '16/05/2026',
                'Fecha de última resolución': '17/05/2026'
            }),
            PostmortemRecord({
                'ID de incidencia': 'INC002',
                'Fecha de envío': '01/05/2026',  # Earliest
                'Fecha de notificación': '02/05/2026',
                'Fecha de última resolución': '03/05/2026'
            }),
            PostmortemRecord({
                'ID de incidencia': 'INC003',
                'Fecha de envío': '10/05/2026',
                'Fecha de notificación': '11/05/2026',
                'Fecha de última resolución': '12/05/2026'
            })
        ]

        despliegue = derivateDespliegue(records)

        # INC002 has earliest date (01/05) -> PAP
        assert despliegue['INC002'] == 'PAP'
        # Others are MESA
        assert despliegue['INC001'] == 'MESA'
        assert despliegue['INC003'] == 'MESA'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

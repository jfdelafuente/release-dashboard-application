#!/usr/bin/env python3
"""
Unit tests for Despliegue derivation logic.

Tests derivateDespliegue() function: PAP/MESA assignment based on the
oldest 'Fecha de envío' (the PAP deployment day) — ALL records sharing
that date get PAP, not just the first one found.
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

    def test_pap_based_only_on_fecha_envio(self):
        """Test that PAP is decided only by 'Fecha de envío', ignoring other date fields."""
        records = [
            PostmortemRecord({
                'ID de incidencia': 'INC001',
                'Fecha de envío': '10/05/2026',
                'Fecha de notificación': '01/05/2026',  # Earliest, but irrelevant now
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

        # INC002 has the earliest 'Fecha de envío' (05/05) -> PAP
        assert despliegue['INC002'] == 'PAP'
        # INC001's 'Fecha de envío' (10/05) is later, despite an earlier date in another field -> MESA
        assert despliegue['INC001'] == 'MESA'

    def test_identical_dates_all_get_pap(self):
        """Test that ALL records sharing the deployment day's 'Fecha de envío' get PAP, not just the first."""
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
            }),
            PostmortemRecord({
                'ID de incidencia': 'INC003',
                'Fecha de envío': '06/05/2026',
                'Fecha de notificación': '05/05/2026',
                'Fecha de última resolución': '05/05/2026'
            })
        ]

        despliegue = derivateDespliegue(records)

        # INC001 and INC002 share the earliest 'Fecha de envío' (05/05) -> both PAP
        assert despliegue['INC001'] == 'PAP'
        assert despliegue['INC002'] == 'PAP'
        # INC003's 'Fecha de envío' is later (06/05) -> MESA
        assert despliegue['INC003'] == 'MESA'

    def test_missing_fecha_envio(self):
        """Test that a record with an empty 'Fecha de envío' cannot be matched as PAP."""
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

        # INC001 has no 'Fecha de envío' to compare -> MESA
        assert despliegue['INC001'] == 'MESA'
        # INC002 has the only (and therefore earliest) 'Fecha de envío' -> PAP
        assert despliegue['INC002'] == 'PAP'

    def test_unparseable_fecha_envio(self):
        """Test that a record with an unparseable 'Fecha de envío' cannot be matched as PAP."""
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

        # INC001's 'Fecha de envío' doesn't parse -> MESA
        assert despliegue['INC001'] == 'MESA'
        # INC002 has the only valid 'Fecha de envío' -> PAP
        assert despliegue['INC002'] == 'PAP'

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

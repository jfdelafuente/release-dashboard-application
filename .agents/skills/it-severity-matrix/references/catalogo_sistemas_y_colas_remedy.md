# Catálogo Canónico de Sistemas, Aplicativos y Colas BMC Remedy

Este documento detalla el inventario canónico de sistemas, subsistemas y colas operativas de soporte en BMC Remedy ITSM asociadas a cada artículo del catálogo de criticidad (Secciones 3.1 a 3.10 de `it-severity-matrix` v2.5).

> [!IMPORTANT]
> **Directriz de Carga Bajo Demanda:** Este documento debe ser leído por la IA mediante `read_file` únicamente cuando se requiera desambiguar un subsistema técnico o verificar la correspondencia entre una cola Remedy (`grupo_asignado`) y un umbral canónico.

---

## 1. Mapeo Canónico por Sección y Código

| Sección | Dominio Funcional / Técnico | Códigos Canónicos | Aplicativos / Servicios Clave | Colas BMC Remedy Asociadas | Suelo Canónico |
| :---: | :--- | :--- | :--- | :--- | :---: |
| **3.1** | **Atención al Cliente (ATC)** | `ATC-P1-01..03`<br/>`ATC-P2-01..02`<br/>`ATC-P3-01` | IVR, CTI, Ficha de Cliente Orange, CRM Jazztel, CRM4TELCO, Siebel 8, POLAR, LivePerson, Djingo, Onuris, Onconnect, Naboo, Boreal, App Mi Orange, MiJazztel. | `DES_SOE_FICHA`, `APL_MOV_SOE`, `SOP_BSS_JAZZTEL`, `DES_CRM4T`, `SOP_CRM4TELCO`, `SOP_ASISTENTE`, `DES_DJINGO`, `SOP_ONURIS`, `SOP_TECNICO_CALL_CENTER` | **SL1 / P1** (>20% colapso IVR o >20% error en 30m) |
| **3.2** | **Ventas y Contratación** | `VNT-P1-01..03`<br/>`VNT-P2-01..02`<br/>`VNT-P3-01` | CERES, Actos Comerciales, ECONTRATO, PANGEA, Televenta. | `APL_MOV_CERES`, `NEG_CAMP_CERES`, `Econtrato_N2`, `PANGEA_SUPP`, `SOP_COMERCIAL_N2` | **SL1 / P1** (>30% volumen, caída ventas >15%, o bloqueo comercial) |
| **3.3** | **Portabilidad** | `POR-P1-01..03`<br/>`POR-P2-01`<br/>`POR-P3-01` | Flujo nocturno, Entidad de Referencia, PANGEA, TEIDE. | `SOP_SMC_TEIDE`, `PANGEA_SUPP`, `PORTA_N2_FIXED`, `PORTA_N2_MOBILE` | **SL1 / P1** (Corte a las 02:00 AM o >2h retraso 08:00–20:00) |
| **3.4** | **Prepago** | `PRE-P1-01..02`<br/>`PRE-P2-01`<br/>`PRE-P3-01` | Recargas APRS, Recargas Web/App, Altas eSIM Prepago, OCS. | `RECARGAS_APRS_SUPP`, `OCS_PREPAID_N2`, `SOP_CANALES_DIGITALES` | **SL1 / P1** (>10% errores o >30m sin actividad) |
| **3.5** | **Provisión y Cobertura** | `PRV-P1-01..03`<br/>`PRV-P2-01..02`<br/>`PRV-P3-01` | POMV, SIGMA, TEIDE, IP24, LUNA, ALTAIR, BRÚJULA, MYADDRESS, GIS FIBRA, SGA, Adamo. | `POMV`, `SOP_TEC_PROVISION`, `SOP_TMC_SIGMA`, `SOP_SMC_TEIDE`, `Fijo Activacion LUNA`, `GIS_FIBRA_N2`, `SOP_TMC_HPE`, `ALTAIR_SUPP` | **SL1 / P1** (Móvil: >20% o 100% por >10m; Fijo/Fibra: >30% o 100% por >30m) |
| **3.6** | **Facturación y Cobros** | `FAC-P1-01..03`<br/>`FAC-P2-01`<br/>`FAC-P3-01` | BSCS, HP-IUM, OCS, OPEN COBROS, EXCALIBUR, HPFMS. | `SOP_BSCS_BILLING`, `OCS_MEDIATION`, `SOP_OPEN_COBROS`, `EXCALIBUR_OPER`, `HPFMS_SUPP` | **SL1 / P1** (Desviación >1 día en fecha de cobro o >3h sin tarificación online) |
| **3.7** | **Middleware Transversal** | `MID-P1-01..02`<br/>`MID-P2-01..02`<br/>`MID-P3-01` | APIGEE API Gateway, TIBCO ESB, GC Middleware, OCCI, PeopleSoft ↔ Siebel. | `SOP_TMC_APIGEE`, `SOP_TIBCO_ESB`, `GC_MIDDLEWARE_OPS`, `SOP_PEOPLESOFT_INTEGRATION` | **SL1 / P1** (Fallos masivos o cortes de integración; Escalado en Paralelo) |
| **3.8** | **Sedes, Circuitos y Tiendas** | `RED-P1-01..02`<br/>`RED-P2-01..02`<br/>`RED-P3-01` | Málaga, Zaragoza, Zamudio, Barcelona, Ulises, Meneses, Tiendas Propias. | `SOP_NET_WAN_SEDES`, `SOP_CORP_CIRCUITS`, `SOP_TIENDAS_POS` | **SL1 / P1** (Sede o doble circuito caído); **SL2 / P2** (1 circuito con HA o tienda individual) |
| **3.9** | **Infraestructura Cloud / Core** | `INF-P1-01..03`<br/>`INF-P2-01`<br/>`INF-P3-01` | IBM Power9/PSeries, VMware ESX, Oracle Exadata RAC, Cabinas SAN, Interconexión Cloud ITX (OCI/GCP). | `SOP_SYS_POWER9`, `SOP_VMWARE_ESX`, `SOP_DB_ORACLE_EXADATA`, `SOP_CLOUD_OCI`, `SOP_CLOUD_GCP`, `SOP_SAN_STORAGE` | **SL1 / P1** (Sin HA o pérdida de conectividad OCI/GCP); **SL2 / P2** (Con HA activa) |
| **3.10**| **Identidad y Automatización** | `IDE-P1-01..02`<br/>`IDE-P2-01..02`<br/>`IDE-P3-01` | Directorio Activo GDU, Evidian SSO, RobotFactory. | `SOP_GDU_IDENTITY`, `SOP_EVIDIAN_SSO`, `ROBOTFACTORY_AUTOMATION` | **SL1 / P1** (Caída global SSO/GDU o parada de robots) |

---

## 2. Tratamiento de Discrepancias de Asignación en Remedy

1. **Reasignación Ficticia:** Si un ticket describe una afectación en un sistema de la Sección 3 pero la cola asignada (`grupo_asignado`) es genérica (ej. `SERVICE_DESK_N1` o `SOPORTE_GENERICO`), el sistema de triaje **debe basarse en el impacto funcional sobre el aplicativo** y no en el estatus de la cola receptora.
2. **Elevación Automática:** La asignación a una cola técnica especializada (ej. `SOP_TMC_APIGEE` o `SOP_BSCS_BILLING`) junto con términos de indisponibilidad total confirma la criticidad de la incidencia, activando el protocolo de severidad objetiva.

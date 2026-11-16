# Catálogo Canónico de Sistemas, Aplicativos y Colas BMC Remedy (Orange / Jazztel / Multimarca)

Este documento constituye el **Inventario Canónico de Sistemas, Aplicativos y Colas Operativas en BMC Remedy ITSM**, sincronizado con la matriz oficial de criticidad y BIAs de Orange Tech Operations (`Aplicaciones - BIAs_16112026.csv`). Actúa como la **Fuente Única de Verdad (SSOT)** para la desambiguación técnica y determinación determinista de criticidad de las skills `it-severity-matrix` y `orange-it-emergency-management`.

> [!IMPORTANT]
> **Directriz de Carga Bajo Demanda (On-Demand Loading):** Este documento debe ser leído por la IA mediante `read_file` únicamente cuando se requiera desambiguar un subsistema técnico, asociar un aplicativo a su sección canónica (3.1 a 3.10), verificar su nivel oficial (`CORE++` vs `CORE` vs `Tier 2 BIA`) o resolver la correspondencia con una cola Remedy (`grupo_asignado`).

---

## 1. Framework de Gobernanza de Criticidad y Tiers de Aplicaciones

El catálogo corporativo clasifica los sistemas activos con impacto operativo (`199` aplicativos inventariados sobre un universo de `554`, siendo `117` de categoría crítica `CORE++`/`CORE`) en tres niveles estrictos:

| Tier | Categoría Oficial | Volumen | Definición Operativa | Suelo Determinista de Severidad |
| :---: | :--- | :---: | :--- | :---: |
| **Tier 0** | **`CORE++`** | **38** | **Núcleo Neurálgico Ultra-Crítico:** Aplicativos indispensables para la operativa masiva (CRM4Telco, Ficha de Cliente, Call Center CTI/IVR, eShop Frontend, Magallanes, Facturación Pospago BSCS, Provisión Core Móvil/Fijo Boreal/Aurora/Luna, APIGEE/TIBCO, Autenticación Identity/LDAP/SSO OAM). Su caída paraliza de inmediato la atención o el negocio. | **SL1 / P1**<br/>(Corte total o bloqueo operativo) |
| **Tier 1** | **`CORE`** | **79** | **Sistemas Críticos de Soporte y Transaccionales:** Facturación fija/datos (Kenan_FX), mediación, tarificación prepago (APRS/TAO/OCS), portabilidades (PORTOS/SGP MOVIL), provisión especializada (POMV/Tramitador SPM/PCNEON/SAP BASIS), ventas (Ceres/Econtrato), middleware (WebMethods/Datapower) y control de fraude (HPFMS/Scoring). *(Excluye `APOLO WORKFLOW EMPRESAS` por figurar en `Baja 2021`)*. | **SL1 / P1** (sin contingencia)<br/>**SL2 / P2** (con HA activa o degradación acotada) |
| **Tier 2** | **`Non-CORE en BIA / Pilares`** | **82** | **Aplicaciones en BIAs Oficiales (`En BIAS = Si`, 80) y Pilares de Fraude (2):** Aplicativos especializados de Cobros/Recobros (`OPENCOBROS`/`ARES`), Fraude (`HUNTER`/`BLACK-LIST`/`DIGO`/`KYC`), Identidad (`GDU`), Citas (`POLAR`), B2B (`CRM B2B`/`VISTA360 B2B`), Mayorista (`PROVISION WHOLESALE`), Red/Puesto (`VPN CORPORATIVA`/`OFFICE 365`/`NOSOTROS`) y Observabilidad/Ticketing (`OCEANE`/`TORRE DE CONTROL`). | **SL2 / P2** o según umbrales de proceso en Secciones 3.1 a 3.10 |

---

## 2. Mapeo Canónico de los Pilares Corporativos vs Dominios Técnicos (3.1 a 3.10)

| Pilar Corporativo (BIA CSV) | Dominio Funcional / Técnico | Códigos Canónicos | Aplicativos Clave en el Catálogo | Suelo Nominal |
| :--- | :--- | :--- | :--- | :---: |
| **Atención al Cliente** | **3.1 ATC** | `ATC-P1-01..03`<br/>`ATC-P2-01..02` | `CALL CENTER CTI`, `IVR`, `FICHA DE CLIENTE`, `IRIS`, `CRM4TELCO`, `MAGALLANES`, `ACME APP/WEB ORANGE`, `ALTAMIRA`, `POLAR`, `CRM B2B` *(+ referencia comercial `App Mi Orange` / `MiJazztel`)* | **SL1 / P1** si es `CORE++` o colapso >20% en 30m |
| **Vender Productos y Servicios** | **3.2 Ventas y Contratación** | `VNT-P1-01..03`<br/>`VNT-P2-01..02` | `PANGEA`, `ESHOP FRONTEND`, `KRATOS`, `CERESRT`, `CERES`, `AGORA`, `ALCE`, `ARPA`, `ECONTRATO`, `FIRMA DIGITAL`, `SEDNA`, `SIGNA`, `SITAM`, `XNET` | **SL1 / P1** si bloqueo comercial o afectación >30% volumen |
| **Provisión (Portabilidad)** | **3.3 Portabilidad** | `POR-P1-01..03`<br/>`POR-P2-01` | `PORTOS` (Fijo), `SGP MOVIL` (Móvil), `PANGEA`, `TEIDE` | **SL1 / P1** en flujo 2 AM o retraso >2h con entidad referencia |
| **Facturación / Cobros (Prepago)**| **3.4 Prepago** | `PRE-P1-01..02`<br/>`PRE-P2-01` | `APRS`, `TAO`, `OCS`, `SEDNA`, `PCRF_GW` | **SL1 / P1** si >10% errores recargas o >30m sin actividad |
| **Provisión** | **3.5 Provisión y Cobertura** | `PRV-P1-01..03`<br/>`PRV-P2-01..02` | `BOREAL`, `AURORA` (AFS Fijo), `LUNA`, `SIGMA`, `GIROS`, `TEIDE`, `ALTAIR`, `MYADDRESS`, `PROVISION MOVIL` (POMV), `TRAMITADOR` (SPM), `SAP BASIS`, `PROVISION WHOLESALE` | **SL1 / P1** si corte en provisión móvil (>20%) o fija (>30%) |
| **Facturación** y **Cobros** | **3.6 Facturación y Cobros** | `FAC-P1-01..03`<br/>`FAC-P2-01` | `BSCS`, `KENAN_FX`, `MEDIACION`, `ABACUS BRM`, `BRM PORTAL M2M`, `COBROS_KFX`, `PSP`, `INTRANSIT`, `XPRESSION`, `FEW`, `OPENCOBROS`, `ARES` | **SL1 / P1** si corte tarificación >3h o retraso ciclo >1 día |
| **Fraude** | **3.6 / Riesgo Transaccional** | `FAC-P1-03`<br/>`VNT-P1-01` | `HPFMS`, `SCORING`, `COCO`, `HUNTER`, `BLACK-LIST`, `DIGO`, `KYC ONLINE IDENTITY`, `ALEGACIONES`, `RAID`, `AVENEW` | **SL1 / P1** si parada de motores de riesgo en contratación |
| **Transversal Middleware** | **3.7 Middleware Transversal** | `MID-P1-01..02`<br/>`MID-P2-01..02` | `OPENAPI` (APIGEE), `TIBCO`, `MICROSERVICIOS`, `TIBCO-OMV`, `WEBMETHODS`, `DATAPOWER`, `EXPERIENCE LAYER`, `MIDDLEWARE MQ CRM4T` | **SL1 / P1** (Corte transversal con Escalado en Paralelo) |
| **Transversal Infra / Red**| **3.8 / 3.9 Infraestructura y Red** | `RED-P1-01..02`<br/>`INF-P1-01..03` | `PORTAL DE REDES`, `VPN CORPORATIVA`, `ELEMENTOS DE ALMACENAMIENTO`, `GRANJA VPAW`, `CITRIX - CONTROL`, `DNS` | **SL1** (Sin HA / Aislamiento) / **SL2** (Con HA activa) |
| **Transversal Identidad** | **3.10 Identidad y Automatización** | `IDE-P1-01..02`<br/>`IDE-P2-01..02` | `LDAP CORPORATIVO`, `IDENTITY`, `SSO OAM`, `GDU`, `CONTROLADOR DE DOMINIO/DA`, `DIRECTORIO ACTIVO`, `RPA NICE` | **SL1 / P1** (Caída global SSO/LDAP o parada RobotFactory) |

---

## 3. Inventario Canónico de Aplicaciones CORE++ (Tier 0 — 38 Aplicaciones Ultra-Críticas)

Toda indisponibilidad total o afectación de flujo operativo en estos sistemas impone de forma determinista el suelo **`SL1 / P1`**.

| # | Aplicativo | Operadora | Dominio Canónico | Código | Cola BMC Remedy | Pilares y BIAs Corporativos | Función Operativa Oficial |
| :-: | :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| 1 | **ACME APP ORANGE** | ORANGE | 3.1 ATC | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | VENDER PRODUCTOS Y SERVICIOS, Seguro Móvil, Gestión de pruebas IT | Área privada del cliente de Orange. Acceso para ver su consumo, contrato, factura y productos contratados a través de Ap |
| 2 | **ACME WEB ORANGE** | ORANGE | 3.1 ATC | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | VENDER PRODUCTOS Y SERVICIOS, Seguro Móvil, Gestión de pruebas IT | Área privada del cliente de Orange. Acceso para ver su consumo, contrato, factura y productos contratados a través de We |
| 3 | **ALTAMIRA** | Multimarca | 3.1 ATC | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | VENDER PRODUCTOS Y SERVICIOS, Seguro Móvil, Gestión Incidencias | Parte de la aplicación del Frontal Comercial Unificado para Orange España. Esta aplicación reemplaza al actual eShop par |
| 4 | **CALL CENTER CTI** | ORANGE | 3.1 ATC | `ATC-P1-01` | `SOP_TECNICO_CALL_CENTER` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Plataforma de Contact_center desplegada en centros internos y proveedores externos para la gestión de llamadas. Tiene co |
| 5 | **CRM4TELCO** | JAZZTEL | 3.1 ATC | `ATC-P1-02` | `SOP_CRM4TELCO` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE, Seguro Móvil | CRM de Jazztel. BD de Clientes de Masivo y ciertos servicios de Empresas. Servicio VIP de Venta y Atención |
| 6 | **FICHA CLIENTE** | JAZZTEL | 3.1 ATC | `ATC-P1-02` | `SOP_CRM4TELCO` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE, Seguro Móvil | Acceso uniforme a diversos sistemas y presentación unificada en una única ficha. |
| 7 | **FICHA DE CLIENTE** | ORANGE | 3.1 ATC | `ATC-P1-02` | `DES_SOE_FICHA` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE, Seguro Móvil | Esta aplicación permitirá al agente visualizar la información necesaria del cliente para que, en los primeros segundos d |
| 8 | **IRIS** | Multimarca | 3.1 ATC | `ATC-P1-02` | `DES_SOE_FICHA` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS, Seguro Móvil | Sistema de vista 360 del cliente. |
| 9 | **IVR** | ORANGE | 3.1 ATC | `ATC-P1-01` | `SOP_TECNICO_CALL_CENTER` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | El sistema IVR es el servicio de atención automática al cliente final. |
| 10 | **PUBLICACION** | ORANGE | 3.1 ATC | `ATC-P2-01` | `SOP_IT_OPERACIONES` | ATENCIÓN AL CLIENTE | Nuevo portal para la actividad de gestión y publicación de contenidos relativos a los sites (OWCS) existentes en el ámbi |
| 11 | **MAGALLANES** | Multimarca | 3.1 ATC / Convergencia | `ATC-P1-02` | `SOP_CANALES_DIGITALES` | Transversal / O&M | Plataforma estratégica de convergencia comercial y atención unificada Multimarca. |
| 12 | **HESMS** | Multimarca | 3.1 ATC / Notificaciones | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE, COBROS, FACTURACIÓN | El sistema HESMS Multicanal es encargado de realizar los envíos de las campañas de marketing a la cartera de clientes de |
| 13 | **SIRES** | Multimarca | 3.1 ATC / Notificaciones | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Sistema centralizado de envío de mensajes. Centraliza la gestión/envío de las comunicaciones SMS/Email/Notificaciones a |
| 14 | **IDENTITY** | Multimarca | 3.10 Identidad | `IDE-P1-01` | `SOP_GDU_IDENTITY` | VENDER PRODUCTOS Y SERVICIOS, COBROS | Herramienta de autenticación y logado unificado de los sistemas de front-end de OSP. Identity concilia la información de |
| 15 | **LDAP CORPORATIVO** | ORANGE | 3.10 Identidad | `IDE-P1-01` | `SOP_GDU_IDENTITY` | Transversal / O&M | Repositorio de usuarios y perfiles que valida la autenticación de acceso de los usuarios a las aplicaciones. |
| 16 | **SSO OAM** | ORANGE | 3.10 Identidad | `IDE-P1-01` | `SOP_EVIDIAN_SSO` | Ciberseguridad | Oracle Single Sign On (OAM) |
| 17 | **CERESRT** | Multimarca | 3.2 Ventas | `VNT-P1-01` | `NEG_CAMP_CERES` | VENDER PRODUCTOS Y SERVICIOS, Seguro Móvil | Aplicación para la gestión y ejecución de Campañas que permite automatizar una relación individualizada con nuestros cli |
| 18 | **ESHOP FRONTEND** | ORANGE | 3.2 Ventas | `VNT-P1-03` | `SOP_CANALES_DIGITALES` | VENDER PRODUCTOS Y SERVICIOS | Frontal web de tienda online (eShop) de Orange para catálogo, captación y contratación digital. |
| 19 | **KRATOS** | Multimarca | 3.2 Ventas | `VNT-P1-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, Seguro Móvil | Aplicación que contiene la réplica del catálogo comercial y las reglas necesarias para que el Frontal Comercial Unificad |
| 20 | **PANGEA** | Multimarca | 3.2 Ventas | `VNT-P1-01` | `PANGEA_SUPP` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, Seguro Móvil | Aplicación de frontal unificado para Orange España. Esta aplicación reemplaza nuestros portales comerciales actuales (es |
| 21 | **GED MOVIL Y FIJO** | ORANGE | 3.2 Ventas / Documental | `VNT-P1-01` | `SOP_COMERCIAL_N2` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FACTURACIÓN, FRAUDE, Estrategia&Negocio Mayorista | Sistema de gestión documental, encargado de la carga, almacenamiento y consulta de diferentes tipologías de documentació |
| 22 | **ALTAIR** | Multimarca | 3.5 Provisión | `PRV-P1-01` | `ALTAIR_SUPP` | ATENCIÓN AL CLIENTE, PROVISION, FRAUDE | Heramienta consolidada de Test&Diagnóstico para realizar el aseguramiento del servicio a los clientes |
| 23 | **AURORA** | Multimarca | 3.5 Provisión | `PRV-P1-01` | `SOP_TEC_PROVISION` | PROVISION, VENDER PRODUCTOS Y SERVICIOS | TIBCO AFS FIJO . Sistema de Provisión de Fijo FTTH. Sistema de orquestación y provisión de servicios de telefonía fija, |
| 24 | **BOREAL** | ORANGE | 3.5 Provisión | `PRV-P1-01` | `POMV` | PROVISION, VENDER PRODUCTOS Y SERVICIOS | Sistema de Provisión de Móvil |
| 25 | **GIROS** | Multimarca | 3.5 Provisión | `PRV-P1-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, FRAUDE | Sistema para la gestión integrada del inventario de recursos de Orange Spain. |
| 26 | **LUNA** | Multimarca | 3.5 Provisión | `PRV-P1-01` | `Fijo Activacion LUNA` | ATENCIÓN AL CLIENTE, PROVISION, COBROS, FRAUDE | Sistema de activación del fijo |
| 27 | **MYADDRESS** | Multimarca | 3.5 Provisión | `PRV-P1-01` | `SOP_TEC_PROVISION` | VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE, Estrategia&Negocio Mayorista | Normalización de direcciones en tiempo real y por lotes, localización en mapa, sirviendo información acerca de la direcc |
| 28 | **SIGMA** | Multimarca | 3.5 Provisión | `PRV-P1-01` | `SOP_TMC_SIGMA` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | SIGMA operacional es el gestor de recursos de la red del dominio móvil. Maestro de numeración, Maestro de terminales, Ma |
| 29 | **TEIDE** | ORANGE | 3.5 Provisión | `PRV-P1-01` | `SOP_SMC_TEIDE` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE, Seguro Móvil | Sistema cuya principal funcionalidad es la contratación y aprovisionamiento de líneas telefónicas móviles junto a los se |
| 30 | **BSCS** | ORANGE | 3.6 Facturación | `FAC-P1-01` | `SOP_BSCS_BILLING` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FACTURACIÓN, FRAUDE, Ciber protección red móvil, Móviles, Seguro Móvil | Sistema de Facturación Pospago (Postpaid billing and customer care solution.) |
| 31 | **FEW** | ORANGE | 3.6 Facturación | `FAC-P1-01` | `SOP_BSCS_BILLING` | VENDER PRODUCTOS Y SERVICIOS | Sistema encargado de ofrecer la factura electrónica e informes de factura a nuestros clientes. |
| 32 | **MDG COH** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS | Sistema con toda la información de cliente (Fijo y Móvil) disponible online en cahe para consulta por cualquier sistema |
| 33 | **MICROSERVICIOS** | Multimarca | 3.7 Middleware | `MID-P1-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS | Aplicación para la exposición de APIs para la utilización por parte de servicios que lleven a cabo funcionalidades muy c |
| 34 | **OPENAPI** | Multimarca | 3.7 Middleware | `MID-P1-01` | `SOP_TMC_APIGEE` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE, Estrategia&Negocio Mayorista | APIGEE. OpenAPI implementa el estándar TMF de APIs dentro Orange España. Habilita una arquitectura cloud native y ciclo |
| 35 | **TIBCO** | Multimarca | 3.7 Middleware | `MID-P1-01` | `SOP_TIBCO_ESB` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | EAI (Middleware). Middleware de Orange. No soporta gestión de ficheros entre interfaces via BATCH. |
| 36 | **TIBCO-OMV** | ORANGE | 3.7 Middleware | `MID-P1-01` | `SOP_TIBCO_ESB` | Transversal / O&M | Plataforma específica de MDW para realizar comunicaciones on-line de los sistemas que gestionan los Operadores Móviles V |
| 37 | **PORTAL DE REDES** | Multimarca | 3.8 Redes / Sedes | `RED-P1-01` | `SOP_NET_WAN_SEDES` | Transversal / O&M | PORTAL DE REDES es un portal que permite un acceso unico a las aplicaciones de red con single sign on, dotando de fucion |
| 38 | **ELEMENTOS DE ALMACENAMIENTO** | ORANGE | 3.9 Infraestructura | `INF-P1-01` | `SOP_SAN_STORAGE` | Transversal / O&M | ELEMENTOS DE ALMACENAMIENTO |

> **Nota de vigencia (`16/11/2026`):** Se incorporan `ESHOP FRONTEND` y `MAGALLANES` al listado `CORE++` y se retiran las fichas dadas de baja en BIA (`AMON`, `ATENAS` y `MIJAZZTEL`), manteniéndose la mención operativa a *App Mi Orange / MiJazztel* en las reglas `ATC-P1-03` / `ATC-P2-02` para tickets comerciales que aún utilicen esa denominación.

---

## 4. Inventario Canónico de Aplicaciones CORE (Tier 1 — 79 Aplicaciones Críticas Activas)

Afectación sin contingencia activa **`SL1 / P1`**; afectación con redundancia activa o degradación acotada activa **`SL2 / P2`**.

| # | Aplicativo | Operadora | Dominio Canónico | Código | Cola BMC Remedy | Pilares y BIAs Corporativos | Función Operativa Oficial |
| :-: | :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| 1 | **AREA PRIVADA CLIENTES** | JAZZTEL | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | PROVISION | Servicio web a través del que los clientes acceden a su propio perfil para consultar/modificar parámetros relacionados c |
| 2 | **GUIS** | ORANGE | 3.1 ATC | `ATC-P1-02` | `DES_SOE_FICHA` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Interfaz Gráfico de Usuario para Call Centers. |
| 3 | **PEOPLESOFT CRM** | ORANGE | 3.1 ATC | `ATC-P1-02` | `SOP_PEOPLESOFT_N2` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE, Gestionar Incidencias | Soporte a clientes Servicios de campo Marketing y ventas |
| 4 | **PEOPLESOFT JZZ** | JAZZTEL | 3.1 ATC | `ATC-P2-01` | `DES_SOE_FICHA` | ATENCIÓN AL CLIENTE | Plataforma de Gestión Financiera y de Recursos Humanos de Jazztel |
| 5 | **PROMOSMS** | Multimarca | 3.1 ATC | `ATC-P1-01` | `SOP_IT_OPERACIONES` | Transversal / O&M | PROMOSMS permite la recepción de mensajes enviados por los clientes para realizar un procesado de la información e inter |
| 6 | **SIEBEL** | ORANGE | 3.1 ATC | `ATC-P1-02` | `SOP_CRM_SIEBEL` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE, Móviles, Seguro Móvil | Ventana única para la gestión de clientes y distribuidores, proporcionando una visión completa del perfil y comportamien |
| 7 | **CONTROLADOR DE DOMINIO/DA** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `SOP_GDU_IDENTITY` | ATENCIÓN AL CLIENTE | Directorio Activo Común |
| 8 | **DIRECTORIO ACTIVO** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `SOP_GDU_IDENTITY` | Transversal / BIA O&M | Servidores que dan servicio de Red |
| 9 | **AGORA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Creado como una extensión del nuevo CRM de la compañía, pretende dotar al canal de distribución de las herramientas nece |
| 10 | **ALCE** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | PROVISION, VENDER PRODUCTOS Y SERVICIOS | Herramienta de gestión de ventas de productos móviles para clientes empresariales |
| 11 | **ARPA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS | Sistema dirigido principalmente a distribuidores que les permite creación de contratos, la activación on-line de líneas |
| 12 | **CATALOGO CORPORATIVO** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | Transversal / O&M | Catálogo corporativo de todas las ofertas de fijo (acceso + voz fija + bundles) que no sean sólo de voz (esta la lleva X |
| 13 | **CERES** | Multimarca | 3.2 Ventas | `VNT-P2-01` | `NEG_CAMP_CERES` | VENDER PRODUCTOS Y SERVICIOS | Aplicación para la gestión y ejecución de Campañas que permite automatizar una relación individualizada con nuestros cli |
| 14 | **ECONTRATO** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `Econtrato_N2` | FRAUDE | Firma digital de documentos en tiendas Orange y control de fraude documental |
| 15 | **PAE** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, Ciber protección red móvil, Móviles | Aplicación destinada al cliente final para segmento empresas orientada a la autogestión de sus productos y servicios. |
| 16 | **SIGNA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Permitirá a los comerciales de PYMES elaborar ofertas y firmar digitalmente el contrato en movilidad |
| 17 | **SITAM** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, Seguro Móvil | SITAM (Sistema de Interfaces de Orange-España) es el sistema que a partir de datos réplica de BSCS, proporciona el nivel |
| 18 | **XNET** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Extranet de ventas fijo. Herramienta Web unificada para la gestión de contratación de productos de telefonía fija para c |
| 19 | **PORTOS** | ORANGE | 3.3 Portabilidad | `POR-P1-01` | `PORTA_N2_FIXED` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS | Sistema de gestión de portabilidad del mercado fijo |
| 20 | **SGP MOVIL** | Multimarca | 3.3 Portabilidad | `POR-P1-01` | `PORTA_N2_MOBILE` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE, Estrategia&Negocio Mayorista | Sistema que gestiona las portabilidades numéricas y el ciclo de vida de su comunicación a otros operadores y terceras en |
| 21 | **APRS** | ORANGE | 3.4 Prepago | `PRE-P1-01` | `RECARGAS_APRS_SUPP` | Transversal / O&M | Ecargada de gestionar las peticiones de recarga que le llegan por línea x25 de las entidades bancarias, y de la gestión |
| 22 | **OCS** | Multimarca | 3.4 Prepago | `PRE-P1-01` | `OCS_PREPAID_N2` | FACTURACIÓN, FRAUDE | OCS es el tarificador online de datos en Orange España de los cliente Amena y Orange de móvil. |
| 23 | **PCRF_GW** | ORANGE | 3.4 Prepago | `PRE-P1-01` | `OCS_PREPAID_N2` | Transversal / O&M | Pasarela para la gestión dinámica de políticas y reglas de charging de datos |
| 24 | **SEDNA** | ORANGE | 3.4 Prepago | `PRE-P1-01` | `OCS_PREPAID_N2` | VENDER PRODUCTOS Y SERVICIOS | SEDNA es el sistema que proporciona el front-end con los sistemas de los clientes prepago (TAO y TA) |
| 25 | **TAO** | ORANGE | 3.4 Prepago | `PRE-P1-01` | `OCS_PREPAID_N2` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FACTURACIÓN, FRAUDE | Realizar la gestión del ciclo de vida del cliente prepago, tarificación de los servicios que consume y gestión del saldo |
| 26 | **GESTION DE INCIDENCIAS** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | Gestionar Incidencias | Herramienta corporativa de gestión de incidencias, problemas y solicitudes de NEGOCIO. Utilizada principalmete para la p |
| 27 | **LYRA** | Multimarca | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | FRAUDE | Aplicación para la provisión de productos PYME sobre acceso de banda ancha. |
| 28 | **NABOO** | Multimarca | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS | Sistema de análisis de los eventos de provisión, entre ellos mobile connect. |
| 29 | **PCNEON OBA** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION | Plataforma de Comunicaciones con NEON – OBA. La plataforma PCN (Plataforma de Comunicaciones con NEON) hace funciones de |
| 30 | **PROVISION MOVIL** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `POMV` | PROVISION | POMV. Sistema de Provisión de Clientes de Móvil |
| 31 | **RESER** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | Transversal / O&M | RESER proporciona el Repositorio de Servicios de Red asociado a las líneas, llevando a cabo tareas de provision de servi |
| 32 | **REVENTA FIBRA ISP** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION | Provisión de fibra de clientes Orange en Red Jazztel |
| 33 | **SAO** | Multimarca | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | Transversal / BIA O&M | SAO - Sistema de auditorias online. Audita tdos los sistemas de la empresa para asegurar la calidad de los datos de nego |
| 34 | **SARO** | Multimarca | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, FRAUDE | Sistema auditorias y regularizaciones online de provisión (SARO) |
| 35 | **SDM** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, Estrategia&Negocio Mayorista | Sistema para la gestión y mantenimiento de MSISDNs y de los repositorios de servicios y parmetros para OMVs y M2M |
| 36 | **SEDRA** | Multimarca | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | Transversal / O&M | SEDRA es el Sistema de Seguimiento del Despliegue de Red de FTSpain en el dominio móvil. |
| 37 | **SGA** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, FRAUDE | Servicio que contiene el inventario de las sim's de prepago de Wholesale. |
| 38 | **SGF** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE, Seguro Móvil | Sistema de ejecución de campañas responsable de la logística asociada.  Por otra parte proporciona una Web de contingenc |
| 39 | **SGL** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION, Seguro Móvil | Sistema de Gestión de Logística |
| 40 | **SGR** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION | Sistema de Gestión de Recursos de numeración y pares de TFCA |
| 41 | **SIEBEL - M2M** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Ventana única para la gestión de clientes y lineas M2M que contiene: datos de clientes y personas de contacto, Gestión d |
| 42 | **TRAMITADOR** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION | Sistema de Provisión de Clientes de Masivo (SPM) |
| 43 | **WEB MANTENEDORES** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE, Estrategia&Negocio Mayorista | Web de adminstración de OT (Órdenes de Trabajo). El personal instalador comprueban in situ si el servicio está instalado |
| 44 | **SAP BASIS** | ORANGE | 3.5 Provisión / SAP | `PRV-P2-01` | `SOP_SYS_POWER9` | PROVISION, Seguro Móvil | Plataforma tecnológica base SAP que soporta procesos de provisión, logística, seguros y áreas corporativas. |
| 45 | **BALANCE INTERFACE** | JAZZTEL | 3.6 / Fraude | `FAC-P1-03` | `HPFMS_SUPP` | FRAUDE | Sistema de consultas e informes predefinidos a la información de CDRs de clientes. |
| 46 | **COCO** | Multimarca | 3.6 / Fraude | `FAC-P1-03` | `HPFMS_SUPP` | PROVISION, FRAUDE | Sistema de información cuya finalidad es analizar el consumo de los clientes para detectar y actuar antes consumo anómal |
| 47 | **HPFMS** | Multimarca | 3.6 / Fraude | `FAC-P1-03` | `HPFMS_SUPP` | FRAUDE | HP Fraud Management System es una plataforma de gestión de Fraude que ofrece soporte a la detección, análisis y decisión |
| 48 | **SCORING** | Multimarca | 3.6 / Fraude | `FAC-P1-03` | `HPFMS_SUPP` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Sistema de Gestión del Riesgo. |
| 49 | **ABACUS BRM** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Sistema dedicado a la generación de facturas rectificativas para el mercado de telefonía móvil postpago de FT España y O |
| 50 | **APOLO** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | Gestionar Incidencias | Sistema para el almacen de datos legales. Este sistema aplica tanto a sitemas del móvil como del fijo (incluido yacom). |
| 51 | **BRM PORTAL M2M** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | COBROS, FACTURACIÓN | Tarificador y facturador plataforma M2M de Orange Spagne. Recibe todos los datos de los clientes, jerarquías, personaliz |
| 52 | **COBROS_KFX** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | Transversal / O&M | Sistema de gestión de remesas y control de impagados. Tiene extensiones para la gestión de impagados. Engloba todas aque |
| 53 | **CTI - NORMALIZADOR BANCARIO** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS, FACTURACIÓN, FRAUDE | Normalización de cuentas bancarias. |
| 54 | **EDITRAN** | Multimarca | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE, COBROS, FACTURACIÓN | Sistema para intercambio de ficheros con entidades externas a Grupo AUNA a través de red X25. |
| 55 | **ESCALA** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | Transversal / BIA O&M | Facturación, estimación y presupuestado del alquiler de líneas. |
| 56 | **INTERFAZ CRM4T-KENAN** | JAZZTEL | 3.6 Facturación | `FAC-P2-01` | `SOP_BSS_KENAN` | Transversal / BIA O&M | GIF. Gestor de Integracion CRM4T - Facturacion |
| 57 | **INTRANSIT** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | COBROS, FACTURACIÓN, FRAUDE | Sistema central de tarificación de tráfico Roaming de la FTES. Se encarga de la tarificación del tráfico Roaming IN y OU |
| 58 | **KENAN_FX** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSS_KENAN` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FACTURACIÓN, FRAUDE, Customer SOC, Security Suite, AntiDDoS | Sistema de facturación y tarificación de servicios y clientes de tecnología fija y datos |
| 59 | **KENAN_FX JZZ** | JAZZTEL | 3.6 Facturación | `FAC-P2-01` | `SOP_BSS_KENAN` | PROVISION, Seguro Móvil | Sistema de facturación KENAN |
| 60 | **MDG GG** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS | Sistema con toda la información de cliente (Fijo y Móvil) disponible online para consulta por cualquier sistema ( en par |
| 61 | **MEDIACION** | JAZZTEL | 3.6 Facturación | `FAC-P2-01` | `OCS_MEDIATION` | COBROS, FACTURACIÓN | Sistema de Mediación de Jazztel se encarga de recoger el tráfico generado por los distintos elementos de red o fuentes e |
| 62 | **PSP** | Multimarca | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Payment Service Provider. Pasarela de pagos de tarjeta de crédito externa que permite realizar cobros de tarjeta de créd |
| 63 | **VOSS-OMV** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | Estrategia&Negocio Mayorista | VOSS, Sistema de Conciliación de OMVs de Orange España, es el sistema que realiza la tarificación y conciliación wholesa |
| 64 | **XPRESSION** | Multimarca | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | COBROS, FACTURACIÓN | Sistema CCM (Customer Communications Management) encargado de la composición de documentos, principalmente facturas. |
| 65 | **DATAPOWER** | Multimarca | 3.7 Middleware | `MID-P2-01` | `SOP_DATAPOWER_OPS` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, Estrategia&Negocio Mayorista | Sistema intermediario para las comunicaciones de la OBA entre FT y NEON vía Web Services. Gestiona todo el tráfico de re |
| 66 | **DISPATCHER** | ORANGE | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | Transversal / O&M | Se utiliza como punto único de integración con WM de forma que se puedan crear nuevos flujos más potentes (en DISPATCHER |
| 67 | **MIDDLEWARE MQ CRM4T** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN, FRAUDE, Estrategia&Negocio Mayorista | Canal de mensajería universal en plataformas distribuidas que se conecta de forma virtual a cualquier sistema IT comerci |
| 68 | **MIDDLEWARE REVENTA ISP** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE | Provision FTTH de Orange y Vodafone |
| 69 | **MIDDLEWARE SISTEMAS BSS** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE, PROVISION | OSB Sistemas. Servicio Middleware que proporcionará capacidades avanzadas de gestión de las comunicaciones e integracion |
| 70 | **MIDDLEWARE SISTEMAS CC** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE | OSB CC. Middleware Sistemas CallCenters |
| 71 | **TIBCO-M2M** | ORANGE | 3.7 Middleware | `MID-P2-01` | `SOP_TIBCO_ESB` | Transversal / O&M | Sistema TIBCO para la plataforma M2M Plataforma específica de MDW para realizar las comunicaciones on-line de los sistem |
| 72 | **WEBMETHODS** | ORANGE | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | Transversal / O&M | EAI (middleware). Se trata del Middleware de wanadoo. Los procesos más importante de los que WM es responsable: Suspensi |
| 73 | **COSTES TERMINACION** | Multimarca | 3.8 Redes / Sedes | `RED-P1-01` | `SOP_NET_WAN_SEDES` | Estrategia&Negocio Mayorista | Plataforma de gestion de routing para reventa de trafico internacional. LCR. |
| 74 | **DNS** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_SYS_POWER9` | Transversal / BIA O&M |  |
| 75 | **GRANJA VPAW** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_VMWARE_ESX` | Transversal / O&M | Granja VDI (Virtual Desktop Infraestruture) de Microsoft utilizada para alojar los PCs virtuales con privilegios especia |
| 76 | **CORREO CORPORATIVO** | Multimarca | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | VENDER PRODUCTOS Y SERVICIOS, FRAUDE, Security Suite | Permite enviar y recibir mensajes de correo electrónico. También proporciona la gestión del calendario, compartida o ind |
| 77 | **EPSILON** | Multimarca | O&M / Plataforma IT | `O&M-P1-01` | `SOP_ITIL_EPSILON` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE, Gestion Capacidad, Gestión de la configuración, Gestion de PaPs y Mesas Postproducción, Gestionar Incidencias, Gestión de pruebas IT | Plataforma de Explotación de Servicios ITIL ORANGE: Gestión de Incidencias/Peticiones, Gestión de cambios, Gestión de pr |
| 78 | **MERLIN** | Multimarca | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Gestión de la configuración, Gestion de PaPs y Mesas Postproducción, Configuración del Software, Gestionar Incidencias | Jira es una herramienta en línea para la administración de tareas de un proyecto, el seguimiento de errores e incidencia |
| 79 | **WIKI ORANGE** | Multimarca | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | BIAs B2B Cloud Housing, Ciberseguridad, Gestion Capacidad, Gestion de PaPs y Mesas Postproducción, Configuración del Software, Gestionar Incidencias, Gestión de pruebas IT | Confluence es software de colaboración en equipo . Escrito en Java y utilizado principalmente en entornos corporativos, |

> **Nota de depuración (`16/11/2026`):** Se actualiza `SAP` a `SAP BASIS`, se retira `NETPLUS` (baja del inventario BIA) y se excluye `APOLO WORKFLOW EMPRESAS` por constar en `Baja 2021` (`En BIAS = No`) dentro del fichero fuente (`79` aplicaciones `CORE` activas).

---

## 5. Aplicaciones Especializadas en BIAs y Pilares (Tier 2 — 82 Aplicaciones Non-CORE)

Incluye la totalidad de aplicativos Non-CORE registrados oficialmente con **`En BIAS = Si` (`80`)** más los aplicativos específicos del pilar de **Fraude (`2`: `DIGO` y `KYC ONLINE IDENTITY`)**, que activan umbrales de las Secciones 3.1 a 3.10.

| # | Aplicativo | Operadora | Dominio Canónico | Código | Cola BMC Remedy | Pilares y BIAs Corporativos | Función Operativa Oficial |
| :-: | :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| 1 | **DESCUBRE ORANGE** | ORANGE | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE, Gestión de pruebas IT | Gestor de Conocimiento Unificado. Consta de portales para ventas (comerciales y distribuidores) y para los agentes de ca |
| 2 | **FICHA CLIENTE MM** | JAZZTEL | 3.1 ATC | `ATC-P2-01` | `DES_SOE_FICHA` | ATENCIÓN AL CLIENTE, FRAUDE | Aplicación de call center cuyo ámbito es la gestión Multimarca en Orange Spain (Orange, Amena, Jazztel) |
| 3 | **GRABADOR DE VOZ CC** | Multimarca | 3.1 ATC | `ATC-P2-01` | `SOP_TECNICO_CALL_CENTER` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Servicio de Grabación,evaluación y transcripción de llamadas. Verint |
| 4 | **HOW** | ORANGE | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS | HOW es la Herramienta Orange Web para la recopilación y explotación de datos relativos a la calidad de atención al clien |
| 5 | **NEA** | Multimarca | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE | El objetivo del sistema es el de habilitar una interfaz de usuario que permita gestionar órdenes masivas de clientes BAU |
| 6 | **POLAR** | Multimarca | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | VENDER PRODUCTOS Y SERVICIOS, Gestión de pruebas IT | Aplicativo dentro del ambito del Field Service Management para la cita e instalación de servicios a cliente final. |
| 7 | **QLIKSENSE** | ORANGE | 3.1 ATC | `ATC-P1-01` | `SOP_IT_OPERACIONES` | FRAUDE | Qlik Sense es una plataforma para el análisis de datos donde puede analizar datos y realizar descubrimientos de datos po |
| 8 | **SAS ABM** | ORANGE | 3.1 ATC | `ATC-P1-01` | `SOP_IT_OPERACIONES` | FRAUDE | SAS ABM (COSTES) OSP: Activity Based Management. Sistema que permite el conocimiento de costes e ingresos (Rentabilidad) |
| 9 | **WOC** | ORANGE | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE, COBROS | Cliente ligero de OpenCobros |
| 10 | **CRM B2B** | ORANGE | 3.1 ATC / Empresas | `ATC-P2-01` | `SOP_COMERCIAL_N2` | FRAUDE, Customer SOC, Ciber protección red móvil, Móviles | CRM del segmento Empresas (B2B) con impacto en control de fraude, Customer SOC y servicios móviles. |
| 11 | **PORTAL AUTOGESTION CENTRALITA** | ORANGE | 3.1 ATC / Empresas | `ATC-P2-02` | `SOP_CANALES_DIGITALES` | Transversal / BIA O&M | Portal web de autogestión de servicios de centralita virtual para clientes de empresa. |
| 12 | **VISTA360 B2B** | ORANGE | 3.1 ATC / Empresas | `ATC-P2-01` | `SOP_COMERCIAL_N2` | FRAUDE | Vista unificada 360º de clientes del segmento Empresas (B2B) y soporte a validaciones de fraude. |
| 13 | **ARGOS** | Multimarca | 3.10 Identidad | `IDE-P2-01` | `ROBOTFACTORY_AUTOMATION` | Configuración del Software, Gestión de pruebas IT | Framework de Testing Automático integrado con Torre de Control |
| 14 | **ASISTENTE** | Multimarca | 3.10 Identidad | `IDE-P2-01` | `SOP_GDU_IDENTITY` | FRAUDE | Infraestructura de asistentes virtuales para distintos canales de entrada: WhatsApp, Web, aplicaciones móviles multimarc |
| 15 | **GDU** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `SOP_GDU_IDENTITY` | ATENCIÓN AL CLIENTE, PROVISION, FRAUDE, Ciberseguridad, Gestión de la configuración | El sistema de Gestión de Usuarios, GDU, se diseñara para mejorar la gestión, control, trazabilidad y seguridad de las cu |
| 16 | **RPA NICE** | Multimarca | 3.10 Identidad | `IDE-P2-01` | `ROBOTFACTORY_AUTOMATION` | ATENCIÓN AL CLIENTE | Software RPA (Robotic Process Automation) que tiene por finalidad capturar e interpretar aplicaciones existentes para pr |
| 17 | **AGENDA UNICA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Herramienta para permitir realizar citas en Punto de Venta en varios canales con expertos para proporcionar soporte en l |
| 18 | **ALEGACIONES** | Multimarca | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Nueva web que permita gestionar el proceso de alegaciones de penalizaciones de fraude al canal de distribución y agiliza |
| 19 | **APOYOS TERRITORIALES** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, FRAUDE | La herramienta “SIAPT” permite gestionar las incidencias del servicio prestado a los clientes. Se recogen, se tramitan o |
| 20 | **AVENEW** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | FRAUDE | La  solución del Punto de Venta de las tiendas propias y franquiciadas,recargas  y la tramitación de medios de pago medi |
| 21 | **DATARYS** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Portal web del área de Big data que contiene dashboards que usarán el resto de áreas de Orange Spain para el seguimiento |
| 22 | **ELENA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, BIAs B2B Cloud Housing, Customer SOC, Security Suite, AntiDDoS | Herramienta para el mercado de Grandes Cuentas para las funciones de: - Entrada de Órdenes de Cliente GGCC. - BPM/Orques |
| 23 | **EUNOMIA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Inventario de Base Instalada de Grandes Cuentas centrado en: - Información de clientes y servicios GGCC necesarios para |
| 24 | **FIRMA DIGITAL** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `Econtrato_N2` | Transversal / BIA O&M | Servicio transversal de firma electrónica y validación documental en procesos comerciales. |
| 25 | **GEICO** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Sistema de gestión electrónica de informes de comisiones. |
| 26 | **MICROSTRATEGY** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Herramienta de Reporte de Informes BI |
| 27 | **PORTALES** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Site donde estará alojada la nueva Home y los nuevos portales, que usarán la tecnología OWCS (Oracle WebCenter Sites). |
| 28 | **SDS-RS** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Administración de la aplicación SDS |
| 29 | **SFTP** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Sistema donde se configuran los servicio SFTP para las diferentes aplicaciones de proveedores externos |
| 30 | **TA PARTNERS** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | Transversal / BIA O&M | Portal y gestión operativa para colaboradores y partners comerciales. |
| 31 | **VPM** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | FRAUDE | Portal de venta al por mayor, exclusivo para clientes wholesales, para la gestión de sus productos de telefonía (voz, da |
| 32 | **WEB DE COMPROBANTES** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, FRAUDE, Seguro Móvil | Herramienta para el registro y tramitacion de los comprobantes de venta asociados |
| 33 | **BIG QUERY** | Multimarca | 3.2 Ventas / Analítica | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, Gestion Capacidad, Gestión de pruebas IT | Plataforma analítica y almacén de datos Cloud (Google BigQuery) para procesos comerciales, capacidad y pruebas IT. |
| 34 | **CACHE DISTRIBUIDA DE CLIENTE** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION, VENDER PRODUCTOS Y SERVICIOS | Monetizar datos de clientes de Telco, tras consentimiento del cliente, para el cálculo de un Credit Scoring de individuo |
| 35 | **DISCRIMINADOR** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION | Esta aplicación permitirá al agente conocer la herramienta de contratación que tiene que utilizar . |
| 36 | **FDTT** | Multimarca | 3.5 Provisión | `PRV-P2-02` | `SOP_TEC_PROVISION` | Transversal / BIA O&M | Aplicativo técnico registrado en BIA corporativo con Criticidad BIAS 5. |
| 37 | **HELIO** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION | Sistema que maneja todas las peticiones que Orange envia a NEON (herramienta de Telefonica para manejar a los operadores |
| 38 | **ICFM** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION | Herramienta para realizar operativas en la gestión de activaciones; liberación de SIM/MSISDN |
| 39 | **OPERADOR LOGISTICO** | JAZZTEL | 3.5 Provisión | `PRV-P2-02` | `SOP_TEC_PROVISION` | Seguro Móvil | Integración operativa con el operador logístico para envíos de terminales, equipamiento y Seguro Móvil. |
| 40 | **PHYSIS** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Inventario de Red para Jazztel |
| 41 | **PROVISION WHOLESALE** | JAZZTEL | 3.5 Provisión | `PRV-P2-02` | `SOP_TEC_PROVISION` | Transversal / BIA O&M | Plataforma de provisión mayorista (Wholesale) para operadores sobre red fija. |
| 42 | **WEB LOGISTICA Y PROCESOS** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `GIS_FIBRA_N2` | PROVISION, FRAUDE | Portal para el control de stock de las instalaciones de las contratas y los envíos que realiza el operador logístico a l |
| 43 | **BLACK-LIST** | ORANGE | 3.6 / Fraude | `FAC-P2-01` | `HPFMS_SUPP` | VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Blacklist de Scoring. Repositorio de lista negra de tarjetas, teléfonos. Consultado por operaciones de recarga, recobro, |
| 44 | **DIGO** | ORANGE | 3.6 / Fraude | `FAC-P2-01` | `HPFMS_SUPP` | FRAUDE | Aplicación operativa vinculada a validaciones y controles del pilar de Fraude (RTO 4h). |
| 45 | **HUNTER** | ORANGE | 3.6 / Fraude | `FAC-P2-01` | `HPFMS_SUPP` | VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Herramienta antifraude. El sistema actual de Scoring se conectará a Hunter, para detectar de modo on-line en el momento |
| 46 | **KYC ONLINE IDENTITY** | ORANGE | 3.6 / Fraude | `FAC-P2-01` | `HPFMS_SUPP` | FRAUDE | Sistema de verificación digital de identidad de cliente (Know Your Customer) en procesos online contra el fraude. |
| 47 | **RAID** | Multimarca | 3.6 / Fraude | `FAC-P2-01` | `HPFMS_SUPP` | Transversal / BIA O&M | Herramienta de Revenue Assurance. Controla la cadena de ingresos para prevenir pérdidas. Se ha unificado la parte movil |
| 48 | **SGRT** | ORANGE | 3.6 / Fraude | `FAC-P2-01` | `HPFMS_SUPP` | ATENCIÓN AL CLIENTE | Gestión y bloqueo de terminales robados. |
| 49 | **ACCON** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | ATENCIÓN AL CLIENTE, COBROS | Aplicación para la gestión operativa del departamento de cobros y recobros de OSP Movil. La parte de fijo está en ARES. |
| 50 | **ALMACEN LOGS** | JAZZTEL | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE | Almacen Logs |
| 51 | **ARES** | JAZZTEL | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | ATENCIÓN AL CLIENTE, COBROS | Nuevo sistema de gestión del recobro. |
| 52 | **BUSINESS OBJECTS** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Principal herramienta de realización de informes en FT España |
| 53 | **OPENCOBROS** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Sistema responsable de la gestión del cobro y recobro de los recibos facturados a clientes finales de Orange (AMENA) y p |
| 54 | **TPVs** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | COBROS | Recobro de pagos por tarjeta. |
| 55 | **EXPERIENCE LAYER** | Multimarca | 3.7 Middleware | `MID-P2-02` | `GC_MIDDLEWARE_OPS` | Transversal / BIA O&M | Capa de exposición y desacoplamiento de APIs de experiencia para frontales digitales Multimarca. |
| 56 | **MIDDLEWARE PLATAFORMA DE ACCESO** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE | Middleware Sistemas Plataforma de Acceso de Sistemas de Altitude. |
| 57 | **MIDDLEWARE SISTEMAS OSS** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE | OSB ingenieria. Middleware Sistemas OSS |
| 58 | **WS INTERMEDIOS DE REMEDY** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS | Aplicación desde la cual se puede consultar/crear incidencias Remedy, gestionar ordenes de trabajo y gestionar incidenci |
| 59 | **VPN CORPORATIVA** | ORANGE | 3.8 Redes / Sedes | `RED-P2-01` | `SOP_NET_WAN_SEDES` | Transversal / BIA O&M | Servicio de acceso remoto seguro (VPN) a la red corporativa para empleados y operación técnica. |
| 60 | **CITRIX - CONTROL** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_SYS_POWER9` | COBROS, FRAUDE | Servidores para control de todas las granjas Citrix (Data Store, Data Collector, XML y Licencias) |
| 61 | **CITRIX - OFFSHORE** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_SYS_POWER9` | Transversal / BIA O&M | Granja de servidores Citrix que da servicio a Off Shore |
| 62 | **SERVIDORES DE FICHEROS** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_SAN_STORAGE` | VENDER PRODUCTOS Y SERVICIOS | La NAS de Orange. |
| 63 | **QLIKVIEW** | ORANGE | O&M / Analítica | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Plataforma de inteligencia de negocio y cuadros de mando analíticos. |
| 64 | **ARTIFACTORY** | Multimarca | O&M / DevSecOps | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Repositorio corporativo de artefactos binarios, paquetes e imágenes de contenedores. |
| 65 | **CLARIVE** | Multimarca | O&M / DevSecOps | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Configuración del Software | Herramienta ALM de automatización de pases a producción y Configuración del Software. |
| 66 | **GITHUB** | Multimarca | O&M / DevSecOps | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Plataforma corporativa de repositorios de código fuente e integración continua (CI/CD). |
| 67 | **OBSERVABILITY AND MONITORING** | Multimarca | O&M / Observabilidad | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Gestion Capacidad, Gestionar Incidencias | Plataforma unificada de observabilidad y monitorización para Gestión de Incidencias y Capacidad. |
| 68 | **PROMETHEUS** | ORANGE | O&M / Observabilidad | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Sistema de monitorización de métricas y series temporales para infraestructura y plataformas Cloud. |
| 69 | **TORRE DE CONTROL** | Multimarca | O&M / Observabilidad | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Cuadro de mando y supervisión extremo a extremo de operaciones y procesos tecnológicos. |
| 70 | **BIBLIOTECA DOCUMENTAL SSII** | Multimarca | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Repositorio documental oficial de Sistemas de Información. |
| 71 | **CLU** | Multimarca | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Aplicativo transversal registrado en BIA corporativo (Criticidad Sistemas 4). |
| 72 | **CONFLUENCE NODUS** | Multimarca | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Gestión de pruebas IT | Repositorio documental colaborativo Nodus vinculado a Gestión de pruebas IT. |
| 73 | **DISCOVERY CMDB** | ORANGE | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Gestión de la configuración | Descubrimiento automático de activos e inventario para la Gestión de la Configuración (CMDB). |
| 74 | **GESTION DE RFS** | ORANGE | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Aplicación para la gestión y tramitación de peticiones de servicio (Request for Service). |
| 75 | **HADES** | ORANGE | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Aplicativo interno registrado en BIA corporativo (Criticidad 2, RTO 72h). |
| 76 | **JIRA NODUS** | Multimarca | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Gestion Capacidad, Configuración del Software, Gestión de pruebas IT | Instancia Jira Nodus para seguimiento de proyectos, capacidad, configuración SW y pruebas IT. |
| 77 | **NOSOTROS** | ORANGE | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Portal corporativo del empleado y gestor de contenidos internos (anteriormente ViveOrange). |
| 78 | **OFFICE 365** | Multimarca | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Gestión de Problemas | Suite colaborativa corporativa en la nube (correo, Teams y ofimática) vinculada a Gestión de Problemas. |
| 79 | **SIRO** | Multimarca | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Sistema operativo transversal incluido en BIA con Criticidad Sistemas 5. |
| 80 | **THADEA** | ORANGE | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Sistema incluido en BIA corporativo con Criticidad Sistemas 5 y RTO 24h. |
| 81 | **TIGRETON** | Multimarca | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / BIA O&M | Aplicativo transversal incluido en BIA corporativo con Criticidad Sistemas 5. |
| 82 | **OCEANE** | Multimarca | O&M / Ticketing | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Ciber protección red móvil, Móviles | Herramienta corporativa de ticketing y gestión de incidencias de red móvil, ciberprotección y empresas. |

---

## 6. Glosario Canónico de Acrónimos y Términos Operacionales de Orange / Jazztel / Multimarca

Para erradicar cualquier ambigüedad en el triaje de tickets y notas de trabajo, la IA debe aplicar las siguientes equivalencias operativas oficiales:

1. **POMV (Provisión Móvil):** Sistema central de provisión de líneas de telefonía móvil de Jazztel y Orange. Gestiona altas, cambios de SIM y activación de bonos.
2. **SPM / TRAMITADOR (Provisión Masivo):** Sistema de tramitación y provisión masiva de clientes residenciales y SOHO en Jazztel.
3. **AFS FIJO / AURORA:** Motor TIBCO AFS (Automated Fulfillment System) para la orquestación y provisión de servicios FTTH (fibra óptica, datos y TV).
4. **OWCS (Oracle WebCenter Sites):** Plataforma CMS corporativa de gestión de contenidos y publicación de portales comerciales y canales web unificados (`PANGEA`, `PUBLICACION`, `PORTALES`).
5. **vPAW (Virtual Privileged Access Workstation):** Granja VDI de Microsoft con PCs virtuales reforzados de salto obligatorio para tareas de administración remota en servidores Windows de producción.
6. **SOE (Service Oriented Enterprise):** Arquitectura estándar de exposición de servicios comerciales y frontales unificados sobre la que corren `FICHA DE CLIENTE` y la capa de integración de agentes.
7. **EAI / WM (Enterprise Application Integration / webMethods):** Bus de middleware histórico Wanadoo/Orange responsable de suspensiones, reactivaciones y bajas masivas de jerarquías de clientes.
8. **SGP (Sistema de Gestión de Portabilidades):** Motor oficial de tramitación de portabilidades móviles (`SGP MOVIL`) y comunicación con la Entidad de Referencia de otros operadores.
9. **BRM (Billing and Revenue Management):** Plataforma Oracle BRM dedicada a facturación rectificativa móvil (`ABACUS BRM`) y facturación de plataformas M2M (`BRM PORTAL M2M`).
10. **KFX / KENAN_FX:** Motor de facturación, tarificación y mediación para clientes y servicios de tecnología fija, datos y empresas en Orange y Jazztel.
11. **CC CTI (Contact Center Computer Telephony Integration):** Pasarela de integración entre telefonía y software de agente para el enrutamiento inteligente de llamadas en centros de atención propios y proveedores externos.
12. **PCNEON OBA:** Plataforma de Comunicaciones con NEON (Telefónica) para la gestión automatizada de bucle de abonado (OBA) y AMLT.
13. **OAM (Oracle Access Manager):** Infraestructura de Single Sign-On (`SSO OAM`) corporativo para el control de acceso y autenticación federada en portales internos.
14. **MDG (Master Data Governance):** Plataforma de caché unificada que ofrece la visión global 360 del cliente (`MDG COH` / `MDG GG`) para consulta inmediata de frontales sin penalizar los BSS transaccionales.
15. **EPSILON:** Plataforma corporativa de gestión ITSM Multimarca sobre arquitectura ITIL (Gestión de Incidencias, Cambios, Problemas, CMDB y Acuerdos de Nivel de Servicio).
16. **MAGALLANES:** Plataforma estratégica de convergencia comercial y de atención Multimarca catalogada como `CORE++`.

---

## 7. Directrices de Triaje y Tratamiento de Discrepancias en BMC Remedy

1. **Prevalencia del Impacto sobre el Aplicativo:** Si un ticket describe una caída en un sistema `CORE++` (ej. `BSCS`, `BOREAL`, `AURORA`, `MAGALLANES`, `ESHOP FRONTEND` u `OPENAPI`) pero la cola asignada es genérica (ej. `SERVICE_DESK_N1` o `SOPORTE_GENERICO`), el sistema de triaje **debe ignorar la cola y clasificar la incidencia como SL1 / P1 de forma inmediata**.
2. **Elevación Automática por Cola Técnica Especializada:** La recepción de una incidencia con términos de corte de servicio en colas especializadas (`SOP_BSCS_BILLING`, `SOP_TMC_APIGEE`, `SOP_TIBCO_ESB`, `POMV`, `OCS_MEDIATION`, `SOP_GDU_IDENTITY`) confirma la criticidad objetiva y descarta cualquier rebaja a P3/P4.
3. **Escalado en Paralelo en Sistemas Transversales:** Toda incidencia en componentes de integración `CORE++` (`OPENAPI`, `TIBCO`, `MICROSERVICIOS`) requiere la convocatoria simultánea de los grupos de infraestructura y de los aplicativos de negocio consumidores.

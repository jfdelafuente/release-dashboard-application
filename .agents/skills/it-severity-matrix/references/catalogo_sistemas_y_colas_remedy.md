# Catálogo Canónico de Sistemas, Aplicativos y Colas BMC Remedy (Orange / Jazztel)

Este documento constituye el **Inventario Canónico de Sistemas, Aplicativos y Colas Operativas en BMC Remedy ITSM**, basado en el catálogo oficial de criticidad de Orange Tech Operations (`catalogo-aplicaciones-criticas.csv`). Actúa como la **Fuente Única de Verdad (SSOT)** para la desambiguación técnica y determinación determinista de criticidad de las skills `it-severity-matrix` y `orange-it-emergency-management`.

> [!IMPORTANT]
> **Directriz de Carga Bajo Demanda (On-Demand Loading):** Este documento debe ser leído por la IA mediante `read_file` únicamente cuando se requiera desambiguar un subsistema técnico, asociar un aplicativo a su sección canónica (3.1 a 3.10), verificar su nivel oficial (`CORE++` vs `CORE`) o resolver la correspondencia con una cola Remedy (`grupo_asignado`).

---

## 1. Framework de Gobernanza de Criticidad y Tiers de Aplicaciones

El catálogo corporativo clasifica los sistemas en tres niveles estrictos de criticidad:

| Tier | Categoría Oficial | Volumen | Definición Operativa | Suelo Determinista de Severidad |
| :---: | :--- | :---: | :--- | :---: |
| **Tier 0** | **`CORE++`** | **39** | **Núcleo Neurálgico Ultra-Crítico:** Aplicativos indispensables para la operativa masiva (CRM, Ficha de Cliente, Call Center CTI/IVR, Facturación Pospago BSCS, Provisión Core Móvil/Fijo Boreal/Aurora/Luna, APIGEE/TIBCO, Autenticación Identity/LDAP). Su caída paraliza de inmediato la atención o el negocio. | **SL1 / P1**<br/>(Corte total o bloqueo operativo) |
| **Tier 1** | **`CORE`** | **81** | **Sistemas Críticos de Soporte y Transaccionales:** Facturación fija/datos (Kenan_FX), mediación, tarificación prepago (APRS/TAO/OCS), portabilidades (PORTOS/SGP MOVIL), provisión especializada (POMV/Tramitador SPM/PCNEON), ventas (Pangea/Ceres/Econtrato), middleware (WebMethods/Datapower) y control de fraude (HPFMS/Scoring). | **SL1 / P1** (sin contingencia)<br/>**SL2 / P2** (con HA activa o degradación acotada) |
| **Tier 2** | **`Non-CORE con Pilares`** | **66** | **Aplicaciones Especializadas / Departamentales:** Aplicativos que soportan procesos de alguno de los 6 pilares clave de negocio (Cobros/Recobros como OpenCobros/ARES, gestión de riesgo Hunter/Blacklist, gestión de identidades GDU, citas en campo Polar, o autoservicio de contraseñas). | **SL2 / P2** o según umbrales de proceso en Secciones 3.1 a 3.10 |

---

## 2. Mapeo Canónico de los 6 Pilares Corporativos vs Dominios Técnicos (3.1 a 3.10)

| Pilar Corporativo (CSV) | Dominio Funcional / Técnico | Códigos Canónicos | Aplicativos Clave en el Catálogo | Suelo Nominal |
| :--- | :--- | :--- | :--- | :---: |
| **Atención al Cliente** | **3.1 ATC** | `ATC-P1-01..03`<br/>`ATC-P2-01..02` | `CALL CENTER CTI`, `IVR`, `FICHA DE CLIENTE`, `IRIS`, `CRM4TELCO`, `ACME APP/WEB ORANGE`, `ALTAMIRA`, `MIJAZZTEL`, `POLAR` | **SL1 / P1** si es `CORE++` o colapso >20% en 30m |
| **Vender Productos y Servicios** | **3.2 Ventas y Contratación** | `VNT-P1-01..03`<br/>`VNT-P2-01..02` | `PANGEA`, `KRATOS`, `CERESRT`, `CERES`, `AGORA`, `ALCE`, `ARPA`, `ECONTRATO`, `SEDNA`, `SIGNA`, `SITAM`, `XNET` | **SL1 / P1** si bloqueo comercial o afectación >30% volumen |
| **Provisión (Portabilidad)** | **3.3 Portabilidad** | `POR-P1-01..03`<br/>`POR-P2-01` | `PORTOS` (Fijo), `SGP MOVIL` (Móvil), `PANGEA`, `TEIDE` | **SL1 / P1** en flujo 2 AM o retraso >2h con entidad referencia |
| **Facturación / Cobros (Prepago)**| **3.4 Prepago** | `PRE-P1-01..02`<br/>`PRE-P2-01` | `APRS`, `TAO`, `OCS`, `SEDNA`, `PCRF_GW` | **SL1 / P1** si >10% errores recargas o >30m sin actividad |
| **Provisión** | **3.5 Provisión y Cobertura** | `PRV-P1-01..03`<br/>`PRV-P2-01..02` | `BOREAL`, `AURORA` (AFS Fijo), `LUNA`, `SIGMA`, `GIROS`, `TEIDE`, `ALTAIR`, `MYADDRESS`, `POMV`, `TRAMITADOR (SPM)` | **SL1 / P1** si corte en provisión móvil (>20%) o fija (>30%) |
| **Facturación** y **Cobros** | **3.6 Facturación y Cobros** | `FAC-P1-01..03`<br/>`FAC-P2-01` | `BSCS`, `KENAN_FX`, `MEDIACION`, `ABACUS BRM`, `BRM M2M`, `COBROS_KFX`, `NETPLUS`, `PSP`, `INTRANSIT`, `XPRESSION`, `FEW` | **SL1 / P1** si corte tarificación >3h o retraso ciclo >1 día |
| **Fraude** | **3.6 / Riesgo Transaccional** | `FAC-P1-03`<br/>`VNT-P1-01` | `HPFMS`, `SCORING`, `COCO`, `HUNTER`, `BLACK-LIST`, `ALEGACIONES`, `RAID`, `AVENEW` | **SL1 / P1** si parada de motores de riesgo en contratación |
| **Transversal Middleware** | **3.7 Middleware Transversal** | `MID-P1-01..02`<br/>`MID-P2-01..02` | `OPENAPI` (APIGEE), `TIBCO`, `MICROSERVICIOS`, `TIBCO-OMV`, `WEBMETHODS`, `DATAPOWER`, `MIDDLEWARE MQ CRM4T` | **SL1 / P1** (Corte transversal con Escalado en Paralelo) |
| **Transversal Infraestructura**| **3.9 Infraestructura Core / Cloud** | `INF-P1-01..03`<br/>`INF-P2-01` | `ELEMENTOS DE ALMACENAMIENTO`, `ADMINISTRACION - DBA`, `VMWARE`, `GRANJA VPAW`, `CITRIX`, `DNS` | **SL1** (Sin HA) / **SL2** (Con HA activa) |
| **Transversal Identidad** | **3.10 Identidad y Automatización** | `IDE-P1-01..02`<br/>`IDE-P2-01..02` | `LDAP CORPORATIVO`, `IDENTITY`, `SSO OAM`, `GDU`, `CONTROLADOR DOMINIO/DA`, `ADSELFSERVICE`, `RPA NICE` | **SL1 / P1** (Caída global SSO/LDAP o parada RobotFactory) |

---

## 3. Inventario Canónico de Aplicaciones CORE++ (Tier 0 — 39 Aplicaciones Ultra-Críticas)

Toda indisponibilidad total o afectación de flujo operativo en estos sistemas impone de forma determinista el suelo **`SL1 / P1`**.

| # | Aplicativo | Operadora | Dominio Canónico | Código | Cola BMC Remedy | Pilares Corporativos | Función Operativa Oficial |
| :-: | :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| 1 | **ACME APP ORANGE** | ORANGE | 3.1 ATC | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN | Área privada del cliente de Orange. Acceso para ver su consumo, contrato, factura y productos contratados a través de Ap |
| 2 | **ACME WEB ORANGE** | ORANGE | 3.1 ATC | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN | Área privada del cliente de Orange. Acceso para ver su consumo, contrato, factura y productos contratados a través de We |
| 3 | **ALTAMIRA** | ORANGE | 3.1 ATC | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN | Parte de la aplicación del Frontal Comercial Unificado para Orange España. Esta aplicación reemplaza al actual eShop par |
| 4 | **AMON** | ORANGE | 3.1 ATC | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | FACTURACIÓN | Área privada del cliente. Acceso para los clientes a un espacio donde poder consultar sus datos, las facturas, el consum |
| 5 | **ATENAS** | JAZZTEL | 3.1 ATC | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN | Nueva tienda online de Jazztel bajo arquitectura SOE |
| 6 | **CALL CENTER CTI** | ORANGE | 3.1 ATC | `ATC-P1-01` | `SOP_TECNICO_CALL_CENTER` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Plataforma de Contact_center desplegada en centros internos y proveedores externos para la gestión de llamadas. Tiene co |
| 7 | **CRM4TELCO** | JAZZTEL | 3.1 ATC | `ATC-P1-02` | `SOP_CRM4TELCO` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | CRM de Jazztel. BD de Clientes de Masivo y ciertos servicios de Empresas. Servicio VIP de Venta y Atención |
| 8 | **FICHA CLIENTE** | JAZZTEL | 3.1 ATC | `ATC-P1-02` | `SOP_CRM4TELCO` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Acceso uniforme a diversos sistemas y presentación unificada en una única ficha. |
| 9 | **FICHA DE CLIENTE** | ORANGE | 3.1 ATC | `ATC-P1-02` | `DES_SOE_FICHA` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Esta aplicación permitirá al agente visualizar la información necesaria del cliente para que, en los primeros segundos d |
| 10 | **IRIS** | Multimarca | 3.1 ATC | `ATC-P1-02` | `DES_SOE_FICHA` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS | Sistema de vista 360 del cliente. |
| 11 | **IVR** | ORANGE | 3.1 ATC | `ATC-P1-01` | `SOP_TECNICO_CALL_CENTER` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | El sistema IVR es el servicio de atención automática al cliente final. |
| 12 | **MIJAZZTEL** | ORANGE | 3.1 ATC | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | Transversal / O&M | Área privada del cliente. Acceso para los clientes a un espacio donde poder consultar sus datos, las facturas, el consum |
| 13 | **PUBLICACION** | ORANGE | 3.1 ATC | `ATC-P2-01` | `SOP_IT_OPERACIONES` | ATENCIÓN AL CLIENTE | Nuevo portal para la actividad de gestión y publicación de contenidos relativos a los sites (OWCS) existentes en el ámbi |
| 14 | **HESMS** | ORANGE | 3.1 ATC / Notificaciones | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE, COBROS, FACTURACIÓN | El sistema HESMS Multicanal es encargado de realizar los envíos de las campañas de marketing a la cartera de clientes de |
| 15 | **SIRES** | ORANGE | 3.1 ATC / Notificaciones | `ATC-P1-03` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Sistema centralizado de envío de mensajes. Centraliza la gestión/envío de las comunicaciones SMS/Email/Notificaciones a  |
| 16 | **IDENTITY** | ORANGE | 3.10 Identidad | `IDE-P1-01` | `SOP_GDU_IDENTITY` | VENDER PRODUCTOS Y SERVICIOS, COBROS | Herramienta de autenticación y logado unificado de los sistemas de front-end de OSP. Identity concilia la información de |
| 17 | **LDAP CORPORATIVO** | ORANGE | 3.10 Identidad | `IDE-P1-01` | `SOP_GDU_IDENTITY` | Transversal / O&M | Repositorio de usuarios y perfiles que valida la autenticación de acceso de los usuarios a las aplicaciones. |
| 18 | **SSO OAM** | ORANGE | 3.10 Identidad | `IDE-P1-01` | `SOP_EVIDIAN_SSO` | Transversal / O&M | Oracle Single Sign On (OAM) |
| 19 | **CERESRT** | ORANGE | 3.2 Ventas | `VNT-P1-01` | `NEG_CAMP_CERES` | VENDER PRODUCTOS Y SERVICIOS | Aplicación para la gestión y ejecución de Campañas que permite automatizar una relación individualizada con nuestros cli |
| 20 | **KRATOS** | ORANGE | 3.2 Ventas | `VNT-P1-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Aplicación que contiene la réplica del catálogo comercial y las reglas necesarias para que el Frontal Comercial Unificad |
| 21 | **PANGEA** | ORANGE | 3.2 Ventas | `VNT-P1-01` | `PANGEA_SUPP` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS | Aplicación de frontal unificado para Orange España. Esta aplicación reemplaza nuestros portales comerciales actuales (es |
| 22 | **GED MOVIL Y FIJO** | ORANGE | 3.2 Ventas / Documental | `VNT-P1-01` | `SOP_COMERCIAL_N2` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FACTURACIÓN, FRAUDE | Sistema de gestión documental, encargado de la carga, almacenamiento y consulta de diferentes tipologías de documentació |
| 23 | **ALTAIR** | ORANGE | 3.5 Provisión | `PRV-P1-01` | `ALTAIR_SUPP` | ATENCIÓN AL CLIENTE, PROVISION, FACTURACIÓN, FRAUDE | Heramienta consolidada de Test&Diagnóstico para realizar el aseguramiento del servicio a los clientes |
| 24 | **AURORA** | ORANGE | 3.5 Provisión | `PRV-P1-01` | `SOP_TEC_PROVISION` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN | TIBCO AFS FIJO . Sistema de Provisión de Fijo FTTH. Sistema de orquestación y provisión de servicios de telefonía fija,  |
| 25 | **BOREAL** | ORANGE | 3.5 Provisión | `PRV-P1-01` | `POMV` | PROVISION, VENDER PRODUCTOS Y SERVICIOS | Sistema de Provisión de Móvil |
| 26 | **GIROS** | Multimarca | 3.5 Provisión | `PRV-P1-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, FRAUDE | Sistema para la gestión integrada del inventario de recursos de Orange Spain. |
| 27 | **LUNA** | ORANGE | 3.5 Provisión | `PRV-P1-01` | `Fijo Activacion LUNA` | ATENCIÓN AL CLIENTE, PROVISION, COBROS, FRAUDE | Sistema de activación del fijo |
| 28 | **MYADDRESS** | ORANGE | 3.5 Provisión | `PRV-P1-01` | `SOP_TEC_PROVISION` | VENDER PRODUCTOS Y SERVICIOS, COBROS | Normalización de direcciones en tiempo real y por lotes, localización en mapa, sirviendo información acerca de la direcc |
| 29 | **SIGMA** | ORANGE | 3.5 Provisión | `PRV-P1-01` | `SOP_TMC_SIGMA` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | SIGMA operacional es el gestor de recursos de la red del dominio móvil. Maestro de numeración, Maestro de terminales, Ma |
| 30 | **TEIDE** | ORANGE | 3.5 Provisión | `PRV-P1-01` | `SOP_SMC_TEIDE` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Sistema cuya principal funcionalidad es la contratación y aprovisionamiento de líneas telefónicas móviles junto a los se |
| 31 | **BSCS** | ORANGE | 3.6 Facturación | `FAC-P1-01` | `SOP_BSCS_BILLING` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FACTURACIÓN, FRAUDE | Sistema de Facturación Pospago (Postpaid billing and customer care solution.) |
| 32 | **FEW** | ORANGE | 3.6 Facturación | `FAC-P1-01` | `SOP_BSCS_BILLING` | VENDER PRODUCTOS Y SERVICIOS | Sistema encargado de ofrecer la factura electrónica e informes de factura a nuestros clientes. |
| 33 | **MDG COH** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS | Sistema con toda la información de cliente (Fijo y Móvil) disponible online en cahe para consulta por cualquier sistema  |
| 34 | **MICROSERVICIOS** | ORANGE | 3.7 Middleware | `MID-P1-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS | Aplicación para la exposición de APIs para la utilización por parte de servicios que lleven a cabo funcionalidades muy c |
| 35 | **OPENAPI** | ORANGE | 3.7 Middleware | `MID-P1-01` | `SOP_TMC_APIGEE` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | APIGEE. OpenAPI implementa el estándar TMF de APIs dentro Orange España. Habilita una arquitectura cloud native y ciclo  |
| 36 | **TIBCO** | ORANGE | 3.7 Middleware | `MID-P1-01` | `SOP_TIBCO_ESB` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | EAI (Middleware). Middleware de Orange. No soporta gestión de ficheros entre interfaces via BATCH. |
| 37 | **TIBCO-OMV** | ORANGE | 3.7 Middleware | `MID-P1-01` | `SOP_TIBCO_ESB` | Transversal / O&M | Plataforma específica de MDW para realizar comunicaciones on-line de los sistemas que gestionan los Operadores Móviles V |
| 38 | **PORTAL DE REDES** | ORANGE | 3.8 Redes / Sedes | `RED-P1-01` | `SOP_NET_WAN_SEDES` | Transversal / O&M | PORTAL DE REDES es un portal que permite un acceso unico a las aplicaciones de red con single sign on, dotando de fucion |
| 39 | **ELEMENTOS DE ALMACENAMIENTO** | ORANGE | 3.9 Infraestructura | `INF-P1-01` | `SOP_SAN_STORAGE` | Transversal / O&M | ELEMENTOS DE ALMACENAMIENTO |

---

## 4. Inventario Canónico de Aplicaciones CORE (Tier 1 — 81 Aplicaciones Críticas)

Afectación sin contingencia activa **`SL1 / P1`**; afectación con redundancia activa o degradación acotada activa **`SL2 / P2`**.

| # | Aplicativo | Operadora | Dominio Canónico | Código | Cola BMC Remedy | Pilares Corporativos | Función Operativa Oficial |
| :-: | :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| 1 | **AREA PRIVADA CLIENTES** | JAZZTEL | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | PROVISION, FACTURACIÓN | Servicio web a través del que los clientes acceden a su propio perfil para consultar/modificar parámetros relacionados c |
| 2 | **GUIS** | ORANGE | 3.1 ATC | `ATC-P1-02` | `DES_SOE_FICHA` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Interfaz Gráfico de Usuario para Call Centers. |
| 3 | **PEOPLESOFT CRM** | ORANGE | 3.1 ATC | `ATC-P1-02` | `SOP_PEOPLESOFT_N2` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Soporte a clientes Servicios de campo Marketing y ventas |
| 4 | **PEOPLESOFT JZZ** | JAZZTEL | 3.1 ATC | `ATC-P2-01` | `DES_SOE_FICHA` | ATENCIÓN AL CLIENTE | Plataforma de Gestión Financiera y de Recursos Humanos de Jazztel |
| 5 | **PROMOSMS** | ORANGE | 3.1 ATC | `ATC-P1-01` | `SOP_IT_OPERACIONES` | Transversal / O&M | PROMOSMS permite la recepción de mensajes enviados por los clientes para realizar un procesado de la información e inter |
| 6 | **SIEBEL** | ORANGE | 3.1 ATC | `ATC-P1-02` | `SOP_CRM_SIEBEL` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Ventana única para la gestión de clientes y distribuidores, proporcionando una visión completa del perfil y comportamien |
| 7 | **CONTROLADOR DE DOMINIO/DA** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `SOP_GDU_IDENTITY` | ATENCIÓN AL CLIENTE | Directorio Activo Común |
| 8 | **DIRECTORIO ACTIVO** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `SOP_GDU_IDENTITY` | Transversal / O&M | Servidores que dan servicio de Red |
| 9 | **AGORA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN | Creado como una extensión del nuevo CRM de la compañía, pretende dotar al canal de distribución de las herramientas nece |
| 10 | **ALCE** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN | Herramienta de gestión de ventas de productos móviles para clientes empresariales |
| 11 | **ARPA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN | Sistema dirigido principalmente a distribuidores que les permite creación de contratos, la activación on-line de líneas  |
| 12 | **CATALOGO CORPORATIVO** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | Transversal / O&M | Catálogo corporativo de todas las ofertas de fijo (acceso + voz fija + bundles) que no sean sólo de voz (esta la lleva X |
| 13 | **CERES** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `NEG_CAMP_CERES` | VENDER PRODUCTOS Y SERVICIOS | Aplicación para la gestión y ejecución de Campañas que permite automatizar una relación individualizada con nuestros cli |
| 14 | **ECONTRATO** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `Econtrato_N2` | FRAUDE | Firma digital de documentos en tiendas Orange y control de fraude documental |
| 15 | **PAE** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Aplicación destinada al cliente final para segmento empresas orientada a la autogestión de sus productos y servicios. |
| 16 | **SIGNA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Permitirá a los comerciales de PYMES elaborar ofertas y firmar digitalmente el contrato en movilidad |
| 17 | **SITAM** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | SITAM (Sistema de Interfaces de Orange-España) es el sistema que a partir de datos réplica de BSCS, proporciona el nivel |
| 18 | **XNET** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Extranet de ventas fijo. Herramienta Web unificada para la gestión de contratación de productos de telefonía fija para c |
| 19 | **PORTOS** | ORANGE | 3.3 Portabilidad | `POR-P1-01` | `PORTA_N2_FIXED` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS | Sistema de gestión de portabilidad del mercado fijo |
| 20 | **SGP MOVIL** | ORANGE | 3.3 Portabilidad | `POR-P1-01` | `PORTA_N2_MOBILE` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Sistema que gestiona las portabilidades numéricas y el ciclo de vida de su comunicación a otros operadores y terceras en |
| 21 | **APRS** | ORANGE | 3.4 Prepago | `PRE-P1-01` | `RECARGAS_APRS_SUPP` | FACTURACIÓN | Ecargada de gestionar las peticiones de recarga que le llegan por línea x25 de las entidades bancarias, y de la gestión  |
| 22 | **OCS** | Multimarca | 3.4 Prepago | `PRE-P1-01` | `OCS_PREPAID_N2` | FACTURACIÓN, FRAUDE | OCS es el tarificador online de datos en Orange España de los cliente Amena y Orange de móvil. |
| 23 | **PCRF_GW** | ORANGE | 3.4 Prepago | `PRE-P1-01` | `OCS_PREPAID_N2` | Transversal / O&M | Pasarela para la gestión dinámica de políticas y reglas de charging de datos |
| 24 | **SEDNA** | ORANGE | 3.4 Prepago | `PRE-P1-01` | `OCS_PREPAID_N2` | VENDER PRODUCTOS Y SERVICIOS | SEDNA es el sistema que proporciona el front-end con los sistemas de los clientes prepago (TAO y TA) |
| 25 | **TAO** | ORANGE | 3.4 Prepago | `PRE-P1-01` | `OCS_PREPAID_N2` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FACTURACIÓN, FRAUDE | Realizar la gestión del ciclo de vida del cliente prepago, tarificación de los servicios que consume y gestión del saldo |
| 26 | **APOLO WORKFLOW EMPRESAS** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION, FACTURACIÓN | Workflow de provisión de servicios de Empresas |
| 27 | **GESTION DE INCIDENCIAS** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | Transversal / O&M | Herramienta corporativa de gestión de incidencias, problemas y solicitudes de NEGOCIO. Utilizada principalmete para la p |
| 28 | **LYRA** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | FRAUDE | Aplicación para la provisión de productos PYME sobre acceso de banda ancha. |
| 29 | **NABOO** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS | Sistema de análisis de los eventos de provisión, entre ellos mobile connect. |
| 30 | **PCNEON OBA** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION | Plataforma de Comunicaciones con NEON – OBA. La plataforma PCN (Plataforma de Comunicaciones con NEON) hace funciones de |
| 31 | **PROVISION MOVIL** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `POMV` | PROVISION | POMV. Sistema de Provisión de Clientes de Móvil |
| 32 | **RESER** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | Transversal / O&M | RESER proporciona el Repositorio de Servicios de Red asociado a las líneas, llevando a cabo tareas de provision de servi |
| 33 | **REVENTA FIBRA ISP** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION | Provisión de fibra de clientes Orange en Red Jazztel |
| 34 | **SAO** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | Transversal / O&M | SAO - Sistema de auditorias online. Audita tdos los sistemas de la empresa para asegurar la calidad de los datos de nego |
| 35 | **SAP** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION | Herramienta de gestión de todas las áreas corporativas (Finanzas, Control, Compras, RRHH, Logística, Servicios Generales |
| 36 | **SARO** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, FRAUDE | Sistema auditorias y regularizaciones online de provisión (SARO) |
| 37 | **SDM** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS | Sistema para la gestión y mantenimiento de MSISDNs y de los repositorios de servicios y parmetros para OMVs y M2M |
| 38 | **SEDRA** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | Transversal / O&M | SEDRA es el Sistema de Seguimiento del Despliegue de Red de FTSpain en el dominio móvil. |
| 39 | **SGA** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, FRAUDE | Servicio que contiene el inventario de las sim's de prepago de Wholesale. |
| 40 | **SGF** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Sistema de ejecución de campañas responsable de la logística asociada.  Por otra parte proporciona una Web de contingenc |
| 41 | **SGL** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION | Sistema de Gestión de Logística |
| 42 | **SGR** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION | Sistema de Gestión de Recursos de numeración y pares de TFCA |
| 43 | **SIEBEL - M2M** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Ventana única para la gestión de clientes y lineas M2M que contiene: datos de clientes y personas de contacto, Gestión d |
| 44 | **TRAMITADOR** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION | Sistema de Provisión de Clientes de Masivo (SPM) |
| 45 | **WEB MANTENEDORES** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Web de adminstración de OT (Órdenes de Trabajo). El personal instalador comprueban in situ si el servicio está instalado |
| 46 | **BALANCE INTERFACE** | JAZZTEL | 3.6 / Fraude | `FAC-P1-03` | `HPFMS_SUPP` | FRAUDE | Sistema de consultas e informes predefinidos a la información de CDRs de clientes. |
| 47 | **COCO** | ORANGE | 3.6 / Fraude | `FAC-P1-03` | `HPFMS_SUPP` | PROVISION, FRAUDE | Sistema de información cuya finalidad es analizar el consumo de los clientes para detectar y actuar antes consumo anómal |
| 48 | **HPFMS** | ORANGE | 3.6 / Fraude | `FAC-P1-03` | `HPFMS_SUPP` | FRAUDE | HP Fraud Management System es una plataforma de gestión de Fraude que ofrece soporte a la detección, análisis y decisión |
| 49 | **SCORING** | ORANGE | 3.6 / Fraude | `FAC-P1-03` | `HPFMS_SUPP` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Sistema de Gestión del Riesgo. |
| 50 | **ABACUS BRM** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | VENDER PRODUCTOS Y SERVICIOS, COBROS, FACTURACIÓN | Sistema dedicado a la generación de facturas rectificativas para el mercado de telefonía móvil postpago de FT España y O |
| 51 | **APOLO** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | PROVISION, FACTURACIÓN | Sistema para el almacen de datos legales. Este sistema aplica tanto a sitemas del móvil como del fijo (incluido yacom). |
| 52 | **BRM PORTAL M2M** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | COBROS, FACTURACIÓN | Tarificador y facturador plataforma M2M de Orange Spagne. Recibe todos los datos de los clientes, jerarquías, personaliz |
| 53 | **COBROS_KFX** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | Transversal / O&M | Sistema de gestión de remesas y control de impagados. Tiene extensiones para la gestión de impagados. Engloba todas aque |
| 54 | **CTI - NORMALIZADOR BANCARIO** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS, FACTURACIÓN, FRAUDE | Normalización de cuentas bancarias. |
| 55 | **EDITRAN** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE, COBROS, FACTURACIÓN | Sistema para intercambio de ficheros con entidades externas a Grupo AUNA a través de red X25. |
| 56 | **ESCALA** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | Transversal / O&M | Facturación, estimación y presupuestado del alquiler de líneas. |
| 57 | **INTERFAZ CRM4T-KENAN** | JAZZTEL | 3.6 Facturación | `FAC-P2-01` | `SOP_BSS_KENAN` | Transversal / O&M | GIF. Gestor de Integracion CRM4T - Facturacion |
| 58 | **INTRANSIT** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | COBROS, FACTURACIÓN, FRAUDE | Sistema central de tarificación de tráfico Roaming de la FTES. Se encarga de la tarificación del tráfico Roaming IN y OU |
| 59 | **KENAN_FX** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSS_KENAN` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FACTURACIÓN, FRAUDE | Sistema de facturación y tarificación de servicios y clientes de tecnología fija y datos |
| 60 | **KENAN_FX JZZ** | JAZZTEL | 3.6 Facturación | `FAC-P2-01` | `SOP_BSS_KENAN` | PROVISION | Sistema de facturación KENAN |
| 61 | **MDG GG** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS | Sistema con toda la información de cliente (Fijo y Móvil) disponible online para consulta por cualquier sistema ( en par |
| 62 | **MEDIACION** | JAZZTEL | 3.6 Facturación | `FAC-P2-01` | `OCS_MEDIATION` | COBROS, FACTURACIÓN | Sistema de Mediación de Jazztel se encarga de recoger el tráfico generado por los distintos elementos de red o fuentes e |
| 63 | **NETPLUS** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | COBROS, FRAUDE | Credit Card Gateway. Netplus es el sistema a través del cual se realizan operaciones de venta y devolución de transaccio |
| 64 | **PSP** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Payment Service Provider. Pasarela de pagos de tarjeta de crédito externa que permite realizar cobros de tarjeta de créd |
| 65 | **VOSS-OMV** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | Transversal / O&M | VOSS, Sistema de Conciliación de OMVs de Orange España, es el sistema que realiza la tarificación y conciliación wholesa |
| 66 | **XPRESSION** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | COBROS, FACTURACIÓN | Sistema CCM (Customer Communications Management) encargado de la composición de documentos, principalmente facturas. |
| 67 | **DATAPOWER** | ORANGE | 3.7 Middleware | `MID-P2-01` | `SOP_DATAPOWER_OPS` | PROVISION, VENDER PRODUCTOS Y SERVICIOS | Sistema intermediario para las comunicaciones de la OBA entre FT y NEON vía Web Services. Gestiona todo el tráfico de re |
| 68 | **DISPATCHER** | ORANGE | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | Transversal / O&M | Se utiliza como punto único de integración con WM de forma que se puedan crear nuevos flujos más potentes (en DISPATCHER |
| 69 | **MIDDLEWARE MQ CRM4T** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN, FRAUDE | Canal de mensajería universal en plataformas distribuidas que se conecta de forma virtual a cualquier sistema IT comerci |
| 70 | **MIDDLEWARE REVENTA ISP** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE | Provision FTTH de Orange y Vodafone |
| 71 | **MIDDLEWARE SISTEMAS BSS** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE, PROVISION | OSB Sistemas. Servicio Middleware que proporcionará capacidades avanzadas de gestión de las comunicaciones e integracion |
| 72 | **MIDDLEWARE SISTEMAS CC** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE | OSB CC. Middleware Sistemas CallCenters |
| 73 | **TIBCO-M2M** | ORANGE | 3.7 Middleware | `MID-P2-01` | `SOP_TIBCO_ESB` | Transversal / O&M | Sistema TIBCO para la plataforma M2M Plataforma específica de MDW para realizar las comunicaciones on-line de los sistem |
| 74 | **WEBMETHODS** | ORANGE | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | Transversal / O&M | EAI (middleware). Se trata del Middleware de wanadoo. Los procesos más importante de los que WM es responsable: Suspensi |
| 75 | **COSTES TERMINACION** | JAZZTEL | 3.8 Redes / Sedes | `RED-P1-01` | `SOP_NET_WAN_SEDES` | Transversal / O&M | Plataforma de gestion de routing para reventa de trafico internacional. LCR. |
| 76 | **DNS** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_SYS_POWER9` | Transversal / O&M |  |
| 77 | **GRANJA VPAW** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_VMWARE_ESX` | Transversal / O&M | Granja VDI (Virtual Desktop Infraestruture) de Microsoft utilizada para alojar los PCs virtuales con privilegios especia |
| 78 | **CORREO CORPORATIVO** | ORANGE | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Permite enviar y recibir mensajes de correo electrónico. También proporciona la gestión del calendario, compartida o ind |
| 79 | **EPSILON** | ORANGE | O&M / Plataforma IT | `O&M-P1-01` | `SOP_ITIL_EPSILON` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Plataforma de Explotación de Servicios ITIL ORANGE: Gestión de Incidencias/Peticiones, Gestión de cambios, Gestión de pr |
| 80 | **MERLIN** | ORANGE | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / O&M | Jira es una herramienta en línea para la administración de tareas de un proyecto, el seguimiento de errores e incidencia |
| 81 | **WIKI ORANGE** | ORANGE | O&M / Plataforma IT | `O&M-P2-01` | `SOP_IT_OPERACIONES` | Transversal / O&M | Confluence es software de colaboración en equipo . Escrito en Java y utilizado principalmente en entornos corporativos,  |

---

## 5. Aplicaciones Especializadas Clave (Tier 2 / Non-CORE con Pilares de Negocio)

Aplicaciones de soporte departamental con impacto en Fraude, Cobros, Identidad o Canales que activan umbrales específicos de las Secciones 3.1 a 3.10.

| # | Aplicativo | Operadora | Dominio Canónico | Código | Cola BMC Remedy | Pilares Corporativos | Función Operativa Oficial |
| :-: | :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| 1 | **DESCUBRE ORANGE** | ORANGE | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE, PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Gestor de Conocimiento Unificado. Consta de portales para ventas (comerciales y distribuidores) y para los agentes de ca |
| 2 | **FICHA CLIENTE MM** | ORANGE | 3.1 ATC | `ATC-P2-01` | `DES_SOE_FICHA` | ATENCIÓN AL CLIENTE | Aplicación de call center cuyo ámbito es la gestión Multimarca en Orange Spain (Orange, Amena, Jazztel) |
| 3 | **GRABADOR DE VOZ CC** | JAZZTEL | 3.1 ATC | `ATC-P2-01` | `SOP_TECNICO_CALL_CENTER` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS | Servicio de Grabación,evaluación y transcripción de llamadas. Verint |
| 4 | **HOW** | ORANGE | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS | HOW es la Herramienta Orange Web para la recopilación y explotación de datos relativos a la calidad de atención al clien |
| 5 | **NEA** | ORANGE | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE | El objetivo del sistema es el de habilitar una interfaz de usuario que permita gestionar órdenes masivas de clientes BAU |
| 6 | **POLAR** | ORANGE | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | VENDER PRODUCTOS Y SERVICIOS | Aplicativo dentro del ambito del Field Service Management para la cita e instalación de servicios a cliente final. |
| 7 | **QLIKSENSE** | ORANGE | 3.1 ATC | `ATC-P1-01` | `SOP_IT_OPERACIONES` | FRAUDE | Qlik Sense es una plataforma para el análisis de datos donde puede analizar datos y realizar descubrimientos de datos po |
| 8 | **SAS ABM** | ORANGE | 3.1 ATC | `ATC-P1-01` | `SOP_IT_OPERACIONES` | FRAUDE | SAS ABM (COSTES) OSP: Activity Based Management. Sistema que permite el conocimiento de costes e ingresos (Rentabilidad) |
| 9 | **WOC** | ORANGE | 3.1 ATC | `ATC-P2-01` | `SOP_CANALES_DIGITALES` | ATENCIÓN AL CLIENTE, COBROS | Cliente ligero de OpenCobros |
| 10 | **ADSELFSERVICE** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `SOP_GDU_IDENTITY` | FACTURACIÓN | Interfaz de auto servicio para que los usuarios de la compañía puedan resetear sus propias contraseñas del dominio vía w |
| 11 | **APODERATOR** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `SOP_GDU_IDENTITY` | FACTURACIÓN | Plataforma para centralizar el control y el uso de los certificados de apoderado de OSP. |
| 12 | **ARGOS** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `ROBOTFACTORY_AUTOMATION` | FACTURACIÓN | Framework de Testing Automático integrado con Torre de Control |
| 13 | **ASISTENTE** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `SOP_GDU_IDENTITY` | FACTURACIÓN | Infraestructura de asistentes virtuales para distintos canales de entrada: WhatsApp, Web, aplicaciones móviles multimarc |
| 14 | **AUTOR GGCC** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `ROBOTFACTORY_AUTOMATION` | FACTURACIÓN | Grupo de aplicaciones y robots para automatizar informes y procesos de Operaciones GGCC |
| 15 | **GDU** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `SOP_GDU_IDENTITY` | ATENCIÓN AL CLIENTE, PROVISION, FRAUDE | El sistema de Gestión de Usuarios, GDU, se diseñara para mejorar la gestión, control, trazabilidad y seguridad de las cu |
| 16 | **RPA NICE** | ORANGE | 3.10 Identidad | `IDE-P2-01` | `ROBOTFACTORY_AUTOMATION` | ATENCIÓN AL CLIENTE | Software RPA (Robotic Process Automation) que tiene por finalidad capturar e interpretar aplicaciones existentes para pr |
| 17 | **AGENDA UNICA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN | Herramienta para permitir realizar citas en Punto de Venta en varios canales con expertos para proporcionar soporte en l |
| 18 | **ALEGACIONES** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN, FRAUDE | Nueva web que permita gestionar el proceso de alegaciones de penalizaciones de fraude al canal de distribución y agiliza |
| 19 | **APOYOS TERRITORIALES** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS, FACTURACIÓN, FRAUDE | La herramienta “SIAPT” permite gestionar las incidencias del servicio prestado a los clientes. Se recogen, se tramitan o |
| 20 | **AVENEW** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | FRAUDE | La  solución del Punto de Venta de las tiendas propias y franquiciadas,recargas  y la tramitación de medios de pago medi |
| 21 | **DATARYS** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Portal web del área de Big data que contiene dashboards que usarán el resto de áreas de Orange Spain para el seguimiento |
| 22 | **ELENA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Herramienta para el mercado de Grandes Cuentas para las funciones de: - Entrada de Órdenes de Cliente GGCC. - BPM/Orques |
| 23 | **EUNOMIA** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Inventario de Base Instalada de Grandes Cuentas centrado en: - Información de clientes y servicios GGCC necesarios para  |
| 24 | **GEICO** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Sistema de gestión electrónica de informes de comisiones. |
| 25 | **MICROSTRATEGY** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Herramienta de Reporte de Informes BI |
| 26 | **PORTALES** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Site donde estará alojada la nueva Home y los nuevos portales, que usarán la tecnología OWCS (Oracle WebCenter Sites). |
| 27 | **SDS-RS** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Administración de la aplicación SDS |
| 28 | **SFTP** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | VENDER PRODUCTOS Y SERVICIOS | Sistema donde se configuran los servicio SFTP para las diferentes aplicaciones de proveedores externos |
| 29 | **VPM** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | FRAUDE | Portal de venta al por mayor, exclusivo para clientes wholesales, para la gestión de sus productos de telefonía (voz, da |
| 30 | **WEB DE COMPROBANTES** | ORANGE | 3.2 Ventas | `VNT-P2-01` | `SOP_COMERCIAL_N2` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Herramienta para el registro y tramitacion de los comprobantes de venta asociados |
| 31 | **CACHE DISTRIBUIDA DE CLIENTE** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION, VENDER PRODUCTOS Y SERVICIOS | Monetizar datos de clientes de Telco, tras consentimiento del cliente, para el cálculo de un Credit Scoring de individuo |
| 32 | **DISCRIMINADOR** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION | Esta aplicación permitirá al agente conocer la herramienta de contratación que tiene que utilizar . |
| 33 | **HELIO** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | ATENCIÓN AL CLIENTE, PROVISION | Sistema que maneja todas las peticiones que Orange envia a NEON (herramienta de Telefonica para manejar a los operadores |
| 34 | **ICFM** | ORANGE | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION | Herramienta para realizar operativas en la gestión de activaciones; liberación de SIM/MSISDN |
| 35 | **PHYSIS** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `SOP_TEC_PROVISION` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Inventario de Red para Jazztel |
| 36 | **WEB LOGISTICA Y PROCESOS** | JAZZTEL | 3.5 Provisión | `PRV-P2-01` | `GIS_FIBRA_N2` | PROVISION | Portal para el control de stock de las instalaciones de las contratas y los envíos que realiza el operador logístico a l |
| 37 | **BLACK-LIST** | ORANGE | 3.6 / Fraude | `FAC-P2-01` | `HPFMS_SUPP` | VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Blacklist de Scoring. Repositorio de lista negra de tarjetas, teléfonos. Consultado por operaciones de recarga, recobro, |
| 38 | **HUNTER** | ORANGE | 3.6 / Fraude | `FAC-P2-01` | `HPFMS_SUPP` | VENDER PRODUCTOS Y SERVICIOS, FRAUDE | Herramienta antifraude. El sistema actual de Scoring se conectará a Hunter, para detectar de modo on-line en el momento  |
| 39 | **RAID** | ORANGE | 3.6 / Fraude | `FAC-P2-01` | `HPFMS_SUPP` | FRAUDE | Herramienta de Revenue Assurance. Controla la cadena de ingresos para prevenir pérdidas. Se ha unificado la parte movil  |
| 40 | **SGRT** | ORANGE | 3.6 / Fraude | `FAC-P2-01` | `HPFMS_SUPP` | ATENCIÓN AL CLIENTE | Gestión y bloqueo de terminales robados. |
| 41 | **ACCON** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | ATENCIÓN AL CLIENTE, COBROS, FACTURACIÓN | Aplicación para la gestión operativa del departamento de cobros y recobros de OSP Movil. La parte de fijo está en ARES. |
| 42 | **ACTUATE REPORT** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | FACTURACIÓN | Sistema de informe Atención al Cliente |
| 43 | **ADDA** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | FACTURACIÓN | Universos de Business Objects que recogen información relativa a los clientes, provisión de los servicios que contratan, |
| 44 | **ADMINISTRACION - MOVIL** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | FACTURACIÓN | Servidores de administración |
| 45 | **ADMINISTRACION - SEGURIDAD** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | FACTURACIÓN | Servidores de administración - Seguridad |
| 46 | **ALMACEN LOGS** | JAZZTEL | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE, FACTURACIÓN | Almacen Logs |
| 47 | **ALMACENAMIENTO CONTRATOS CLIENTE** | JAZZTEL | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | FACTURACIÓN | Servicio Tipo SaaS (Normadat) para el almacenaje de los contratos de los clientes. |
| 48 | **ANTISPAM** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | FACTURACIÓN | Pasarela Antispam InterScan Message Security Suite 7.1 |
| 49 | **ANTIVIRUS** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | FACTURACIÓN | Sistema de detección de virus en entornos cliente, correo electrónico y navegación por internet |
| 50 | **APL JAZZTEL** | JAZZTEL | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | FACTURACIÓN | No es una aplicación como tal. Se ha creado para relacionar los servidores que no se sabe qué aplicación tiene. |
| 51 | **ARES** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | ATENCIÓN AL CLIENTE, COBROS, FACTURACIÓN | Nuevo sistema de gestión del recobro. |
| 52 | **ASP INTERCO** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_BSCS_BILLING` | FACTURACIÓN | Servicio tipo SaaS.. Sistema de Tarificación del tráfico de interconexión entre operadores. También se puede utilizar pa |
| 53 | **BUSINESS OBJECTS** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Principal herramienta de realización de informes en FT España |
| 54 | **OPENCOBROS** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Sistema responsable de la gestión del cobro y recobro de los recibos facturados a clientes finales de Orange (AMENA) y p |
| 55 | **TPVs** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | COBROS | Recobro de pagos por tarjeta. |
| 56 | **VIVEORANGE** | ORANGE | 3.6 Facturación | `FAC-P2-01` | `SOP_OPEN_COBROS` | PROVISION, VENDER PRODUCTOS Y SERVICIOS, COBROS, FRAUDE | Portal del empleado y gestor de contenidos del Área de Recursos, dirigido a todos los empleados de OSP. |
| 57 | **MIDDLEWARE PLATAFORMA DE ACCESO** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE | Middleware Sistemas Plataforma de Acceso de Sistemas de Altitude. |
| 58 | **MIDDLEWARE SISTEMAS OSS** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE | OSB ingenieria. Middleware Sistemas OSS |
| 59 | **WS INTERMEDIOS DE REMEDY** | JAZZTEL | 3.7 Middleware | `MID-P2-01` | `GC_MIDDLEWARE_OPS` | ATENCIÓN AL CLIENTE, VENDER PRODUCTOS Y SERVICIOS | Aplicación desde la cual se puede consultar/crear incidencias Remedy, gestionar ordenes de trabajo y gestionar incidenci |
| 60 | **ADMINISTRACION - DBA** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_DB_ORACLE_EXADATA` | FACTURACIÓN | Servidores de administración del grupo de BBDD. Se recogen servicios como el Catálogo de RMAN, el Oracle Enterprise Mana |
| 61 | **ADMINISTRACION - LINUX Y VMWARE** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_VMWARE_ESX` | FACTURACIÓN | Servidores de administración del grupo de Linux y Vmware |
| 62 | **APACHE** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_SYS_POWER9` | FACTURACIÓN | Servidores Apache |
| 63 | **APLICACIONES GROUPWARE** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_SYS_POWER9` | FACTURACIÓN | Aplicaciones y bases de datos en Notes-Domino |
| 64 | **CITRIX - CONTROL** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_SYS_POWER9` | COBROS | Servidores para control de todas las granjas Citrix (Data Store, Data Collector, XML y Licencias) |
| 65 | **CITRIX - OFFSHORE** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_SYS_POWER9` | FRAUDE | Granja de servidores Citrix que da servicio a Off Shore |
| 66 | **SERVIDORES DE FICHEROS** | ORANGE | 3.9 Infraestructura | `INF-P2-01` | `SOP_SAN_STORAGE` | VENDER PRODUCTOS Y SERVICIOS | La NAS de Orange. |

---

## 6. Glosario Canónico de Acrónimos y Términos Operacionales de Orange / Jazztel

Para erradicar cualquier ambigüedad en el triaje de tickets y notas de trabajo, la IA debe aplicar las siguientes equivalencias operativas oficiales:

1. **POMV (Provisión Móvil):** Sistema central de provisión de líneas de telefonía móvil de Jazztel y Orange. Gestiona altas, cambios de SIM y activación de bonos.
2. **SPM / TRAMITADOR (Provisión Masivo):** Sistema de tramitación y provisión masiva de clientes residenciales y SOHO en Jazztel.
3. **AFS FIJO / AURORA:** Motor TIBCO AFS (Automated Fulfillment System) para la orquestación y provisión de servicios FTTH (fibra óptica, datos y TV de Orange).
4. **OWCS (Oracle WebCenter Sites):** Plataforma CMS corporativa de gestión de contenidos y publicación de portales comerciales y canales web unificados (`PANGEA`, `PUBLICACION`, `PORTALES`).
5. **vPAW (Virtual Privileged Access Workstation):** Granja VDI de Microsoft con PCs virtuales reforzados de salto obligatorio para tareas de administración remota en servidores Windows de producción.
6. **SOE (Service Oriented Enterprise):** Arquitectura estándar de exposición de servicios comerciales y frontales unificados sobre la que corren `FICHA DE CLIENTE`, `ATENAS` y la capa de integración de agentes.
7. **EAI / WM (Enterprise Application Integration / webMethods):** Bus de middleware histórico Wanadoo/Orange responsable de suspensiones, reactivaciones y bajas masivas de jerarquías de clientes.
8. **SGP (Sistema de Gestión de Portabilidades):** Motor oficial de tramitación de portabilidades móviles y comunicación con la Entidad de Referencia de otros operadores.
9. **BRM (Billing and Revenue Management):** Plataforma Oracle BRM dedicada a facturación rectificativa móvil (`ABACUS BRM`) y facturación de plataformas M2M (`BRM PORTAL M2M`).
10. **KFX / KENAN_FX:** Motor de facturación, tarificación y mediación para clientes y servicios de tecnología fija, datos y empresas en Orange y Jazztel.
11. **CC CTI (Contact Center Computer Telephony Integration):** Pasarela de integración entre telefonía y software de agente para el enrutamiento inteligente de llamadas en centros de atención propios y proveedores externos.
12. **PCNEON OBA:** Plataforma de Comunicaciones con NEON (Telefónica) para la gestión automatizada de bucle de abonado (OBA) y AMLT.
13. **OAM (Oracle Access Manager):** Infraestructura de Single Sign-On (SSO) corporativo para el control de acceso y autenticación federada en portales internos.
14. **MDG (Master Data Governance):** Plataforma de caché unificada que ofrece la visión global 360 del cliente (`MDG COH` / `MDG GG`) para consulta inmediata de frontales sin penalizar los BSS transaccionales.
15. **EPSILON:** Plataforma corporativa de gestión ITSM de Orange sobre arquitectura ITIL (Gestión de Incidencias, Cambios, Problemas, CMDB y Acuerdos de Nivel de Servicio).

---

## 7. Directrices de Triaje y Tratamiento de Discrepancias en BMC Remedy

1. **Prevalencia del Impacto sobre el Aplicativo:** Si un ticket describe una caída en un sistema `CORE++` (ej. `BSCS`, `BOREAL`, `AURORA` o `OPENAPI`) pero la cola asignada es genérica (ej. `SERVICE_DESK_N1` o `SOPORTE_GENERICO`), el sistema de triaje **debe ignorar la cola y clasificar la incidencia como SL1 / P1 de forma inmediata**.
2. **Elevación Automática por Cola Técnica Especializada:** La recepción de una incidencia con términos de corte de servicio en colas especializadas (`SOP_BSCS_BILLING`, `SOP_TMC_APIGEE`, `SOP_TIBCO_ESB`, `POMV`, `OCS_MEDIATION`, `SOP_GDU_IDENTITY`) confirma la criticidad objetiva y descarta cualquier rebaja a P3/P4.
3. **Escalado en Paralelo en Sistemas Transversales:** Toda incidencia en componentes de integración `CORE++` (`OPENAPI`, `TIBCO`, `MICROSERVICIOS`) requiere la convocatoria simultánea de los grupos de infraestructura y de los aplicativos de negocio consumidores.

#!/usr/bin/env python3
"""
Servidor HTTP personalizado para Release Dashboard Application
Resuelve problemas de sincronización de archivos en Windows
"""

import os
import re
import json
import sys
import time
import http.server
import socketserver
import urllib.parse
from pathlib import Path
from email.parser import BytesParser
from email import policy

# Raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.absolute()

sys.path.insert(0, str(PROJECT_ROOT / 'converters' / 'cli'))
from upload_csv import run_upload  # noqa: E402
from generate_postmortem_report import generate_report, generate_all_reports  # noqa: E402

# Single Source of Truth (Fase 1.1): Motor de informes ejecutivos en cso-incident-masivas-report/backend
CSO_BACKEND_ROOT = Path(os.environ.get(
    "CSO_BACKEND_ROOT",
    str(PROJECT_ROOT.parent / "cso-incident-masivas-report" / "backend")
))
import importlib.util

cso_init_py = CSO_BACKEND_ROOT / "report_generator" / "__init__.py"
try:
    cso_is_file = cso_init_py.is_file()
except OSError:
    cso_is_file = False

if cso_is_file:
    try:
        spec = importlib.util.spec_from_file_location(
            "cso_report_generator",
            str(cso_init_py),
            submodule_search_locations=[str(CSO_BACKEND_ROOT / "report_generator")]
        )
        cso_mod = importlib.util.module_from_spec(spec)
        sys.modules["cso_report_generator"] = cso_mod
        spec.loader.exec_module(cso_mod)

        ExecutiveIncidentData = getattr(cso_mod, "ExecutiveIncidentData", None)
        sanitize_incident_ref = getattr(cso_mod, "sanitize_incident_ref", None)
        extract_fields_from_jira_description = getattr(cso_mod, "extract_fields_from_jira_description", None)
        get_executive_report_path = getattr(cso_mod, "get_executive_report_path", None)
        get_executive_report_filename = getattr(cso_mod, "get_executive_report_filename", None)
        cleanup_old_executive_reports = getattr(cso_mod, "cleanup_old_executive_reports", None)
        ExecutiveReportBuilder = getattr(cso_mod, "ExecutiveReportBuilder", None)
        ConfluenceParser = getattr(cso_mod, "ConfluenceParser", None)
    except (OSError, Exception):
        cso_is_file = False

if not cso_is_file:
    try:
        sys.path.insert(0, str(PROJECT_ROOT / 'converters' / 'src'))
        from report_generator.executive_models import (
            ExecutiveIncidentData,
            sanitize_incident_ref,
            extract_fields_from_jira_description,
        )
        from report_generator.executive_paths import (
            get_executive_report_path,
            get_executive_report_filename,
            cleanup_old_executive_reports,
        )
        from report_generator.executive_report_builder import ExecutiveReportBuilder
        from report_generator.confluence_parser import ConfluenceParser
    except (ImportError, Exception):
        ExecutiveIncidentData = None
        sanitize_incident_ref = None
        extract_fields_from_jira_description = None
        get_executive_report_path = None
        get_executive_report_filename = None
        cleanup_old_executive_reports = None
        ExecutiveReportBuilder = None
        ConfluenceParser = None

# Epsilon Resumen IA Service
try:
    sys.path.insert(0, str(PROJECT_ROOT / 'converters' / 'src'))
    from epsilon_service import generate_epsilon_summary, find_incident_in_local_dumps
except (ImportError, Exception):
    generate_epsilon_summary = None
    find_incident_in_local_dumps = None

# MonTMC / Remedy Services & Cache
try:
    from converters.src.montmc_client import MonTMCClient, RemedyNotFoundError, MonTMCError
    from converters.cli.sync_montmc_incidents import sync_remedy_incidents
except (ImportError, Exception):
    try:
        sys.path.insert(0, str(PROJECT_ROOT / 'converters' / 'src'))
        sys.path.insert(0, str(PROJECT_ROOT / 'converters' / 'cli'))
        from montmc_client import MonTMCClient, RemedyNotFoundError, MonTMCError
        from sync_montmc_incidents import sync_remedy_incidents
    except (ImportError, Exception):
        MonTMCClient = None
        RemedyNotFoundError = None
        MonTMCError = None
        sync_remedy_incidents = None

REMEDY_DETAIL_CACHE = {}  # { idRemedy: (timestamp, data_dict, status) }

REPORTS_PATH_PREFIX = '/api/reports/postmortem/'
EXECUTIVE_REPORT_PREFIX = '/api/reports/executive-incident'
EXECUTIVE_REPORT_V1_PREFIX = '/api/v1/reports/executive-incident'
FASTAPI_BACKEND_URL = os.environ.get("FASTAPI_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
EPSILON_CACHE = {}  # { codigo: (timestamp, content, status) }


def get_storage_dir() -> Path:
    env_dir = os.environ.get("RELEASE_DASHBOARD_STORAGE_DIR", "").strip()
    if env_dir:
        return Path(env_dir)
    prod_storage = Path("/infocodes/var/storage/release-dashboard")
    if os.name != "nt" and prod_storage.is_dir():
        return prod_storage
    return PROJECT_ROOT / "data"


STORAGE_DIR = get_storage_dir()

# Puerto por defecto: 8080 para no colisionar con FastAPI (puerto 8000).
# Configurable vía variable de entorno PORT/SERVE_APP_PORT o argumento --port
DEFAULT_PORT = int(os.environ.get("SERVE_APP_PORT", os.environ.get("PORT", 8080)))
PORT = DEFAULT_PORT



class CustomHTTPHandler(http.server.SimpleHTTPRequestHandler):
    # Asegurar que sirve desde el PROJECT_ROOT
    directory = str(PROJECT_ROOT)

    def handle(self):
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def _send_raw_response(self, status, content, content_type='application/json; charset=utf-8', extra_headers=None):
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.send_header('Content-Length', str(len(content)))
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(content)
            return True
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            return False
        except Exception as e:
            print(f"  Error enviando respuesta HTTP: {e}")
            return False

    def _send_json(self, status, payload, extra_headers=None):
        try:
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(body)))
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
            return True
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            return False
        except Exception as e:
            print(f"  Error enviando respuesta JSON: {e}")
            return False

    def proxy_to_nextjs(self):
        candidate_ports = [3001, 3000]
        excluded = {'host', 'connection', 'keep-alive', 'accept-encoding', 'content-length'}
        headers = {k: v for k, v in self.headers.items() if k.lower() not in excluded}
        headers['Connection'] = 'close'

        body_data = None
        if self.command in ('POST', 'PUT', 'PATCH'):
            try:
                content_length = int(self.headers.get('Content-Length', 0))
            except ValueError:
                content_length = 0
            body_data = self.rfile.read(content_length) if content_length > 0 else None

        last_error = None
        for port in candidate_ports:
            target_url = f"http://localhost:{port}{self.path}"
            req = urllib.request.Request(
                target_url,
                method=self.command,
                headers=headers,
                data=body_data,
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    self.send_response(resp.status)
                    for header, val in resp.getheaders():
                        if header.lower() not in ('transfer-encoding', 'content-length', 'connection'):
                            self.send_header(header, val)
                    self.send_header('Connection', 'close')
                    content = resp.read()
                    self.send_header('Content-Length', str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    return
            except urllib.error.HTTPError as e:
                self.send_response(e.code)
                for header, val in e.headers.items():
                    if header.lower() not in ('transfer-encoding', 'content-length', 'connection'):
                        self.send_header(header, val)
                self.send_header('Connection', 'close')
                body = e.read()
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                return
            except Exception as e:
                last_error = e
                continue

        print(f"  Error proxy Next.js (ningún puerto disponible {candidate_ports}): {last_error}")
        msg = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'><title>502 Bad Gateway - Gestión de Problemas</title>"
            "<style>body{font-family:sans-serif;max-width:600px;margin:50px auto;line-height:1.6;color:#222;}"
            "code,pre{background:#f4f4f4;padding:3px 6px;border-radius:4px;}pre{padding:12px;}</style></head><body>"
            "<h2>502 - Servicio Gestión de Problemas no disponible</h2>"
            "<p>No se pudo conectar con el servidor Next.js en <code>http://localhost:3001</code> ni en <code>http://localhost:3000</code>.</p>"
            "<p>Para arrancarlo en local, simplemente ejecuta en la carpeta del proyecto:</p>"
            "<pre>cd ../gestion-problemas-dashboard\nnpm run dev</pre>"
            "<p><i>(Este comando arranca automáticamente en el puerto 3001 con la ruta base /problemas)</i></p>"
            "</body></html>"
        ).encode('utf-8')
        self._send_raw_response(
            502,
            msg,
            content_type='text/html; charset=utf-8',
            extra_headers={'Connection': 'close'}
        )

    def proxy_to_epsilon_ia(self, codigo):
        import ssl
        import time
        from datetime import datetime

        parsed_url = urllib.parse.urlparse(self.path)
        q_params = urllib.parse.parse_qs(parsed_url.query)
        force = 'force' in q_params or 'refresh' in q_params or (q_params.get('force', [''])[0].lower() in ('1', 'true', 'yes'))
        is_mock = 'mock' in q_params or (q_params.get('mock', [''])[0].lower() in ('1', 'true', 'yes'))
        no_cache = force or ('no-cache' in self.headers.get('Cache-Control', ''))
        now = time.time()

        if not no_cache and codigo in EPSILON_CACHE:
            cached_time, cached_content, cached_status = EPSILON_CACHE[codigo]
            if now - cached_time < 900:  # 15 minutos de caché
                print(f"  Proxy Epsilon IA (cache HIT): {codigo}")
                try:
                    self.send_response(cached_status)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('X-Cache-Status', 'HIT')
                    self.send_header('Content-Length', str(len(cached_content)))
                    self.end_headers()
                    self.wfile.write(cached_content)
                except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                    pass
                return

        # 1. Consulta corporativa en vivo (SOPTMC) salvo si se pide mock directo
        if not is_mock:
            target_url = f"https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA/{codigo}"
            print(f"  Proxy Epsilon IA (cache MISS/LIVE): {target_url}")
            soptmc_content = None
            soptmc_status = None
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                req = urllib.request.Request(
                    target_url,
                    headers={'User-Agent': 'ReleaseDashboard/1.0', 'Accept': 'application/json'}
                )
                with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                    soptmc_content = resp.read()
                    soptmc_status = resp.status
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                return
            except Exception as e:
                print(f"  Error proxy Epsilon IA (SOPTMC): {e}")

            if soptmc_content is not None and soptmc_status == 200:
                EPSILON_CACHE[codigo] = (now, soptmc_content, soptmc_status)
                try:
                    disk_cache_file = PROJECT_ROOT / "data" / ".epsilon_cache" / f"{codigo}.json"
                    disk_cache_file.parent.mkdir(parents=True, exist_ok=True)
                    disk_cache_file.write_bytes(soptmc_content)
                except Exception:
                    pass
                try:
                    self.send_response(soptmc_status)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', '*')
                    self.send_header('X-Cache-Status', 'MISS')
                    self.send_header('Content-Length', str(len(soptmc_content)))
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(soptmc_content)
                except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                    pass
                return

        # 2. Resiliencia offline: Snapshot en disco si no se fuerza refresh
        disk_cache_file = PROJECT_ROOT / "data" / ".epsilon_cache" / f"{codigo}.json"
        if not no_cache and disk_cache_file.exists():
            disk_content = None
            try:
                with open(disk_cache_file, "rb") as f:
                    disk_content = f.read()
            except Exception as read_err:
                print(f"  Error leyendo disk cache para Epsilon IA: {read_err}")

            if disk_content:
                print(f"  Fallback exitoso a caché en disco para Epsilon IA: {codigo}")
                EPSILON_CACHE[codigo] = (now, disk_content, 200)
                try:
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                    self.send_header('Access-Control-Allow-Headers', '*')
                    self.send_header('X-Cache-Status', 'DISK_FALLBACK')
                    self.send_header('Content-Length', str(len(disk_content)))
                    self.end_headers()
                    self.wfile.write(disk_content)
                except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                    pass
                return

        # 3. Fallback inteligente: Buscar datos técnicos en volcados locales y auto-generar con LLM / Mock
        if find_incident_in_local_dumps and generate_epsilon_summary:
            found = find_incident_in_local_dumps(codigo, PROJECT_ROOT)
            if found:
                incident_item, source_filename, file_mtime = found
                print(f"  Generando resumen Epsilon IA desde volcado local '{source_filename}' para {codigo}...")
                out_bytes = None
                try:
                    is_valid, summary_data, meta = generate_epsilon_summary(
                        incident_data=incident_item,
                        mock=is_mock,
                    )
                    if is_valid:
                        is_stale = (now - file_mtime) > 7200  # Volcado de más de 2 horas
                        summary_data["meta"] = {
                            "source": "local_dump_fallback",
                            "dump_file": source_filename,
                            "dump_timestamp": datetime.fromtimestamp(file_mtime).isoformat(),
                            "is_stale_warning": is_stale,
                            "llm_meta": meta,
                        }
                        out_bytes = json.dumps(summary_data, ensure_ascii=False, indent=2).encode('utf-8')
                        try:
                            disk_cache_file.parent.mkdir(parents=True, exist_ok=True)
                            disk_cache_file.write_bytes(out_bytes)
                        except Exception as write_err:
                            print(f"  Aviso: no se pudo escribir en disk cache: {write_err}")

                        EPSILON_CACHE[codigo] = (now, out_bytes, 200)
                    else:
                        print(f"  Fallo de validación Pydantic para {codigo}: {summary_data.get('error')}")
                except Exception as gen_err:
                    print(f"  Error generando resumen LLM local para {codigo}: {gen_err}")

                if out_bytes:
                    try:
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json; charset=utf-8')
                        self.send_header('Access-Control-Allow-Origin', '*')
                        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                        self.send_header('Access-Control-Allow-Headers', '*')
                        self.send_header('X-Cache-Status', 'LOCAL_LLM_GENERATED')
                        self.send_header('Content-Length', str(len(out_bytes)))
                        self.end_headers()
                        self.wfile.write(out_bytes)
                    except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                        pass
                    return

        # Incidencia no encontrada ni en SOPTMC ni en los volcados locales
        err_msg = f"Incidencia '{codigo}' no disponible en SOPTMC corporativo ni en los volcados locales"
        err_payload = json.dumps({"success": False, "error": err_msg}, ensure_ascii=False).encode('utf-8')
        try:
            self.send_response(502)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(err_payload)))
            self.end_headers()
            self.wfile.write(err_payload)
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_POST(self):
        print(f"POST {self.path}")
        if self.path.startswith('/problemas'):
            self.proxy_to_nextjs()
        elif self.path == '/api/upload':
            self.handle_upload()
        elif self.path == f'{REPORTS_PATH_PREFIX}batch':
            self.handle_reports_batch()
        elif self.path.startswith('/api/reports') and not self.path.startswith(REPORTS_PATH_PREFIX):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            if not self.proxy_to_fastapi_executive(body_data=body):
                self._send_json(502, {'success': False, 'error': f'FastAPI backend ({FASTAPI_BACKEND_URL}) no disponible'})
        elif self.path in (
            EXECUTIVE_REPORT_PREFIX,
            f'{EXECUTIVE_REPORT_PREFIX}/',
            EXECUTIVE_REPORT_V1_PREFIX,
            f'{EXECUTIVE_REPORT_V1_PREFIX}/',
        ):
            self.handle_executive_report_generate()
        elif self.path == '/api/incident-manager/save-message' or self.path.startswith('/api/incident-manager/save-message?'):
            self.handle_incident_manager_save_message()
        elif self.path in ('/api/ingestion/retry-ia', '/api/epsilon/retry') or self.path.split('?')[0].rstrip('/') in ('/api/ingestion/retry-ia', '/api/epsilon/retry'):
            self.handle_ingestion_retry_ia()
        elif self.path in ('/api/epsilon/generate', '/api/epsilon/resumen') or self.path.split('?')[0].rstrip('/') in ('/api/epsilon/generate', '/api/epsilon/resumen'):
            self.handle_epsilon_generate()
        elif self.path in ('/api/sync-remedy', '/api/sync-remedy/') or self.path.split('?')[0].rstrip('/') == '/api/sync-remedy':
            self.handle_sync_remedy()
        else:
            self.send_error(404, "Not Found")

    def do_PUT(self):
        print(f"PUT {self.path}")
        if self.path.startswith('/api/reports') or self.path.startswith('/api/'):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            if not self.proxy_to_fastapi_executive(body_data=body):
                self._send_json(502, {'success': False, 'error': f'FastAPI backend ({FASTAPI_BACKEND_URL}) no disponible'})
        else:
            self.send_error(404, "Not Found")

    def do_DELETE(self):
        print(f"DELETE {self.path}")
        if self.path.startswith('/api/reports') or self.path.startswith('/api/'):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else None
            if not self.proxy_to_fastapi_executive(body_data=body):
                self._send_json(502, {'success': False, 'error': f'FastAPI backend ({FASTAPI_BACKEND_URL}) no disponible'})
        else:
            self.send_error(404, "Not Found")

    def handle_reports_batch(self):
        result = generate_all_reports()
        self._send_json(200, result)

    def handle_upload(self):
        content_type = self.headers.get('Content-Type', '')
        if not content_type.startswith('multipart/form-data'):
            self._send_json(400, {'success': False, 'error': 'Content-Type debe ser multipart/form-data'})
            return

        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except ValueError:
            content_length = 0

        if content_length <= 0:
            self._send_json(400, {'success': False, 'error': 'Petición vacía'})
            return

        body = self.rfile.read(content_length)
        header_bytes = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode('utf-8')
        message = BytesParser(policy=policy.default).parsebytes(header_bytes + body)

        file_bytes = None
        filename = None
        dashboard_type = 'massive'
        release_name = None

        if message.is_multipart():
            for part in message.iter_parts():
                field_name = part.get_param('name', header='Content-Disposition')
                if field_name == 'file':
                    filename = part.get_filename()
                    file_bytes = part.get_payload(decode=True)
                elif field_name == 'type':
                    dashboard_type = part.get_payload(decode=True).decode('utf-8').strip()
                elif field_name == 'release_name':
                    release_name = part.get_payload(decode=True).decode('utf-8').strip()

        if not file_bytes or not filename:
            self._send_json(400, {'success': False, 'error': 'No se recibió ningún archivo CSV'})
            return

        if dashboard_type == 'postmortem' and not release_name:
            self._send_json(400, {'success': False, 'error': 'Falta el nombre de la release (release_name)'})
            return

        filename = Path(filename).name
        if not filename.lower().endswith('.csv'):
            self._send_json(400, {'success': False, 'error': 'El archivo debe tener extensión .csv'})
            return

        input_dir = STORAGE_DIR / 'input'
        input_dir.mkdir(parents=True, exist_ok=True)
        csv_path = input_dir / filename
        csv_path.write_bytes(file_bytes)
        print(f"  Guardado: {csv_path} ({len(file_bytes)} bytes)")

        t0 = time.perf_counter()
        import upload_csv
        import importlib
        importlib.reload(upload_csv)
        result = upload_csv.run_upload(csv_path, dashboard_type, PROJECT_ROOT, release_name, wait_eval=False)
        elapsed = time.perf_counter() - t0

        if not result['success']:
            print(f"  Error de conversión: {result.get('details', result.get('error'))}")
            self._send_json(500, result)
            return

        print(f"  Conversión OK: {filename} ({elapsed:.3f}s)")
        if result.get('background_tasks'):
            print(f"  [Segundo Plano] Tareas lanzadas: {result.get('background_tasks')}")
        # Invalidar caché en memoria de Epsilon para evitar que tickets modificados queden obsoletos (LIFECYCLE_STATUS_MISMATCH)
        EPSILON_CACHE.clear()
        self._send_json(200, result)

    def handle_report_download(self):
        release_name = urllib.parse.unquote(self.path[len(REPORTS_PATH_PREFIX):]).strip()
        if not release_name:
            self._send_json(400, {'error': 'Falta el nombre de la release'})
            return

        try:
            result = generate_report(release_name)
        except Exception as e:
            print(f"  Error generando informe: {e}")
            self._send_json(500, {'error': 'No se pudo generar el informe', 'details': str(e)[:4000]})
            return

        if not result['success']:
            self._send_json(404, {'error': result['error']})
            return

        pptx_path = Path(result['path'])
        body = pptx_path.read_bytes()
        self._send_raw_response(
            200,
            body,
            content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',
            extra_headers={'Content-Disposition': f'attachment; filename="{pptx_path.name}"'}
        )

    def proxy_to_fastapi_executive(self, body_data: bytes = None) -> bool:
        """
        Delega la petición de informe ejecutivo al backend propietario FastAPI
        (http://127.0.0.1:8000). Si FastAPI responde (cualquier código HTTP),
        transmite la respuesta y devuelve True. Si FastAPI no está levantado en local
        (ConnectionRefusedError / URLError), devuelve False para ejecutar el fallback
        usando el mismo módulo Single Source of Truth de cso-incident-masivas-report.
        """
        import urllib.request
        import urllib.error

        excluded = {'host', 'connection', 'keep-alive', 'accept-encoding', 'content-length'}
        headers = {k: v for k, v in self.headers.items() if k.lower() not in excluded}
        headers['Connection'] = 'close'

        target_url = f"{FASTAPI_BACKEND_URL}{self.path}"
        req = urllib.request.Request(
            target_url,
            method=self.command,
            headers=headers,
            data=body_data,
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                self.send_response(resp.status)
                for header, val in resp.getheaders():
                    if header.lower() not in ('transfer-encoding', 'content-length', 'connection'):
                        self.send_header(header, val)
                self.send_header('Connection', 'close')
                content = resp.read()
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return True
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for header, val in e.headers.items():
                if header.lower() not in ('transfer-encoding', 'content-length', 'connection'):
                    self.send_header(header, val)
            self.send_header('Connection', 'close')
            body = e.read()
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return True
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            return True
        except Exception as e:
            print(f"  [FastAPI Proxy] FastAPI ({FASTAPI_BACKEND_URL}) no alcanzable ({e}); ejecutando fallback local sobre Single Source of Truth.")
            return False

    def handle_executive_report_generate(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        except Exception as e:
            self._send_json(400, {'success': False, 'error': f'Error leyendo cuerpo HTTP: {e}'})
            return

        # 1. Intentar delegar primero a FastAPI (Single Source of Truth en ejecución)
        if self.proxy_to_fastapi_executive(body_data=body):
            return

        # 2. Fallback en proceso (cuando FastAPI no está arrancado en local)
        try:
            payload = json.loads(body.decode('utf-8'))
        except Exception as e:
            self._send_json(400, {'success': False, 'error': f'JSON inválido: {e}'})
            return

        incident_ref = payload.get('incidentRef') or payload.get('incident_ref') or payload.get('id')
        if not incident_ref:
            self._send_json(400, {'success': False, 'error': 'Falta el código de incidencia (incidentRef)'})
            return

        data_dict = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        if 'incidentRef' not in data_dict:
            data_dict['incidentRef'] = incident_ref

        # Ingesta o parseo de Confluence si se incluye contenido o URL
        raw_content = payload.get('rawContent') or data_dict.get('rawContent') or ''
        confluence_url = payload.get('confluenceUrl') or data_dict.get('sourceUrl') or ''

        if raw_content:
            try:
                parser = ConfluenceParser()
                parsed_data = parser.parse(raw_content, fallback_ref=incident_ref, source_url=confluence_url)
                base_dict = parsed_data.to_dict()
                # Preservar campos explícitos no vacíos
                for k, v in data_dict.items():
                    if v and k != 'rawContent':
                        base_dict[k] = v
                data_dict = base_dict
            except Exception as pe:
                print(f"  Aviso al parsear contenido Confluence: {pe}")
        elif confluence_url and not data_dict.get('impactText'):
            try:
                import urllib.request
                req = urllib.request.Request(confluence_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    html_content = resp.read().decode('utf-8', errors='ignore')
                    parser = ConfluenceParser()
                    parsed_data = parser.parse(html_content, fallback_ref=incident_ref, source_url=confluence_url)
                    base_dict = parsed_data.to_dict()
                    for k, v in data_dict.items():
                        if v:
                            base_dict[k] = v
                    data_dict = base_dict
            except Exception as ce:
                print(f"  Nota: No se pudo obtener Confluence automáticamente ({ce}). Se usarán datos base.")

        # Fallback a datos de Jira si no se obtuvieron o faltan secciones en data_dict
        jira_desc = data_dict.get('description') or payload.get('description') or ''
        if jira_desc and (not data_dict.get('impactText') or not data_dict.get('causeText') or not data_dict.get('solutionText')):
            extracted = extract_fields_from_jira_description(jira_desc)
            for ek, ev in extracted.items():
                if not data_dict.get(ek):
                    data_dict[ek] = ev

        force = payload.get('force', False)
        target_path = get_executive_report_path(incident_ref)

        if target_path.is_file() and not force:
            clean_ref = sanitize_incident_ref(incident_ref)
            self._send_json(200, {
                'success': True,
                'incidentRef': clean_ref,
                'incident_ref': clean_ref,
                'filename': target_path.name,
                'downloadUrl': f"{EXECUTIVE_REPORT_PREFIX}/{clean_ref}",
                'download_url': f"{EXECUTIVE_REPORT_PREFIX}/{clean_ref}",
                'sizeBytes': target_path.stat().st_size,
                'size_bytes': target_path.stat().st_size,
                'cached': True,
            })
            return

        try:
            incident_data = ExecutiveIncidentData.from_dict(data_dict)
            builder = ExecutiveReportBuilder()
            metadata = builder.generate(incident_data, target_path)

            # Higiene automática: limpiar informes con más de 14 días
            try:
                cleaned = cleanup_old_executive_reports(max_age_days=14, keep_min=5)
                if cleaned:
                    print(f"  [Cleanup] Eliminados {len(cleaned)} informes ejecutivos antiguos: {', '.join(cleaned)}")
            except Exception as clean_err:
                print(f"  [Cleanup] Aviso no bloqueante: {clean_err}")

            self._send_json(200, {
                'success': True,
                'incidentRef': metadata.incident_ref,
                'incident_ref': metadata.incident_ref,
                'filename': metadata.filename,
                'downloadUrl': f"{EXECUTIVE_REPORT_PREFIX}/{metadata.incident_ref}",
                'download_url': f"{EXECUTIVE_REPORT_PREFIX}/{metadata.incident_ref}",
                'generatedAt': metadata.generated_at,
                'generated_at': metadata.generated_at,
                'sizeBytes': metadata.size_bytes,
                'size_bytes': metadata.size_bytes,
                'slideCount': metadata.slide_count,
                'slide_count': metadata.slide_count,
            })
        except Exception as e:
            print(f"  Error generando informe ejecutivo: {e}")
            self._send_json(500, {
                'success': False,
                'error': 'Error generando informe ejecutivo PowerPoint',
                'details': str(e),
            })

    def handle_executive_report_get(self):
        # 1. Intentar delegar primero a FastAPI (Single Source of Truth en ejecución)
        if self.proxy_to_fastapi_executive():
            return

        # 2. Fallback en proceso
        active_prefix = (
            EXECUTIVE_REPORT_V1_PREFIX
            if self.path.startswith(EXECUTIVE_REPORT_V1_PREFIX)
            else EXECUTIVE_REPORT_PREFIX
        )
        path_without_prefix = self.path[len(active_prefix):].split('?')[0]
        parts = [p for p in path_without_prefix.split('/') if p]

        if not parts:
            self._send_json(400, {'success': False, 'error': 'Falta el código de incidencia'})
            return

        incident_ref = sanitize_incident_ref(parts[0])

        # Caso 1: Comprobación de estado /status
        if len(parts) >= 2 and parts[1] == 'status':
            report_path = get_executive_report_path(incident_ref)
            if report_path.is_file():
                self._send_json(200, {
                    'exists': True,
                    'incidentRef': incident_ref,
                    'incident_ref': incident_ref,
                    'filename': report_path.name,
                    'downloadUrl': f"{EXECUTIVE_REPORT_PREFIX}/{incident_ref}",
                    'download_url': f"{EXECUTIVE_REPORT_PREFIX}/{incident_ref}",
                    'sizeBytes': report_path.stat().st_size,
                    'size_bytes': report_path.stat().st_size,
                })
            else:
                self._send_json(200, {'exists': False, 'incidentRef': incident_ref, 'incident_ref': incident_ref})
            return

        # Caso 2: Descarga del archivo binario
        report_path = get_executive_report_path(incident_ref)
        if not report_path.is_file():
            self._send_json(404, {
                'success': False,
                'error': f'No existe informe generado para la incidencia {incident_ref}. Debe solicitarlo primero.',
            })
            return

        try:
            body = report_path.read_bytes()
            self._send_raw_response(
                200,
                body,
                content_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                extra_headers={'Content-Disposition': f'attachment; filename="{report_path.name}"'}
            )
        except Exception as e:
            self._send_json(500, {'success': False, 'error': f'Error al leer archivo: {str(e)}'})

    def handle_agents_catalog(self):
        catalog_path = PROJECT_ROOT / 'data' / 'output' / 'agents_catalog.json'
        if 'refresh=true' in self.path:
            try:
                from build_agents_catalog import build_and_save_catalog
                build_and_save_catalog()
            except Exception as e:
                print(f"  Error refrescando catálogo de agentes: {e}")

        if catalog_path.is_file():
            try:
                content = json.loads(catalog_path.read_text(encoding='utf-8'))
                self._send_json(200, content)
                return
            except Exception as e:
                self._send_json(500, {'error': f'Error leyendo catálogo: {e}'})
                return
        self._send_json(404, {'error': 'Catálogo de agentes no encontrado'})

    def handle_incident_manager_pending(self):
        try:
            import incident_manager_service
            import importlib
            importlib.reload(incident_manager_service)
            from incident_manager_service import get_pending_incidents_payload
            catalog_path = STORAGE_DIR / 'output' / 'high_priority_notifications.json'
            if not catalog_path.exists():
                catalog_path = PROJECT_ROOT / 'data' / 'output' / 'high_priority_notifications.json'
            store_path = STORAGE_DIR / 'agent_executive_messages.json'
            if not store_path.exists():
                store_path = PROJECT_ROOT / 'data' / 'agent_executive_messages.json'
            payload = get_pending_incidents_payload(catalog_path=catalog_path, store_path=store_path)
            self._send_json(200, payload)
        except Exception as e:
            print(f"  Error obteniendo incidencias pendientes: {e}")
            self._send_json(500, {'success': False, 'error': str(e)})

    def handle_incident_manager_emergency_cockpit(self):
        try:
            import incident_manager_service
            import importlib
            importlib.reload(incident_manager_service)
            from incident_manager_service import get_emergency_cockpit_payload
            catalog_path = STORAGE_DIR / 'output' / 'high_priority_notifications.json'
            if not catalog_path.exists():
                catalog_path = PROJECT_ROOT / 'data' / 'output' / 'high_priority_notifications.json'
            store_path = STORAGE_DIR / 'agent_executive_messages.json'
            if not store_path.exists():
                store_path = PROJECT_ROOT / 'data' / 'agent_executive_messages.json'

            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)

            only_pending_val = query_params.get('only_pending', ['false'])[0].lower()
            only_pending = only_pending_val in ('true', '1', 'yes')
            severity = query_params.get('severity', ['all'])[0]
            comm_phase = query_params.get('comm_phase', ['all'])[0]

            payload = get_emergency_cockpit_payload(
                catalog_path=catalog_path,
                store_path=store_path,
                only_pending=only_pending,
                severity=severity,
                comm_phase=comm_phase
            )
            self._send_json(200, payload)
        except Exception as e:
            print(f"  Error obteniendo telemetría de emergencias: {e}")
            self._send_json(500, {'success': False, 'error': str(e)})

    def handle_incident_manager_save_message(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length <= 0:
                self._send_json(400, {'success': False, 'error': 'Payload vacío.'})
                return

            raw_body = self.rfile.read(content_length)
            body = json.loads(raw_body.decode('utf-8'))

            from incident_manager_service import validate_and_save_agent_message
            store_path = STORAGE_DIR / 'agent_executive_messages.json'
            eval_script = PROJECT_ROOT / 'converters' / 'cli' / 'evaluate_incident_notifications.py'

            status, resp = validate_and_save_agent_message(
                incident_id=body.get('incident_id', ''),
                phase=body.get('phase', ''),
                completo=body.get('completo', ''),
                breve=body.get('breve', ''),
                origen=body.get('origen', 'incident-reporter'),
                store_path=store_path,
                eval_script=eval_script
            )
            self._send_json(status, resp)
        except json.JSONDecodeError as e:
            self._send_json(400, {'success': False, 'error': f'JSON inválido: {e}'})
        except Exception as e:
            print(f"  Error guardando mensaje de agente: {e}")
            self._send_json(500, {'success': False, 'error': str(e)})

    def handle_ingestion_logs(self):
        """Devuelve el resumen estructurado y las últimas trazas del log de auditoría de ingesta."""
        try:
            summary_path = STORAGE_DIR / 'output' / 'ingestion_audit_summary.json'
            if not summary_path.exists():
                summary_path = PROJECT_ROOT / 'data' / 'output' / 'ingestion_audit_summary.json'

            log_path = STORAGE_DIR / 'logs' / 'ingestion_audit.log'
            if not log_path.exists():
                log_path = PROJECT_ROOT / 'data' / 'logs' / 'ingestion_audit.log'

            summary_data = None
            if summary_path.exists():
                try:
                    with open(summary_path, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                except Exception as e:
                    print(f"  Error leyendo resumen de auditoría: {e}")

            log_tail = []
            if log_path.exists():
                try:
                    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                        lines = f.readlines()
                        log_tail = lines[-200:]
                except Exception as e:
                    print(f"  Error leyendo log de auditoría: {e}")

            self._send_json(200, {
                'success': True,
                'has_summary': summary_data is not None,
                'has_log': log_path.exists(),
                'summary': summary_data,
                'log_tail': "".join(log_tail),
            })
        except Exception as e:
            self._send_json(500, {'success': False, 'error': str(e)})

    def handle_ingestion_retry_ia(self):
        """Relanza la obtención de Resumen IA en Epsilon para incidencias con error o todas si se fuerza."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
            payload = json.loads(raw_body) if raw_body.strip() else {}

            target_incidents = payload.get('incidents', [])
            force = bool(payload.get('force', False))
            all_active = bool(payload.get('all', False))

            try:
                from converters.cli.retry_epsilon_ia import (
                    retry_incidents,
                    find_missing_epsilon_incidents,
                    find_all_active_incident_codes,
                    CORPORATE_EPSILON_URL,
                    LOCAL_PROXY_URL
                )
            except ImportError:
                sys.path.insert(0, str(PROJECT_ROOT))
                from converters.cli.retry_epsilon_ia import (
                    retry_incidents,
                    find_missing_epsilon_incidents,
                    find_all_active_incident_codes,
                    CORPORATE_EPSILON_URL,
                    LOCAL_PROXY_URL
                )

            if not target_incidents:
                if all_active or force:
                    target_incidents = find_all_active_incident_codes(PROJECT_ROOT)
                else:
                    target_incidents = find_missing_epsilon_incidents(PROJECT_ROOT)

            if not target_incidents:
                self._send_json(200, {
                    'success': True,
                    'message': 'Todas las incidencias activas ya cuentan con Resumen IA. No hay pendientes de sincronización.',
                    'count': 0,
                    'results': {'success': [], 'failed': [], 'skipped_cached': []}
                })
                return

            candidate_urls = [CORPORATE_EPSILON_URL, LOCAL_PROXY_URL]
            results = retry_incidents(
                incident_codes=target_incidents,
                base_urls=candidate_urls,
                force=force,
                re_evaluate=True,
                project_root=PROJECT_ROOT,
            )

            # Cargar resumen de auditoría actualizado
            summary_path = PROJECT_ROOT / 'data' / 'output' / 'ingestion_audit_summary.json'
            summary_data = None
            if summary_path.exists():
                try:
                    with open(summary_path, 'r', encoding='utf-8') as f:
                        summary_data = json.load(f)
                except Exception:
                    pass

            self._send_json(200, {
                'success': True,
                'message': f"Relanzamiento finalizado: {len(results.get('success', []))} recuperadas, {len(results.get('skipped_cached', []))} ya cacheadas, {len(results.get('failed', []))} fallidas.",
                'count': len(target_incidents),
                'results': results,
                'summary': summary_data,
            })
        except Exception as e:
            self._send_json(500, {'success': False, 'error': str(e)})

    def handle_epsilon_generate(self):
        """Maneja la generación y validación de resúmenes vía POST /api/epsilon/generate y /api/epsilon/resumen."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except ValueError:
            content_length = 0

        if content_length <= 0:
            self._send_json(400, {"success": False, "error": "Cuerpo de solicitud vacío o JSON inválido"})
            return

        try:
            raw_body = self.rfile.read(content_length).decode('utf-8')
            payload = json.loads(raw_body)
        except Exception as e:
            self._send_json(400, {"success": False, "error": f"Cuerpo de solicitud vacío o JSON inválido: {e}"})
            return

        parsed_url = urllib.parse.urlparse(self.path)
        q_params = urllib.parse.parse_qs(parsed_url.query)
        is_mock_query = q_params.get('mock', [''])[0].lower() in ('1', 'true', 'yes')

        if isinstance(payload, dict) and "incident_data" in payload:
            incident_data = payload.get("incident_data", {})
            is_mock = is_mock_query or bool(payload.get("mock", False))
            model = payload.get("model")
            provider = payload.get("provider")
        elif isinstance(payload, dict):
            incident_data = payload
            is_mock = is_mock_query
            model = None
            provider = None
        else:
            self._send_json(400, {"success": False, "error": "Datos de incidencia insuficientes para generar resumen"})
            return

        if not isinstance(incident_data, dict) or not incident_data:
            self._send_json(400, {"success": False, "error": "Datos de incidencia insuficientes para generar resumen"})
            return

        if not generate_epsilon_summary:
            self._send_json(500, {"success": False, "error": "Módulo epsilon_service no disponible en el servidor"})
            return

        try:
            is_valid, data_or_errors, meta = generate_epsilon_summary(
                incident_data=incident_data,
                provider=provider,
                model=model,
                mock=is_mock,
            )
        except Exception as err:
            self._send_json(502, {"success": False, "error": f"Fallo en el servicio LLM: {err}"})
            return

        if not is_valid:
            self._send_json(422, {
                "success": False,
                "error": data_or_errors.get("error", "Error de validación de esquema Epsilon"),
                "validation_errors": data_or_errors.get("validation_errors", []),
                "raw_output": data_or_errors.get("raw_output", {}),
                "meta": meta,
            })
            return

        # Si se detecta un código de incidencia, guardar en la caché local
        code = (
            incident_data.get("codigo")
            or incident_data.get("id")
            or incident_data.get("ID de incidencia")
            or incident_data.get("id_incidencia")
            or ""
        )
        code_str = str(code).strip().upper()
        if code_str.startswith("INC"):
            try:
                cache_dir = PROJECT_ROOT / "data" / ".epsilon_cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_file = cache_dir / f"{code_str}.json"
                cache_bytes = json.dumps(data_or_errors, ensure_ascii=False, indent=2).encode('utf-8')
                cache_file.write_bytes(cache_bytes)
                EPSILON_CACHE[code_str] = (time.time(), cache_bytes, 200)
            except Exception as write_err:
                print(f"  Aviso: no se pudo persistir en .epsilon_cache: {write_err}")

        # Responder 200 OK estructurado con data y meta
        response_payload = {
            "success": True,
            "data": data_or_errors,
            "meta": meta,
            **data_or_errors,
        }
        self._send_json(200, response_payload)

    def handle_sync_remedy(self):
        """Maneja POST /api/sync-remedy disparando la sincronización incremental de Remedy."""
        if not sync_remedy_incidents:
            self._send_json(500, {"success": False, "error": "Módulo de sincronización MonTMC no disponible"})
            return

        dias = 3
        usuario = None

        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                raw_body = self.rfile.read(content_length)
                body_json = json.loads(raw_body.decode('utf-8'))
                if isinstance(body_json, dict):
                    if "dias" in body_json:
                        dias = int(body_json["dias"])
                    if "usuario" in body_json:
                        usuario = str(body_json["usuario"]).strip()
        except Exception:
            pass

        if '?' in self.path:
            q_str = self.path.split('?', 1)[1]
            q_params = urllib.parse.parse_qs(q_str)
            if 'dias' in q_params:
                try:
                    dias = int(q_params['dias'][0])
                except ValueError:
                    pass
            if 'usuario' in q_params:
                usuario = q_params['usuario'][0].strip()

        try:
            run_sync = sync_remedy_incidents
            if not hasattr(run_sync, 'mock_calls') and not getattr(run_sync, '_mock_return_value', None) is not None and not isinstance(run_sync, unittest.mock.Mock if 'unittest.mock' in sys.modules else ()):
                import importlib
                mod_name = 'converters.cli.sync_montmc_incidents'
                if mod_name in sys.modules:
                    importlib.reload(sys.modules[mod_name])
                    from converters.cli.sync_montmc_incidents import sync_remedy_incidents as reloaded_sync
                    run_sync = reloaded_sync

            result = run_sync(
                dias=dias,
                usuario=usuario,
                project_root=PROJECT_ROOT,
            )
            status_code = 200 if result.get("success") else 502
            self._send_json(status_code, result)
        except Exception as e:
            self._send_json(500, {"success": False, "error": f"Error interno en sincronización: {e}"})

    def handle_remedy_detail(self, id_remedy):
        """Maneja GET /api/remedy/detail/{idRemedy} con soporte de caché en memoria y disco."""
        clean_id = (id_remedy or "").strip().upper()
        if not clean_id:
            self._send_json(400, {"success": False, "error": "Falta idRemedy"})
            return

        q_params = urllib.parse.parse_qs(self.path.split('?', 1)[1]) if '?' in self.path else {}
        force = 'force' in q_params or 'refresh' in q_params or (q_params.get('force', [''])[0].lower() in ('1', 'true', 'yes'))
        no_cache = force or ('no-cache' in self.headers.get('Cache-Control', ''))
        now = time.time()

        # 1. Caché en memoria (TTL 300s)
        if not no_cache and clean_id in REMEDY_DETAIL_CACHE:
            cached_time, cached_payload, cached_status = REMEDY_DETAIL_CACHE[clean_id]
            if now - cached_time < 300:
                print(f"  Proxy Remedy Detail (cache HIT memoria): {clean_id}")
                resp_copy = dict(cached_payload)
                resp_copy["_cached"] = True
                self._send_json(cached_status, resp_copy)
                return

        # 2. Consulta en vivo a MonTMC
        client = MonTMCClient() if MonTMCClient else None
        if client:
            try:
                data = client.fetch_remedy_detail(clean_id)
                remedy_node = data.get("remedy") or {}
                worklogs = remedy_node.get("worklog") or []
                payload = {
                    "success": True,
                    "idRemedy": clean_id,
                    "remedy": remedy_node,
                    "worklogs": worklogs,
                    "detalle": remedy_node.get("detalle") or "",
                    "solucion": remedy_node.get("detalleSolucion") or "",
                    "paps": remedy_node.get("paps") or [],
                    "_cached": False,
                }
                REMEDY_DETAIL_CACHE[clean_id] = (now, payload, 200)

                # Persistencia en disco
                try:
                    cache_dir = PROJECT_ROOT / "data" / ".remedy_cache"
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    disk_file = cache_dir / f"{clean_id}.json"
                    with open(disk_file, "w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False)
                except Exception:
                    pass

                self._send_json(200, payload)
                return
            except RemedyNotFoundError as e:
                self._send_json(404, {"success": False, "error": str(e), "idRemedy": clean_id})
                return
            except Exception as e:
                print(f"  Aviso: Error consultando Remedy en MonTMC ({e}). Verificando caché en disco...")

        # 3. Fallback a caché en disco
        disk_file = PROJECT_ROOT / "data" / ".remedy_cache" / f"{clean_id}.json"
        if not no_cache and disk_file.exists():
            try:
                with open(disk_file, "r", encoding="utf-8") as f:
                    disk_payload = json.load(f)
                disk_payload["_cached"] = True
                disk_payload["_source"] = "disk_fallback"
                print(f"  Fallback exitoso a caché en disco para Remedy: {clean_id}")
                self._send_json(200, disk_payload)
                return
            except Exception as e:
                print(f"  Error leyendo caché en disco para Remedy: {e}")

        self._send_json(502, {
            "success": False,
            "error": f"No se pudo obtener detalle de Remedy para {clean_id} ni existe copia en caché local",
            "idRemedy": clean_id,
        })

    def do_GET(self):
        # Debug
        print(f"GET {self.path}")

        if (
            self.path.startswith(f"{EXECUTIVE_REPORT_PREFIX}/")
            or self.path == EXECUTIVE_REPORT_PREFIX
            or self.path.startswith(f"{EXECUTIVE_REPORT_V1_PREFIX}/")
            or self.path == EXECUTIVE_REPORT_V1_PREFIX
        ):
            self.handle_executive_report_get()
            return

        if self.path.startswith(REPORTS_PATH_PREFIX):
            self.handle_report_download()
            return

        if self.path == '/api/agents-catalog' or self.path.startswith('/api/agents-catalog?'):
            self.handle_agents_catalog()
            return

        if self.path == '/api/incident-manager/pending' or self.path.startswith('/api/incident-manager/pending?'):
            self.handle_incident_manager_pending()
            return

        clean_path = self.path.split('?')[0].rstrip('/')
        if clean_path == '/api/logs/ingestion' or self.path == '/api/logs/ingestion' or self.path.startswith('/api/logs/ingestion?'):
            self.handle_ingestion_logs()
            return

        if self.path == '/api/incident-manager/emergency-cockpit' or self.path.startswith('/api/incident-manager/emergency-cockpit?'):
            self.handle_incident_manager_emergency_cockpit()
            return

        if self.path.startswith('/api/reports') or self.path.startswith('/api/departments') or self.path in ('/healthz', '/readyz', '/api/health'):
            if self.proxy_to_fastapi_executive():
                return
            if self.path in ('/healthz', '/readyz', '/api/health'):
                self._send_json(200, {'status': 'ok', 'service': 'serve_app', 'timestamp': datetime.now(timezone.utc).isoformat()})
                return
            self._send_json(502, {'success': False, 'error': f'FastAPI backend ({FASTAPI_BACKEND_URL}) no disponible'})
            return

        if self.path.startswith('/api/epsilon/resumenIA/'):
            codigo = self.path[len('/api/epsilon/resumenIA/'):].split('?')[0].strip()
            self.proxy_to_epsilon_ia(codigo)
            return

        if self.path.startswith('/api/remedy/detail/'):
            id_remedy = self.path[len('/api/remedy/detail/'):].split('?')[0].strip()
            self.handle_remedy_detail(id_remedy)
            return

        if self.path.startswith('/problemas'):
            self.proxy_to_nextjs()
            return

        # Servir archivos desde STORAGE_DIR si se solicita /data/
        if self.path.startswith('/data/'):
            clean_rel = self.path[len('/data/'):].split('?')[0].lstrip('/')
            file_on_storage = STORAGE_DIR / clean_rel
            if not file_on_storage.is_file():
                file_on_storage = PROJECT_ROOT / 'data' / clean_rel
            if file_on_storage.is_file():
                try:
                    content = file_on_storage.read_bytes()
                    content_type = self.guess_type(str(file_on_storage))
                    self.send_response(200)
                    self.send_header('Content-type', content_type)
                    self.send_header('Content-Length', str(len(content)))
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(content)
                    return
                except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                    # El cliente cerró la conexión (recarga rápida en navegador o fetch abortado)
                    return
                except Exception as e:
                    print(f"  Error sirviendo {file_on_storage}: {e}")
                    return

        # Si es una petición para index.json, servirlo dinámicamente
        if 'index.json' in self.path:
            try:
                actual_path = STORAGE_DIR / 'output' / 'index.json'
                if not actual_path.exists():
                    actual_path = PROJECT_ROOT / 'data' / 'output' / 'index.json'
                print(f"  Intentando servir: {actual_path}")
                print(f"  Existe: {actual_path.exists()}")

                if actual_path.exists():
                    with open(actual_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    raw_bytes = content.encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Content-Length', str(len(raw_bytes)))
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(raw_bytes)
                    print(f"  Servido OK ({len(raw_bytes)} bytes)")
                    return
            except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
                return
            except Exception as e:
                print(f"  Error: {e}")
                return

        # Para todo lo demás, usar el comportamiento normal
        print(f"  Sirviendo normalmente desde: {self.directory}")
        return super().do_GET()

    def log_message(self, format, *args):
        print(f"[{self.client_address[0]}] {format % args}")

if __name__ == '__main__':
    os.chdir(PROJECT_ROOT)
    import argparse
    parser = argparse.ArgumentParser(description="Release Dashboard Static Server")
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=PORT,
        help=f"Puerto del servidor HTTP estático (default: {PORT})"
    )
    args, _ = parser.parse_known_args()
    PORT = args.port

    print("==================================================")
    print("Release Dashboard Server (Estático & Provisión)")
    print(f"Sirviendo desde: {PROJECT_ROOT}")
    print(f"URL: http://localhost:{PORT}/")
    print(f"Dashboard Portal: http://localhost:{PORT}/dashboards/portal/")
    print(f"Consola Triaje Emergencias: http://localhost:{PORT}/dashboards/emergency-triage-console/")
    print(f"Gestión de Problemas (proxy :3001): http://localhost:{PORT}/problemas")
    print(f"Nota: API principal FastAPI disponible en http://localhost:8000/docs")
    print("==================================================\n")
    print("Presiona Ctrl+C para detener el servidor\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), CustomHTTPHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido")


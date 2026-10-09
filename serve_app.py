#!/usr/bin/env python3
"""
Servidor HTTP personalizado para Release Dashboard Application
Resuelve problemas de sincronización de archivos en Windows
"""

import os
import re
import json
import sys
import http.server
import socketserver
import urllib.parse
from pathlib import Path
from email.parser import BytesParser
from email import policy

# Cambiar al directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.absolute()
os.chdir(PROJECT_ROOT)

sys.path.insert(0, str(PROJECT_ROOT / 'converters' / 'cli'))
from upload_csv import run_upload  # noqa: E402
from generate_postmortem_report import generate_report, generate_all_reports  # noqa: E402
from converters.src.report_generator.executive_models import (  # noqa: E402
    ExecutiveIncidentData,
    sanitize_incident_ref,
    extract_fields_from_jira_description,
)
from converters.src.report_generator.executive_paths import (  # noqa: E402
    get_executive_report_path,
    get_executive_report_filename,
    cleanup_old_executive_reports,
)
from converters.src.report_generator.executive_report_builder import ExecutiveReportBuilder  # noqa: E402
from converters.src.report_generator.confluence_parser import ConfluenceParser  # noqa: E402

REPORTS_PATH_PREFIX = '/api/reports/postmortem/'
EXECUTIVE_REPORT_PREFIX = '/api/reports/executive-incident'
EPSILON_CACHE = {}  # { codigo: (timestamp, content, status) }

# Puerto por defecto: 8080 para no colisionar con FastAPI (puerto 8000).
# Configurable vía variable de entorno PORT/SERVE_APP_PORT o argumento --port
DEFAULT_PORT = int(os.environ.get("SERVE_APP_PORT", os.environ.get("PORT", 8080)))
PORT = DEFAULT_PORT



class CustomHTTPHandler(http.server.SimpleHTTPRequestHandler):
    # Asegurar que sirve desde el PROJECT_ROOT
    directory = str(PROJECT_ROOT)

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
        self.send_response(502)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(msg)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(msg)

    def proxy_to_epsilon_ia(self, codigo):
        import ssl
        import time

        no_cache = 'no-cache' in self.headers.get('Cache-Control', '')
        now = time.time()
        if not no_cache and codigo in EPSILON_CACHE:
            cached_time, cached_content, cached_status = EPSILON_CACHE[codigo]
            if now - cached_time < 900:  # 15 minutos de caché
                print(f"  Proxy Epsilon IA (cache HIT): {codigo}")
                self.send_response(cached_status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('X-Cache-Status', 'HIT')
                self.send_header('Content-Length', str(len(cached_content)))
                self.end_headers()
                self.wfile.write(cached_content)
                return

        target_url = f"https://soptmc.si.orange.es/MonTMC/api/epsilon/resumenIA/{codigo}"
        print(f"  Proxy Epsilon IA (cache MISS/LIVE): {target_url}")
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(
                target_url,
                headers={'User-Agent': 'ReleaseDashboard/1.0', 'Accept': 'application/json'}
            )
            with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
                content = resp.read()
                if resp.status == 200:
                    EPSILON_CACHE[codigo] = (now, content, resp.status)
                self.send_response(resp.status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', '*')
                self.send_header('X-Cache-Status', 'MISS')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-cache')
                self.end_headers()
                self.wfile.write(content)
        except Exception as e:
            print(f"  Error proxy Epsilon IA: {e}")
            err_payload = json.dumps({"success": False, "error": str(e)}, ensure_ascii=False).encode('utf-8')
            self.send_response(502)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(err_payload)))
            self.end_headers()
            self.wfile.write(err_payload)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
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
        elif self.path == EXECUTIVE_REPORT_PREFIX or self.path == f'{EXECUTIVE_REPORT_PREFIX}/':
            self.handle_executive_report_generate()
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

        input_dir = PROJECT_ROOT / 'data' / 'input'
        input_dir.mkdir(parents=True, exist_ok=True)
        csv_path = input_dir / filename
        csv_path.write_bytes(file_bytes)
        print(f"  Guardado: {csv_path} ({len(file_bytes)} bytes)")

        result = run_upload(csv_path, dashboard_type, PROJECT_ROOT, release_name)

        if not result['success']:
            print(f"  Error de conversión: {result.get('details', result.get('error'))}")
            self._send_json(500, result)
            return

        print(f"  Conversión OK: {filename}")
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
        self.send_response(200)
        self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.presentationml.presentation')
        self.send_header('Content-Disposition', f'attachment; filename="{pptx_path.name}"')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_executive_report_generate(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
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
        path_without_prefix = self.path[len(EXECUTIVE_REPORT_PREFIX):].split('?')[0]
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
            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.presentationml.presentation')
            self.send_header('Content-Disposition', f'attachment; filename="{report_path.name}"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            self._send_json(500, {'success': False, 'error': f'Error al leer archivo: {str(e)}'})

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Debug
        print(f"GET {self.path}")

        if self.path.startswith(f"{EXECUTIVE_REPORT_PREFIX}/") or self.path == EXECUTIVE_REPORT_PREFIX:
            self.handle_executive_report_get()
            return

        if self.path.startswith(REPORTS_PATH_PREFIX):
            self.handle_report_download()
            return

        if self.path.startswith('/api/epsilon/resumenIA/'):
            codigo = self.path[len('/api/epsilon/resumenIA/'):].split('?')[0].strip()
            self.proxy_to_epsilon_ia(codigo)
            return

        if self.path.startswith('/problemas'):
            self.proxy_to_nextjs()
            return

        # Si es una petición para index.json, sirvirlo dinámicamente
        if 'index.json' in self.path:
            try:
                actual_path = PROJECT_ROOT / 'data' / 'output' / 'index.json'
                print(f"  Intentando servir: {actual_path}")
                print(f"  Existe: {actual_path.exists()}")

                if actual_path.exists():
                    with open(actual_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Content-Length', len(content))
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(content.encode('utf-8'))
                    print(f"  Servido OK ({len(content)} bytes)")
                    return
            except Exception as e:
                print(f"  Error: {e}")

        # Para todo lo demás, usar el comportamiento normal
        print(f"  Sirviendo normalmente desde: {self.directory}")
        return super().do_GET()

    def log_message(self, format, *args):
        print(f"[{self.client_address[0]}] {format % args}")

if __name__ == '__main__':
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


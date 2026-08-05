#!/usr/bin/env python3
"""
Servidor HTTP personalizado para Release Dashboard Application
Resuelve problemas de sincronización de archivos en Windows
"""

import os
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

REPORTS_PATH_PREFIX = '/api/reports/postmortem/'

PORT = 8000


class CustomHTTPHandler(http.server.SimpleHTTPRequestHandler):
    # Asegurar que sirve desde el PROJECT_ROOT
    directory = str(PROJECT_ROOT)

    def do_POST(self):
        print(f"POST {self.path}")
        if self.path == '/api/upload':
            self.handle_upload()
        elif self.path == f'{REPORTS_PATH_PREFIX}batch':
            self.handle_reports_batch()
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

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Debug
        print(f"GET {self.path}")

        if self.path.startswith(REPORTS_PATH_PREFIX):
            self.handle_report_download()
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

print(f"Release Dashboard Server")
print(f"Sirviendo desde: {PROJECT_ROOT}")
print(f"URL: http://localhost:{PORT}/")
print(f"Dashboard Portal: http://localhost:{PORT}/dashboards/portal/")
print(f"\nPresiona Ctrl+C para detener el servidor\n")

with socketserver.TCPServer(("", PORT), CustomHTTPHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido")

#!/usr/bin/env python3
"""
Servidor HTTP personalizado para Release Dashboard Application
Resuelve problemas de sincronización de archivos en Windows
"""

import os
import json
import http.server
import socketserver
from pathlib import Path

# Cambiar al directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.absolute()
os.chdir(PROJECT_ROOT)

PORT = 8000

class CustomHTTPHandler(http.server.SimpleHTTPRequestHandler):
    # Asegurar que sirve desde el PROJECT_ROOT
    directory = str(PROJECT_ROOT)

    def do_GET(self):
        # Debug
        print(f"GET {self.path}")

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
print(f"Dashboard Portal: http://localhost:{PORT}/dashboards/src/dashboard-portal.html")
print(f"\nPresiona Ctrl+C para detener el servidor\n")

with socketserver.TCPServer(("", PORT), CustomHTTPHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido")

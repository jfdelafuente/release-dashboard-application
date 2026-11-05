"""
Cliente HTTP / REST API para Confluence (Atlassian Cloud y Data Center).
"""

import re
import requests
from incident_report.config import Settings


class ConfluenceClient:
    def __init__(
        self,
        token: str = None,
        user: str = None,
        timeout: int = 15,
        verify_ssl: bool = None,
    ):
        settings = Settings.from_env(verify_ssl_override=verify_ssl)
        self.token = token or settings.confluence_token
        self.user = user or settings.confluence_user
        self.timeout = timeout
        self.verify_ssl = settings.confluence_verify_ssl

        if not self.verify_ssl:
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass

    def fetch_page(self, url: str) -> str:
        """
        Obtiene el contenido HTML de una página de Confluence.
        Soporta tanto descarga directa como Confluence REST API (imprescindible para Atlassian Cloud).
        """
        headers = {
            "User-Agent": "IncidentExecutiveReportCLI/2.0",
            "Accept": "application/json, text/html, */*",
        }

        auth = None
        if self.token:
            if self.user:
                auth = (self.user, self.token)
            else:
                headers["Authorization"] = f"Bearer {self.token}"

        page_id_match = re.search(r"/pages/(\d+)", url) or re.search(r"[?&]pageId=(\d+)", url)
        if page_id_match:
            page_id = page_id_match.group(1)
            base_match = re.match(r"(https?://[^/]+(?:/wiki)?)", url)
            if base_match:
                base_wiki_url = base_match.group(1)
                if "atlassian.net" in base_wiki_url and not base_wiki_url.endswith("/wiki"):
                    base_wiki_url = f"{base_wiki_url}/wiki"
                api_url = f"{base_wiki_url}/rest/api/content/{page_id}?expand=body.storage,version"

                try:
                    api_resp = requests.get(
                        api_url,
                        headers=headers,
                        auth=auth,
                        timeout=self.timeout,
                        verify=self.verify_ssl,
                    )
                    if api_resp.status_code == 200:
                        data = api_resp.json()
                        title = data.get("title", "")
                        storage_value = (
                            data.get("body", {})
                            .get("storage", {})
                            .get("value", "")
                        )
                        return f"<h1>{title}</h1>\n{storage_value}"
                    elif api_resp.status_code in [401, 403]:
                        raise PermissionError(
                            f"Error de autenticación con Confluence Cloud (HTTP {api_resp.status_code}).\n"
                            "Para instancias Cloud (atlassian.net), asegúrese de configurar en su archivo .env:\n"
                            "  CONFLUENCE_USER=su_correo@dominio.com\n"
                            "  CONFLUENCE_TOKEN=su_api_token\n"
                            "(Puede generar un API Token en: https://id.atlassian.com/manage-profile/security/api-tokens)"
                        )
                except requests.exceptions.SSLError as e:
                    raise ConnectionError(
                        f"Error de verificación SSL al conectar con Confluence ({url}):\n{e}\n\n"
                        "Este fallo ocurre habitualmente en redes corporativas con inspección SSL (proxy corporativo).\n"
                        "Soluciones:\n"
                        "  1. Añada el flag '--no-verify-ssl' a su comando:\n"
                        '       python generate_report.py --url "..." --no-verify-ssl ...\n'
                        "  2. O configure en su archivo .env:\n"
                        "       CONFLUENCE_VERIFY_SSL=false\n"
                        "  3. O descargue/guarde la página en HTML local y ejecute con:\n"
                        "       python generate_report.py --file postmortem.html ..."
                    )
                except (PermissionError, FileNotFoundError):
                    raise
                except Exception:
                    pass

        try:
            response = requests.get(
                url,
                headers=headers,
                auth=auth,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            if response.status_code == 200:
                return response.text
            elif response.status_code in [401, 403]:
                raise PermissionError(
                    f"Error de autenticación con Confluence (HTTP {response.status_code}). "
                    "Por favor verifique el token de acceso en el archivo .env o en la variable CONFLUENCE_TOKEN."
                )
            elif response.status_code == 404:
                raise FileNotFoundError(
                    f"Página de Confluence no encontrada (HTTP 404): {url}"
                )
            else:
                raise RuntimeError(
                    f"Error al obtener contenido de Confluence: HTTP {response.status_code} - {response.reason}"
                )
        except requests.exceptions.SSLError as e:
            raise ConnectionError(
                f"Error de verificación SSL al conectar con Confluence ({url}):\n{e}\n\n"
                "Este fallo ocurre habitualmente en redes corporativas con inspección SSL (proxy corporativo).\n"
                "Soluciones:\n"
                "  1. Añada el flag '--no-verify-ssl' a su comando:\n"
                '       python generate_report.py --url "..." --no-verify-ssl ...\n'
                "  2. O configure en su archivo .env:\n"
                "       CONFLUENCE_VERIFY_SSL=false\n"
                "  3. O descargue/guarde la página en HTML local y ejecute con:\n"
                "       python generate_report.py --file postmortem.html ..."
            )
        except requests.Timeout:
            raise TimeoutError(
                f"Tiempo de espera agotado al conectar con Confluence ({self.timeout}s). Verifique su conexión de red o VPN."
            )
        except requests.RequestException as e:
            raise ConnectionError(
                f"Error de conexión con Confluence ({url}): {e}"
            )


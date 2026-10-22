# Contrato de Comandos CLI: deploy-agents.cmd Integration

**Feature**: `011-agents-skills-catalog`

---

## 1. Propósito

Definir las reglas formales de construcción sintáctica para los comandos de despliegue generados en la interfaz de usuario del dashboard y copiados al portapapeles del operador.

---

## 2. Parámetros del Script `deploy-agents.cmd`

El script nativo `.\deploy-agents.cmd` (ubicado en `C:\Users\jose.delafuente\Claude\Projects\biblioteca-agentes\deploy-agents.cmd`) delega en PowerShell `.agents/skills/agent-deployer/scripts/deploy_agents.ps1`.

### Argumentos reconocidos:
- **`TargetRepo`** (Posicional 1 o `-TargetRepo`): Ruta al directorio raíz del proyecto destino (obligatorio).
- **`-Agents`**: Lista de nombres o alias de agentes separados por comas (ej. `"incident-analyzer,incident-reporter"`).
- **`-Domain`**: Nombre de un dominio completo (ej. `"it-incidents"` o `"brand-content"`).
- **`-All`**: Flag para desplegar todos los agentes y skills de la biblioteca.
- **`-WhatIf`**: Flag para simular la operación sin copiar archivos.
- **`-Force`**: Sobrescribir archivos existentes sin confirmación interactiva.
- **`-List`**: Muestra el catálogo en texto.

---

## 3. Matriz de Generación de Comandos en el Dashboard

| Acción en UI | Entrada | Comando Generado |
| :--- | :--- | :--- |
| **Copia Rápida 1-Clic** (Tarjeta Agente) | Agente `incident-analyzer`, TargetRepo `<TargetRepo>` | `.\deploy-agents.cmd "<TargetRepo>" -Agents "incident-analyzer"` |
| **Copia Rápida con Ruta Previa** | Agente `orange-brand-generator`, TargetRepo `C:\proyectos\app` | `.\deploy-agents.cmd "C:\proyectos\app" -Agents "orange-brand-generator"` |
| **Despliegue por Dominio** | Dominio `it-incidents`, TargetRepo `<TargetRepo>` | `.\deploy-agents.cmd "<TargetRepo>" -Domain "it-incidents"` |
| **Despliegue Lote (Multi-selección)** | Agentes `[incident-describer, incident-reporter]`, TargetRepo `<TargetRepo>` | `.\deploy-agents.cmd "<TargetRepo>" -Agents "incident-describer,incident-reporter"` |
| **Modo Simulación (WhatIf)** | Agente `incident-analyzer`, Flag WhatIf marcado | `.\deploy-agents.cmd "<TargetRepo>" -Agents "incident-analyzer" -WhatIf` |

---

## 4. Gestión del Portapapeles y Notificación en UI

1. Al hacer clic en el botón de copia, se ejecuta `navigator.clipboard.writeText(command)`.
2. Se muestra un feedback visual inmediato:
   - El botón cambia temporalmente su texto/icono a `✓ Copiado` durante 2.5 segundos.
   - Si está disponible `ui-feedback.js`, se dispara un toast flotante corporativo: `"Comando copiado al portapapeles"`.
3. Si el usuario aún no ha configurado una ruta en el asistente, el placeholder `<TargetRepo>` queda claramente señalado para recordarle sustituirlo o completar el campo en el asistente.


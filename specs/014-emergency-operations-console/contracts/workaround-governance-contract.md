# Contract: Workaround Governance & De-escalation Restriction (`workaround-governance-contract`)

**Feature**: `014-emergency-operations-console`  
**Governing Authority**: Customer & Service Ops (IM-CSO)  
**Standard**: Skill `orange-it-emergency-management` (Reglas de Oro de Triaje y BCM)  

---

## 1. Principio Fundamental (Regla de Oro N2 y N3)

> **"La aplicación de cualquier workaround o solución temporal requiere siempre la autorización explícita de Customer & Service Ops (IM-CSO). Un workaround NO reduce automáticamente la severidad del ticket. Una Emergencia solo se da por resuelta cuando el impacto sobre el negocio o servicio ha desaparecido por completo."**

---

## 2. Reglas de Validación de Desescalada

### Regla R-GOV-01: Prohibición de Desescalada Unilateral
Cualquier acción en la interfaz que intente:
- Modificar la severidad sugerida de `SL1` a `SL2`, `SL3` o `SL4`.
- Marcar la incidencia como `Resuelta` o `Cerrada` en el flujo de monitorización mientras persista un impacto no erradicado.
**DEBE ser rechazada y bloqueada.**

### Regla R-GOV-02: Bloqueo Visual Activo
Cuando un ticket cuente con mitigación o parche temporal activo (`workaround_detectado == true`), la consola debe:
1. Renderizar el estado de bloqueo:
   ```html
   <div class="im-gov-lock-banner">
     <span class="im-gov-lock-icon">🔒</span>
     <div>
       <strong>Desescalada Bloqueada por Regla de Oro:</strong>
       <span>Workaround activo requiere autorización de IM-CSO y erradicación total del impacto en producción.</span>
     </div>
   </div>
   ```
2. Mostrar el selector de severidad en estado deshabilitado (`disabled`) con tooltip explicativo.
3. Deshabilitar cualquier acción de cierre operativo en la interfaz.

### Regla R-GOV-03: Autorización Exclusiva por IM-CSO
Solo una confirmación formal registrada en la gobernanza por Customer & Service Ops permite levantar la advertencia de autorización pendiente. No obstante, el bloqueo de desescalada permanece activo mientras el servicio continúe degradado.

---

## 3. Matriz de Estados de Workaround

| Estado Workaround | Autorizado por CSO | Impacto Erradicado | ¿Permite Desescalar? | Estado en UI |
| :---: | :---: | :---: | :---: | :--- |
| **No detectado** | N/A | No | No (Sigue en fallo) | Severidad SL1 fija |
| **Detectado** | ❌ No | ❌ No | ❌ **BLOQUEADO** | Alerta roja: *Pendiente Autorización CSO* + Candado |
| **Detectado** | ✅ Sí | ❌ No | ❌ **BLOQUEADO** | Badge verde: *Autorizado CSO* + Candado (Impacto activo) |
| **Erradicado** | ✅ Sí | ✅ Sí | ✅ **PERMITIDO** | Banner verde: *Impacto erradicado; cierre autorizado* |


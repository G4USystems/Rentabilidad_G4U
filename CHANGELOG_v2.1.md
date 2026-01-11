# Tío Gilito P&L - Actualización Completa v2.1

**Fecha:** 11 Enero 2026
**Commit:** `962bb5f`
**Branch:** main

---

## Resumen Ejecutivo

Esta actualización incluye **fixes críticos de bugs**, **ofertas dinámicas desde Airtable**, **distribución de gastos generales por mes/proyecto**, y la **base para AI Brain** (simulaciones financieras).

---

## 1. BUGS CORREGIDOS

### 1.1 Error 422 al Actualizar Proyectos
**Problema:** Airtable devolvía error 422 (Unprocessable Entity) al editar proyectos.

**Causa raíz:**
- Se enviaban strings vacíos `""` para campos Date y Single Select
- El campo "Service" no existía como linked record

**Solución implementada:**
- Solo se envían campos con valores NO vacíos
- Validación con `.strip()` antes de incluir en el record
- Service ahora es linked record a tabla "Ofertas G4U"

**Archivos:** `api/index.py` líneas 1908-1950, 1959-2010

---

### 1.2 Top Gastos Solo Mostraba "Sin Categoría"
**Problema:** El widget de Top Gastos por Categoría G4U solo mostraba "Sin Categoría G4U".

**Causa:** Se usaba `t.category_id` pero el campo correcto es `t.category`.

**Solución:**
```javascript
var catId = t.category || t.category_id || '';
var cat = categories.find(c => c.id === catId);
key = cat ? cat.name : 'Sin Categoría G4U';
```

**Archivo:** `api/static/index.html` línea 2253

---

### 1.3 Botón "Excluir" No Funcionaba
**Problema:** Al hacer clic en "Excluir" transacción, daba error porque el campo `Is Excluded` no existía en Airtable.

**Solución:** Las transacciones excluidas se guardan en `settings.json` local, no en Airtable.

```json
{
  "excluded_transactions": ["tx_id_1", "tx_id_2", ...]
}
```

**Archivos:** `api/index.py` líneas 2541-2603, `api/settings.json`

---

## 2. OFERTAS G4U DINÁMICAS

### 2.1 Nueva Tabla en Airtable
Se creó la tabla **"Ofertas G4U"** con:
- `Name`: Nombre de la oferta (GTM, Consulting, etc.)
- `Descripcion`: Descripción opcional
- `Projects`: Linked record inverso a Projects

### 2.2 Campo Service como Linked Record
El campo **Service** en Projects ahora es un `multipleRecordLinks` que apunta a "Ofertas G4U".

**Cómo funciona:**
1. Frontend carga ofertas desde `/api/settings/offerings`
2. Selectores se populan dinámicamente con IDs de Airtable
3. Al guardar proyecto, se envía como array: `{"Service": ["recXXX"]}`
4. Al mostrar, se resuelve ID a nombre

### 2.3 Ofertas Disponibles
| ID Record | Nombre |
|-----------|--------|
| recg8meBhWruwB1Sw | GTM (Go-To-Market) |
| recT6ADwo6IY3z0BA | Consulting |
| recqpH6csRgmIZcxo | Training |
| rec2tJ01Vf0UqLF1u | Development |
| recO3MXyOxzWmJV2W | Marketing |
| recspuyhs3W9J77fG | Otro |
| recVmZbTlB5hctU27 | Trust Engine |

**Cómo agregar nuevas ofertas:** Directamente en la tabla "Ofertas G4U" de Airtable.

---

## 3. DISTRIBUCIÓN DE GASTOS GENERALES

### 3.1 Concepto
Los gastos asignados al proyecto **"General"** se distribuyen porcentualmente entre los proyectos activos de cada mes.

### 3.2 Definición de Proyecto Activo
Un proyecto es **ACTIVO** en un mes si:
1. Status = "Active" o "Activo"
2. `start_date <= fin_del_mes`
3. `end_date` es null O `end_date >= inicio_del_mes`
4. NO es el proyecto "General" (es la fuente, no destino)

**Ejemplo:**
```
Proyecto A: start="2025-01-01", end="2025-03-31" → Activo en Ene, Feb, Mar
Proyecto B: start="2025-02-01", end=null → Activo desde Feb en adelante
Proyecto C: start="2024-01-01", end="2024-12-31" → Inactivo en 2025
```

### 3.3 Configuración en Settings
En la sección **Settings > Distribución Mensual de Gastos Generales**:
1. Selecciona el mes (YYYY-MM)
2. Aparecen los proyectos activos de ese mes
3. Asigna % a cada proyecto (suma debe ser ≤ 100%)
4. Guarda

**Almacenamiento** (`settings.json`):
```json
{
  "monthly_distributions": {
    "2025-01": {
      "recProyectoA": 40,
      "recProyectoB": 60
    },
    "2025-02": {
      "recProyectoA": 30,
      "recProyectoB": 50,
      "recProyectoC": 20
    }
  }
}
```

### 3.4 Cálculo en P&L

**P&L por Proyectos:**
1. Se agrupan gastos del proyecto "General" por mes
2. Para cada mes, se aplica la distribución configurada
3. Los gastos se mueven del "General" a los proyectos destino

**Fórmula:**
```
gastoDistribuido = gastoGeneralMes × porcentajeProyecto / sumaPorcentajes
```

**P&L por Clientes:**
1. Mismo proceso, pero se mapea proyecto → cliente
2. El cliente del proyecto recibe los gastos distribuidos

**Ejemplo práctico:**
```
Gastos General en Enero: €10,000
Distribución: ProyectoA=40%, ProyectoB=60%
ProyectoA (Cliente: Multiplo) recibe: €4,000
ProyectoB (Cliente: Paymatico) recibe: €6,000
General queda en: €0
```

---

## 4. ENDPOINTS IMPLEMENTADOS

### 4.1 Proyectos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/projects` | Lista de proyectos |
| POST | `/api/project` | Crear proyecto |
| PUT | `/api/project/<id>` | Actualizar proyecto |
| DELETE | `/api/project/<id>` | Eliminar proyecto |

### 4.2 Ofertas G4U
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/settings/offerings` | Lista de ofertas (desde Airtable) |
| POST | `/api/settings/offerings` | Guardar ofertas (en settings.json) |
| POST | `/api/admin/create-offerings-table` | Crear tabla Ofertas en Airtable |

### 4.3 Distribución de Gastos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/monthly-distribution?month=YYYY-MM` | Distribución de un mes + proyectos activos |
| POST | `/api/monthly-distribution` | Guardar distribución mensual |
| GET | `/api/monthly-distribution/all` | Todas las distribuciones guardadas |
| GET | `/api/general-expenses-distribution` | Config general (legacy) |

### 4.4 Transacciones
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| PUT | `/api/transaction/<id>` | Actualizar (categoría, proyecto, excluir) |
| GET | `/api/excluded-transactions` | IDs de transacciones excluidas |
| GET | `/api/transaction-allocations` | Todas las asignaciones |
| POST | `/api/transaction-allocation` | Crear asignación |

### 4.5 AI Brain (Preview)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/ai/chat` | Chat con AI para análisis |
| POST | `/api/ai/scenario` | Ejecutar escenario predefinido |

---

## 5. AI BRAIN (Preview)

### 5.1 Modelos Soportados
- **Groq:** Llama 3 70B, Mixtral 8x7B (ultra rápido, gratuito con límites)
- **OpenAI:** GPT-4o, GPT-4o Mini, o1, o1-mini
- **Anthropic:** Claude Opus, Sonnet, Haiku
- **Google:** Gemini 2.0 Pro, Flash
- **xAI:** Grok 2

### 5.2 Escenarios Predefinidos
1. **Proyección 3 meses:** Optimista / Base / Pesimista
2. **Detectar anomalías:** Gastos inusuales
3. **Tendencias:** Análisis estacional
4. **Optimización:** Sugerencias de ahorro
5. **What-if +20% ingresos**
6. **What-if -10% costos**

### 5.3 Requisitos
Variables de entorno con API keys:
- `GROQ_API_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GEMINI_API_KEY`
- `XAI_API_KEY`

---

## 6. ESTRUCTURA DE ARCHIVOS

### 6.1 api/settings.json
```json
{
  "service_offerings": [...],           // Fallback si Airtable no disponible
  "general_expenses_distribution": {},  // Config legacy
  "monthly_distributions": {},          // Distribuciones por mes
  "excluded_transactions": []           // IDs de transacciones excluidas
}
```

### 6.2 Archivos Modificados
| Archivo | Cambios |
|---------|---------|
| `api/index.py` | +939 líneas (endpoints, validaciones, AI) |
| `api/static/index.html` | +1464 líneas (UI, filtros, P&L) |
| `api/settings.json` | Nuevo archivo de configuración |

---

## 7. ESTADO DEL FEEDBACK

| # | Feedback | Estado | Notas |
|---|----------|--------|-------|
| 1 | Error 422 al actualizar proyectos | ✅ Resuelto | No enviar strings vacíos |
| 2 | Ofertas G4U hardcodeadas | ✅ Resuelto | Tabla dinámica en Airtable |
| 3 | Top Gastos solo "Sin Categoría" | ✅ Resuelto | Resolver category correctamente |
| 4 | Botón Excluir no funciona | ✅ Resuelto | Guardar en settings.json |
| 5 | Distribución gastos generales | ✅ Implementado | Por mes y proyecto activo |
| 6 | Quitar IVA de ingresos | ⏳ Pendiente | Toggle implementado, lógica pendiente |
| 7 | Margen promedio incorrecto | ⏳ Pendiente | Usar margen ponderado |
| 8 | Filtro parcialmente asignadas | ⏳ Pendiente | - |
| 9 | AI Brain para simulaciones | 🔄 En progreso | UI lista, funciones JS pendientes |

---

## 8. PRÓXIMOS PASOS

1. **Completar AI Brain:** Implementar funciones JS de chat y escenarios
2. **Fix IVA:** Calcular ingresos netos usando `vat_amount`
3. **Margen ponderado:** Calcular margen global por ingresos, no promedio simple
4. **Headers sticky:** En tabla de transacciones
5. **Drilldown P&L:** Click en proyecto → ver transacciones

---

@Alfonso Saiz de Baranda - Aquí tienes el changelog completo. Lo más importante:

1. **Ya funcionan las ofertas** desde Airtable (tabla "Ofertas G4U")
2. **Error 422 corregido** - ya se pueden editar proyectos sin problemas
3. **Distribución de gastos generales** funciona por mes/proyecto activo
4. **AI Brain** tiene la UI lista, falta conectar las funciones JS

Para agregar nuevas ofertas: directamente en Airtable > tabla "Ofertas G4U" > nuevo registro.

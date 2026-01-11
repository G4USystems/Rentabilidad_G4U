# Feedback Pendiente de Implementación - Tio Gilito P&L G4U

Este documento contiene todos los items de feedback y bugs reportados por el equipo que están pendientes de implementación.

---

## Estado de Items

| # | Título | Status | Prioridad |
|---|--------|--------|-----------|
| 1 | Quitar IVA de los ingresos | Waiting Review | CRÍTICO |
| 2 | Diferenciar Ingresos y Gastos en categorías | Waiting Review | ALTO |
| 3 | Arreglar margen promedio de Proyectos | Waiting Review | CRÍTICO |
| 4 | Ordenar columnas en Transacciones | Waiting Review | ALTO |
| 5 | Gastos "Generales" repartidos por cliente | Waiting Review | ALTO |
| 6 | Salarios por transacción, no por panel | Waiting Review | ALTO |
| 7 | Filtros "Sin Categoría / Cliente / Proyecto" | Waiting Review | ALTO |
| 8 | Arreglar bugs varios v1 | Feedback | CRÍTICO |
| 9 | Qué hacer con devoluciones | Feedback | MEDIO |
| 10 | Drilldown desde P&L por proyectos | Feedback | ALTO |
| 11 | Excluir transacciones del flujo de caja | Feedback | ALTO |
| 12 | Versión v1 (meta-task) | Feedback | - |

---

## 1. Poder quitar el IVA de los ingresos

**Status:** Waiting Review
**Prioridad:** CRÍTICO

### Descripción
> Ahora mismo los ingresos y gastos incluyen IVA a la hora de calcular la rentabilidad. ¿Qué se puede hacer? ¿Podríamos sacar todo lo que es IVA de TODAS las transacciones y hacer una parte de Impuestos donde apareciera ahí todo?

> Creo que Qonto tiene columnas donde te divide el monto entre IVA y no IVA

### Comentario de Alfonso
> *No está funcionando bien. Pongo el IVA, pero luego en la parte de rentabilidad sigue apareciendo los ingresos. Por ejemplo, en Multiplo los ingresos deberían ser 15.000€ en PnL pero aparecen con IVA.*

### Solución Propuesta
- Qonto provee `vat_amount_cents` y `vat_rate` en cada transacción
- Calcular monto neto: `amount - vat_amount`
- Agregar toggle en UI "Mostrar montos sin IVA"
- Crear sección "Impuestos" separada en P&L

---

## 2. Diferenciar Ingresos y Gastos en categorías

**Status:** Waiting Review
**Prioridad:** ALTO

### Descripción
> Deberían estar ordenadas y diferenciando las de ingresos de las de gastos

### Solución Propuesta
```html
<optgroup label="📈 INGRESOS">
  <option>Revenue</option>
  <option>Other Income</option>
</optgroup>
<optgroup label="📉 GASTOS">
  <option>COGS</option>
  <option>Operating Expense</option>
  ...
</optgroup>
```

---

## 3. Arreglar margen promedio de Proyectos

**Status:** Waiting Review
**Prioridad:** CRÍTICO

### Descripción
> Eso de -37,9% está mal

### Problema Identificado
Se está calculando promedio simple de márgenes en lugar de margen ponderado.

### Solución
```javascript
// Incorrecto (actual):
avgMargin = sum(margins) / count

// Correcto:
const totalIncome = projects.reduce((s, p) => s + p.income, 0);
const totalExpenses = projects.reduce((s, p) => s + p.expenses, 0);
const globalMargin = totalIncome > 0
  ? ((totalIncome - totalExpenses) / totalIncome * 100)
  : 0;
```

---

## 4. Ordenar columnas en Transacciones

**Status:** Waiting Review
**Prioridad:** ALTO

### Descripción
> Al hacer click en cada columna, debería poder reordenar las transacciones de mayor a menor y de menor a mayor. Sobre todo por Monto

### Solución Propuesta
- Habilitar sorting en todas las columnas de la tabla
- Prioridad: Monto, Fecha, Contraparte
- Indicador visual de orden (▲/▼)

---

## 5. Gastos "Generales" repartidos por cliente

**Status:** Waiting Review
**Prioridad:** ALTO

### Descripción
> Deberíamos poder seleccionar gastos como proyecto/cliente "General" y que desde Ajustes podamos dictaminar que % de los Generales se dividen por cada uno de los clientes

### Solución Propuesta
1. Crear proyecto/categoría especial "General"
2. En Ajustes → Nueva sección "Distribución de Generales"
3. Configurar % por cliente (debe sumar 100%)
4. En P&L por Cliente: agregar porcentaje correspondiente de gastos generales

### Nuevo Modelo
```python
class GeneralExpenseDistribution(Base):
    id: int
    client_name: str
    percentage: Decimal  # Ej: 30.00 = 30%
    is_active: bool
```

---

## 6. Salarios por transacción, no por panel

**Status:** Waiting Review
**Prioridad:** ALTO

### Descripción
> Ahora mismo, los salarios se dividen en un panel de Configuraciones. Creo que esto no es correcto. Lo mejor es que las transacciones se puedan "dividir" y asignar cada gasto o ingreso a múltiples proyectos o clientes.

> De esta manera, el control sería más granular y real

### Solución Propuesta
- Ya existe `TransactionAllocation` en el backend
- Mejorar UI para permitir división fácil:
  1. Botón "Dividir" en cada transacción
  2. Modal con líneas: Proyecto | Cliente | % | Monto
  3. Validar suma = 100%

---

## 7. Filtros "Sin Categoría / Cliente / Proyecto"

**Status:** Waiting Review
**Prioridad:** ALTO

### Descripción
> Para poder clasificar rápido, quiero poder solo ver las que no tienen categoría, cliente o proyecto

### Solución Propuesta
Agregar opciones al filtro de estado:
- "Sin Categoría"
- "Sin Proyecto"
- "Sin Cliente"
- "Sin ninguna asignación"

---

## 8. Arreglar Bugs varios v1

**Status:** Feedback
**Prioridad:** CRÍTICO

### Sub-items:

#### 8.1 Cambio Copy: "Este AÑO"
**Status:** ARREGLADO ✅

#### 8.2 Cambio Copy: "Egreso" → "Gasto", "Monto" → "Cantidad"
**Status:** Pendiente

#### 8.3 Filtro parcialmente asignadas no funciona
**Descripción:** No aparecen las que tienen categoría pero no proyecto con el filtro actual.

**Solución:** Revisar lógica de filtrado:
```javascript
// Parcialmente asignada = tiene ALGUNO pero NO TODOS:
const isPartial = (
  (t.category_id && !t.project_id) ||
  (!t.category_id && t.project_id) ||
  // otras combinaciones
);
```

#### 8.4 Filtro en PnL no funciona
**Status:** Pendiente investigación

#### 8.5 Asignación de ingresos no funciona (Fellow)
**Descripción:** En Fellow, los ingresos mostrados en la tabla no coinciden con el resumen de P&L.

**Causa probable:** Las allocations no se suman correctamente cuando hay múltiples por transacción.

#### 8.6 Asignación no funciona bien
**Descripción:** Muchas transacciones aparecen al 1%. Al intentar quitarlas, da error.

#### 8.7 Suma 1% / flujo de asignación
**Pregunta del equipo:** "¿Deberíamos dejar editar? ¿Cómo puede ser más rápido este proceso?"

**Respuesta de Martin:** Si usas la selección múltiple usando el checkbox al lado de cada transacción, cuando asignas % se asigna la misma proporción en todas las seleccionadas.

---

## 9. Qué hacer con devoluciones

**Status:** Feedback
**Prioridad:** MEDIO

### Descripción
> Todo esto son devoluciones. ¿Qué hacemos con ellas? ¿Podemos crear algo para "ignorar transacciones"? Tampoco creo que mueva mucho la aguja pero desde luego molesta

### Opciones Propuestas
1. **Auto-detectar:** Usar `status = reversed` de Qonto
2. **Categoría especial:** "Devolución" que se netea automáticamente
3. **Excluir:** Marcar como `is_excluded_from_reports = true`
4. **Vincular:** Agrupar devolución con transacción original

---

## 10. Drilldown desde P&L por proyectos

**Status:** Feedback
**Prioridad:** ALTO

### Descripción
> En vista PnL por proyectos, debería poder hacerse click y ver los ingresos y gastos asignados a cada proyecto. Una vista filtrada directamente, o poner debajo del PnL esas transacciones

### Solución Propuesta
1. Hacer las tarjetas de proyecto clickeables
2. Al click, opción A: Cambiar a vista transacciones filtrada
3. Al click, opción B: Mostrar modal/expandible con transacciones

```javascript
function showProjectTransactions(projectId) {
  showView('transactions');
  document.getElementById('filter-project').value = projectId;
  applyTransactionFilters();
}
```

---

## 11. Excluir transacciones del flujo de caja

**Status:** Feedback
**Prioridad:** ALTO

### Descripción
> Por ejemplo, estas transacciones son de la inversión en marketing de Fellow Funders. No son un ingreso ni un gasto. Solo algo que gestionamos. Me gustaría poder seleccionar estas transacciones y que no se consideren ingresos o gastos de nada

### Estado Actual
Ya existe `is_excluded_from_reports` en el modelo Transaction.

### Mejora Necesaria
1. Agregar checkbox/botón "Excluir de reportes" en UI
2. Badge visual para transacciones excluidas
3. Opción de filtrar por "Excluidas"

---

## 12. Versión v1 (meta-task)

**Status:** Feedback

Esta es la versión que agrupa todos los issues anteriores. Representa el milestone v1 del producto.

---

## Notas Adicionales

### Comunicación del Equipo

**Sobre versión desactualizada:**
- Alfonso reportó que estaba en versión anterior
- Martin indicó usar el link en "App"

**Sobre flujo de asignación:**
- La selección múltiple permite asignar el mismo % a varias transacciones a la vez

---

## Priorización Recomendada

### Sprint 1 - Crítico (1-2 semanas)
1. Quitar IVA de ingresos
2. Arreglar margen promedio
3. Fix filtro parcialmente asignadas
4. Fix asignación de ingresos
5. Fix error allocations 1%

### Sprint 2 - UX (1 semana)
1. Diferenciar categorías ingresos/gastos
2. Ordenar columnas transacciones
3. Filtros "Sin..."
4. Cambios de copy

### Sprint 3 - Features (2 semanas)
1. Drilldown P&L → Transacciones
2. División de transacciones en UI
3. Excluir transacciones
4. Manejo devoluciones

### Sprint 4 - Arquitectura (2 semanas)
1. Gastos Generales distribuidos
2. Mejoras de performance

---

*Última actualización: 2026-01-11*

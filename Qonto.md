# Qonto API - Documentación Completa

## Descripción General

Qonto es un banco digital para empresas y autónomos en Europa. Su API permite integrar servicios bancarios en aplicaciones, automatizar operaciones financieras y acceder a datos de transacciones en tiempo real.

**Documentación Oficial:** https://docs.qonto.com/

**Base URL:** `https://thirdparty.qonto.com/v2`

---

## Autenticación

### Método: API Key (Implementado en el proyecto)

La autenticación se realiza mediante un header `Authorization` que combina el `organization_slug` y la `api_key`:

```
Authorization: {organization_slug}:{api_key}
```

**Headers requeridos:**
```http
Authorization: org-slug:your-api-key
Content-Type: application/json
Accept: application/json
```

### Método: OAuth 2.0

Para acceso delegado (aplicaciones de terceros):

1. **Obtener código de autorización:**
   ```
   GET /oauth2/auth
   ```

2. **Intercambiar por tokens:**
   ```
   POST /oauth2/token
   ```

**Tokens:**
- Access Token: válido 1 hora
- Refresh Token: válido 90 días

### Método: QSeal Certificate (PSD2)

Para instituciones financieras y TPPs (Third Party Providers).

---

## Configuración de Credenciales

### Variables de Entorno

```env
QONTO_API_KEY=your_qonto_api_key_here
QONTO_ORGANIZATION_SLUG=your_organization_slug
QONTO_IBAN=your_iban_here
QONTO_API_BASE_URL=https://thirdparty.qonto.com/v2
```

### Obtener Credenciales

1. Acceder a la cuenta Qonto
2. Ir a **Configuración → Integraciones → API**
3. Generar una nueva API key
4. Copiar el organization slug (visible en la URL de tu cuenta)

---

## Endpoints de la API

### Organización

#### GET /organization
Obtiene detalles de la organización y sus cuentas bancarias.

**Response:**
```json
{
  "organization": {
    "slug": "org-slug",
    "legal_name": "Company Name",
    "bank_accounts": [
      {
        "slug": "account-slug",
        "iban": "FR7616798000010000012345678",
        "bic": "TRZOFR21XXX",
        "name": "Main Account",
        "currency": "EUR",
        "balance_cents": 1000000,
        "authorized_balance_cents": 950000
      }
    ]
  }
}
```

---

### Cuentas Bancarias

#### GET /v2/bank_accounts
Lista todas las cuentas bancarias de la organización.

#### POST /v2/bank_accounts
Crea una nueva cuenta bancaria.

#### GET /v2/bank_accounts/{id}
Obtiene detalles de una cuenta específica.

#### PATCH /v2/bank_accounts/{id}
Actualiza el nombre de una cuenta.

#### POST /v2/bank_accounts/{id}/close
Cierra una cuenta bancaria.

**Campos de respuesta de cuenta:**
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `slug` | string | Identificador único de la cuenta |
| `iban` | string | IBAN de la cuenta |
| `bic` | string | Código BIC/SWIFT |
| `name` | string | Nombre de la cuenta |
| `currency` | string | Código de moneda (EUR, etc.) |
| `balance_cents` | integer | Balance actual en centavos |
| `authorized_balance_cents` | integer | Balance autorizado en centavos |

---

### Transacciones

#### GET /v2/transactions
Obtiene lista de transacciones con filtros y paginación.

**Parámetros de Query:**

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `iban` | string | Sí* | IBAN de la cuenta |
| `bank_account_id` | string | Sí* | ID de la cuenta (alternativa a IBAN) |
| `status[]` | array | No | Filtrar por estado: `pending`, `completed`, `declined`, `reversed` |
| `side` | string | No | Filtrar por tipo: `credit` (ingreso) o `debit` (gasto) |
| `updated_at_from` | datetime | No | Fecha mínima de actualización (ISO 8601) |
| `updated_at_to` | datetime | No | Fecha máxima de actualización (ISO 8601) |
| `settled_at_from` | date | No | Fecha mínima de liquidación |
| `settled_at_to` | date | No | Fecha máxima de liquidación |
| `current_page` | integer | No | Número de página (default: 1) |
| `per_page` | integer | No | Items por página (max: 100) |

*Se requiere `iban` o `bank_account_id`

**Response:**
```json
{
  "transactions": [
    {
      "id": "transaction-uuid",
      "amount_cents": 15000,
      "currency": "EUR",
      "local_amount_cents": 15000,
      "local_currency": "EUR",
      "side": "debit",
      "status": "completed",
      "operation_type": "transfer",
      "emitted_at": "2024-01-15T10:30:00.000Z",
      "settled_at": "2024-01-15T14:00:00.000Z",
      "label": "Proveedor XYZ",
      "reference": "INV-2024-001",
      "note": "Pago factura enero",
      "vat_amount_cents": 2500,
      "vat_rate": 21.0,
      "attachment_ids": ["attach-uuid-1"],
      "label_ids": ["label-uuid-1"]
    }
  ],
  "meta": {
    "current_page": 1,
    "next_page": 2,
    "prev_page": null,
    "total_pages": 5,
    "total_count": 450,
    "per_page": 100
  }
}
```

#### GET /v2/transactions/{id}
Obtiene detalle de una transacción específica.

**Response:**
```json
{
  "transaction": {
    "id": "transaction-uuid",
    "amount_cents": 15000,
    "currency": "EUR",
    "side": "debit",
    "status": "completed",
    "operation_type": "transfer",
    "emitted_at": "2024-01-15T10:30:00.000Z",
    "settled_at": "2024-01-15T14:00:00.000Z",
    "label": "Proveedor XYZ",
    "reference": "INV-2024-001",
    "note": "Pago factura enero",
    "initiator": {
      "id": "member-uuid",
      "first_name": "Juan",
      "last_name": "García"
    }
  }
}
```

---

### Estructura de Datos de Transacción

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | string | UUID único de la transacción |
| `amount_cents` | integer | Monto en centavos |
| `currency` | string | Código de moneda (EUR, USD, etc.) |
| `local_amount_cents` | integer | Monto en moneda local (si difiere) |
| `local_currency` | string | Código de moneda local |
| `side` | string | `credit` (ingreso) o `debit` (gasto) |
| `status` | string | Estado: `pending`, `completed`, `declined`, `reversed` |
| `operation_type` | string | Tipo de operación (ver tabla abajo) |
| `emitted_at` | datetime | Fecha/hora de emisión (ISO 8601 con Z) |
| `settled_at` | datetime | Fecha/hora de liquidación |
| `label` | string | Nombre del tercero/contraparte |
| `reference` | string | Referencia de la transacción |
| `note` | string | Notas adicionales |
| `vat_amount_cents` | integer | Monto de IVA en centavos |
| `vat_rate` | decimal | Tasa de IVA (ej: 21.0) |
| `attachment_ids` | array | IDs de archivos adjuntos |
| `label_ids` | array | IDs de etiquetas/categorías |

### Tipos de Operación (`operation_type`)

| Valor | Descripción |
|-------|-------------|
| `transfer` | Transferencia SEPA |
| `card` | Pago con tarjeta |
| `direct_debit` | Domiciliación bancaria |
| `income` | Ingreso recibido |
| `qonto_fee` | Comisión de Qonto |
| `check` | Cheque |
| `swift_income` | Ingreso SWIFT internacional |
| `swift_outcome` | Pago SWIFT internacional |

### Estados de Transacción (`status`)

| Estado | Descripción |
|--------|-------------|
| `pending` | En proceso, no liquidada |
| `completed` | Liquidada exitosamente |
| `declined` | Rechazada |
| `reversed` | Revertida/cancelada |

---

### Labels (Etiquetas/Categorías)

#### GET /v2/labels
Obtiene todas las etiquetas de categorización de Qonto.

**Response:**
```json
{
  "labels": [
    {
      "id": "label-uuid",
      "name": "Marketing",
      "parent_id": null
    },
    {
      "id": "label-uuid-2",
      "name": "Google Ads",
      "parent_id": "label-uuid"
    }
  ]
}
```

#### GET /v2/labels/{id}
Obtiene una etiqueta específica.

---

### Memberships (Miembros del Equipo)

#### GET /v2/memberships
Lista todos los miembros del equipo.

**Response:**
```json
{
  "memberships": [
    {
      "id": "member-uuid",
      "first_name": "Juan",
      "last_name": "García",
      "email": "juan@empresa.com",
      "role": "admin"
    }
  ]
}
```

#### GET /v2/membership
Obtiene la membresía del usuario autenticado.

#### POST /v2/memberships/invite_employee_or_accountant
Invita a un nuevo miembro.

---

### Attachments (Adjuntos)

#### POST /v2/attachments
Sube un archivo (JPEG, PNG, PDF).

#### GET /v2/attachments/{id}
Descarga un adjunto. **Nota:** Las URLs son válidas por 30 minutos.

#### GET /v2/transactions/{id}/attachments
Lista adjuntos de una transacción.

#### POST /v2/transactions/{id}/attachments
Sube un adjunto a una transacción.

#### DELETE /v2/transactions/{id}/attachments
Elimina todos los adjuntos de una transacción.

#### DELETE /v2/transactions/{transaction_id}/attachments/{attachment_id}
Elimina un adjunto específico.

---

### Transferencias SEPA

#### Beneficiarios

```
GET    /v2/sepa/beneficiaries           # Listar beneficiarios
POST   /v2/sepa/beneficiaries           # Agregar beneficiario
PATCH  /v2/sepa/beneficiaries/{id}      # Actualizar
PATCH  /v2/sepa/beneficiaries/trust     # Marcar como confiables
PATCH  /v2/sepa/beneficiaries/untrust   # Revocar confianza
```

#### Verificación

```
POST /v2/sepa/verify_payee              # Verificar IBAN y nombre
POST /v2/sepa/bulk_verify_payee         # Verificar múltiples
```

#### Transferencias

```
GET  /v2/sepa/transfers                 # Listar transferencias
POST /v2/sepa/transfers                 # Crear transferencia
POST /v2/sepa/transfers/{id}/cancel     # Cancelar
POST /v2/sepa/transfers/{id}/download_proof  # Descargar comprobante
```

#### Transferencias Recurrentes

```
GET  /v2/sepa/recurring_transfers           # Listar
POST /v2/sepa/recurring_transfers           # Crear
POST /v2/sepa/recurring_transfers/{id}/cancel  # Cancelar
```

#### Transferencias en Lote

```
POST /v2/sepa/bulk_transfers            # Crear hasta 400 transferencias
GET  /v2/sepa/bulk_transfers/{id}       # Obtener estado
```

---

### Webhooks

#### Suscripciones

```
POST   /v2/webhook_subscriptions        # Suscribirse a eventos
GET    /v2/webhook_subscriptions        # Listar suscripciones
DELETE /v2/webhook_subscriptions/{id}   # Desuscribirse
```

#### Eventos Disponibles

| Recurso | Eventos |
|---------|---------|
| Transacciones | `created`, `updated` |
| Cuentas | `created`, `updated` |
| Miembros | `created`, `updated` |
| Tarjetas | Múltiples eventos |
| Beneficiarios | `created`, `updated`, `deleted` |
| Facturas | `created`, `updated` |

---

## Paginación

Todas las listas soportan paginación estándar:

**Parámetros:**
- `current_page`: Número de página (1-indexed)
- `per_page`: Items por página (máximo 100)

**Respuesta Meta:**
```json
{
  "meta": {
    "current_page": 1,
    "next_page": 2,
    "prev_page": null,
    "total_pages": 5,
    "total_count": 450,
    "per_page": 100
  }
}
```

---

## Rate Limiting

- Las solicitudes están limitadas por frecuencia
- Al recibir código `429 Too Many Requests`, esperar antes de reintentar
- Recomendación: Implementar backoff exponencial (2^attempt segundos)

---

## Manejo de Errores

### Códigos HTTP

| Código | Significado | Acción |
|--------|-------------|--------|
| `200` | Éxito | Procesar respuesta |
| `401` | No autenticado | Verificar API key y organization slug |
| `403` | Acceso denegado | Verificar permisos |
| `404` | No encontrado | Recurso no existe |
| `429` | Rate limited | Esperar y reintentar con backoff |
| `500` | Error del servidor | Reintentar |

### Ejemplo de Error

```json
{
  "errors": [
    {
      "code": "invalid_request",
      "message": "The IBAN parameter is required"
    }
  ]
}
```

---

## Implementación en el Proyecto

### Cliente Qonto

**Ubicación:** `app/integrations/qonto_client.py`

```python
from app.integrations.qonto_client import QontoClient, get_qonto_client

# Usar singleton
client = get_qonto_client()

# O crear instancia personalizada
client = QontoClient(
    api_key="your-api-key",
    organization_slug="your-org-slug",
    iban="your-iban"
)
```

### Métodos Disponibles

```python
# Organización
await client.get_organization()

# Cuentas
await client.get_bank_accounts()
await client.get_bank_account_by_iban(iban)

# Transacciones
await client.get_transactions(
    iban=None,
    status=["completed"],
    settled_at_from=date(2024, 1, 1),
    settled_at_to=date(2024, 12, 31),
    side="credit",  # o "debit"
    page=1,
    per_page=100
)

await client.get_all_transactions(...)  # Con paginación automática
await client.get_transaction(transaction_id)

# Labels y Memberships
await client.get_labels()
await client.get_memberships()

# Adjuntos
await client.get_attachments(transaction_id)
```

### Parseo de Transacciones

```python
raw_transaction = {...}  # Respuesta de API
parsed = QontoClient.parse_transaction(raw_transaction)

# Resultado:
{
    "qonto_id": "uuid",
    "amount": Decimal("150.00"),
    "amount_cents": 15000,
    "currency": "EUR",
    "side": "debit",
    "status": "completed",
    "operation_type": "transfer",
    "emitted_at": datetime(...),
    "settled_at": datetime(...),
    "label": "Proveedor XYZ",
    "counterparty_name": "Proveedor XYZ",
    "vat_amount": Decimal("25.00"),
    "vat_rate": Decimal("21"),
    ...
}
```

### Conversión de Montos

```python
# De centavos a decimal
amount = QontoClient.parse_amount(15000, "EUR")  # Decimal("150.00")
```

---

## Sincronización de Datos

### Endpoints del Proyecto

```
POST /api/v1/sync/init           # Inicializar categorías
POST /api/v1/sync/all            # Sincronizar todo
POST /api/v1/sync/accounts       # Sincronizar cuentas
POST /api/v1/sync/transactions   # Sincronizar transacciones
```

### Servicio de Sincronización

**Ubicación:** `app/services/sync_service.py`

```python
from app.services.sync_service import SyncService

sync = SyncService(db_session)

# Sincronizar cuentas
accounts = await sync.sync_accounts()

# Sincronizar transacciones
result = await sync.sync_transactions(
    iban=None,
    from_date=date(2024, 1, 1),
    to_date=date(2024, 12, 31),
    full_sync=False
)
# result = {"total_fetched": 100, "created": 50, "updated": 30, "skipped": 20, "errors": 0}
```

---

## Modelo de Datos Local

### QontoAccount

```python
class QontoAccount(Base):
    __tablename__ = "qonto_accounts"

    id: int                          # PK
    qonto_id: str                    # slug de Qonto (unique)
    slug: str                        # identificador
    iban: str                        # IBAN (unique)
    bic: Optional[str]               # BIC
    name: str                        # Nombre
    currency: str                    # EUR
    balance: Decimal                 # Balance actual
    authorized_balance: Decimal      # Balance autorizado
    is_active: bool
    is_main: bool
    last_synced_at: datetime
```

### Transaction

```python
class Transaction(Base):
    __tablename__ = "transactions"

    id: int                          # PK
    qonto_id: str                    # ID de Qonto (unique)
    account_id: int                  # FK a qonto_accounts
    amount: Decimal
    amount_cents: int
    currency: str
    side: TransactionSide            # CREDIT/DEBIT
    status: TransactionStatus        # PENDING/COMPLETED/DECLINED/REVERSED
    operation_type: TransactionType  # TRANSFER/CARD/etc.
    emitted_at: datetime
    settled_at: datetime
    label: str                       # Nombre contraparte
    reference: str
    note: str
    counterparty_name: str
    counterparty_iban: str
    vat_amount: Decimal
    vat_rate: Decimal
    category_id: int                 # FK a categories
    project_id: int                  # FK a projects
    is_reconciled: bool
    review_status: ReviewStatus      # PENDING/CONFIRMED
```

---

## Límites y Mejores Prácticas

### Límites de Transferencias

| Tipo de Beneficiario | Límite Instant | Límite 24h |
|---------------------|----------------|------------|
| No confiable | >5.000€ | >20.000€/24h |
| Confiable | >10.000€ | >50.000€/24h |

- Transferencias >30.000€ requieren adjunto
- SCA obligatorio para beneficiarios no confiables

### Mejores Prácticas

1. **Rate Limiting:** Implementar delays entre requests (0.1s recomendado)
2. **Paginación:** Usar `per_page=100` para máxima eficiencia
3. **Filtros:** Usar `settled_at_from/to` para limitar datos
4. **Reintentos:** Implementar backoff exponencial
5. **Caché:** Cachear datos que no cambian frecuentemente

---

## Recursos Adicionales

- **Documentación Oficial:** https://docs.qonto.com/
- **API Reference:** https://docs.qonto.com/docs/business-api
- **Sandbox:** Disponible para testing
- **Soporte:** support@qonto.com

---

## Changelog del Proyecto

| Fecha | Versión | Cambios |
|-------|---------|---------|
| 2024 | 1.0 | Implementación inicial del cliente Qonto |
| 2024 | 1.1 | Agregado soporte para labels y memberships |
| 2024 | 1.2 | Paginación automática en get_all_transactions |

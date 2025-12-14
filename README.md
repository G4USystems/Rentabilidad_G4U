# Rentabilidad G4U - Sistema de Reportes P&L con Qonto

Sistema de integración con la API de Qonto para generación de reportes de Pérdidas y Ganancias (P&L) con KPIs de rentabilidad global y por proyectos.

## Características

- 🏦 **Integración con Qonto API**: Sincronización automática de transacciones
- 📊 **Reportes P&L**: Estados de resultados configurables por período
- 📈 **KPIs de Rentabilidad**: Métricas globales y por proyecto
- 🏷️ **Categorización**: Sistema flexible de categorías de ingresos/gastos
- 📁 **Gestión de Proyectos**: Asignación de transacciones a proyectos
- 📄 **Exportación**: PDF, Excel, CSV y JSON

## Estructura del Proyecto

```
Rentabilidad_G4U/
├── app/
│   ├── api/              # Endpoints REST
│   ├── core/             # Configuración central
│   ├── models/           # Modelos de datos
│   ├── schemas/          # Esquemas Pydantic
│   ├── services/         # Lógica de negocio
│   ├── integrations/     # Integraciones externas (Qonto)
│   └── reports/          # Generación de reportes
├── alembic/              # Migraciones de BD
├── tests/                # Tests unitarios e integración
└── docs/                 # Documentación
```

## Instalación

1. Clonar el repositorio:
```bash
git clone <repository-url>
cd Rentabilidad_G4U
```

2. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus credenciales de Qonto
```

5. Ejecutar migraciones:
```bash
alembic upgrade head
```

6. Iniciar el servidor:
```bash
uvicorn app.main:app --reload
```

## Configuración de Qonto

1. Obtén tu API Key desde el portal de Qonto
2. Configura las siguientes variables en `.env`:
   - `QONTO_API_KEY`: Tu clave de API
   - `QONTO_ORGANIZATION_SLUG`: Slug de tu organización
   - `QONTO_IBAN`: IBAN de la cuenta a monitorear

## API Endpoints

### Transacciones
- `GET /api/v1/transactions` - Listar transacciones
- `GET /api/v1/transactions/{id}` - Detalle de transacción
- `POST /api/v1/transactions/sync` - Sincronizar con Qonto

### Reportes P&L
- `GET /api/v1/reports/pl` - Generar reporte P&L
- `GET /api/v1/reports/pl/summary` - Resumen de P&L
- `POST /api/v1/reports/pl/export` - Exportar reporte

### KPIs
- `GET /api/v1/kpis/global` - KPIs globales
- `GET /api/v1/kpis/projects` - KPIs por proyecto
- `GET /api/v1/kpis/trends` - Tendencias temporales

### Proyectos
- `GET /api/v1/projects` - Listar proyectos
- `POST /api/v1/projects` - Crear proyecto
- `PUT /api/v1/projects/{id}` - Actualizar proyecto

### Categorías
- `GET /api/v1/categories` - Listar categorías
- `POST /api/v1/categories` - Crear categoría

## Documentación API

Una vez iniciado el servidor, accede a:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## KPIs Disponibles

### Globales
- **Margen Bruto**: (Ingresos - Costos Directos) / Ingresos
- **Margen Neto**: Beneficio Neto / Ingresos
- **EBITDA**: Beneficio antes de intereses, impuestos, depreciación y amortización
- **Ratio de Gastos Operativos**: Gastos Operativos / Ingresos
- **Burn Rate**: Tasa de consumo de efectivo mensual

### Por Proyecto
- **ROI del Proyecto**: (Ingresos - Costos) / Costos
- **Margen de Contribución**: Ingresos - Costos Variables
- **Punto de Equilibrio**: Costos Fijos / Margen de Contribución Unitario

## Licencia

MIT License - G4U Systems

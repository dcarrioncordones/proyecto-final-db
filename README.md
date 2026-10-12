# Análisis exploratorio y visualización de datos con SQL y NoSQL

Trabajo final de **MCD512 · Big Data** (Maestría en Ciencia de Datos, INTEC). Prof. José M. Aquino Cepeda, MSc.
Autor: Dan Carrión, matrícula 1131022.

Se construyen **30 visualizaciones** (diez por gestor) a partir de tres bases de datos que corren en Docker:

| Gestor | Base de datos | Conexión |
|---|---|---|
| SQL Server 2022 | Northwind | ODBC (Microsoft ODBC Driver 18) |
| Oracle Database Free | Esquema HR | ODBC (Oracle Instant Client) |
| MongoDB 8.0 | `bigdata_final.sensores_datos` (simulación propia) | PyMongo |

## Entregables

- **Informe:** [`informe/salida/Trabajo_final_Big_Data_Dan_Carrion.pdf`](informe/salida/Trabajo_final_Big_Data_Dan_Carrion.pdf) (también en `.docx`).
- **Dashboard interactivo:** [`dashboard/index.html`](dashboard/index.html). Se abre con doble clic; no necesita Internet, servidor ni las bases encendidas.
- **Notebook:** [`Trabajo_final_Big_Data.ipynb`](Trabajo_final_Big_Data.ipynb).
- **Consultas:** [`sql/northwind.sql`](sql/northwind.sql), [`sql/hr.sql`](sql/hr.sql) y [`mongo/consultas.js`](mongo/consultas.js).

## Cómo reproducirlo

Con Docker Desktop (en Apple Silicon, con Rosetta activado), todo se hace con `docker/lab.py`: crear los contenedores, cargar los datos, verificar las conexiones y extraer los datos para regenerar figuras y dashboard. La guía paso a paso está en **[COMO_CORRER.md](COMO_CORRER.md)**.

```bash
python3 docker/lab.py configurar
python3 docker/lab.py iniciar
python3 docker/lab.py cargar sqlserver   # también oracle y mongodb
python3 docker/lab.py construir-cliente
python3 docker/lab.py verificar
python3 docker/lab.py integrar
```

Sin Docker, el análisis se puede recalcular sobre los CSV ya extraídos (requiere Python 3.11 o superior):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py --usar-exportados
```

## Estructura

| Carpeta | Contenido |
|---|---|
| `docker/` | Compose de los tres gestores, cliente con drivers ODBC y `lab.py` |
| `src/` | Conexiones y extracción, análisis, validaciones y dashboard |
| `sql/`, `mongo/` | Consultas por visualización y preparación de la colección |
| `data/original/` | Scripts oficiales de Northwind y HR |
| `data/procesados/` | Datos extraídos de las tres bases y su procedencia (hashes) |
| `figuras/` | Las 30 figuras en PNG |
| `dashboard/` | Dashboard HTML y datos de las figuras interactivas |
| `evidencias/` | Registro de conexiones verificadas y de las 17 comprobaciones |
| `informe/` | Informe final, su generador y las capturas que usa |
| `config/` | Plantillas de conexión sin credenciales |

## Notas

- Las contraseñas se generan localmente en `docker/.env` y no se incluyen en el repositorio.
- Las lecturas de sensores son una simulación reproducible (semilla 5122026), no mediciones reales.
- El dashboard muestra una copia de los datos extraídos; el monitoreo de S10 es una reproducción histórica, no *streaming*.

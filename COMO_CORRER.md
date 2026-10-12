# Cómo correr el proyecto con Docker

Guía para un Mac con Apple Silicon. Al terminar tendrás SQL Server (Northwind), Oracle (HR) y MongoDB (sensores) en contenedores, las conexiones verificadas, los datos extraídos desde esas bases y el dashboard, el PDF y el notebook regenerados.

**Cómo leer esta guía**

- Cada paso tiene un bloque **Ejecuta**: son los únicos comandos que tienes que correr, en ese orden, uno por uno.
- Debajo aparece lo que **deberías ver**. Si ves eso, pasa al siguiente paso.
- Donde veas **📸 Captura**, toma una captura de la Terminal con **Cmd + Shift + 4** (arrastra para seleccionar el área) y guárdala en `evidencias/` con el nombre indicado. En la sección 10 se agregan al informe. Ninguna muestra contraseñas.
- Si algo falla, ve a la sección 12 (Problemas frecuentes). No necesitas ningún comando `docker` directamente; todo se hace con `python3 docker/lab.py`.
- Todos los comandos se ejecutan **desde la carpeta del proyecto** (`proyecto-final-db`), no desde `docker/`.

## Qué se va a crear

| Gestor | Contenedor | Datos | Puerto en tu Mac |
|---|---|---|---|
| SQL Server 2022 | `bigdata-sqlserver` | Base `Northwind` | `127.0.0.1:1434` |
| Oracle Free (ARM64) | `bigdata-oracle` | Esquema `HR`, servicio `FREEPDB1` | `127.0.0.1:1522` |
| MongoDB 8.0 | `bigdata-mongodb` | Base `bigdata_final`, colección `sensores_datos` | `127.0.0.1:27020` |

Los puertos no chocan con tus otros contenedores (1433, 27017–27019). Los datos se guardan en volúmenes propios del proyecto `bigdata-final`.

Además hay un **cliente de análisis** (`analisis`): un contenedor temporal con Python, los drivers ODBC de SQL Server y Oracle, y PyMongo. Se crea, ejecuta su tarea y se elimina; los archivos que genera quedan en tu carpeta. Así no tienes que instalar drivers ODBC en macOS.

## 1. Preparar Docker Desktop

1. Abre Docker Desktop y espera a que indique que el motor está funcionando.
2. En **Settings → General → Virtual Machine Options**, deja seleccionado **Apple Virtualization framework** y marca **Use Rosetta for x86_64/amd64 emulation on Apple Silicon**. Pulsa **Apply & restart** si cambiaste algo.

Rosetta es necesario porque SQL Server y el cliente de análisis sólo existen para `amd64` y se emulan en tu Mac. No uses Docker VMM: con él la emulación no usa Rosetta y SQL Server suele fallar.

La primera vez se descargan varias imágenes (varios GB). Si Docker se queda sin memoria, detén tus otros contenedores desde Docker Desktop; sus datos se conservan.

**Ejecuta:**

```bash
cd "/Users/dancarrion/proyecto-final-db"
python3 --version
```

**Deberías ver:** Python 3.11 o superior.

## 2. Contraseñas

**Ejecuta:**

```bash
python3 docker/lab.py configurar
python3 docker/lab.py validar
```

**Deberías ver:**

- `configurar`: `Creado docker/.env con cuatro contraseñas distintas.` o, si ya existía, `docker/.env ya existe y es válido; se conserva.` Ambos son correctos.
- `validar`: `Compose y configuración válidos.`

`docker/.env` guarda las contraseñas de SQL Server, Oracle (administrador y usuario HR) y MongoDB. No se imprimen en pantalla, no se incluyen en el ZIP ni en Git y no deben aparecer en capturas. No las cambies después de crear las bases: editar el archivo no cambia la contraseña guardada dentro de cada gestor.

Al usar estas imágenes aceptas los términos de [SQL Server Developer y su driver ODBC](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server), [Oracle Database Free](https://container-registry.oracle.com/ords/ocr/ba/database/free) y [Oracle Instant Client](https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html).

## 3. SQL Server y Northwind

**Ejecuta:**

```bash
python3 docker/lab.py iniciar sqlserver
python3 docker/lab.py cargar sqlserver
```

`iniciar` crea el contenedor y espera (hasta 15 minutos) a que SQL Server responda. `cargar` crea la base `Northwind` y ejecuta el script oficial `data/original/instnwnd.sql`.

**Deberías ver:** `Northwind cargada: 830 pedidos y 2155 líneas.`

> 📸 **Captura:** la salida de `cargar sqlserver`. Guárdala como `evidencias/carga_sqlserver.png`.

Si ya estaba cargada, verás `Northwind ya contiene las siete tablas con los conteos esperados; se conserva.` El cargador nunca borra una base existente: si encuentra datos distintos, se detiene y te avisa.

## 4. Oracle y el esquema HR

**Ejecuta:**

```bash
python3 docker/lab.py iniciar oracle
python3 docker/lab.py cargar oracle
```

El primer arranque de Oracle es el más lento (puede tardar 5–10 minutos); `iniciar` espera solo. `cargar` crea el usuario HR y ejecuta los scripts oficiales `hr_create.sql`, `hr_populate.sql` y `hr_code.sql`.

**Deberías ver:** `HR cargado: 107 empleados y 10 filas de job_history.`

> 📸 **Captura:** la salida de `cargar oracle`. Guárdala como `evidencias/carga_oracle.png`.

Si ya estaba cargado, verás `HR ya contiene las siete tablas con los conteos esperados; se conserva.` El cargador nunca elimina el esquema HR.

## 5. MongoDB y los sensores

**Ejecuta:**

```bash
python3 docker/lab.py iniciar mongodb
python3 docker/lab.py cargar mongodb
```

`cargar` importa `data/procesados/sensores.jsonl` en `bigdata_final.sensores_datos`: 12,960 lecturas sintéticas (3 ciudades, 6 estaciones, 18 sensores, 30 días de septiembre de 2026). Las fechas se guardan como tipo fecha de MongoDB y un índice único evita duplicados, así que repetir el paso es seguro.

**Deberías ver:** el conteo `documents: 12960` y `Importación por clave completada`.

> 📸 **Captura:** la salida de `cargar mongodb`. Guárdala como `evidencias/carga_mongodb.png`.

Los datos siguen siendo simulados aunque estén en MongoDB; el informe lo indica.

## 6. Comprobar los tres gestores

**Ejecuta:**

```bash
python3 docker/lab.py estado
```

**Deberías ver:** `bigdata-sqlserver`, `bigdata-oracle` y `bigdata-mongodb` con estado `Up` y `(healthy)`.

> 📸 **Captura:** los tres contenedores `healthy`. Guárdala como `evidencias/lab_estado.png`.

## 7. Construir el cliente de análisis

**Ejecuta:**

```bash
python3 docker/lab.py construir-cliente
python3 docker/lab.py drivers
```

La primera construcción tarda varios minutos: instala Python, las librerías del proyecto, el driver ODBC 18 de Microsoft y Oracle Instant Client con ODBC (verificado con el hash publicado por Oracle).

**Deberías ver:** una lista de drivers que incluye `ODBC Driver 18 for SQL Server` y `Oracle Instant Client ODBC`.

> 📸 **Captura:** la lista de drivers ODBC. Guárdala como `evidencias/lab_drivers.png`.

## 8. Verificar las conexiones

Estas son las **capturas obligatorias** del trabajo ("capturas de conexión exitosa"). Ejecuta cada gestor por separado para tener una captura por gestor.

**Ejecuta:**

```bash
python3 docker/lab.py verificar sqlserver
```

> 📸 **Captura (obligatoria):** el comando y su resultado. Guárdala como `evidencias/conexion_sqlserver.png`.

```bash
python3 docker/lab.py verificar oracle
```

> 📸 **Captura (obligatoria):** guárdala como `evidencias/conexion_oracle.png`.

```bash
python3 docker/lab.py verificar mongodb
```

> 📸 **Captura (obligatoria):** guárdala como `evidencias/conexion_mongodb.png`.

Cada verificación se conecta al gestor y hace una consulta real:

| Gestor | Conector | Consulta |
|---|---|---|
| SQL Server | `pyodbc` + ODBC Driver 18 | `DB_NAME()` y `COUNT(*)` de `dbo.Orders` |
| Oracle | `pyodbc` + Oracle Instant Client ODBC | Esquema actual y `COUNT(*)` de `employees` |
| MongoDB | `pymongo` | `ping` y conteo de `sensores_datos` |

**Deberías ver:** `CONEXIÓN VERIFICADA` con sus conteos en cada caso. Los resultados se acumulan en `evidencias/conexiones.json` y `evidencias/conexiones.txt` (con fecha, sin contraseñas).

## 9. Extraer los datos y regenerar todo

**Ejecuta:**

```bash
python3 docker/lab.py integrar
```

Este comando:

1. Respalda `data/procesados`, `docs` y `evidencias` en `../respaldos_bigdata_final/<fecha>/`.
2. Vuelve a verificar las tres conexiones; si alguna falla, se detiene sin tocar nada.
3. Exporta Northwind y HR por ODBC y los sensores por PyMongo a `data/procesados/`.
4. Registra fecha y hashes de lo extraído en `data/procesados/proveniencia_fuentes.json`.
5. Recalcula las 30 figuras, ejecuta las 17 comprobaciones y regenera el dashboard.

**Deberías ver:** el respaldo, las tres extracciones y, al final, `17/17 comprobaciones correctas` y `Terminado`.

> 📸 **Captura:** la parte final de la salida, donde se ven las extracciones y `17/17 comprobaciones correctas`. Guárdala como `evidencias/lab_integrar.png`.

| Resultado | Dónde queda |
|---|---|
| Datos de SQL Server, Oracle y MongoDB | `data/procesados/nw_*.csv`, `hr_*.csv`, `sensores.csv` |
| Figuras | `figuras/` |
| Dashboard | `dashboard/index.html` |
| Comprobaciones | `evidencias/validacion.json` |

**Importante:** a partir de aquí no ejecutes `python run.py` sin opciones, porque reemplaza los datos extraídos por las muestras. Para regenerar, usa `python3 docker/lab.py integrar` otra vez.

### Abrir el dashboard

El dashboard no necesita servidor, Docker ni las bases encendidas: es un archivo HTML con los datos ya calculados.

**Opción A (la más simple):** en Finder, entra a la carpeta `dashboard` del proyecto y haz doble clic en `index.html`. Se abre en tu navegador.

**Opción B (desde la Terminal):**

```bash
open dashboard/index.html
```

**Si se ve en blanco** (algunos navegadores limitan archivos locales), sírvelo localmente:

```bash
python3 -m http.server 8766 --bind 127.0.0.1 --directory dashboard
```

Abre <http://127.0.0.1:8766> en el navegador. Para detenerlo, vuelve a la Terminal y pulsa Ctrl+C.

**Cómo usarlo:** elige una base (Northwind, HR o Sensores) y uno de sus diez gráficos. N01 tiene filtro por país, H01 por departamento, y S06 y S10 por sensor. En S10 usa Reproducir/Pausar/Reiniciar para el monitoreo simulado.

**Deberías ver:** un aviso arriba que indica que los datos vienen de SQL Server, Oracle y MongoDB. Si dice que son muestras, no se ejecutó `integrar` correctamente.

> 📸 **Captura (opcional):** si quieres mostrar el dashboard en el informe, captura las vistas que necesites (sección 10).

## 10. Informe final

El informe está en `informe/salida/Trabajo_final_Big_Data_Dan_Carrion.pdf` (y su versión editable `.docx`). Usa las capturas recortadas de `informe/recursos/capturas/` y `informe/recursos/dashboard/`, las figuras de `figuras/` y los resultados de `docs/`.

Si cambias los datos o las capturas, puedes regenerarlo con `informe/construir_informe.js`. Requiere Node.js con la librería `docx` y Microsoft Word para exportar a PDF. Si sólo necesitas un cambio de texto, edita el `.docx` en Word y exporta el PDF.

## 11. Notebook y paquete de entrega

**11.1 Ejecuta el notebook con los datos extraídos.** La primera vez crea el entorno local (las dos primeras líneas); después basta con la tercera:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt jupyterlab ipykernel
.venv/bin/python -m jupyter lab
```

En Jupyter abre `Trabajo_final_Big_Data.ipynb`, usa **Run → Run All Cells** y guarda. El notebook detecta que los datos vienen de las bases y no los reemplaza. Cierra Jupyter con Ctrl+C en la Terminal.

**11.2 Genera el paquete.**

```bash
python3 src/empacar.py
```

**Deberías ver:** un resumen con las rutas de `entrega/Proyecto_final_Big_Data.zip` y `entrega/Trabajo_final_Big_Data_Dan_Carrion.pdf`. El ZIP excluye `.env`, entornos virtuales y cachés.

## 12. Problemas frecuentes

Para ver qué está pasando dentro de un gestor:

```bash
python3 docker/lab.py logs sqlserver
```

(Cambia `sqlserver` por `oracle` o `mongodb` según el caso. Muestra las últimas 80 líneas.)

| Problema | Qué hacer |
|---|---|
| `Cannot connect to the Docker daemon` | Abre Docker Desktop y espera a que el motor esté listo. |
| `port is already allocated` | Otro programa usa 1434, 1522 o 27020. Cambia sólo el número de la izquierda en `ports` de `docker/compose.yaml` (por ejemplo `127.0.0.1:1435:1433`). |
| SQL Server no llega a `healthy` o se reinicia | Revisa sus logs y que Rosetta esté activado (sección 1). |
| Oracle se queda en `starting` | Es normal hasta ~10 minutos la primera vez. En los logs debe aparecer `DATABASE IS READY TO USE!`. Si no, sube la memoria de Docker Desktop. |
| `exit code 137` | Falta de memoria. Detén otros contenedores o aumenta la memoria en Docker Desktop y repite el paso. |
| Oracle pide iniciar sesión o aceptar términos al descargar | Sigue las indicaciones de [container-registry.oracle.com](https://container-registry.oracle.com/ords/ocr/ba/database/free). No uses imágenes de otras fuentes. |
| Falla el checksum de Instant Client | La descarga se dañó o Oracle cambió el archivo. Repite `construir-cliente`; si persiste, compara con el hash publicado por Oracle antes de tocar el `Dockerfile`. |
| `drivers` no muestra los dos drivers | Repite `construir-cliente` y revisa el error de la construcción. |
| `Login failed` después de editar `docker/.env` | Las bases conservan la contraseña con la que se crearon. Restaura el `.env` original. |
| El cargador dice que hay contenido distinto | Existe una base o esquema con otros datos. El cargador no lo borra; revisa qué contiene antes de seguir. |
| El dashboard muestra datos anteriores | Repite `integrar` y recarga el navegador. |

## 13. Detener y retomar

Para detener los gestores sin perder datos:

```bash
python3 docker/lab.py detener
```

Para retomar otro día (no hace falta volver a cargar los datos):

```bash
python3 docker/lab.py iniciar
python3 docker/lab.py estado
```

No uses `docker compose down -v`: borra los volúmenes con las bases.

## Resumen de comandos

Una vez leída la guía, la secuencia completa es (uno por uno, avanzando sólo si el anterior terminó bien):

```bash
cd "/Users/dancarrion/proyecto-final-db"
python3 docker/lab.py configurar
python3 docker/lab.py validar
python3 docker/lab.py iniciar sqlserver
python3 docker/lab.py cargar sqlserver
python3 docker/lab.py iniciar oracle
python3 docker/lab.py cargar oracle
python3 docker/lab.py iniciar mongodb
python3 docker/lab.py cargar mongodb
python3 docker/lab.py estado
python3 docker/lab.py construir-cliente
python3 docker/lab.py drivers
python3 docker/lab.py verificar sqlserver
python3 docker/lab.py verificar oracle
python3 docker/lab.py verificar mongodb
python3 docker/lab.py integrar
```

Toma las 📸 capturas a medida que avanzas. Después: notebook (11.1) y `python3 src/empacar.py`.

## Referencia

**Conectarte desde DBeaver u otro cliente en tu Mac** (opcional; el proyecto no lo necesita):

| Gestor | Servidor | Base / servicio | Usuario | Contraseña (en `docker/.env`) |
|---|---|---|---|---|
| SQL Server | `127.0.0.1:1434` | `Northwind` | `sa` | `SQL_PASSWORD` |
| Oracle | `127.0.0.1:1522` | Servicio `FREEPDB1` (no SID) | `hr` | `HR_PASSWORD` |
| MongoDB | `127.0.0.1:27020` | `bigdata_final`, autenticación `admin` | `bigdata_admin` | `MONGO_PASSWORD` |

En SQL Server activa la opción de confiar en el certificado del servidor: el del laboratorio es autofirmado.

Dentro de Docker, el cliente usa los nombres de servicio (`sqlserver,1433`, `oracle:1521/FREEPDB1`, `mongodb:27017`) en vez de `localhost`, porque `localhost` dentro de un contenedor apunta al propio contenedor.

**Archivos del laboratorio:**

| Archivo | Para qué sirve |
|---|---|
| `docker/compose.yaml` | Define los tres gestores, sus puertos y volúmenes, y el cliente |
| `docker/.env.example` | Plantilla de variables (sin contraseñas reales) |
| `docker/lab.py` | Todos los comandos de esta guía |
| `docker/Dockerfile` | Imagen del cliente con drivers ODBC y librerías de Python |
| `docker/cliente.py` | Arma las conexiones dentro de Docker sin exponer contraseñas |
| `docker/mongo_verificar.js` | Validador, índices y conteo de la colección |
| `docker/test_laboratorio.py` | Pruebas locales de `lab.py`; no inicia Docker |
| `src/origen.py` | Registra y comprueba la procedencia de cada fuente |

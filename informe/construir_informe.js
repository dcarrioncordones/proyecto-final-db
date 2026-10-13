// Genera el informe final en Word con el estilo del informe multinodo (MCD512).
// Uso: node informe/construir_informe.js [paginas.json]
// La primera pasada usa números de página provisionales; la segunda recibe las páginas reales del PDF.
const fs = require('fs');
const path = require('path');
const d = require('docx');

const ROOT = path.resolve(__dirname, '..');
const R = (...p) => path.join(ROOT, ...p);
const PAGES = process.argv[2] && fs.existsSync(process.argv[2]) ? JSON.parse(fs.readFileSync(process.argv[2])) : {};

const NAVY = '1F3B5C', BLUE = '3A5F8A', GRAY = '333333', CAPTION = '555555', BORDER = 'BFC7D1', CODEBG = 'F3F4F6';
const MONO = 'Consolas', HEAD = 'Arial', BODY = 'Calibri';
const REPO = 'https://github.com/dcarrioncordones/proyecto-final-db';
const DASH = 'https://dcarrioncordones.github.io/proyecto-final-db/dashboard/';
const TEXT_W = 9360; // 6.5 in en DXA

const viz = JSON.parse(fs.readFileSync(R('docs/visualizaciones.json')));
const res = JSON.parse(fs.readFileSync(R('docs/resultados.json')));
const con = Object.fromEntries(JSON.parse(fs.readFileSync(R('evidencias/conexiones.json'))).map(c => [c.motor, c]));
const fmt = (n, dec = 2) => n.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });

// ---------- utilidades de formato ----------
function runs(text, base = {}) {
  // **negrita**, *cursiva* y `código` en línea.
  const out = [];
  for (const part of text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/)) {
    if (!part) continue;
    if (part.startsWith('**')) out.push(new d.TextRun({ ...base, text: part.slice(2, -2), bold: true }));
    else if (part.startsWith('`')) out.push(new d.TextRun({ ...base, text: part.slice(1, -1), font: MONO, size: 19 }));
    else if (part.startsWith('*')) out.push(new d.TextRun({ ...base, text: part.slice(1, -1), italics: true }));
    else out.push(new d.TextRun({ ...base, text: part }));
  }
  return out;
}
const P = (text, opts = {}) => new d.Paragraph({
  // Con código en línea se alinea a la izquierda para no estirar los espacios.
  children: runs(text), alignment: text.includes('`') ? d.AlignmentType.LEFT : d.AlignmentType.JUSTIFIED,
  spacing: { after: 120, line: 276 }, ...opts,
});
let bookmarkId = 0;
const headings = [];
function H1(text) {
  headings.push({ level: 1, text });
  return new d.Paragraph({
    heading: d.HeadingLevel.HEADING_1, pageBreakBefore: true, spacing: { after: 240 },
    children: [new d.Bookmark({ id: `h${++bookmarkId}`, children: [new d.TextRun(text)] })],
  });
}
const H2 = (text) => new d.Paragraph({ heading: d.HeadingLevel.HEADING_2, keepNext: true, spacing: { before: 280, after: 120 }, children: [new d.TextRun(text)] });
const H3 = (text, pageBreak = false) => new d.Paragraph({ heading: d.HeadingLevel.HEADING_3, keepNext: true, pageBreakBefore: pageBreak, spacing: { before: 180, after: 80 }, children: [new d.TextRun(text)] });
const bullets = (items, ref = 'bullets') => items.map(t => new d.Paragraph({
  numbering: { reference: ref, level: 0 }, spacing: { after: 60, line: 264 }, alignment: d.AlignmentType.JUSTIFIED, children: runs(t),
}));
const numbered = (items) => bullets(items, 'numbers');

function wrap(line, width = 94) {
  if (line.length <= width) return [line];
  const out = []; let rest = line;
  while (rest.length > width) {
    let cut = rest.lastIndexOf(' ', width);
    if (cut < width * 0.5) cut = Math.max(rest.lastIndexOf(',', width) + 1, width);
    out.push(rest.slice(0, cut)); rest = '    ' + rest.slice(cut).trimStart();
  }
  out.push(rest); return out;
}
function code(text) {
  const lines = text.replace(/\s+$/, '').split('\n').flatMap(l => wrap(l));
  return lines.map((l, i) => new d.Paragraph({
    keepNext: i < lines.length - 1, keepLines: true,
    border: { left: { style: d.BorderStyle.SINGLE, size: 12, color: BLUE, space: 6 } },
    shading: { type: d.ShadingType.CLEAR, fill: CODEBG, color: 'auto' },
    indent: { left: 180 },
    spacing: { before: i === 0 ? 80 : 0, after: i === lines.length - 1 ? 180 : 0, line: 240 },
    children: [new d.TextRun({ text: l || ' ', font: MONO, size: 17 })],
  }));
}
// Párrafo con un enlace externo entre dos textos.
const linkP = (before, url, after = '', opts = {}) => new d.Paragraph({
  alignment: d.AlignmentType.LEFT, spacing: { after: 120, line: 276 }, ...opts,
  children: [...runs(before), new d.ExternalHyperlink({ link: url, children: [new d.TextRun({ text: url, style: 'Hyperlink' })] }), ...runs(after)],
});
const label = (text) => new d.Paragraph({ keepNext: true, spacing: { before: 120, after: 40 }, children: runs(text) });

// Versión comprimida: IMG_DIR contiene copias optimizadas con la misma ruta relativa al proyecto.
const IMG_DIR = process.env.IMG_DIR;
// SIN_ANEXO_C=1 omite el Anexo C (capturas del dashboard) para reducir el tamaño del PDF.
const SIN_ANEXO_C = process.env.SIN_ANEXO_C === '1';
const imgPath = (file) => IMG_DIR && fs.existsSync(path.join(IMG_DIR, path.relative(ROOT, file))) ? path.join(IMG_DIR, path.relative(ROOT, file)) : file;
function pngSize(file) {
  const b = fs.readFileSync(file);
  if (b[0] === 0x89) return [b.readUInt32BE(16), b.readUInt32BE(20)];
  // JPEG: buscar marcador SOF
  let i = 2;
  while (i < b.length) {
    const m = b[i + 1], len = b.readUInt16BE(i + 2);
    if (m >= 0xc0 && m <= 0xc3) return [b.readUInt16BE(i + 7), b.readUInt16BE(i + 5)];
    i += 2 + len;
  }
  throw new Error('Tamaño de imagen desconocido: ' + file);
}
let figN = 0;
function figure(file, caption, widthIn = 6.2, maxHeightIn = 7.6) {
  file = imgPath(file);
  const [w, h] = pngSize(file);
  let wi = widthIn, hi = widthIn * h / w;
  if (hi > maxHeightIn) { hi = maxHeightIn; wi = hi * w / h; }
  figN += 1;
  return [
    new d.Paragraph({
      alignment: d.AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 80 },
      children: [new d.ImageRun({
        type: file.endsWith('.jpg') ? 'jpg' : 'png', data: fs.readFileSync(file),
        transformation: { width: Math.round(wi * 96), height: Math.round(hi * 96) },
        altText: { title: caption, description: caption, name: path.basename(file) },
      })],
    }),
    new d.Paragraph({
      alignment: d.AlignmentType.CENTER, spacing: { after: 220 },
      children: [
        new d.TextRun({ text: `Figura ${figN}. `, bold: true, italics: true, color: CAPTION, size: 19 }),
        ...runs(caption, { italics: true, color: CAPTION, size: 19 }),
      ],
    }),
  ];
}
const cellBorders = { top: { style: d.BorderStyle.SINGLE, size: 4, color: BORDER }, bottom: { style: d.BorderStyle.SINGLE, size: 4, color: BORDER }, left: { style: d.BorderStyle.SINGLE, size: 4, color: BORDER }, right: { style: d.BorderStyle.SINGLE, size: 4, color: BORDER } };
function table(headers, rows, ratios) {
  const total = ratios.reduce((a, b) => a + b, 0);
  const widths = ratios.map(r => Math.floor(TEXT_W * r / total));
  widths[widths.length - 1] += TEXT_W - widths.reduce((a, b) => a + b, 0);
  const cell = (text, i, head) => new d.TableCell({
    width: { size: widths[i], type: d.WidthType.DXA }, borders: cellBorders,
    shading: head ? { type: d.ShadingType.CLEAR, fill: BLUE, color: 'auto' } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new d.Paragraph({ children: runs(String(text), head ? { bold: true, color: 'FFFFFF', size: 19 } : { size: 19 }) })],
  });
  return [new d.Table({
    width: { size: TEXT_W, type: d.WidthType.DXA }, columnWidths: widths,
    rows: [
      new d.TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => cell(h, i, true)) }),
      ...rows.map(r => new d.TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false)) })),
    ],
  }), new d.Paragraph({ spacing: { after: 120 }, children: [] })];
}

// ---------- consultas por visualización ----------
function sqlBlocks(file) {
  const out = {}; let id = null;
  for (const line of fs.readFileSync(R(file), 'utf8').split('\n')) {
    const m = line.match(/^-- ([NH]\d\d):/);
    if (m) { id = m[1]; out[id] = [line]; continue; }
    if (id && line.trim() === '') { id = null; continue; }
    if (id) out[id].push(line);
  }
  return Object.fromEntries(Object.entries(out).map(([k, v]) => [k, v.join('\n')]));
}
const SQL = { ...sqlBlocks('sql/northwind.sql'), ...sqlBlocks('sql/hr.sql') };
const MONGO = {
  S01: `// S01: media diaria por ciudad, sólo temperatura.
c.aggregate([
  { $match: { type: 'temperatura' } },
  { $group: { _id: { date: { $dateTrunc: { date: '$timestamp', unit: 'day', timezone: tz } },
                     city: '$city' },
              mean: { $avg: '$value' }, n: { $sum: 1 } } },
  { $sort: { '_id.date': 1 } }
]);`,
  S02: `// S02: intensidad de lecturas por ubicación.
c.aggregate([
  { $group: { _id: { city: '$city', station: '$station', lat: '$latitude', lon: '$longitude' },
              n: { $sum: 1 } } }
]);`,
  S03: `// S03: observaciones separadas por tipo y unidad; nunca sumar magnitudes diferentes.
c.find({}, { _id: 0, type: 1, value: 1, unit: 1 });`,
  S04: `// S04: alineación por estación y timestamp; los tipos se pivotan en Python.
c.aggregate([
  { $group: { _id: { station: '$station', timestamp: '$timestamp' },
              readings: { $push: { type: '$type', value: '$value' } } } },
  { $sort: { '_id.timestamp': 1 } }
]);`,
  S05: `// S05: conteo de eventos diarios por ciudad.
c.aggregate([
  { $group: { _id: { date: { $dateTrunc: { date: '$timestamp', unit: 'day', timezone: tz } },
                     city: '$city' },
              n: { $sum: 1 } } },
  { $sort: { '_id.date': 1 } }
]);`,
  S06: `// S06: series para mediana/MAD por sensor y hora local (cálculo en Python).
c.aggregate([
  { $project: { _id: 0, sensor_id: 1, value: 1, timestamp: 1,
                hour: { $hour: { date: '$timestamp', timezone: tz } } } },
  { $sort: { sensor_id: 1, timestamp: 1 } }
]);`,
  S07: `// S07: datos para el calendario; las alertas se derivan en Python.
c.find({}, { _id: 0, timestamp: 1, sensor_id: 1, value: 1 });`,
  S08: `// S08: co-localización de sensores, no conectividad física.
c.aggregate([
  { $group: { _id: { sensor_id: '$sensor_id', station: '$station', type: '$type' } } }
]);`,
  S09: `// S09: sólo temperatura; muestreo sistemático reproducible en Python.
c.find({ type: 'temperatura' }, { _id: 0, station: 1, city: 1, value: 1, timestamp: 1 })
 .sort({ station: 1, timestamp: 1 });`,
  S10: `// S10: reproducción histórica; últimas 48 lecturas de un sensor.
c.find({ sensor_id: 'SDQ-1-temperatura' }, { _id: 0, value: 1, timestamp: 1 })
 .sort({ timestamp: -1 }).limit(48);`,
};

function vizSection(v, source, queryLabel, first) {
  const q = v.id.startsWith('S') ? MONGO[v.id] : SQL[v.id];
  return [
    H3(`${v.id} · ${v.title}`, !first),
    ...figure(R('figuras', v.id + '.png'), `${v.title} (${v.id}). Fuente: ${source}.`, 6.0, 3.6),
    P(`**Construcción.** ${v.method}`),
    P(`**Resultado observado.** ${v.insight}`),
    P(`**Insight y decisión que apoya.** ${v.decision}`),
    P(`**Límite de interpretación.** ${v.limit}`),
    label(`**Consulta** (${queryLabel}):`),
    ...code(q),
    label('**Transformación y visualización en Python** (`src/analisis.py`):'),
    ...code(v.code),
  ];
}
const vizOf = (prefix) => viz.filter(v => v.id.startsWith(prefix));
const cap = (f) => R('informe/recursos/capturas', f + '.png');
const dash = (f) => R('informe/recursos/dashboard', f + '.png');
const utc = (s) => s.replace('T', ' ').slice(0, 19) + ' UTC';

// ---------- contenido ----------
const cover = [
  new d.Paragraph({ alignment: d.AlignmentType.CENTER, spacing: { before: 400, after: 300 }, children: [new d.ImageRun({ type: 'jpg', data: fs.readFileSync(R('informe/recursos/intec_logo.jpg')), transformation: { width: 130, height: 146 }, altText: { title: 'INTEC', description: 'Logo de INTEC', name: 'intec' } })] }),
  new d.Paragraph({ alignment: d.AlignmentType.CENTER, spacing: { after: 100 }, children: [new d.TextRun({ text: 'INSTITUTO TECNOLÓGICO DE SANTO DOMINGO (INTEC)', bold: true, size: 26 })] }),
  new d.Paragraph({ alignment: d.AlignmentType.CENTER, spacing: { after: 100 }, children: [new d.TextRun({ text: 'Maestría en Ciencia de Datos', size: 24 })] }),
  new d.Paragraph({ alignment: d.AlignmentType.CENTER, spacing: { after: 100 }, children: [new d.TextRun({ text: 'MCD512 · Big Data', size: 24 })] }),
  new d.Paragraph({ spacing: { before: 700 }, children: [] }),
  new d.Paragraph({ alignment: d.AlignmentType.CENTER, spacing: { after: 200 }, children: [new d.TextRun({ text: 'Análisis Exploratorio y Visualización de Datos con SQL y NoSQL', bold: true, color: NAVY, size: 40 })] }),
  new d.Paragraph({ alignment: d.AlignmentType.CENTER, children: [new d.TextRun({ text: 'Northwind en SQL Server, HR en Oracle y sensores en MongoDB sobre Docker', color: BLUE, size: 26 })] }),
  new d.Paragraph({ spacing: { before: 1300 }, children: [] }),
  ...[['Estudiante: ', 'Dan Carrión'], ['Matrícula: ', '1131022'], ['Asignatura: ', 'MCD512 · Big Data'], ['Docente: ', 'Prof. José M. Aquino Cepeda, MSc'], ['Pruebas realizadas: ', '11 de octubre de 2026'], ['Fecha de entrega: ', 'octubre de 2026']]
    .map(([k, v]) => new d.Paragraph({ alignment: d.AlignmentType.CENTER, spacing: { after: 80 }, children: [new d.TextRun({ text: k, bold: true, size: 24 }), new d.TextRun({ text: v, size: 24 })] })),
  new d.Paragraph({ alignment: d.AlignmentType.CENTER, spacing: { after: 80 }, children: [new d.TextRun({ text: 'Repositorio: ', bold: true, size: 24 }), new d.ExternalHyperlink({ link: REPO, children: [new d.TextRun({ text: REPO.replace('https://', ''), style: 'Hyperlink', size: 24 })] })] }),
  new d.Paragraph({ alignment: d.AlignmentType.CENTER, spacing: { after: 80 }, children: [new d.TextRun({ text: 'Dashboard: ', bold: true, size: 24 }), new d.ExternalHyperlink({ link: DASH, children: [new d.TextRun({ text: DASH.replace('https://', '').replace(/\/$/, ''), style: 'Hyperlink', size: 24 })] })] }),
];

const body = [];
const add = (...xs) => xs.forEach(x => Array.isArray(x) ? body.push(...x) : body.push(x));

// 1. Introducción
add(H1('1. Introducción y objetivos'));
add(P('Este trabajo transforma los resultados de tres gestores de bases de datos en visualizaciones que apoyan el análisis exploratorio y la toma de decisiones. Se utilizan la base **Northwind** en **SQL Server 2022**, el esquema **HR** en **Oracle Database Free** y una colección de lecturas de sensores en **MongoDB 8.0**. Los tres gestores se ejecutan como contenedores de Docker Desktop en un Mac con Apple Silicon y se consultan desde un cliente Python con los drivers ODBC de Microsoft y Oracle y con PyMongo.'));
add(P(`Las conexiones se verificaron el 11 de octubre de 2026 con consultas reales sobre cada gestor. A partir de esas conexiones se extrajeron ${res.nw.orders} pedidos y ${fmt(res.nw.lines, 0)} líneas de venta de Northwind, ${res.hr.employees} empleados de HR y ${fmt(res.sensors.rows, 0)} documentos de sensores. Sobre esos datos se construyeron **30 visualizaciones** (diez por gestor), un dashboard interactivo en HTML y un notebook de Jupyter. Cada figura se acompaña de su construcción, el resultado observado, la decisión que apoya, su límite de interpretación y el código utilizado.`));
add(P('En Northwind, las ventas netas suman 1,265,793.04 con un máximo mensual en abril de 1998 y una concentración del 45.0% en los diez principales clientes. En HR, el salario mediano es 6,200.00 y Americas concentra el 65.4% de la plantilla. En los sensores, el detector robusto basado en la mediana y la MAD identifica las 103 anomalías inyectadas con una precisión de 75.2%.'));
add(H3('Objetivos'));
add(bullets([
  'Establecer conexiones verificables a SQL Server y Oracle mediante ODBC, y a MongoDB mediante su driver para Python.',
  'Describir las tres bases de datos y extraer sus datos con consultas de sólo lectura, conservando relaciones, unidades y procedencia.',
  'Construir diez visualizaciones por gestor, seleccionando el tipo de gráfico según el *insight* buscado.',
  'Explicar cada visualización con su método, resultado, decisión que apoya y límites, junto con el código o fórmula utilizada.',
  'Integrar las visualizaciones en un dashboard con filtros, interactividad y un monitoreo simulado en tiempo real.',
  'Validar la precisión de los cálculos con comprobaciones automáticas de sumas, claves y reglas estadísticas.',
]));
add(H3('Organización del informe'));
add(P('La sección 2 describe la metodología y las herramientas. La sección 3 documenta el laboratorio en Docker y la configuración de las conexiones. Las secciones 4, 5 y 6 corresponden a cada gestor: descripción de la base, carga, evidencia de conexión, diez visualizaciones y los *insights* obtenidos. La sección 7 presenta la extracción integrada, las validaciones y el dashboard; la 8 discute los resultados y la 9 resume las conclusiones. ' + (SIN_ANEXO_C ? 'Los anexos contienen los pasos de reproducción, el inventario del código fuente y los enlaces al repositorio y al dashboard.' : 'Los anexos contienen los pasos de reproducción, el inventario del código fuente, los enlaces al repositorio y al dashboard, y las capturas del dashboard.')));

add(H3('Código fuente'));
add(linkP('Todo el código, las consultas, los datos extraídos, el dashboard y este informe están en el repositorio ', REPO, '. El archivo `COMO_CORRER.md` explica paso a paso cómo reproducir el laboratorio y regenerar los resultados.'));
add(H3('Dashboard interactivo'));
add(linkP('El dashboard está publicado en ', DASH, ' y se abre en cualquier navegador, sin instalar nada. Permite elegir la base de datos y cada una de sus diez visualizaciones, aplicar filtros, hacer zoom, inspeccionar valores al pasar el cursor y reproducir el monitoreo simulado de S10 (sección 7.2).'));

// 2. Metodología
add(H1('2. Metodología y herramientas'));
add(P('El trabajo siguió las cuatro fases de la guía del curso. Cada fase produce archivos que la siguiente reutiliza, de modo que las figuras, el dashboard y el informe se calculan sobre los mismos datos extraídos.'));
add(table(['Fase', 'Actividades realizadas', 'Resultado'], [
  ['1. Conexión y extracción', 'Contenedores de los tres gestores, carga de Northwind, HR y sensores; conexiones ODBC y PyMongo; extracción de sólo lectura', 'CSV por tabla y colección, con hashes de procedencia'],
  ['2. Análisis exploratorio', 'Conversión de fechas, uniones con claves, estadística descriptiva, correlaciones y detección de atípicos con MAD', 'Tres tablas analíticas y resultados verificables'],
  ['3. Visualización', 'Selección del gráfico según el insight, paleta accesible, etiquetas y unidades; versión estática (PNG) e interactiva (Plotly)', '30 figuras con explicación'],
  ['4. Dashboarding', 'Selector de base y figura, filtros, KPI, panel explicativo, reproducción temporal y diseño responsivo; pruebas de uso', 'dashboard/index.html'],
], [1.2, 3, 1.6]));
add(H2('2.1 Herramientas'));
add(table(['Componente', 'Versión / detalle', 'Uso en el trabajo'], [
  ['Docker Desktop', '4.94.0 (Engine 29.8.2, Compose 5.5.1), Apple Virtualization y Rosetta', 'Ejecución de los tres gestores y del cliente de análisis'],
  ['SQL Server', '2022 Developer (imagen mssql/server:2022-latest, amd64)', 'Base Northwind'],
  ['Oracle Database Free', 'Imagen database/free:23.26.3.0-lite-arm64', 'Esquema HR en el servicio FREEPDB1'],
  ['MongoDB', '8.0 (arm64)', 'Base bigdata_final, colección sensores_datos'],
  ['Drivers', 'Microsoft ODBC Driver 18; Oracle Instant Client 23.26 ODBC; unixODBC', 'Conexión ODBC a SQL Server y Oracle'],
  ['Python', '3.11 con pyodbc 5.3, PyMongo 4.18, pandas 3.0, NumPy, SciPy', 'Conexión, extracción y análisis'],
  ['Visualización', 'Matplotlib 3.11 (PNG) y Plotly 7.1 (interactivo)', 'Figuras del informe y del dashboard'],
  ['Entornos', 'Jupyter Notebook y scripts Python; Safari para el dashboard', 'Ejecución reproducible y revisión'],
], [1.3, 2.6, 2.1]));
add(H2('2.2 Definiciones y criterios de calidad'));
add(P('Las métricas se definieron antes de construir las figuras para evitar ambigüedades entre fuentes:'));
add(bullets([
  '**Venta neta de línea** = UnitPrice × Quantity × (1 − Discount), con el precio histórico de *Order Details* y no el precio actual del catálogo. La venta bruta total es 1,354,458.59 y la reducción por descuentos, 88,665.55.',
  '**Antigüedad** = (fecha de referencia 08/10/2026 − hire_date) / 365.25 años. Las uniones izquierdas conservan al empleado sin departamento.',
  '**Fechas de sensores**: se almacenan como BSON Date en UTC y se agrupan en la zona America/Santo_Domingo.',
  '**Atípicos**: una lectura es alerta si |valor − mediana| / (1.4826 × MAD) > 3.5, con mediana y MAD calculadas por sensor y hora del día [11].',
  '**Claves sin duplicación**: línea de venta = OrderID + ProductID; lectura = sensor_id + timestamp.',
]));
add(P('La precisión de las visualizaciones se valida con 17 comprobaciones automáticas (`src/validar.py`): conciliación de ventas por mes, cliente, categoría y empleado; conservación de los 107 empleados; existencia de supervisores sin ciclos; unicidad temporal por sensor; cobertura de 720 lecturas por sensor; reproducción de la regla MAD y de su matriz de confusión. Las 17 resultaron correctas sobre los datos extraídos.'));
add(P('Para la accesibilidad se usan paletas distinguibles para daltonismo, etiquetas y leyendas en todos los gráficos, y la información principal también se expresa en texto, de modo que el color no es la única vía de lectura.'));

// 3. Laboratorio
add(H1('3. Laboratorio en Docker y conexiones'));
add(P('Los tres gestores se ejecutan en un proyecto de Docker Compose llamado `bigdata-final`, con volúmenes persistentes y puertos publicados sólo en la interfaz local. Un cuarto servicio, `analisis`, es un cliente temporal de Python que contiene los drivers ODBC y PyMongo: se crea para cada tarea, se conecta a los gestores por la red interna de Compose y se elimina al terminar. Así no se instalan drivers en macOS y la configuración queda descrita en archivos versionables.'));
add(table(['Servicio', 'Contenedor', 'Datos', 'Puerto en el Mac'], [
  ['SQL Server 2022', 'bigdata-sqlserver', 'Base Northwind', '127.0.0.1:1434'],
  ['Oracle Database Free', 'bigdata-oracle', 'Esquema HR, servicio FREEPDB1', '127.0.0.1:1522'],
  ['MongoDB 8.0', 'bigdata-mongodb', 'bigdata_final.sensores_datos', '127.0.0.1:27020'],
  ['Cliente de análisis', 'analisis (temporal)', 'Python, ODBC 18, Instant Client, PyMongo', 'Sin puerto'],
], [1.5, 1.6, 2.2, 1.4]));
add(P('Todas las operaciones se ejecutan con `docker/lab.py`, que envuelve los comandos de Docker Compose, espera a que cada gestor esté saludable, oculta las contraseñas en la salida e impide reinstalar una base que ya contiene datos.'));
add(H2('3.1 Preparación de Docker Desktop'));
add(P('SQL Server 2022 y el cliente con el driver ODBC de Oracle sólo se distribuyen para arquitectura amd64. En un Mac con Apple Silicon, Docker Desktop los ejecuta mediante emulación; se activó **Rosetta** con el *Apple Virtualization framework* para acelerarla [10]. Oracle y MongoDB usan imágenes ARM64 nativas.'));
add(figure(cap('docker_rosetta'), 'Configuración de Docker Desktop: Apple Virtualization framework con Rosetta para emular amd64.'));
add(figure(cap('versiones'), 'Versiones de Docker Engine, Docker Compose y Python utilizadas en el laboratorio.', 3.9, 4.6));
add(H2('3.2 Configuración de credenciales'));
add(P('`lab.py configurar` genera `docker/.env` con cuatro contraseñas aleatorias distintas (SQL Server, administrador de Oracle, usuario HR y administrador de MongoDB) y permisos 600; no se imprimen ni se incluyen en la entrega. `lab.py validar` comprueba la sintaxis de Compose y las variables sin crear contenedores.'));
add(figure(cap('configurar'), 'Creación y validación de la configuración del laboratorio.', 4.4));
add(H2('3.3 Cadenas de conexión del cliente'));
add(P('Dentro de la red de Compose el cliente usa los nombres de servicio en lugar de `localhost`. El archivo `docker/cliente.py` construye las cadenas a partir de las variables de entorno, sin escribir contraseñas en disco:'));
add(code(`SQLSERVER_ODBC = 'DRIVER={ODBC Driver 18 for SQL Server};SERVER=sqlserver,1433;'
                 'DATABASE=Northwind;UID=sa;PWD=***;Encrypt=yes;TrustServerCertificate=yes'
ORACLE_ODBC    = 'DRIVER={Oracle Instant Client ODBC};DBQ=oracle:1521/FREEPDB1;UID=hr;PWD=***'
MONGODB_URI    = 'mongodb://bigdata_admin:***@mongodb:27017/?authSource=admin'`));
add(P('La verificación (`src/conexiones.py verificar`) abre cada conexión y ejecuta una consulta sobre una tabla del trabajo; sólo registra éxito si el conteo es mayor que cero. El resultado se guarda con fecha UTC y conector en `evidencias/conexiones.json`.'));
add(code(`def connect(motor):
    if motor in ('sqlserver', 'oracle'):
        import pyodbc
        return pyodbc.connect(os.environ[{'sqlserver': 'SQLSERVER_ODBC',
                                          'oracle': 'ORACLE_ODBC'}[motor]], timeout=10)
    from pymongo import MongoClient
    client = MongoClient(os.environ['MONGODB_URI'], serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    return client`));
add(H2('3.4 Cliente de análisis con drivers ODBC'));
add(P('La imagen del cliente parte de `python:3.11-slim-bookworm` e instala unixODBC, Microsoft ODBC Driver 18 desde el repositorio de Microsoft [3] y Oracle Instant Client Basic y ODBC [4]. Los ZIP de Oracle se verifican con sus hashes SHA-256 antes de registrarse en `/etc/odbcinst.ini`. Luego se instalan las librerías de `requirements.txt`.'));
add(figure(cap('cliente_build'), 'Construcción del cliente: instalación de msodbcsql18 y verificación de los paquetes de Oracle Instant Client (/tmp/basic.zip: OK, /tmp/odbc.zip: OK).', 6.3));
add(figure(cap('lab_drivers'), 'Imagen del cliente construida y drivers ODBC registrados: ODBC Driver 18 for SQL Server y Oracle Instant Client ODBC.', 4.6));
add(H2('3.5 Estado de los tres gestores'));
add(figure(cap('lab_estado'), 'Los tres contenedores en ejecución y con estado healthy, con sus puertos locales.', 6.4));
add(figure(cap('docker_desktop'), 'Vista de Docker Desktop: el proyecto bigdata-final con SQL Server (emulado, AMD64), Oracle y MongoDB.', 6.2));

// 4. SQL Server
add(H1('4. SQL Server y Northwind'));
add(H2('4.1 Descripción de la base de datos'));
add(P('Northwind es la base de ejemplo de Microsoft que modela una distribuidora de alimentos: clientes, empleados, pedidos, líneas de pedido, productos, categorías, proveedores y transportistas [1]. Sus pedidos cubren del 4 de julio de 1996 al 6 de mayo de 1998. El análisis usa la cadena Orders → Order Details → Products → Categories, junto con Orders → Customers y Orders → Employees; Products → Suppliers aporta el análisis de precios. Todas las uniones son de muchos a uno y se comprueba que conserven las 2,155 líneas.'));
add(table(['Tabla', 'Filas', 'Uso en el análisis'], [
  ['Orders', '830', 'Fecha del pedido, cliente y empleado'],
  ['Order Details', '2,155', 'Precio histórico, cantidad y descuento'],
  ['Customers', '91', 'Empresa y país del cliente'],
  ['Products / Categories', '77 / 8', 'Catálogo y clasificación comercial'],
  ['Employees / Suppliers', '9 / 29', 'Ventas por empleado y precios por proveedor'],
], [2, 1, 3.5]));
add(H2('4.2 Instalación y carga'));
add(P('`lab.py iniciar sqlserver` crea el contenedor a partir de la imagen oficial de SQL Server para Linux [8] y espera a que el *healthcheck* ejecute `SELECT 1` con sqlcmd. Después, `lab.py cargar sqlserver` crea la base vacía `Northwind` y ejecuta el script oficial `instnwnd.sql`; al terminar verifica los conteos de las siete tablas principales.'));
add(figure(cap('sql_iniciar'), 'Creación del contenedor de SQL Server y estado healthy en el puerto 1434.', 6.4));
add(figure(cap('carga_sqlserver'), 'Carga de Northwind: 830 pedidos y 2,155 líneas.', 4.4));
add(H2('4.3 Conexión ODBC y evidencia'));
add(P(`La conexión usa **pyodbc** con **Microsoft ODBC Driver 18**, con cifrado activo y confianza en el certificado autofirmado del laboratorio. La prueba consulta \`DB_NAME()\` y \`COUNT(*)\` de \`dbo.Orders\`: devolvió la base Northwind con ${con.sqlserver.orders} pedidos. Última verificación registrada: ${utc(con.sqlserver.timestamp_utc)}.`));
add(figure(cap('conexion_sqlserver'), 'Conexión exitosa a SQL Server mediante ODBC Driver 18 (CONEXIÓN VERIFICADA, 830 pedidos).', 6.4));
add(H2('4.4 Visualizaciones'));
add(P('Las diez figuras siguientes se calculan sobre las tablas extraídas de SQL Server. Las consultas equivalentes están en `sql/northwind.sql`. Los importes son ventas netas (después de descuentos), sin costos, impuestos ni flete; julio de 1996 y mayo de 1998 son meses parciales.'));
vizOf('N').forEach((v, i) => add(vizSection(v, 'SQL Server / Northwind', '`sql/northwind.sql`', i === 0)));
add(H2('4.5 Insights obtenidos de Northwind'));
add(bullets([
  '**Crecimiento y estacionalidad.** Las ventas crecen durante 1997 y alcanzan su máximo en abril de 1998 (123,798.68); 1998-Q1 es el trimestre más alto (298,491.55). Para presupuestar conviene comparar sólo trimestres completos.',
  '**Concentración de clientes.** Los diez principales clientes generan el 45.0% de la venta neta; QUICK-Stop aporta 110,277.30. Es un riesgo de dependencia que justifica un seguimiento de cuentas clave.',
  '**Mezcla de producto.** Beverages es la categoría líder (21.2% del total) y Côte de Blaye el producto de mayor ingreso (141,396.73). Sin costos no se puede afirmar que sean los más rentables.',
  '**Descuentos.** La correlación entre descuento y cantidad es débil (r = 0.129): los descuentos no se asocian claramente con pedidos más grandes y requieren un análisis por producto y cliente.',
  '**Operación.** Margaret Peacock concentra el 18.4% de las ventas, y el martes registra más pedidos (168). Ambos datos ayudan a planificar personal y metas, combinados con la cartera asignada.',
]));

// 5. Oracle
add(H1('5. Oracle y recursos humanos'));
add(H2('5.1 Descripción de la base de datos'));
add(P('El esquema HR de Oracle modela una organización: employees se relaciona con departments y jobs; departments con locations; locations con countries, y countries con regions. job_history guarda los puestos y departamentos anteriores de algunos empleados [2]. Se utilizó la versión oficial del repositorio oracle-samples, que contiene cinco regiones.'));
add(table(['Tabla', 'Filas', 'Uso en el análisis'], [
  ['employees', '107', 'Salario, fecha de ingreso, puesto y supervisor'],
  ['departments / jobs', '27 / 19', 'Asignación organizacional y bandas salariales'],
  ['locations / countries / regions', '23 / 25 / 5', 'Ubicación geográfica de los departamentos'],
  ['job_history', '10', 'Cambios de puesto de 7 empleados'],
], [2.3, 1.1, 3.1]));
add(P('HR no contiene edad, género, competencias, evaluaciones de desempeño, bajas ni salarios históricos. Por eso la "distribución demográfica" se aborda con la ubicación de los departamentos, el radar compara métricas estructurales de los puestos y el waterfall se presenta como escenario de bandas salariales, no como una carrera real.'));
add(H2('5.2 Instalación y carga'));
add(P('El primer arranque de Oracle descarga la imagen Lite del registro oficial de Oracle [9] y crea la base de datos; el *healthcheck* comprueba que la PDB `FREEPDB1` responda. `lab.py cargar oracle` crea el usuario HR y ejecuta como HR los scripts oficiales `hr_create.sql`, `hr_populate.sql` y `hr_code.sql`.'));
add(figure(cap('oracle_iniciar'), 'Descarga de la imagen de Oracle Database Free Lite y contenedor healthy.', 4.4));
add(P('**Incidencia y solución.** La primera carga falló con `ORA-00959: tablespace \'USERS\' does not exist`: la variante Lite de la imagen no incluye ese tablespace, que el esquema HR usa por defecto. El error ocurrió antes de crear el usuario, por lo que no quedaron objetos a medias. Se modificó el cargador para crear el tablespace cuando falta y se repitió la carga:'));
add(code(`CREATE TABLESPACE users
  DATAFILE '/opt/oracle/oradata/FREE/FREEPDB1/users01.dbf'
  SIZE 100M AUTOEXTEND ON NEXT 50M MAXSIZE 2G;`));
add(figure(cap('carga_oracle'), 'Primer intento con ORA-00959 y carga posterior: HR contiene las siete tablas con los conteos esperados.', 6.3));
add(H2('5.3 Conexión ODBC y evidencia'));
add(P(`La conexión usa **pyodbc** con el driver **Oracle Instant Client ODBC** y el descriptor \`oracle:1521/FREEPDB1\` (nombre de servicio, no SID). La prueba consulta el esquema actual y \`COUNT(*)\` de \`employees\`: devolvió el esquema HR con ${con.oracle.employees} empleados. Última verificación registrada: ${utc(con.oracle.timestamp_utc)}.`));
add(P('**Incidencia y solución.** La primera verificación devolvió `ORA-01017: invalid credential`. La contraseña era correcta, pero el cliente la enviaba entre llaves (`PWD={…}`), un formato que acepta el driver de Microsoft pero que el driver ODBC de Oracle interpreta como parte de la contraseña. Se envió la contraseña sin llaves, lo cual es seguro porque el generador sólo usa letras, números, guion y guion bajo.'));
add(figure(cap('conexion_oracle'), 'Conexión exitosa a Oracle mediante Oracle Instant Client ODBC (CONEXIÓN VERIFICADA, esquema HR, 107 empleados).', 6.4));
add(H2('5.4 Visualizaciones'));
add(P('Las diez figuras siguientes se calculan sobre las siete tablas de HR extraídas de Oracle. Las consultas están en `sql/hr.sql`. El salario se expresa en la unidad de la muestra (mensual, sin moneda documentada) y la antigüedad se mide a la fecha fija del 08/10/2026.'));
vizOf('H').forEach((v, i) => add(vizSection(v, 'Oracle / HR', '`sql/hr.sql`', i === 0)));
add(H2('5.5 Insights obtenidos de HR'));
add(bullets([
  '**Compensación.** El salario mediano es 6,200.00 y el promedio 6,461.83, con un máximo de 24,000.00: la distribución tiene cola hacia salarios altos concentrados en puestos directivos.',
  '**Antigüedad y salario.** La correlación es moderada (r = 0.415). La antigüedad mediana es 10.76 años; la mayoría de la plantilla (66 empleados) tiene entre 9 y 12 años.',
  '**Estructura.** El organigrama tiene una sola raíz y tres niveles por debajo del presidente para 107 empleados: una estructura plana con amplitudes de supervisión grandes en algunos gerentes.',
  '**Ubicación.** South San Francisco concentra 45 empleados y Americas el 65.4% de la plantilla; un empleado no tiene departamento ni ubicación, lo que señala un problema de calidad de datos.',
  '**Movilidad.** Sólo 7 empleados tienen historial (10 transiciones, 4 con cambio de departamento): no alcanza para estimar rotación, pero sí para formular preguntas sobre movilidad interna.',
]));

// 6. MongoDB
add(H1('6. MongoDB y sensores'));
add(H2('6.1 Descripción de la base de datos'));
add(P('La colección `sensores_datos` de la base `bigdata_final` guarda una lectura por documento: timestamp (BSON Date), city, station, sensor_id, type, value, unit, latitude, longitude e injected_anomaly. Los datos son una **simulación propia** y reproducible (semilla 5122026) con ciclos diarios, ruido y 103 anomalías inyectadas; la etiqueta injected_anomaly sólo se usa para evaluar el detector, no para detectar.'));
add(table(['Propiedad', 'Configuración'], [
  ['Ubicaciones', 'Santo Domingo, Santiago y Punta Cana; dos estaciones por ciudad'],
  ['Magnitudes', 'Temperatura (°C), humedad (%) y CO2 (ppm)'],
  ['Frecuencia y período', 'Una lectura por hora y sensor, septiembre de 2026'],
  ['Tamaño', '18 sensores × 720 horas = 12,960 documentos'],
  ['Índices', 'Único (sensor_id, timestamp); compuesto (type, timestamp, city)'],
], [1.8, 4.7]));
add(H2('6.2 Instalación y carga'));
add(P('`lab.py iniciar mongodb` crea una instancia con autenticación. `lab.py cargar mongodb` aplica un validador de esquema y los índices, e importa `sensores.jsonl` con `mongoimport` en modo *upsert* por (sensor_id, timestamp), de modo que repetir la carga no duplica lecturas. Las fechas se importan como BSON Date mediante Extended JSON [6].'));
add(figure(cap('carga_mongodb'), 'Creación del contenedor de MongoDB e importación de 12,960 documentos en sensores_datos.', 5.2));
add(H2('6.3 Conexión con PyMongo y evidencia'));
add(P(`La conexión usa **PyMongo** con autenticación contra la base \`admin\` [5]. La prueba ejecuta \`ping\` y cuenta los documentos de \`sensores_datos\`: devolvió ${fmt(con.mongodb.documents, 0)} documentos. Última verificación registrada: ${utc(con.mongodb.timestamp_utc)}.`));
add(figure(cap('conexion_mongodb'), 'Conexión exitosa a MongoDB mediante PyMongo (CONEXIÓN VERIFICADA, 12,960 documentos).', 6.4));
add(H2('6.4 Visualizaciones'));
add(P('Las diez figuras siguientes se calculan sobre los documentos extraídos de MongoDB. Las consultas están en `mongo/consultas.js`; en todas, `c` es la colección `sensores_datos` y `tz` la zona `America/Santo_Domingo`. Las magnitudes con unidades distintas nunca se suman entre sí.'));
vizOf('S').forEach((v, i) => add(vizSection(v, 'MongoDB / sensores (simulación)', '`mongo/consultas.js`', i === 0)));
add(H2('6.5 Insights obtenidos de los sensores'));
add(bullets([
  '**Patrones por ubicación.** Santo Domingo registra la mayor temperatura media (28.24 °C). La cobertura es uniforme: cada estación aporta 2,160 lecturas y cada ciudad el 33.3% diario.',
  '**Correlación entre sensores.** Temperatura y humedad se relacionan de forma inversa (r = −0.590) y temperatura y CO2 de forma directa (r = 0.341), relaciones definidas por el generador.',
  '**Anomalías.** El detector MAD identifica las 103 anomalías inyectadas (sensibilidad 100%) con 34 falsos positivos (precisión 75.2%): conviene revisar las alertas antes de descartar datos y calibrar el umbral.',
  '**Patrón diario.** El 25 de septiembre concentra 9 alertas sobre 432 lecturas, la jornada que más revisión requiere.',
  '**Monitoreo.** La reproducción histórica permite probar alertas visuales y controles antes de conectar un flujo real.',
]));

// 7. Integración y dashboard
add(H1('7. Extracción integrada, validación y dashboard'));
add(H2('7.1 Extracción desde los tres gestores'));
add(P('`lab.py integrar` respalda los resultados anteriores y ejecuta `run.py --desde-bd` dentro del cliente. Este comando vuelve a verificar las tres conexiones, exporta las tablas de Northwind y HR por ODBC y la colección por PyMongo, registra la fecha y el hash SHA-256 de cada CSV en `proveniencia_fuentes.json`, recalcula las 30 visualizaciones, ejecuta las 17 comprobaciones y regenera el dashboard. Si una conexión falla, se detiene antes de modificar los datos.'));
add(figure(cap('lab_integrar'), 'Integración: respaldo, verificación de las tres conexiones y extracción de sólo lectura desde SQL Server, Oracle y MongoDB.', 6.4));
add(figure(cap('lab_integrar_fin'), 'Final de la integración: dashboard regenerado y 17/17 comprobaciones correctas.', 4.2));
add(H2('7.2 Dashboard interactivo'));
add(P('El dashboard (`dashboard/index.html`) organiza las 30 visualizaciones por base de datos. Un selector elige la base y otro la figura; los botones Anterior y Siguiente recorren las diez figuras. Cada vista muestra tres indicadores clave, el gráfico interactivo de Plotly (información al pasar el cursor, zoom, series activables desde la leyenda, treemap navegable y gráfico 3D rotable) y un panel con el método, el resultado, la decisión y el límite, además de la fórmula o el código [7].'));
add(P('Hay filtros específicos en N01 (país), H01 (departamento), S06 y S10 (sensor). El aviso superior indica la procedencia de los datos: tras la integración, informa que se extrajeron de SQL Server, Oracle y MongoDB. El archivo incluye los datos y una copia local de Plotly, por lo que funciona sin Internet ni servidor.'));
add(linkP('Para facilitar su consulta, el dashboard se publicó con GitHub Pages en ', DASH, '. Esa página sirve el mismo archivo del repositorio, con los datos extraídos de los tres gestores; no se conecta a las bases en tiempo real.'));
add(figure(dash('vista_general'), 'Vista general del dashboard: aviso de procedencia, selectores, filtro de país, indicadores y N01.', 6.3));
add(P('El monitoreo en tiempo real se simula en S10: con Reproducir, Pausar y Reiniciar, cada segundo agrega una hora histórica de un sensor a una ventana de 48 lecturas y muestra el umbral de alerta. No es *streaming* desde MongoDB, sino una reproducción de la serie extraída.'));
add(figure(dash('vista_sensores_s10'), 'Dashboard de monitoreo simulado (S10) con controles de reproducción y filtro de sensor.', 6.3));
add(H2('7.3 Pruebas de usabilidad'));
add(P('Se recorrieron las 30 visualizaciones en el navegador, verificando que cada una se dibuja sin errores, y se probaron los filtros, la navegación y los controles de reproducción. En la revisión, el mapa de S02 aparecía en blanco: las seis estaciones tienen el mismo número de lecturas, por lo que la escala de densidad quedaba sin rango y Plotly no dibujaba nada. Se reemplazó por un gráfico de estaciones en longitud y latitud a igual escala, coloreado por número de lecturas, que además funciona sin mapas externos. El diseño apila los paneles en pantallas estrechas y los controles tienen etiquetas y foco visible para el teclado.' + (SIN_ANEXO_C ? ' Las 30 vistas pueden explorarse en el dashboard publicado (sección 7.2).' : ' El Anexo C reúne las capturas de las 30 vistas.')));

// 8. Discusión
add(H1('8. Discusión y recomendaciones'));
add(H2('8.1 Interpretación de los resultados'));
add(P('La venta neta cuantifica ingresos después de descuentos, pero no utilidad: el treemap y el ranking de clientes señalan dónde concentrar el seguimiento, no dónde está el margen. El pico de abril de 1998 debe leerse en una serie cuyos extremos son meses incompletos; para reportes operativos conviene mostrar también los días cubiertos y la venta por día.'));
add(P('En HR, los histogramas y violines muestran la heterogeneidad salarial, pero explicar diferencias exige comparar puestos equivalentes. El historial de siete empleados describe cambios registrados y no permite estimar rotación. En los sensores, la MAD controla la influencia de los extremos; su precisión de 75.2% justifica una revisión manual, y la evaluación es retrospectiva: para medir generalización habría que calibrar con datos anteriores y probar con datos posteriores.'));
add(H2('8.2 Escalabilidad y recomendaciones técnicas'));
add(P('Con volúmenes mayores, agregar en el gestor (por día, mes, departamento o ubicación) reduce la transferencia de datos; la extracción completa usada aquí es adecuada para el tamaño de las muestras, pero no se midió con millones de filas. Las siguientes mejoras se proponen como trabajo futuro, no como resultados comprobados:'));
add(table(['Componente', 'Mejora propuesta', 'Comprobación necesaria'], [
  ['SQL Server', 'Índices sobre fechas y claves de unión; preagregación mensual', 'Plan de ejecución y tiempos con volumen representativo'],
  ['Oracle', 'Filtrar columnas y fechas; revisar índices de las relaciones', 'Plan de consulta y conteos después de filtros'],
  ['MongoDB', 'Agregaciones temporales con índice compuesto; política de retención', 'explain(), selectividad y tamaño de la colección'],
  ['Sensores', 'Referencia robusta entrenada sólo con datos anteriores', 'Prueba temporal separada: precisión y sensibilidad'],
  ['Dashboard', 'Muestrear figuras densas conservando métricas completas', 'Tiempo de carga y pérdida visual por muestreo'],
], [1.2, 2.6, 2.6]));
add(P('En cuanto a fechas, todas las agregaciones de sensores declaran la zona horaria explícitamente y Northwind usa la fecha del pedido sin hora, lo que evita desplazamientos de día al agrupar.'));

// 9. Conclusiones
add(H1('9. Conclusiones'));
add(P('Se establecieron las tres conexiones requeridas: SQL Server y Oracle mediante ODBC (Microsoft ODBC Driver 18 y Oracle Instant Client ODBC) y MongoDB mediante PyMongo, todas verificadas con consultas reales sobre tablas y colecciones del trabajo. Los datos de las 30 visualizaciones provienen de esas conexiones, con procedencia trazable por hash.'));
add(P('Las visualizaciones cubren los requisitos de cada gestor: ventas, clientes, empleados, tendencias y productos en Northwind; compensación, ubicación, estructura, movilidad y comparaciones por departamento en HR; y series temporales, patrones por ubicación, anomalías, correlaciones y monitoreo simulado en los sensores. Cada figura explica su método, resultado, decisión y límite, y su precisión se respalda con 17 comprobaciones automáticas.'));
add(P('La principal lección metodológica es mantener coherencia entre lo que contiene la fuente y lo que comunica el gráfico: el ingreso no se presenta como utilidad, las métricas estructurales no se presentan como competencias, los cambios registrados no se extrapolan a rotación y la reproducción histórica no se presenta como *streaming*. El laboratorio en Docker, la extracción automatizada y el dashboard sin dependencias permiten reproducir todo el trabajo con unos pocos comandos.'));

// Referencias
headings.push({ level: 1, text: 'Referencias' });
add(new d.Paragraph({ heading: d.HeadingLevel.HEADING_1, pageBreakBefore: true, spacing: { after: 240 }, children: [new d.TextRun('Referencias')] }));
const refs = [
  ['Microsoft. Northwind and pubs sample databases for SQL Server (instnwnd.sql).', 'https://github.com/microsoft/sql-server-samples/blob/master/samples/databases/northwind-pubs/instnwnd.sql'],
  ['Oracle. Database Sample Schemas: Human Resources (HR).', 'https://github.com/oracle-samples/db-sample-schemas/tree/main/human_resources'],
  ['Microsoft Learn. Install the Microsoft ODBC driver for SQL Server (Linux).', 'https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server'],
  ['Oracle. Oracle Instant Client Downloads for Linux x86-64 (Basic y ODBC).', 'https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html'],
  ['MongoDB. PyMongo Driver: Connect to MongoDB.', 'https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/'],
  ['MongoDB. $dateTrunc (aggregation expression operator).', 'https://www.mongodb.com/docs/manual/reference/operator/aggregation/dateTrunc/'],
  ['Plotly. Plotly Open Source Graphing Library for Python.', 'https://plotly.com/python/'],
  ['Microsoft Learn. Deploy and connect to SQL Server Linux containers.', 'https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-docker-container-deployment'],
  ['Oracle. Oracle Database Free container images (Oracle Container Registry).', 'https://container-registry.oracle.com/ords/ocr/ba/database/free'],
  ['Docker. Docker Desktop settings: Virtual Machine Options y Rosetta.', 'https://docs.docker.com/desktop/settings-and-maintenance/settings/'],
  ['Leys, C., Ley, C., Klein, O., Bernard, P. y Licata, L. (2013). Detecting outliers: Do not use standard deviation around the mean, use absolute deviation around the median. Journal of Experimental Social Psychology, 49(4), 764–766.', 'https://doi.org/10.1016/j.jesp.2013.03.013'],
];
refs.forEach(([t, url], i) => add(new d.Paragraph({
  tabStops: [{ type: d.TabStopType.LEFT, position: 540 }], indent: { left: 540, hanging: 540 }, spacing: { after: 80 },
  children: [new d.TextRun({ text: `[${i + 1}]\t${t} `, size: 20 }), new d.ExternalHyperlink({ link: url, children: [new d.TextRun({ text: url, style: 'Hyperlink', size: 20 })] })],
})));
add(P('Guía docente: Trabajo final de Big Data, MCD512, INTEC, Prof. José M. Aquino, marzo de 2026. Se utilizó para definir los entregables y criterios del trabajo.', { spacing: { before: 200, after: 120, line: 276 } }));

// Anexo A
add(H1('Anexo A. Reproducción del laboratorio'));
add(P('Desde la carpeta del proyecto, con Docker Desktop abierto y Rosetta activado, la secuencia completa es la siguiente. Cada comando debe terminar correctamente antes de ejecutar el siguiente; la guía detallada está en `COMO_CORRER.md`.'));
add(code(`python3 docker/lab.py configurar          # contraseñas en docker/.env
python3 docker/lab.py validar
python3 docker/lab.py iniciar sqlserver
python3 docker/lab.py cargar sqlserver
python3 docker/lab.py iniciar oracle
python3 docker/lab.py cargar oracle
python3 docker/lab.py iniciar mongodb
python3 docker/lab.py cargar mongodb
python3 docker/lab.py construir-cliente
python3 docker/lab.py drivers
python3 docker/lab.py verificar sqlserver   # también oracle y mongodb
python3 docker/lab.py integrar             # extracción, análisis, validación y dashboard
python3 docker/lab.py detener              # detiene los gestores conservando los datos`));
add(P('Para ejecutar el análisis sin Docker sobre los CSV ya extraídos se usa un entorno local de Python:'));
add(code(`python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py --usar-exportados`));
add(P('El notebook `Trabajo_final_Big_Data.ipynb` ejecuta las mismas etapas y muestra las figuras; detecta si los datos provienen de los gestores y, en ese caso, no los reemplaza por las muestras.'));

// Anexo B
add(H1('Anexo B. Código fuente y configuración'));
add(H2('B.1 Repositorio'));
add(linkP('El proyecto completo está publicado en ', REPO, '. La tabla resume los archivos principales.'));
add(table(['Archivo', 'Contenido'], [
  ['sql/northwind.sql', 'Consultas de SQL Server por visualización (N01–N10)'],
  ['sql/hr.sql', 'Consultas de Oracle por visualización (H01–H10)'],
  ['mongo/consultas.js', 'Agregaciones de MongoDB por visualización (S01–S10)'],
  ['mongo/preparar_coleccion.js', 'Validador de esquema e índices de la colección'],
  ['src/conexiones.py', 'Verificación de conexiones (ODBC y PyMongo) y extracción de sólo lectura'],
  ['src/analisis.py', 'Preparación analítica y las 30 figuras (PNG y Plotly)'],
  ['src/validar.py', '17 comprobaciones de datos y resultados'],
  ['src/dashboard.py, dashboard_template.html', 'Construcción del dashboard interactivo'],
  ['src/origen.py', 'Registro y comprobación de procedencia por hash'],
  ['run.py', 'Orquestación del análisis: --desde-bd y --usar-exportados'],
  ['Trabajo_final_Big_Data.ipynb', 'Notebook de Jupyter ejecutable'],
  ['docker/compose.yaml, Dockerfile', 'Gestores, volúmenes, puertos y cliente con drivers ODBC'],
  ['docker/lab.py, docker/cliente.py', 'Operación del laboratorio y cadenas de conexión'],
  ['config/.env.example, odbc.ini.example', 'Plantillas de conexión sin credenciales reales'],
  ['requirements.txt, README.md, COMO_CORRER.md', 'Dependencias e instrucciones de instalación y ejecución'],
], [2.6, 3.9]));
add(H2('B.2 Dashboard en línea'));
add(linkP('El dashboard (`dashboard/index.html`) está publicado con GitHub Pages en ', DASH, '. También puede abrirse localmente con doble clic desde la carpeta del proyecto, sin Internet ni servidor.'));

// Anexo C
if (!SIN_ANEXO_C) {
add(H1('Anexo C. Capturas del dashboard'));
add(P('Las capturas siguientes muestran la versión interactiva de cada visualización en el dashboard, con su panel explicativo. Se tomaron en Safari después de la integración con los tres gestores. Cada base comienza con una vista general que incluye el aviso de procedencia, los selectores y sus tres indicadores clave, comunes a sus diez visualizaciones.'));
[['N', 'C.1 SQL Server / Northwind', 'vista_general'], ['H', 'C.2 Oracle / HR', 'vista_hr'], ['S', 'C.3 MongoDB / sensores', 'vista_sensores_s10']].forEach(([prefix, title, overview], g) => {
  add(new d.Paragraph({ heading: d.HeadingLevel.HEADING_2, pageBreakBefore: true, keepNext: true, spacing: { before: 200, after: 120 }, children: [new d.TextRun(title)] }));
  add(figure(dash(overview), `Dashboard: vista general de ${title.slice(4)} con indicadores clave.`, 6.2, 3.5));
  // La vista general ocupa el lugar de una captura: luego, dos detalles por página.
  vizOf(prefix).forEach((v, i) => {
    if (i % 2 === 1) add(new d.Paragraph({ children: [new d.PageBreak()] }));
    add(figure(dash(v.id), `Dashboard: ${v.id} · ${v.title}.`, 6.2, 3.5));
  });
});
}

// ---------- índice ----------
const toc = [
  new d.Paragraph({ heading: d.HeadingLevel.HEADING_1, spacing: { after: 240 }, children: [new d.TextRun('Índice')] }),
  ...headings.map(h => new d.Paragraph({
    tabStops: [{ type: d.TabStopType.RIGHT, position: 9350, leader: d.LeaderType.DOT }], spacing: { after: 110 },
    children: [new d.TextRun({ text: h.text, size: 23 }), new d.TextRun({ text: `\t${PAGES[h.text] ?? '0'}`, size: 23 })],
  })),
];

// ---------- documento ----------
const footer = new d.Footer({ children: [new d.Paragraph({ alignment: d.AlignmentType.CENTER, children: [
  new d.TextRun({ text: 'MCD512 · Dan Carrión (1131022) · ', color: '777777', size: 18 }),
  new d.TextRun({ children: [d.PageNumber.CURRENT], color: '777777', size: 18 }),
] })] });
const page = { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } };
const doc = new d.Document({
  creator: 'Dan Carrión', title: 'Análisis Exploratorio y Visualización de Datos con SQL y NoSQL',
  description: 'Trabajo final MCD512 Big Data',
  styles: {
    default: { document: { run: { font: BODY, size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: HEAD, bold: true, color: NAVY, size: 32 }, paragraph: { outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: HEAD, bold: true, color: BLUE, size: 26 }, paragraph: { outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: HEAD, bold: true, color: GRAY, size: 23 }, paragraph: { outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: 'bullets', levels: [{ level: 0, format: d.LevelFormat.BULLET, text: '•', alignment: d.AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    { reference: 'numbers', levels: [{ level: 0, format: d.LevelFormat.DECIMAL, text: '%1.', alignment: d.AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
  ] },
  sections: [
    { properties: { page }, children: cover },
    { properties: { page: { ...page, pageNumbers: { start: 1 } } }, footers: { default: footer }, children: [...toc, ...body] },
  ],
});
const out = R('informe/salida', `Trabajo_final_Big_Data_Dan_Carrion${process.env.OUT_SUFFIX || ''}.docx`);
fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(R('informe/salida/encabezados.json'), JSON.stringify(headings.map(h => h.text)));
d.Packer.toBuffer(doc).then(b => { fs.writeFileSync(out, b); console.log('Informe Word:', out, '| figuras:', figN); });

"""Ejecutar desde cualquier directorio: python run.py [--desde-bd | --usar-exportados]."""
from pathlib import Path
import argparse, subprocess, sys
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--usar-exportados',action='store_true',help='Conservar CSV de una extracción previa, sin volver a generar muestras')
parser.add_argument('--desde-bd',action='store_true',help='Verificar las tres conexiones y extraer sus datos antes del análisis')
args=parser.parse_args()
if args.desde_bd and args.usar_exportados: parser.error('Usa sólo --desde-bd o --usar-exportados')
if args.desde_bd:
    subprocess.run([sys.executable,str(ROOT/'src/conexiones.py'),'verificar'],cwd=ROOT,check=True)
    for motor in ['sqlserver','oracle','mongodb']:
        subprocess.run([sys.executable,str(ROOT/'src/conexiones.py'),'extraer','--motor',motor],cwd=ROOT,check=True)
steps=[] if args.usar_exportados or args.desde_bd else ['preparar_datos.py']
steps+=['analisis.py','dashboard.py','validar.py']
for script in steps:
    print('Ejecutando',script,flush=True)
    subprocess.run([sys.executable,str(ROOT/'src'/script)],cwd=ROOT,check=True)
print('Terminado. Abre dashboard/index.html.')

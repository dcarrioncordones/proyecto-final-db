"""Ubica la página de cada título de primer nivel en el PDF para completar el índice.

Uso: python informe/paginas_indice.py salida/informe.pdf salida/encabezados.json salida/paginas.json
La portada es una sección aparte; la numeración visible empieza en 1 en la página física 2.
"""
import json, sys
import pymupdf

pdf, titles_file, out = sys.argv[1:4]
doc = pymupdf.open(pdf)
titles = json.load(open(titles_file))
lines = [[l.strip() for l in page.get_text().splitlines()] for page in doc]
pages, start = {}, 2  # después de portada e índice
for title in titles:
    for i in range(start, len(lines)):
        if title in lines[i]:
            pages[title] = i  # índice físico base 0 = número visible
            start = i
            break
    else:
        raise SystemExit(f'No se encontró en el PDF: {title}')
json.dump(pages, open(out, 'w'), ensure_ascii=False, indent=1)
print(pages)

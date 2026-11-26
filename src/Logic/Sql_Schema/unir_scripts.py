"""Genera Biblioteca.sql (script consolidado) uniendo los archivos de EstructuraPorPartes/.

Escribe dos copias idénticas: una junto a las partes y otra en la raíz del repositorio
(la que se ejecuta en la evaluación). Úsalo cada vez que cambies alguna de las partes,
para que el consolidado nunca quede distinto:   python src/Logic/Sql_Schema/unir_scripts.py
"""
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
PARTES = sorted((CARPETA / "EstructuraPorPartes").glob("0*.sql"))
DESTINOS = (CARPETA / "Biblioteca.sql", CARPETA.parents[2] / "Biblioteca.sql")

ENCABEZADO = (
    "-- BIBLIOTECA.SQL: SCRIPT CONSOLIDADO (ESTRUCTURA, PROGRAMACION, DATOS Y SEGURIDAD)\n"
    "-- GENERADO CON unir_scripts.py A PARTIR DE EstructuraPorPartes/. NO EDITAR A MANO.\n"
    "-- EJECUTAR COMPLETO CON UN USUARIO ADMINISTRADOR DE MYSQL (POR EJEMPLO root).\n"
)


def main():
    bloques = [ENCABEZADO]
    for parte in PARTES:
        texto = parte.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
        bloques.append(f"\n-- ============================================================\n"
                       f"-- {parte.name}\n"
                       f"-- ============================================================\n"
                       f"{texto}\n")
    for destino in DESTINOS:
        destino.write_text("".join(bloques), encoding="utf-8", newline="\r\n")
        print(f"Generado {destino} con {len(PARTES)} partes.")


if __name__ == "__main__":
    main()

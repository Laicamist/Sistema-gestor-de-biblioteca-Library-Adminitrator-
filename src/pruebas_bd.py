"""Prueba de humo del backend contra el MySQL real (sin interfaz).

Requisitos: haber ejecutado Biblioteca.sql (o las 4 partes) y tener el .env listo.
Ejecutar desde la raíz del proyecto:   python src/pruebas_bd.py

Deja en la base 1 préstamo ya devuelto y algunos movimientos de auditoría.
Para regresar a los datos iniciales, vuelve a ejecutar Biblioteca.sql.
"""
from ConexionSQL.conexion import Database
from ConexionSQL.dao import DAO
from Logic.sesion_servicio import SesionServicio
from Logic.prestamo_servicio import PrestamoServicio
from Logic.catalogo_servicio import CatalogoServicio
from Logic.reporte_servicio import ReporteServicio
from Logic.alumno_servicio import AlumnoServicio
from Modelos import (
    AccesoDenegadoError, BibliotecaError, DatosInvalidosError, Ejemplar, LoginError, PrestamoError,
)

resultados = []


def revisar(nombre, funcion, espera=None):
    """Ejecuta una prueba. Si 'espera' es una excepción, la prueba pasa cuando se lanza."""
    try:
        valor = funcion()
        ok = espera is None
        detalle = valor if ok else f"se esperaba {espera.__name__} y no hubo error"
    except Exception as e:  # noqa: BLE001 - queremos ver cualquier falla
        ok = espera is not None and isinstance(e, espera)
        detalle = f"{type(e).__name__}: {e}"
    resultados.append(ok)
    print(f"[{'OK ' if ok else 'FALLA'}] {nombre} -> {detalle}")


def sin_guardar(dao, funcion):
    """Ejecuta dentro de una transacción que siempre se deshace: la base no cambia."""
    dao.conn.start_transaction()
    try:
        return funcion()
    finally:
        dao.conn.rollback()


def eliminar_libro_de_prueba(catalogo, reportes):
    """Da de alta un libro con una copia, la da de BAJA y elimina el libro.
    La auditoría debe guardar el borrado de la copia y el del libro."""
    libro = catalogo.registrar_libro("PRUEBA-ELIMINAR", "LIBRO DE PRUEBA", "PRUEBAS", 1)
    catalogo.registrar_ejemplar("PRUEBA-BAJA-01", libro.id_libro, "PASILLO Z")
    catalogo.cambiar_estado_ejemplar("PRUEBA-BAJA-01", "BAJA")
    copias = catalogo.eliminar_libro(libro.id_libro)
    movimientos = [(a.tabla_afectada, a.tipo_operacion) for a in reportes.auditoria(3)]
    if ("EJEMPLARES", "DELETE") not in movimientos or ("LIBROS", "DELETE") not in movimientos:
        raise AssertionError(f"la auditoría no registró los borrados: {movimientos}")
    return f"{copias} copia en BAJA borrada con el libro; auditoría: {movimientos[:2]}"


def main():
    # 1. Conexión con cada usuario de MySQL
    for perfil in ("LOGIN", "ADMINISTRADOR", "BIBLIOTECARIO", "CONSULTA"):
        revisar(f"Conectar con el perfil {perfil}",
                lambda p=perfil: Database(p).close() or "conectado")

    dao = DAO()
    sesiones = SesionServicio(dao)
    prestamos = PrestamoServicio(dao, sesiones)
    catalogo = CatalogoServicio(dao, sesiones)
    reportes = ReporteServicio(dao, sesiones)
    alumnos = AlumnoServicio(dao, sesiones)

    # 2. Login (SP_LOGIN con OUT) y hash SHA-256
    revisar("Contraseña incorrecta", lambda: sesiones.iniciar_sesion("BCHAVEZ", "MALA"), LoginError)
    revisar("Cuenta inactiva (MRUIZ)", lambda: sesiones.iniciar_sesion("MRUIZ", "MRUIZ123"), LoginError)
    revisar("Login administrador", lambda: sesiones.iniciar_sesion("BCHAVEZ", "ADMIN123"))
    revisar("@USUARIO_APP en la conexión",
            lambda: dao._consultar_uno("SELECT @USUARIO_APP AS u")["u"])

    # 3. Lector: consulta por código (SP_CONSULTAR_EJEMPLAR + FN_EJEMPLAR_DISPONIBLE)
    revisar("Escanear ejemplar prestado",
            lambda: (lambda e: f"{e.titulo} | {e.estado} | prestado a {e.prestado_a}")(
                prestamos.consultar_ejemplar("7501000000011")))
    revisar("Escanear código inexistente",
            lambda: prestamos.consultar_ejemplar("0000000000000"), BibliotecaError)

    # 4. Transacción de préstamo y triggers de validación
    revisar("Préstamo válido (LUIS, 7501000000012)",
            lambda: prestamos.prestar("7501000000012", "22120002"))
    revisar("Trigger: ejemplar ya prestado",
            lambda: prestamos.prestar("7501000000012", "23120003"), PrestamoError)
    revisar("Trigger: alumno con 3 préstamos (ANA)",
            lambda: prestamos.prestar("7501000000072", "22120001"), PrestamoError)
    revisar("Trigger: alumno inactivo (RICARDO)",
            lambda: prestamos.prestar("7501000000072", "20120004"), PrestamoError)
    revisar("Ejemplar en mantenimiento no se presta",
            lambda: prestamos.prestar("7501000000112", "22120002"), PrestamoError)
    revisar("Disponibilidad (SP con OUT) del libro 1", lambda: catalogo.disponibilidad(1))

    # 5. Transacción de devolución
    revisar("Devolución (días de retraso)", lambda: prestamos.devolver("7501000000012"))
    revisar("Devolver otra vez el mismo ejemplar",
            lambda: prestamos.devolver("7501000000012"), PrestamoError)
    revisar("Devolución con retraso (vencido 19 días)", lambda: prestamos.devolver("7501000000011"))

    # 6. Trigger de código de barras vacío (se manda directo al DAO para saltar la validación de Python)
    revisar("Trigger: código de barras vacío",
            lambda: dao.agregar_ejemplar(Ejemplar("   ", 1, "PASILLO A")), DatosInvalidosError)

    # 7. Auditoría con el usuario de la app
    revisar("Auditoría registra a BCHAVEZ",
            lambda: [(a.tabla_afectada, a.tipo_operacion, a.usuario_responsable)
                     for a in reportes.auditoria(4)])

    # 8. Reportes y funciones
    revisar("Reporte préstamos vencidos", lambda: f"{len(reportes.prestamos_vencidos())} filas")
    revisar("Reporte alumnos con vencidos (CTE)", lambda: f"{len(reportes.alumnos_con_vencidos())} filas")
    revisar("Reporte libros más solicitados", lambda: f"{len(reportes.libros_mas_solicitados())} filas")
    revisar("Resumen de inicio (V_RESUMEN)",
            lambda: (lambda r: f"{r.prestamos_activos} activos, {r.prestamos_vencidos} vencidos, "
                               f"{r.ejemplares_disponibles}/{r.total_ejemplares} ejemplares disponibles")(
                reportes.resumen()))
    revisar("Función en consulta: FN_DISPONIBLES_LIBRO(1)",
            lambda: dao._consultar_uno("SELECT FN_DISPONIBLES_LIBRO(1) AS d")["d"])

    # 9. Permisos reales de MySQL (no solo de Python)
    sesiones.cerrar_sesion()
    sesiones.iniciar_sesion("IPEREZ", "CONS123")
    revisar("CONSULTA no puede leer USUARIOS en MySQL",
            lambda: dao._consultar("SELECT * FROM USUARIOS"), AccesoDenegadoError)
    revisar("CONSULTA sí puede ver el resumen de inicio",
            lambda: f"{reportes.resumen().prestamos_activos} préstamos activos")
    revisar("CONSULTA no puede registrar préstamos (app)",
            lambda: prestamos.prestar("7501000000012", "22120002"), AccesoDenegadoError)
    sesiones.cerrar_sesion()
    sesiones.iniciar_sesion("OALVAREZ", "BIBLIO123")
    revisar("BIBLIOTECARIO lista alumnos con préstamos activos y vencidos",
            lambda: [(a.matricula, a.prestamos_activos, a.prestamos_vencidos) for a in alumnos.listar()][:3])
    revisar("Historial de ANA (SP_HISTORIAL_ALUMNO)",
            lambda: f"{len(prestamos.historial('22120001'))} préstamos")
    revisar("BIBLIOTECARIO guarda un libro sin cambios",
            lambda: (lambda l: catalogo.actualizar_libro(l.id_libro, l.isbn, l.titulo, l.autor, l.id_categoria,
                                                         l.editorial, l.anio).titulo)(catalogo.listar_libros()[0]))
    revisar("BIBLIOTECARIO no puede insertar préstamos sin el SP",
            lambda: dao._ejecutar("INSERT INTO PRESTAMOS (ID_EJEMPLAR, ID_ALUMNO, ID_USUARIO, "
                                  "FECHA_PRESTAMO, FECHA_LIMITE) VALUES (2, 2, 2, CURDATE(), CURDATE())"),
            AccesoDenegadoError)
    sesiones.cerrar_sesion()
    sesiones.iniciar_sesion("BCHAVEZ", "ADMIN123")
    revisar("ADMINISTRADOR no puede borrar la auditoría",
            lambda: dao._ejecutar("DELETE FROM AUDITORIA"), AccesoDenegadoError)

    # 10. Eliminar libro: sus copias en BAJA se borran con él (transacción + auditoría)
    revisar("No se elimina un libro con copias en uso (libro 1)",
            lambda: catalogo.eliminar_libro(1), DatosInvalidosError)
    revisar("No se elimina un libro con préstamos aunque sus copias estén en BAJA",
            lambda: sin_guardar(dao, lambda: (
                dao._ejecutar("UPDATE EJEMPLARES SET estado = 'BAJA' WHERE codigo_barras = '7501000000151'"),
                catalogo.eliminar_libro(8))),
            DatosInvalidosError)
    revisar("Trigger: MySQL no borra un ejemplar que no está en BAJA",
            lambda: sin_guardar(dao, lambda: dao._ejecutar(
                "DELETE FROM EJEMPLARES WHERE codigo_barras = '7501000000051'")),
            DatosInvalidosError)
    revisar("Eliminar libro con todas sus copias en BAJA",
            lambda: eliminar_libro_de_prueba(catalogo, reportes))
    sesiones.cerrar_sesion()
    revisar("El usuario de LOGIN no puede leer USUARIOS ni los hashes",
            lambda: dao._consultar("SELECT * FROM USUARIOS"), AccesoDenegadoError)

    dao.cerrar()
    print(f"\n{sum(resultados)} de {len(resultados)} pruebas correctas.")


if __name__ == "__main__":
    main()

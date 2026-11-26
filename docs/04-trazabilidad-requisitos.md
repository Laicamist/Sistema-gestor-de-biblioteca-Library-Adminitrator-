# Trazabilidad: dónde se cumple cada requisito

Para cada requisito de la guía del proyecto: qué objeto de la base o qué parte del código lo cumple, dónde se ve en la aplicación y cómo demostrarlo. Los scripts SQL están en `src/Logic/Sql_Schema/EstructuraPorPartes/`:
- `01` estructura.
- `02` programación: funciones, triggers, procedimientos y vistas.
- `03` datos de prueba.
- `04` seguridad.

## A. Diseño y construcción de la base de datos

| Requisito | Dónde se cumple |
| --- | --- |
| Entidades | 9 tablas: ROLES, USUARIOS, CARRERAS, ALUMNOS, CATEGORIAS, LIBROS, EJEMPLARES, PRESTAMOS, AUDITORIA (`01_estructura.sql`). Descripción en [03-modelo-de-datos.md](03-modelo-de-datos.md). |
| Diagrama entidad-relación | [03-modelo-de-datos.md](03-modelo-de-datos.md) (Mermaid) y [diagrama-er.png](diagrama-er.png). |
| Tablas y relaciones | 7 relaciones 1:N con llave foránea; PRESTAMOS resuelve la relación N:M entre ALUMNOS y EJEMPLARES. |
| Llaves primarias y foráneas | `PRIMARY KEY AUTO_INCREMENT` en todas; `FOREIGN KEY` en USUARIOS, ALUMNOS, LIBROS, EJEMPLARES y PRESTAMOS. |
| Restricciones de integridad | `UNIQUE`, `CHECK` (semestre 1–12, año > 0, fecha límite ≥ fecha de préstamo, código no vacío), `ENUM`, `NOT NULL`, `DEFAULT`. Lista completa en la sección 5 de [03-modelo-de-datos.md](03-modelo-de-datos.md). |
| Implementación en SQL | `01_estructura.sql`; todo junto en `Biblioteca.sql`. |
| Datos de prueba | `03_datos_prueba.sql`: 4 usuarios (uno inactivo), 8 alumnos (uno inactivo), 10 libros, 18 ejemplares en los 4 estados, 15 préstamos devueltos y 7 activos (3 vencidos). ANA queda con 3 préstamos activos para demostrar el límite. Las fechas son relativas a `CURDATE()`, así que los vencidos siempre lo están. |

## B. Lector de código de barras

| Requisito | Dónde se cumple |
| --- | --- |
| Código guardado en una columna con restricción contra duplicados | `EJEMPLARES.CODIGO_BARRAS VARCHAR(30) NOT NULL UNIQUE` + `CHECK` de no vacío + `TRG_VAL_EJEMPLARES_BI/BU`. Un duplicado llega a la app como el aviso "Ya existe un registro con ese valor (…)" (error 1062 traducido en `DAO._traducir`). |
| Buscar o consultar por código | Lector → Consultar → `SP_CONSULTAR_EJEMPLAR`. |
| Préstamo y devolución | Lector → Prestar (ejemplar + credencial) y Devolver. |
| Registrar la entrada de un artículo | Lector → Alta de ejemplar (INSERT en EJEMPLARES). |
| Identificar a un alumno | Credencial escaneada en Prestar y en el buscador de Alumnos (`MATRICULA UNIQUE`). |
| Cómo funciona | El lector es un teclado HID: escribe el código y manda Enter; `returnPressed` del campo dispara la operación (`UI/pantallas/lector.py`). |
| Demostración física | Guion y etiquetas en [05-evidencias-lector.md](05-evidencias-lector.md). |

## C. Tabla de usuarios y seguridad

| Requisito | Dónde se cumple |
| --- | --- |
| Identificador, nombre completo, nombre de usuario, hash, rol y estado | Tabla USUARIOS: `ID_USUARIO`, `NOMBRE_COMPLETO`, `NOMBRE_USUARIO` (UNIQUE), `CONTRASENA_HASH CHAR(64)`, `ID_ROL` (FK a ROLES), `ESTADO_CUENTA`. |
| Inicio de sesión | Pantalla de login → `SesionServicio.iniciar_sesion` → `SP_LOGIN` (IN usuario y hash; OUT id, rol y mensaje). |
| No guardar contraseñas en texto plano | `Logic/seguridad.py`: `hashear()` con SHA-256; solo el hash llega a MySQL. El trigger de auditoría de USUARIOS nunca guarda el hash, solo si cambió. |
| Algoritmo adecuado | SHA-256, de la familia SHA-2 que pide la guía. |
| Roles diferentes | ROLES: ADMINISTRADOR, BIBLIOTECARIO y CONSULTA. Los permisos de cada uno están en `config.PERMISOS`. |
| Restringir por rol en la aplicación | La barra lateral solo muestra los módulos permitidos y cada método de servicio llama a `_exigir(permiso)`, que lanza `AccesoDenegadoError`. |
| Restringir por rol en MySQL | `04_seguridad.sql`: un usuario de MySQL por rol (`BIB_ADMIN`, `BIB_BIBLIOTECARIO`, `BIB_CONSULTA`) más `BIB_LOGIN`, que solo puede ejecutar `SP_LOGIN`. Al iniciar sesión la app se reconecta con el usuario del rol (`Database(perfil)`). |
| Evitar operaciones no autorizadas | Ejemplos que comprueba `pruebas_bd.py`: CONSULTA no puede leer USUARIOS, el bibliotecario no puede insertar en PRESTAMOS sin el procedimiento y ni el administrador puede borrar la auditoría. |

## D. Transacciones

| Requisito | Dónde se cumple |
| --- | --- |
| `START TRANSACTION` / `COMMIT` / `ROLLBACK` | `SP_REGISTRAR_PRESTAMO` y `SP_REGISTRAR_DEVOLUCION` (`02_programacion.sql`). |
| Varias modificaciones relacionadas | Préstamo: INSERT en PRESTAMOS + UPDATE del ejemplar a PRESTADO. Devolución: UPDATE del préstamo a DEVUELTO con fecha + UPDATE del ejemplar a DISPONIBLE. |
| Cuándo se usa `ROLLBACK` | `DECLARE EXIT HANDLER FOR SQLEXCEPTION` hace `ROLLBACK` si falla cualquier sentencia, incluido un `SIGNAL` de los triggers. También hay `ROLLBACK` explícito si el código no existe o no hay préstamo activo. |
| Concurrencia | `SELECT ... FOR UPDATE` bloquea la fila del ejemplar durante la transacción. |
| Uso desde la app | Lector → Prestar / Devolver → `PrestamoServicio.prestar` / `devolver` → `DAO.registrar_prestamo` / `registrar_devolucion`. |
| Cómo demostrar el ROLLBACK | Prestar `7501000000072` a la matrícula `22120001` (ANA ya tiene 3): el trigger lanza el error, la transacción se cancela y el ejemplar sigue DISPONIBLE. |
| Transacción desde Python | Eliminar libro (`DAO.eliminar_libro`): `start_transaction`, borra sus copias en BAJA y el libro, y `commit`; si una llave foránea o un trigger lo rechaza, `rollback` y no se borra nada. |

## E. Procedimientos almacenados (7)

| Procedimiento | Parámetros | Modifica | Dónde lo usa la app |
| --- | --- | --- | --- |
| `SP_LOGIN` | IN usuario, hash · **OUT** id, rol, mensaje | No | Login |
| `SP_CONSULTAR_EJEMPLAR` | IN código | No | Lector (todos los modos), cambio de ubicación y de estado |
| `SP_REGISTRAR_PRESTAMO` | IN código, alumno, usuario, días · **OUT** mensaje | **INSERT + UPDATE** (transacción) | Lector → Prestar |
| `SP_REGISTRAR_DEVOLUCION` | IN código · **OUT** días de retraso, mensaje | **UPDATE + UPDATE** (transacción) | Lector → Devolver |
| `SP_DISPONIBILIDAD_LIBRO` | IN libro · **OUT** total, disponibles | No | Catálogo → panel de ejemplares |
| `SP_CAMBIAR_UBICACION` | IN código, ubicación | **UPDATE** (dispara la auditoría) | Catálogo → Cambiar ubicación |
| `SP_HISTORIAL_ALUMNO` | IN matrícula | No | Alumnos → historial |

Se cumplen los tres requisitos: con parámetros de entrada (todos), con parámetros de salida (4) y con inserción o actualización (3). Todos se llaman desde `ConexionSQL/dao.py` con `callproc`.

## F. Funciones (3)

| Función | Qué calcula | Dónde se usa |
| --- | --- | --- |
| `FN_DIAS_RETRASO(id_prestamo)` | Días de retraso; 0 si no hay | Vistas `V_PRESTAMOS_VENCIDOS` y `V_ALUMNOS_CON_VENCIDOS`; procedimientos `SP_HISTORIAL_ALUMNO` y `SP_REGISTRAR_DEVOLUCION` |
| `FN_DISPONIBLES_LIBRO(id_libro)` | Copias disponibles de un libro | Vista `V_DISPONIBILIDAD`; procedimientos `SP_CONSULTAR_EJEMPLAR` y `SP_DISPONIBILIDAD_LIBRO` |
| `FN_EJEMPLAR_DISPONIBLE(código)` | 1 si la copia está disponible, 0 si no | `SP_CONSULTAR_EJEMPLAR` (la ficha del lector se pinta en verde o rojo) |

## G. Triggers de validación (5)

| Trigger | Cuándo | Qué impide |
| --- | --- | --- |
| `TRG_VAL_EJEMPLARES_BI` | BEFORE INSERT en EJEMPLARES | Código de barras vacío o nulo |
| `TRG_VAL_EJEMPLARES_BU` | BEFORE UPDATE en EJEMPLARES | Dejar vacío el código de barras |
| `TRG_VAL_EJEMPLARES_BD` | BEFORE DELETE en EJEMPLARES | Borrar una copia que no está en BAJA (solo se borran al eliminar su libro) |
| `TRG_VAL_PRESTAMOS_BI` | BEFORE INSERT en PRESTAMOS | Prestar un ejemplar que no está DISPONIBLE, a un alumno INACTIVO o con 3 préstamos activos |
| `TRG_VAL_PRESTAMOS_BU` | BEFORE UPDATE en PRESTAMOS | Modificar un préstamo ya devuelto o poner una devolución anterior al préstamo |

Todos usan `SIGNAL SQLSTATE '45000'`. El DAO convierte el error 1644 en un error de negocio con el mensaje del trigger, y la app lo muestra en un aviso rojo. En los préstamos, el procedimiento atrapa ese error, hace `ROLLBACK` y regresa el mensaje en su parámetro OUT (`ERROR: ...`).

## H. Triggers de auditoría (9) y tabla AUDITORIA

| Requisito | Dónde se cumple |
| --- | --- |
| Tabla con id, tabla, operación, fecha y hora, usuario, datos anteriores y nuevos | AUDITORIA: `ID_MOVIMIENTO`, `TABLA_AFECTADA`, `TIPO_OPERACION`, `FECHA_HORA`, `USUARIO_RESPONSABLE`, `DATOS_ANTERIORES` (JSON), `DATOS_NUEVOS` (JSON). |
| Triggers | `TRG_AUD_EJEMPLARES_AI`, `_AU` y `_AD`, `TRG_AUD_PRESTAMOS_AI` y `_AU`, `TRG_AUD_LIBROS_AD`, `TRG_AUD_ALUMNOS_AU`, `TRG_AUD_USUARIOS_AI` y `_AU`. Cubren INSERT, UPDATE y DELETE. |
| Usuario responsable | Después del login la app ejecuta `SET @USUARIO_APP = '<usuario>'` (`DAO.establecer_usuario_app`). Los triggers usan `COALESCE(@USUARIO_APP, USER())`, así que un cambio hecho fuera de la app también queda con el usuario de MySQL. |
| Ejemplo de la guía (ubicación anterior y nueva) | Catálogo → Cambiar ubicación → `SP_CAMBIAR_UBICACION` → `TRG_AUD_EJEMPLARES_AU` guarda la ubicación anterior y la nueva. |
| Dónde se ve | Pantalla Auditoría (solo administrador), con detalle antes/después. La bitácora es de solo lectura incluso para `BIB_ADMIN`. |

## I. Reportes y consultas avanzadas

| Reporte (vista) | Características de la guía que usa |
| --- | --- |
| Préstamos vencidos (`V_PRESTAMOS_VENCIDOS`) | JOIN de 5 tablas, función almacenada |
| Alumnos con retraso (`V_ALUMNOS_CON_VENCIDOS`) | **CTE** (`WITH`), JOIN de 3 tablas, `COUNT`/`SUM`/`MAX`, `GROUP BY`, función de ventana `RANK()` |
| Libros más solicitados (`V_LIBROS_MAS_SOLICITADOS`) | JOIN de 4 tablas, `COUNT`, `GROUP BY`, **`HAVING`** (≥ 2 préstamos), `RANK()` |
| Libros sin préstamos (`V_LIBROS_SIN_PRESTAMOS`) | **`NOT EXISTS`** con subconsulta correlacionada |
| Disponibilidad (`V_DISPONIBILIDAD`) | Subconsulta escalar, función almacenada |
| Resumen de inicio (`V_RESUMEN`) | Subconsultas escalares, `COUNT`, `COUNT(DISTINCT)` |

Se usan las 8 características de la lista (la guía pide al menos 3). Los reportes que pide la guía para una biblioteca, libros más solicitados y alumnos con préstamos vencidos, son los dos primeros. Todos se **presentan en la aplicación**: pantalla Reportes, con filtro y exportación a CSV, y el resumen en Inicio.

## 4. Requisitos de la aplicación

| Requisito | Dónde se cumple |
| --- | --- |
| Inicio de sesión | `UI/pantallas/login.py` |
| Menú principal | `UI/ventana_principal.py`: barra lateral con los módulos del rol y pantalla de inicio (`inicio.py`) |
| Módulos para administrar los registros | Catálogo (libros y ejemplares), Alumnos, Usuarios: alta, consulta, edición y baja |
| Búsquedas mediante código de barras | Lector (ejemplares), buscador del Catálogo (ISBN) y de Alumnos (credencial) |
| Operaciones con procedimientos almacenados | Los 7 procedimientos de la sección E |
| Visualización de los reportes | Reportes e Inicio |
| Mensajes de error y confirmación | Avisos verde, rojo, ámbar e informativo en cada pantalla; ventana de confirmación para eliminar, dar de baja, desactivar y cambiar rol; tonos del lector |
| Restricciones de acceso según el rol | Sección C (aplicación + MySQL) |
| Operaciones reales, no simuladas | Todo pasa por MySQL; `pruebas_bd.py` lo comprueba contra la base real (39 casos) |

## Usuarios de prueba

| Usuario | Contraseña | Rol |
| --- | --- | --- |
| BCHAVEZ | ADMIN123 | Administrador |
| OALVAREZ | BIBLIO123 | Bibliotecario |
| IPEREZ | CONS123 | Consulta |
| MRUIZ | MRUIZ123 | Bibliotecario (cuenta inactiva) |

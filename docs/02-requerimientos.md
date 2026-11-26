# Requerimientos del sistema

Roles: **ADM** = administrador, **BIB** = bibliotecario, **CON** = consulta. Los permisos de cada rol están en `src/config.py` (`PERMISOS`) y en `04_seguridad.sql`.

## Requerimientos funcionales

### Seguridad y acceso
| ID | Requerimiento | Roles | Cómo se cumple |
| --- | --- | --- | --- |
| RF-01 | Iniciar sesión con nombre de usuario y contraseña. | Todos | Pantalla de login → `SP_LOGIN` (parámetros IN y OUT). |
| RF-02 | Rechazar credenciales incorrectas y cuentas inactivas con un mensaje claro. | Todos | `SP_LOGIN` regresa el mensaje; usuario de prueba MRUIZ inactivo. |
| RF-03 | Mostrar solo los módulos que el rol del usuario puede usar. | Todos | Barra lateral filtrada por `config.PERMISOS`. |
| RF-04 | Impedir operaciones no autorizadas aunque se intenten por otro camino. | Todos | Cada servicio revisa el permiso (`_exigir`) y MySQL lo vuelve a revisar con el usuario de base de datos del rol. |
| RF-05 | Cerrar sesión y volver al login. | Todos | Botón "Cerrar sesión". |

### Lector de código de barras
| ID | Requerimiento | Roles | Cómo se cumple |
| --- | --- | --- | --- |
| RF-06 | Consultar un ejemplar escaneando su etiqueta: libro, ubicación, estado, a quién está prestado y si está vencido. | Todos | Lector → Consultar → `SP_CONSULTAR_EJEMPLAR` + `FN_EJEMPLAR_DISPONIBLE`. |
| RF-07 | Registrar un préstamo escaneando el ejemplar y la credencial del alumno (o escribiendo la matrícula). | ADM, BIB | Lector → Prestar → `SP_REGISTRAR_PRESTAMO` (transacción). |
| RF-08 | Registrar una devolución escaneando el ejemplar e informar los días de retraso. | ADM, BIB | Lector → Devolver → `SP_REGISTRAR_DEVOLUCION` (transacción) + `FN_DIAS_RETRASO`. |
| RF-09 | Dar de alta un ejemplar nuevo escaneando su etiqueta, sin permitir códigos repetidos ni vacíos. | ADM, BIB | Lector → Alta de ejemplar; `UNIQUE` en `CODIGO_BARRAS` y `TRG_VAL_EJEMPLARES_BI`. |
| RF-10 | Buscar un libro escaneando su ISBN y a un alumno escaneando su credencial. | ADM, BIB | Buscadores de Catálogo y Alumnos. |

### Catálogo
| ID | Requerimiento | Roles | Cómo se cumple |
| --- | --- | --- | --- |
| RF-11 | Registrar y editar libros (ISBN único, título, autor, editorial, año, categoría). | ADM, BIB | Catálogo → formulario de libro. |
| RF-12 | Eliminar un libro sin ejemplares o con todas sus copias dadas de BAJA (se borran con él), siempre que sus copias no tengan préstamos en el historial. | ADM | Catálogo → Eliminar: validación en Python, transacción en el DAO, llaves foráneas y `TRG_VAL_EJEMPLARES_BD`; queda en auditoría (`TRG_AUD_EJEMPLARES_AD`, `TRG_AUD_LIBROS_AD`). |
| RF-13 | Crear categorías. | ADM | Formulario de libro → "Nueva categoría". |
| RF-14 | Ver las copias de un libro y cuántas están disponibles. | ADM, BIB | Panel de ejemplares → `SP_DISPONIBILIDAD_LIBRO` (OUT). |
| RF-15 | Cambiar la ubicación de un ejemplar, registrando la anterior y la nueva. | ADM, BIB | `SP_CAMBIAR_UBICACION` + `TRG_AUD_EJEMPLARES_AU`. |
| RF-16 | Cambiar el estado de un ejemplar a disponible, mantenimiento o baja (no si está prestado). | ADM, BIB | Panel de ejemplares; baja con confirmación. |

### Alumnos
| ID | Requerimiento | Roles | Cómo se cumple |
| --- | --- | --- | --- |
| RF-17 | Registrar y editar alumnos (matrícula única, carrera, semestre 1–12, correo, teléfono). | ADM, BIB | Alumnos → formulario de alumno. |
| RF-18 | Dar de baja a un alumno solo si no tiene libros sin devolver, y reactivarlo. | ADM, BIB | Alumnos → Dar de baja / Reactivar (`TRG_AUD_ALUMNOS_AU`). |
| RF-19 | Ver el historial de préstamos de un alumno con fechas, estado y días de retraso. | ADM, BIB | Ficha del alumno → `SP_HISTORIAL_ALUMNO`. |
| RF-20 | Crear carreras. | ADM | Formulario de alumno → "Nueva carrera". |

### Reglas del préstamo (las aplica la base de datos)
| ID | Requerimiento | Cómo se cumple |
| --- | --- | --- |
| RF-21 | Solo se presta un ejemplar en estado DISPONIBLE. | `TRG_VAL_PRESTAMOS_BI` |
| RF-22 | Un alumno inactivo no puede pedir libros. | `TRG_VAL_PRESTAMOS_BI` |
| RF-23 | Un alumno puede tener como máximo 3 préstamos activos. | `TRG_VAL_PRESTAMOS_BI` |
| RF-24 | El préstamo dura 7 días por omisión. | `SP_REGISTRAR_PRESTAMO` (`P_DIAS`) y `config.DIAS_PRESTAMO` |
| RF-25 | Un préstamo devuelto no se puede volver a modificar, y la devolución no puede ser anterior al préstamo. | `TRG_VAL_PRESTAMOS_BU` |
| RF-26 | Préstamo y cambio de estado del ejemplar se guardan juntos o no se guarda nada. | Transacción con `START TRANSACTION`, `COMMIT` y `ROLLBACK` en los procedimientos. |

### Reportes, auditoría y usuarios
| ID | Requerimiento | Roles | Cómo se cumple |
| --- | --- | --- | --- |
| RF-27 | Ver un resumen del día: préstamos activos y vencidos, alumnos con retraso, ejemplares disponibles y alumnos activos. | Todos | Inicio → `V_RESUMEN`. |
| RF-28 | Reporte de préstamos vencidos y de alumnos con retraso (ranking). | Todos | `V_PRESTAMOS_VENCIDOS`, `V_ALUMNOS_CON_VENCIDOS`. |
| RF-29 | Reporte de libros más solicitados, disponibilidad por libro y libros sin préstamos. | Todos | `V_LIBROS_MAS_SOLICITADOS`, `V_DISPONIBILIDAD`, `V_LIBROS_SIN_PRESTAMOS`. |
| RF-30 | Filtrar y exportar los reportes a CSV. | Todos | Pantalla de reportes. |
| RF-31 | Consultar la bitácora de auditoría con el detalle antes y después de cada cambio. | ADM | Pantalla de auditoría. |
| RF-32 | Crear usuarios, cambiar su rol, activarlos o desactivarlos y restablecer su contraseña; nadie puede quitarse su propio rol ni desactivarse. | ADM | Pantalla de usuarios (`TRG_AUD_USUARIOS_AI/AU`). |

## Requerimientos no funcionales

| ID | Tipo | Requerimiento |
| --- | --- | --- |
| RNF-01 | Seguridad | Las contraseñas se guardan como hash SHA-256 (64 caracteres hexadecimales); nunca en texto plano ni en la auditoría. Las nuevas deben tener al menos 8 caracteres con letras y números. |
| RNF-02 | Seguridad | Cada rol se conecta a MySQL con su propio usuario y permisos mínimos (`GRANT`). El usuario de login solo puede ejecutar `SP_LOGIN`, y los préstamos solo se modifican a través de los procedimientos. |
| RNF-03 | Seguridad | La auditoría es de solo lectura para todos los usuarios de la aplicación; solo la escriben los triggers. |
| RNF-04 | Integridad | Llaves primarias y foráneas, `UNIQUE`, `CHECK`, `ENUM` y `NOT NULL` en todas las tablas; reglas de negocio en triggers que lanzan `SIGNAL SQLSTATE '45000'`. |
| RNF-05 | Integridad | Las operaciones de varias modificaciones se hacen en transacción y bloquean la fila del ejemplar (`SELECT ... FOR UPDATE`) para que dos préstamos simultáneos no tomen la misma copia. |
| RNF-06 | Usabilidad | El lector se usa como teclado: después de cada lectura el campo recupera el foco, y hay un tono distinto para éxito y para error. |
| RNF-07 | Usabilidad | Mensajes de error y confirmación en español dentro de la pantalla. Las acciones peligrosas (eliminar, dar de baja, desactivar) piden confirmación. |
| RNF-08 | Usabilidad | Interfaz en español con tema claro y oscuro; el tema y el sonido elegidos se recuerdan entre sesiones. |
| RNF-09 | Rendimiento | Una lectura del lector se resuelve con una sola llamada a un procedimiento sobre columnas indexadas (`UNIQUE`), en menos de un segundo con la base local. |
| RNF-10 | Mantenibilidad | Código en capas (interfaz, servicios, acceso a datos y modelos); solo el DAO ejecuta SQL. Cada pantalla vive en su propio archivo. |
| RNF-11 | Portabilidad | Funciona en Windows con Python 3.10 o superior y MySQL 8.0. La conexión se configura en un archivo `.env`, sin contraseñas escritas en el código. |
| RNF-12 | Confiabilidad | Si MySQL no está disponible al abrir la aplicación, muestra el error y permite reintentar la conexión desde el login. Cualquier error de la base se muestra como aviso y nunca cierra la aplicación. |
| RNF-13 | Verificabilidad | `src/pruebas_bd.py` comprueba contra la base real el login, las transacciones, los triggers, la auditoría, los reportes y los permisos de MySQL (39 casos). |

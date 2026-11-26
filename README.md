# Library Administrator · Sistema gestor de biblioteca

Proyecto final de **Taller de Bases de Datos** (ITSUR, 2026). Aplicación de escritorio en **Python + PySide6** conectada a **MySQL 8** para administrar los préstamos de una biblioteca escolar. Cada ejemplar físico tiene su propio código de barras, y el **lector de código de barras** se usa para consultar, prestar, devolver y dar de alta ejemplares. Las credenciales de los alumnos también se leen con el lector.

No es un punto de venta: no hay ventas ni cobros, solo control de préstamos, ejemplares y alumnos.

## Qué hace

| Módulo | Qué se puede hacer | Roles |
| --- | --- | --- |
| Inicio de sesión | Usuario y contraseña; la contraseña viaja como hash SHA-256 a `SP_LOGIN` | Todos |
| Inicio | Resumen del día (`V_RESUMEN`), préstamos vencidos, libros más pedidos y accesos rápidos | Todos |
| Lector | Consultar un ejemplar, prestar (ejemplar + credencial), devolver y dar de alta etiquetas nuevas | Consultar: todos · lo demás: administrador y bibliotecario |
| Catálogo | Libros (alta, edición, baja), ejemplares, ubicación, estado y disponibilidad | Administrador y bibliotecario |
| Alumnos | Alta, edición, baja y reactivación; historial de préstamos de cada alumno | Administrador y bibliotecario |
| Reportes | 5 reportes desde vistas SQL, con filtro y exportación a CSV | Todos |
| Auditoría | Bitácora que llenan los triggers, con detalle antes/después | Administrador |
| Usuarios | Cuentas del personal: alta, rol, activar/desactivar y contraseña | Administrador |

Las restricciones por rol se aplican **dos veces**: en la aplicación (cada servicio revisa el permiso) y en MySQL (cada rol se conecta con su propio usuario de base de datos con `GRANT` limitados).

## Requisitos

- Python 3.10 o superior.
- MySQL Server 8.0 y MySQL Workbench 8.0.
- Un lector de código de barras USB que funcione como teclado (HID) y mande Enter al final de cada lectura. Es la configuración de fábrica de casi todos.

## Instalación

1. **Base de datos.** En MySQL Workbench, conectado como `root`, abre y ejecuta completo **`Biblioteca.sql`** (en la raíz del repositorio). Crea la base `BIBLIOTECA`, las tablas, funciones, triggers, procedimientos, vistas, los datos de prueba y los usuarios de MySQL con sus permisos.
   - El mismo script está dividido en `src/Logic/Sql_Schema/EstructuraPorPartes/` (01 estructura, 02 programación, 03 datos de prueba, 04 seguridad). Si cambias una parte, regenera el consolidado con `python src/Logic/Sql_Schema/unir_scripts.py`.
   - Para regresar a los datos iniciales (por ejemplo, antes de la presentación), vuelve a ejecutar `Biblioteca.sql`.
2. **Dependencias.**
   ```bash
   pip install -r requirements.txt
   ```
3. **Conexión.** Copia `.env_Ejemplo` como `.env` en la raíz. Las contraseñas de los usuarios de MySQL ya coinciden con las de `04_seguridad.sql`; solo cambia el host o el puerto si tu servidor no usa los de siempre.
4. **Ejecutar** desde la raíz del proyecto:
   ```bash
   python src/main.py
   ```
5. **Prueba del backend (opcional).** `python src/pruebas_bd.py` revisa la base real sin interfaz: login, transacciones, triggers, auditoría, reportes y permisos de MySQL. Debe terminar con **35 de 35 pruebas correctas**. Deja movimientos en la base, así que después vuelve a ejecutar `Biblioteca.sql`.

## Usuarios de prueba

| Usuario | Contraseña | Rol | Nota |
| --- | --- | --- | --- |
| BCHAVEZ | ADMIN123 | Administrador | Acceso total |
| OALVAREZ | BIBLIO123 | Bibliotecario | Préstamos, catálogo y alumnos |
| IPEREZ | CONS123 | Consulta | Solo consulta y reportes |
| MRUIZ | MRUIZ123 | Bibliotecario | Cuenta **inactiva**: sirve para mostrar el rechazo del login |

Usuarios de MySQL que crea `04_seguridad.sql`: `BIB_LOGIN` (solo ejecuta `SP_LOGIN`), `BIB_ADMIN`, `BIB_BIBLIOTECARIO` y `BIB_CONSULTA`. Antes del login, la aplicación se conecta con el usuario de `DB_USER_LOGIN` del `.env` (`BIB_LOGIN`, o `BIB_CONSULTA`, que también puede ejecutar `SP_LOGIN`). Al iniciar sesión se reconecta con el usuario de MySQL de su rol.

## Lector de código de barras

El lector escribe el código en el campo que tiene el foco y al final manda un sufijo, normalmente Enter. La aplicación procesa la lectura con Enter, con Tab o, si el lector está configurado sin sufijo, en cuanto termina de escribir (reconoce la ráfaga rápida del lector; al escribir a mano hay que presionar Enter):

- **Lector → Consultar:** escanea un ejemplar y ve título, ubicación, estado, a quién está prestado y si está vencido (`SP_CONSULTAR_EJEMPLAR`).
- **Lector → Prestar:** escanea el ejemplar, luego la credencial del alumno (o escribe la matrícula) y confirma con un segundo Enter (`SP_REGISTRAR_PRESTAMO`, con transacción).
- **Lector → Devolver:** escanea el ejemplar; muestra los días de retraso (`SP_REGISTRAR_DEVOLUCION`, con transacción).
- **Lector → Alta de ejemplar:** elige el libro y la ubicación y escanea la etiqueta nueva. El código se guarda en `EJEMPLARES.CODIGO_BARRAS`, que es `UNIQUE`.
- **Catálogo y Alumnos:** el buscador acepta el ISBN o la credencial escaneados.

Las etiquetas de prueba para imprimir (ejemplares, etiquetas nuevas, credenciales e ISBN) están en [`docs/etiquetas-codigos.pdf`](docs/etiquetas-codigos.pdf). El guion de la demostración y las evidencias está en [`docs/05-evidencias-lector.md`](docs/05-evidencias-lector.md).

## Entregables

| No. | Entregable | Dónde está |
| --- | --- | --- |
| 1 | Descripción del problema y justificación | [`docs/01-problema-y-justificacion.md`](docs/01-problema-y-justificacion.md) |
| 2 | Requerimientos funcionales y no funcionales | [`docs/02-requerimientos.md`](docs/02-requerimientos.md) |
| 3–4 | Diagrama entidad-relación, modelo relacional y diccionario de datos | [`docs/03-modelo-de-datos.md`](docs/03-modelo-de-datos.md) |
| 5 | Script para crear la base de datos (tablas, funciones, procedimientos, triggers, vistas y datos) | [`Biblioteca.sql`](Biblioteca.sql) · por partes: [`01_estructura.sql`](src/Logic/Sql_Schema/EstructuraPorPartes/01_estructura.sql) y [`03_datos_prueba.sql`](src/Logic/Sql_Schema/EstructuraPorPartes/03_datos_prueba.sql) |
| 6 | Script de procedimientos almacenados, funciones y triggers | [`02_programacion.sql`](src/Logic/Sql_Schema/EstructuraPorPartes/02_programacion.sql) |
| 7 | Script de usuarios, roles y permisos de seguridad | [`04_seguridad.sql`](src/Logic/Sql_Schema/EstructuraPorPartes/04_seguridad.sql) |
| 8 | Código fuente completo | Este repositorio (`src/`); el trabajo de cada integrante se ve en el historial de commits |
| 9 | Evidencias del lector de código de barras | [`docs/05-evidencias-lector.md`](docs/05-evidencias-lector.md) y [`docs/etiquetas-codigos.pdf`](docs/etiquetas-codigos.pdf) |

También hay apoyo para la presentación:
- [`docs/04-trazabilidad-requisitos.md`](docs/04-trazabilidad-requisitos.md): cada requisito de la guía, el objeto de la base que lo cumple y la pantalla donde se ve.
- [`docs/06-preguntas-de-defensa.md`](docs/06-preguntas-de-defensa.md): preguntas probables sobre el diseño y la implementación, con su respuesta.

## Objetos de la base de datos

| Tipo | Objetos |
| --- | --- |
| Tablas (9) | `ROLES`, `USUARIOS`, `CARRERAS`, `ALUMNOS`, `CATEGORIAS`, `LIBROS`, `EJEMPLARES`, `PRESTAMOS`, `AUDITORIA` |
| Funciones (3) | `FN_DIAS_RETRASO`, `FN_DISPONIBLES_LIBRO`, `FN_EJEMPLAR_DISPONIBLE` |
| Procedimientos (7) | `SP_LOGIN`, `SP_CONSULTAR_EJEMPLAR`, `SP_REGISTRAR_PRESTAMO`, `SP_REGISTRAR_DEVOLUCION`, `SP_DISPONIBILIDAD_LIBRO`, `SP_CAMBIAR_UBICACION`, `SP_HISTORIAL_ALUMNO` |
| Triggers de validación (4) | `TRG_VAL_EJEMPLARES_BI`, `TRG_VAL_EJEMPLARES_BU`, `TRG_VAL_PRESTAMOS_BI`, `TRG_VAL_PRESTAMOS_BU` |
| Triggers de auditoría (8) | `TRG_AUD_EJEMPLARES_AI`, `TRG_AUD_EJEMPLARES_AU`, `TRG_AUD_PRESTAMOS_AI`, `TRG_AUD_PRESTAMOS_AU`, `TRG_AUD_LIBROS_AD`, `TRG_AUD_ALUMNOS_AU`, `TRG_AUD_USUARIOS_AI`, `TRG_AUD_USUARIOS_AU` |
| Vistas (6) | `V_PRESTAMOS_VENCIDOS`, `V_ALUMNOS_CON_VENCIDOS`, `V_LIBROS_MAS_SOLICITADOS`, `V_LIBROS_SIN_PRESTAMOS`, `V_DISPONIBILIDAD`, `V_RESUMEN` |

## Estructura del código

```
Biblioteca.sql                  Script completo de la base (copia del consolidado)
requirements.txt                Dependencias de Python
.env_Ejemplo                    Plantilla de la conexión (copiar como .env)
docs/                           Documentos de entrega y etiquetas para imprimir
src/
  main.py                       Punto de entrada: crea el DAO, los servicios y abre la interfaz
  config.py                     Permisos por rol, días de préstamo y otras constantes
  pruebas_bd.py                 Prueba de humo del backend contra MySQL (35 casos)
  ConexionSQL/                  Conexión por perfil (usuario de MySQL por rol) y DAO
  Logic/                        Servicios con las reglas de negocio y la revisión de permisos
    Sql_Schema/                 Scripts SQL por partes y el generador del consolidado
  Modelos/                      Dataclasses de tablas y resultados, y errores de negocio
  UI/                           Interfaz PySide6: tema claro/oscuro, componentes y pantallas
    pantallas/                  Una pantalla por módulo (login, inicio, lector, catálogo...)
    recursos/                   Fuente Inter (licencia OFL) y sonidos del lector
```

La aplicación está en capas: las pantallas llaman a los **servicios** (`Logic/`), que validan los datos y el permiso del rol, y estos al **DAO** (`ConexionSQL/dao.py`), el único que ejecuta SQL. Los préstamos y devoluciones siempre pasan por los procedimientos almacenados, que hacen su propia transacción.

## Equipo

| Integrante | Cuenta de GitHub |
| --- | --- |
| Isaac Pérez Albor | [Laicamist](https://github.com/Laicamist) |
| Brayan Yafeth Chávez Reyes | [YafethReyes](https://github.com/YafethReyes) |
| _por completar_ | [monkiekingnum2fan](https://github.com/monkiekingnum2fan) |

Taller de Bases de Datos · Ingeniería en Software · 2026.

# Descripción del problema y justificación del sistema

**Proyecto:** Library Administrator, sistema gestor de biblioteca
**Materia:** Taller de Bases de Datos · Ingeniería en Software · ITSUR, 2026

## 1. Contexto

La biblioteca escolar presta libros a los alumnos de las distintas carreras (escenario simulado para el proyecto). Tiene varios títulos y, de los más pedidos, varias copias físicas acomodadas por pasillo y estante. El personal está formado por un responsable (administrador) y bibliotecarios que atienden el mostrador. Además, hay personas que solo necesitan consultar información, como un coordinador que revisa los reportes.

Sin un sistema, el control se lleva en una libreta o en una hoja de cálculo: se anota a mano el título, el nombre del alumno y la fecha.

## 2. Problemática

1. **No se sabe qué copia tiene cada alumno.** Se anota el título, pero no la copia exacta. Si hay tres copias de *Código limpio*, no se sabe cuál salió ni cuál regresó.
2. **Errores de captura.** Escribir a mano códigos largos, títulos y matrículas en el mostrador provoca errores y hace lenta la atención en horas de mucha gente.
3. **Préstamos sin control.** Nada impide prestar un libro que ya está prestado o en reparación, prestarle a un alumno dado de baja, o que un alumno acumule muchos libros.
4. **Retrasos sin seguimiento.** Para saber quién debe libros hay que revisar todas las anotaciones y calcular los días a mano, así que los retrasos se detectan tarde o nunca.
5. **No se sabe la disponibilidad.** Para responder si queda alguna copia de un título hay que ir al estante.
6. **Cambios sin responsable.** Si alguien cambia una ubicación, da de baja una copia o borra un registro, no queda constancia de quién lo hizo ni de cuál era el dato anterior.
7. **Información no protegida.** Cualquiera que abra la libreta o el archivo puede modificar cualquier dato; no hay usuarios ni permisos.
8. **Sin información para decidir.** No hay forma rápida de saber qué libros se piden más (para comprar más copias) ni cuáles nunca se usan.

## 3. Solución propuesta

Un sistema de información de escritorio, **Library Administrator**, conectado a una base de datos relacional en MySQL:

- **Cada copia física tiene una etiqueta con código de barras único.** Con el lector se consulta, presta, devuelve y da de alta un ejemplar sin escribir el código. La credencial del alumno también se lee con el lector.
- **Las reglas viven en la base de datos.** Los triggers de validación impiden prestar una copia que no está disponible, prestar a un alumno inactivo o con 3 préstamos activos, y registrar códigos vacíos. El código de barras es `UNIQUE`.
- **Préstamos y devoluciones con transacción.** Un procedimiento almacenado registra el préstamo y cambia el estado de la copia en una sola transacción. Si algo falla, se deshace todo (`ROLLBACK`).
- **Retrasos calculados, no anotados.** La función `FN_DIAS_RETRASO` calcula los días de retraso al momento, y los reportes muestran quién debe libros y desde cuándo.
- **Usuarios, roles y permisos.** Inicio de sesión con contraseña guardada como hash SHA-256 y tres roles: administrador, bibliotecario y consulta. Los permisos se aplican en la aplicación y también en MySQL, con un usuario de base de datos por rol.
- **Auditoría automática.** Los triggers registran quién cambió qué, cuándo, y los datos antes y después del cambio.
- **Reportes para la toma de decisiones**, dentro de la aplicación: libros más solicitados, alumnos con préstamos vencidos, disponibilidad por libro y libros sin préstamos.

## 4. Objetivos

**General.** Controlar los préstamos, devoluciones y ejemplares de la biblioteca con un sistema de información que use el lector de código de barras y una base de datos relacional con seguridad, integridad, auditoría y reportes.

**Específicos**
1. Diseñar e implementar la base de datos (entidades, relaciones, llaves y restricciones) con datos de prueba.
2. Identificar cada ejemplar con un código de barras único y usar el lector físico para consultar, prestar, devolver y dar de alta.
3. Garantizar la integridad de préstamos y devoluciones con transacciones, procedimientos almacenados, funciones y triggers de validación.
4. Proteger el acceso con inicio de sesión, contraseñas con hash y permisos por rol, en la aplicación y en MySQL.
5. Registrar automáticamente los cambios importantes en una tabla de auditoría.
6. Presentar en la aplicación reportes que apoyen las decisiones de la biblioteca.

## 5. Alcance

**Incluye:** inicio de sesión y roles; catálogo de libros, categorías y ejemplares; alumnos y carreras; préstamo y devolución con el lector; historial de préstamos por alumno; reportes; auditoría; administración de usuarios del sistema.

**No incluye:** venta o cobro de ningún tipo (no es un punto de venta), multas en dinero, reservaciones en línea, acceso de los alumnos al sistema ni varias sucursales.

## 6. Justificación

- **Operativa.** Escanear una etiqueta y una credencial toma segundos y elimina los errores de captura. Así se atiende más rápido y se sabe con certeza qué copia salió y cuál regresó.
- **Integridad de la información.** Las reglas del préstamo no dependen de la memoria del bibliotecario ni de que la aplicación esté bien programada: las cumple la base de datos con triggers, restricciones y transacciones, aunque alguien intente modificar los datos directamente.
- **Seguridad y responsabilidad.** Cada persona entra con su cuenta y solo puede hacer lo que su rol permite. Las contraseñas nunca se guardan en texto plano. La auditoría deja constancia de cada cambio y de quién lo hizo, y nadie puede borrarla desde la aplicación.
- **Toma de decisiones.** Los reportes muestran qué títulos conviene comprar, qué copias no se usan y qué alumnos deben libros, para dar seguimiento a los retrasos.
- **Factibilidad.** Usa herramientas gratuitas y conocidas por el equipo: MySQL 8, Python y PySide6. El lector de código de barras es un dispositivo económico que funciona como teclado y no requiere controladores.

## 7. Usuarios del sistema

| Rol | Quién es | Qué hace |
| --- | --- | --- |
| Administrador | Responsable de la biblioteca | Todo: además de lo del bibliotecario, administra usuarios, ve la auditoría, crea categorías y carreras y elimina libros. |
| Bibliotecario | Personal de mostrador | Préstamos y devoluciones con el lector, catálogo y ejemplares, alumnos, reportes. |
| Consulta | Coordinador o personal de apoyo | Consulta ejemplares con el lector y ve los reportes; no modifica nada. |

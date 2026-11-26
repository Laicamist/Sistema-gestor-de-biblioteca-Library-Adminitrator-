# Preguntas probables en la defensa

La guía pide que los integrantes respondan preguntas sobre el diseño y la implementación. Estas son las más probables, con una respuesta corta basada en lo que hay en el proyecto. Conviene que cada integrante pueda abrir el script o el archivo que se menciona y explicarlo.

## Diseño de la base de datos

**1. ¿Por qué separaron LIBROS y EJEMPLARES?**
Porque un libro (la obra, con su ISBN) puede tener varias copias físicas, y lo que se presta es una copia concreta. El código de barras va en EJEMPLARES, una etiqueta por copia, y así se sabe qué copia tiene cada alumno, dónde está y en qué estado. Si el código estuviera en LIBROS, no podríamos distinguir entre tres copias del mismo título.

**2. ¿Qué tipo de relación hay entre ALUMNOS y EJEMPLARES y cómo la resolvieron?**
Es muchos a muchos: un alumno pide muchas copias y una copia la piden muchos alumnos a lo largo del tiempo. Se resuelve con la tabla PRESTAMOS, que además guarda los datos de la relación: fechas, estado y el usuario que la registró.

**3. ¿En qué forma normal está la base?**
En tercera forma normal. Los atributos son atómicos (1FN); las llaves primarias son de una sola columna, así que no hay dependencias parciales (2FN); y no hay dependencias transitivas porque los nombres de carrera, categoría y rol están en su propia tabla (3FN).

**4. ¿Por qué no guardan la disponibilidad ni los días de retraso en una columna?**
Porque son datos derivados que cambian con el tiempo y se desactualizarían. Se calculan al momento con `FN_DISPONIBLES_LIBRO` y `FN_DIAS_RETRASO`.

**5. ¿Qué restricciones de integridad usaron?**
Llaves primarias y foráneas; `UNIQUE` en código de barras, ISBN, matrícula y nombre de usuario; `CHECK` para el semestre (1–12), el año (> 0), la fecha límite (no antes del préstamo) y el código no vacío; `ENUM` para los estados; `NOT NULL` y `DEFAULT`. Las reglas que dependen de otras tablas van en triggers.

**6. ¿Por qué AUDITORIA no tiene llaves foráneas?**
Porque debe conservar el registro aunque la fila original desaparezca. Por ejemplo, cuando se elimina un libro, su información queda en `DATOS_ANTERIORES`.

**7. ¿Por qué los datos anteriores y nuevos de la auditoría son JSON?**
Porque cada tabla auditada tiene columnas distintas. Con `JSON_OBJECT` una sola tabla guarda cualquier cambio y en la app se muestra campo por campo.

## Lector de código de barras

**8. ¿Cómo se comunica el lector con la aplicación?**
Funciona como un teclado: escribe el código en el campo que tiene el foco y manda Enter. La señal `returnPressed` del campo ejecuta la consulta o el registro. No usamos ninguna librería especial, por eso funciona con cualquier lector USB.

**9. ¿Qué evita que haya dos ejemplares con el mismo código?**
La restricción `UNIQUE` sobre `EJEMPLARES.CODIGO_BARRAS`. Si se escanea una etiqueta repetida en el alta, MySQL rechaza el INSERT (error 1062) y la app muestra el aviso. Además, un `CHECK` y el trigger `TRG_VAL_EJEMPLARES_BI` impiden el código vacío.

**10. ¿Qué operaciones hace el lector?**
Consultar un ejemplar, prestar (ejemplar y credencial del alumno), devolver, dar de alta una etiqueta nueva y buscar libros por ISBN o alumnos por credencial.

**11. ¿Por qué el préstamo pide un segundo Enter?**
Para confirmar. El primer escaneo muestra los datos del ejemplar y del alumno; el segundo Enter registra. Así un escaneo accidental no presta un libro.

## Seguridad

**12. ¿Cómo guardan las contraseñas?**
Como hash SHA-256: 64 caracteres hexadecimales en `CONTRASENA_HASH`. La app calcula el hash (`Logic/seguridad.py`) y solo el hash viaja a `SP_LOGIN`; la contraseña nunca se guarda ni se muestra. Ni el administrador puede verla: solo puede asignar una nueva.

**13. ¿Cómo funciona el inicio de sesión?**
La app se conecta con un usuario de MySQL que solo puede ejecutar `SP_LOGIN`. El procedimiento recibe el usuario y el hash (IN) y regresa el id, el rol y un mensaje (OUT). Si es correcto, la app se reconecta con el usuario de MySQL de ese rol y ejecuta `SET @USUARIO_APP` para la auditoría.

**14. ¿Dónde se aplican los permisos por rol?**
En dos capas. En la app: la barra lateral muestra solo los módulos del rol y cada servicio revisa el permiso antes de operar. En MySQL: cada rol se conecta con su propio usuario con `GRANT` limitados (`04_seguridad.sql`). Aunque alguien se saltara la app, MySQL rechaza la operación.

**15. ¿Qué no puede hacer cada rol?**
- **Consulta:** no modifica nada; solo consulta con el lector y ve reportes.
- **Bibliotecario:** no ve usuarios ni auditoría, no borra libros y no puede insertar en PRESTAMOS directamente, solo a través de los procedimientos.
- **Administrador:** todo, pero tampoco puede borrar ni modificar la auditoría.

**16. ¿Por qué un usuario no puede desactivarse o cambiarse el rol a sí mismo?**
Para que el sistema nunca se quede sin administrador por error. Lo valida el servicio de usuarios.

**17. ¿SHA-256 es suficiente?**
La guía acepta SHA-2. Sabemos que para producción es mejor un algoritmo lento con sal, como bcrypt o Argon2id, porque resiste mejor los ataques de diccionario. Usamos SHA-256 porque así se pidió y porque es el mismo hash que calcula `SHA2(texto, 256)` en MySQL, lo que facilita comprobarlo desde Workbench.

## Transacciones y procedimientos

**18. ¿Dónde está la transacción y por qué es necesaria?**
En `SP_REGISTRAR_PRESTAMO` y `SP_REGISTRAR_DEVOLUCION`. Un préstamo son dos cambios: insertar en PRESTAMOS y marcar el ejemplar como PRESTADO. Si solo se hiciera uno, la base quedaría inconsistente; con la transacción se guardan los dos (`COMMIT`) o ninguno (`ROLLBACK`).

**19. ¿Cuándo se ejecuta el ROLLBACK?**
- Cuando falla cualquier sentencia: el `EXIT HANDLER FOR SQLEXCEPTION` hace `ROLLBACK` y regresa el mensaje del error en el parámetro OUT. Por ejemplo, cuando el trigger rechaza a un alumno con 3 préstamos.
- De forma explícita, cuando el código no existe o no hay préstamo activo.

**20. ¿Para qué sirve el `FOR UPDATE`?**
Bloquea la fila del ejemplar mientras dura la transacción. Si dos bibliotecarios escanean la misma copia al mismo tiempo, el segundo espera y luego el trigger ve que ya no está disponible.

**21. ¿Qué procedimientos tienen IN, OUT y cuáles modifican datos?**
- Todos reciben parámetros IN.
- Con OUT: `SP_LOGIN`, `SP_REGISTRAR_PRESTAMO`, `SP_REGISTRAR_DEVOLUCION` y `SP_DISPONIBILIDAD_LIBRO`.
- Modifican datos: `SP_REGISTRAR_PRESTAMO` (INSERT + UPDATE), `SP_REGISTRAR_DEVOLUCION` (UPDATE) y `SP_CAMBIAR_UBICACION` (UPDATE).
- Los 7 se usan desde la app; ver la tabla en [04-trazabilidad-requisitos.md](04-trazabilidad-requisitos.md).

**22. ¿Cómo llama Python a un procedimiento con OUT?**
Con `cursor.callproc(nombre, args)` del conector de MySQL, poniendo `None` en el lugar de cada OUT. `callproc` regresa los argumentos con los OUT ya llenos, y los SELECT del procedimiento se leen con `stored_results()` (`DAO._llamar_sp`).

## Funciones y triggers

**23. ¿Dónde se usan las funciones?**
- `FN_DIAS_RETRASO`: en las vistas de vencidos, en el historial y en la devolución.
- `FN_DISPONIBLES_LIBRO`: en `V_DISPONIBILIDAD`, `SP_CONSULTAR_EJEMPLAR` y `SP_DISPONIBILIDAD_LIBRO`.
- `FN_EJEMPLAR_DISPONIBLE`: en `SP_CONSULTAR_EJEMPLAR`.

Ninguna es un script suelto: todas se usan en objetos que llama la app.

**24. ¿Qué validan los triggers y cómo avisan?**
- `TRG_VAL_PRESTAMOS_BI`: que el ejemplar esté disponible, que el alumno esté activo y que no tenga ya 3 préstamos.
- `TRG_VAL_PRESTAMOS_BU`: que no se modifique un préstamo devuelto ni se ponga una devolución anterior al préstamo.
- `TRG_VAL_EJEMPLARES_BI/BU`: que el código no quede vacío.

Avisan con `SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = '...'`, y la app muestra ese mensaje.

**25. ¿Por qué validar en triggers si la app ya valida?**
Porque la base debe protegerse sola: las reglas se cumplen aunque los datos se modifiquen desde Workbench u otro programa. En la demostración la app deja pasar a propósito a un alumno con 3 préstamos para que se vea que MySQL lo rechaza.

**26. ¿Cómo sabe la auditoría qué usuario de la app hizo el cambio si todos los bibliotecarios usan el mismo usuario de MySQL?**
Por la variable de sesión `@USUARIO_APP`, que la app asigna después del login en su conexión. Los triggers guardan `COALESCE(@USUARIO_APP, USER())`: si el cambio viene de fuera de la app, queda el usuario de MySQL.

**27. ¿Qué cambios se auditan?**
- Altas y cambios de ejemplares (estado y ubicación).
- Préstamos y devoluciones.
- Eliminación de libros.
- Cambios de alumnos.
- Altas y cambios de usuarios, sin guardar el hash, solo si cambió la contraseña.

Ocho triggers en total.

## Reportes y aplicación

**28. ¿Qué técnicas SQL usan los reportes?**
- JOIN de 3, 4 y 5 tablas.
- Subconsultas (escalares y correlacionadas).
- `COUNT`, `SUM` y `MAX`.
- `GROUP BY` y `HAVING`.
- `NOT EXISTS`.
- La función de ventana `RANK()`.
- Una CTE con `WITH`.

Están en las vistas de `02_programacion.sql` y la pantalla Reportes muestra cuál usa cada uno.

**29. ¿Para qué decisión sirve cada reporte?**
- **Más solicitados:** qué títulos conviene comprar.
- **Alumnos con retraso:** a quién dar seguimiento primero.
- **Préstamos vencidos:** qué libros reclamar.
- **Disponibilidad:** qué títulos están agotados.
- **Sin préstamos:** qué títulos reubicar o revisar.

**30. ¿Cómo está organizado el código?**
En capas:
- **Pantallas** (`UI/pantallas`), que solo muestran datos y llaman a los servicios.
- **Servicios** (`Logic`), que validan los datos y los permisos.
- **DAO** (`ConexionSQL/dao.py`), el único que ejecuta SQL.
- **Modelos** (`Modelos`), con dataclasses para tablas y resultados.

**31. ¿Cómo comprobaron que todo funciona contra la base real?**
Con `src/pruebas_bd.py`: 35 casos contra MySQL. Revisa la conexión de cada perfil, el login, el préstamo y la devolución, cada trigger, la auditoría con el usuario de la app, los reportes y que MySQL rechace las operaciones sin permiso.

**32. ¿Qué mejorarían con más tiempo?**
- bcrypt o Argon2id para las contraseñas.
- Reservaciones.
- Avisos por correo a los alumnos con retraso.
- Multas.
- Paginar la auditoría desde el servidor.

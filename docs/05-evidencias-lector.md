# Evidencias del lector de código de barras

Guía para preparar la demostración con el lector físico y reunir las evidencias del entregable 9. Los códigos y resultados corresponden a los datos de `03_datos_prueba.sql`. Las etiquetas para imprimir están en [etiquetas-codigos.pdf](etiquetas-codigos.pdf).

## 1. Cómo usa el sistema el lector

- El lector USB funciona como **teclado** (HID): al leer una etiqueta "escribe" el código en el campo que tiene el foco y normalmente manda **Enter** al final. No necesita controladores.
- En la aplicación, el fin de la lectura dispara la consulta o el registro. Los campos del lector (`CampoLector` en `src/UI/componentes.py`) lo detectan con Enter, con Tab o con un salto de línea, y si el lector no manda ningún sufijo, por la ráfaga rápida de teclas: unos 150 ms después del último carácter. Al escribir a mano hay que presionar Enter. Después de cada lectura el campo recupera el foco, así que se puede escanear una etiqueta tras otra sin tocar el mouse. Suena un tono de éxito o de error.
- El código de cada copia está en `EJEMPLARES.CODIGO_BARRAS`, con `UNIQUE`, `CHECK` de no vacío y los triggers `TRG_VAL_EJEMPLARES_BI/BU`.
- Las etiquetas usan **Code 128**, que el lector entrega exactamente como está impreso. No se usó EAN-13 porque ese formato agrega un dígito verificador que no coincidiría con los códigos guardados.

## 2. Preparación (antes de la presentación)

1. Ejecutar completo `Biblioteca.sql` en MySQL Workbench como `root`. Así los datos quedan como en las etiquetas; las fechas de los préstamos son relativas al día de hoy, así que los vencidos siempre aparecen vencidos.
2. Revisar que exista el `.env` en la raíz del proyecto y abrir la aplicación con `python src/main.py`.
3. Imprimir `etiquetas-codigos.pdf` **al 100 %** (sin "ajustar a la página"). Recortar y pegar las de la sección 1 en libros o tarjetas; las credenciales pueden quedarse en hoja.
4. Probar el lector en el Bloc de notas: al escanear `7501000000011` debe aparecer el código completo. Lo ideal es que también salte de línea (sufijo "Enter/CR"), pero la aplicación funciona aunque el lector no mande sufijo o mande Tab.
5. Si se va a correr `src/pruebas_bd.py`, hacerlo **antes** del paso 1, porque esas pruebas cambian datos.

## 3. Guion de la demostración

Cada paso indica qué escanear y qué debe verse. Entre paréntesis, el objeto de la base que se demuestra.

### Parte A: inicio de sesión y roles
| # | Acción | Resultado esperado |
| --- | --- | --- |
| A1 | Iniciar sesión con `MRUIZ` / `MRUIZ123` | "LA CUENTA ESTA INACTIVA" (`SP_LOGIN` con OUT). |
| A2 | Iniciar sesión con `IPEREZ` / `CONS123` (consulta) | Solo aparecen Inicio, Lector y Reportes; en el Lector solo existe el modo Consultar. |
| A3 | Lector → Consultar → escanear **7501000000011** | Ficha de *Código limpio*: PRESTADO a ANA GARCIA MARTINEZ, vencido (`SP_CONSULTAR_EJEMPLAR`, `FN_EJEMPLAR_DISPONIBLE`). |
| A4 | Cerrar sesión e iniciar con `OALVAREZ` / `BIBLIO123` (bibliotecario) | Aparecen Catálogo y Alumnos; en el Lector, los 4 modos. |

### Parte B: préstamo con transacción
| # | Acción | Resultado esperado |
| --- | --- | --- |
| B1 | Lector → Prestar → escanear **7501000000012** | Ficha del ejemplar DISPONIBLE; pide al alumno. |
| B2 | Escanear la credencial **22120002** (Luis) | Tarjeta del alumno: activo, 1 de 3 préstamos. |
| B3 | Enter otra vez (o el botón) | "PRESTAMO REGISTRADO CORRECTAMENTE · se devuelve a más tardar el …" (`SP_REGISTRAR_PRESTAMO`: INSERT + UPDATE + COMMIT). |
| B4 | Lector → Consultar → escanear **7501000000012** | Ahora está PRESTADO a Luis. |

### Parte C: reglas que la base no deja romper (triggers y ROLLBACK)
| # | Acción | Resultado esperado |
| --- | --- | --- |
| C1 | Prestar → escanear **7501000000072** y la credencial **22120001** (Ana) → Enter | Préstamo rechazado: "EL ALUMNO YA TIENE 3 PRESTAMOS ACTIVOS" (`TRG_VAL_PRESTAMOS_BI` + `ROLLBACK`). |
| C2 | Prestar → **7501000000072** y la credencial **20120004** (Ricardo) → Enter | La tarjeta muestra INACTIVO; al confirmar: "EL ALUMNO ESTA INACTIVO (DADO DE BAJA)". |
| C3 | Prestar → escanear **7501000000112** | Aviso: el ejemplar está en MANTENIMIENTO. Con la credencial 22120002 y Enter: "EL EJEMPLAR NO ESTA DISPONIBLE PARA PRESTAMO". |
| C4 | Consultar → escanear **7501000000072** | Sigue DISPONIBLE: la transacción rechazada no dejó nada a medias. |

### Parte D: devolución
| # | Acción | Resultado esperado |
| --- | --- | --- |
| D1 | Lector → Devolver → escanear **7501000000011** | "DEVOLUCION REGISTRADA … · 19 días de retraso" (`SP_REGISTRAR_DEVOLUCION` con OUT, `FN_DIAS_RETRASO`). |
| D2 | Devolver → escanear **7501000000011** otra vez | Rechazado: "ESE EJEMPLAR NO TIENE UN PRESTAMO ACTIVO". |

### Parte E: alta de un ejemplar nuevo y código único
| # | Acción | Resultado esperado |
| --- | --- | --- |
| E1 | Lector → Alta de ejemplar → elegir *Código limpio*, escribir la ubicación `PASILLO A - ESTANTE 1` → escanear la etiqueta nueva **7501000000014** | Pide confirmar; con Enter otra vez: "Ejemplar 7501000000014 registrado…" (INSERT, `TRG_VAL_EJEMPLARES_BI`, `TRG_AUD_EJEMPLARES_AI`). |
| E2 | En el mismo modo, escanear **7501000000012** dos veces | "Ya existe un registro con ese valor…" (restricción `UNIQUE` en `CODIGO_BARRAS`). |

### Parte F: búsquedas con el lector en otros módulos
| # | Acción | Resultado esperado |
| --- | --- | --- |
| F1 | Catálogo → en el buscador escanear el ISBN **9780132350884** | Se elige *Código limpio*; el panel muestra sus 4 copias (con la nueva) y la disponibilidad (`SP_DISPONIBILIDAD_LIBRO` con OUT). |
| F2 | Elegir la copia 7501000000014 → Cambiar ubicación → `PASILLO B - ESTANTE 2` | "Ejemplar … movido a PASILLO B - ESTANTE 2" (`SP_CAMBIAR_UBICACION` → `TRG_AUD_EJEMPLARES_AU`). |
| F3 | Alumnos → en el buscador escanear la credencial **22120001** | Ficha de Ana con su historial: el préstamo devuelto con 19 días de retraso y los activos (`SP_HISTORIAL_ALUMNO`). |

### Parte G: reportes y auditoría
| # | Acción | Resultado esperado |
| --- | --- | --- |
| G1 | Reportes → Préstamos vencidos y Alumnos con retraso | Los reportes ya no incluyen el préstamo devuelto en D1. Doble clic en un alumno abre su ficha. |
| G2 | Cerrar sesión e iniciar con `BCHAVEZ` / `ADMIN123` → Auditoría | Movimientos hechos por **OALVAREZ**: el préstamo (INSERT en PRESTAMOS y UPDATE del ejemplar), la devolución, el alta del ejemplar y el cambio de ubicación con la anterior y la nueva. |

## 4. Evidencias que conviene guardar

Guardar las imágenes en `docs/evidencias/` con estos nombres, para que el repositorio quede ordenado:

| Archivo | Qué muestra |
| --- | --- |
| `01-lector-conectado.jpg` | Foto del lector conectado a la computadora donde corre el sistema. |
| `02-bloc-de-notas.png` | El lector escribiendo un código en el Bloc de notas (prueba de que funciona como teclado). |
| `03-consulta.png` | Paso A3: ficha del ejemplar consultado con el lector. |
| `04-prestamo.png` | Paso B3: préstamo registrado. |
| `05-rechazo-trigger.png` | Paso C1: préstamo rechazado por el límite de 3. |
| `06-devolucion.png` | Paso D1: devolución con días de retraso. |
| `07-alta-ejemplar.png` | Paso E1: etiqueta nueva registrada. |
| `08-codigo-duplicado.png` | Paso E2: rechazo por código repetido. |
| `09-auditoria.png` | Paso G2: movimientos con el usuario responsable. |
| `10-unique-workbench.png` | En Workbench: `SHOW CREATE TABLE EJEMPLARES;` donde se vea `UNIQUE KEY` en `CODIGO_BARRAS`. |
| `demo-lector.mp4` | (Opcional) Video corto de las partes B a E con el lector en mano. |

Consultas útiles en Workbench para las capturas:

```sql
USE BIBLIOTECA;
SHOW CREATE TABLE EJEMPLARES;                       -- UNIQUE en CODIGO_BARRAS
SELECT CODIGO_BARRAS, ESTADO, UBICACION FROM EJEMPLARES WHERE CODIGO_BARRAS IN ('7501000000012', '7501000000014');
SELECT * FROM AUDITORIA ORDER BY ID_MOVIMIENTO DESC LIMIT 10;
SELECT * FROM V_PRESTAMOS_VENCIDOS;
```

## 5. Si algo no funciona

| Síntoma | Causa probable |
| --- | --- |
| El código aparece pero no pasa nada | Ya no debería pasar: la aplicación lee aunque el lector no mande Enter. Si sigue igual, revisar la terminal donde se ejecutó `python src/main.py`; cualquier error del lector ahora también sale en rojo en la pantalla. |
| Aparecen letras o símbolos raros | Distribución de teclado distinta entre el lector y Windows: configurar el lector en "US keyboard" o en el idioma del sistema. |
| No se lee la etiqueta | Se imprimió reducida: imprimir al 100 % y acercar el lector a 10–15 cm. |
| "No existe un ejemplar con el código…" en un código de la hoja | La base no tiene los datos de prueba: volver a ejecutar `Biblioteca.sql`. |
| "… es el ISBN de «…», no la etiqueta de un ejemplar" | Se escaneó el código de barras de la contraportada (ISBN) de un libro que tiene copias con etiqueta propia: escanear la etiqueta del ejemplar. |

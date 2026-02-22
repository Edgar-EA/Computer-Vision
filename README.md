# Proyecto 6: Sistema de Asistencia con Reconocimiento Facial

Sistema automatizado de asistencia usando **DeepFace + OpenCV**, con exportación CSV compatible con **Odoo HR Attendance** y notificaciones por **Gmail**.

Todo el sistema vive en un solo archivo: `main.py`.

---

## Requisitos

- Python **3.11** (no compatible con versiones anteriores o posteriores)
- Cámara web
- Sistema operativo: Windows, Linux o macOS

---

## Instalación

### 1. Instalar Python 3.11

Descarga Python 3.11 desde [python.org](https://www.python.org/downloads/).

> **Windows:** durante la instalación, marca la opción **"Add Python to PATH"**.

### 2. Crear el entorno virtual con Python 3.11

Primero localiza la ruta exacta del ejecutable:
```bash
where python      # Windows
which python3     # Linux / macOS
```

Copia la ruta donde aparezca la versión 3.11 y úsala para crear el entorno virtual:
```bash
# Windows
C:\ruta\a\python3.11.exe -m venv .venv
.venv\Scripts\activate

# Linux / macOS
/ruta/a/python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

---

## Uso

### Paso 1 — Registrar personas (enrolamiento)

**Desde la cámara (recomendado):**
```bash
python main.py enrolar "Juan Perez"
# ESPACIO → capturar foto | Q → terminar
```

**Manualmente:** crea la carpeta y copia las fotos directamente:
```
known_faces/
  Juan_Perez/        ← usa guion bajo en lugar de espacios
    foto1.jpg
    foto2.jpg        ← mínimo 3–5 fotos por persona
```

---

### Paso 2 — Ejecutar el sistema
```bash
python main.py
```

La cámara se abre y comienza el reconocimiento en tiempo real.

| Tecla | Acción |
|-------|--------|
| `E` | Exportar CSV + simular importación en Odoo + enviar correo |
| `Q` | Salir (exporta automáticamente) |

---

## Flujo del sistema
```
Cámara
  → DeepFace reconoce el rostro
  → SQLite registra check_in / check_out
  → CSV exportado en formato Odoo
  → Simulación de importación en Odoo HR Attendance
  → Notificación Gmail con resumen + CSV adjunto
```

**Lógica de registros:**
- Primera detección del día → **Entrada** (check_in)
- Segunda detección del día → **Salida** (check_out)
- Cooldown de 3 horas (10 800 s) para evitar registros duplicados

---

## Importar CSV en Odoo

El archivo generado en `exports/` es compatible directamente con Odoo:

1. Ve a **Asistencias → Asistencias → Importar**
2. Sube el archivo `asistencias_YYYY-MM-DD.csv`
3. Mapea las columnas:

| Columna CSV | Campo en Odoo |
|-------------|---------------|
| `Employee`  | Empleado      |
| `Check In`  | Entrada       |
| `Check Out` | Salida        |

---

## Configuración de Gmail (opcional)

Edita las siguientes constantes en `main.py`:
```python
GMAIL_SENDER   = "tu_correo@gmail.com"
GMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"   # App Password de Google
DESTINATARIOS  = ["supervisor@empresa.com", "rrhh@empresa.com"]
```

> Si no se configura Gmail, el sistema funciona en **modo demo** e imprime en consola lo que enviaría.

Para generar un App Password en Google: **Cuenta de Google → Seguridad → Verificación en dos pasos → Contraseñas de aplicación**.

---

## Configuración de DeepFace

Edita estas constantes al inicio de `main.py`:
```python
MODEL_NAME = "Facenet512"   # Modelo de reconocimiento facial
DETECTOR   = "opencv"       # Backend detector de rostros
THRESHOLD  = 0.40           # Umbral de distancia (menor = más estricto)
```

| Parámetro | Opciones disponibles |
|-----------|----------------------|
| `MODEL_NAME` | `Facenet512`, `VGG-Face`, `ArcFace`, `DeepFace` |
| `DETECTOR`   | `opencv`, `retinaface`, `mtcnn`, `ssd` |

---

## Estructura del proyecto
```
proyecto/
├── main.py               # Sistema completo
├── requirements.txt      # Dependencias
├── known_faces/          # Fotos de personas registradas
│   └── Juan_Perez/
├── exports/              # CSVs generados
└── asistencias.db        # Base de datos SQLite
```
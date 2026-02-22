# Proyecto 6: Computer Vision

# Sistema de Asistencia con Reconocimiento Facial

Sistema automatizado de asistencia usando **DeepFace + OpenCV**, con exportación CSV compatible con **Odoo HR Attendance** y notificaciones por **Gmail**.

Todo el sistema vive en un solo archivo: `main.py`.

# Instalación 
Este proyecto requiere Python 3.11. No funcionara correctamente con versiones anteriores o superiores
## 1. Instalar Python 3.11
Busca la pagina oficial de Python y descarga la version 3.11 (Durante la instalacion en Windows asegurate de marcar: Add Python to PATH)
Una vez terminada la instalacion necesitaras la ruta en donde se instalo para poder crear el entorno virtual con esa version en especifica
Abre una consola de comandos y ejecuta:
```bash
where python
```
Copia la ruta en donde salga la version 3.11

## Crear entorno virtual con Python 3.11
```bash
C:\ruta\completa\python.exe -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

# 2. Instalar dependencias
pip3 install -r requirements.txt

## Paso 1 — Registrar Personas (Enrolamiento)

### Desde la cámara (recomendado)
```bash
python main.py enrolar "Juan Perez"
# Presiona ESPACIO para capturar fotos | Q para terminar
```

### Manualmente
Crea la carpeta y copia las fotos directamente:
```
known_faces/
  Juan_Perez/        ← guion bajo en lugar de espacio
    foto1.jpg
    foto2.jpg        ← mínimo 3-5 fotos por persona
```

---

## Paso 2 — Ejecutar el Sistema

```bash
python main.py
```

La cámara se abre y comienza el reconocimiento en tiempo real.

**Controles:**

| Tecla | Acción |
|-------|--------|
| `E` | Exportar CSV + simular Odoo + enviar Gmail |
| `Q` | Salir (exporta automáticamente al cerrar) |

---

## Flujo Completo

```
Cámara
  → DeepFace reconoce el rostro
  → SQLite registra check_in / check_out
  → CSV exportado (formato Odoo)
  → Simulación de importación en Odoo HR Attendance
  → Notificación Gmail con resumen + CSV adjunto
```

**Lógica de check_in / check_out:**
- Primera detección del día → **Entrada**
- Segunda detección del día → **Salida**
- Cooldown de 10800 segundos evita registros duplicados

---

## Importar CSV en Odoo SaaS

El CSV generado en `exports/` es compatible directo con Odoo:

1. Ve a **Asistencias → Asistencias → Importar**
2. Sube el archivo `asistencias_YYYY-MM-DD.csv`
3. Mapea las columnas:
   - `Employee` → **Empleado**
   - `Check In` → **Entrada**
   - `Check Out` → **Salida**

---

## Configurar Gmail (opcional)

Edita estas líneas en `main.py`:

```python
GMAIL_SENDER   = "tu_correo@gmail.com"
GMAIL_PASSWORD = "xxxx xxxx xxxx xxxx"   # App Password 
DESTINATARIOS  = ["supervisor@empresa.com", "rrhh@empresa.com"]
```

Sin configurar Gmail, el sistema funciona en **modo demo** e imprime en consola lo que enviaría.

---

## Configuración de DeepFace

Edita estas constantes al inicio de `main.py`:

```python
MODEL_NAME  = "Facenet512"  # Modelo de reconocimiento
DETECTOR    = "opencv"      # Detector de rostros
THRESHOLD   = 0.40          # Umbral de distancia (más bajo = más estricto)

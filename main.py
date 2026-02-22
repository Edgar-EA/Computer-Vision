import cv2
import os
import time
import sqlite3
import csv
import json
import smtplib
import ssl
import random
from datetime import datetime, date, timedelta
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from deepface import DeepFace



KNOWN_FACES_DIR  = Path("known_faces")
EXPORTS_DIR      = Path("exports")
DB_PATH          = Path("attendance.db")
COOLDOWN_SEG     = 10800          # Segundos entre registros del mismo empleado

# DeepFace
MODEL_NAME       = "Facenet512"   # VGG-Face | Facenet | Facenet512 | ArcFace
DETECTOR         = "opencv"       # opencv | retinaface | mtcnn
DISTANCE_METRIC  = "cosine"
THRESHOLD        = 0.40

# Gmail (opcional — deja los valores demo para solo simular)
GMAIL_SENDER     = "edgar2410067@hybridge.education"
GMAIL_PASSWORD   = "xxxx xxxx xxxx xxxx"   # App Password de Google (Obviamente no iba a poner el mio...)
DESTINATARIOS    = ["edgar2410067@hybridge.education",]

# Odoo (solo referencia visual en la simulación)
ODOO_URL         = "https://edgar-angel-pruebas.odoo.com"

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            check_in   TEXT,
            check_out  TEXT,
            date       TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    con.commit()
    return con


def registrar_asistencia(con, name: str) -> str:
    """
    Auto check_in / check_out:
      - Primera detección del día  → check_in
      - Segunda detección del día  → check_out
    Retorna: 'check_in' | 'check_out' | 'ya_completo'
    """
    hoy = date.today().isoformat()
    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = con.execute(
        "SELECT id, check_in, check_out FROM attendance WHERE name=? AND date=? ORDER BY id DESC LIMIT 1",
        (name, hoy)
    ).fetchone()

    if row is None:
        con.execute(
            "INSERT INTO attendance (name, check_in, date) VALUES (?,?,?)",
            (name, ahora, hoy)
        )
        con.commit()
        return "check_in"
    elif row[2] is None:
        con.execute("UPDATE attendance SET check_out=? WHERE id=?", (ahora, row[0]))
        con.commit()
        return "check_out"
    else:
        return "ya_completo"


def get_asistencias_hoy(con) -> list:
    hoy = date.today().isoformat()
    rows = con.execute(
        "SELECT name, check_in, check_out, date FROM attendance WHERE date=? ORDER BY check_in",
        (hoy,)
    ).fetchall()
    return [{"name": r[0], "check_in": r[1], "check_out": r[2], "date": r[3]} for r in rows]



#  RECONOCIMIENTO FACIAL CON DEEPFACE
def identificar_rostros(frame) -> list:
    resultados = []

    if not KNOWN_FACES_DIR.exists() or not any(KNOWN_FACES_DIR.iterdir()):
        return resultados

    try:
        dfs = DeepFace.find(
            img_path=frame,
            db_path=str(KNOWN_FACES_DIR),
            model_name=MODEL_NAME,
            detector_backend=DETECTOR,
            distance_metric=DISTANCE_METRIC,
            enforce_detection=False,
            silent=True,
        )

        for df in dfs:
            if df.empty:
                resultados.append({"name": "Desconocido", "confidence": 0.0, "bbox": (0, 0, 120, 120)})
                continue

            mejor = df.iloc[0]
            distancia = mejor[f"{MODEL_NAME}_{DISTANCE_METRIC}"]
            confianza = max(0.0, round((1 - distancia) * 100, 1))

            if distancia > THRESHOLD:
                name = "Desconocido"
            else:
                identity_path = mejor["identity"]
                carpeta = os.path.basename(os.path.dirname(identity_path))
                name = carpeta.replace("_", " ")

            bbox = (
                int(mejor.get("source_x", 0)),
                int(mejor.get("source_y", 0)),
                int(mejor.get("source_w", 120)),
                int(mejor.get("source_h", 120)),
            )
            resultados.append({"name": name, "confidence": confianza, "bbox": bbox})

    except Exception as e:
        print(f"[DeepFace] {e}")

    return resultados


#  EXPORTAR CSV PARA ODOO
def exportar_csv(registros: list, fecha: str) -> Path:
    EXPORTS_DIR.mkdir(exist_ok=True)
    path = EXPORTS_DIR / f"asistencias_{fecha}.csv"

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Employee", "Check In", "Check Out", "Work Hours"])
        for r in registros:
            writer.writerow([
                r["name"], r["check_in"], r["check_out"] or "",
                calcular_horas(r["check_in"], r["check_out"])
            ])

    print(f"[CSV] Exportado: {path.name} ({len(registros)} registros)")
    return path


def calcular_horas(ci: str, co: str) -> str:
    if not ci or not co:
        return ""
    try:
        fmt = "%Y-%m-%d %H:%M:%S"
        delta = datetime.strptime(co, fmt) - datetime.strptime(ci, fmt)
        h, m = divmod(delta.seconds // 60, 60)
        return f"{h:02d}:{m:02d}"
    except Exception:
        return ""


#  SIMULACIÓN ODOO
def simular_odoo(csv_path: Path, registros: list) -> dict:
    print(f"\n{'─'*50}")
    print(f" ODOO — {ODOO_URL}")
    print(f" {csv_path.name}  ({len(registros)} registros)")
    print(f"{'─'*50}")

    exitosos = []

    for i, r in enumerate(registros, 1):
        time.sleep(0.08)
        odoo_id = random.randint(100, 9999)
        exitosos.append({**r, "odoo_id": odoo_id})
        accion = "check_in" if not r["check_out"] else "completo"
        print(f"  [{i:02d}] [+] {r['name']:<22} → hr.attendance #{odoo_id}  [{accion}]")

    result = {
        "exitosos": exitosos, "errores": [],
        "total": len(registros), "timestamp": datetime.now().isoformat()
    }

    log_path = EXPORTS_DIR / f"odoo_log_{date.today().isoformat()}.json"
    log_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  {len(exitosos)}/{len(registros)} importados  |  Log: {log_path.name}")
    print(f"{'─'*50}\n")
    return result


#  NOTIFICACIONES GMAIL
def _html_reporte(registros: list, ausentes: list, odoo: dict, fecha: str) -> str:
    filas = ""
    for r in registros:
        ci = r["check_in"].split(" ")[1] if r["check_in"] else "—"
        co = r["check_out"].split(" ")[1] if r["check_out"] else "—"
        hrs = calcular_horas(r["check_in"], r["check_out"]) or "En curso"
        filas += f"<tr><td>{r['name']}</td><td>{ci}</td><td>{co}</td><td>{hrs}</td><td style='color:green'>[+]</td></tr>"

    for a in ausentes:
        filas += f"<tr style='background:#fff3f3'><td><b>{a}</b></td><td colspan='3' style='color:red'>— AUSENTE —</td><td>[-]</td></tr>"

    bloque_ausentes = ""
    if ausentes:
        bloque_ausentes = f"""
        <div style='padding:12px;background:#fff3e0;border-left:4px solid #ff9800;margin:10px 0'>
        [*] <b>Ausentes:</b> {", ".join(ausentes)}
        </div>"""

    return f"""
    <html><body style='font-family:Arial,sans-serif;max-width:680px;margin:auto'>
      <div style='background:#714B67;padding:18px;border-radius:8px 8px 0 0'>
        <h2 style='color:white;margin:0'>Sistema de Asistencia Facial</h2>
        <p style='color:#ddd;margin:4px 0 0'>Reporte diario — {fecha}</p>
      </div>
      <div style='padding:16px;background:#f5f5f5;border:1px solid #ddd'>
        <table style='width:100%;border-collapse:collapse'>
          <tr>
            <td style='text-align:center;padding:10px;background:#e8f5e9;border-radius:5px'>
              <b style='font-size:22px;color:green'>{len(registros)}</b><br>Presentes</td>
            <td style='width:10px'></td>
            <td style='text-align:center;padding:10px;background:#ffebee;border-radius:5px'>
              <b style='font-size:22px;color:red'>{len(ausentes)}</b><br>Ausentes</td>
            <td style='width:10px'></td>
            <td style='text-align:center;padding:10px;background:#e3f2fd;border-radius:5px'>
              <b style='font-size:22px;color:#1976D2'>{len(odoo["exitosos"])}</b><br>En Odoo</td>
          </tr>
        </table>
      </div>
      <div style='padding:16px'>
        <table style='width:100%;border-collapse:collapse;font-size:13px'>
          <thead><tr style='background:#714B67;color:white'>
            <th style='padding:8px;text-align:left'>Empleado</th>
            <th style='padding:8px'>Entrada</th><th style='padding:8px'>Salida</th>
            <th style='padding:8px'>Horas</th><th style='padding:8px'>Odoo</th>
          </tr></thead>
          <tbody>{filas}</tbody>
        </table>
      </div>
      {bloque_ausentes}
      <div style='padding:10px;text-align:center;color:#999;font-size:11px'>
        Generado: {datetime.now().strftime("%Y-%m-%d %H:%M")} — Sistema Asistencia Facial
      </div>
    </body></html>"""


def enviar_gmail(registros: list, ausentes: list, odoo: dict, csv_path: Path, fecha: str):
    demo = (GMAIL_SENDER == "tu_correo@gmail.com")

    print(f"{'─'*50}")
    print(f" GMAIL {'(MODO DEMO)' if demo else ''}")

    if demo:
        print(f"Destinatarios: {', '.join(DESTINATARIOS)}")
        print(f"Asunto: Reporte Asistencia — {fecha}")
        print(f"Presentes: {len(registros)} | Ausentes: {len(ausentes)} | Odoo: {len(odoo['exitosos'])}")
        print(f"Configura GMAIL_SENDER y GMAIL_PASSWORD para envío real")
        print(f"{'─'*50}")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Asistencia {fecha} — {len(registros)} presentes, {len(ausentes)} ausentes"
        msg["From"] = GMAIL_SENDER
        msg["To"] = ", ".join(DESTINATARIOS)
        msg.attach(MIMEText(_html_reporte(registros, ausentes, odoo, fecha), "html"))

        if csv_path.exists():
            with open(csv_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={csv_path.name}")
            msg.attach(part)

        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
            s.login(GMAIL_SENDER, GMAIL_PASSWORD)
            s.sendmail(GMAIL_SENDER, DESTINATARIOS, msg.as_string())

        print(f"Enviado a: {', '.join(DESTINATARIOS)}")
    except smtplib.SMTPAuthenticationError:
        print("Error auth — Ve a: Google Account → Seguridad → Contraseñas de aplicaciones")
    except Exception as e:
        print(f"Error: {e}")
    print(f"{'─'*50}")


#  ENROLAMIENTO — captura fotos nuevas personas
def enrolar_persona(nombre: str, num_fotos: int = 5):
    """
    Captura fotos desde cámara para registrar una nueva persona.
    Uso: python main.py enrolar "Juan Perez"
    """
    carpeta = KNOWN_FACES_DIR / nombre.replace(" ", "_")
    carpeta.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(0)
    count = 0
    print(f"\n[ENROLAMIENTO] Persona: {nombre}")
    print("Presiona ESPACIO para capturar foto | Q para terminar\n")

    while count < num_fotos:
        ret, frame = cap.read()
        if not ret:
            continue
        cv2.putText(frame, f"{nombre}  [{count}/{num_fotos}]", (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
        cv2.putText(frame, "ESPACIO = capturar  |  Q = salir", (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.imshow("Enrolamiento", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord(" "):
            path = carpeta / f"{count+1}.jpg"
            cv2.imwrite(str(path), frame)
            count += 1
            print(f"Foto {count} guardada")
        elif key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"\n[ENROLAMIENTO] Completado: {count} fotos → {carpeta}")


#  SISTEMA PRINCIPAL — Cámara en tiempo real
def ejecutar_sistema():
    KNOWN_FACES_DIR.mkdir(exist_ok=True)
    EXPORTS_DIR.mkdir(exist_ok=True)

    con = init_db()
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("No se pudo abrir la cámara.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    cooldown = {}
    frame_count = 0
    ANALIZAR_CADA = 10   # Analiza 1 de cada N frames para no saturar CPU

    print("\n" + "═"*50)
    print("SISTEMA DE ASISTENCIA FACIAL ACTIVO")
    print("  Q = salir  |  E = exportar + simular Odoo + Gmail")
    print("═"*50 + "\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        frame_count += 1
        display = frame.copy()

        if frame_count % ANALIZAR_CADA == 0:
            resultados = identificar_rostros(frame)

            for r in resultados:
                name = r["name"]
                conf = r["confidence"]
                x, y, w, h = r["bbox"]

                color = (0, 200, 0) if name != "Desconocido" else (0, 0, 220)
                cv2.rectangle(display, (x, y), (x+w, y+h), color, 2)
                cv2.putText(display, f"{name}  {conf:.0f}%", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

                if name != "Desconocido":
                    ahora = time.time()
                    if ahora - cooldown.get(name, 0) >= COOLDOWN_SEG:
                        accion = registrar_asistencia(con, name)
                        cooldown[name] = ahora
                        if accion != "ya_completo":
                            icono = "→ IN" if accion == "check_in" else "← OUT"
                            print(f"  {icono}  {name}  ({datetime.now().strftime('%H:%M:%S')})")

        cv2.putText(display, datetime.now().strftime("%Y-%m-%d  %H:%M:%S"),
                    (10, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        cv2.putText(display, "Q: salir  |  E: exportar + Odoo + Gmail",
                    (10, display.shape[0]-12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1)

        cv2.imshow("Sistema de Asistencia", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("e"):
            _exportar_y_notificar(con)

    cap.release()
    cv2.destroyAllWindows()
    print("\n[SISTEMA] Cerrando — exportando reporte final...")
    _exportar_y_notificar(con)
    con.close()


def _exportar_y_notificar(con):
    hoy = date.today().isoformat()
    registros = get_asistencias_hoy(con)

    if not registros:
        print("[EXPORT] Sin registros hoy.")
        return

    presentes = {r["name"] for r in registros}
    ausentes = []
    if KNOWN_FACES_DIR.exists():
        for carpeta in KNOWN_FACES_DIR.iterdir():
            if carpeta.is_dir():
                nombre = carpeta.name.replace("_", " ")
                if nombre not in presentes:
                    ausentes.append(nombre)

    csv_path = exportar_csv(registros, hoy)
    odoo = simular_odoo(csv_path, registros)
    enviar_gmail(registros, ausentes, odoo, csv_path, hoy)


#  PUNTO DE ENTRADA
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "enrolar":
        # python main.py enrolar "Juan Perez"
        nombre = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else input("Nombre completo: ")
        enrolar_persona(nombre)
    else:
        ejecutar_sistema()

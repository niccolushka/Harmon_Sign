"""Веб-приложение для визуализации гармонического сигнала и спектров."""

import json
import math
import mimetypes
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "harmonics.db"


def get_connection() -> sqlite3.Connection:
    """Создаёт подключение к SQLite с выдачей строк как словарей."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Создаёт таблицу гармоник и добавляет базовую гармонику при первом запуске."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS harmonics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amplitude REAL NOT NULL,
                frequency REAL NOT NULL,
                phase REAL NOT NULL,
                harmonic INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        count = connection.execute("SELECT COUNT(*) FROM harmonics").fetchone()[0]
        if count == 0:
            connection.execute(
                """
                INSERT INTO harmonics (amplitude, frequency, phase, harmonic, enabled)
                VALUES (?, ?, ?, ?, ?)
                """,
                (1.0, 5.0, 0.0, 1, 1),
            )
        connection.commit()


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Преобразует строку БД в JSON-совместимый словарь."""
    return {
        "id": row["id"],
        "amplitude": row["amplitude"],
        "frequency": row["frequency"],
        "phase": row["phase"],
        "harmonic": row["harmonic"],
        "enabled": bool(row["enabled"]),
    }


def validate_harmonic(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Проверяет параметры гармоники из запроса."""
    try:
        amplitude = float(payload.get("amplitude", 1))
        frequency = float(payload.get("frequency", 1))
        phase = float(payload.get("phase", 0))
        harmonic = int(payload.get("harmonic", 1))
        enabled = 1 if bool(payload.get("enabled", True)) else 0
    except (TypeError, ValueError):
        return None, "Амплитуда, частота, фаза и номер гармоники должны быть числами."

    if amplitude < 0:
        return None, "Амплитуда не может быть отрицательной."
    if frequency <= 0:
        return None, "Частота должна быть больше нуля."
    if harmonic <= 0:
        return None, "Номер гармоники должен быть положительным целым числом."

    return {
        "amplitude": amplitude,
        "frequency": frequency,
        "phase": phase,
        "harmonic": harmonic,
        "enabled": enabled,
    }, None


def fetch_harmonics() -> list[dict[str, Any]]:
    """Возвращает все сохранённые гармоники."""
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM harmonics ORDER BY id").fetchall()
    return [row_to_dict(row) for row in rows]


def build_signal(harmonics: list[dict[str, Any]]) -> dict[str, Any]:
    """Рассчитывает сигнал, спектр, чистый спектр и отфильтрованный спектр."""
    enabled = [item for item in harmonics if item["enabled"]]
    max_frequency = max((item["frequency"] * item["harmonic"] for item in enabled), default=10.0)
    duration = 1.0
    sample_count = 512
    cutoff_frequency = max_frequency * 0.65
    time_points: list[float] = []
    signal_points: list[float] = []
    filtered_points: list[float] = []

    for index in range(sample_count):
        time_value = duration * index / sample_count
        value = 0.0
        filtered_value = 0.0
        for item in enabled:
            actual_frequency = item["frequency"] * item["harmonic"]
            angle = 2 * math.pi * actual_frequency * time_value + math.radians(item["phase"])
            harmonic_value = item["amplitude"] * math.sin(angle)
            value += harmonic_value
            if actual_frequency <= cutoff_frequency:
                filtered_value += harmonic_value
        time_points.append(round(time_value, 5))
        signal_points.append(round(value, 5))
        filtered_points.append(round(filtered_value, 5))

    spectrum = []
    filtered_spectrum = []
    for item in enabled:
        actual_frequency = item["frequency"] * item["harmonic"]
        point = {"frequency": round(actual_frequency, 5), "amplitude": round(item["amplitude"], 5), "phase": round(item["phase"], 5)}
        spectrum.append(point)
        if actual_frequency <= cutoff_frequency:
            filtered_spectrum.append(point)

    return {
        "time": time_points,
        "signal": signal_points,
        "filteredSignal": filtered_points,
        "spectrum": spectrum,
        "pureSpectrum": spectrum,
        "filteredSpectrum": filtered_spectrum,
        "cutoffFrequency": round(cutoff_frequency, 5),
    }


class HarmonicHandler(BaseHTTPRequestHandler):
    """HTTP-обработчик страниц и JSON API."""

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.send_file(BASE_DIR / "templates" / "index.html", "text/html; charset=utf-8")
        elif path == "/api/harmonics":
            harmonics = fetch_harmonics()
            self.send_json({"harmonics": harmonics, "visualization": build_signal(harmonics)})
        elif path == "/api/export":
            self.send_json(fetch_harmonics())
        elif path.startswith("/static/"):
            self.send_static(path)
        else:
            self.send_json({"error": "Страница не найдена."}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/harmonics":
            self.send_json({"error": "Маршрут не найден."}, HTTPStatus.NOT_FOUND)
            return
        data, error = validate_harmonic(self.read_json())
        if error:
            self.send_json({"error": error}, HTTPStatus.BAD_REQUEST)
            return
        with get_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO harmonics (amplitude, frequency, phase, harmonic, enabled) VALUES (:amplitude, :frequency, :phase, :harmonic, :enabled)",
                data,
            )
            connection.commit()
        self.send_json({"id": cursor.lastrowid}, HTTPStatus.CREATED)

    def do_PUT(self) -> None:
        harmonic_id = self.parse_harmonic_id()
        if harmonic_id is None:
            self.send_json({"error": "Гармоника не найдена."}, HTTPStatus.NOT_FOUND)
            return
        data, error = validate_harmonic(self.read_json())
        if error:
            self.send_json({"error": error}, HTTPStatus.BAD_REQUEST)
            return
        with get_connection() as connection:
            cursor = connection.execute(
                """
                UPDATE harmonics
                SET amplitude = :amplitude, frequency = :frequency, phase = :phase, harmonic = :harmonic, enabled = :enabled
                WHERE id = :id
                """,
                {**data, "id": harmonic_id},
            )
            connection.commit()
        status = HTTPStatus.OK if cursor.rowcount else HTTPStatus.NOT_FOUND
        self.send_json({"status": "ok"} if cursor.rowcount else {"error": "Гармоника не найдена."}, status)

    def do_DELETE(self) -> None:
        harmonic_id = self.parse_harmonic_id()
        if harmonic_id is None:
            self.send_json({"error": "Гармоника не найдена."}, HTTPStatus.NOT_FOUND)
            return
        with get_connection() as connection:
            cursor = connection.execute("DELETE FROM harmonics WHERE id = ?", (harmonic_id,))
            connection.commit()
        status = HTTPStatus.OK if cursor.rowcount else HTTPStatus.NOT_FOUND
        self.send_json({"status": "ok"} if cursor.rowcount else {"error": "Гармоника не найдена."}, status)

    def parse_harmonic_id(self) -> int | None:
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) == 3 and parts[:2] == ["api", "harmonics"] and parts[2].isdigit():
            return int(parts[2])
        return None

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, path: str) -> None:
        file_path = (BASE_DIR / path.lstrip("/")).resolve()
        if not str(file_path).startswith(str((BASE_DIR / "static").resolve())) or not file_path.exists():
            self.send_json({"error": "Файл не найден."}, HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        self.send_file(file_path, content_type)


def run(host: str = "127.0.0.1", port: int = 5000) -> None:
    """Запускает локальный HTTP-сервер."""
    init_db()
    server = ThreadingHTTPServer((host, port), HarmonicHandler)
    print(f"Сервер запущен: http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()

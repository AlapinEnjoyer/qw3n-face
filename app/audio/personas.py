import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from app.config import PERSONAS_FILE


@dataclass
class Persona:
    name: str
    speaker: str
    language: str
    instruct: str
    created_at: str


class PersonaStore:
    def __init__(self) -> None:
        self._file = PERSONAS_FILE

    def _read(self) -> list[dict[str, str]]:
        if not self._file.exists():
            return []
        try:
            return json.loads(self._file.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _write(self, data: list[dict[str, str]]) -> None:
        self._file.write_text(json.dumps(data, indent=2))

    def all(self) -> list[Persona]:
        return [Persona(**d) for d in self._read()]

    def get(self, name: str) -> Persona | None:
        for d in self._read():
            if d.get("name") == name:
                return Persona(**d)
        return None

    def save(self, persona: Persona) -> None:
        data = self._read()
        for i, d in enumerate(data):
            if d.get("name") == persona.name:
                data[i] = asdict(persona)
                self._write(data)
                return
        data.append(asdict(persona))
        self._write(data)

    def delete(self, name: str) -> None:
        data = [d for d in self._read() if d.get("name") != name]
        self._write(data)


persona_store = PersonaStore()


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

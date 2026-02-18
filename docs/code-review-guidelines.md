# Code Review Guidelines

> Regelwerk für Code Reviews in Python-Projekten.
> Nutzbar von AI-Tools (z.B. Claude) und Menschen gleichermaßen.
>
> Stand: Februar 2026 | Python 3.11+

---

## Inhaltsverzeichnis

1. [Architekturprinzipien](#1-architekturprinzipien)
2. [Python Code Style & Qualität](#2-python-code-style--qualität)
3. [Type Hints](#3-type-hints)
4. [Projekt-Setup & Tooling](#4-projekt-setup--tooling)
5. [Dependency Management](#5-dependency-management)
6. [Testing](#6-testing)
7. [Sicherheit](#7-sicherheit)
8. [Review-Checkliste](#8-review-checkliste)

---

## 1. Architekturprinzipien

### KISS – Keep It Simple, Stupid

- Bevorzuge einfache Funktionen gegenüber komplexen Klassenhierarchien.
- Vermeide Metaclasses, komplexe Decorators und Descriptors, sofern sie kein reales Problem lösen.
- Pythons Lesbarkeit ist ein erstklassiger Wert: *„Simple is better than complex"* (PEP 20).
- Jede Abstraktion muss ihren Mehrwert gegenüber der einfachen Lösung rechtfertigen.

**Review-Frage:** *Gibt es eine einfachere Lösung, die denselben Zweck erfüllt?*

### DRY – Don't Repeat Yourself

- Gemeinsame Logik in Funktionen und Module extrahieren.
- `attrs`/`dataclasses` verwenden, um Boilerplate zu vermeiden.
- Helper-Methoden für wiederkehrende Muster (z.B. `_get_int()` / `_set_int()`).
- **Caveat:** Übertriebenes DRY kann Lesbarkeit verschlechtern. Drei ähnliche Zeilen sind besser als eine voreilige Abstraktion.

**Review-Frage:** *Gibt es duplizierten Code, der sinnvoll extrahiert werden kann – ohne die Lesbarkeit zu opfern?*

### YAGNI – You Ain't Gonna Need It

- Keine Features implementieren, die noch nicht gebraucht werden.
- Keine generischen Frameworks für Einmal-Operationen bauen.
- Keine Feature-Flags oder Backwards-Compatibility-Shims, wenn der Code direkt geändert werden kann.
- Keine hypothetischen Erweiterungspunkte.

**Review-Frage:** *Wird diese Funktionalität tatsächlich jetzt gebraucht, oder ist sie spekulativ?*

### SOLID (Python-spezifisch)

| Prinzip | Python-Anwendung |
|---|---|
| **SRP** – Single Responsibility | Jedes Modul/jede Klasse hat genau eine Verantwortung. Pythons Modulsystem macht das natürlich. |
| **OCP** – Open/Closed | `typing.Protocol` oder `abc.ABC` für Erweiterungspunkte, statt bestehenden Code zu modifizieren. |
| **LSP** – Liskov Substitution | Subklassen müssen für ihre Basistypen substituierbar sein. Besonders relevant bei Enums und Dataclasses. |
| **ISP** – Interface Segregation | `Protocol` (structural subtyping) statt fetter ABCs. Aufrufer hängen nur von den Methoden ab, die sie nutzen. |
| **DIP** – Dependency Inversion | Dependencies injizieren (als Parameter übergeben), nicht intern importieren und instanziieren. |

### Weitere Architekturmuster

- **Composition over Inheritance:** Bevorzuge Komposition und Delegation gegenüber tiefen Vererbungshierarchien.
- **Protocol over ABC:** `typing.Protocol` für Interfaces – flexibler, kein Vererbungszwang.
- **Functional Core / Imperative Shell:** I/O und Seiteneffekte an die Systemgrenze schieben. Business-Logik als reine Funktionen halten.
- **Kein globaler mutabler State:** Dependency Injection oder Context Manager verwenden.

---

## 2. Python Code Style & Qualität

### Linting & Formatting: Ruff

Ruff ist der aktuelle Standard-Linter und -Formatter für Python (2025+). Er ersetzt flake8, black, isort, pyupgrade und pydocstyle in einem einzigen Tool (10–100× schneller).

**Empfohlene Konfiguration in `pyproject.toml`:**

```toml
[tool.ruff]
target-version = "py311"
line-length = 88

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort (Import-Sortierung)
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "SIM",  # flake8-simplify
    "RUF",  # Ruff-eigene Regeln
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

**Review-Regeln:**

- Code muss `ruff check` und `ruff format --check` bestehen.
- Import-Sortierung folgt dem isort-Profil (stdlib → third-party → local).
- Keine `# noqa`-Kommentare ohne Begründung.
- Keine ungenutzten Imports oder Variablen.

### Naming Conventions (PEP 8)

| Element | Konvention | Beispiel |
|---|---|---|
| Module | `snake_case` | `client.py`, `dummy.py` |
| Klassen | `PascalCase` | `DeviceProfile`, `CommandCodes` |
| Funktionen/Methoden | `snake_case` | `detect_api_model()` |
| Konstanten | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_PORT` |
| Private Mitglieder | `_leading_underscore` | `_state`, `_get_int()` |
| Dunder-Methoden | `__double_underscore__` | `__init__`, `__repr__` |

- Kurze Namen (`cc`, `zn`, `e`) sind akzeptabel, wenn sie im Domain-Kontext etabliert sind.
- Boolean-Variablen sollten als Frage lesbar sein: `is_connected`, `has_data`.

### Error Handling

- Spezifische Exceptions fangen, niemals `except Exception` oder `except:` ohne Grund.
- Eigene Exception-Klassen für domain-spezifische Fehler definieren.
- `try`-Blöcke so klein wie möglich halten.
- Keine Exceptions zum Steuern des normalen Programmflusses verwenden.
- Logging vor Re-Raise verwenden, wenn Kontext verloren gehen könnte.

### Docstrings & Kommentare

- Öffentliche APIs sollten Docstrings haben (Modul, Klasse, öffentliche Methoden).
- Interne Helper brauchen keine Docstrings, wenn der Name selbsterklärend ist.
- Kommentare erklären *warum*, nicht *was* – der Code selbst erklärt das *was*.
- Keine auskommentierten Code-Blöcke committen.
- Keine `# TODO`-Kommentare ohne Issue-Referenz.

---

## 3. Type Hints

### Moderne Syntax (Python 3.10+)

```python
# RICHTIG – moderne Syntax
def process(value: int | None) -> str | int: ...
def get_items() -> list[str]: ...
def get_mapping() -> dict[str, int]: ...

# FALSCH – veraltete Syntax (nicht in neuem Code verwenden)
from typing import Optional, Union, List, Dict
def process(value: Optional[int]) -> Union[str, int]: ...
```

### Regeln

| Regel | Details |
|---|---|
| **PEP 604** | `X \| None` statt `Optional[X]`, `A \| B` statt `Union[A, B]` |
| **PEP 585** | `list[str]`, `dict[str, int]`, `tuple[int, ...]` statt `typing.List`, `typing.Dict` |
| **collections.abc** | `Callable`, `Sequence`, `Mapping`, `Iterator` aus `collections.abc` importieren, nicht aus `typing` |
| **PEP 673** | `Self` für Methoden, die die eigene Instanz zurückgeben (Python 3.11+) |
| **PEP 695** | `type Vector = list[float]` für Type Aliases (Python 3.12+) |

### Annotation-Strategie

- **Alle öffentlichen APIs** vollständig annotieren (Funktionssignaturen + Rückgabewerte).
- Interne Helper dürfen unannotiert bleiben, wenn es die Lesbarkeit verbessert.
- `Any` nur an Systemgrenzen verwenden (z.B. JSON-Deserialisierung vor Validierung).
- `TypedDict` für strukturierte Dict-Typen (Config, Protokoll-Daten).
- `Literal["on", "off"]` für String-/Int-Literaltypen.

### Type Checking

- **mypy** als CI-Gate (autoritativer Checker).
- **Pyright/Pylance** im Editor für schnelles Feedback.
- `py.typed` Marker-Datei für PEP 561 Kompatibilität in Libraries.
- Strikte mypy-Konfiguration anstreben:

```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true  # für neue Module
```

---

## 4. Projekt-Setup & Tooling

### pyproject.toml als Single Source of Truth

`pyproject.toml` ist die einzige Konfigurationsdatei für:
- Projekt-Metadaten und Dependencies
- Build-System-Konfiguration
- Tool-Konfigurationen (ruff, mypy, pytest, isort)

Keine separaten `setup.py`, `setup.cfg`, `requirements.txt`, `tox.ini`, `.flake8` oder `.mypy.ini` mehr verwenden.

### Build-Backend

| Backend | Einsatz |
|---|---|
| **uv_build** | Standard für neue Pure-Python-Projekte. Zero-Config, schnell, integriert mit `uv`. |
| **Hatchling** | Wenn Build-Hooks, VCS-basierte Versionierung oder Plugin-Erweiterbarkeit benötigt wird. |
| **setuptools** | Legacy-Projekte. Für neue Projekte nur mit guter Begründung. |

```toml
# Empfohlen für neue Projekte
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Package Manager: uv

`uv` (Astral, Rust-basiert) ist der empfohlene Package Manager (2025+). Er ersetzt pip, pip-tools, virtualenv und teilweise Poetry:

```bash
uv add attrs                     # Dependency hinzufügen
uv add --dev pytest ruff mypy    # Dev-Dependency hinzufügen
uv sync                          # Environment aus Lockfile erstellen
uv sync --locked                 # CI: Lockfile strikt enforced
uv run pytest                    # Kommando im venv ausführen
```

### Lock-File

- **`uv.lock` immer committen** – garantiert reproduzierbare Builds.
- Lockfile nie manuell editieren.
- In CI: `uv sync --locked` verwenden, um unbeabsichtigte Dependency-Änderungen zu erkennen.

### CI Pipeline (empfohlene Steps)

```yaml
steps:
  - run: uv sync --locked
  - run: uv run ruff check .
  - run: uv run ruff format --check .
  - run: uv run mypy src/
  - run: uv run pytest --cov --cov-fail-under=85
```

### Package Layout

- **`src/`-Layout** verwenden (verhindert versehentliche Imports aus dem Working Directory).
- `py.typed` Marker für Libraries, die Type Hints bereitstellen.
- `__all__` in `__init__.py` explizit definieren.

---

## 5. Dependency Management

### Versions-Strategie (Two-Layer-Ansatz)

```toml
# pyproject.toml – loose Constraints für Interoperabilität
[project]
dependencies = [
    "attrs>=22.1",            # Minimum-Version-Floor
    "aiohttp>=3.8,<4",       # Upper Bound bei bekannten Breaking Changes
]
```

Die exakte Auflösung aller transitiven Dependencies erfolgt im Lockfile (`uv.lock`).

### Review-Regeln für Dependencies

- **Minimale Dependencies:** Jede neue Runtime-Dependency muss begründet werden.
- **Keine unnötigen Extras:** Nur installieren, was tatsächlich gebraucht wird.
- **Upper Bounds sparsam setzen:** Nur bei bekannten Inkompatibilitäten. Zu enge Bounds verursachen Dependency-Konflikte.
- **Dev-Dependencies trennen:** Test- und Entwicklungstools gehören in `[project.optional-dependencies]` oder `[dependency-groups]`, nicht in die Runtime-Dependencies.
- **Transitive Dependencies nicht direkt importieren:** Nur explizit deklarierte Dependencies im Code verwenden.

### Vulnerability Scanning

In der CI-Pipeline regelmäßig auf bekannte Schwachstellen prüfen:

```bash
uv run pip-audit              # Prüft gegen Python Packaging Advisory Database
# oder
uv-secure uv.lock            # Prüft Lockfile direkt
```

- **GitHub Dependabot** aktivieren für automatische PRs bei Sicherheitsupdates.
- Bei Vulnerability-Fund: Severity bewerten und zeitnah patchen.

### Dependency Review bei PRs

Wenn ein PR Dependencies ändert, prüfen:

1. Ist die neue Dependency wirklich notwendig, oder kann stdlib das?
2. Wie aktiv wird das Paket gepflegt? (Letzte Releases, offene Issues)
3. Wie groß ist der Dependency Tree? (transitive Dependencies)
4. Ist die Lizenz kompatibel?
5. Gibt es bekannte Sicherheitsprobleme?

---

## 6. Testing

### Framework & Konfiguration

- **pytest** als Test-Framework (Standard).
- Konfiguration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"        # Async Tests ohne @pytest.mark.asyncio
testpaths = ["tests"]
```

### Test-Organisation

```
tests/
    conftest.py              # Nur projektweite Fixtures
    test_core.py
    test_protocol.py
    integration/
        conftest.py          # Integrationsspezifische Fixtures
        test_api.py
```

- `conftest.py` pro Verzeichnis – Fixtures dort platzieren, wo sie gebraucht werden.
- Nicht alle Fixtures in die Root-`conftest.py` packen.

### Fixture-Patterns

**Factory Fixtures** (empfohlen für parametrische Testobjekte):

```python
@pytest.fixture
def make_state():
    def _make_state(zn=1, api_model=ApiModel.APIHDA_SERIES):
        client = MagicMock(spec=Client)
        client.request = AsyncMock()
        return State(client, zn, api_model)
    return _make_state
```

**Yield Fixtures** für Cleanup:

```python
@pytest.fixture
async def client():
    async with AsyncClient() as c:
        yield c
    # Cleanup passiert automatisch
```

**Fixture Scopes bewusst wählen:**

| Scope | Einsatz |
|---|---|
| `function` (default) | Frisch für jeden Test. Standard für mutablen State. |
| `module` | Geteilt für alle Tests einer Datei. Gut für teure, read-only Setups. |
| `session` | Geteilt für gesamten Testlauf. Nur für wirklich teure globale Setups. |

### Async Testing

- `asyncio_mode = "auto"` in der pytest-Konfiguration – kein `@pytest.mark.asyncio` Decorator nötig.
- `AsyncMock` aus `unittest.mock` für async Callables.
- `@pytest_asyncio.fixture` (nicht `@pytest.fixture`) für async Fixtures.

### Mocking

- `unittest.mock.MagicMock` und `AsyncMock` als Standard.
- **`spec=` Parameter immer verwenden** – stellt sicher, dass nur existierende Attribute gemockt werden.
- Mocks so schmal wie möglich: nur das mocken, was für den Test nötig ist.
- Externes I/O mocken (Netzwerk, Dateisystem), interne Logik nicht.

### Coverage

- **Ziel: 85%+** für Library-Code.
- Coverage als CI-Gate: `pytest --cov --cov-fail-under=85`.
- Coverage allein ist kein Qualitätsmaß – Tests müssen auch sinnvolle Assertions enthalten.
- Edge Cases und Fehlerpfade testen, nicht nur Happy Path.

### Review-Regeln für Tests

- Jeder PR mit Codeänderungen sollte entsprechende Tests enthalten.
- Tests müssen isoliert und idempotent sein (keine Abhängigkeiten zwischen Tests).
- Test-Namen beschreiben das erwartete Verhalten: `test_volume_clamps_to_max_when_exceeded`.
- Keine Magic Numbers in Tests – Konstanten oder sprechende Variablen verwenden.
- Arrange-Act-Assert-Pattern einhalten.
- Keine `time.sleep()` in Tests – async Waits oder Mocks verwenden.

---

## 7. Sicherheit

### Allgemeine Regeln

- **Keine Secrets im Code oder in Commits:** API-Keys, Passwörter, Tokens gehören in Umgebungsvariablen oder Secret-Manager.
- **`.gitignore` prüfen:** `.env`, Credential-Dateien und IDE-Configs müssen ausgeschlossen sein.
- **Keine hartcodierten Pfade oder Konfigurationen**, die sicherheitsrelevant sind.

### Input-Validierung

- An **Systemgrenzen** validieren: User-Input, externe APIs, Netzwerk-Daten, Datei-Inhalte.
- Internem Code und Framework-Garantien vertrauen – nicht alles doppelt validieren.
- Bei Protokoll-Implementierungen: Puffer-Grenzen prüfen, unerwartete Datenformate abfangen.

### OWASP-Awareness

Für Projekte mit Netzwerk-Kommunikation oder Web-Schnittstellen:

- **Injection:** Input nie ungeprüft in Queries oder Kommandos einbauen.
- **Broken Authentication:** Sichere Token-Generierung, Session-Management.
- **Sensitive Data Exposure:** Keine sensiblen Daten in Logs oder Fehlermeldungen.
- **XML External Entities:** `defusedxml` statt `xml.etree` für externe XML-Daten.

### Dependency-Sicherheit

- Regelmäßig `pip-audit` oder `uv-secure` ausführen.
- Dependabot-Alerts zeitnah bearbeiten.
- Bei Sicherheitslücken in Dependencies: Patch oder Workaround priorisieren.

---

## 8. Review-Checkliste

Kompakte Checkliste für jedes Code Review. Jeder Punkt sollte mit "Ja" beantwortet werden können:

### Korrektheit
- [ ] Code tut, was er soll (Anforderung erfüllt)
- [ ] Edge Cases werden behandelt
- [ ] Fehlerpfade sind abgedeckt
- [ ] Keine off-by-one Fehler oder Boundary Issues

### Architektur
- [ ] KISS: Einfachste Lösung für das Problem
- [ ] DRY: Keine unnötige Duplikation
- [ ] YAGNI: Keine spekulativen Features
- [ ] SRP: Jedes Modul/jede Klasse hat eine klare Verantwortung
- [ ] Keine tiefen Vererbungshierarchien

### Code-Qualität
- [ ] Sprechende Namen (Variablen, Funktionen, Klassen)
- [ ] Ruff-clean (keine Linting-Fehler)
- [ ] Type Hints vorhanden (öffentliche APIs)
- [ ] Moderne Python-Syntax (PEP 604, PEP 585)
- [ ] Keine auskommentierten Code-Blöcke

### Tests
- [ ] Tests für neue/geänderte Funktionalität vorhanden
- [ ] Tests sind isoliert und idempotent
- [ ] Edge Cases und Fehlerpfade getestet
- [ ] Coverage nicht gesunken
- [ ] Sinnvolle Assertions (nicht nur "läuft ohne Exception")

### Dependencies
- [ ] Neue Dependencies begründet
- [ ] Keine transitive Dependency direkt importiert
- [ ] Lockfile aktualisiert (wenn Dependencies geändert)

### Sicherheit
- [ ] Keine Secrets im Code
- [ ] Input an Systemgrenzen validiert
- [ ] Keine bekannten Vulnerabilities in neuen Dependencies

### Dokumentation
- [ ] Öffentliche APIs haben Docstrings
- [ ] Komplexe Logik ist kommentiert (*warum*, nicht *was*)
- [ ] Breaking Changes sind dokumentiert

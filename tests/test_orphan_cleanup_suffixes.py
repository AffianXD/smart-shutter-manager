"""Regressionstest fuer den Bug 'Positions-Quelle & Zielposition nicht
nutzbar' (v0.15.5 -> v0.15.6): _async_cleanup_orphaned_profile_entities
in __init__.py kannte nur die fixen (nicht profilgebundenen) Select-
Suffixe {"source", "type"} - "position_source" (PositionSourceSelect)
fehlte, wodurch JEDE PositionSourceSelect-Entity bei jedem HA-Start als
vermeintlich verwaistes Profil sofort wieder geloescht wurde. Keine
Fehlermeldung, keine Exception - reine stille Fehlklassifikation.

Statt das komplette __init__.py mit all seinen HA-Abhaengigkeiten zu
importieren (Config-Entries, Panel-Registrierung, Services, ...), wird
hier direkt der Quelltext auf die Menge 'fixed_suffixes' geprueft: JEDER
tatsaechlich im Code verwendete, nicht profilgebundene Select-Suffix
MUSS darin enthalten sein. Wird kuenftig ein neuer solcher Suffix
eingefuehrt (z.B. fuer ein weiteres Feature), MUSS er hier UND in
fixed_suffixes ergaenzt werden - der Test macht genau diese Kopplung
sichtbar, statt sie erneut stillschweigend auseinanderlaufen zu lassen.
"""
import re
import sys
from pathlib import Path

PKG_DIR = str(Path(__file__).resolve().parents[1] / "custom_components/smart_shutter")

failures = 0


def check(name, cond):
    global failures
    status = "OK  " if cond else "FAIL"
    if not cond:
        failures += 1
    print(f"{status} - {name}")


with open(f"{PKG_DIR}/__init__.py", encoding="utf-8") as f:
    init_src = f.read()

match = re.search(r"fixed_suffixes\s*=\s*\{([^}]*)\}", init_src)
check("fixed_suffixes-Definition in __init__.py gefunden", match is not None)

fixed_suffixes = set()
if match:
    fixed_suffixes = {s.strip().strip("'\"") for s in match.group(1).split(",") if s.strip()}
    print(f"     gefundene fixed_suffixes: {sorted(fixed_suffixes)}")

# Alle aktuell im Code tatsaechlich verwendeten, NICHT profilgebundenen
# Select-Suffixe (Form "{device_id}_{open|close}_<suffix>", OHNE
# Profil-Bindung). Bei jedem neuen derartigen Select-Typ: hier UND in
# __init__.py.fixed_suffixes ergaenzen.
known_fixed_suffixes = {
    "source",          # ShutterSourceSelect (open_source/close_source)
    "type",            # LocalActionTypeSelect (open_type/close_type)
    "position_source",  # PositionSourceSelect (open_position_source/close_position_source)
}

for suffix in sorted(known_fixed_suffixes):
    check(
        f"Suffix '{suffix}' ist in fixed_suffixes enthalten (sonst wird die Entity als verwaist geloescht)",
        suffix in fixed_suffixes,
    )

# Zusaetzlich: direkt in select.py nach tatsaechlich erzeugten
# registry_key-Mustern suchen und sicherstellen, dass keiner davon
# unentdeckt an fixed_suffixes vorbeirutscht (sofern er nicht offensichtlich
# profilgebunden ist, erkennbar an "profile" im Funktionsnamen/Kontext).
with open(f"{PKG_DIR}/const.py", encoding="utf-8") as f:
    const_src = f.read()

registry_key_fns = re.findall(r'def (\w*registry_key)\(action: str\) -> str:\s*\n\s*return f"([^"]*)"', const_src)
check("mindestens die bekannten registry_key-Funktionen in const.py gefunden", len(registry_key_fns) >= 2)
# _async_cleanup_orphaned_profile_entities betrachtet NUR domain in
# ("select", "time") - registry_key-Funktionen, die ausschliesslich fuer
# number.py-Entities verwendet werden (aktuell: position_registry_key,
# fuer die Zielposition-NUMBER-Entity), sind fuer diese Cleanup-Routine
# irrelevant und daher hier bewusst ausgenommen.
NUMBER_DOMAIN_ONLY_FNS = {"position_registry_key"}
for fn_name, fmt in registry_key_fns:
    if fn_name in NUMBER_DOMAIN_ONLY_FNS:
        continue
    # fmt sieht z.B. so aus: "{action}_position_source" -> Suffix nach
    # "{action}_" abschneiden.
    suffix = fmt.split("{action}_", 1)[-1] if "{action}_" in fmt else None
    if suffix is None:
        continue
    check(
        f"registry_key-Funktion '{fn_name}' (Suffix '{suffix}') ist in fixed_suffixes beruecksichtigt",
        suffix in fixed_suffixes,
    )

print(f"\n{'ALLE TESTS OK' if failures == 0 else str(failures) + ' FEHLGESCHLAGEN'}")
sys.exit(0 if failures == 0 else 1)

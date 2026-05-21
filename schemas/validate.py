import json
import sys
from pathlib import Path
from pydantic import ValidationError
from schemas.models import BOMComponent, RiskReport


def validate_bom(filepath: str) -> list[BOMComponent]:
    path = Path(filepath)
    if not path.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    raw = json.loads(path.read_text())

    components = []
    errors = []

    items = raw if isinstance(raw, list) else raw.get("components", [])

    for i, item in enumerate(items):
        try:
            components.append(BOMComponent(**item))
        except ValidationError as e:
            errors.append(f"Component {i} ({item.get('component_name', '?')}): {e}")

    if errors:
        print(f"VALIDATION FAILED — {len(errors)} error(s):\n")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)

    print(f"OK — {len(components)} component(s) validated with zero errors")
    for c in components:
        print(f"  {c.component_name} | {c.material_name} | {c.quantity_kg} kg | {c.supplier_country}")
    return components


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m schemas.validate <path/to/bom.json>")
        sys.exit(1)
    validate_bom(sys.argv[1])

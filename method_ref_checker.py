import re
import sys


def main():
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()

    defined = set(re.findall(r"^\s*(?:static\s+|async\s+|get\s+|set\s+)*([A-Za-z_$][\w$]*)\s*\(", src, re.MULTILINE))
    defined |= set(re.findall(r"^\s*([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(", src, re.MULTILINE))

    called = set(re.findall(r"this\.([A-Za-z_$][\w$]*)\s*\(", src))

    missing = sorted(m for m in called if m not in defined)

    native_apis = {"attachShadow", "dispatchEvent", "addEventListener", "removeEventListener", "getRootNode"}
    missing = [m for m in missing if m not in native_apis]

    if missing:
        print(f"{len(missing)} possibly undefined method references found:")
        for m in missing:
            print(f"  this.{m}(...)")
        sys.exit(1)
    else:
        print(f"Method reference check OK: {len(called)} this._method() calls checked, all defined")
        sys.exit(0)


if __name__ == "__main__":
    main()

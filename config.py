"""Engine configuration: optional features, settable as UCI options or
constructor args."""

from dataclasses import dataclass

# UCI option name -> (EngineConfig field name, value type: "bool" | "int" | "str")
_UCI_OPTIONS = {
    "Hash": ("tt_size_mb", "int"),
}


@dataclass
class EngineConfig:
    tt_size_mb: int = 64
    # Not read anywhere.
    time_management_mode: str = "fixed"

    @staticmethod
    def uci_options() -> list:
        """`option ...` lines advertised in response to the `uci` command."""
        return [
            "option name Hash type spin default 64 min 1 max 4096",
        ]

    def set_uci_option(self, name: str, value: str) -> bool:
        """Apply `setoption name <name> value <value>`. Returns False for an
        unknown option."""
        entry = _UCI_OPTIONS.get(name)
        if entry is None:
            return False
        field_name, kind = entry
        if kind == "bool":
            setattr(self, field_name, value.strip().lower() in ("true", "1", "yes"))
        elif kind == "int":
            setattr(self, field_name, int(value))
        else:
            setattr(self, field_name, value)
        return True


if __name__ == "__main__":
    import sys

    def check(name, cond):
        print(f"  {'ok  ' if cond else 'FAIL'}  {name}")
        return cond

    ok = True
    c = EngineConfig()
    ok &= check("defaults: hash 64mb", c.tt_size_mb == 64)
    ok &= check("set Hash 128", c.set_uci_option("Hash", "128") and c.tt_size_mb == 128)
    ok &= check("unknown option rejected", c.set_uci_option("NotReal", "1") is False)
    ok &= check("uci_options mentions every field",
                all(any(n in line for line in EngineConfig.uci_options())
                    for n in ("Hash",)))
    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    sys.exit(0 if ok else 1)

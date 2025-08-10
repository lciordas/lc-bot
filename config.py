"""Engine configuration: optional features, settable as UCI options or
constructor args."""

from dataclasses import dataclass

# UCI option name -> (EngineConfig field name, value type: "bool" | "int" | "str")
_UCI_OPTIONS = {
    "Hash": ("tt_size_mb", "int"),
    "OwnBook": ("use_opening_book", "bool"),
    "BookPath": ("book_path", "str"),
    "UseTablebase": ("use_tablebase", "bool"),
    "TablebasePath": ("tablebase_path", "str"),
    "UseNNUE": ("use_nnue", "bool"),
    "NNUEPath": ("nnue_path", "str"),
    "NNUEMode": ("nnue_mode", "str"),
}


@dataclass
class EngineConfig:
    use_opening_book: bool = False
    book_path: str = ""
    use_tablebase: bool = False
    tablebase_path: str = ""
    # NNUE is off by default; the hand-written eval is the fallback.
    use_nnue: bool = False
    nnue_path: str = ""
    nnue_mode: str = "hybrid"     # "hybrid" (base eval + residual) or "pure"
    tt_size_mb: int = 64
    # Not read anywhere.
    time_management_mode: str = "fixed"

    @staticmethod
    def uci_options() -> list:
        """`option ...` lines advertised in response to the `uci` command."""
        return [
            "option name Hash type spin default 64 min 1 max 4096",
            "option name OwnBook type check default false",
            "option name BookPath type string default <empty>",
            "option name UseTablebase type check default false",
            "option name TablebasePath type string default <empty>",
            "option name UseNNUE type check default false",
            "option name NNUEPath type string default <empty>",
            "option name NNUEMode type combo default hybrid var hybrid var pure",
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
    ok &= check("defaults: book/tablebase off", not c.use_opening_book and not c.use_tablebase)
    ok &= check("defaults: hash 64mb", c.tt_size_mb == 64)
    ok &= check("set OwnBook true", c.set_uci_option("OwnBook", "true") and c.use_opening_book)
    ok &= check("set UseTablebase true", c.set_uci_option("UseTablebase", "true") and c.use_tablebase)
    ok &= check("set Hash 128", c.set_uci_option("Hash", "128") and c.tt_size_mb == 128)
    ok &= check("set BookPath", c.set_uci_option("BookPath", "/tmp/x.bin") and c.book_path == "/tmp/x.bin")
    ok &= check("unknown option rejected", c.set_uci_option("NotReal", "1") is False)
    ok &= check("uci_options mentions every field",
                all(any(n in line for line in EngineConfig.uci_options())
                    for n in ("Hash", "OwnBook", "BookPath", "UseTablebase", "TablebasePath")))
    print(f"\n{'ALL PASS' if ok else 'FAILURES PRESENT'}")
    sys.exit(0 if ok else 1)

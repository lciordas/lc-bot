"""Attack tables: lookup tables for leapers, magic bitboards for sliders.

Python ints don't wrap, so `occ * magic` is masked with `& _FULL` before the shift.
"""

import random

from constants import (
    BLACK, WHITE, FULL_BB,
    NOT_FILE_A, NOT_FILE_H, NOT_FILE_AB, NOT_FILE_GH,
)
from bitboard import popcount

_FULL = FULL_BB


# --- Leaper attack tables (built at import) ---

def _build_king_attacks():
    table = [0] * 64
    for sq in range(64):
        bb = 1 << sq
        a = 0
        a |= (bb << 8)
        a |= (bb >> 8)
        a |= (bb << 1) & NOT_FILE_A
        a |= (bb >> 1) & NOT_FILE_H
        a |= (bb << 9) & NOT_FILE_A
        a |= (bb << 7) & NOT_FILE_H
        a |= (bb >> 7) & NOT_FILE_A
        a |= (bb >> 9) & NOT_FILE_H
        table[sq] = a & FULL_BB
    return table


def _build_knight_attacks():
    table = [0] * 64
    for sq in range(64):
        bb = 1 << sq
        a = 0
        a |= (bb << 17) & NOT_FILE_A      # NNE
        a |= (bb << 15) & NOT_FILE_H      # NNW
        a |= (bb << 10) & NOT_FILE_AB     # ENE
        a |= (bb << 6) & NOT_FILE_GH      # WNW
        a |= (bb >> 6) & NOT_FILE_AB      # ESE
        a |= (bb >> 10) & NOT_FILE_GH     # WSW
        a |= (bb >> 15) & NOT_FILE_A      # SSE
        a |= (bb >> 17) & NOT_FILE_H      # SSW
        table[sq] = a & FULL_BB
    return table


def _build_pawn_attacks():
    """PAWN_ATTACKS[color][sq] = squares a pawn of `color` on `sq` attacks."""
    white = [0] * 64
    black = [0] * 64
    for sq in range(64):
        bb = 1 << sq
        white[sq] = (((bb << 7) & NOT_FILE_H) | ((bb << 9) & NOT_FILE_A)) & FULL_BB
        black[sq] = (((bb >> 7) & NOT_FILE_A) | ((bb >> 9) & NOT_FILE_H)) & FULL_BB
    return (white, black)


KING_ATTACKS = _build_king_attacks()
KNIGHT_ATTACKS = _build_knight_attacks()
PAWN_ATTACKS = _build_pawn_attacks()  # PAWN_ATTACKS[color][sq]


# --- Sliding-piece ray attacks (table builder + verification reference) ---

# (df, dr) per direction
_ROOK_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
_BISHOP_DIRS = ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _ray_attacks(sq: int, dirs, occupancy: int) -> int:
    """Attack set by walking each ray until (and including) the first blocker."""
    attacks = 0
    sf = sq & 7
    sr = sq >> 3
    for df, dr in dirs:
        f, r = sf + df, sr + dr
        while 0 <= f < 8 and 0 <= r < 8:
            t = r * 8 + f
            attacks |= (1 << t)
            if occupancy & (1 << t):
                break
            f += df
            r += dr
    return attacks


# --- Magic bitboards ---

def _relevant_mask(sq: int, dirs) -> int:
    """Occupancy bits that matter for `sq`: each ray minus its edge square."""
    mask = 0
    sf, sr = sq & 7, sq >> 3
    for df, dr in dirs:
        f, r = sf + df, sr + dr
        while 0 <= f < 8 and 0 <= r < 8:
            nf, nr = f + df, r + dr
            if not (0 <= nf < 8 and 0 <= nr < 8):
                break  # edge square
            mask |= 1 << (r * 8 + f)
            f, r = nf, nr
    return mask


def _subsets(mask: int):
    """Yield every subset of `mask` (Carry-Rippler), including 0 and the full set."""
    sub = 0
    while True:
        yield sub
        sub = (sub - mask) & mask
        if sub == 0:
            break


def _find_magic(sq: int, dirs, rng) -> tuple:
    """Search for a collision-free magic for `sq`. Returns (magic, shift, mask, table)."""
    mask = _relevant_mask(sq, dirs)
    bits = popcount(mask)
    shift = 64 - bits
    occs = list(_subsets(mask))
    atts = [_ray_attacks(sq, dirs, o) for o in occs]
    size = 1 << bits
    for _ in range(10_000_000):
        # Sparse candidates are far more likely to work.
        magic = rng.getrandbits(64) & rng.getrandbits(64) & rng.getrandbits(64)
        if popcount((mask * magic) & 0xFF00000000000000) < 6:
            continue
        table = [0] * size
        used = [False] * size
        ok = True
        for o, a in zip(occs, atts):
            idx = (((o * magic) & _FULL) >> shift)
            if not used[idx]:
                used[idx] = True
                table[idx] = a
            elif table[idx] != a:
                ok = False
                break
        if ok:
            return magic, shift, mask, table
    raise RuntimeError(f"no magic found for square {sq}")


def _build_magics(dirs, rng):
    magics = [0] * 64
    shifts = [0] * 64
    masks = [0] * 64
    tables = [None] * 64
    for sq in range(64):
        magics[sq], shifts[sq], masks[sq], tables[sq] = _find_magic(sq, dirs, rng)
    return magics, shifts, masks, tables


# Found by _build_magics with seed 0xBEEF1234; regenerate with `python3 attacks.py regen`.
_ROOK_MAGIC = (
    0x0080008040002011, 0x0300208302400010, 0x8100200011000840, 0x0480044800100080,
    0x4380040028000280, 0x0200020064082110, 0x0080020001000080, 0x0600040041008022,
    0x1004800280754004, 0x0180804000802004, 0x1042001040208208, 0x04A2000C12002040,
    0x8020800800040080, 0x9001000900020400, 0x0404000108700204, 0x8041000100165882,
    0x0009020020408208, 0x2000444004201000, 0x0000410011002000, 0x2040808008001001,
    0x0004008004080080, 0x0401010002080400, 0x0000040090080201, 0x1000120000A84104,
    0x0840800100204100, 0x1048288300400100, 0x9040100080200080, 0x40100091000AA102,
    0xC008008080080401, 0xB023020080040080, 0x000F502400120198, 0x0850010200249044,
    0x0080002000400050, 0x00A0005001400020, 0x0002900082802000, 0x4040100A02004020,
    0x0418800400800800, 0x420200D0AA001804, 0x0800300184000A48, 0x0809140382002441,
    0x4200288040048000, 0x0000201000404001, 0x001D204200820011, 0x0010000815010020,
    0x0001000800050010, 0x0000020004008080, 0x2422108128240002, 0x0084108841060014,
    0x2146400180002880, 0x8000400020100040, 0x0080807000600180, 0x0000801000080280,
    0x0405080181040080, 0x0002000400800280, 0x0000300802410400, 0x0100891184C40200,
    0x0800410480102602, 0x4000421220810202, 0x3804100820034101, 0x1400100020050009,
    0x1216000410200802, 0x0402000108441082, 0x00020B4800901204, 0x0480102308824C06,
)
_BISHOP_MAGIC = (
    0x02042C00822A0200, 0x2023100420828100, 0x0070011065020002, 0x04182241C1800000,
    0x0401104000130280, 0x002088200A044140, 0x0000880808442200, 0x10008A0100824000,
    0x00500450A2480100, 0x0001880141220200, 0x80001020C0810028, 0x000444041080900C,
    0x0000040504000800, 0x0005008210400010, 0x4040211088844000, 0x0010010101100200,
    0x4C20045004812821, 0x0820001024011058, 0x200A430808010121, 0x001402880C101260,
    0x0006000C02110100, 0x0042412808080C00, 0x2804000842084400, 0x420026C842023000,
    0x0220041308900440, 0x0041200428088100, 0x3082088011040400, 0x0C08088288020002,
    0x140084000B802000, 0x0010002010441000, 0x4418020000824104, 0x0410408902020150,
    0x2008020800400940, 0x11009004022848A8, 0x200C002808040044, 0x2000100820440400,
    0x0440010010010040, 0x0020008100182410, 0x4046060C40122802, 0x0061010820220220,
    0x4002622004106048, 0x0080420210402000, 0x81C5018241121000, 0x0000419144010805,
    0x0000012212002402, 0x0112281005000020, 0x82502420840000A0, 0x0010408089100082,
    0x4002082282100001, 0x000C440098280020, 0x0400104218B02020, 0x00C0948042020000,
    0x001C989002021000, 0x441C085010508002, 0x4220044102240045, 0x8420080881045095,
    0x410CA08808311000, 0x2000202218040404, 0x1200004080480820, 0x00000300D0840400,
    0x0504000242028200, 0x0000E09060010110, 0x8000045042880100, 0x0420201102108010,
)


def _build_from_magics(dirs, magics):
    """Build (shifts, masks, tables) from the embedded magics, checking for collisions."""
    shifts = [0] * 64
    masks = [0] * 64
    tables = [None] * 64
    for sq in range(64):
        mask = _relevant_mask(sq, dirs)
        shift = 64 - popcount(mask)
        magic = magics[sq]
        table = [0] * (1 << popcount(mask))
        used = [False] * len(table)
        for o in _subsets(mask):
            idx = (((o * magic) & _FULL) >> shift)
            a = _ray_attacks(sq, dirs, o)
            if used[idx] and table[idx] != a:
                raise RuntimeError(f"embedded magic collision at square {sq}")
            used[idx] = True
            table[idx] = a
        masks[sq], shifts[sq], tables[sq] = mask, shift, table
    return shifts, masks, tables


_ROOK_SHIFT, _ROOK_MASK, _ROOK_TABLE = _build_from_magics(_ROOK_DIRS, _ROOK_MAGIC)
_BISHOP_SHIFT, _BISHOP_MASK, _BISHOP_TABLE = _build_from_magics(_BISHOP_DIRS, _BISHOP_MAGIC)


def rook_attacks(sq: int, occupancy: int) -> int:
    return _ROOK_TABLE[sq][(((occupancy & _ROOK_MASK[sq]) * _ROOK_MAGIC[sq]) & _FULL) >> _ROOK_SHIFT[sq]]


def bishop_attacks(sq: int, occupancy: int) -> int:
    return _BISHOP_TABLE[sq][(((occupancy & _BISHOP_MASK[sq]) * _BISHOP_MAGIC[sq]) & _FULL) >> _BISHOP_SHIFT[sq]]


def queen_attacks(sq: int, occupancy: int) -> int:
    return rook_attacks(sq, occupancy) | bishop_attacks(sq, occupancy)


# --- Self-test: magic lookups must equal the ray reference everywhere ---

def attacks_selftest(samples_per_square: int = 200) -> bool:
    """Check magic lookups against the ray walker on every square. True iff all match."""
    rng = random.Random(0xA77AC)
    ok = True
    for sq in range(64):
        trials = [0, _FULL, _ROOK_MASK[sq], _BISHOP_MASK[sq]]
        trials += [rng.getrandbits(64) for _ in range(samples_per_square)]
        for occ in trials:
            if rook_attacks(sq, occ) != _ray_attacks(sq, _ROOK_DIRS, occ):
                ok = False
            if bishop_attacks(sq, occ) != _ray_attacks(sq, _BISHOP_DIRS, occ):
                ok = False
    return ok


if __name__ == "__main__":
    import sys
    import time
    if len(sys.argv) > 1 and sys.argv[1] == "regen":
        rng = random.Random(0xBEEF1234)
        rook_magics = _build_magics(_ROOK_DIRS, rng)[0]
        bishop_magics = _build_magics(_BISHOP_DIRS, rng)[0]
        for name, arr in (("_ROOK_MAGIC", rook_magics), ("_BISHOP_MAGIC", bishop_magics)):
            print(name + " = (")
            for i in range(0, 64, 4):
                print("    " + ", ".join("0x%016X" % m for m in arr[i:i + 4]) + ",")
            print(")")
        sys.exit(0)
    t0 = time.perf_counter()
    passed = attacks_selftest()
    dt = time.perf_counter() - t0
    rook_entries = sum(len(t) for t in _ROOK_TABLE)
    bishop_entries = sum(len(t) for t in _BISHOP_TABLE)
    print(f"magic vs ray reference: {'ALL MATCH' if passed else 'MISMATCH'}  ({dt:.2f}s)")
    print(f"table sizes: rook {rook_entries} entries, bishop {bishop_entries} entries")
    sys.exit(0 if passed else 1)

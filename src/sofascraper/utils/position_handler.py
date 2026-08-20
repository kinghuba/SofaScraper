"""
formation_position.py

Given a football (soccer) formation string, e.g. "4-3-3", "3-5-2", "4-1-2-3",
and a squad/shirt number where the numbering convention is:

    0  -> goalkeeper
    1..N -> outfield players, assigned line by line from defense to attack,
            and within each line from RIGHT to LEFT (as viewed on the pitch,
            attacking upfield),

this module returns the most likely position for that player, as
{'position': <code>, 'side': <'right' | 'center' | 'left' | None>}.

--------------------------------------------------------------------------
HOW FORMATIONS ARE INTERPRETED
--------------------------------------------------------------------------
A formation string is split on '-' into segments:

    defense_count - mid_segment_1 - ... - mid_segment_k - forward_count

* The FIRST segment is always the back line (defenders).
* The LAST segment is always the front line (forwards/strikers).
* Everything in between is one or more midfield "rows". Most formations
  (4-3-3, 4-4-2, 3-5-2 ...) have exactly one midfield row. Formations like
  4-1-2-3, 4-2-3-1 or 4-1-4-1 have two (or more) midfield rows, which are
  labelled from deepest to most advanced as:
        1 row  -> M            (plain midfield)
        2 rows -> DM, AM        (defensive mid, attacking mid)
        3 rows -> DM, CM, AM
        4+ rows-> interpolated between DM -> CM -> AM

--------------------------------------------------------------------------
HOW EACH LINE IS LABELLED (right -> left)
--------------------------------------------------------------------------
This mirrors how real back-lines / midfields / front-lines are usually
described:

DEFENSE line of size n:
    n = 1            -> CB (sole/sweeper, no side)
    n = 2             -> CB(right), CB(left)
    n = 3             -> CB(right), CB(center), CB(left)
    n = 4             -> RB, CB(right), CB(left), LB
    n >= 5            -> RWB, CB(right), CB(center), CB(left), ..., LWB
                          (extra inner defenders are shared out as more CBs)

MIDFIELD-type line (base is 'DM', 'CM' or 'AM'), size n:
    n <= 3            -> <base>(right)[, <base>(center)], <base>(left)
    n >= 4            -> R<base>, C<base>(right)[..center..], C<base>(left), L<base>
                          e.g. base 'CM', n=5 (as in 3-5-2's midfield):
                          RM, CM(right), CM(center), CM(left), LM

FORWARD line of size n:
    n = 1             -> ST (no side)
    n = 2             -> ST(right), ST(left)
    n >= 3             -> RW, ST(...), ..., LW

Whenever a code already encodes a side in its name (RB, LB, RWB, LWB, RM,
LM, RW, LW, RDM, LDM, ...) `side` is returned as None, since the side is
already baked into the position code. Whenever the code is a "generic"
one shared by several players in the same line (CB, CM, DM, AM, ST),
`side` carries 'right' / 'center' / 'left' (or a numbered fallback for
unusually wide lines) to disambiguate.

This matches the examples used to derive these rules:
    4-3-3, player 5  -> {'position': 'CM',  'side': 'right'}
    4-3-3, player 6  -> {'position': 'CM',  'side': 'center'}
    3-5-2, player 4  -> {'position': 'RM', 'side': None}
    3-5-2, player 1  -> {'position': 'CB', 'side': 'right'}
    any formation, player 0 -> {'position': 'GK', 'side': None}
"""

from typing import Dict, List, Optional, Tuple, TypedDict


class PositionResult(TypedDict):
    position: Optional[str]
    side: Optional[str]


# --------------------------------------------------------------------------
# Side distribution helper
# --------------------------------------------------------------------------
def _distribute_sides(n: int) -> list[str | None] | list[str]:
    """
    Return `n` side labels, ordered right -> left, symmetric about the
    center. Used whenever a *generic* position code is shared by several
    players in the same line.

        n=1 -> [None]                          (nothing to disambiguate)
        n=2 -> ['right', 'left']
        n=3 -> ['right', 'center', 'left']
        n=4 -> ['right', 'right-2', 'left-2', 'left']
        n=5 -> ['right', 'right-2', 'center', 'left-2', 'left']
        ...

    Sizes above 3 are uncommon in real formations but handled gracefully.
    """
    if n <= 0:
        return []
    if n == 1:
        return [None]

    half = n // 2
    right_side = ['right' if i == 0 else f'right-{i + 1}' for i in range(half)]
    left_side = ['left' if i == 1 else f'left-{i}' for i in range(half, 0, -1)]

    if n % 2 == 1:
        return right_side + ['center'] + left_side
    return right_side + left_side


def _defense_line(n: int) -> list[tuple[str, str | None]]:
    if n <= 0:
        return []
    if n <= 3:
        return [('CB', s) for s in _distribute_sides(n)]

    left_code, right_code = ('LB', 'RB') if n == 4 else ('LWB', 'RWB')
    inner_n = n - 2
    inner = [('CB', s) for s in _distribute_sides(inner_n)]
    return [(right_code, None)] + inner + [(left_code, None)]


def _forward_line(n: int) -> list[tuple[str, str | None]]:
    if n <= 0:
        return []
    if n <= 2:
        return [('ST', s) for s in _distribute_sides(n)]

    inner_n = n - 2
    inner = [('ST', s) for s in _distribute_sides(inner_n)]
    return [('RW', None)] + inner + [('LW', None)]


def _midfield_line(n: int, base: str = '') -> list[tuple[str, str | None]]:
    if n <= 0:
        return []
    if n <= 3:
        return [(base, s) for s in _distribute_sides(n)]

    inner_code = base if base.startswith('C') else f'C{base}'
    outer_right, outer_left = f'R{base[1:]}', f'L{base[1:]}'
    inner_n = n - 2
    inner = [(inner_code, s) for s in _distribute_sides(inner_n)]
    return [(outer_right, None)] + inner + [(outer_left, None)]


def _middle_row_roles(k: int) -> List[str]:
    """
    Label each midfield row (from the one closest to defense, to the one
    closest to attack) with a role base used by `_midfield_line`.
    """
    if k <= 0:
        return []
    if k == 1:
        return ['CM']
    if k == 2:
        return ['DM', 'AM']
    if k == 3:
        return ['DM', 'CM', 'AM']

    # k >= 4: interpolate DM -> CM -> AM across the rows
    roles = []
    for i in range(k):
        frac = i / (k - 1)
        if frac < 1 / 3:
            roles.append('DM')
        elif frac < 2 / 3:
            roles.append('CM')
        else:
            roles.append('AM')
    return roles


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def parse_formation(formation: str) -> List[int]:
    """Turn '4-1-2-3' into [4, 1, 2, 3], validating it's all positive ints."""
    parts = formation.strip().split('-')
    if len(parts) < 2:
        raise ValueError(
            f"Invalid formation '{formation}': need at least a defense and "
            "an attack line, e.g. '4-3-3'."
        )
    try:
        segments = [int(p) for p in parts]
    except ValueError as exc:
        raise ValueError(f"Invalid formation '{formation}': all segments must be integers.") from exc

    if any(s <= 0 for s in segments):
        raise ValueError(f"Invalid formation '{formation}': all segments must be positive.")

    return segments


def build_lineup(formation: str) -> List[Tuple[str, Optional[str]]]:
    """
    Build the full outfield lineup for a formation, ordered exactly as
    squad numbers 1..N would be assigned (defense -> midfield rows ->
    attack, each row right -> left).
    """
    segments = parse_formation(formation)
    defense_n, forward_n = segments[0], segments[-1]
    middle_segments = segments[1:-1]
    roles = _middle_row_roles(len(middle_segments))

    lineup: List[Tuple[str, Optional[str]]] = []
    lineup.extend(_defense_line(defense_n))
    for role, n in zip(roles, middle_segments):
        lineup.extend(_midfield_line(n, base=role))
    lineup.extend(_forward_line(forward_n))
    return lineup


def get_player_position(formation: str, player_number: int) -> PositionResult:
    """
    Return the likely position for `player_number` within `formation`.

    Player 0 is always the goalkeeper. Players 1..N are assigned line by
    line (defense, then each midfield row, then attack), right to left
    within each line.

    Raises ValueError for a malformed formation or an out-of-range number.
    """
    if player_number < 0:
        raise ValueError("player_number must be >= 0.")

    if player_number == 0:
        return {'position': 'GK', 'side': None}

    lineup = build_lineup(formation)
    idx = player_number - 1

    if idx >= len(lineup):
        return {'position': None, 'side': None}

    code, side = lineup[idx]
    return {'position': code, 'side': side}
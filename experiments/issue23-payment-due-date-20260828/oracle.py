from __future__ import annotations

import argparse
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

CASES = ('P1', 'B1', 'P2', 'P3', 'P4', 'N1', 'N2', 'N3', 'N4', 'R1', 'R2')
POSITIVES = ('P1', 'B1', 'P2', 'P3', 'P4', 'R1')
NEGATIVES = ('N1', 'N2', 'N3', 'N4')
STATE_FIELDS = ('inventoryQuantity', 'costQuantity', 'costAmount', 'salesRows', 'customerAmount')
MOVEMENT_FIELDS = ('salesRows', 'customerRows', 'inventoryRows', 'costRows')


def parse(path: Path) -> dict[str, tuple[str, Optional[str]]]:
    rows: dict[str, tuple[str, Optional[str]]] = {}
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        parts = raw.split('###')
        if len(parts) == 2 and parts[0] == 'complete':
            key, value, marker = parts[0], parts[1], None
        elif len(parts) == 3:
            key, value, marker = parts
        else:
            raise AssertionError(f'malformed receipt line: {raw!r}')
        if key in rows:
            raise AssertionError(f'duplicate label: {key}')
        rows[key] = (value, marker)
    return rows


def value(rows, key):
    if key not in rows:
        raise AssertionError(f'missing label: {key}')
    return rows[key][0]


def boolean(rows, key):
    item = rows[key]
    assert item[1] == 'Boolean', (key, item)
    assert item[0] in ('true', 'false'), (key, item)
    return item[0] == 'true'


def number(rows, key):
    item = rows[key]
    assert item[1] == 'Number', (key, item)
    return Decimal(item[0])


def date(rows, key):
    item = rows[key]
    assert item[1] == 'Date', (key, item)
    if item[0] == '':
        return datetime(1, 1, 1)
    match = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{1,4}) (\d{1,2}):(\d{2}):(\d{2}) (AM|PM)', item[0])
    if not match:
        raise AssertionError((key, item))
    month, day, year, hour, minute, second = map(int, match.groups()[:6])
    am_pm = match.group(7)
    hour = hour % 12 + (12 if am_pm == 'PM' else 0)
    return datetime(year, month, day, hour, minute, second)


def expected_behavior_labels() -> set[str]:
    labels = {'nonce', 'metadata.attributeExists', 'metadata.name', 'metadata.containsDate', 'metadata.dateOnly', 'run.R', 'complete'}
    for case in CASES:
        labels.update({
            f'{case}.begin', f'{case}.documentDate', f'{case}.dueDateInput',
            f'{case}.draftSucceeded', f'{case}.draftError', f'{case}.documentRef', f'{case}.draftDueDate',
            f'{case}.postCallSucceeded', f'{case}.postError', f'{case}.postDueDate', f'{case}.postedAfter', f'{case}.end',
        })
        labels.update(f'{case}.before.{field}' for field in STATE_FIELDS)
        labels.update(f'{case}.after.{field}' for field in STATE_FIELDS)
        labels.update(f'{case}.movements.{field}' for field in MOVEMENT_FIELDS)
    return labels


def validate_baseline(rows):
    assert set(rows) == {'nonce', 'metadata.attributeExists', 'complete'}, sorted(set(rows))
    assert boolean(rows, 'metadata.attributeExists') is False
    assert rows['complete'] == ('true', None)


def validate_behavior(rows):
    expected = expected_behavior_labels()
    assert set(rows) == expected, {'missing': sorted(expected-set(rows)), 'extra': sorted(set(rows)-expected)}
    assert rows['complete'] == ('true', None)
    assert boolean(rows, 'metadata.attributeExists') is True
    assert value(rows, 'metadata.name') == 'PaymentDueDate'
    assert boolean(rows, 'metadata.containsDate') is True
    assert boolean(rows, 'metadata.dateOnly') is True
    refs = []
    for case in CASES:
        assert boolean(rows, f'{case}.begin') is True
        assert boolean(rows, f'{case}.end') is True
        assert boolean(rows, f'{case}.draftSucceeded') is True
        assert value(rows, f'{case}.draftError') == ''
        ref = value(rows, f'{case}.documentRef')
        assert ref
        refs.append(ref)
        assert date(rows, f'{case}.draftDueDate') == date(rows, f'{case}.dueDateInput')
        assert date(rows, f'{case}.postDueDate') == date(rows, f'{case}.dueDateInput')
    assert len(set(refs)) == len(refs), refs
    for case in POSITIVES:
        assert boolean(rows, f'{case}.postedAfter') is True, f'{case} must post'
        assert [number(rows, f'{case}.movements.{field}') for field in MOVEMENT_FIELDS] == [Decimal(1)] * 4
        deltas = [number(rows, f'{case}.after.{field}') - number(rows, f'{case}.before.{field}') for field in STATE_FIELDS]
        assert deltas == [Decimal(-1), Decimal(-1), Decimal(-1), Decimal(1), Decimal(4)], (case, deltas)
    for case in NEGATIVES + ('R2',):
        assert boolean(rows, f'{case}.postedAfter') is False, f'{case} must remain unposted'
        assert [number(rows, f'{case}.movements.{field}') for field in MOVEMENT_FIELDS] == [Decimal(0)] * 4
        before = [number(rows, f'{case}.before.{field}') for field in STATE_FIELDS]
        after = [number(rows, f'{case}.after.{field}') for field in STATE_FIELDS]
        assert after == before, (case, before, after)
    for case in ('P1', 'P2', 'P3', 'P4'):
        assert date(rows, f'{case}.dueDateInput').date() > date(rows, f'{case}.documentDate').date()
    assert date(rows, 'B1.dueDateInput').date() == date(rows, 'B1.documentDate').date()
    for case in NEGATIVES:
        assert date(rows, f'{case}.dueDateInput').date() < date(rows, f'{case}.documentDate').date()
    assert date(rows, 'R1.dueDateInput').year == 1
    assert date(rows, 'R2.dueDateInput').year == 1
    assert date(rows, 'N4.documentDate').year == date(rows, 'N4.dueDateInput').year + 1
    assert date(rows, 'P4.dueDateInput').year == date(rows, 'P4.documentDate').year + 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('baseline', 'behavior'))
    parser.add_argument('receipt', type=Path)
    args = parser.parse_args()
    rows = parse(args.receipt)
    if args.mode == 'baseline':
        validate_baseline(rows)
    else:
        validate_behavior(rows)
    print(f'PASS {args.mode} labels={len(rows)}')


if __name__ == '__main__':
    main()

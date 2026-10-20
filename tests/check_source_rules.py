#!/usr/bin/env python3
"""ROM-free comparison with original pinned TTYD64 source, not port constants."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--logic', type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    reference = Path(__file__).resolve().parent / 'reference'
    provenance = json.loads((reference / 'provenance.json').read_text())
    xml = reference / 'ttyd64-b8d2058-Moves.xml'
    hp = reference / 'ttyd64-b8d2058-partner-hp.txt'
    assert sha(xml) == provenance['moves_XML_content_sha256'], 'Pinned source XML changed'
    assert sha(hp) == provenance['hp_excerpt_sha256'], 'Pinned source HP excerpt changed'
    constants = dict(re.findall(r'^#define\s+(TTYD64_\w+)\s+(\d+)\s*$',
                               (source / 'include/ttyd64_rules.h').read_text(), re.M))

    def number(token):
        return int(constants[token]) if token in constants else int(token, 0)

    # Parse the actual checked-in native base table, as the full game build does.
    blocks = re.split(r'\{\s*//\s*0x([0-9A-Fa-f]+):[^\n]*',
                      (source / 'src/move_data.inc.c').read_text())
    native = {}
    for i in range(1, len(blocks), 2):
        fp = re.search(r'\.costFP\s*=\s*(\w+)', blocks[i + 1])
        bp = re.search(r'\.costBP\s*=\s*(\w+)', blocks[i + 1])
        assert fp and bp, 'Unrecognized native cost entry ' + blocks[i]
        index = int(blocks[i], 16)
        assert index not in native, 'Duplicate native move entry'
        native[index] = [number(fp[1]), number(bp[1])]
    expected_count = int(re.search(r'#define\s+NUM_MOVES\s+(\d+)',
                                 (source / 'include/move_enum.h').read_text())[1])
    assert len(native) == expected_count, 'Native table/enum extent changed'
    vanilla = json.loads((reference / 'paperboat-7f038b8-costs.json').read_text())
    for index, expected in vanilla.items():
        assert native[int(index)] == expected, f'Vanilla base cost changed: {index}'

    # These IDs have different meanings; comparing their numeric slots is invalid.
    excluded = {0x0f: 'Poison Drive replaces Smash Charge', 0x11: 'Ice Smash replaces Super Smash Charge',
                0x30: 'Tornado Jump replaces Super Jump Charge',
                0xb9: 'relocated/appended identity', 0xba: 'relocated/appended identity',
                0xbb: 'relocated/appended identity', 0xbc: 'relocated/appended identity'}
    expected = {}
    for move in ET.fromstring(xml.read_text()):
        index = int(move.attrib['index'], 16)
        if index not in excluded and index in native:
            expected[index] = [int(move.attrib['fp'], 16), int(move.attrib['bp'], 16)]
    request = {'costs': [{'index': index, 'fp': values[0], 'bp': values[1]}
                         for index, values in native.items()]}
    result = subprocess.run([str(args.logic.resolve()), '--source-rules'], input=json.dumps(request),
                            text=True, capture_output=True, check=True)
    actual = json.loads(result.stdout)
    assert len(actual['costs']) == len(native), 'Compiled cost response incomplete'
    failures = []
    compared = set()
    for row in actual['costs']:
        index = row['index']
        assert row['vanilla'] == native[index], f'Vanilla lookup changed: {index}'
        if index in expected:
            compared.add(index)
            if row['ttyd64'] != expected[index]:
                failures.append({'index': hex(index), 'actual': row['ttyd64'], 'source': expected[index]})
    assert compared == set(expected), 'Compiled source comparison incomplete'
    assert not failures, 'TTYD64 FP/BP source differences: ' + json.dumps(failures)
    rows = []
    for line in hp.read_text().splitlines():
        values = [int(value) for value in re.findall(r'(\d+)`b', line.split('%')[0])]
        if values:
            assert len(values) == 3, 'Unrecognized source HP row'
            rows.append(values if any(values) else [-1, -1, -1])
    assert len(rows) == 11, 'Source partner table changed'
    assert actual['health'] == rows, 'Compiled partner HP differs from source table'
    print(f'Source {provenance["ttyd64_commit"]}: {len(expected)} semantic FP/BP rows and33 HP cells match; '
          f'{len(vanilla)} Vanilla base rows preserved. Excluded IDs: '
          + ','.join(hex(index) for index in excluded))
    print('Method: original source XML/excerpt parser + compiled pure gameplay functions; no ROM or engine.')


if __name__ == '__main__':
    main()

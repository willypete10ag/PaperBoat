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


def check_item_source(source, reference, provenance):
    """Compare original item powers/text and source script consumers independently."""
    originals = {}
    for name in ('Items.xml', 'item-scripts.patch', 'item-messages.patch'):
        path = reference / ('ttyd64-b8d2058-' + name)
        assert sha(path) == provenance[name + '_sha256'], 'Pinned item source changed: ' + name
        originals[name] = path.read_text()
    # These are semantic identity translations, not copied expected powers/text.
    identities = {'CourageShell':'COURAGE_SHELL', 'PowerPunch':'POWER_PUNCH',
                  'MiniMrMini':'MINI_MR_MINI', 'MrSoftener':'MR_SOFTENER'}
    items = {row.attrib['name']:row.attrib for row in ET.fromstring(originals['Items.xml'])}
    native_items = dict(re.findall(r'\{\s*//\s*0x[0-9A-Fa-f]+:\s*(\w+) \(TTYD64\)(.*?)\n    \},',
                                   (source / 'src/item_data.inc.c').read_text(), re.S))
    script = originals['item-scripts.patch']
    native_script = (source / 'src/battle/move/item/ttyd64_status.c').read_text()
    popup = (source / 'src/battle/popup_messages.c').read_text()
    text = json.loads((source / 'port/ttyd64/messages.json').read_text())
    header = (source / 'include/ttyd64_assets.h').read_text()
    paths = re.search(r'gMsgPaths_sec2F\[\] = \{(.*?)\};',
                      (source / 'include/assets/messages.h').read_text(), re.S)[1]
    paths = re.findall(r'"__OTR__messages/ttyd64/(\w+)"', paths)
    source_table = re.search(r'\$StringTable_BattlePopUp_NewStrings\s*\{(.*?)\}',
                             originals['item-messages.patch'], re.S)[1]
    table = re.findall(r'^\s*\$(\w+)\s*%', source_table, re.M)
    for name, native_id in identities.items():
        row = items[name]
        for key, field in [('powA','potencyA'), ('powB','potencyB'), ('sellValue','sellValue')]:
            expected = int(row.get(key, '0'), 16)
            actual = int(re.search(r'\.' + field + r'\s*=\s*(\d+)', native_items[name])[1])
            assert actual == expected, f'{name}.{field}: {actual} != source {expected}'
        # Last case of each source item is its result-message switch branch.
        branches = re.findall(r'Case == \.Item:' + name + r'\b(.*?)(?=\n\s*Case(?:OR)? == \.Item:|\n\})',
                              script, re.S)
        calls = [m for branch in branches for m in re.findall(
            r'Call\s+ShowMessageBox\s*\(\s*([0-9A-F]+)\s+([0-9A-F]+)\s*\)', branch)]
        assert len(calls) == 1, 'Ambiguous active source message: ' + name
        index, duration = (int(x,16) for x in calls[0])
        source_string = table[index - 0x100]
        expected_text = re.search(r'#string \$' + source_string + r'[^\n]*\n\{\n(.*?)\[End\]',
                                  originals['item-messages.patch'], re.S)[1]
        native_key = re.search(r'case ITEM_' + native_id +
                              r':\s*script->varTable\[6\] = (\w+);', native_script)[1]
        native_text_key = re.search(r'\[' + native_key + r'\]\s+MSG_TTYD64_(\w+)', popup)[1]
        assert text[native_text_key] == expected_text, 'Source result text differs: ' + name
        section, offset = re.search(r'MSG_TTYD64_' + native_text_key +
                                    r' MESSAGE_ID\((0x\w+), (\d+)\)', header).groups()
        assert int(section,16) == 0x2f and paths[int(offset)] == native_text_key
        assert f'Call(ShowMessageBox, LVar6, {duration})' in native_script
        assert popup.count('case ' + native_key + ':') == 4, 'Missing popup lifecycle consumer'
    assert native_script.index('Call(N(GetResultMessage))') > native_script.index('Call(ChooseNextTarget')
    assert 'Call(WaitForMessageBoxDone)' in native_script
    print('Independent item source:4 identities /12 power-price cells,4 source-script result texts, '
          'native message resource mapping and popup lifecycle consumers match. '
          'Static consumer checks do not establish all native callsite or item mechanics parity.')


def check_star_source(source, reference, provenance):
    originals = {}
    for name in ('Smooch.bpat', 'team-targets.patch'):
        path = reference / ('ttyd64-b8d2058-' + name)
        assert sha(path) == provenance[name + '_sha256'], 'Pinned star source changed'
        originals[name] = path.read_text()
    active = originals['Smooch.bpat']
    amount = int(re.search(r'Call\s+\$Heal_PlayerTeam\s*\(\s*\.Actor:Partner\s+(\d+)`', active)[1])
    native = (source / 'src/battle/move/star_power/smooch.c').read_text()
    actual = int(re.search(r'ttyd64_partner_combat_heal\(gBattleStatus.partnerActor, (\d+)\)', native)[1])
    assert actual == amount, 'Smooch partner power differs from active source'
    assert 'ttyd64_partner_combat_alive()' in native and 'ttyd64_partner_status_cure_debuff' not in native
    targets = originals['team-targets.patch']
    text = re.search(r'#string \$String_MarioAndPartner\s*\{\s*(.*?)\[End\]', targets, re.S)[1]
    draw = (source / 'src/battle/states/select_target.c').read_text()
    assert f'dx_string_to_msg(teamName, "{text}")' in draw, 'Team label differs from source'
    source_ids = {int(v,16) for v in re.findall(r'ORI\s+A[13], R0, (007[8C])', targets)}
    enums = (source / 'include/move_enum.h').read_text()
    native_ids = {int(re.search(r'\b'+name+r'\s*=\s*(0x[0-9A-Fa-f]+)', enums)[1],16) for name in ('MOVE_REFRESH','MOVE_SMOOCH')}
    assert native_ids == source_ids, 'Team move identity mapping differs'
    print('Independent active star source: Smooch partner power/living admission/no cure, two team move identities and exact label; static consumers, not gameplay.')


def check_food_source(source, reference, provenance):
    originals = {}
    for name in ('Items.xml', 'food.bpat', 'food-team.patch'):
        path = reference / ('ttyd64-b8d2058-' + name)
        assert sha(path) == provenance[name + '_sha256'], 'Pinned food source changed'
        originals[name] = path.read_text()
    # Source powers/sell prices are DECIMAL; indices and flag masks are HEX.
    # Exclude special-script items explicitly from this conventional-food slice.
    special = {'VoltShroom','HustleDrink','LifeShroom','SuperSoda',
               'ElectroPop','StrangeCake','KookyCookie','Coconut'}
    blocks = re.split(r'\{\s*//\s*0x([0-9A-Fa-f]+):[^\n]*',
                      (source / 'src/item_data.inc.c').read_text())
    native = {int(blocks[i],16):blocks[i+1] for i in range(1,len(blocks),2)}
    compared = []
    for row in ET.fromstring(originals['Items.xml']):
        a = row.attrib
        flags = int(a['typeFlags'],16)
        hp, fp = int(a.get('powA','0')), int(a.get('powB','0'))
        if flags & 0x87 != 0x87 or hp < 0 or fp < 0 or hp + fp == 0 or a['name'] in special:
            continue
        index = int(a['index'],16)
        # Only original native food slots in this batch; new source-only foods
        # need identity/assets/scripts in a later port.
        if not 0x8a <= index <= 0xdf:
            continue
        assert index in native, 'Missing source food identity: ' + a['name']
        for field,expected in [('potencyA',hp),('potencyB',fp),('sellValue',int(a['sellValue']))]:
            actual = int(re.search(r'\.'+field+r'\s*=\s*(-?\d+)',native[index])[1])
            assert actual == expected, a['name']+'.'+field+' differs from original food source'
        assert 'TARGET_FLAG_PLAYER' in native[index] and 'ITEM_TYPE_FLAG_FOOD_OR_DRINK' in native[index]
        compared.append(index)
    assert len(compared) > 40, 'Food source coverage unexpectedly narrowed'
    active = re.sub(r'/%.*?%/', '', originals['food.bpat'], flags=re.S)
    active = active[active.index('#new:Script $Script_UseItem_Food'):]
    assert re.search(r'Call\s+\$Heal_PlayerTeam\s*\(\s*\*Var7\s+\*VarB', active)
    assert re.search(r'Call\s+\$RecoverFP\s*\(\s*\*VarC', active)
    assert 'LB        A0, 5 (V1) % fp' in originals['food-team.patch']
    script = (source / 'src/battle/move/item/food.c').read_text()
    body = script[script.index('API_CALLABLE(N(RecoverPartnerFood))'):script.index('API_CALLABLE(N(HasPartnerHP))')]
    assert 'ttyd64_partner_combat_can_heal_with_item(gBattleStatus.moveArgument)' in body
    assert 'ttyd64_partner_combat_heal(partner, item->potencyA)' in body
    assert 'gPlayerData.curFP + item->potencyB' in body and 'MIN(fp, gPlayerData.curMaxFP)' in body
    partner_script = script[script.index('EvtScript N(EVS_UseOnPartner)'):script.index('EvtScript N(EVS_UseItem)')]
    assert 'Call(N(RecoverPartnerFood))' in partner_script and 'Call(N(HasPartnerHP))' in partner_script
    for path in ('src/world_use_item.c','src/ttyd64_partner_hp.c'):
        assert 'return ttyd64_item_is_recovery_food(itemID);' in (source / path).read_text()
    print(f'Independent conventional food source: {len(compared)} identities /{3*len(compared)} HP-FP-price cells; active selected-HP/shared-FP source and native consumer wiring. Static checks, not gameplay or special/partner-owned food parity.')



def check_world_special_source(source, reference, provenance):
    path = reference / 'ttyd64-b8d2058-world-food.patch'
    assert sha(path) == provenance['world-food.patch_sha256']
    active = re.sub(r'/%.*?%/', '', path.read_text(), flags=re.S)
    assert '@Hook 8BFDC' in active and 'SAB     V0, $HealMenu_State' in active
    assert re.search(r'If\s+\*VarC\s+!=\s+\.False', active)
    assert re.search(r'Call\s+802C0288\s*\(\s*\*VarC', active)
    original = ET.parse(reference / 'ttyd64-b8d2058-Items.xml').getroot()
    selected = [r.attrib for r in original if r.attrib['name'] in ('ElectroPop','SuperSoda','KookyCookie')]
    assert len(selected) == 3
    for row in selected:
        assert int(row['typeFlags'],16) & 0x87 == 0x87
        assert int(row.get('powA','0')) == 0 and int(row['powB']) > 0
    world = (source / 'src/world_use_item.c').read_text()
    admission = world[world.index('b32 ttyd64_world_item_can_target_partner'):world.index('API_CALLABLE(WorldItem_GetHPRecipientPos)')]
    cases = set(re.findall(r'case (ITEM_\w+):', admission))
    assert cases == {'ITEM_ELECTRO_POP','ITEM_SUPER_SODA','ITEM_KOOKY_COOKIE'}
    assert '!ttyd64_mode_enabled()' in admission and 'CONTEXT_WORLD' in admission
    assert 'IfNe(LVarB, 0)' in world and 'IfNe(LVarC, 0)' in world
    print('Independent world-special source:3 world-usable zero-HP FP foods; active recipient hook and guarded native admission. Static checks, not keyboard gameplay or battle-status parity.')


def check_electric_source(source, reference, provenance):
    items = {row.attrib['name']:row.attrib for row in ET.fromstring(
        (reference / 'ttyd64-b8d2058-Items.xml').read_text())}
    blocks = re.split(r'\{\s*//\s*0x([0-9A-Fa-f]+):[^\n]*',
                      (source / 'src/item_data.inc.c').read_text())
    native = {int(blocks[i],16):blocks[i+1] for i in range(1,len(blocks),2)}
    for name, filename in [('VoltShroom','volt_shroom.c'),('ElectroPop','electro_pop.c')]:
        key = 'electric-'+name+'.patch'
        path = reference / ('ttyd64-b8d2058-'+key)
        assert sha(path) == provenance[key+'_sha256'], 'Pinned electric source changed'
        active = path.read_text()
        assert re.search(r'Call\s+GetOwnerTarget\s*\(\s*\*Var4', active)
        assert re.search(r'Call\s+\$Function_InflictStatus\s*\(\s*\*Var4\s+\.Status:Static\s+\*Var0', active)
        assert re.search(r'Call\s+GetItemPower\s*\(\s*\.Item:VoltShroom\s+\*Var0', active)
        row = items[name]
        for field, key in [('potencyA','powA'),('potencyB','powB')]:
            actual = int(re.search(r'\.'+field+r'\s*=\s*(-?\d+)',native[int(row['index'],16)])[1])
            assert actual == int(row.get(key,'0')), name+'.'+field+' differs from original source'
        script = (source / 'src/battle/move/item' / filename).read_text()
        assert 'Call(N(GetElectricTarget))' in script and 'Call(N(InflictElectric))' in script
        assert 'Call(GetItemPower, ITEM_VOLT_SHROOM, LVar0, LVar1)' in script
        assert 'Call(GetActorPos, ACTOR_PLAYER,' not in script
        if name == 'ElectroPop':
            assert 'LB        V0, 1C (A2)' in active and 'Call  $Function_HealFP' in active
            assert 'IfEq(LVar9, ACTOR_PLAYER)' in script
            assert script.count('Call(N(AddFP), LVar3)') == 1
    targets = (reference / 'ttyd64-b8d2058-team-targets.patch').read_text()
    assert 'ORI     T1, T1, 0001' in targets
    native_targets = (source / 'src/battle/190B20.c').read_text()
    assert 'if (healingPartner && battleStatus->moveArgument == ITEM_VOLT_SHROOM)' in native_targets
    assert 'battleStatus->curTargetListFlags |= TARGET_FLAG_SELECT_ONE;' in native_targets
    helper = (source / 'src/battle/common/move/ElectricItem.inc.c').read_text()
    assert 'owner->targetActorID == ACTOR_PARTNER' in helper
    assert 'ttyd64_partner_status_can_target_item(gBattleStatus.moveArgument)' in helper
    assert 'inflict_status(target, STATUS_KEY_STATIC, script->varTable[0])' in helper
    print('Independent electric source:2 identities /4 power cells, active selected-actor Static and shared-FP consumers; static wiring, not gameplay/world/partner-owned parity.')


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
    check_item_source(source, reference, provenance)
    check_star_source(source, reference, provenance)
    check_food_source(source, reference, provenance)
    check_electric_source(source, reference, provenance)
    check_world_special_source(source, reference, provenance)
    print(f'Source {provenance["ttyd64_commit"]}: {len(expected)} semantic FP/BP rows and33 HP cells match; '
          f'{len(vanilla)} Vanilla base rows preserved. Excluded IDs: '
          + ','.join(hex(index) for index in excluded))
    print('Method: original source XML/excerpt parser + compiled pure gameplay functions; no ROM or engine.')


if __name__ == '__main__':
    main()

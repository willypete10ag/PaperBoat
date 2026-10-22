"""Controlled native API HP ownership checks; no keyboard/combat claim.

Baseline observes getter mutation and save-buffer aliasing, not preview corruption.
Fixed checks separate runtime ownership, pure reads, snapshot/load boundaries,
rank normalization, explicit zero, invalid IDs, failed load and preview isolation.
"""
import json, os, sys
from pathlib import Path
import gdb
sys.path.insert(0, os.environ['PORTING_FIXTURE_DIR'])
from fixture_support import *
validate_runtime()
def cmd(s): return gdb.execute(s, to_string=True)
def val(s): return int(gdb.parse_and_eval(s))
def put(s,n): cmd(f'set variable {s} = {n}')
def hp(i): return val(f'ttyd64_get_partner_hp({i})')
def maximum(i): return val(f'ttyd64_get_partner_max_hp({i})')
def checks():
    for s in ('pagination off','confirm off','print thread-events off'):cmd('set '+s)
    gdb.Breakpoint('state_step_startup',temporary=True,internal=True);cmd('run')
    put('gPortResetToTitleScreen',1)
    gdb.Breakpoint('state_step_title_screen',temporary=True,internal=True);cmd('continue')
    cmd('call clear_player_data()')
    baseline=os.environ.get('HP_OWNERSHIP_BASELINE')=='1'
    passed=[]
    def check(name,ok):
        assert ok,name
        passed.append(name);record_check(name);print('HP_OWNERSHIP_CHECK='+name,flush=True)
    scratch='gCurrentSaveFile.shipSaveData.partnerHP'
    for mode in (0,1):
        cmd(f'call ttyd64_mode_select_file({mode})')
        cmd('call ttyd64_set_partner_hp(1, 3)')
        put('gPlayerData.partners[2].level',1)
        snapshot=bytes(gdb.selected_inferior().read_memory(val(f'&{scratch}'),val(f'sizeof({scratch})')))
        check(f'mode{mode}-rank-read-value',maximum(2)==15)
        after=bytes(gdb.selected_inferior().read_memory(val(f'&{scratch}'),len(snapshot)))
        check(f'mode{mode}-getter-'+('mutates-save-buffer' if baseline else 'preserves-save-buffer'),(after!=snapshot) if baseline else (after==snapshot))
        put(f'{scratch}[1].curHP',8)
        check(f'mode{mode}-scratch-'+('aliases-live-hp' if baseline else 'isolated-from-live-hp'),hp(1)==(8 if baseline else 3))
        put('gPlayerData.partners[2].level',0)
    if not baseline:
        runtime='RuntimePartnerHP'
        put(f'{runtime}[2].curHP',-7)
        before=bytes(gdb.selected_inferior().read_memory(val(f'&{runtime}'),val(f'sizeof({runtime})')))
        check('negative-read-clamped',hp(2)==0)
        check('all-getters-pure',all(hp(i)>=-1 and maximum(i)>=-1 for i in range(-1,14)) and before==bytes(gdb.selected_inferior().read_memory(val(f'&{runtime}'),len(before))))
        cmd('call ttyd64_set_partner_hp(2, 0)')
        put('gPlayerData.partners[2].level',2)
        check('rank-read-preserves-dead',hp(2)==0 and maximum(2)==25)
        cmd('call fio_serialize_state()')
        check('serialize-snapshots-live-hp',val(f'{scratch}[1].curHP')==3 and val(f'{scratch}[2].curHP')==0 and val(f'{scratch}[2].maxHP')==25)
        check('serialize-does-not-normalize-runtime',val(f'{runtime}[2].maxHP')==10)
        cmd('call fio_save_game(3)')
        saved=fixture_save().read_bytes();data=json.loads(saved)
        check('json-writer-wounded-dead-and-rank',data['ship']['ttyd64PartnerHP']['partners'][1]['curHP']==3 and data['ship']['ttyd64PartnerHP']['partners'][2]=={'curHP':0,'maxHP':25})
        cmd('call ttyd64_set_partner_hp(1, 1)')
        check('preview-valid-no-live-change',val('fio_load_summary(3)')==1 and hp(1)==1 and val('ttyd64_mode_enabled()')==1)
        check('load-commits-runtime',val('fio_load_game(3)')==1 and hp(1)==3 and hp(2)==0 and maximum(2)==25)
        fixture_save().unlink()
        try:check('failed-load-preserves-live',val('fio_load_game(3)')==0 and hp(1)==3 and hp(2)==0)
        finally:fixture_save().write_bytes(saved)
        put('gPlayerData.partners[1].level',2);cmd('call ttyd64_reset_partner_hp(1)')
        check('explicit-rank-reset-full',hp(1)==30 and maximum(1)==30)
        check('invalid-ids-rejected',all(hp(i)==-1 and val(f'ttyd64_set_partner_hp({i}, 9)')==-1 for i in (-2147483648,-1,0,5,10,11,12,2147483647)))
        cmd('call clear_player_data()')
        check('new-game-runtime-reset-and-vanilla',hp(1)==10 and maximum(1)==10 and val('ttyd64_mode_enabled()')==0)
    Path(os.environ['PARTNER_HP_RESULT']).write_text(json.dumps({'checks_passed':len(passed),'checks':passed,'baseline':baseline,'method':__doc__},indent=2)+'\n')
    cmd('kill')
try:checks()
except Exception:
    import traceback
    traceback.print_exc();cmd('quit 1')

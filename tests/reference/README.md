# Independent source-rule oracle

TTYD64 b8d2058ea057b2dfc168f2d909a2a2ea0927ce17: Moves.xml is the original
public source configuration; the HP text is the exact active PartnersHPTable
excerpt from globals/patch/PartnersHP.patch. Attribution: eldexterr/ttyd64.
provenance.json records original content hashes and commits. No ROM, generated
archive, game asset or save is included. These are source rules, not ROM dumps.

The Vanilla cost snapshot is parsed from PaperBoat develop7f038b855's checked-in
src/move_data.inc.c, covering185 original move IDs. Source-rule CTest parses the
original XML/excerpt independently of port constants, verifies native base costs
against this Vanilla snapshot, and asks the compiled pure gameplay functions for
both modes' effective costs and all33 partner/rank HP cells. Seven reused or
relocated source move IDs are excluded explicitly; matching costs do not prove
move mechanics, stacking, availability, enemy AI, world distribution or campaign
parity. Regenerating a reference requires reviewing a new pinned source commit.

Original Items.xml, Battle_NewItems_BattleScripts.patch and
Battle_MessageBox_NewIndexes.patch from the same pinned commit are now included.
The item oracle parses four modifier-item identities' source powers/prices,
active script result-message IDs and original strings independently. It compares
12 native table cells and4 result texts/resource mappings/lifecycle consumers.
This is a narrow static consumer oracle plus separate native keyboard acceptance;
it does not close all item mechanics/native-callsite gaps (R2-L2).

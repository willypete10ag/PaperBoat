#!/usr/bin/env python3
"""Build/extract and run ROM-dependent native fixtures in owned Linux sandboxes."""

import argparse, datetime, hashlib, json, os, shutil, signal, subprocess, sys, time, uuid
from pathlib import Path


def required(name):
    if not os.environ.get(name):
        raise SystemExit(f"Missing {name}; see tools/porting/README.md")
    return Path(os.environ[name]).expanduser().resolve()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def run(command, **kwargs):
    return subprocess.run([str(x) for x in command], check=True, **kwargs)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", help="Comma-separated fixture IDs; omitted fixtures are explicitly recorded as skipped")
    ap.add_argument(
        "--reuse-archive",
        action="store_true",
        help="Explicitly skip extraction and record the supplied existing archive hash",
    )
    ap.add_argument("--skip-build", action="store_true", help="Require a matching build receipt rather than rebuilding")
    args = ap.parse_args()
    source = required("PAPERBOAT_SOURCE_DIR")
    build = required("PAPERBOAT_BUILD_DIR")
    binary = required("PAPERBOAT_EXECUTABLE")
    rom = required("PAPERBOAT_ROM")
    archive = required("PAPERBOAT_ROM_ARCHIVE")
    port = required("PAPERBOAT_PORT_ARCHIVE")
    reference = required("TTYD64_REFERENCE_DIR")
    work = required("PORTING_WORK_DIR")
    results = required("PORTING_RESULTS_DIR")
    fixture_dir = Path(__file__).resolve().parent
    fixture_commit = os.environ.get("PORTING_FIXTURE_COMMIT") or git(source, "rev-parse", "HEAD")

    def verify_fixture(path):
        committed = subprocess.check_output(
            ["git", "-C", str(source), "show", fixture_commit + ":tools/porting/" + str(path.relative_to(fixture_dir))]
        )
        if hashlib.sha256(committed).hexdigest() != sha(path):
            ap.error(f"Uncommitted/changed fixture: {path}")

    for name in (
        "run_acceptance.py",
        "run_acceptance.sh",
        "fixture_support.py",
        "fixtures/keyboard.json",
        "build_badge_assets.py",
    ):
        verify_fixture(fixture_dir / name)
    for tool in ("gdb", "Xvfb", "xdotool", "xdpyinfo", "import", "convert", "cmake"):
        if not shutil.which(tool):
            ap.error(f"Required Linux tool missing: {tool}")
    for p in (rom, reference / "globals/patch/PartnersHP.patch", source / "CMakeLists.txt"):
        if not p.is_file():
            ap.error(f"Required input missing: {p}")
    if git(source, "status", "--porcelain", "--untracked-files=normal"):
        ap.error("Game checkout has tracked or untracked files: commit first; evidence must identify exact source")
    commit = git(source, "rev-parse", "HEAD")
    if work.exists():
        ap.error("PORTING_WORK_DIR must be a new directory; refusing existing saves/results")
    work.mkdir(parents=True)
    if results.exists():
        ap.error("PORTING_RESULTS_DIR must be new; evidence is never overwritten")
    results.mkdir(parents=True)
    launch = work / "launch"
    launch.mkdir()
    receipt = build / "porting-build.json"
    if not args.skip_build:
        with (results / "build.log").open("w") as log:
            run(
                ["cmake", "-S", source, "-B", build, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Debug"],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            run(
                ["cmake", "--build", build, "--parallel", os.environ.get("PORTING_BUILD_JOBS", "4")],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        receipt.write_text(
            json.dumps({"game_commit": commit, "executable_sha256": sha(binary), "built_at": now()}, indent=2) + "\n"
        )
    if not receipt.is_file():
        ap.error("No build receipt; omit --skip-build to build this commit")
    build_info = json.loads(receipt.read_text())
    if build_info["game_commit"] != commit or build_info["executable_sha256"] != sha(binary):
        ap.error("Build receipt does not match source commit/executable")
    if not args.reuse_archive:
        archive.parent.mkdir(parents=True, exist_ok=True)
        if archive.exists():
            ap.error("Archive exists: use a fresh path or explicitly --reuse-archive")
        extraction = work / "extraction"
        extraction.mkdir()
        with (results / "extraction.log").open("w") as log:
            run([binary, "--extract-rom", rom, source, extraction], stdout=log, stderr=subprocess.STDOUT)
        shutil.move(extraction / "pm64.o2r", archive)
    for p in (archive, port):
        if not p.is_file():
            ap.error(f"Required archive missing: {p}")
    for original, name in [
        (archive, "pm64.o2r"),
        (port, "paperboat.o2r"),
        (source / "assets", "assets"),
        (source / "config.yml", "config.yml"),
    ]:
        (launch / name).symlink_to(original, target_is_directory=original.is_dir())
    # Linux resolves resource paths from /proc/self/exe, not cwd. A real copy
    # (not a symlink) must sit beside the supplied archives.
    staged_binary = launch / binary.name
    shutil.copy2(binary, staged_binary)
    if sha(staged_binary) != sha(binary):
        ap.error("Staged executable differs from the built executable")
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(
            (
                "GOOMBARIO_",
                "PARTNER_",
                "FP_DRAIN_",
                "PITY_FLOWER_",
                "DEFEND_PLUS_",
                "DUPLICATE_BADGES_",
                "FLOWER_SAVER_",
                "WORLD_",
                "BATTLE_RETURN_",
                "LAST_STAND_",
                "JUMPMAN_",
                "HAMMERMAN_",
                "BADGE_ASSETS_",
            )
        ):
            env.pop(key)
    env.update(
        PORTING_FIXTURE_DIR=str(fixture_dir),
        PAPERBOAT_SOURCE_DIR=str(source),
        PORTING_WORK_DIR=str(work),
        SDL_AUDIODRIVER="dummy",
        SDL_VIDEODRIVER="x11",
        LIBGL_ALWAYS_SOFTWARE="1",
        DEBUGINFOD_URLS="",
        XDG_CACHE_HOME=str(work / "cache"),
    )
    profile = fixture_dir / "fixtures/keyboard.json"
    base = {
        "schema_version": 1,
        "game_commit": commit,
        "game_source_clean": True,
        "executable_sha256": sha(binary),
        "rom_sha256": sha(rom),
        "rom_archive_sha256": sha(archive),
        "port_archive_sha256": sha(port),
        "reference_commit": git(reference, "rev-parse", "HEAD"),
        "runner_sha256": sha(Path(__file__)),
        "fixture_commit": fixture_commit,
        "build_skipped": args.skip_build,
        "helper_sha256": sha(fixture_dir / "fixture_support.py"),
        "input_profile_sha256": sha(fixture_dir / "fixtures/keyboard.json"),
        "shell_wrapper_sha256": sha(fixture_dir / "run_acceptance.sh"),
        "build": build_info,
        "extraction_skipped": args.reuse_archive,
    }

    def runtime(group, suffix="runtime"):
        home = work / group / suffix
        (home / "saves").mkdir(parents=True, exist_ok=False)
        (home / ".porting-disposable").write_text("PaperBoat acceptance runtime v1\n")
        shutil.copyfile(profile, home / "paperboat.cfg.json")
        return home

    attempted = []

    def execute(name, script, home, extra=None, seed=None):
        attempted.append(name)
        outfile = results / (name + ".payload.json")
        methods = results / (name + ".methods.json")
        local = env.copy()
        local.update(SHIP_HOME=str(home), PORTING_SAVE_DIR=str(home / "saves"), PORTING_CHECK_METHODS=str(methods))
        seed_hash = sha(seed) if seed else None
        if seed:
            shutil.copyfile(seed, home / "saves/file3.json")
        for key in (
            "LAST_STAND",
            "DUPLICATE_BADGES",
            "PITY_FLOWER",
            "WORLD_BADGES",
            "DEFEND_PLUS",
            "JUMPMAN",
            "HAMMERMAN",
            "FP_DRAIN",
            "FLOWER_SAVER",
            "PARTNER_HP",
            "GOOMBARIO",
            "PARTNER_HEALING",
            "WORLD_HEAL",
            "WORLD_HUD",
            "WORLD_SWAP",
            "BATTLE_RETURN",
            "PARTNER_SLICE",
            "BADGE_ASSETS",
        ):
            local[key + "_RESULT"] = str(outfile)
            local[key + "_PID"] = str(results / (name + ".pid"))
        local["LAST_STAND_SOURCE"] = str(source / "src/battle/1A5830.c")
        if extra:
            local.update(extra)
        verify_fixture(fixture_dir / script)
        script_hash = sha(fixture_dir / script)
        start = now()
        logpath = results / (name + ".log")
        proc = None
        error = None
        interrupted = False
        try:
            with logpath.open("w") as log:
                proc = subprocess.Popen(
                    (
                        [sys.executable, str(fixture_dir / script), str(source / "port/ttyd64")]
                        if script == "check_badge_assets.py"
                        else ["gdb", "-q", "-batch", "-x", str(fixture_dir / script), str(staged_binary)]
                    ),
                    cwd=launch,
                    env=local,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                code = proc.wait(timeout=int(os.environ.get("PORTING_FIXTURE_TIMEOUT", "1800")))
        except (Exception, KeyboardInterrupt) as exc:
            code = -1
            error = repr(exc)
            interrupted = isinstance(exc, KeyboardInterrupt)
        finally:
            if proc:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        logtext = logpath.read_text(errors="replace")
        ok = (
            code == 0
            and "Traceback (most recent call last)" not in logtext
            and "Error in sourced command file" not in logtext
        )
        loaded = []
        if script != "check_badge_assets.py":
            import re

            loaded = re.findall(r"Reading archive: (.+)", logtext)
            expected = {(launch / "pm64.o2r").resolve(), (launch / "paperboat.o2r").resolve()}
            actual = {Path(path.strip()).resolve() for path in loaded}
            if archive.resolve() not in actual or not actual.issubset(expected):
                ok = False
                error = error or f"Archive provenance mismatch: loaded={loaded}"
        if script == "seed_new_game_gdb.py" and (
            "PORTING_SEED_CREATED_FROM_NEW_GAME" not in logtext or not (home / "saves/file3.json").is_file()
        ):
            ok = False
            error = error or "Seed did not complete its native new-game save"
        payload = None
        try:
            if outfile.is_file():
                payload = json.loads(outfile.read_text())
        except (ValueError, OSError) as exc:
            ok = False
            error = f"Invalid payload: {exc}"
        if script != "seed_new_game_gdb.py" and payload is None:
            ok = False
            error = error or "Fixture did not produce its required payload"
        if sha(fixture_dir / script) != script_hash:
            ok = False
            error = "Fixture changed during execution"
        try:
            records = (
                [
                    {
                        "check": entry["asset"],
                        "driver": "independent_asset_decoder",
                        "fixture_uses_debugger_setup": False,
                    }
                    for entry in payload["checks"]
                ]
                if script == "check_badge_assets.py" and payload
                else (
                    json.loads(methods.read_text())
                    if methods.is_file()
                    else [
                        {
                            "check": "script assertions",
                            "driver": "controlled_api_or_state",
                            "fixture_uses_debugger_setup": True,
                            "note": "No named-check list in this diagnostic script; consult full log",
                        }
                    ]
                )
            )
        except (ValueError, OSError, KeyError, TypeError) as exc:
            records = []
            ok = False
            error = error or f"Invalid check-method evidence: {exc}"
        artifact = {
            **base,
            "fixture": name,
            "fixture_script": script,
            "fixture_script_sha256": script_hash,
            "configuration": extra or {},
            "loaded_archives": loaded,
            "seed_save_sha256": seed_hash,
            "started_at": start,
            "ended_at": now(),
            "status": "pass" if ok else "fail",
            "exit_code": code,
            "error": error,
            "checks": records,
            "observations": payload,
            "full_log": logtext,
        }
        (results / (name + ".result.json")).write_text(json.dumps(artifact, indent=2) + "\n")
        print(f'{name}: {artifact["status"]}', flush=True)
        if interrupted:
            failures.append(name)
            raise KeyboardInterrupt
        return ok

    all_cases = []

    def add(name, script, group, extra=None, kind="seed", suffix="runtime"):
        all_cases.append((name, script, group, extra or {}, kind, suffix))

    add("combat", "goombario_combat_gdb.py", "partner-combat", {"GOOMBARIO_LETHAL": "1", "GOOMBARIO_VISUAL": "0"})
    add(
        "combat-nonlethal-visual",
        "goombario_combat_gdb.py",
        "partner-combat",
        {"GOOMBARIO_LETHAL": "0", "GOOMBARIO_VISUAL": "1"},
    )
    add("hp-ownership", "partner_hp_ownership_gdb.py", "hp-ownership", {"HP_OWNERSHIP_BASELINE": os.environ.get("HP_OWNERSHIP_BASELINE", "0")})
    add("foundation-writer", "partner_hp_gdb.py", "partner-hp", kind="empty")
    add("foundation", "partner_hp_gdb.py", "partner-hp", {"PARTNER_HP_LOAD_ONLY": "1"}, kind="existing")
    add("healing", "partner_healing_gdb.py", "partner-healing")
    for prefix, script, group in [
        ("DUPLICATE_BADGES", "duplicate_badges_gdb.py", "duplicate-badges"),
        ("PITY_FLOWER", "pity_flower_gdb.py", "pity-flower"),
        ("DEFEND_PLUS", "defend_plus_gdb.py", "defend-plus"),
        ("JUMPMAN", "jumpman_gdb.py", "jumpman"),
        ("HAMMERMAN", "hammerman_gdb.py", "hammerman"),
        ("FP_DRAIN", "fp_drain_gdb.py", "fp-drain"),
        ("FLOWER_SAVER", "flower_saver_gdb.py", "flower-saver"),
    ]:
        add(group + "-writer", script, group, kind="empty")
        add(group, script, group, {prefix + "_LOAD_ONLY": "1"}, kind="existing")
    for name, extra, suffix in [
        ("fp-drain-coexist", {"FP_DRAIN_COEXIST": "1"}, "coexist-runtime"),
        ("fp-drain-cap", {"FP_DRAIN_FP_START": "98"}, "cap-runtime"),
        ("fp-drain-zero", {"FP_DRAIN_BASE_DAMAGE": "1"}, "zero-runtime"),
    ]:
        add(name, "fp_drain_gdb.py", "fp-drain", {"FP_DRAIN_LOAD_ONLY": "1", **extra}, kind="group-seed", suffix=suffix)
    add(
        "pity-flower-forced-guard",
        "pity_flower_gdb.py",
        "pity-flower",
        {"PITY_FLOWER_LOAD_ONLY": "1", "PITY_FLOWER_BLOCKED": "1"},
        kind="existing",
    )
    add(
        "defend-plus-forced-guard",
        "defend_plus_gdb.py",
        "defend-plus",
        {"DEFEND_PLUS_LOAD_ONLY": "1", "DEFEND_PLUS_BLOCKED": "1"},
        kind="existing",
    )
    add(
        "defend-plus-floor",
        "defend_plus_gdb.py",
        "defend-plus",
        {"DEFEND_PLUS_LOAD_ONLY": "1", "DEFEND_PLUS_INPUT": "1"},
        kind="existing",
    )
    add("world-badges-writer", "world_badges_gdb.py", "pity-flower", kind="empty", suffix="acquisition-runtime")
    add(
        "world-badges",
        "world_badges_gdb.py",
        "pity-flower",
        {"WORLD_BADGES_LOAD_ONLY": "1"},
        kind="existing",
        suffix="acquisition-runtime",
    )
    for name, script in [
        ("partner-world-heal", "partner_world_heal_gdb.py"),
        ("partner-world-hud", "partner_world_hud_gdb.py"),
        ("partner-world-swap", "partner_world_swap_gdb.py"),
        ("partner-battle-return", "partner_battle_return_gdb.py"),
    ]:
        add(name, script, name)
    for pid, phases in [
        (1, "pause,world-items,battle,team,victory,victory-dead,recovery,statuses"),
        (2, "ground-combat,ground-contracts,team,victory,victory-dead,recovery,statuses"),
        (3, "ground-combat,ground-contracts,team,victory,victory-dead,recovery,statuses"),
    ]:
        add(
            "partner-slice-" + str(pid),
            "partner_playable_slice_gdb.py",
            "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER": str(pid), "PARTNER_SLICE_PHASES": phases},
        )
    for pid in (1,2,3):
        add("world-special-"+str(pid), "partner_playable_slice_gdb.py", "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER":str(pid),"PARTNER_SLICE_PHASES":"world-special",
             "WORLD_SPECIAL_BASELINE":os.environ.get("PORTING_WORLD_SPECIAL_BASELINE","0")})
    for pid in (1,2,3):
        add("electric-foods-"+str(pid), "partner_playable_slice_gdb.py", "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER":str(pid),"PARTNER_SLICE_PHASES":"electric-foods",
             "ELECTRIC_FOODS_BASELINE":os.environ.get("PORTING_ELECTRIC_FOODS_BASELINE","0")})
    for pid in (1,2,3):
        add("food-recovery-"+str(pid), "partner_playable_slice_gdb.py", "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER":str(pid),"PARTNER_SLICE_PHASES":"food-recovery",
             "FOOD_RECOVERY_BASELINE":os.environ.get("PORTING_FOOD_RECOVERY_BASELINE","0")})
    for pid in (1,2,3):
        add("star-recovery-"+str(pid), "partner_playable_slice_gdb.py", "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER":str(pid),"PARTNER_SLICE_PHASES":"star-recovery",
             "STAR_RECOVERY_BASELINE":os.environ.get("PORTING_STAR_RECOVERY_BASELINE","0")})
    for pid in (1,2,3):
        add("partner-recovery-"+str(pid), "partner_playable_slice_gdb.py", "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER":str(pid),"PARTNER_SLICE_PHASES":"recovery"})
    for pid in (1,2,3):
        add("popup-review-"+str(pid), "partner_playable_slice_gdb.py", "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER":str(pid),"PARTNER_SLICE_PHASES":"popup-review",
             "PARTNER_POPUP_BASELINE":os.environ.get("PORTING_POPUP_BASELINE","0")})
    for name in ("orphan-badges","hammer-shrink"):
        add(name, "partner_playable_slice_gdb.py", "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER":"1","PARTNER_SLICE_PHASES":name,
             "MENU_SHRINK_BASELINE":os.environ.get("PORTING_MENU_SHRINK_BASELINE","0")})
    for pid in (1,2,3):
        add("defeat-review-"+str(pid), "partner_playable_slice_gdb.py", "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER":str(pid),"PARTNER_SLICE_PHASES":"defeat-review",
             "PARTNER_DEFEAT_BASELINE":os.environ.get("PORTING_DEFEAT_BASELINE","0")})
    for pid in (1,2,3):
        add("native-guard-"+str(pid), "partner_playable_slice_gdb.py", "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER":str(pid),"PARTNER_SLICE_PHASES":"native-guard"})
    for pid in (1,2,3):
        add("native-status-"+str(pid), "partner_playable_slice_gdb.py", "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER":str(pid),"PARTNER_SLICE_PHASES":"native-status",
             "PARTNER_STATUS_BASELINE":os.environ.get("PORTING_STATUS_BASELINE","0")})
    add("goomba-family", "partner_playable_slice_gdb.py", "partner-playable-slice",
        {"PARTNER_SLICE_PARTNER": "1", "PARTNER_SLICE_PHASES": "family",
         "PARTNER_FAMILY_BASELINE": os.environ.get("PORTING_FAMILY_BASELINE", "0")})
    for pid in (1, 2, 3):
        add(
            "partner-recovery-hooks-" + str(pid),
            "partner_playable_slice_gdb.py",
            "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER": str(pid), "PARTNER_SLICE_PHASES": "recovery-hooks",
             "PARTNER_RECOVERY_BASELINE": os.environ.get("PORTING_RECOVERY_BASELINE", "0")},
        )
    for pid in (1, 2, 3):
        add(
            "partner-level-up-" + str(pid),
            "partner_playable_slice_gdb.py",
            "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER": str(pid), "PARTNER_SLICE_PHASES": "level-up"},
        )
    for pid in (1, 2, 3):
        add(
            "actor-modifiers-" + str(pid),
            "partner_playable_slice_gdb.py",
            "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER": str(pid), "PARTNER_SLICE_PHASES": "modifiers"},
        )
    for pid in (1, 2, 3):
        add(
            "status-items-" + str(pid),
            "partner_playable_slice_gdb.py",
            "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER": str(pid), "PARTNER_SLICE_PHASES": "status-items",
             "ITEM_MESSAGES_BASELINE": os.environ.get("PORTING_ITEM_MESSAGES_BASELINE", "0")},
        )
    for pid in (1, 2, 3):
        add(
            "regeneration-" + str(pid),
            "partner_playable_slice_gdb.py",
            "partner-playable-slice",
            {"PARTNER_SLICE_PARTNER": str(pid), "PARTNER_SLICE_PHASES": "regeneration"},
        )
    add(
        "partner-ground-ui",
        "partner_playable_slice_gdb.py",
        "partner-playable-slice",
        {"PARTNER_SLICE_PARTNER": "1", "PARTNER_SLICE_PHASES": "ground-ui"},
    )
    add(
        "playtest-startup",
        "partner_playable_slice_gdb.py",
        "goombario-playtest/sessions/"
        + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S-")
        + uuid.uuid4().hex[:8],
        {
            "PARTNER_SLICE_PARTNER": "1",
            "PARTNER_SLICE_PLAYTEST": "1",
            "PARTNER_SLICE_VERIFY_ONLY": "1",
            "PARTNER_SLICE_GROUND": "1",
        },
    )
    add("badge-assets", "check_badge_assets.py", "badge-assets", kind="empty")
    add("last-stand", "last_stand_gdb.py", "last-stand", kind="empty")
    add("last-stand-vanilla", "last_stand_gdb.py", "last-stand-vanilla", {"LAST_STAND_VARIANT": "baseline"}, kind="empty")
    add("source-costs", "flower_saver_gdb.py", "flower-saver", {"FLOWER_SAVER_SOURCE_COSTS": "1", "FLOWER_SAVER_SOURCE_COSTS_BASELINE": os.environ.get("PORTING_SOURCE_COSTS_BASELINE", "0")}, kind="empty", suffix="cost-runtime")
    add("dip-native", "partner_playable_slice_gdb.py", "partner-playable-slice", {"PARTNER_SLICE_PARTNER": "1", "PARTNER_SLICE_PHASES": "dip"})
    add("bp-render", "partner_playable_slice_gdb.py", "partner-playable-slice", {"PARTNER_SLICE_PARTNER": "1", "PARTNER_SLICE_PHASES": "bp", "PARTNER_BP_BASELINE": os.environ.get("PORTING_DIP_BASELINE", "0")})
    add("dip-menu", "flower_saver_gdb.py", "flower-saver", {"FLOWER_SAVER_DIP": "1", "FLOWER_SAVER_DIP_BASELINE": os.environ.get("PORTING_DIP_BASELINE", "0")}, kind="empty", suffix="dip-runtime")
    add("flower-saver-vanilla", "flower_saver_gdb.py", "flower-saver", {"FLOWER_SAVER_BASELINE": "1"}, kind="empty", suffix="vanilla-runtime")
    add("duplicate-badges-vanilla", "duplicate_badges_gdb.py", "duplicate-badges", {"DUPLICATE_BADGES_VANILLA": "1"}, kind="empty", suffix="vanilla-runtime")
    add("last-stand-forced-guard", "last_stand_gdb.py", "last-stand-blocked", {"LAST_STAND_BLOCKED": "1"}, kind="empty")
    for name, script, group, suffix in [
        ("pity-animation", "pity_flower_animation.gdb", "pity-flower", "animation-runtime"),
        ("fp-drain-animation", "fp_drain_animation.gdb", "fp-drain", "animation-runtime"),
        ("flower-saver-visual", "flower_saver_visual.gdb", "flower-saver", "visual-runtime"),
    ]:
        add(name, script, group, kind="group-seed", suffix=suffix)
    selected = set(args.only.split(",")) if args.only else {c[0] for c in all_cases} | {"save-modes"}
    if "foundation" in selected:
        selected.add("foundation-writer")
    for name, script, group, extra, kind, suffix in list(all_cases):
        if name in selected and kind == "group-seed":
            selected.add(group + "-writer")
        if name in selected and kind == "existing":
            selected.add(next(c[0] for c in all_cases if c[2] == group and c[5] == suffix and c[4] == "empty"))
    unknown = selected - ({c[0] for c in all_cases} | {"save-modes"})
    if unknown:
        ap.error("Unknown fixture IDs: " + ",".join(sorted(unknown)))
    manifest = {
        **base,
        "started_at": now(),
        "requested_fixtures": sorted(selected),
        "skipped_fixtures": [name for name in [c[0] for c in all_cases] + ["save-modes"] if name not in selected],
    }
    failures = []
    xvfb = None
    xlog = None
    try:
        # Let Xvfb atomically allocate a free display; never remove another server's lock.
        read_fd, write_fd = os.pipe()
        xlog = (results / "xvfb.log").open("w")
        xvfb = subprocess.Popen(
            ["Xvfb", "-displayfd", str(write_fd), "-screen", "0", "1280x720x24", "-nolisten", "tcp"],
            pass_fds=(write_fd,),
            stdout=xlog,
            stderr=xlog,
        )
        os.close(write_fd)
        import select

        if not select.select([read_fd], [], [], 20)[0]:
            raise RuntimeError("Xvfb did not allocate a display")
        # Xvfb writes the digits and newline separately. A single os.read can
        # return only the digits; closing then breaks its second write (SIGPIPE).
        # Consume the full readiness line before closing our end of the pipe.
        with os.fdopen(read_fd) as display_pipe:
            display_number = display_pipe.readline().strip()
        if not display_number.isdigit() or xvfb.poll() is not None:
            raise RuntimeError("Xvfb failed before reporting a ready display; see xvfb.log")
        env["DISPLAY"] = ":" + display_number
        run(["xdpyinfo"], env=env, stdout=subprocess.DEVNULL)
        seedhome = runtime("seed")
        env["PORTING_SEED_SAVE"] = str(seedhome / "saves/file3.json")
        if not execute("seed", "seed_new_game_gdb.py", seedhome):
            failures.append("seed")
            raise RuntimeError("Cannot generate native new-game seed")
        for name, script, group, extra, kind, suffix in all_cases:
            if name not in selected:
                continue
            home = work / group / suffix
            if kind != "existing":
                if home.exists():
                    shutil.rmtree(home)
                home = runtime(group, suffix)
                if extra.get("PARTNER_SLICE_PLAYTEST") == "1":
                    (home.parent / ".owned-playtest").write_text("PaperBoat Goombario isolated playtest v1\n")
            if not execute(
                name,
                script,
                home,
                extra,
                (
                    seedhome / "saves/file3.json"
                    if kind == "seed"
                    else (work / group / "runtime/saves/file3.json" if kind == "group-seed" else None)
                ),
            ):
                failures.append(name)
        if "save-modes" in selected:
            # One shared lifecycle group, with separate per-scenario receipts.
            name, driver = "save-modes", fixture_dir / "check_save_modes.py"
            verify_fixture(driver)
            attempted.append(name)
            started = now()
            output = results / name
            command = [sys.executable, str(driver), "--source", str(source), "--executable", str(binary),
                       "--package", str(build), "--archive", str(archive), "--output", str(output),
                       "--fixture-commit", fixture_commit]
            with (results / (name + ".log")).open("w") as log:
                process = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
            child_paths = sorted(output.glob("*-result.json"))
            children = [json.loads(path.read_text()) for path in child_paths]
            ok = process.returncode == 0 and len(children) == 4 and all(
                child["status"] == "pass" and child["git_commit"] == commit
                and child["executable_sha256"] == base["executable_sha256"]
                and child["fixture_commit"] == fixture_commit and child["fixture_sha256"] == sha(driver)
                and child["rom_archive_sha256"] == base["rom_archive_sha256"]
                and child["port_archive_sha256"] == base["port_archive_sha256"] for child in children)
            report = {**base, "fixture": name, "fixture_sha256": sha(driver), "started_at": started,
                      "ended_at": now(), "status": "pass" if ok else "fail", "command": command,
                      "scenario_results": [{"path": str(path.relative_to(results)), "sha256": sha(path)} for path in child_paths],
                      "check_methods": [dict(check=child.get("scenario", "") + ": " + check["check"], driver=check["method"])
                                        for child in children for check in child.get("checks", [])],
                      "full_log": (results / (name + ".log")).read_text() + "\n" + "\n".join(child["full_log"] for child in children)}
            (results / (name + ".result.json")).write_text(json.dumps(report, indent=2) + "\n")
            if not ok: failures.append(name)
            print(name + ": " + report["status"], flush=True)
    except BaseException as exc:
        failures.append("runner-aborted")
        manifest["runner_error"] = repr(exc)
        raise
    finally:
        if xvfb:
            xvfb.terminate()
            xvfb.wait(timeout=10)
        if xlog:
            xlog.close()
        unchanged = (
            git(source, "rev-parse", "HEAD") == commit
            and not git(source, "status", "--porcelain", "--untracked-files=normal")
            and sha(binary) == base["executable_sha256"]
            and sha(staged_binary) == base["executable_sha256"]
            and sha(archive) == base["rom_archive_sha256"]
            and sha(port) == base["port_archive_sha256"]
            and sha(Path(__file__)) == base["runner_sha256"]
            and sha(fixture_dir / "fixture_support.py") == base["helper_sha256"]
        )
        if not unchanged:
            failures.append("source-or-driver-changed")
            for artifact_path in results.glob("*.result.json"):
                artifact = json.loads(artifact_path.read_text())
                artifact.update(status="fail", error="Source, binary, archives or driver changed during acceptance")
                artifact_path.write_text(json.dumps(artifact, indent=2) + "\n")
        manifest.update(
            ended_at=now(),
            failed_fixtures=failures,
            attempted_fixtures=attempted,
            not_run_fixtures=sorted(selected - set(attempted)),
        )
        (results / "run-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if (
        git(source, "rev-parse", "HEAD") != commit
        or git(source, "status", "--porcelain", "--untracked-files=normal")
        or sha(binary) != base["executable_sha256"]
    ):
        raise RuntimeError("Source/executable changed during acceptance; discard results")
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())

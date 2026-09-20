"""
cli.py - the `student-wiki` command.

  student-wiki init [DIR] [--dry-run] [--json]
  student-wiki upgrade [--root DIR] [--force] [--dry-run] [--json]
  student-wiki doctor [--root DIR] [--json]
  student-wiki tracker <command> ...     deadlines, grades, calendar (see: tracker --help)
  student-wiki file <path> ...           file a course source into raw/ (see: file --help)
"""
import argparse
import sys

from . import __version__
from .vault import ROOT_HELP

EPILOG = """more commands:
  tracker   deadlines, exams, to-dos, grades and the calendar feed (student-wiki tracker --help)
  file      file a course source into raw/ with provenance (student-wiki file --help)
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="student-wiki", description="Create, upgrade and run a student knowledge wiki.",
        epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"student-wiki {__version__}")
    commands = parser.add_subparsers(dest="command", required=True, metavar="{init,upgrade,doctor,tracker,file}")

    init = commands.add_parser("init", help="create a vault")
    init.add_argument("dir", nargs="?", default=".", help="vault folder (default: the current directory)")
    init.add_argument("--dry-run", action="store_true", help="print the proposal and write nothing")
    init.add_argument("--json", action="store_true", help="print one JSON object")

    upgrade = commands.add_parser("upgrade", help="refresh the tool-owned files in a vault")
    upgrade.add_argument("--root", help=ROOT_HELP)
    upgrade.add_argument("--force", action="store_true", help="back up locally modified files, then overwrite them")
    upgrade.add_argument("--dry-run", action="store_true", help="print the proposal and write nothing")
    upgrade.add_argument("--json", action="store_true", help="print one JSON object")

    doctor = commands.add_parser("doctor", help="check the install and the vault")
    doctor.add_argument("--root", help=ROOT_HELP)
    doctor.add_argument("--json", action="store_true", help="print one JSON object")
    return parser


def dispatch(argv) -> None:
    if argv and argv[0] == "tracker":
        from . import tracker
        return tracker.main(argv[1:])
    if argv and argv[0] == "file":
        from . import file_source
        return file_source.main(argv[1:])
    args = build_parser().parse_args(argv)
    from . import scaffold
    {"init": scaffold.cmd_init, "upgrade": scaffold.cmd_upgrade, "doctor": scaffold.cmd_doctor}[args.command](args)


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if "--hook" in argv:
        # A session hook must never block the session: bad arguments and a missing vault included.
        try:
            dispatch(argv)
        except BaseException:
            pass
        sys.exit(0)
    dispatch(argv)

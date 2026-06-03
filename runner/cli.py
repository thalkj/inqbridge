"""Command-line interface for the Inquisit runner."""
import argparse
import json
import sys

from .run import run_script


def main():
    parser = argparse.ArgumentParser(
        description="InqBridge: Audited local runner for Inquisit scripts"
    )
    parser.add_argument("script", help="Path to the .iqx script to run")
    parser.add_argument("-m", "--mode", default="monkey", choices=["human", "monkey"],
                        help="Run mode (default: monkey)")
    parser.add_argument("-s", "--subject-id", default="1", help="Subject ID (default: 1)")
    parser.add_argument("-g", "--group-id", default="1", help="Group ID (default: 1)")
    parser.add_argument("--timeout", type=int, default=600,
                        help="Timeout in seconds (default: 600)")
    parser.add_argument("--artifacts-dir", help="Override artifacts output directory")
    parser.add_argument("--inquisit-exe", help="Override Inquisit executable path")
    parser.add_argument("--fast-mode", action="store_true",
                        help="Collapse timings for quick compile/data/layout checks")
    parser.add_argument("--auto-capture", action="store_true",
                        help="Inject screenCapture=true into temp trial-like copies")
    parser.add_argument("--auto-fix", action="store_true",
                        help="Attempt one auto-fix retry on compile errors")

    args = parser.parse_args()

    try:
        result = run_script(
            script_path=args.script,
            mode=args.mode,
            subject_id=args.subject_id,
            group_id=args.group_id,
            timeout_seconds=args.timeout,
            artifacts_dir=args.artifacts_dir,
            inquisit_exe=args.inquisit_exe,
            fast_mode=args.fast_mode,
            auto_capture=args.auto_capture,
            auto_fix=args.auto_fix,
        )
        print(json.dumps(result, indent=2))
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

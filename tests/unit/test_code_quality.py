"""Test code quality metrics including duplicate code detection."""

import subprocess
import sys
from pathlib import Path


def test_no_duplicate_code():
    """Test that there is no duplicate code in the raillock package."""

    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent
    raillock_dir = project_root / "raillock"

    # Run pylint duplicate code check
    cmd = [
        sys.executable,
        "-m",
        "pylint",
        "--disable=all",
        "--enable=duplicate-code",
        str(raillock_dir),
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_root,
            check=False,  # Don't raise on non-zero exit
        )

        # Pylint returns non-zero for any issues, but we only care about duplicate code
        # If there are duplicate code issues, they'll be in stdout
        if "R0801" in result.stdout or "duplicate-code" in result.stdout:
            # Extract just the duplicate code warnings
            lines = result.stdout.split("\n")
            duplicate_lines = [
                line for line in lines if "R0801" in line or "Similar lines" in line
            ]
            if duplicate_lines:
                failure_msg = "Duplicate code detected:\n" + "\n".join(duplicate_lines)
                raise AssertionError(failure_msg)

        # If we get here, no duplicate code was found
        print("✓ No duplicate code detected")

    except subprocess.CalledProcessError as e:
        raise AssertionError(f"Failed to run pylint duplicate code check: {e}")
    except FileNotFoundError:
        raise AssertionError("pylint not found. Install with: uv add pylint --dev")

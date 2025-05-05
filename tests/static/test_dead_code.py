"""
Test for dead code in the raillock package.
"""

import os
import unittest
import subprocess


class TestDeadCode(unittest.TestCase):
    def setUp(self):
        """Set up test environment."""
        # Get the project root using os.path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(os.path.dirname(current_dir))
        self.whitelist_path = os.path.join(
            self.project_root, "tests", "static", "whitelist.py"
        )
        self.raillock_dir = os.path.join(self.project_root, "raillock")
        self.vendor_dir = os.path.join(self.raillock_dir, "vendor")  # Path to ignore

    def test_no_dead_code_in_raillock(self):
        """
        Run vulture to find dead code in the raillock package,
        excluding the vendor directory and using the whitelist.
        """
        cmd = [
            "vulture",
            self.raillock_dir,
            self.whitelist_path,
            "--exclude",
            self.vendor_dir,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.project_root
        )

        if result.returncode != 0 and "vulture: error:" in result.stderr:
            self.fail(f"Vulture command failed:\n{result.stderr}")

        self.assertEqual(
            result.stdout.strip(),
            "",
            f"Vulture found potential dead code:\n{result.stdout}",
        )


if __name__ == "__main__":
    unittest.main()

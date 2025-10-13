#!/usr/bin/env python3
"""
API v2 All-in-One Script for Speed Roulette 2 (VR-2)
parallel execution of four environments' API test scripts

supported environments:
- CIT-2 (cit_vr_2.py)
- QAT-2 (qat_vr_2.py)
- UAT-2 (uat_vr_2.py)
- STG-2 (stg_vr_2.py)
"""

import asyncio
import concurrent.futures
import subprocess
import sys
import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Tuple

# set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class APIv2AllVR2Runner:
    """parallel execution of four Speed Roulette 2 API environments' executor"""

    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.api_scripts = {
            "CIT-2": "cit_vr_2.py",
            "QAT-2": "qat_vr_2.py",
            "UAT-2": "uat_vr_2.py",
            "STG-2": "stg_vr_2.py",
        }
        self.results = {}
        self.execution_times = {}

    def run_single_api_script(
        self, env_name: str, script_name: str
    ) -> Tuple[str, bool, float, str]:
        """
        execute single Speed Roulette 2 API script

        Args:
            env_name: environment name (CIT-2, QAT-2, UAT-2, STG-2)
            script_name: script file name

        Returns:
            Tuple[environment name, success, execution time, output result]
        """
        script_path = self.script_dir / script_name

        if not script_path.exists():
            return env_name, False, 0.0, f"Script not found: {script_path}"

        start_time = time.time()

        try:
            # execute Python script
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=60,  # 60 seconds timeout
                cwd=self.script_dir,
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                return env_name, True, execution_time, result.stdout
            else:
                return (
                    env_name,
                    False,
                    execution_time,
                    f"Error: {result.stderr}",
                )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return env_name, False, execution_time, "Execution timeout (60s)"
        except Exception as e:
            execution_time = time.time() - start_time
            return env_name, False, execution_time, f"Exception: {str(e)}"

    def run_all_parallel(self) -> Dict[str, Dict]:
        """
        parallel execution of all Speed Roulette 2 API scripts

        Returns:
            execution result dictionary
        """
        logger.info(
            "Starting parallel execution of all Speed Roulette 2 API scripts..."
        )

        # use ThreadPoolExecutor to execute in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # submit all tasks
            future_to_env = {
                executor.submit(
                    self.run_single_api_script, env_name, script_name
                ): env_name
                for env_name, script_name in self.api_scripts.items()
            }

            # collect results
            for future in concurrent.futures.as_completed(future_to_env):
                env_name = future_to_env[future]
                try:
                    env_name, success, execution_time, output = future.result()
                    self.results[env_name] = {
                        "success": success,
                        "execution_time": execution_time,
                        "output": output,
                    }
                    self.execution_times[env_name] = execution_time

                    status = "✓ SUCCESS" if success else "✗ FAILED"
                    logger.info(
                        f"{env_name}: {status} ({execution_time:.2f}s)"
                    )

                except Exception as e:
                    logger.error(f"{env_name}: Exception occurred: {e}")
                    self.results[env_name] = {
                        "success": False,
                        "execution_time": 0.0,
                        "output": f"Exception: {str(e)}",
                    }

        return self.results

    def run_all_sequential(self) -> Dict[str, Dict]:
        """
        sequential execution of all Speed Roulette 2 API scripts (for comparison)

        Returns:
            execution result dictionary
        """
        logger.info(
            "Starting sequential execution of all Speed Roulette 2 API scripts..."
        )

        for env_name, script_name in self.api_scripts.items():
            logger.info(f"Executing {env_name}...")
            env_name, success, execution_time, output = (
                self.run_single_api_script(env_name, script_name)
            )

            self.results[env_name] = {
                "success": success,
                "execution_time": execution_time,
                "output": output,
            }
            self.execution_times[env_name] = execution_time

            status = "✓ SUCCESS" if success else "✗ FAILED"
            logger.info(f"{env_name}: {status} ({execution_time:.2f}s)")

        return self.results

    def print_summary(self):
        """print execution summary"""
        print("\n" + "=" * 80)
        print("Speed Roulette 2 API v2 All-in-One Execution Summary")
        print("=" * 80)

        total_time = sum(self.execution_times.values())
        success_count = sum(
            1 for result in self.results.values() if result["success"]
        )
        total_count = len(self.results)

        print(f"Total Scripts: {total_count}")
        print(f"Successful: {success_count}")
        print(f"Failed: {total_count - success_count}")
        print(f"Total Execution Time: {total_time:.2f} seconds")
        print(f"Average Execution Time: {total_time/total_count:.2f} seconds")

        print("\nDetailed Results:")
        print("-" * 80)

        for env_name, result in self.results.items():
            status = "✓ SUCCESS" if result["success"] else "✗ FAILED"
            print(
                f"{env_name:>6}: {status:>12} | {result['execution_time']:>6.2f}s"
            )

            if not result["success"]:
                print(f"         Error: {result['output'][:100]}...")

        print("-" * 80)

    def save_outputs(self, output_dir: str = "vr2_api_outputs"):
        """save all Speed Roulette 2 scripts' outputs to file"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        for env_name, result in self.results.items():
            output_file = output_path / f"{env_name.lower().replace('-', '_')}_vr2_output.txt"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"Environment: {env_name}\n")
                f.write(f"Success: {result['success']}\n")
                f.write(f"Execution Time: {result['execution_time']:.2f}s\n")
                f.write(f"Output:\n{'-'*50}\n")
                f.write(result["output"])

            logger.info(
                f"Saved {env_name} Speed Roulette 2 output to {output_file}"
            )


def main():
    """main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="parallel execution of four Speed Roulette 2 API environments' scripts"
    )
    parser.add_argument(
        "--mode",
        choices=["parallel", "sequential"],
        default="parallel",
        help="execution mode: parallel (parallel) or sequential (sequential)",
    )
    parser.add_argument(
        "--save-outputs",
        action="store_true",
        help="save all Speed Roulette 2 scripts outputs to file",
    )
    parser.add_argument(
        "--output-dir",
        default="vr2_api_outputs",
        help="output file directory (default: vr2_api_outputs)",
    )

    args = parser.parse_args()

    runner = APIv2AllVR2Runner()

    try:
        if args.mode == "parallel":
            logger.info("Running Speed Roulette 2 APIs in PARALLEL mode")
            results = runner.run_all_parallel()
        else:
            logger.info("Running Speed Roulette 2 APIs in SEQUENTIAL mode")
            results = runner.run_all_sequential()

        # print summary
        runner.print_summary()

        # optional: save outputs
        if args.save_outputs:
            runner.save_outputs(args.output_dir)

        # check if there are failed scripts
        failed_count = sum(
            1 for result in results.values() if not result["success"]
        )
        if failed_count > 0:
            logger.warning(f"{failed_count} Speed Roulette 2 script(s) failed")
            sys.exit(1)
        else:
            logger.info("All Speed Roulette 2 scripts completed successfully!")

    except KeyboardInterrupt:
        logger.info("Speed Roulette 2 execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in Speed Roulette 2 execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

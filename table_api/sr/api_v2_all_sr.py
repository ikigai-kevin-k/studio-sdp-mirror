#!/usr/bin/env python3
"""
API v2 All-in-One Script for Speed Roulette (SR)
parallel execution of thirteen environments' API test scripts

supported environments:
- CIT (api_v2_sr.py)
- PRD (api_v2_prd_sr.py)
- PRD-5 (api_v2_prd_sr_5.py)
- PRD-6 (api_v2_prd_sr_6.py)
- PRD-7 (api_v2_prd_sr_7.py)
- STG (api_v2_stg_sr.py)
- QAT (api_v2_qat_sr.py)
- UAT (api_v2_uat_sr.py)
- DEV (api_v2_dev_sr.py)
- CIT-5 (api_v2_sr_5.py)
- CIT-6 (api_v2_sr_6.py)
- CIT-7 (api_v2_sr_7.py)
- GLC (api_v2_glc_sr.py)
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


class APIv2AllSRRunner:
    """parallel execution of thirteen Speed Roulette API environments' executor"""

    def __init__(self, deal_result: str = None):
        self.script_dir = Path(__file__).parent
        self.api_scripts = {
            "CIT": "api_v2_sr.py",
            "PRD": "api_v2_prd_sr.py",
            "PRD-5": "api_v2_prd_sr_5.py",
            "PRD-6": "api_v2_prd_sr_6.py",
            "PRD-7": "api_v2_prd_sr_7.py",
            "STG": "api_v2_stg_sr.py",
            "QAT": "api_v2_qat_sr.py",
            "UAT": "api_v2_uat_sr.py",
            "DEV": "api_v2_dev_sr.py",
            "CIT-5": "api_v2_sr_5.py",
            "CIT-6": "api_v2_sr_6.py",
            "CIT-7": "api_v2_sr_7.py",
            "GLC": "api_v2_glc_sr.py",
        }
        self.results = {}
        self.execution_times = {}
        self.deal_result = deal_result

    def run_single_api_script(
        self, env_name: str, script_name: str
    ) -> Tuple[str, bool, float, str]:
        """
        execute single Speed Roulette API script

        Args:
            env_name: environment name (CIT, PRD, PRD-5, PRD-6, PRD-7, STG, QAT, UAT, DEV, CIT-5, CIT-6, CIT-7, GLC)
            script_name: script file name

        Returns:
            Tuple[environment name, success, execution time, output result]
        """
        script_path = self.script_dir / script_name

        if not script_path.exists():
            return env_name, False, 0.0, f"Script not found: {script_path}"

        start_time = time.time()

        try:
            # build command arguments
            cmd = [sys.executable, str(script_path)]
            
            # if deal_result exists, add --result parameter
            if self.deal_result is not None:
                cmd.extend(["--result", self.deal_result])
            
            # execute Python script
            result = subprocess.run(
                cmd,
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
        parallel execution of all Speed Roulette API scripts

        Returns:
            execution result dictionary
        """
        logger.info(
            "Starting parallel execution of all Speed Roulette API scripts..."
        )

        # use ThreadPoolExecutor to execute in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=13) as executor:
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
        sequential execution of all Speed Roulette API scripts (for comparison)

        Returns:
            execution result dictionary
        """
        logger.info(
            "Starting sequential execution of all Speed Roulette API scripts..."
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
        print("Speed Roulette API v2 All-in-One Execution Summary")
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

    def save_outputs(self, output_dir: str = "sr_api_outputs"):
        """save all Speed Roulette scripts' outputs to file"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        for env_name, result in self.results.items():
            output_file = output_path / f"{env_name.lower()}_sr_output.txt"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"Environment: {env_name}\n")
                f.write(f"Success: {result['success']}\n")
                f.write(f"Execution Time: {result['execution_time']:.2f}s\n")
                f.write(f"Output:\n{'-'*50}\n")
                f.write(result["output"])

            logger.info(
                f"Saved {env_name} Speed Roulette output to {output_file}"
            )


def main():
    """main function"""
    import argparse

    parser = argparse.ArgumentParser(
        description="parallel execution of thirteen Speed Roulette API environments' scripts"
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
        help="save all Speed Roulette scripts outputs to file",
    )
    parser.add_argument(
        "--output-dir",
        default="sr_api_outputs",
        help="output file directory (default: sr_api_outputs)",
    )
    parser.add_argument(
        "--result",
        type=str,
        default=None,
        help="Deal result to pass to deal post (e.g., '0')",
    )

    args = parser.parse_args()

    # parse deal_result parameter
    deal_result = None
    if args.result:
        deal_result = args.result.strip()
        # validate that it's a valid number string
        try:
            int(deal_result)  # validate it's a number
            logger.info(f"Deal result parsed: {deal_result}")
        except ValueError as e:
            logger.error(
                f"Invalid --result format: {args.result}. "
                f"Expected format: a number string (e.g., '0'). Error: {e}"
            )
            sys.exit(1)

    runner = APIv2AllSRRunner(deal_result=deal_result)

    try:
        if args.mode == "parallel":
            logger.info("Running Speed Roulette APIs in PARALLEL mode")
            results = runner.run_all_parallel()
        else:
            logger.info("Running Speed Roulette APIs in SEQUENTIAL mode")
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
            logger.warning(f"{failed_count} Speed Roulette script(s) failed")
            sys.exit(1)
        else:
            logger.info("All Speed Roulette scripts completed successfully!")

    except KeyboardInterrupt:
        logger.info("Speed Roulette execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in Speed Roulette execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

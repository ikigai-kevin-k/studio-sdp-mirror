#!/usr/bin/env python3
"""
API v2 All-in-One Script
並行執行五個環境的 API 測試腳本

支援環境：
- CIT (api_v2_sb.py)
- PRD (api_v2_prd_sb.py)
- STG (api_v2_stg_sb.py)
- QAT (api_v2_qat_sb.py)
- UAT (api_v2_uat_sb.py)
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

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class APIv2AllRunner:
    """並行執行五個 API 環境的執行器"""

    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.api_scripts = {
            "CIT": "api_v2_sb.py",
            "PRD": "api_v2_prd_sb.py",
            "STG": "api_v2_stg_sb.py",
            "QAT": "api_v2_qat_sb.py",
            "UAT": "api_v2_uat_sb.py",
        }
        self.results = {}
        self.execution_times = {}

    def run_single_api_script(
        self, env_name: str, script_name: str
    ) -> Tuple[str, bool, float, str]:
        """
        執行單個 API 腳本

        Args:
            env_name: 環境名稱 (CIT, PRD, STG, QAT, UAT)
            script_name: 腳本檔案名稱

        Returns:
            Tuple[環境名稱, 是否成功, 執行時間, 輸出結果]
        """
        script_path = self.script_dir / script_name

        if not script_path.exists():
            return env_name, False, 0.0, f"Script not found: {script_path}"

        start_time = time.time()

        try:
            # 執行 Python 腳本
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                timeout=60,  # 60 秒超時
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
        並行執行所有 API 腳本

        Returns:
            執行結果字典
        """
        logger.info("Starting parallel execution of all API scripts...")

        # 使用 ThreadPoolExecutor 進行並行執行
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            # 提交所有任務
            future_to_env = {
                executor.submit(
                    self.run_single_api_script, env_name, script_name
                ): env_name
                for env_name, script_name in self.api_scripts.items()
            }

            # 收集結果
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
        順序執行所有 API 腳本（用於比較）

        Returns:
            執行結果字典
        """
        logger.info("Starting sequential execution of all API scripts...")

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
        """打印執行摘要"""
        print("\n" + "=" * 80)
        print("API v2 All-in-One Execution Summary")
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

    def save_outputs(self, output_dir: str = "api_outputs"):
        """保存所有腳本的輸出到檔案"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        for env_name, result in self.results.items():
            output_file = output_path / f"{env_name.lower()}_output.txt"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"Environment: {env_name}\n")
                f.write(f"Success: {result['success']}\n")
                f.write(f"Execution Time: {result['execution_time']:.2f}s\n")
                f.write(f"Output:\n{'-'*50}\n")
                f.write(result["output"])

            logger.info(f"Saved {env_name} output to {output_file}")


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="並行執行五個 API 環境的腳本")
    parser.add_argument(
        "--mode",
        choices=["parallel", "sequential"],
        default="parallel",
        help="執行模式：並行 (parallel) 或順序 (sequential)",
    )
    parser.add_argument(
        "--save-outputs", action="store_true", help="保存所有腳本的輸出到檔案"
    )
    parser.add_argument(
        "--output-dir",
        default="api_outputs",
        help="輸出檔案目錄 (預設: api_outputs)",
    )

    args = parser.parse_args()

    runner = APIv2AllRunner()

    try:
        if args.mode == "parallel":
            logger.info("Running in PARALLEL mode")
            results = runner.run_all_parallel()
        else:
            logger.info("Running in SEQUENTIAL mode")
            results = runner.run_all_sequential()

        # 打印摘要
        runner.print_summary()

        # 可選：保存輸出
        if args.save_outputs:
            runner.save_outputs(args.output_dir)

        # 檢查是否有失敗的腳本
        failed_count = sum(
            1 for result in results.values() if not result["success"]
        )
        if failed_count > 0:
            logger.warning(f"{failed_count} script(s) failed")
            sys.exit(1)
        else:
            logger.info("All scripts completed successfully!")

    except KeyboardInterrupt:
        logger.info("Execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

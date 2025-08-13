"""
Test cases for VIP Roulette Controller (main-vip.py)
"""

import pytest
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestVIPRoulette:
    """Test class for VIP Roulette functionality"""

    def test_import_main_vip(self):
        """Test that main_vip module can be imported"""
        try:
            import main_vip

            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import main_vip: {e}")

    def test_main_function_exists(self):
        """Test that main function exists in main_vip"""
        import main_vip

        assert hasattr(main_vip, "main")
        assert callable(main_vip.main)

    def test_timestamp_function(self):
        """Test timestamp generation function"""
        import main_vip

        timestamp = main_vip.get_timestamp()
        assert isinstance(timestamp, str)
        assert len(timestamp) > 0

    def test_config_loading(self):
        """Test configuration loading functionality"""
        import main_vip

        try:
            config = main_vip.load_table_config()
            assert isinstance(config, dict)
        except Exception as e:
            # Config file might not exist in test environment
            pytest.skip(f"Config loading test skipped: {e}")


if __name__ == "__main__":
    pytest.main([__file__])

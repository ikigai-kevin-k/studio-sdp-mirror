"""
Unified MQTT Configuration Manager

This module provides a unified configuration management system for MQTT clients
across different game types (Sicbo, Baccarat, Roulette).

Features:
- Centralized configuration management
- JSON configuration file support
- Game-specific configuration templates
- Environment-based configuration switching
- Configuration validation and error handling
- Default configuration fallbacks
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


class GameType(Enum):
    """Supported game types"""
    SICBO = "sicbo"
    BACCARAT = "baccarat"
    ROULETTE = "roulette"


class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class BrokerConfig:
    """Broker configuration data class"""
    broker: str
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    priority: int = 1
    keepalive: int = 60
    ssl: bool = False
    ssl_ca_certs: Optional[str] = None
    ssl_certfile: Optional[str] = None
    ssl_keyfile: Optional[str] = None


@dataclass
class GameConfig:
    """Game-specific configuration"""
    game_type: GameType
    game_code: str
    command_topic: str
    response_topic: str
    shaker_topic: Optional[str] = None
    status_topic: Optional[str] = None
    timeout: int = 10
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class MQTTConfig:
    """Complete MQTT configuration"""
    client_id: str
    brokers: List[BrokerConfig]
    game_config: GameConfig
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    max_history_size: int = 100
    reconnect_delay: float = 5.0
    max_connection_attempts: int = 3
    default_username: str = "PFC"
    default_password: str = "wago"


class MQTTConfigManager:
    """
    Unified MQTT Configuration Manager
    
    This class provides centralized configuration management for MQTT clients
    across different game types and environments.
    """

    def __init__(self, config_dir: str = "conf"):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger("MQTTConfigManager")
        
        # Cache for loaded configurations
        self._config_cache: Dict[str, MQTTConfig] = {}
        
        # Default configurations
        self._default_configs = self._create_default_configs()

    def _create_default_configs(self) -> Dict[str, MQTTConfig]:
        """Create default configurations for each game type"""
        default_configs = {}
        
        # Default broker configurations
        default_brokers = [
            BrokerConfig(
                broker="192.168.20.9",
                port=1883,
                username="PFC",
                password="wago",
                priority=1
            ),
            BrokerConfig(
                broker="192.168.20.10",
                port=1883,
                username="PFC",
                password="wago",
                priority=2
            )
        ]
        
        # Sicbo default configuration
        sicbo_game_config = GameConfig(
            game_type=GameType.SICBO,
            game_code="SBO-001",
            command_topic="ikg/idp/SBO-001/command",
            response_topic="ikg/idp/SBO-001/response",
            shaker_topic="ikg/sicbo/Billy-III/listens",
            status_topic="ikg/sicbo/Billy-III/says",
            timeout=10,
            retry_count=3
        )
        
        default_configs["sicbo"] = MQTTConfig(
            client_id="sicbo_client",
            brokers=default_brokers.copy(),
            game_config=sicbo_game_config,
            environment=Environment.DEVELOPMENT
        )
        
        # Baccarat default configuration
        baccarat_game_config = GameConfig(
            game_type=GameType.BACCARAT,
            game_code="BAC-001",
            command_topic="ikg/idp/BAC-001/command",
            response_topic="ikg/idp/BAC-001/response",
            timeout=10,
            retry_count=3
        )
        
        default_configs["baccarat"] = MQTTConfig(
            client_id="baccarat_client",
            brokers=default_brokers.copy(),
            game_config=baccarat_game_config,
            environment=Environment.DEVELOPMENT
        )
        
        # Roulette default configuration
        roulette_game_config = GameConfig(
            game_type=GameType.ROULETTE,
            game_code="ROU-001",
            command_topic="ikg/idp/ROU-001/command",
            response_topic="ikg/idp/ROU-001/response",
            timeout=10,
            retry_count=3
        )
        
        default_configs["roulette"] = MQTTConfig(
            client_id="roulette_client",
            brokers=default_brokers.copy(),
            game_config=roulette_game_config,
            environment=Environment.DEVELOPMENT
        )
        
        return default_configs

    def load_config_from_file(
        self,
        game_type: Union[str, GameType],
        environment: Union[str, Environment] = Environment.DEVELOPMENT
    ) -> MQTTConfig:
        """
        Load configuration from JSON file
        
        Args:
            game_type: Game type (sicbo, baccarat, roulette)
            environment: Environment (development, staging, production)
            
        Returns:
            MQTTConfig object
            
        Raises:
            FileNotFoundError: If configuration file not found
            ValueError: If configuration is invalid
        """
        # Normalize inputs
        if isinstance(game_type, str):
            game_type = GameType(game_type.lower())
        if isinstance(environment, str):
            environment = Environment(environment.lower())
        
        # Create cache key
        cache_key = f"{game_type.value}_{environment.value}"
        
        # Check cache first
        if cache_key in self._config_cache:
            self.logger.debug(f"Using cached configuration for {cache_key}")
            return self._config_cache[cache_key]
        
        # Try to load from file
        config_file = self.config_dir / f"{game_type.value}-broker.json"
        
        if not config_file.exists():
            self.logger.warning(
                f"Configuration file not found: {config_file}. Using default configuration."
            )
            return self.get_default_config(game_type)
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Parse configuration
            config = self._parse_config_from_dict(config_data, game_type, environment)
            
            # Cache the configuration
            self._config_cache[cache_key] = config
            
            self.logger.info(f"Loaded configuration from {config_file}")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration from {config_file}: {e}")
            self.logger.info(f"Falling back to default configuration for {game_type.value}")
            return self.get_default_config(game_type)

    def _parse_config_from_dict(
        self,
        config_data: Dict[str, Any],
        game_type: GameType,
        environment: Environment
    ) -> MQTTConfig:
        """Parse configuration from dictionary"""
        try:
            # Parse brokers
            brokers = []
            for broker_data in config_data.get("brokers", []):
                broker = BrokerConfig(
                    broker=broker_data["broker"],
                    port=broker_data.get("port", 1883),
                    username=broker_data.get("username"),
                    password=broker_data.get("password"),
                    priority=broker_data.get("priority", 1),
                    keepalive=broker_data.get("keepalive", 60),
                    ssl=broker_data.get("ssl", False),
                    ssl_ca_certs=broker_data.get("ssl_ca_certs"),
                    ssl_certfile=broker_data.get("ssl_certfile"),
                    ssl_keyfile=broker_data.get("ssl_keyfile")
                )
                brokers.append(broker)
            
            # Parse game configuration
            game_config_data = config_data.get("game_config", {})
            game_config = GameConfig(
                game_type=game_type,
                game_code=game_config_data.get("game_code", f"{game_type.value.upper()}-001"),
                command_topic=game_config_data.get("command_topic", f"ikg/idp/{game_type.value.upper()}-001/command"),
                response_topic=game_config_data.get("response_topic", f"ikg/idp/{game_type.value.upper()}-001/response"),
                shaker_topic=game_config_data.get("shaker_topic"),
                status_topic=game_config_data.get("status_topic"),
                timeout=game_config_data.get("timeout", 10),
                retry_count=game_config_data.get("retry_count", 3),
                retry_delay=game_config_data.get("retry_delay", 1.0)
            )
            
            # Create MQTT configuration
            config = MQTTConfig(
                client_id=f"{game_type.value}_client_{environment.value}",
                brokers=brokers,
                game_config=game_config,
                environment=environment,
                log_level=config_data.get("log_level", "INFO"),
                max_history_size=config_data.get("max_history_size", 100),
                reconnect_delay=config_data.get("reconnect_delay", 5.0),
                max_connection_attempts=config_data.get("max_connection_attempts", 3),
                default_username=config_data.get("default_username", "PFC"),
                default_password=config_data.get("default_password", "wago")
            )
            
            # Validate configuration
            self._validate_config(config)
            
            return config
            
        except Exception as e:
            raise ValueError(f"Invalid configuration format: {e}")

    def _validate_config(self, config: MQTTConfig):
        """Validate configuration"""
        if not config.brokers:
            raise ValueError("At least one broker must be configured")
        
        if not config.game_config.game_code:
            raise ValueError("Game code must be specified")
        
        if not config.game_config.command_topic:
            raise ValueError("Command topic must be specified")
        
        if not config.game_config.response_topic:
            raise ValueError("Response topic must be specified")
        
        # Validate broker configurations
        for broker in config.brokers:
            if not broker.broker:
                raise ValueError("Broker address must be specified")
            if broker.port <= 0 or broker.port > 65535:
                raise ValueError(f"Invalid port number: {broker.port}")

    def get_default_config(self, game_type: Union[str, GameType]) -> MQTTConfig:
        """
        Get default configuration for game type
        
        Args:
            game_type: Game type
            
        Returns:
            MQTTConfig object
        """
        if isinstance(game_type, str):
            game_type = GameType(game_type.lower())
        
        if game_type.value not in self._default_configs:
            raise ValueError(f"No default configuration available for {game_type.value}")
        
        return self._default_configs[game_type.value]

    def create_config_template(
        self,
        game_type: Union[str, GameType],
        environment: Union[str, Environment] = Environment.DEVELOPMENT,
        output_file: Optional[str] = None
    ) -> str:
        """
        Create configuration template file
        
        Args:
            game_type: Game type
            environment: Environment
            output_file: Output file path (optional)
            
        Returns:
            JSON configuration string
        """
        if isinstance(game_type, str):
            game_type = GameType(game_type.lower())
        if isinstance(environment, str):
            environment = Environment(environment.lower())
        
        # Get default configuration
        config = self.get_default_config(game_type)
        
        # Convert to dictionary
        config_dict = {
            "brokers": [asdict(broker) for broker in config.brokers],
            "game_config": asdict(config.game_config),
            "environment": environment.value,
            "log_level": config.log_level,
            "max_history_size": config.max_history_size,
            "reconnect_delay": config.reconnect_delay,
            "max_connection_attempts": config.max_connection_attempts,
            "default_username": config.default_username,
            "default_password": config.default_password
        }
        
        # Convert to JSON
        json_config = json.dumps(config_dict, indent=2, ensure_ascii=False)
        
        # Write to file if specified
        if output_file:
            output_path = Path(output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_config)
            self.logger.info(f"Configuration template written to {output_path}")
        
        return json_config

    def save_config(
        self,
        config: MQTTConfig,
        output_file: Optional[str] = None
    ) -> str:
        """
        Save configuration to file
        
        Args:
            config: MQTTConfig object
            output_file: Output file path (optional)
            
        Returns:
            JSON configuration string
        """
        # Convert to dictionary
        config_dict = {
            "brokers": [asdict(broker) for broker in config.brokers],
            "game_config": asdict(config.game_config),
            "environment": config.environment.value,
            "log_level": config.log_level,
            "max_history_size": config.max_history_size,
            "reconnect_delay": config.reconnect_delay,
            "max_connection_attempts": config.max_connection_attempts,
            "default_username": config.default_username,
            "default_password": config.default_password
        }
        
        # Convert to JSON
        json_config = json.dumps(config_dict, indent=2, ensure_ascii=False)
        
        # Write to file if specified
        if output_file:
            output_path = Path(output_file)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_config)
            self.logger.info(f"Configuration saved to {output_path}")
        
        return json_config

    def list_available_configs(self) -> List[str]:
        """List available configuration files"""
        config_files = []
        for config_file in self.config_dir.glob("*-broker.json"):
            config_files.append(config_file.name)
        return sorted(config_files)

    def get_config_info(self, config: MQTTConfig) -> Dict[str, Any]:
        """Get configuration information summary"""
        return {
            "client_id": config.client_id,
            "game_type": config.game_config.game_type.value,
            "game_code": config.game_config.game_code,
            "environment": config.environment.value,
            "broker_count": len(config.brokers),
            "primary_broker": config.brokers[0].broker if config.brokers else None,
            "command_topic": config.game_config.command_topic,
            "response_topic": config.game_config.response_topic,
            "log_level": config.log_level,
            "timeout": config.game_config.timeout,
            "retry_count": config.game_config.retry_count
        }

    def clear_cache(self):
        """Clear configuration cache"""
        self._config_cache.clear()
        self.logger.info("Configuration cache cleared")

    def reload_config(
        self,
        game_type: Union[str, GameType],
        environment: Union[str, Environment] = Environment.DEVELOPMENT
    ) -> MQTTConfig:
        """
        Reload configuration from file (bypass cache)
        
        Args:
            game_type: Game type
            environment: Environment
            
        Returns:
            MQTTConfig object
        """
        # Clear cache for this configuration
        if isinstance(game_type, str):
            game_type = GameType(game_type.lower())
        if isinstance(environment, str):
            environment = Environment(environment.lower())
        
        cache_key = f"{game_type.value}_{environment.value}"
        if cache_key in self._config_cache:
            del self._config_cache[cache_key]
        
        # Reload configuration
        return self.load_config_from_file(game_type, environment)


# Convenience functions for easy access
def get_config(
    game_type: Union[str, GameType],
    environment: Union[str, Environment] = Environment.DEVELOPMENT,
    config_dir: str = "conf"
) -> MQTTConfig:
    """
    Get MQTT configuration for game type and environment
    
    Args:
        game_type: Game type (sicbo, baccarat, roulette)
        environment: Environment (development, staging, production)
        config_dir: Configuration directory
        
    Returns:
        MQTTConfig object
    """
    manager = MQTTConfigManager(config_dir)
    return manager.load_config_from_file(game_type, environment)


def create_config_template(
    game_type: Union[str, GameType],
    environment: Union[str, Environment] = Environment.DEVELOPMENT,
    config_dir: str = "conf"
) -> str:
    """
    Create configuration template for game type
    
    Args:
        game_type: Game type
        environment: Environment
        config_dir: Configuration directory
        
    Returns:
        JSON configuration string
    """
    manager = MQTTConfigManager(config_dir)
    return manager.create_config_template(game_type, environment)

"""配置加载模块"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional


def load_settings(config_path: Optional[str] = None) -> Dict[str, Any]:
    """加载YAML配置文件

    Args:
        config_path: 配置文件路径，默认使用当前包内的settings.yaml

    Returns:
        配置字典
    """
    if config_path is None:
        # 默认使用当前包内的settings.yaml
        config_path = Path(__file__).parent / "settings.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)

    return settings


def get_quality_filter_config(settings: Dict[str, Any]) -> Dict[str, Any]:
    """提取质量过滤器配置

    Args:
        settings: 完整的配置字典

    Returns:
        质量过滤器配置字典
    """
    return settings.get('quality_filter', {
        'enabled': False,
        'rules': {},
        'ai_analysis': {}
    })

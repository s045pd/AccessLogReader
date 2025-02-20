import os
import sys
from pathlib import Path
from typing import Optional

import click
import streamlit.web.cli as stcli

# 添加父目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from v2log.utils.generator import create_demo_log

# 获取包内data目录
DEFAULT_DB_PATH = Path(__file__).parent / "data" / "IP2LOCATION-LITE-DB11.BIN"


@click.command()
@click.argument("log_file", type=click.Path(exists=True), required=False)
@click.option("--filter", "-f", help='过滤规则，例如: "dst:*.google.com"')
@click.option("--db-path", type=click.Path(), help="IP2Location数据库路径")
@click.option("--demo", is_flag=True, help="使用示例日志文件")
def main(
    log_file: Optional[str],
    filter: Optional[str],
    db_path: Optional[str],
    demo: bool,
):
    """Access Log Reader - 分析访问日志"""
    # 处理 demo 模式
    if demo:
        click.echo("生成示例日志数据...")
        demo_log = create_demo_log()
        log_file = str(demo_log)
    elif not log_file:
        click.echo("错误: 请指定日志文件路径或使用 --demo 参数")
        sys.exit(1)

    # 使用指定的数据库路径或默认路径
    db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    if not db_path.exists():
        click.echo(f"错误: 未找到IP2Location数据库: {db_path}")
        sys.exit(1)

    # 设置环境变量
    os.environ["READER_LOG_FILE"] = str(Path(log_file).absolute())
    os.environ["READER_DB_PATH"] = str(db_path)
    if filter:
        os.environ["READER_FILTER"] = filter

    # 启动Streamlit应用
    import v2log.app

    # 获取 reader.app 模块的路径
    app_path = Path(v2log.app.__file__).absolute()

    # 使用 streamlit cli 启动
    sys.argv = ["streamlit", "run", str(app_path)]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()

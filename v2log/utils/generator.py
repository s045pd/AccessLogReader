import random
from datetime import datetime, timedelta
from pathlib import Path

# 示例域名列表
DOMAINS = [
    "api2.cursor.sh",
    "github.com",
    "google.com",
    "cloudflare.com",
    "amazon.com",
    "microsoft.com",
    "apple.com",
    "netflix.com",
    "facebook.com",
    "twitter.com",
]

# 示例IP地址列表
IPS = [
    "61.130.183.4",
    "52.84.96.123",
    "140.82.112.4",
    "13.107.42.16",
    "104.244.42.129",
    "31.13.92.36",
    "199.232.69.194",
    "151.101.65.69",
]


def generate_log(count: int = 10000, start_time: datetime = None) -> str:
    """生成示例日志数据"""
    if start_time is None:
        start_time = datetime.now()

    logs = []
    current_time = start_time

    for _ in range(count):
        # 随机生成时间（在1小时内）
        seconds = random.randint(0, 3600)
        current_time = start_time + timedelta(seconds=seconds)

        # 随机选择IP和域名
        ip = random.choice(IPS)
        domain = random.choice(DOMAINS)
        port = random.randint(1024, 65535)

        # 生成日志行
        log_line = (
            f"{current_time.strftime('%Y/%m/%d %H:%M:%S')} "
            f"{ip}:{port} accepted tcp:{domain}:443 "
            "[inbound-27018 -> default]"
        )
        logs.append(log_line)

    # 按时间排序
    return "\n".join(sorted(logs))


def create_demo_log(output_path: Path = None) -> Path:
    """创建示例日志文件"""
    if output_path is None:
        output_path = Path.home() / ".accesslogreader" / "demo.log"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 生成日志数据
    log_data = generate_log(
        count=10000,
        start_time=datetime.now() - timedelta(hours=1),
    )

    # 写入文件
    output_path.write_text(log_data)
    return output_path

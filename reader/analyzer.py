import pickle
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import IP2Location
import numpy as np
import pandas as pd


class IPAnalyzer:
    # 定义类级别的常量
    COLUMNS = ["min", "src", "dst", "count", "x", "y", "country", "city"]
    DEFAULT_LOCATION = {
        "x": np.float32(0),
        "y": np.float32(0),
        "country": "Unknown",
        "city": "Unknown",
    }

    def __init__(
        self,
        db_path=Path("IP2LOCATION-LITE-DB11.BIN"),
        cache_dir=Path.home() / ".accesslogreader" / "cache",
        batch_size=100000,
    ):
        self.ip_database = IP2Location.IP2Location(str(db_path))
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size
        self.ip_location_cache = {}
        self.log_pattern = re.compile(
            r"(\d{4}/\d{2}/\d{2} \d{2}:\d{2}):\d{2} ([\d\.]+):\d+ accepted "
            r"tcp:([\w\.-]+):"
        )

    def get_file_lines(self, file_path: Path) -> int:
        """使用系统命令快速获取文件行数"""
        try:
            # 对于Unix/Linux系统
            result = subprocess.run(
                ["wc", "-l", str(file_path)], capture_output=True, text=True
            )
            return int(result.stdout.split()[0])
        except (subprocess.SubprocessError, ValueError, IndexError):
            try:
                # 对于Windows系统
                result = subprocess.run(
                    ["find", "/c", "/v", "", str(file_path)],
                    capture_output=True,
                    text=True,
                    shell=True,
                )
                return int(result.stdout.split()[-1])
            except (subprocess.SubprocessError, ValueError, IndexError):
                # 如果命令行方法都失败了，使用文件大小估算
                return file_path.stat().st_size // 100  # 使用 Path.stat()

    def get_cache_path(self, log_file_path: Path) -> Path:
        """获取缓存文件路径"""
        last_modified = log_file_path.stat().st_mtime
        cache_name = f"{log_file_path.stem}_{int(last_modified)}.pkl"
        return self.cache_dir / cache_name

    def save_cache(self, data, cache_path: Path):
        """保存缓存数据"""
        with cache_path.open("wb") as f:
            pickle.dump(data, f)

    def load_cache(self, cache_path: Path):
        """加载缓存数据"""
        try:
            with cache_path.open("rb") as f:
                return pickle.load(f)
        except Exception:  # 处理所有可能的文件读取错误
            return None

    def get_location(self, ip):
        # 先检查缓存
        if ip in self.ip_location_cache:
            return self.ip_location_cache[ip]

        try:
            rec = self.ip_database.get_all(ip)
            location = {
                "x": np.float32(rec.latitude),
                "y": np.float32(rec.longitude),
                "country": rec.country_long,
                "city": rec.city,
            }
        except Exception:
            location = self.DEFAULT_LOCATION.copy()

        # 保存到缓存
        self.ip_location_cache[ip] = location
        return location

    def parse_log_line(self, line):
        """解析单行日志"""
        match = self.log_pattern.match(line)
        if match:
            minute_str, source_ip, destination = match.groups()
            # 跳过本地回环地址相关的记录
            is_loopback = "127.0.0.1" in (source_ip, destination) or (
                destination.replace(".", "").isdigit()
                and destination == "127.0.0.1"
            )
            if is_loopback:
                return None

            return dict(
                zip(
                    ["min", "src", "dst"],
                    [
                        datetime.strptime(minute_str, "%Y/%m/%d %H:%M"),
                        source_ip,
                        destination,
                    ],
                )
            )
        return None

    def _process_line(self, line, aggregated_data, ip_records):
        """处理单行日志"""
        if not (parsed := self.parse_log_line(line.strip())):
            return 0

        key = (parsed["min"], parsed["src"], parsed["dst"])
        aggregated_data[key] += 1

        # 获取IP地理位置信息
        src_ip = parsed["src"]
        if src_ip not in ip_records:
            ip_records[src_ip] = self.get_location(src_ip)

        return 1

    def _load_cache_data(self, temp_cache_path, cache_path, use_cache):
        """加载缓存数据"""
        # 尝试加载临时缓存
        if temp_cache_path.exists():
            temp_data = self.load_cache(temp_cache_path)
            if temp_data is not None:
                return (
                    temp_data["line_number"],
                    defaultdict(int, temp_data["aggregated"]),
                    temp_data["ip_records"],
                )

        # 如果存在完整缓存且不是强制刷新
        if use_cache and cache_path.exists():
            cached_data = self.load_cache(cache_path)
            if cached_data is not None:
                return 0, defaultdict(int), {}

        return 0, defaultdict(int), {}

    def process_log_file(
        self,
        log_file_path: Path,
        use_cache=True,
        progress_callback=None,
        batch_callback=None,
    ):
        """处理日志文件"""
        log_file_path = Path(log_file_path)
        cache_path = self.get_cache_path(log_file_path)
        temp_cache_path = cache_path.with_suffix(".temp.pkl")

        # 加载缓存
        start_line, aggregated_data, ip_records = self._load_cache_data(
            temp_cache_path, cache_path, use_cache
        )

        # 如果有完整缓存数据，直接返回
        if use_cache and cache_path.exists() and start_line == 0:
            cached_data = self.load_cache(cache_path)
            if cached_data is not None:
                if progress_callback:
                    progress_callback(1.0, "从缓存加载完成")
                if batch_callback:
                    batch_callback(cached_data)
                return cached_data

        total_lines = self.get_file_lines(log_file_path)
        processed_count = 0
        current_line = 0
        update_interval = self.batch_size / 10

        with log_file_path.open("r") as f:
            # 跳过已处理的行
            for _ in range(start_line):
                next(f)
                current_line += 1

            while True:
                try:
                    line = next(f)
                    current_line += 1

                    processed_count += self._process_line(
                        line, aggregated_data, ip_records
                    )

                    if processed_count >= self.batch_size:
                        self._process_batch(
                            aggregated_data,
                            ip_records,
                            batch_callback,
                            temp_cache_path,
                            current_line,
                        )
                        processed_count = 0

                    self._update_progress(
                        progress_callback,
                        current_line,
                        total_lines,
                        update_interval,
                    )

                except StopIteration:
                    break

        # 处理完成
        final_df = self._create_dataframe(aggregated_data, ip_records)
        self.save_cache(final_df, cache_path)

        if temp_cache_path.exists():
            temp_cache_path.unlink()

        if progress_callback:
            progress_callback(1.0, "处理完成")

        return final_df

    def _process_batch(
        self,
        aggregated_data,
        ip_records,
        batch_callback,
        temp_cache_path,
        current_line,
    ):
        """处理批量日志"""
        temp_df = self._create_dataframe(aggregated_data, ip_records)
        if batch_callback:
            batch_callback(temp_df)

        # 保存临时缓存
        temp_cache = {
            "aggregated": dict(aggregated_data),
            "ip_records": ip_records,
            "line_number": current_line,
        }
        self.save_cache(temp_cache, temp_cache_path)

    def _update_progress(
        self, progress_callback, current_line, total_lines, update_interval
    ):
        """更新进度"""
        if progress_callback and current_line % update_interval == 0:
            progress = current_line / total_lines
            progress_callback(
                progress,
                f"处理中... ({current_line}/{total_lines})",
            )

    def _create_dataframe(self, aggregated_data, ip_records):
        """从聚合数据创建DataFrame"""
        if not aggregated_data:
            return pd.DataFrame(columns=self.COLUMNS)

        records = []
        for (minute, ip, dest), count in aggregated_data.items():
            location = ip_records[ip]
            records.append(
                dict(
                    zip(
                        self.COLUMNS,
                        [
                            minute,
                            ip,
                            dest,
                            count,
                            location["x"],
                            location["y"],
                            location["country"],
                            location["city"],
                        ],
                    )
                )
            )

        return pd.DataFrame(records, columns=self.COLUMNS)

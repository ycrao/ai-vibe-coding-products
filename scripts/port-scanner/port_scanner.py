import argparse
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed


COMMON_PORTS = [
    20,
    21,
    22,
    23,
    25,
    53,
    80,
    110,
    143,
    443,
    3306,
    3389,
    8080,
]


def scan_port(host: str, port: int, timeout: float = 2.0) -> bool:
    """
    扫描单个端口，开放返回 True，其他情况返回 False
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((host, port))
            # connect_ex 返回 0 表示连接成功，端口开放
            return result == 0
        except socket.error:
            return False


def scan_ports(
    host: str,
    ports: list[int],
    max_workers: int = 100,
    timeout: float = 1.0,
) -> list[int]:
    open_ports: list[int] = []
    total = len(ports)
    if total == 0:
        return open_ports

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_port = {
            executor.submit(scan_port, host, port, timeout): port for port in ports
        }

        completed = 0
        for future in as_completed(future_to_port):
            port = future_to_port[future]
            try:
                is_open = future.result()
                if is_open:
                    open_ports.append(port)
            except Exception:
                pass
            completed += 1
            bar_len = 40
            filled_len = int(bar_len * completed / total)
            bar = "#" * filled_len + "-" * (bar_len - filled_len)
            percent = completed * 100.0 / total
            print(
                f"\r扫描进度: [{bar}] {completed}/{total} ({percent:5.1f}%)",
                end="",
                flush=True,
            )

    print()
    open_ports.sort()
    return open_ports


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="简单多线程端口扫描器")
    parser.add_argument(
        "-H",
        "--host",
        required=True,
        help="目标主机，例如 127.0.0.1",
    )
    parser.add_argument(
        "-p",
        "--ports",
        required=False,
        help="端口范围，例如 1-1024 或单个端口 80",
    )
    parser.add_argument(
        "--common",
        action="store_true",
        help="只扫描常见端口（如 22, 80, 443 等）",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=100,
        help="最大线程数，默认 100",
    )
    parser.add_argument(
        "-T",
        "--timeout",
        type=float,
        default=1.0,
        help="连接超时时间（秒），默认 1.0",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="将扫描结果写入文件，例如 result.txt",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    ports: list[int] = []

    if args.ports:
        port_range = args.ports.strip()
        if "-" in port_range:
            start_str, end_str = port_range.split("-", 1)
            start_port = int(start_str)
            end_port = int(end_str)
            ports.extend(range(start_port, end_port + 1))
        else:
            ports.append(int(port_range))

    if args.common:
        ports.extend(COMMON_PORTS)

    ports = sorted(set(ports))

    if not ports:
        print("必须指定端口范围(-p) 或使用 --common")
        return

    if any(p < 0 or p > 65535 for p in ports):
        print("端口必须在 0-65535 范围内")
        return

    print(
        f"开始扫描 {args.host}，共 {len(ports)} 个端口，最大线程数 {args.threads}，超时 {args.timeout}s ..."
    )

    open_ports = scan_ports(
        host=args.host,
        ports=ports,
        max_workers=args.threads,
        timeout=args.timeout,
    )

    print("\n扫描完成。")
    if open_ports:
        print("开放端口列表:")
        for p in open_ports:
            print(f"  - {p}")
    else:
        print("未发现开放端口。")

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                if open_ports:
                    for p in open_ports:
                        f.write(f"{p}\n")
                else:
                    f.write("未发现开放端口。\n")
            print(f"结果已写入文件: {args.output}")
        except OSError as e:
            print(f"写入文件失败: {e}")


if __name__ == "__main__":
    main()
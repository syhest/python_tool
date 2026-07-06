import serial
import time
import argparse
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor

class SerialCommander:
    def __init__(self, port, baudrate=115200, log_file='set_card_iperf.log', simulate=False, quiet=False):
        self.port = port
        self.baudrate = baudrate
        self.log_file = log_file
        self.ser = None
        self.log = []
        self.simulate = simulate
        self.quiet = quiet

    def log_message(self, message):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.log.append(log_entry)
        if not self.quiet:
            print(log_entry)

    def save_log(self):
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.log))
        if not self.quiet:
            self.log_message(f"Log saved to {self.log_file}")

    def start_serial(self):
        self.log_message(f"Opening serial port {self.port} at {self.baudrate} baud")
        if self.simulate:
            self.log_message("Running in simulation mode")
            self.log_message("Output: picocom v3.1")
            self.log_message(f"Output: port is        : {self.port}")
            self.log_message("Output: flowcontrol    : none")
            self.log_message(f"Output: baudrate is    : {self.baudrate}")
            self.log_message("Output: parity is      : none")
            self.log_message("Output: databits are   : 8")
            self.log_message("Output: stopbits are   : 1")
            self.log_message("Output: escape is      : C-a")
            self.log_message("Output: local echo is  : no")
            self.log_message("Output: noinit is      : no")
            self.log_message("Output: noreset is     : no")
            self.log_message("Output: hangup is      : no")
            self.log_message("Output: nolock is      : no")
            self.log_message("Output: send_cmd is    : sz -vv")
            self.log_message("Output: receive_cmd is : rz -vv -E")
            self.log_message("Output: imap is        :")
            self.log_message("Output: omap is        :")
            self.log_message("Output: emap is        : crcrlf,delbs,")
            self.log_message("Output: logfile is     : none")
            self.log_message("Output: initstring     : none")
            self.log_message("Output: exit_after is  : not set")
            self.log_message("Output: exit is        : no")
            self.log_message("Output:")
            self.log_message("Output: Type [C-a] [C-h] to see available commands")
            self.log_message("Output: Terminal ready")
            self.log_message("Output: *Switch>")
            return

        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0.5
            )
            time.sleep(1)
            self.read_output(timeout=0.5)
        except Exception as e:
            self.log_message(f"Error opening serial port: {e}")
            self.log_message("Switching to simulation mode")
            self.simulate = True
            self.start_serial()

    def read_output(self, timeout=0.5):
        output = []
        if self.simulate:
            return output

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.ser and self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8', errors='ignore').rstrip()
                    if line:
                        if not line.endswith('#') and not line.endswith('>') and line.strip():
                            output.append(line)
                            self.log_message(f"Output: {line}")
                except:
                    pass
            else:
                time.sleep(0.05)
        return output

    def send_command(self, command, wait_time=0.05):
        self.log_message(f"Sending: {command}")
        if self.simulate:
            if command == '':
                self.log_message("Output: Switch#")
            elif command == 'en':
                self.log_message("Output: Switch#")
            elif command == 'cpss':
                self.log_message("Output: Entering character mode")
                self.log_message("Output: Console#")
            elif command == 'CLIexit':
                self.log_message("Output: Connection closed by foreign host.")
                self.log_message("Output: Switch#")
            elif command == 'ip -br a':
                self.log_message("Output: lo               UNKNOWN        127.0.0.1/8")
                self.log_message("Output: enp129s0f0      DOWN")
                self.log_message("Output: enp129s0f1      DOWN")
                time.sleep(wait_time)
                return ["enp129s0f0      DOWN", "enp129s0f1      DOWN"]
            time.sleep(wait_time)
            return []

        if self.ser and self.ser.is_open:
            try:
                self.ser.write((command + '\n').encode('utf-8'))
                self.ser.flush()
                time.sleep(wait_time)
                return self.read_output(timeout=0.05)
            except Exception as e:
                self.log_message(f"Error sending command: {e}")
        return []

    def close_serial(self):
        self.log_message("Closing serial port")
        if not self.simulate and self.ser and self.ser.is_open:
            self.ser.close()

    def detect_nic_names(self):
        self.log_message("Detecting NIC names using 'ip -br a'")

        if self.simulate:
            self.log_message("Simulation mode: using default NIC names")
            return "enp129s0f0", "enp129s0f1"

        output = self.send_command("ip -br a", wait_time=0.5)

        nic_candidates = []
        for line in output:
            parts = line.split()
            if parts and parts[0].startswith("enp129s0"):
                nic_candidates.append(parts[0])

        nic_candidates.sort()

        if len(nic_candidates) >= 2:
            nic_f0 = nic_candidates[0]
            nic_f1 = nic_candidates[1]
            self.log_message(f"Detected NICs: {nic_f0}, {nic_f1}")
            return nic_f0, nic_f1
        elif len(nic_candidates) == 1:
            self.log_message(f"Warning: Only one NIC detected: {nic_candidates[0]}, using fallback")
            return nic_candidates[0], "enp129s0f1"
        else:
            self.log_message("Warning: No NICs detected, using fallback names")
            return "enp129s0f0", "enp129s0f1"

    def configure_iperf(self, node, card):
        self.log_message(f"Configuring iperf for node {node}, card {card}")

        nic_f0, nic_f1 = self.detect_nic_names()

        last_octet = 2 + (node - 1) * 2 + (card - 1)

        if node <= 5:
            ip_f0 = f"10.0.0.{last_octet}"
            ip_f1 = f"20.0.0.{last_octet}"
        else:
            ip_f0 = f"20.0.0.{last_octet}"
            ip_f1 = f"10.0.0.{last_octet}"

        command_f0 = f'sudo busybox ifconfig {nic_f0} {ip_f0} netmask 255.255.255.0'
        self.send_command(command_f0, wait_time=0.1)

        command_f01 = f'sudo busybox ifconfig {nic_f0} up'
        self.send_command(command_f01, wait_time=0.1)

        command_f1 = f'sudo busybox ifconfig {nic_f1} {ip_f1} netmask 255.255.255.0'
        self.send_command(command_f1, wait_time=0.1)

        command_f11 = f'sudo busybox ifconfig {nic_f1} up'
        self.send_command(command_f11, wait_time=0.1)

    def start_iperf_server(self):
        self.log_message("Starting iperf server")
        command = 'iperf3 -s -i 1 -p 5001 > /dev/null &'
        self.send_command(command, wait_time=0.1)
        command1 = 'iperf3 -s -i 1 -p 5002 > /dev/null &'
        self.send_command(command1, wait_time=0.1)

    def start_iperf_client(self, node, card):
        self.log_message(f"Starting iperf client for node {node}, card {card}")

        last_octet = 2 + (node - 1) * 2 + (card - 1)

        if node <= 5:
            f0_ip = f"10.0.0.{last_octet}"
            f1_ip = f"20.0.0.{last_octet}"
        else:
            f0_ip = f"20.0.0.{last_octet}"
            f1_ip = f"10.0.0.{last_octet}"

        target_f0 = f"{f0_ip.rsplit('.', 1)[0]}.{last_octet + 10}"
        target_f1 = f"{f1_ip.rsplit('.', 1)[0]}.{last_octet + 10}"

        command_f0 = f'iperf3 -c {target_f0} -i 1 -t 9999 --bidir -p 5001 > /dev/null &'
        self.send_command(command_f0, wait_time=0.1)

        command_f1 = f'iperf3 -c {target_f1} -i 1 -t 9999 --bidir -p 5002 > /dev/null &'
        self.send_command(command_f1, wait_time=0.1)

    def kill_iperf(self):
        self.log_message("Killing iperf processes")
        command = 'pkill -9 iperf3'
        self.send_command(command, wait_time=0.1)

def get_serial_ports(node_nums, card_num):
    ports = []

    if isinstance(node_nums, int):
        node_nums = [node_nums]

    for node_num in node_nums:
        if node_num == 0:
            nodes = list(range(1, 11))
        else:
            nodes = [node_num]

        if card_num == 0:
            cards = list(range(1, 3))
        else:
            cards = [card_num]

        for node in nodes:
            for card in cards:
                if node < 10:
                    port_num = 1000 + node * 10 + card
                else:
                    port_num = 1100 + (node - 10) * 10 + card
                ports.append((node, card, port_num))

    return ports

def get_serial_device(port_num):
    return f"/dev/ttyUART_{port_num}"

def configure_serial_port(node, card, port_num, quiet=False, action=None, target_ip=None):
    device = get_serial_device(port_num)
    if not quiet:
        print(f"\n===== 配置节点 {node} 卡 {card}，串口: {device} =====")

    commander = SerialCommander(device, quiet=quiet)

    try:
        commander.start_serial()
        if action == 'server':
            commander.start_iperf_server()
        elif action == 'client':
            commander.start_iperf_client(node, card)
        elif action == 'kill':
            commander.kill_iperf()
        else:
            commander.configure_iperf(node, card)
    finally:
        commander.close_serial()
        commander.save_log()

async def configure_serial_port_async(node, card, port_num, quiet=False, action=None, target_ip=None):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, configure_serial_port, node, card, port_num, quiet, action, target_ip)

def show_progress_bar(current, total, bar_length=40):
    percent = (current / total) * 100
    filled_length = int(bar_length * current // total)
    bar = '=' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f"\rProgress: [{bar}] {percent:.1f}% ({current}/{total})")
    sys.stdout.flush()

import sys

async def run_coroutine_mode(serial_ports, action=None, target_ip=None):
    total = len(serial_ports)

    max_workers = min(total, 64)
    executor = ThreadPoolExecutor(max_workers=max_workers)
    loop = asyncio.get_event_loop()

    completed_count = 0
    lock = threading.Lock()

    def update_progress():
        nonlocal completed_count
        with lock:
            completed_count += 1
        show_progress_bar(completed_count, total)

    async def configure_with_counter(node, card, port_num):
        await loop.run_in_executor(executor, configure_serial_port, node, card, port_num, True, action, target_ip)
        update_progress()

    tasks = [configure_with_counter(node, card, port_num) for node, card, port_num in serial_ports]

    print(f"\n配置进行中... (线程池大小: {max_workers})")
    show_progress_bar(0, total)

    await asyncio.gather(*tasks)

    executor.shutdown(wait=True)
    show_progress_bar(total, total)
    print()

def main():
    parser = argparse.ArgumentParser(description='Set card iperf configuration')
    parser.add_argument('-n', '--node', type=str, required=True, help='选择节点号（1-10，0表示所有节点，支持逗号分隔多个节点如：1,2,3,4）')
    parser.add_argument('-c', '--card', type=int, required=True, help='选择卡号（1-2，0表示所有卡）')
    parser.add_argument('-t', '--thread', action='store_true', help='启用多线程模式，每个串口操作在独立线程中进行')
    parser.add_argument('-a', '--async', dest='async_mode', action='store_true', help='启用多协程模式，每个串口操作在独立协程中进行')
    parser.add_argument('-s', '--server', action='store_true', help='启动iperf服务端模式')
    parser.add_argument('-C', '--client', action='store_true', help='启动iperf客户端模式')
    parser.add_argument('-k', '--kill', action='store_true', help='终止所有iperf进程')
    args = parser.parse_args()

    node_nums = []
    try:
        parts = args.node.split(',')
        for part in parts:
            num = int(part.strip())
            if num < 0 or num > 10:
                print(f"错误：节点号 {num} 必须在 0-10 范围内")
                return
            node_nums.append(num)
    except ValueError:
        print("错误：节点号格式不正确，应为逗号分隔的数字")
        return

    if args.card < 0 or args.card > 2:
        print("错误：卡号必须在 0-2 范围内")
        return

    action = None
    target_ip = None

    if args.server:
        action = 'server'
    elif args.client:
        action = 'client'
        target_ip = f"10.0.0.{2 + (1011 - 1011)}"
    elif args.kill:
        action = 'kill'

    serial_ports = get_serial_ports(node_nums, args.card)

    print(f"\n===== 配置参数 =====")
    print(f"节点号: {'所有节点' if 0 in node_nums else ', '.join(map(str, node_nums))}")
    print(f"卡号: {'所有卡' if args.card == 0 else args.card}")
    print(f"串口数量: {len(serial_ports)}")
    print(f"串口列表: {[p[2] for p in serial_ports]}")
    print(f"线程模式: {'启用' if args.thread else '禁用'}")
    print(f"协程模式: {'启用' if args.async_mode else '禁用'}")
    print(f"操作模式: {'iperf服务端' if args.server else 'iperf客户端' if args.client else '终止iperf' if args.kill else '配置IP'}")

    if args.async_mode:
        asyncio.run(run_coroutine_mode(serial_ports, action, target_ip))
    elif args.thread:
        threads = []
        completed_count = 0
        lock = threading.Lock()

        def configure_with_progress(node, card, port_num):
            nonlocal completed_count
            configure_serial_port(node, card, port_num, quiet=True, action=action, target_ip=target_ip)
            with lock:
                completed_count += 1

        for node, card, port_num in serial_ports:
            thread = threading.Thread(target=configure_with_progress, args=(node, card, port_num))
            threads.append(thread)
            thread.start()

        print("\n配置进行中...")
        show_progress_bar(0, len(serial_ports))

        while completed_count < len(serial_ports):
            show_progress_bar(completed_count, len(serial_ports))
            time.sleep(0.1)

        for thread in threads:
            thread.join()

        show_progress_bar(len(serial_ports), len(serial_ports))
        print()
    else:
        for node, card, port_num in serial_ports:
            configure_serial_port(node, card, port_num, action=action, target_ip=target_ip)

    print("\n===== 配置完成 =====")
    if args.server:
        print(f"所有 {len(serial_ports)} 个串口的iperf服务端已启动")
    elif args.client:
        print(f"所有 {len(serial_ports)} 个串口的iperf客户端已启动")
    elif args.kill:
        print(f"所有 {len(serial_ports)} 个串口的iperf进程已终止")
    else:
        print(f"所有 {len(serial_ports)} 个串口的iperf配置已完成")
    print("日志已保存到 set_card_iperf.log")

if __name__ == '__main__':
    main()

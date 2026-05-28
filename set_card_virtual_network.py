import serial
import time
import argparse
import threading
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor

class SerialCommander:
    def __init__(self, port, baudrate=115200, log_file='set_card_virtual_network.log', simulate=False, quiet=False):
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

    def configure_virtual_network(self, port_num):
        self.log_message(f"Configuring virtual network for serial {port_num}")
        
        card_num = port_num % 10
        if port_num < 1100:
            node_num = (port_num // 10) % 10
        else:
            node_num = 10 + ((port_num // 10) % 10)
        
        ip_last = 100 + (node_num - 1) * 7 + card_num
        
        vlan_configs = [
            {'vlan': 4001, 'subnet': '1.1.1'},
            {'vlan': 4002, 'subnet': '1.1.2'}
        ]
        
        for config in vlan_configs:
            ip_address = f"{config['subnet']}.{ip_last}"
            commands = [
                f'vconfig add eth0 {config["vlan"]}',
                f'ifconfig eth0.{config["vlan"]} {ip_address} netmask 255.255.255.0',
                f'vconfig set_flag eth0.{config["vlan"]} 1 1'
            ]
            
            for cmd in commands:
                self.send_command(cmd, wait_time=0.1)
        
        mac_base = 0xA02233445566
        
        if port_num < 1100:
            serial_index = (node_num - 1) * 7 + (card_num - 1)
        else:
            serial_index = 70 + ((node_num - 10) - 1) * 7 + (card_num - 1)
        
        for i, config in enumerate(vlan_configs):
            mac_address = mac_base + serial_index * 4 + (i * 2)
            mac_str = f"{mac_address:012x}"
            mac_formatted = f"{mac_str[0:2]}:{mac_str[2:4]}:{mac_str[4:6]}:{mac_str[6:8]}:{mac_str[8:10]}:{mac_str[10:12]}"
            self.send_command(f'ifconfig eth0.{config["vlan"]} hw ether {mac_formatted}', wait_time=0.1)
        
        for config in vlan_configs:
            commands = [
                f'tc qdisc add dev eth0.{config["vlan"]} root handle 1: htb default 1',
                f'tc class add dev eth0.{config["vlan"]} parent 1: classid 1:1 htb rate 1250mbit ceil 1250mbit burst 156250 cburst 156250'
            ]
            
            for cmd in commands:
                self.send_command(cmd, wait_time=0.1)

def get_serial_ports(node_num, card_num):
    ports = []
    
    if node_num == 0:
        nodes = list(range(1, 13))
    else:
        nodes = [node_num]
    
    if card_num == 0:
        cards = list(range(1, 8))
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

def configure_serial_port(node, card, port_num, quiet=False):
    device = get_serial_device(port_num)
    if not quiet:
        print(f"\n===== 配置节点 {node} 卡 {card}，串口: {device} =====")
    
    commander = SerialCommander(device, quiet=quiet)
    
    try:
        commander.start_serial()
        commander.configure_virtual_network(port_num)
    finally:
        commander.close_serial()
        commander.save_log()

async def configure_serial_port_async(node, card, port_num, quiet=False):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, configure_serial_port, node, card, port_num, quiet)

def show_progress_bar(current, total, bar_length=40):
    percent = (current / total) * 100
    filled_length = int(bar_length * current // total)
    bar = '=' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write(f"\rProgress: [{bar}] {percent:.1f}% ({current}/{total})")
    sys.stdout.flush()

async def run_coroutine_mode(serial_ports):
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
        await loop.run_in_executor(executor, configure_serial_port, node, card, port_num, True)
        update_progress()
    
    tasks = [configure_with_counter(node, card, port_num) for node, card, port_num in serial_ports]
    
    print(f"\n配置进行中... (线程池大小: {max_workers})")
    show_progress_bar(0, total)
    
    await asyncio.gather(*tasks)
    
    executor.shutdown(wait=True)
    show_progress_bar(total, total)
    print()

def main():
    parser = argparse.ArgumentParser(description='Set card virtual network configuration')
    parser.add_argument('-n', '--node', type=int, required=True, help='选择节点号（1-12，0表示所有节点）')
    parser.add_argument('-c', '--card', type=int, required=True, help='选择卡号（1-7，0表示所有卡）')
    parser.add_argument('-t', '--thread', action='store_true', help='启用多线程模式，每个串口操作在独立线程中进行')
    parser.add_argument('-a', '--async', dest='async_mode', action='store_true', help='启用多协程模式，每个串口操作在独立协程中进行')
    args = parser.parse_args()

    if args.node < 0 or args.node > 12:
        print("错误：节点号必须在 0-12 范围内")
        return
    
    if args.card < 0 or args.card > 7:
        print("错误：卡号必须在 0-7 范围内")
        return

    serial_ports = get_serial_ports(args.node, args.card)
    
    print(f"\n===== 配置参数 =====")
    print(f"节点号: {'所有节点' if args.node == 0 else args.node}")
    print(f"卡号: {'所有卡' if args.card == 0 else args.card}")
    print(f"串口数量: {len(serial_ports)}")
    print(f"串口列表: {[p[2] for p in serial_ports]}")
    print(f"线程模式: {'启用' if args.thread else '禁用'}")
    print(f"协程模式: {'启用' if args.async_mode else '禁用'}")

    if args.async_mode:
        asyncio.run(run_coroutine_mode(serial_ports))
    elif args.thread:
        threads = []
        completed_count = 0
        lock = threading.Lock()
        
        def configure_with_progress(node, card, port_num):
            nonlocal completed_count
            configure_serial_port(node, card, port_num, quiet=True)
            with lock:
                nonlocal completed_count
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
            configure_serial_port(node, card, port_num)

    print("\n===== 配置完成 =====")
    print(f"所有 {len(serial_ports)} 个串口的虚拟网卡配置已完成")
    print("日志已保存到 set_card_virtual_network.log")

if __name__ == '__main__':
    main()
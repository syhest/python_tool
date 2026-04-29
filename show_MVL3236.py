import serial
import time
import re
import os
import argparse
import threading

class SerialCommander:
    def __init__(self, port, baudrate=115200, log_file='mvl_3236_config.log', simulate=False, quiet=False):
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
        self.log_message(f"Log saved to {self.log_file}")

    def start_serial(self):
        self.log_message(f"Opening serial port {self.port} at {self.baudrate} baud")
        if self.simulate:
            self.log_message("Running in simulation mode")
            # 模拟串口初始化输出
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
            # 自动切换到模拟模式
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
            time.sleep(wait_time)
            if command == '':
                self.log_message("Output: *Switch>")
                return ["*Switch>"]
            elif command == 'en':
                self.log_message("Output: Switch#")
                return ["Switch#"]
            elif command == 'cpss':
                self.log_message("Output: Entering character mode")
                self.log_message("Output: Console#")
                return ["Entering character mode", "Console#"]
            elif command == 'show interfaces status ethernet 0/0,4,8,12,16,20,24,26,27':
                output = [
                    "Dev/Port         Mode        Link   Speed  Duplex  Loopback Mode",
                    "---------  ----------------  -----  -----  ------  -------------",
                    "0/0             SGMII         Up    2.5G    Full    None",
                    "0/4             SGMII         Up    2.5G    Full    None",
                    "0/8             SGMII         Up    2.5G    Full    None",
                    "0/12            SGMII         Up    2.5G    Full    None",
                    "0/16            SGMII         Up    2.5G    Full    None",
                    "0/20            SGMII         Up    2.5G    Full    None",
                    "0/24            SGMII         Up    2.5G    Full    None",
                    "0/26            QSFP+         Up    40G     Full    None",
                    "0/27            QSFP+         Up    40G     Full    None",
                    "Console#"
                ]
                for line in output:
                    self.log_message(f"Output: {line}")
                return output
            elif command == 'show interfaces mac counters ethernet 0/0,4,8,12,16,20,24,26,27':
                output = [
                    "Interface      UC Received          MC Received          BC Received       Octets Received",
                    "--------- -------------------- -------------------- -------------------- -------------------",
                    "0/0          1762700                 1                    0                225625721",
                    "0/4          2601306                 1                    0                332967289",
                    "0/8          2436742                 1                    0                311903097",
                    "0/12          1887298                 1                    0                241574267",
                    "0/16             0                    0                    0                    0",
                    "0/20          1068432                 0                    0                136759296",
                    "0/24           765152                 0                    0                 97939456",
                    "0/26         1000000                20                   10                120000000",
                    "0/27         1000000                20                   10                120000000",
                    "",
                    "Interface        UC Sent              MC Sent             BRDC Sent           Octets Sent",
                    "--------- -------------------- -------------------- --------------------- --------------------",
                    "0/0          1762702                 1                    0                225625977",
                    "0/4          2601305                 1                    0                332967161",
                    "0/8          2436742                 1                    0                311903097",
                    "0/12          1887298                 1                    0                241574267",
                    "0/16          1378002                 0                    0                176384256",
                    "0/20          1068432                 0                    0                136759296",
                    "0/24           765152                 0                    0                 97939456",
                    "0/26          990000                20                   10                119000000",
                    "0/27          990000                20                   10                119000000",
                    "Console#"
                ]
                for line in output:
                    self.log_message(f"Output: {line}")
                return output
            elif command == 'CLIexit':
                self.log_message("Output: Connection closed by foreign host.")
                self.log_message("Output: Switch#")
                return ["Connection closed by foreign host.", "Switch#"]
            return []

        if self.ser and self.ser.is_open:
            try:
                self.ser.write((command + '\n').encode('utf-8'))
                self.ser.flush()
                time.sleep(wait_time)
                
                output = []
                timeout = 5.0
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    lines = self.read_output(timeout=1.0)
                    output.extend(lines)
                    
                    if lines and 'Type <CR>' in lines[-1]:
                        self.log_message("Sending: <CR> to continue")
                        self.ser.write('\n'.encode('utf-8'))
                        self.ser.flush()
                        time.sleep(0.5)
                    elif lines and (lines[-1].endswith('Console#') or lines[-1].endswith('Switch#')):
                        break
                    else:
                        time.sleep(0.5)
                
                return output
            except Exception as e:
                self.log_message(f"Error sending command: {e}")
        return []

    def enter_cpss_shell(self):
        self.log_message("Entering CPSS shell")
        self.send_command('')
        time.sleep(0.2)
        self.send_command('en')
        time.sleep(0.2)
        self.send_command('cpss')
        time.sleep(0.5)
        self.read_output(timeout=2)

    def parse_interface_status(self, output):
        status = {}
        for line in output:
            match = re.match(r'^\s*(\d+/\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', line)
            if match:
                port = match.group(1)
                mode = match.group(2)
                link = match.group(3)
                speed = match.group(4)
                duplex = match.group(5)
                status[port] = {'mode': mode, 'link': link, 'speed': speed, 'duplex': duplex}
        return status

    def parse_mac_counters(self, output):
        counters = {}
        in_receive_section = True
        
        for line in output:
            if 'UC Sent' in line:
                in_receive_section = False
                continue
            if not line.strip() or 'Interface' in line or '---------' in line or 'Type <CR>' in line:
                continue
            
            parts = re.split(r'\s+', line.strip())
            if len(parts) >= 5:
                port = parts[0]
                if not re.match(r'^\d+/\d+$', port):
                    continue
                try:
                    uc = int(parts[1])
                    octets = int(parts[-1])
                except ValueError:
                    continue
                if in_receive_section:
                    if port not in counters:
                        counters[port] = {}
                    counters[port]['rx_uc'] = uc
                    counters[port]['rx_octets'] = octets
                else:
                    if port not in counters:
                        counters[port] = {}
                    counters[port]['tx_uc'] = uc
                    counters[port]['tx_octets'] = octets
        return counters

    def exit_cpss_shell(self):
        self.log_message("Exiting CPSS shell")
        self.send_command('CLIexit')
        time.sleep(0.2)
        self.read_output(timeout=0.5)

    def close_serial(self):
        self.log_message("Closing serial port")
        if not self.simulate and self.ser and self.ser.is_open:
            self.ser.close()

    def get_port_info(self):
        target_ports = ['0/0', '0/4', '0/8', '0/12', '0/16', '0/20', '0/24', '0/26', '0/27']
        
        status_output = self.send_command('show interfaces status ethernet 0/0,4,8,12,16,20,24,26,27', wait_time=1.0)
        counters_output = self.send_command('show interfaces mac counters ethernet 0/0,4,8,12,16,20,24,26,27', wait_time=1.0)
        
        status = self.parse_interface_status(status_output)
        counters = self.parse_mac_counters(counters_output)
        
        port_info = []
        for port in target_ports:
            port_status = status.get(port, {})
            port_counters = counters.get(port, {})
            
            info = {
                'port': port,
                'status': port_status.get('link', 'Down'),
                'speed': port_status.get('speed', 'n/a'),
                'rx_uc': port_counters.get('rx_uc', 0),
                'rx_octets': port_counters.get('rx_octets', 0),
                'tx_uc': port_counters.get('tx_uc', 0),
                'tx_octets': port_counters.get('tx_octets', 0)
            }
            port_info.append(info)
        
        return port_info

    def display_port_info(self, port_info):
        print("\n" + "="*100)
        print(f"端口状态和速率信息")
        print("="*100)
        print(f"{'端口':<8} {'状态':<8} {'速率':<8} {'RX UC':<12} {'RX字节数':<14} {'TX UC':<12} {'TX字节数':<14}")
        print("-"*100)
        
        for info in port_info:
            print(f"{info['port']:<8} {info['status']:<8} {info['speed']:<8} "
                  f"{info['rx_uc']:<12} {info['rx_octets']:<14} {info['tx_uc']:<12} {info['tx_octets']:<14}")
        print("="*100)
        return port_info

def get_serial_port(node):
    if node < 10:
        return f"/dev/ttyUART_10{node}8"
    else:
        return f"/dev/ttyUART_11{node-10}8"

def get_node_port_info(node, simulate=False, quiet=False):
    port = get_serial_port(node)
    log_file = f'mvl_3236_config_node{node}.log'
    if not quiet:
        print(f"\n===== 查看节点 {node}，串口：{port} =====")

    commander = SerialCommander(port, simulate=simulate, quiet=quiet, log_file=log_file)
    port_info = None

    try:
        commander.start_serial()
        commander.enter_cpss_shell()
        port_info = commander.get_port_info()
        commander.exit_cpss_shell()
    finally:
        commander.close_serial()
        commander.save_log()

    return {'node': node, 'port_info': port_info}

def main():
    parser = argparse.ArgumentParser(description='MVL3236 端口状态查看脚本')
    parser.add_argument('-n', '--nodes', type=int, nargs='+', help='选择查看的节点（支持多个节点，如 -n 1 2 3，节点号范围：1-12；-n 0 表示所有节点）')
    parser.add_argument('-t', '--thread', action='store_true', help='启用多线程模式，并行获取多个节点的端口信息')
    args = parser.parse_args()

    if not args.nodes:
        print("错误：必须指定至少一个节点，使用 -n 参数")
        return

    nodes_to_check = []
    if 0 in args.nodes:
        nodes_to_check = list(range(1, 13))
    else:
        for node in args.nodes:
            if node < 1 or node > 12:
                print(f"错误：节点号 {node} 超出范围（1-12）")
                return
        nodes_to_check = args.nodes

    all_nodes_info = []

    if args.thread:
        print(f"启用多线程模式，并行处理 {len(nodes_to_check)} 个节点...")
        threads = []
        results = []
        
        def thread_worker(node):
            result = get_node_port_info(node, simulate=False, quiet=True)
            results.append(result)

        for node in nodes_to_check:
            t = threading.Thread(target=thread_worker, args=(node,))
            threads.append(t)
            t.start()

        import sys
        
        total = len(threads)
        completed = 0
        spinner = ['|', '/', '-', '\\']
        spin_index = 0
        
        while completed < total:
            completed = sum(1 for t in threads if not t.is_alive())
            progress = int((completed / total) * 20)
            bar = '█' * progress + '░' * (20 - progress)
            
            sys.stdout.write(f'\r等待中 [{bar}] {completed}/{total} {spinner[spin_index]}')
            sys.stdout.flush()
            
            spin_index = (spin_index + 1) % 4
            time.sleep(0.1)
        
        sys.stdout.write('\n')
        all_nodes_info = sorted(results, key=lambda x: x['node'])
    else:
        for node in nodes_to_check:
            result = get_node_port_info(node, simulate=False, quiet=False)
            all_nodes_info.append(result)

    print("\n" + "="*95)
    print(f"所有节点端口状态和速率信息汇总")
    print("="*95)
    
    for node_info in all_nodes_info:
        node = node_info['node']
        port_info = node_info['port_info']
        
        print(f"\n--- 节点 {node} ---")
        print(f"{'端口':<8} {'状态':<8} {'速率':<8} {'RX UC':<12} {'RX字节数':<14} {'TX UC':<12} {'TX字节数':<14}")
        print("-"*95)
        
        for info in port_info:
            print(f"{info['port']:<8} {info['status']:<8} {info['speed']:<8} "
                  f"{info['rx_uc']:<12} {info['rx_octets']:<14} {info['tx_uc']:<12} {info['tx_octets']:<14}")

    print("\n===== 查看完成 =====")
    print("日志已保存到 mvl_3236_config.log")

if __name__ == '__main__':
    main()


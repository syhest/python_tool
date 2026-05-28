import serial
import time
import re
import os
import argparse

class SerialCommander:
    def __init__(self, port, baudrate=115200, log_file='ctc_7132_config.log', simulate=False):
        self.port = port
        self.baudrate = baudrate
        self.log_file = log_file
        self.ser = None
        self.log = []
        self.simulate = simulate
        self.nexthop_map = {
            '0x1f01': '2147488228',
            '0x1f03': '2147488227'
        }
        # 节点与端口映射
        self.node_ports = {
            1: [12, 13],
            2: [20, 21],
            3: [8, 9],
            4: [24, 25],
            5: [22, 23],
            6: [2, 3],
            7: [14, 15],
            8: [10, 11],
            9: [0, 1],
            10: [26, 27],
            11: [28, 29],
            12: [30, 31]
        }
    
    def log_message(self, message):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        self.log.append(log_entry)
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
            self.log_message("Output: Switch#")
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
            # 模拟输出
            return output
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.ser and self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8', errors='ignore').rstrip()
                    if line:
                        # 过滤掉命令提示符和空行
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
            # 模拟命令响应
            if command == '':
                self.log_message("Output: Switch#")
            elif command == 'ctc-shell':
                self.log_message("Output: CTC_CLI(ctc-sdk)#")
            elif command == 'exit':
                self.log_message("Output: CTC_CLI#")
            elif 'show nexthop brguc port' in command:
                port = command.split(' ')[-1]
                if port in self.nexthop_map:
                    nexthop_id = self.nexthop_map[port]
                    self.log_message(f"Output: Gport:{port} L2Uc Nexthop Id:{nexthop_id}")
            # 不再模拟命令回显，避免重复记录
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
    
    def enter_ctc_shell(self):
        self.log_message("Entering CTC shell")
        # 先发送回车确保在命令提示符
        self.send_command('')
        time.sleep(0.2)
        self.send_command('ctc-shell')
        time.sleep(0.5)
        self.read_output(timeout=0.5)
    
    def exit_ctc_shell(self):
        self.log_message("Exiting CTC shell")
        self.send_command('exit')
        time.sleep(0.2)
        self.send_command('exit')
        time.sleep(0.2)
        self.read_output(timeout=0.5)
    
    def close_serial(self):
        self.log_message("Closing serial port")
        if not self.simulate and self.ser and self.ser.is_open:
            self.ser.close()
    
    def get_nexthop_id(self, port):
        self.log_message(f"Getting Nexthop Id for port {port}")
        if self.simulate:
            # 在模拟模式下直接从映射表中获取
            if port in self.nexthop_map:
                nexthop_id = self.nexthop_map[port]
                self.log_message(f"Found Nexthop Id: {nexthop_id}")
                return nexthop_id
            return None
        
        output = self.send_command(f'show nexthop brguc port {port}', wait_time=0.5)
        for line in output:
            match = re.search(r'Nexthop Id:(\d+)', line)
            if match:
                nexthop_id = match.group(1)
                self.log_message(f"Found Nexthop Id: {nexthop_id}")
                return nexthop_id
        return None
    
    def run_commands(self, nodes=None, in_port=None, out_port=None):
        # Remove linkagg 5-15
        for i in range(5, 16):
            self.send_command(f'linkagg remove linkagg {i}')
        
        # ACL uninstall entries 2-5 (twice)
        for _ in range(2):
            for i in range(2, 6):
                self.send_command(f'acl uninstall entry {i}')
        
        # ACL remove entries 2-5
        for i in range(2, 6):
            self.send_command(f'acl remove entry {i}')
        
        # ACL destroy groups 2-5
        for i in range(2, 6):
            self.send_command(f'acl destroy group {i}')
        
        # Remove and recreate linkagg 2-3
        for i in range(2, 4):
            self.send_command(f'linkagg remove linkagg {i}')
            self.send_command(f'linkagg create linkagg {i}')
        
        # 处理in/out端口参数
        if in_port and out_port:
            self.send_command(f'linkagg 2 add member-port {in_port}')
            self.send_command(f'linkagg 3 add member-port {out_port}')
            
            # MAC enable/disable for in/out ports            
            self.send_command(f'port {in_port} mac enable')
            self.send_command(f'port {out_port} mac enable')
            self.send_command(f'port {in_port} port-en enable')
            self.send_command(f'port {out_port} port-en enable')

            # Disable other ports in the range
            if in_port >= 44 and in_port <= 47:
                for port in range(44, 48):
                    if port != in_port and port != out_port:
                        self.send_command(f'port {port} mac disable')
            
            # Disable 60-63 ports
            if in_port >= 60 and in_port <= 63:
                for port in range(60, 64):
                    if port != in_port and port != out_port:
                        self.send_command(f'port {port} mac disable')
            
            # Port properties for in/out ports
            for port in [in_port, out_port]:
                self.send_command(f'port {port} property lb-hash-lag-profile value 1')
                self.send_command(f'port {port} acl-property priority 0 direction ingress acl-en enable  tcam-lkup-type l2')
        else:
            # 默认配置
            self.send_command('linkagg 2 add member-port 44')
            self.send_command('linkagg 3 add member-port 47')
            
            # MAC disable/enable commands
            self.send_command('port all mac disable')
            enable_ports = [2, 3, 12, 13, 20, 21, 24, 25, 44, 45, 46, 47, 60, 61, 62, 63]
            for port in enable_ports:
                self.send_command(f'port {port} mac enable')
            
            # Port properties for 44-47
            for port in range(44, 48):
                self.send_command(f'port {port} property lb-hash-lag-profile value 1')
                self.send_command(f'port {port} acl-property priority 0 direction ingress acl-en enable  tcam-lkup-type l2')
            
            # Port properties for 60-63
            for port in range(60, 64):
                self.send_command(f'port {port} property lb-hash-lag-profile value 1')
                self.send_command(f'port {port} acl-property priority 0 direction ingress acl-en enable  tcam-lkup-type l2')
        
        # Remove and recreate linkagg 1
        self.send_command('linkagg remove linkagg 1')
        self.send_command('linkagg create linkagg 1 member-num 32')
        
        # 处理节点参数
        selected_ports = []
        if nodes:
            for node in nodes:
                if node in self.node_ports:
                    selected_ports.extend(self.node_ports[node])
            
            # Add member ports to linkagg 1 based on selected nodes
            for port in selected_ports:
                self.send_command(f'linkagg 1 add member-port {port}')
            
            # MAC disable for all ports in node_ports
            # Port acl properties for node_ports
            all_node_ports = []
            for node_ports in self.node_ports.values():
                all_node_ports.extend(node_ports)
            for port in all_node_ports:
                self.send_command(f'port {port} mac disable')
                self.send_command(f'port {port} port-en disable')
                self.send_command(f'port {port} acl-property priority 1 direction ingress acl-en disable')

            # MAC enable for selected ports
            # Port acl properties for selected ports
            for port in selected_ports:
                self.send_command(f'port {port} mac enable')
                self.send_command(f'port {port} port-en enable')
                self.send_command(f'port {port} acl-property priority 1 direction ingress acl-en enable tcam-lkup-type l2')
        else:
            # 默认配置
            # Add member ports to linkagg 1
            member_ports = [2, 3, 12, 13, 20, 21, 24, 25]
            for port in member_ports:
                self.send_command(f'linkagg 1 add member-port {port}')
            
            # Port acl properties for specific ports
            acl_ports = [2, 3, 12, 13, 20, 21, 24, 25]
            for port in acl_ports:
                self.send_command(f'port {port} acl-property priority 1 direction ingress acl-en enable tcam-lkup-type l2')
        
        # Parser and lb-hash commands
        self.send_command('parser lb-hash selector-group-id 1 packet-type l2 macsa')
        self.send_command('parser lb-hash selector-group-id 1 packet-type ipv4 ipsa ipda')
        self.send_command('lb-hash select-offset profile-id 1 linkagg static unicast offset  32')
        self.send_command('lb-hash select-offset profile-id 1 head-lag static non-unicast offset 32')
        
        # ACL group 2
        self.send_command('acl create group 2 priority 0 direction ingress none')
        self.send_command('acl add group 2 entry 2 mac-entry field-mode')
        self.send_command('acl entry 2 add key-field field-port gport 0x1f02')
        
        # Get nexthop id for port 0x1f01
        nexthop_id = self.get_nexthop_id('0x1f01')
        if nexthop_id:
            self.send_command(f'acl entry 2 add action-field redirect {nexthop_id}')
        
        self.send_command('acl install entry 2')
        
        # ACL group 3
        self.send_command('acl create group 3 priority 1 direction ingress none')
        self.send_command('acl add group 3 entry 3 mac-entry field-mode')
        self.send_command('acl entry 3 add key-field field-port gport 0x1f01')
        
        # Get nexthop id for port 0x1f03
        nexthop_id = self.get_nexthop_id('0x1f03')
        if nexthop_id:
            self.send_command(f'acl entry 3 add action-field redirect {nexthop_id}')
        
        self.send_command('acl install entry 3')

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='CTC7132 配置脚本')
    parser.add_argument('-n', '--nodes', type=int, nargs='+', help='选择配置的节点（支持多个节点，如 -n 1 2 3；-n 0 表示所有节点）')
    parser.add_argument('--in', dest='in_port', type=int, help='输入端口')
    parser.add_argument('--of', dest='out_port', type=int, help='输出端口')
    args = parser.parse_args()
    
    # 处理 -n 0 的情况
    nodes_to_configure = None
    if args.nodes:
        if 0 in args.nodes:
            # 配置所有节点 1-12
            nodes_to_configure = list(range(1, 13))
        else:
            # 验证并收集指定的节点
            for node in args.nodes:
                if node < 1 or node > 12:
                    print(f"错误：节点号 {node} 超出范围（1-12）")
                    return
            nodes_to_configure = args.nodes
    
    commander = SerialCommander('/dev/ttyS6')
    
    try:
        commander.start_serial()
        commander.enter_ctc_shell()
        commander.run_commands(nodes=nodes_to_configure, in_port=args.in_port, out_port=args.out_port)
        commander.exit_ctc_shell()
    finally:
        commander.close_serial()
        commander.save_log()

if __name__ == '__main__':
    main()

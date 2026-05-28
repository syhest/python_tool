import serial
import time
import re
import os
import argparse

class SerialCommander:
    def __init__(self, port, baudrate=115200, log_file='ctc_7132_config_fowarding_gateway.log', simulate=False):
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
    
    def run_commands(self):
        # 创建下行口vlan
        self.send_command('linkagg create linkagg 5 failover')
        self.send_command('linkagg 5 add member-port 12')
        self.send_command('linkagg 5 add member-port 13')
        
        self.send_command('linkagg create linkagg 6 failover')
        self.send_command('linkagg 6 add member-port 20')
        self.send_command('linkagg 6 add member-port 21')
        
        self.send_command('linkagg create linkagg 7 failover')
        self.send_command('linkagg 7 add member-port 8')
        self.send_command('linkagg 7 add member-port 9')
        
        self.send_command('linkagg create linkagg 8 failover')
        self.send_command('linkagg 8 add member-port 24')
        self.send_command('linkagg 8 add member-port 25')
        
        self.send_command('linkagg create linkagg 9 failover')
        self.send_command('linkagg 9 add member-port 22')
        self.send_command('linkagg 9 add member-port 23')
        
        self.send_command('linkagg create linkagg 10 failover')
        self.send_command('linkagg 10 add member-port 2')
        self.send_command('linkagg 10 add member-port 3')
        
        self.send_command('linkagg create linkagg 11 failover')
        self.send_command('linkagg 11 add member-port 14')
        self.send_command('linkagg 11 add member-port 15')
        
        self.send_command('linkagg create linkagg 12 failover')
        self.send_command('linkagg 12 add member-port 10')
        self.send_command('linkagg 12 add member-port 11')
        
        self.send_command('linkagg create linkagg 13 failover')
        self.send_command('linkagg 13 add member-port 0')
        self.send_command('linkagg 13 add member-port 1')
        
        self.send_command('linkagg create linkagg 14 failover')
        self.send_command('linkagg 14 add member-port 26')
        self.send_command('linkagg 14 add member-port 27')
        
        self.send_command('linkagg create linkagg 15 failover')
        self.send_command('linkagg 15 add member-port 28')
        self.send_command('linkagg 15 add member-port 29')
        
        self.send_command('linkagg create linkagg 16 failover')
        self.send_command('linkagg 16 add member-port 30')
        self.send_command('linkagg 16 add member-port 31')
        
        self.send_command('parser lb-hash selector-group-id 1 packet-type ipv4 ipsa ipda')
        
        # 创建vlan
        self.send_command('vlan remove vlan 4001')
        self.send_command('vlan remove vlan 4002')
        
        self.send_command('vlan create vlan 4001 default-entry')
        self.send_command('vlan create vlan 4002 default-entry')
        
        # 面板口加入vlan成员口
        self.send_command('vlan add port 0x2c vlan 4001')
        self.send_command('vlan add port 0x3c vlan 4002')
        
        # 面板口pvid配置
        self.send_command('port 44 default vlan 4001')
        self.send_command('port 60 default vlan 4002')
        
        # 面板口untagged配置
        self.send_command('port 44 vlan-ctl drop-all-tagged')
        self.send_command('port 44 vlan-filtering direction both enable')
        
        self.send_command('port 60 vlan-ctl drop-all-tagged')
        self.send_command('port 60 vlan-filtering direction both enable')
        
        self.send_command('vlan 4001 port 0x2c untagged')
        self.send_command('vlan 4002 port 0x3c untagged')
        
        # port 0 - 15, 20 - 31 配置
        ports_to_configure = list(range(16)) + list(range(20, 32))
        for port in ports_to_configure:
            # port X 加入vlan成员口
            self.send_command(f'vlan add port {port} vlan 4001')
            self.send_command(f'vlan add port {port} vlan 4002')
            
            # port X tagged配置
            self.send_command(f'port {port} vlan-ctl allow-all')
            self.send_command(f'port {port} vlan-filtering direction both enable')

def main():
    commander = SerialCommander('/dev/ttyS6')
    
    try:
        commander.start_serial()
        commander.enter_ctc_shell()
        commander.run_commands()
        commander.exit_ctc_shell()
    finally:
        commander.close_serial()
        commander.save_log()

if __name__ == '__main__':
    main()

import socket, sys, logging, threading, time, string, os, random, _thread, pickle

class Packet:
    def __init__(self, data = None, checksum = None, sequence_number = None, last_pkt = None):
        self.data = data
        self.checksum = checksum
        self.sequence_number = sequence_number
        self.last_pkt = last_pkt
        self.serialized_form = None
        
    def getSerializedPacket(self):
        if(not self.serialized_form):
            self.serialized_form = pickle.dumps({'sequence_number': self.sequence_number, 'checksum': self.checksum, 'data': self.data, 'last_pkt': self.last_pkt})
        return self.serialized_form

    def deserializePacket(self, packet):
        deserialized_form = pickle.loads(packet)
        self.data = deserialized_form['data']
        self.checksum = deserialized_form['checksum']
        self.sequence_number = deserialized_form['sequence_number']
        self.last_pkt = deserialized_form['last_pkt']

class Checksum:
    def __init__(self):
        pass

    @staticmethod
    def compute(data):
        chk_sum = 0
        for i in range(0, len(data), 2):
            if (i+1) < len(data):
                pos_1 = ord(data[i])
                pos_2 = ord(data[i+1])
                chk_sum = chk_sum + (pos_1+(pos_2 << 8))
            elif (i+1)==len(data):
                chk_sum += ord(data[i])
            else:
                raise "Error at CS compute"
        chk_sum = chk_sum + (chk_sum >> 16)
        chk_sum = ~chk_sum & 0xffff
        return chk_sum

    @classmethod
    def verify(cls, data, chk):
        if(cls.compute(data) == chk):
            return True
        else:
            return False


class Randomize_utility:
    @staticmethod
    def randomString(stringLength=255):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(stringLength))

class GBN:
    def __init__(self, window_size, sequence_bits, segment_size, timeout_period, num_of_packets, port_num):
        self.window_size = window_size
        self.sequence_bits = sequence_bits
        self.sequence_max = 2 ** self.sequence_bits
        self.send_base = 1
        self.segment_size = segment_size
        self.timeout_period = timeout_period
        self.num_of_packets = num_of_packets + 1 
        self.inorder_ack = 1
        self.timer = False
        self.udp_helper = UDP(port_num)
        self.terminated = False
        self.once = True
        self.queue = [None]
        self.mutex = _thread.allocate_lock() 
        self.main_mutex = _thread.allocate_lock() 
        self.checksum_count = int(num_of_packets*0.1)
        self.lost_ack_count = int(0.05*num_of_packets)
        self.check_packets = [ random.randint(1,num_of_packets) for i in range(self.checksum_count)]
        self.lost_ack_packets = [ random.randint(1,num_of_packets) for i in range(self.lost_ack_count)]
        print("Total Packets ----> ", self.check_packets)
        print("Ack Packets Lost ---->", self.lost_ack_packets)
        for i in range(1, self.num_of_packets+1):
            self.queue.append({'num': i, 'data': None, 'status': 'not_sent', 'timer': None})

    def get_next_sequence_number(self, curr_seq):
        return curr_seq
        curr_seq%=self.sequence_max
        if(curr_seq == 0): curr_seq = self.sequence_max
        return curr_seq
    
    def slide_window(self,):
        self.mutex.acquire()
        for i in range(self.send_base, min(self.send_base + self.window_size + 1, self.num_of_packets)):
            if(self.queue[i]['status'] == 'acked'):
                self.send_base+=1
            else:
                break

        self.mutex.release()
    
    def timeout_check(self, sequence_number):
        if(self.queue[sequence_number]['status'] is not 'acked'):
            self.queue[sequence_number]['status'] = 'timeout'
            print("Resending Timedout Packet: ", self.get_next_sequence_number(sequence_number))
        self.process_queue()

    def update_queue_ack(self, ack_rec):

        for index, item in enumerate(self.queue):
            if index == 0: continue
            if index == ack_rec: return
            item['status'] = "acked"
    
    def process_queue(self):
        self.mutex.acquire()
        sb_status = self.queue[self.send_base]['status'] 
        if(sb_status == "not_sent" or sb_status == "timeout"):
            for i in range(self.send_base, min(self.send_base + self.window_size + 1, self.num_of_packets)):
                self.queue[i]['status'] = 'sent'
                self.queue[i]['timer'] = threading.Timer(0.1, self.timeout_check, [i])
                self.queue[i]['timer'].start()
                self.send_packet(i)
        self.mutex.release()
        
    def next(self, ack = None, timer = None):
        self.main_mutex.acquire()
        inorder_ack = self.inorder_ack

        if(ack):
            if(ack in self.lost_ack_packets):
                self.main_mutex.release()
                self.lost_ack_packets.pop(self.lost_ack_packets.index(ack))
                print("Simulating ack loss for ack no: ", ack)
                return
                
            if(ack > inorder_ack):
                print("Received ACK: ", self.get_next_sequence_number(ack))
                self.inorder_ack = ack
                self.update_queue_ack(ack)
                self.slide_window()
                self.send_base = ack
                self.process_queue()
            
            if(ack >= self.num_of_packets+1):
                self.done()

        else:
            self.process_queue()
        
        self.main_mutex.release()
    
    def start(self):
        self.next()

    def done(self):
        if(not self.terminated):
            print("Done transmitting packets !")
            self.terminated = True
            exit()

    def send_packet(self, sequence_number):
        print("Sending ", self.get_next_sequence_number(sequence_number), "; Timer started")
        if(not self.queue[sequence_number]['data']): self.queue[sequence_number]['data'] = Randomize_utility.randomString(self.segment_size)
        checksum = Checksum.compute(self.queue[sequence_number]['data'])
        if(sequence_number in self.check_packets):
            checksum = "myrandomchecksum"
            self.check_packets.pop(self.check_packets.index(sequence_number))
            print("Simulating wrong checksum for packet: ", sequence_number)
        packet = Packet(self.queue[sequence_number]['data'], checksum, sequence_number, False)
        self.udp_helper.send(packet.getSerializedPacket(), self)


class SR:
    def __init__(self, window_size, sequence_bits, segment_size, timeout_period, num_of_packets, port_num):
        self.window_size = window_size
        self.sequence_bits = sequence_bits
        self.sequence_max = 2 ** self.sequence_bits
        self.send_base = 1
        self.segment_size = segment_size
        self.timeout_period = timeout_period
        self.num_of_packets = num_of_packets + 1
        self.inorder_ack = 1
        self.timer = False
        self.udp_helper = UDP(port_num)
        self.terminated = False
        self.once = True
        self.queue = [None]
        self.mutex = _thread.allocate_lock() 
        self.main_mutex = _thread.allocate_lock()
        self.checksum_count = int(num_of_packets*0.1)
        self.lost_ack_count = int(0.05*num_of_packets)
        self.check_packets = [ random.randint(1,num_of_packets) for i in range(self.checksum_count)]
        self.lost_ack_packets = [ random.randint(1,num_of_packets) for i in range(self.lost_ack_count)]
        print("Total Packets ----> ", self.check_packets)
        print("Ack Packets Lost ---->", self.lost_ack_packets)
        for i in range(1, self.num_of_packets+1):
            self.queue.append({'num': i, 'data': None, 'status': 'not_sent', 'timer': None})

    def get_next_sequence_number(self, curr_seq):
        return curr_seq
        curr_seq%=self.sequence_max
        if(curr_seq == 0): curr_seq = self.sequence_max
        return curr_seq
    
    def slide_window(self,):
        self.mutex.acquire()
        for i in range(self.send_base, min(self.send_base + self.window_size + 1, self.num_of_packets)):
            if(self.queue[i]['status'] == 'acked'):
                self.send_base+=1
            else:
                break

        self.mutex.release()
    
    def timeout_check(self, sequence_number):
        self.mutex.acquire()
        if(self.queue[sequence_number]['status'] is not 'acked'):
            self.queue[sequence_number]['status'] = 'timeout'
            print("Resending Timedout Packet: ", self.get_next_sequence_number(sequence_number))
        self.mutex.release()
        self.process_queue()

    def update_queue_ack(self, ack_rec):
        self.mutex.acquire()
        self.queue[ack_rec]['status'] = "acked"
        self.mutex.release()
    
    def process_queue(self):
        self.mutex.acquire()
        for i in range(self.send_base, min(self.send_base + self.window_size + 1, self.num_of_packets)):
            status = self.queue[i]['status']
            if(status == "not_sent" or status=="timeout"):
                self.queue[i]['status'] = 'sent'
                self.queue[i]['timer'] = threading.Timer(0.5, self.timeout_check, [i])
                self.queue[i]['timer'].start()
                self.send_packet(i)
        self.mutex.release()
        
    def next(self, ack = None, timer = None):
        self.main_mutex.acquire()
        inorder_ack = self.inorder_ack
        if(inorder_ack >= self.num_of_packets+1):
            self.done()

        if(ack):
            if(ack in self.lost_ack_packets):
                self.main_mutex.release()
                self.lost_ack_packets.pop(self.lost_ack_packets.index(ack))
                print("Simulating ack loss for ack no: ", ack)
                return

            condition = ack in range(self.send_base, min(self.send_base + self.window_size + 1, self.num_of_packets))
            if(condition):
                print("Received ACK: ", self.get_next_sequence_number(ack))
                self.inorder_ack = ack
                self.update_queue_ack(ack)
                self.slide_window()
                self.process_queue()

        elif(inorder_ack > self.num_of_packets):
            self.done()
        
        else:
            self.process_queue()
        
        self.main_mutex.release()
    
    def start(self):
        self.next()

    def done(self):
        if(not self.terminated):
            print("Packets Transmitted\n")
            self.terminated = True
            exit()

    def send_packet(self, sequence_number):
        print("Sent Packet #-> ", self.get_next_sequence_number(sequence_number))
        if(not self.queue[sequence_number]['data']): self.queue[sequence_number]['data'] = Randomize_utility.randomString(self.segment_size)
        checksum = Checksum.compute(self.queue[sequence_number]['data'])
        if(sequence_number in self.check_packets):
            checksum = "myrandomchecksum"
            self.check_packets.pop(self.check_packets.index(sequence_number))
            print("Simulating wrong checksum for packet: ", sequence_number)
        packet = Packet(self.queue[sequence_number]['data'], checksum, sequence_number, False)
        self.udp_helper.send(packet.getSerializedPacket(), self)

class UDP:
    def __init__(self, port_num):
        self.ip_addr = '127.0.0.1'
        self.port_num = port_num
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiver_running = False
        self.receiver = None
        self.parent = None
    
    def send(self, content, parent):
        self.parent = parent
        self.client_socket.sendto(content, (self.ip_addr, self.port_num))
        if(not self.receiver_running):
            pass
        self.start_receiver()
        return
    
    def receive(self):
        while True:
            try:
                ack_rec,_ = self.client_socket.recvfrom(1024)
                if(ack_rec):
                    ack_rec = int(ack_rec.decode("utf-8"))
                    self.parent.next(ack_rec)
                    break
            except ConnectionResetError:
                print("ConnectionResetError")
                os._exit(0)
        return
    
    def start_receiver(self):
        self.receiver_running = True
        self.receiver = threading.Thread(target=self.receive, args=())
        self.receiver.start()
        return
    
    def waitToReceive(self):
        self.receiver.join()
        return

if __name__ == "__main__":
    if(len(sys.argv) is not 4):
        print("*"*20)
        print("Invalid Input! \n\n Mysender inputfile portNum 1000")
        print("*"*20)
    else:
        try:
            file = open(sys.argv[1]).readlines()

            protocol = file[0].strip()
            sequence_bits = int(file[1].strip().split(' ')[0])
            window_size = int(file[1].strip().split(' ')[1])
            
            timeout_period = float(file[2].strip())
            segment_size = int(file[3].strip())
            port_num = int(sys.argv[2])

            if(protocol == "GBN"):
                gbn = GBN(window_size, sequence_bits, segment_size, timeout_period, int(sys.argv[3]), port_num)
                gbn.start()
            elif(protocol == "SR"):
                sr = SR(window_size, sequence_bits, segment_size, timeout_period, int(sys.argv[3]), port_num)
                sr.start()
        
        except ConnectionResetError:
            print("ConnectionResetError")
            os._exit(0)

        except Exception :
            raise Exception
        

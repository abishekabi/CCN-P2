import socket, sys, logging, threading, time, string, os, random, _thread, pickle


logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")


class Packet:
    def __init__(self, data = None, checksum = None, sequence_number = None, last_pkt = None):
        self.data = data
        self.checksum = checksum
        self.sequence_number = sequence_number
        self.last_pkt = last_pkt
        self.serialized_form = None
    
    def deserialize_packet(self, packet):
        deserialized_form = pickle.loads(packet)
        self.data = deserialized_form['data']
        self.checksum = deserialized_form['checksum']
        self.sequence_number = deserialized_form['sequence_number']
        self.last_pkt = deserialized_form['last_pkt']


    def serialize_pkt(self):
        if(not self.serialized_form):
            self.serialized_form = pickle.dumps({'sequence_number': self.sequence_number, 'checksum': self.checksum, 'data': self.data, 'last_pkt': self.last_pkt})
        return self.serialized_form



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


class GBN:
    def __init__(self, window_size, sequence_bits):
        self.expected_sequence_numberber = 1
        self.once = True
    def receive_packet(self, packet):
        if(packet.sequence_number == 4 and self.once):
            self.once = False
            return self.expected_sequence_numberber, True
        if(packet.sequence_number == self.expected_sequence_numberber):
            self.expected_sequence_numberber+=1
            return self.expected_sequence_numberber, False
        else:
            return self.expected_sequence_numberber, True 



class SR:
    def __init__(self, window_size, sequence_bits):
        self.window_size = window_size
        self.sequence_bits = sequence_bits
        self.r_base = 1
        self.sequence_max = 2 ** self.sequence_bits
        self.queue = {}
        self.next_sequence_number = 1
        self.mutex = _thread.allocate_lock()


    def slide_window(self):
        for key in self.queue:
            if(self.queue[key] == 'rcvd'):
                del self.queue[key]
                self.add_one_to_queue()
            else:
                return

    def is_packet_inorder(self, sequence_number):
        if sequence_number in self.queue: return True
        elif sequence_number < self.next_sequence_number: return True
        else: return False

    def add_one_to_queue(self):
        self.queue[self.next_sequence_number] = 'waiting'
        self.next_sequence_number+=1


    def receive_packet(self, packet):
        self.mutex.acquire()
        if(self.is_packet_inorder(packet.sequence_number)):
            self.queue[packet.sequence_number] = 'rcvd'
            self.slide_window()
            self.mutex.release()
            return packet.sequence_number, False
        else:
            self.mutex.release()
            return packet.sequence_number, True

    def init_queue(self):
        for i in range(self.r_base, self.window_size + 1):
            self.add_one_to_queue()




class UDP:
    def __init__(self, protocol_name, window_size, sequence_bits, port_number):
        self.ip_address = '127.0.0.1'
        self.port_number = port_number
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.ip_address, self.port_number))
        self.receiver_running = False
        self.receiver = None
        self.protocol = None
        self.packets = 0
        self.selectedPacket = 5
        if(protocol_name == "GBN"):
            self.protocol = GBN(window_size, sequence_bits)
        elif(protocol_name == "SR"):
            self.protocol = SR(window_size, sequence_bits)
            self.protocol.init_queue()
        else:
            raise Exception('Invalid protocol!')
    
    def simulatePacketLoss(self):
        self.packets+= 1
        if(self.packets == 10):
            self.packets = 0
            self.selectedPacket = random.randint(0, 10)
        if(self.selectedPacket == self.packets):
            self.selectedPacket = None
            return True
        return False

    def wait_to_receive(self):
        self.receiver.join()
        return


    def send(self, content):
        return
    
    
    def start_listen(self):
        while True:
            try:
                data, addr = self.server_socket.recvfrom(1024)
                packet = Packet()
                packet.deserialize_packet(data)

                if(self.simulatePacketLoss()):
                    print("Simulating packet loss for packet with seq #: ", packet.sequence_number)
                    continue

                if(Checksum.verify(packet.data, packet.checksum)):
                    ack_num, discard = self.protocol.receive_packet(packet)
                    if(discard):
                        print("Discarding packet with sequence # " + str(packet.sequence_number))
                    else:
                        print("Received Segment # ", str(packet.sequence_number))
                    _ = self.server_socket.sendto(str(ack_num).encode(), addr) 
                    print("ACK Sent: ", str(ack_num))
                else:
                    print("Discarding packet with invalid checksum, packet #: ", packet.sequence_number)

            except KeyboardInterrupt:
                print ('Interrupted')
                os._exit(0)
            except ConnectionResetError:
                pass
            except Exception:
                raise Exception
        return
    
    

if __name__ == "__main__":
    if(len(sys.argv) is not 3):
        print("*"*20)
        print("Invalid Input! \n\n Mysender inputfile portNum")
        print("*"*20)
    else:
        try:
            port_number = int(sys.argv[2])
            file = open(sys.argv[1]).readlines()
            protocol = file[0].strip()
            sequence_bits = int(file[1].strip().split(' ')[0])
            window_size = int(file[1].strip().split(' ')[1])
            timeout_period = float(file[2].strip())
            segment_size = int(file[3].strip())

            if(protocol == "GBN"):
                udp_helper = UDP('GBN', window_size, sequence_bits, port_number)
            elif(protocol == "SR"):
                udp_helper = UDP('SR', window_size, sequence_bits, port_number)
            
            udp_helper.start_listen()
            
        except Exception :
            raise Exception


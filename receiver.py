import socket
import sys
import os
import logging
import threading
import random
import time
import _thread
from checksum import Checksum
from packet import Packet

logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")

UDP_IP_ADDRESS = "127.0.0.1"
UDP_PORT_NO = 6789

class GBN:
    def __init__(self, window_size, sequence_bits):
        self.expected_seq_number = 1
        self.once = True
    def receive_packet(self, packet):
        if(packet.seq_num == 4 and self.once):
            self.once = False
            return self.expected_seq_number, True
        if(packet.seq_num == self.expected_seq_number):
            self.expected_seq_number+=1
            return self.expected_seq_number, False
        else:
            return self.expected_seq_number, True # to discard because the packet is either out of order or duplicate

class SR:
    def __init__(self, window_size, sequence_bits):
        self.window_size = window_size
        self.sequence_bits = sequence_bits
        self.r_base = 1
        self.sequence_max = 2 ** self.sequence_bits
        self.queue = {}
        self.next_seq_num = 1
        self.mutex = _thread.allocate_lock() # slide window mutex

    def is_packet_inorder(self, seq_num):
        if seq_num in self.queue: return True
        elif seq_num < self.next_seq_num: return True
        else: return False

    def add_one_to_queue(self):
        self.queue[self.next_seq_num] = 'waiting'
        self.next_seq_num+=1

    def slide_window(self):
        for key in self.queue:
            if(self.queue[key] == 'rcvd'):
                del self.queue[key]
                self.add_one_to_queue()
            else:
                return

    def init_queue(self):
        for i in range(self.r_base, self.window_size + 1):
            self.add_one_to_queue()

    def receive_packet(self, packet):
        self.mutex.acquire()
        if(self.is_packet_inorder(packet.seq_num)):
            self.queue[packet.seq_num] = 'rcvd'
            self.slide_window()
            self.mutex.release()
            return packet.seq_num, False
        else:
            self.mutex.release()
            return packet.seq_num, True # to discard because the packet is out of order

class UDPHelper:
    def __init__(self, protocol_name, window_size, sequence_bits):
        self.ip_address = '127.0.0.1'
        self.port_number = 6789
        self.serverSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.serverSock.bind((UDP_IP_ADDRESS, UDP_PORT_NO))
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
            raise Exception('Invalid protocol name.')
    
    def send(self, content):
        # self.clientSock.sendto(content, (self.ip_address, self.port_number))
        # if(not self.receiver_running):
        #     self.startReceiver()
        return
    
    def simulatePacketLoss(self):
        self.packets+= 1
        if(self.packets == 10):
            self.packets = 0
            self.selectedPacket = random.randint(0, 10)
        if(self.selectedPacket == self.packets):
            self.selectedPacket = None
            return True
        return False
    
    def startListening(self):
        while True:
            try:
                data, addr = self.serverSock.recvfrom(1024)
                packet = Packet()
                packet.deserializePacket(data)
                # print('addr: ', addr)

                if(self.simulatePacketLoss()):
                    print("Simulating packet loss for packet with seq no: ", packet.seq_num)
                    continue

                if(Checksum.verify(packet.data, packet.checksum)):
                    ack_num, discard = self.protocol.receive_packet(packet)
                    if(discard):
                        print("Discarding packet with sequence number " + str(packet.seq_num))
                    else:
                        print("Received Segment: ", str(packet.seq_num))
                    _ = self.serverSock.sendto(str(ack_num).encode(), addr) #sending ack with ack_num
                    print("ACK Sent: ", str(ack_num))
                else:
                    print("Discarding packet with invalid checksum, packet no: ", packet.seq_num)

            except KeyboardInterrupt:
                print ('Interrupted')
                os._exit(0)
            except ConnectionResetError:
                pass # Do nothing.
            except Exception:
                raise Exception
        return
    
    def waitToReceive(self):
        self.receiver.join()
        return




if __name__ == "__main__":
    if(len(sys.argv) is not 3):
        print("Invalid number of arguments.")
        print("Syntax: ")
        print("Mysender inputfile portNum")
    else:
        try:
            UDP_PORT_NO = int(sys.argv[2])
            file = open(sys.argv[1]).readlines()
            protocol = file[0].strip()
            sequence_bits = int(file[1].strip().split(' ')[0])
            window_size = int(file[1].strip().split(' ')[1])
            timeout_period = float(file[2].strip())
            segment_size = int(file[3].strip())

            if(protocol == "GBN"):
                udp_helper = UDPHelper('GBN', window_size, sequence_bits)
            elif(protocol == "SR"):
                udp_helper = UDPHelper('SR', window_size, sequence_bits)
            
            udp_helper.startListening()
            
        except Exception :
            raise Exception
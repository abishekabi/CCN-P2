import socket
import sys
import logging
import threading
import time
import string
import os
import random
import _thread
from checksum import Checksum
from packet import Packet

class Util:
    @staticmethod
    def randomString(stringLength=255):
        letters = string.ascii_lowercase
        return ''.join(random.choice(letters) for i in range(stringLength))

class GBN:
    def __init__(self, window_size, sequence_bits, segment_size, timeout_period, num_of_packets, port_no):
        self.window_size = window_size
        self.sequence_bits = sequence_bits
        self.sequence_max = 2 ** self.sequence_bits
        self.send_base = 1
        self.segment_size = segment_size
        self.timeout_period = timeout_period
        self.num_of_packets = num_of_packets + 1 # number_of_segments
        self.inorder_ack = 1
        self.timer = False
        self.udp_helper = UDPHelper(port_no)
        self.terminated = False
        self.once = True
        self.queue = [None]
        self.mutex = _thread.allocate_lock() # slide window mutex
        self.main_mutex = _thread.allocate_lock() # slide window mutex
        self.checksumECount = int(num_of_packets*0.1)
        self.lostAckECount = int(0.05*num_of_packets)
        self.checkEPackets = [ random.randint(1,num_of_packets) for i in range(self.checksumECount)]
        self.lostAckEPackets = [ random.randint(1,num_of_packets) for i in range(self.lostAckECount)]
        print("checkEPackts: ", self.checkEPackets)
        print("lostAckEPackets: ", self.lostAckEPackets)
        for i in range(1, self.num_of_packets+1):
            self.queue.append({'num': i, 'data': None, 'status': 'not_sent', 'timer': None})

    def get_next_seq_num(self, curr_seq):
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
    
    def timeout_check(self, seq_num):
        if(self.queue[seq_num]['status'] is not 'acked'):
            self.queue[seq_num]['status'] = 'timeout'
            print("Timedout segment: ", self.get_next_seq_num(seq_num), ", Resending")
        self.process_queue()

    def update_queue_ack(self, ack_rec):

        for index, item in enumerate(self.queue):
            if index == 0: continue
            if index == ack_rec: return
            item['status'] = "acked"
    
    def process_queue(self):
        self.mutex.acquire()
        sb_status = self.queue[self.send_base]['status'] #sendbase status
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
            if(ack in self.lostAckEPackets):
                self.main_mutex.release()
                self.lostAckEPackets.pop(self.lostAckEPackets.index(ack))
                print("Simulating ack loss for ack no: ", ack)
                return
                
            if(ack > inorder_ack):
                print("Received ACK: ", self.get_next_seq_num(ack))
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
            print("Done transmitting packets. Terminating.")
            self.terminated = True
            exit()

    def send_packet(self, seq_num):
        print("Sending ", self.get_next_seq_num(seq_num), "; Timer started")
        if(not self.queue[seq_num]['data']): self.queue[seq_num]['data'] = Util.randomString(self.segment_size)
        checksum = Checksum.compute(self.queue[seq_num]['data'])
        if(seq_num in self.checkEPackets):
            checksum = "avalakipavalaki"
            self.checkEPackets.pop(self.checkEPackets.index(seq_num))
            print("Simulating wrong checksum for packet: ", seq_num)
        packet = Packet(self.queue[seq_num]['data'], checksum, seq_num, False)
        self.udp_helper.send(packet.getSerializedPacket(), self)


class SR:
    def __init__(self, window_size, sequence_bits, segment_size, timeout_period, num_of_packets, port_no):
        self.window_size = window_size
        self.sequence_bits = sequence_bits
        self.sequence_max = 2 ** self.sequence_bits
        self.send_base = 1
        self.segment_size = segment_size
        self.timeout_period = timeout_period
        self.num_of_packets = num_of_packets + 1 # number_of_segments
        self.inorder_ack = 1
        self.timer = False
        self.udp_helper = UDPHelper(port_no)
        self.terminated = False
        self.once = True
        self.queue = [None]
        self.mutex = _thread.allocate_lock() # slide window mutex
        self.main_mutex = _thread.allocate_lock() # slide window mutex
        self.checksumECount = int(num_of_packets*0.1)
        self.lostAckECount = int(0.05*num_of_packets)
        self.checkEPackets = [ random.randint(1,num_of_packets) for i in range(self.checksumECount)]
        self.lostAckEPackets = [ random.randint(1,num_of_packets) for i in range(self.lostAckECount)]
        print("checkEPackts: ", self.checkEPackets)
        print("lostAckEPackets: ", self.lostAckEPackets)
        for i in range(1, self.num_of_packets+1):
            self.queue.append({'num': i, 'data': None, 'status': 'not_sent', 'timer': None})

    def get_next_seq_num(self, curr_seq):
        return curr_seq
        curr_seq%=self.sequence_max
        if(curr_seq == 0): curr_seq = self.sequence_max
        return curr_seq
    
    def slide_window(self,):
        self.mutex.acquire()
        for i in range(self.send_base, min(self.send_base + self.window_size + 1, self.num_of_packets)):
            # print('ha ha -> ', self.queue[i]['status'])
            if(self.queue[i]['status'] == 'acked'):
                self.send_base+=1
            else:
                break

        self.mutex.release()
    
    def timeout_check(self, seq_num):
        self.mutex.acquire()
        if(self.queue[seq_num]['status'] is not 'acked'):
            self.queue[seq_num]['status'] = 'timeout'
            print("Timedout segment: ", self.get_next_seq_num(seq_num), ", Resending")
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
        if(inorder_ack >= self.num_of_packets+1): #check if transmission is done
            self.done()

        if(ack):
            if(ack in self.lostAckEPackets):
                self.main_mutex.release()
                self.lostAckEPackets.pop(self.lostAckEPackets.index(ack))
                print("Simulating ack loss for ack no: ", ack)
                return

            condition = ack in range(self.send_base, min(self.send_base + self.window_size + 1, self.num_of_packets))
            if(condition):
                print("Received ACK: ", self.get_next_seq_num(ack))
                self.inorder_ack = ack
                self.update_queue_ack(ack)
                self.slide_window()
                self.process_queue()

        elif(inorder_ack > self.num_of_packets): #check if transmission is done
            self.done()
        
        else:
            self.process_queue()
        
        self.main_mutex.release()
    
    def start(self):
        self.next()

    def done(self):
        if(not self.terminated):
            print("Done transmitting packets. Terminating.")
            self.terminated = True
            exit()

    def send_packet(self, seq_num):
        print("Sending ", self.get_next_seq_num(seq_num), "; Timer started")
        if(not self.queue[seq_num]['data']): self.queue[seq_num]['data'] = Util.randomString(self.segment_size)
        checksum = Checksum.compute(self.queue[seq_num]['data'])
        if(seq_num in self.checkEPackets):
            checksum = "avalakipavalaki"
            self.checkEPackets.pop(self.checkEPackets.index(seq_num))
            print("Simulating wrong checksum for packet: ", seq_num)
        packet = Packet(self.queue[seq_num]['data'], checksum, seq_num, False)
        self.udp_helper.send(packet.getSerializedPacket(), self)

class UDPHelper:
    def __init__(self, port_no):
        self.ip_address = '127.0.0.1'
        self.port_number = port_no
        self.clientSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiver_running = False
        self.receiver = None
        self.parent = None
    
    def send(self, content, parent):
        self.parent = parent
        self.clientSock.sendto(content, (self.ip_address, self.port_number))
        if(not self.receiver_running):
            pass
        self.startReceiver()
        return
    
    def receive(self):
        while True:
            try:
                ack_rec,_ = self.clientSock.recvfrom(1024)
                if(ack_rec):
                    ack_rec = int(ack_rec.decode("utf-8"))
                    self.parent.next(ack_rec)
                    break #remove this
            except ConnectionResetError:
                print("Receiver not found.")
                os._exit(0)
        return
    
    def startReceiver(self):
        self.receiver_running = True
        self.receiver = threading.Thread(target=self.receive, args=())
        self.receiver.start()
        return
    
    def waitToReceive(self):
        self.receiver.join()
        return

if __name__ == "__main__":
    if(len(sys.argv) is not 4):
        print("Invalid number of arguments.")
        print("Syntax: ")
        print("Mysender inputfile portNum 1000")
    else:
        try:
            file = open(sys.argv[1]).readlines()
            protocol = file[0].strip()
            sequence_bits = int(file[1].strip().split(' ')[0])
            window_size = int(file[1].strip().split(' ')[1])
            timeout_period = float(file[2].strip())
            segment_size = int(file[3].strip())
            port_no = int(sys.argv[2])

            if(protocol == "GBN"):
                gbn = GBN(window_size, sequence_bits, segment_size, timeout_period, int(sys.argv[3]), port_no)
                gbn.start()
            elif(protocol == "SR"):
                sr = SR(window_size, sequence_bits, segment_size, timeout_period, int(sys.argv[3]), port_no)
                sr.start()
        
        except ConnectionResetError:
            print("Receiver not found")
            os._exit(0)

        except Exception :
            raise Exception
        
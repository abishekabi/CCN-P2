import pickle

class Packet:
    def __init__(self, data = None, checksum = None, seq_num = None, last_pkt = None):
        self.data = data
        self.checksum = checksum
        self.seq_num = seq_num
        self.last_pkt = last_pkt
        
        self.serialized_form = None
        
    def getSerializedPacket(self):
        if(not self.serialized_form):
            self.serialized_form = pickle.dumps({'seq_num': self.seq_num, 'checksum': self.checksum, 'data': self.data, 'last_pkt': self.last_pkt})
        return self.serialized_form

    def deserializePacket(self, packet):
        deserialized_form = pickle.loads(packet)
        # print("deserialized_form: ", deserialized_form)
        self.data = deserialized_form['data']
        self.checksum = deserialized_form['checksum']
        self.seq_num = deserialized_form['seq_num']
        self.last_pkt = deserialized_form['last_pkt']
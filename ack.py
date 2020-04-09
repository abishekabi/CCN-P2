import pickle

class Ack:
    def __init__(self, checksum = None, ack_num = None):
        self.ack_num = ack_num
        self.serialized_ack = None
        
    def getSerializedAck(self):
        if(not self.serialized_ack):
            self.serialized_ack = pickle.dumps({'ack_num': self.ack_num})
        return self.serialized_ack

    def deserializeAck(self, ack):
        deserialized_ack = pickle.loads(ack)
        print("deserialized_ack: ", deserialized_ack)
        self.ack_num = deserialized_ack['ack_num']
        print("data---> ", self.ack_num)
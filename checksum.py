class Checksum:
    def __init__(self):
        pass
    
    @staticmethod
    def compute(data):
        chk_sum = 0
        # Takes in 2 chars
        for i in range(0, len(data), 2):
            if (i+1) < len(data):
                pos_1 = ord(data[i]) 
                pos_2 = ord(data[i+1])
                chk_sum = chk_sum + (pos_1+(pos_2 << 8))
            elif (i+1)==len(data):
                chk_sum += ord(data[i])
            else:
                raise "Something's off"
        chk_sum = chk_sum + (chk_sum >> 16)
        chk_sum = ~chk_sum & 0xffff

        return chk_sum
    
    @classmethod
    def verify(cls, data, chk):
        if(cls.compute(data) == chk):
            return True
        else:
            return False
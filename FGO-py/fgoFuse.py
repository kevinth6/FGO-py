import time
from fgoSchedule import ScriptStop
from fgoLogging import getLogger
logger=getLogger('Fuse')

# Tulkas modified. Added fuse_time check to first throw a StuckException that can be recovered,
# before ScriptStop
StuckException = type('StuckException', (Exception,), {})
TimeoutException = type('TimeoutException', (Exception,), {})
MAX_FUSE_TIME = 3
class Fuse:
    def __init__(self,fv=150,logsize=10):
        self.value=0
        self.max=fv
        self.logsize=logsize
        self.log=[None]*logsize
        self.logptr=0
        self.fuse_time=0
        self.timeout_time=None
    def increase(self):
        logger.debug(f'{self.value}')
        if self.value>self.max:
            self.fuse_time += 1
            self.save()
            if self.fuse_time >= MAX_FUSE_TIME:
                raise ScriptStop('Fused')
            else:
                self.value = 0
                raise StuckException(f"Stuck {self.fuse_time}")
        if self.timeout_time and time.time() > self.timeout_time:
            self.save()
            raise TimeoutException('Timeout')
        self.value+=1
    def reset(self,detect=None):
        self.value=0
        self.fuse_time = 0
        if detect is not None and detect is not self.log[(self.logptr-1)%self.logsize]:
            self.log[self.logptr]=detect
            self.logptr=(self.logptr+1)%self.logsize
        return True
    def save(self,path='fgoFuse'):[self.log[(i+self.logptr)%self.logsize].save(f'{path}/Fuse_{i:02}') for i in range(self.logsize)if self.log[(i+self.logptr)%self.logsize]]
fuse=Fuse()

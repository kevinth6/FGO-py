from tksDetect import *
import fgoSchedule

class TksCommon:
    def __init__(self, config):
        self.config = config

    def back_to_menu(self):
        """Try to get back to the interface that contains the menu on the bottom"""
        while not TksDetect().isMainInterface():
            t = TksDetect.cache
            if t.appear(MAIN_TL_CLOSE):
                t.click(MAIN_TL_CLOSE)
            elif t.appear(MAIN_MENU_CLOSE):
                t.click(MAIN_MENU_CLOSE)
            elif t.appear(NOTICE):
                t.click(C_NOTICE_CLOSE)
            fgoSchedule.schedule.sleep(.5)

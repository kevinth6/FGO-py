import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *

logger = getLogger('TksCommon')

FlowException = type('FlowException', (Exception,), {})


class TksCommon:
    def __init__(self, config):
        self.config = config

    def wait(self, img, rect=(0, 0, 1280, 720), threshold=.05, interval=.3):
        while not TksDetect().appear(img, rect, threshold):
            schedule.sleep(interval)
        return self

    def wait_btn(self, button, interval=.3):
        return self.wait(button.img, button.rect, button.threshold, interval)

    def wait_and_click(self, img, rect=(0, 0, 1280, 720), threshold=.05, interval=.3, after_delay=.3):
        while not (p := TksDetect().find(img, rect, threshold)):
            schedule.sleep(interval)

        TksDetect.cache.click(p, after_delay)
        return self

    def wait_and_click_btn(self, button, interval=.3, after_delay=.3):
        return self.wait_and_click(button.img, button.rect, button.threshold, interval, after_delay)

    def wait_for_main_interface(self, interval=.3):
        while not TksDetect().isMainInterface():
            schedule.sleep(interval)
        return self

    def back_to_top(self):
        """Get back to the interface that contains the menu on the bottom"""
        logger.info('Back to menu')
        while not TksDetect().isMainInterface():
            t = TksDetect.cache
            if t.appear_btn(NOTICE):
                t.click(P_NOTICE_CLOSE)
            elif t.find_and_click_btn(MAIN_TL_CLOSE) \
                    or t.find_and_click_btn(MAIN_MENU_CLOSE) \
                    or t.find_and_click(IMG.TKS_CROSS, A_FULL_DIALOG_CROSS):
                pass
            else:
                t.device.perform('\xBB\x08', (200, 200))
            fgoSchedule.schedule.sleep(.5)
        return self

    def go_menu(self, menu_pos):
        """Go to one main menu, guarantee in main interface before return"""
        logger.info('Go menu ' + str(menu_pos))
        if not TksDetect.cache:
            TksDetect()

        TksDetect.cache.click(P_MAIN_MENU, 0.3)
        self.wait_btn(MAIN_MENU_CLOSE)
        fgoDevice.device.touch(menu_pos)

        while not TksDetect().isMainInterface():
            if TksDetect.cache.find_and_click_btn(MAIN_MENU_CLOSE):
                break
            schedule.sleep(0.3)

        return self

    def swipe_and_click_sub_menu(self, img, max_swipe=20):
        """You must guarantee the menu exists, otherwise Exception thrown."""
        for i in range(max_swipe):
            if s := TksDetect().find_and_click(img, A_SUB_MENUS):
                break
            fgoDevice.device.swipe(P_SUBMENU_SWIPE_START + P_SUBMENU_SWIPE_END)
            schedule.sleep(0.3)

        if not s:
            raise FlowException("Can find the menu")

        return self

    def close_all_dialogs(self, check_times=3):
        """Guarantee all the dialogs are closed, try to click the button with button_img,
        exit if not finding the button for 3 times."""
        logger.info("Closing all Dialogs")
        i = 0
        while i < check_times:
            t = TksDetect().cache
            if p := t.find(IMG.TKS_DIALOG_CLOSE, A_DIALOG_BUTTONS) \
                    or t.find(IMG.TKS_DIALOG_CLOSE2, A_DIALOG_BUTTONS):
                logger.info("Dialog found with close button")
                t.click(p)
            elif p := t.find(IMG.TKS_CROSS, A_FULL_DIALOG_CROSS):
                logger.info("Dialog found with cross button")
                t.click(p)
            elif p := t.find(IMG.TKS_DIALOG_FORWARD, A_FULL_DIALOG_CONFIRM):
                logger.info("Dialog found with forward button")
                t.click(p)
            elif t.isMainInterface():
                i = i + 1
            else:
                fgoDevice.device.press('\xBB')
            schedule.sleep(.8)
        logger.info("Finish closing Dialogs")

    def wait_for_main_interface(self, interval=.3):
        while not TksDetect().isMainInterface():
            schedule.sleep(interval)
        return self

    def wait_for_submenu(self, interval=.3):
        return self.wait(IMG.LISTBAR, A_LIST_BAR)

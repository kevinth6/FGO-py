import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *

logger = getLogger('TksCommon')

FlowException = type('FlowException', (Exception,), {})


def save_get(dict, name):
    return dict[name] if name in dict else None


class TksCommon:
    def click(self, pos, after_delay=0.3):
        device.touch(pos)
        schedule.sleep(after_delay)
        return self

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
        logger.info('Back to top')
        while not (TksDetect().appear_btn(B_TOP_NOTICE)
                   and TksDetect.cache.isMainInterface()
                   and TksDetect.cache.appear(IMG.LISTBAR, A_LIST_BAR)):
            t = TksDetect.cache
            if t.find_and_click_btn(B_MAIN_TL_CLOSE) \
                    or t.find_and_click_btn(B_MAIN_MENU_CLOSE) \
                    or t.find_and_click(IMG.TKS_BACK_MGMT, A_TL_BUTTONS):
                pass
            else:
                t.device.perform('\xBB', (200,))
            fgoSchedule.schedule.sleep(.5)
        TksDetect.cache.click(P_SCROLL_TOP, after_delay=.5)
        return self

    def go_menu(self, menu_pos):
        """Go to one main menu, guarantee in main interface before return"""
        logger.info('Go menu ' + str(menu_pos))
        if not TksDetect.cache:
            TksDetect()

        TksDetect.cache.click(P_MAIN_MENU, .5)
        self.wait_btn(B_MAIN_MENU_CLOSE)
        fgoDevice.device.touch(menu_pos)

        schedule.sleep(.5)
        while not TksDetect().isMainInterface():
            if TksDetect.cache.find_and_click_btn(B_MAIN_MENU_CLOSE):
                break
            schedule.sleep(.5)

        return self

    def scroll_and_find(self, img, area, end_pos=P_RIGHT_SCROLL_END, max_swipe=20):
        return self.scroll_and_find_func(lambda t, i: t.find(img, area), end_pos, max_swipe)

    def scroll_and_find_func(self, func, end_pos=P_RIGHT_SCROLL_END, max_swipe=20):
        for i in range(max_swipe):
            if (s := func(TksDetect(), i)) or TksDetect.cache.is_list_end(end_pos):
                break
            fgoDevice.device.swipe(A_SWIPE_RIGHT_DOWN)
            schedule.sleep(0.3)

        return s

    def scroll_and_click(self, img, area, end_pos=P_RIGHT_SCROLL_END, max_swipe=20):
        """You must guarantee the menu exists, otherwise Exception thrown."""
        if s := self.scroll_and_find(img, area, end_pos, max_swipe):
            TksDetect.cache.click(s)
            return self
        else:
            raise FlowException("Can't find the target to click, area " + str(area))

    def find_dialog_close(self, detect):
        if p := detect.find(IMG.TKS_DIALOG_CLOSE, A_DIALOG_BUTTONS) \
                or detect.find(IMG.TKS_DIALOG_CLOSE2, A_DIALOG_BUTTONS):
            logger.info("Dialog found with close button")
            return p
        elif p := detect.find(IMG.TKS_CROSS, A_FULL_DIALOG_CROSS):
            logger.info("Dialog found with cross button")
            return p
        elif p := detect.find(IMG.TKS_DIALOG_FORWARD, A_FULL_DIALOG_CONFIRM):
            logger.info("Dialog found with forward button")
            return p
        elif detect.appear_btn(B_NOTICE):
            logger.info("Notice dialog found")
            return P_NOTICE_CLOSE
        else:
            return None

    def close_all_dialogs(self, check_times=3):
        """Guarantee all the dialogs are closed, try to click the button with button_img,
        exit if not finding the button for 3 times. until_func accepts a TksDetection and return bool"""
        logger.info("Closing all Dialogs")
        i = 0
        while i < check_times:
            t = TksDetect(.4, .3).cache
            if p := self.find_dialog_close(t):
                t.click(p)
            elif t.isMainInterface():
                i = i + 1
            else:
                fgoDevice.device.press('\xBB')

        logger.info("Finish closing Dialogs")
        return self

    def wait_for_main_interface(self, interval=.5):
        while not TksDetect().isMainInterface():
            schedule.sleep(interval)
        return self

    def wait_for_submenu(self, interval=.5):
        while not TksDetect.cache.appear(IMG.LISTBAR, A_LIST_BAR):
            schedule.sleep(interval)
        return self

    def click_and_wait_for_menu_view(self, pos, move_step=None, interval=.7, max_times=5):
        for i in range(max_times):
            self.click(pos, interval)
            if TksDetect().is_on_menu() and TksDetect.cache.appear(IMG.LISTBAR, A_LIST_BAR):
                return True
            if move_step:
                pos = (pos[0] + move_step[0], pos[1] + move_step[1])
        return False

    def skip_possible_story(self):
        # try to skip story
        fgoDevice.device.perform('\x08', (500,))
        t = TksDetect(.2, .3).cache
        if p := t.find(IMG.TKS_SKIP_YES, A_DIALOG_BUTTONS):
            logger.info('skip main story')
            t.click(p, after_delay=.5)
            return True
        return False

    def handle_special_drop(self, detect, fav=True):
        if detect.isSpecialDropSuspended():
            logger.info('Special dropped.')
            while fav and (p := detect.find(IMG.TKS_FAV, A_LEFT_BUTTONS, after_delay=.5)):
                logger.info('Mark special as fav.')
                detect.click(p)
                detect = TksDetect().cache
        fgoDevice.device.perform('\x1B', (500,))

    def eat_apple(self, context):
        job_context = context.cur_job_context()
        job_config = context.cur_job_config()
        if not job_context.apple_remaining():
            logger.info('No apple remaining.')
            fgoDevice.device.press('Z')
            return False
        job_context.apple_used += 1
        logger.info('Eating an apple. Used ' + str(job_context.apple_used))
        apple_kind = (job_config['appleKind']) if 'appleKind' in job_config else 0
        fgoDevice.device.perform('W4K8'[apple_kind] + 'L', (1000, 2000))
        while TksDetect(.5, .5).isApEmpty():
            pass
        # for i in set('W4K')-{'W4K8'[self.appleKind]}:
        #     if not Detect().isApEmpty():break
        #     fgoDevice.device.perform(i+'L',(600,1200))
        # else:raise ScriptStop('No Apples')
        return True

    def swipe_on_map_and_do(self, func):
        schedule.sleep(1)
        fgoDevice.device.pinch()
        schedule.sleep(1)
        TksDetect().find_and_click_btn(B_MAIN_TL_CLOSE, after_delay=1)

        schedule.sleep(1)
        fgoDevice.device.swipe(A_SWIPE_CENTER_DOWN)
        schedule.sleep(1)
        fgoDevice.device.swipe(A_SWIPE_CENTER_DOWN)
        schedule.sleep(1)

        i = 0
        while True:
            schedule.sleep(.5)
            if func(TksDetect(), i):
                return True
            else:
                i += 1
                if i > 2:
                    break
                fgoDevice.device.swipe(A_SWIPE_CENTER_UP)
        return False

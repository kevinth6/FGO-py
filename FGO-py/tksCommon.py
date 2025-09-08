import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *

logger = getLogger('TksCommon')

FlowException = type('FlowException', (Exception,), {})
AbandonException = type('AbandonException', (Exception,), {})


class TksCommon:
    def click(self, pos, after_delay=0.5, offset=None):
        if offset:
            clp = lambda value, minv, maxv: max(min(value, maxv), minv)
            pos = (clp(pos[0] + offset[0], 0, 1280), clp(pos[1] + offset[1], 0, 720))
        device.touch(pos)
        schedule.sleep(after_delay)
        return self

    def wait(self, img, rect=(0, 0, 1280, 720), threshold=.05, interval=.5):
        while not TksDetect().appear(img, rect, threshold):
            schedule.sleep(interval)
        return self

    def click_and_wait(self, pos, img, rect=(0, 0, 1280, 720), threshold=.05, interval=.8):
        for i in range(20):
            self.click(pos, after_delay=interval)
            if TksDetect().appear(img, rect, threshold):
                break
        return self

    def wait_btn(self, button, interval=.5):
        return self.wait(button.img, button.rect, button.threshold, interval)

    def wait_and_click(self, img, rect=(0, 0, 1280, 720), threshold=.05, after_delay=.5, interval=.8):
        while not (p := TksDetect().find(img, rect, threshold)):
            schedule.sleep(interval)

        TksDetect.cache.click(p, after_delay)
        return self

    def wait_and_click_btn(self, button, after_delay=.5, interval=.5):
        return self.wait_and_click(button.img, button.rect, button.threshold, interval, after_delay)

    def wait_for_main_interface(self, interval=.5):
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
            elif p := self.find_dialog_close(t):
                t.click(p, after_delay=.8)
            else:
                self.click(P_TL_BUTTON, after_delay=.2)
                fgoDevice.device.perform('\xBB', (200,))
            fgoSchedule.schedule.sleep(.5)
        self.click(P_SCROLL_TOP, after_delay=.5)
        return self

    def go_menu(self, menu_pos):
        """Go to one main menu, guarantee in main interface before return"""
        logger.info(f'Go menu {menu_pos}')
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

    def go_chapter(self, chapter):
        if not (chapter in INSTANCES):
            raise AbandonException(f'Unknown chapter {chapter}')

        for i in range(1, 3):
            if str(i) in INSTANCES[chapter]['menus']:
                logger.info(f'Go to chapter menu {i}')
                self.wait_for_submenu()
                schedule.sleep(.8)
                self.scroll_and_click(INSTANCES[chapter]['menus'][str(i)], A_SUB_MENUS,
                                      scroll_area=A_SWIPE_RIGHT_DOWN_LOW)
                schedule.sleep(1)
                if p := self.find_dialog_close(TksDetect()):
                    self.click(p)
                    raise AbandonException('Unexpected dialog during menus ')
            else:
                break

    def scroll_and_find(self, func, end_pos=P_RIGHT_SCROLL_END, max_swipe=20, top_pos=P_SCROLL_TOP,
                        scroll_area=A_SWIPE_RIGHT_DOWN):
        self.click(top_pos, after_delay=.8)
        for i in range(max_swipe):
            if (s := func(TksDetect(), i)) or TksDetect.cache.is_list_end(end_pos) or \
                    not TksDetect.cache.appear(IMG.LISTBAR, clamp_rect(
                        (top_pos[0] - 35, top_pos[1] - 35, end_pos[0] + 35, end_pos[1] + 35))):
                break
            fgoDevice.device.swipe(scroll_area)
            schedule.sleep(.5)

        return s

    def scroll_and_click(self, img, area, end_pos=P_RIGHT_SCROLL_END, max_swipe=20, top_pos=P_SCROLL_TOP,
                         threshold=.05, scroll_area=A_SWIPE_RIGHT_DOWN):
        """You must guarantee the menu exists, otherwise Exception thrown."""
        if s := self.scroll_and_find(lambda t, i: t.find(img, area, threshold), end_pos, max_swipe, top_pos,
                                     scroll_area):
            TksDetect.cache.click(s)
            return self
        else:
            raise FlowException("Can't find the target to click, area " + str(area))

    def find_dialog_close(self, t):
        if p := t.find(IMG.TKS_DIALOG_CLOSE, A_DIALOG_BUTTONS) \
                or t.find(IMG.TKS_DIALOG_CLOSE2, A_DIALOG_BUTTONS) \
                or t.find(IMG.APEMPTY, A_DIALOG_BUTTONS):
            logger.info("Dialog found with close button")
            return p
        elif p := (t.find(IMG.TKS_CANCEL, A_DIALOG_BUTTONS) or t.find(IMG.TKS_CANCEL2, A_DIALOG_BUTTONS)):
            logger.info("Dialog found with cancel button")
            return p
        elif p := t.find(IMG.TKS_EXIT, A_DIALOG_BUTTONS):
            logger.info("Dialog found with exit button")
            return p
        elif p := t.find(IMG.TKS_CROSS, A_FULL_DIALOG_CROSS):
            logger.info("Dialog found with cross button")
            return p
        elif p := t.find(IMG.TKS_DIALOG_FORWARD, A_FULL_DIALOG_CONFIRM):
            logger.info("Dialog found with forward button")
            return p
        elif t.appear_btn(B_NOTICE):
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
        while not TksDetect().appear(IMG.LISTBAR, A_LIST_BAR):
            schedule.sleep(interval)
        return self

    def click_and_wait_for_menu_view(self, pos, move_step=None, interval=1, max_times=5):
        for i in range(max_times):
            self.click(pos, interval)
            if TksDetect().is_on_menu():
                t = TksDetect.cache
                if t.appear(IMG.TKS_CAMPAIGN_REWARD_BTN, A_TOP_RIGHT) \
                    and t.appear(IMG.LISTBAR, A_LIST_BAR):
                    return pos
                else:
                    logger.warn('Unexcpected menu. exit')
                    t.click(P_TL_BUTTON, after_delay=.7)
                    return None
            if move_step:
                pos = (pos[0] + move_step[0], pos[1] + move_step[1])
        return None

    def skip_possible_story(self):
        # try to skip story
        fgoDevice.device.perform('\x08', (500,))
        t = TksDetect(.2, .3).cache
        if p := t.find(IMG.TKS_SKIP_YES, A_DIALOG_BUTTONS):
            logger.info('skip main story')
            t.click(p, after_delay=.5)
            return True
        return False

    def handle_special_drop(self, t, context, fav=True):
        cjc = context.cur_job_context()
        if t.isSpecialDropSuspended():
            while fav and (p := t.find(IMG.TKS_FAV, A_LEFT_BUTTONS)):
                logger.info('Mark special as fav.')
                t.click(p)
                t = TksDetect().cache
            fgoDevice.device.perform('\x1B', (1500,))
            cjc.special_drops += 1
            return True
        else:
            return False

    def eat_apple(self, context):
        if not context.apple_remaining():
            logger.info('No apple remaining.')
            fgoDevice.device.press('Z')
            return False
        context.apple_used += 1
        logger.info('Eating an apple. Used ' + str(context.apple_used))
        apple_kind = context.apple_kind() or 0
        fgoDevice.device.perform('W4K8'[apple_kind] + 'L', (1000, 2000))
        while TksDetect(.5, .5).isApEmpty():
            pass
        context.save_stat()
        # for i in set('W4K')-{'W4K8'[self.appleKind]}:
        #     if not Detect().isApEmpty():break
        #     fgoDevice.device.perform(i+'L',(600,1200))
        # else:raise ScriptStop('No Apples')
        return True

    def swipe_on_map_and_do(self, func):
        self._pinch_and_swipe_down()

        i = 0
        while True:
            schedule.sleep(.5)
            if ret := func(TksDetect(), i):
                return ret
            else:
                i += 1
                if i > 2:
                    break
                fgoDevice.device.swipe(A_SWIPE_CENTER_UP)
        return None

    def _pinch_and_swipe_down(self):
        schedule.sleep(3)
        fgoDevice.device.pinch()
        schedule.sleep(1)
        TksDetect().find_and_click_btn(B_MAIN_TL_CLOSE, after_delay=1)

        schedule.sleep(1)
        fgoDevice.device.swipe(A_SWIPE_CENTER_DOWN)
        schedule.sleep(1)
        fgoDevice.device.swipe(A_SWIPE_CENTER_DOWN)
        schedule.sleep(1)

    def go_on_map_and_menu(self, map_img, menu_img, map_screen, map_pos, menu_scroll, menu_pos):
        """search by images first, if not found, search by swipe and pos"""
        if not map_img and not map_screen and not map_pos:
            logger.info("Campaign have no map, skip the map locating")
            p = True
        else:
            if p := self.swipe_on_map_and_do(lambda t, st: t.find(map_img, threshold=.05)):
                p = self.click_and_wait_for_menu_view(p)

            if not p:
                logger.info(f'find map location by screen {map_screen} and pos {map_pos}')
                self._pinch_and_swipe_down()
                for i in range(map_screen):
                    fgoDevice.device.swipe(A_SWIPE_CENTER_UP)
                    schedule.sleep(1)
                p = self.click_and_wait_for_menu_view(map_pos)

        if p:
            if not (p := self.scroll_and_find(lambda t, i: t.find(menu_img, A_INSTANCE_TITLE, threshold=.03))):
                logger.info(f'find menu location by scroll {menu_scroll} and pos {menu_pos}')
                self.click(P_SCROLL_TOP, after_delay=.8)
                for i in range(menu_scroll):
                    fgoDevice.device.swipe(A_SWIPE_RIGHT_DOWN)
                    schedule.sleep(.5)
                p = menu_pos
            self.click((p[0] - 100, p[1]), after_delay=.7)
            return True
        else:
            logger.warning(f"Can't open section menu")
            return False

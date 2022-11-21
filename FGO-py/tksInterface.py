import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *
from tksCommon import TksCommon, FlowException

logger = getLogger('TksInterface')


class TksInterface:
    def __init__(self, context):
        self.common = TksCommon()
        self.context = context

    def _wait_for_start(self):
        logger.info('Wait for the game start screen')

        # the login box could be flashed at the beginning of the game, so here check 3 times
        i = 0
        while not (t := TksDetect().appear(IMG.TKS_LOGIN_RECORDS, A_LOGIN_BOX)) or i < 3:
            fgoDevice.device.press('\xBB')
            schedule.sleep(.5)
            if t:
                i = i + 1

    def _wait_for_game_enter(self):
        logger.info('Waiting for entering the game')
        while True:
            t = TksDetect().cache
            if t.is_on_top() \
                    or t.isMainInterface() \
                    or t.appear(IMG.TKS_DIALOG_CLOSE, A_DIALOG_BUTTONS) \
                    or t.appear(IMG.TKS_DIALOG_FORWARD, A_FULL_DIALOG_CONFIRM):
                break
            else:
                t.device.perform('Z', (500,))
        schedule.sleep(1)

    def _select_account(self, account, max_swipe):
        logger.info('Select account ' + account)
        TksDetect.cache.find_and_click(IMG.TKS_LOGIN_DROPDOWN, A_LOGIN_BOX)

        for i in range(max_swipe):
            if s := TksDetect().find_and_click(ACCOUNTS[account], A_LOGIN_BOX):
                break
            fgoDevice.device.swipe((625, 420, 625, 370))
            schedule.sleep(0.3)
        if not s:
            raise FlowException("Can find the account " + account)

        TksDetect().find_and_click(IMG.TKS_LOGIN, A_LOGIN_BOX, retry=3)
        self._wait_for_game_enter()

    def switch_to_account(self, account):
        logger.info('Switch to account ' + account)
        self.common.back_to_top().go_menu(P_MENU_ROOM) \
            .scroll_and_click(IMG.TKS_MENU_BACK_MAIN, A_SUB_MENUS) \
            .wait_and_click(IMG.TKS_DIALOG_YES, A_DIALOG_BUTTONS)
        self._wait_for_start()
        self._select_account(account, 5)
        self.common.close_all_dialogs()

    def rotate_all_accounts(self):
        """login each account one by one. Just login, no work. Usually for all the accounts
        appearing in the friend list in battle"""
        if not ('accounts' in self.context.config):
            return
        for account in self.context.config["accounts"]:
            self.switch_to_account(account)

    def _go_section_in_chapter(self, chapter, section):
        logger.info(f'Go to section {section}')
        # sometimes campaign map is slow to open
        if self.common.swipe_on_map_and_do(
                lambda t, i: t.find_and_click(INSTANCES[chapter]['sections'][section], threshold=.1)):
            return self
        else:
            raise FlowException('Unable to find the section')

    def _go_instance(self, chapter, instance):
        if instance and (instance in INSTANCES[chapter]['instances']):
            self.common.scroll_and_click(INSTANCES[chapter]['instances'][instance], A_INSTANCE_MENUS)
        else:
            self.common.scroll_and_click(IMG.TKS_FREE_DONE, A_INSTANCE_MENUS)
        # TODO: could be dialogs here

    def go_free_instance(self, chapter, section, instance):
        logger.info(f'Go to free instance: chapter {chapter}, section {section}, instance {instance}')
        if not (chapter in INSTANCES):
            raise FlowException('Unknown chapter ' + chapter)

        for i in range(1, 3):
            if str(i) in INSTANCES[chapter]['menus']:
                logger.info(f'Go to chapter menu {i}')
                self.common.wait_for_submenu()
                self.common.scroll_and_click(INSTANCES[chapter]['menus'][str(i)], A_SUB_MENUS)
            else:
                break

        if section and (str(section) in INSTANCES[chapter]['sections']):
            while not TksDetect().is_on_map():
                schedule.sleep(.5)
            self._go_section_in_chapter(chapter, str(section))

        while not TksDetect().is_on_menu():
            schedule.sleep(.5)
        self._go_instance(chapter, instance)

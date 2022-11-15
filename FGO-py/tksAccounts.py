from tksDetect import *
from fgoDetect import IMG
import fgoSchedule, fgoDevice
from fgoLogging import getLogger
from tksCommon import FlowException

logger = getLogger('TksAccounts')


class TksAccounts:
    def __init__(self, config, common):
        self.config = config
        self.common = common

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
                    or t.appear(IMG.TKS_DIALOG_CLOSE, A_DIALOG_BUTTONS)\
                    or t.appear(IMG.TKS_DIALOG_FORWARD, A_FULL_DIALOG_CONFIRM):
                break
            else:
                t.device.perform('\xBB\x08', (200, 200))
            schedule.sleep(0.5)


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
            .swipe_and_click_sub_menu(IMG.TKS_MENU_BACK_MAIN) \
            .wait_and_click(IMG.TKS_DIALOG_YES, A_DIALOG_BUTTONS)
        self._wait_for_start()
        self._select_account(account, 5)
        self.common.close_all_dialogs()

    def rotate_all_accounts(self):
        """login each account one by one. Just login, no work. Usually for all the accounts
        appearing in the friend list in battle"""
        if not ('accounts' in self.config):
            return
        for account in self.config["accounts"]:
            self.switch_to_account(account)

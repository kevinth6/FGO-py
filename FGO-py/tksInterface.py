import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from fgoConst import KEYMAP
from tksDetect import *
from tksCommon import TksCommon, FlowException, AbandonException
from tksBattle import TksBattleGroup
from tksContext import TksContext

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
                t.device.perform('\xBB', (500,))
        schedule.sleep(1)

    def _select_account(self, account, max_swipe):
        logger.info('Select account ' + account)
        TksDetect.cache.find_and_click(IMG.TKS_LOGIN_DROPDOWN, A_LOGIN_BOX)

        for i in range(max_swipe):
            if s := TksDetect().find_and_click(ACCOUNTS[account], A_LOGIN_BOX, threshold=.02):
                break
            self.common.swipe((625, 420, 625, 395))
            schedule.sleep(0.8)
        if not s:
            raise FlowException("Can find the account " + account)

        TksDetect().find_and_click(IMG.TKS_LOGIN, A_LOGIN_BOX, retry=3)
        self._select_region(self.context.config['account_regions'][account])
        self._wait_for_game_enter()
    
    def _select_region(self, region):
        logger.info(f'Select region {region}')
        self.common.wait_and_click(IMG.TKS_REGION_SELECT, A_BR_BUTTONS) \
            .wait(IMG.TKS_REGION_IOS, A_DIALOG_BUTTONS)
        ret = False
        if region == 'ios':
            ret = TksDetect.cache.find_and_click(IMG.TKS_REGION_IOS, A_DIALOG_BUTTONS)
        elif region == 'android':
            ret = TksDetect.cache.find_and_click(IMG.TKS_REGION_ANDROID, A_DIALOG_BUTTONS)
        else:
            raise AbandonException('Invalid region! ')

        if not ret:
            raise AbandonException('Fail to select region! ')

    def switch_to_account(self, account):
        logger.info('Switch to account ' + account)
        self.common.back_to_top().go_menu(P_MENU_ROOM) \
            .scroll_and_click(IMG.TKS_MENU_BACK_MAIN, A_SUB_MENUS) \
            .wait_and_click(IMG.TKS_DIALOG_YES, A_DIALOG_BUTTONS)
        self._wait_for_start()
        self._select_account(account, 5)

        logger.info('Account login post process')
        i = 0
        while i < 3:
            t = TksDetect(.3, .3).cache
            if t.isTurnBegin():
                logger.info('In battle')
                TksBattleGroup(TksContext.anonymous_context(), run_once=True)()
            elif t.find_and_click(IMG.TKS_NOT_CONTINUE, A_DIALOG_BUTTONS, after_delay=.7):
                logger.info('Click not continue')
            elif t.find_and_click(IMG.TKS_INTERRUPTED_BATTLE_ENTER, A_DIALOG_BUTTONS, after_delay=.7):
                logger.info('Continue interrupted battle')
            elif p := self.common.find_dialog_close(t):
                t.click(p, after_delay=.8)
            else:
                i += 1

    def retrieve_week_awards(self):
        for i in range(3):
            if TksDetect().find_and_click(IMG.TKS_COMPLETED_NOTICE, A_AWARD_NOTICE, threshold=.02):
                logger.info('Found awards notice.')
                break
        if i >= 2:
            logger.info('No awards notice available.')
            return False

        while True:
            t = TksDetect(.2, .5).cache
            if t.appear(IMG.TKS_WEEK_AWARD_ON, A_CAMPAIGN_REWARD_TABS, threshold=.01):
                if t.appear(IMG.TKS_REWARD_READY, A_DESKTOP_AWARD_VIEWS):
                    if p := t.find(IMG.TKS_QUARTZ_SPLIT, A_AWARD_1ST_ICON):
                        logger.info('Find ready quartz split. Get it.')
                        t.click(p, after_delay=.7)
                        t.click(P_DESKTOP_AWARD_VIEW, after_delay=.7)
                    else:
                        logger.info('No ready week award any more.')
                        t.click(P_TL_BUTTON, after_delay=.7)
                        break
                else:
                    t.click(P_DESKTOP_AWARD_VIEW, after_delay=.7)
            elif p := t.find(IMG.TKS_WEEK_AWARD_OFF, A_CAMPAIGN_REWARD_TABS):
                logger.info('Not in week award view. Go to the view')
                t.click(p, after_delay=.7)
            elif p := self.common.find_dialog_close(t):
                t.click(p, after_delay=.7)
            elif t.is_on_map() or t.is_on_top():
                break
            else:
                t.click(P_DESKTOP_AWARD_VIEW, after_delay=.7)

    def rotate_all_accounts(self):
        """login each account one by one. Just login, no work. Usually for all the accounts
        appearing in the friend list in battle"""
        if not ('accounts' in self.context.config):
            return
        for account in self.context.config["accounts"]:
            self.switch_to_account(account)

    def go_section_in_chapter(self, chapter, section):
        logger.info(f'Go to section {section}')
        # sometimes campaign map is slow to open
        if self.common.swipe_on_map_and_do(
                lambda t, i: t.find_and_click(INSTANCES[chapter]['sections'][section], threshold=.1)):
            return self
        else:
            raise FlowException(f'Unable to find the section {section}')

    def go_free_instance(self, chapter, section, instance):
        logger.info(
            f'Go to free instance: chapter {chapter}, section {section}, instance {instance}')
        self.common.go_chapter(chapter)

        if section and (str(section) in INSTANCES[chapter]['sections']):
            while not TksDetect().is_on_map():
                schedule.sleep(.5)
            self.go_section_in_chapter(chapter, str(section))

        while not TksDetect().is_on_menu():
            schedule.sleep(.5)
            
        for i in range(3):
            if instance:
                if instance in INSTANCES[chapter]['instances']:
                    p = self.common.scroll_and_find(lambda t, i: t.find(INSTANCES[chapter]['instances'][instance],
                                                                    rect=A_INSTANCE_MENUS, threshold=.02), max_swipe=80)
                else:
                    raise AbandonException(
                        f'Unable to find the instance {instance}')
            else:
                p = self.common.scroll_and_find(lambda t, i: t.find(IMG.TKS_FREE_DONE, A_INSTANCE_MENUS))
            if p:
                break

        if p:
            self.common.click(p, after_delay=.8)
            return True
        else:
            logger.warning('No free instance found. ')
            return False

    def run_free(self):
        cjc = self.context.cur_job_context()
        while True:
            if self.go_free_instance(cjc.chapter(), cjc.section(), cjc.instance()):
                if TksBattleGroup(self.context)():
                    self.common.back_to_top()
                else:
                    break
            else:
                break

    def run_reishift(self):
        cjc = self.context.cur_job_context()
        quest = []
        if cjc.goto():
            quest = tuple(map(int, cjc.goto().split("-")))
        self.common.goto(quest)
        for i in range(3):
            p = self.common.scroll_and_find(lambda t, i: t.find(IMG.TKS_FREE_DONE, A_INSTANCE_MENUS))
            if p:
                break
        if p:
            self.common.click(p, after_delay=.8)
            t = TksDetect(.3, .3)
            if pos := t.find(IMG.TKS_TASK_BEGIN, A_DIALOG_BUTTONS, .05):
                self.common.click(pos, .8)

            if pos := self.common.find_dialog_close(t):
                self.common.click(pos, .3)
                return False

            if TksBattleGroup(self.context)():
                self.common.back_to_top()
                return True
        else:
            logger.warning('No free instance found. ')
            return False

    def run_rank_up(self):
        logger.info(f'Go rank up')
        self.common.go_chapter('rank_up')
        schedule.sleep(1)

        while True:
            t = TksDetect(.3, .3)
            if t.appear(IMG.TKS_CHOOSE_FRIEND, A_TOP_RIGHT):
                TksBattleGroup(self.context, run_once=True)()
            elif t.isApEmpty():
                logger.info('AP empty.')
                if not self.common.eat_apple(self.context):
                    logger.info('Exit due to no AP.')
                    break
            elif self.common.handle_special_drop(t, self.context):
                logger.info('Special dropped.')
            elif t.find_and_click(IMG.TKS_DIALOG_BEGIN, A_DIALOG_BUTTONS):
                logger.info('click begin')
            elif t.appear_btn(B_SUMMON_SALE):
                raise FlowException('Card position full. Need synthesis. ')
            elif p := self.common.find_dialog_close(t):
                self.common.click(p, .7)
            elif t.is_on_menu():
                self.common.click(P_SCROLL_TOP, .7)
                logger.info("Select first instance in menu")
                i = 0
                while i < 3:
                    self.common.click(KEYMAP['8'], 3)
                    if TksDetect().appear(IMG.TKS_CHOOSE_FRIEND, A_TOP_RIGHT) \
                            or TksDetect.cache.appear(IMG.TKS_DIALOG_BEGIN, A_DIALOG_BUTTONS) \
                            or TksDetect.cache.isApEmpty():
                        break
                    i += 1
                if i == 3:
                    logger.info('No rank up to run. Exit')
                    break
            elif t.is_on_top():
                logger.info("Unexpected on top. Re-enter")
                self.common.go_chapter('rank_up')
                schedule.sleep(1)
            else:
                fgoDevice.device.perform('\xBB', (500,))

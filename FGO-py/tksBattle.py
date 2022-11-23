import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *
from tksCommon import FlowException, TksCommon
from fgoKernel import Battle, Turn, withLock, lock, time
from tksContext import TksContext

logger = getLogger('TksBattle')

DefeatedException = type('DefeatedException', (Exception,), {})
MAX_DEFEATED_TIMES = 2


class TksBattle(Battle):
    def __init__(self, context):
        self.common = TksCommon()
        self.context = context
        super().__init__(Turn)

    def check_options(self):
        logger.info('check battle options')
        TksDetect().click(P_BATTLE_OPTION)
        if not self.common.wait(IMG.TKS_BATTLE_ESCAPE, A_BATTLE_OPTIONS):
            raise FlowException("Can't open battle option menu")
        # close all options here
        changed = False
        while TksDetect().find_and_click(IMG.TKS_BATTLE_OPTION_OPEN, A_BATTLE_OPTIONS):
            logger.info('disable battle option ')
            changed = True
        self.common.click(P_BATTLE_OPTION_CLOSE, 1)
        if changed:
            # enable double speed
            logger.info('enable double speed')
            self.common.click(P_BATTLE_ATTACK, 1) \
                .wait(IMG.TKS_BATTLE_BACK, A_BATTLE_CMD) \
                .click(P_BATTLE_SPEED, 1) \
                .click(P_BATTLE_BACK, 2)
        self.context.battle_options_checked = True

    def __call__(self):
        if (not self.context.battle_options_checked) and TksDetect(0, .3).isTurnBegin():
            self.check_options()
        return super().__call__()


class TksBattleGroup:
    def __init__(self, context, run_once=False, is_free=True):
        self.context = context
        self.run_once = run_once
        self.is_free = is_free
        self.common = TksCommon()
        self.jc = self.context.cur_job_context()

    def __call__(self, check_options=True):
        logger.info('enter battle group')
        while True:
            if not self._before_battle():
                logger.info("can't enter battle, exit battle group")
                return False
            battle = TksBattle(self.context)
            self._after_battle(battle(), battle.result)
            if self.run_once:
                logger.info('run once done. exit battle group ')
                break
        return True

    def choose_team(self):
        if team_index := self.jc.team_index():
            pass
        elif self.jc.easy_mode():
            team_index = 2
        else:
            team_index = 1
        logger.info('choose team ' + str(team_index))
        if TksDetect.cache.getTeamIndex() != team_index:
            fgoDevice.device.perform('\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79'[team_index], (1000,))

    def battle_completed(self):
        while True:
            t = TksDetect().cache
            if t.isBattleContinue():
                break
            elif self.common.handle_special_drop(t, self.context):
                pass
            elif t.isAddFriend():
                logger.info('add friend')
                fgoDevice.device.perform('X', (300,))
            elif p := self.common.find_dialog_close(t):
                t.click(p)
            elif t.isMainInterface() or t.is_on_map() or t.is_on_menu():
                break
            elif self.common.skip_possible_story():
                pass
            else:
                fgoDevice.device.perform(' ', (600,))

    def _before_battle(self):
        while True:
            t = TksDetect(.8, .8).cache
            if t.isTurnBegin():
                logger.info('turn begin')
                break
            elif t.isApEmpty():
                logger.info('AP empty.')
                if not self.common.eat_apple(self.context):
                    return False
            elif p := t.find(IMG.TKS_DIALOG_CLOSE2, A_DIALOG_BUTTONS):
                # could be friend constraint confirm
                logger.info('Dialog pops up. click close')
                t.click(p)
            elif t.appear(IMG.TKS_CHOOSE_FRIEND, A_TOP_RIGHT):
                logger.info('choose friend. ')
                self.choose_friend()
                # could enter the battle directly if it's in battle continue
            elif t.appear(IMG.TKS_TEAM_CONFIRM, A_TOP_RIGHT):
                self.choose_team()
                fgoDevice.device.perform(' ', (5000,))
            else:
                self.common.skip_possible_story()
            fgoDevice.device.press('\xBB')
        return True

    def _after_battle(self, completed, result):
        if completed:
            logger.info('battle completed. result ' + str(result))
            if result:
                self.jc.battle_completed += 1
                self.jc.total_turns += result['turn']
                self.jc.total_time += result['time']
                self.jc.materials = TksContext.dict_add(self.jc.materials, result['material'])

            fgoDevice.device.perform(' ', (600,))
            self.battle_completed()
        else:
            logger.info('battle failed. result ' + str(result))
            self.jc.battle_failed += 1
            fgoDevice.device.perform('CI', (1000, 1000,))
            self.common.click(P_FAIL_CLOSE, 1)
            if self.jc.battle_failed > MAX_DEFEATED_TIMES:
                raise DefeatedException()

        # handle battle continue
        if TksDetect().isBattleContinue():
            if self.run_once:
                logger.info('cancel battle continue')
                fgoDevice.device.perform('F', (1000,))
            else:
                logger.info('battle continue')
                fgoDevice.device.perform('L', (1000,))

    def choose_friend(self):
        if self.is_free:
            if not self.jc.friend_reisou():
                if not self.jc.campaign_friend_checked and (self.jc.campaign_servant() or self.jc.campaign_reisou()):
                    self._handle_campaign_friend_options()
                    self.jc.campaign_friend_checked = True
                if self.jc.campaign_reisou() and self.jc.campaign_reisou() == 2:
                    self.common.click(PS_FRIEND_CLASSES['all'], after_delay=2)
            if self.jc.friend_class() and self.jc.friend_class() in PS_FRIEND_CLASSES:
                self.common.click(PS_FRIEND_CLASSES[self.jc.friend_class()], after_delay=1)

        has_friend = True
        while True:
            t = TksDetect(.2, .3)
            if t.isNoFriend() or not has_friend:
                self.common.wait(IMG.TKS_FRIEND_REFRESH, A_FRIEND_OPTIONS_BAR)
                fgoDevice.device.perform('\xBAK', (500, 1000))
                has_friend = True
            else:
                if self.jc.friend_reisou() and self.jc.friend_reisou() in FRIEND_REISOUS:
                    if p := self.common.scroll_and_find(
                            lambda t, i: t.find(FRIEND_REISOUS[self.jc.friend_reisou()], A_FRIEND_ICONS),
                            end_pos=P_FRIEND_SCROLL_END, top_pos=P_FRIEND_SCROLL_TOP):
                        return self.common.click(p)
                    else:
                        has_friend = False
                else:
                    return fgoDevice.device.press('8')

    def _handle_campaign_friend_options(self):
        logger.info('Handle campaign friend options')
        t = TksDetect(.3, .3).cache
        if p := (t.find(IMG.TKS_FRIEND_OPTIONS, A_FRIEND_OPTIONS_BAR)
                 or t.find(IMG.TKS_FRIEND_OPTIONS_ON, A_FRIEND_OPTIONS_BAR)):
            self.common.click_and_wait(p, IMG.TKS_DIALOG_DECIDE, A_DIALOG_BUTTONS)
        else:
            return

        logger.info('In campaign friend options dialog')
        self.common.click(P_FRIEND_OPTION_SCROLL_TOP, after_delay=.5)
        self.common.click(P_FRIEND_OPTION_RESET, after_delay=.5)
        if self.jc.campaign_servant():
            self.common.click(P_FRIEND_CAMPAIGN_SERVANT, after_delay=.5)
        if self.jc.campaign_reisou():
            self.common.click(P_FRIEND_CAMPAIGN_REISOU, after_delay=.5)
            if self.jc.campaign_reisou() == 2:
                self.common.click(P_FRIEND_OPTION_SCROLL_MID)
                TksDetect(.3, .3).find_and_click(IMG.TKS_FRIEND_REISOU_MAX, after_delay=.5)

        if (idx := self.jc.campaign_reisou_idx()) is not None:
            logger.info(f'Setup campaign reisou by idx {self.jc.campaign_reisou_idx()}')
            func = lambda t: self._disable_all_reisou(t)
            self._friend_option_scroll(func)
            reisou_imgs = []
            func = lambda t: self._scan_reisou(t, reisou_imgs)
            self._friend_option_scroll(func)
            if idx >= len(reisou_imgs):
                logger.warning(f'Unable to find the campaign reisou.')
            else:
                func = lambda t: self._enable_reisou(t, reisou_imgs[idx])
                self._friend_option_scroll(func, True)

        TksDetect.cache.find_and_click(IMG.TKS_DIALOG_DECIDE, after_delay=.7)

    def _friend_option_scroll(self, func, find_return=False):
        self.common.click(P_FRIEND_OPTION_SCROLL_TOP, after_delay=.5)
        for i in range(5):
            ret = func(TksDetect())
            if find_return and ret:
                return ret
            if TksDetect.cache.is_list_end(P_FRIEND_OPTION_SCROLL_END):
                break
            fgoDevice.device.swipe(A_SWIPE_FRIEND_OPTION_DOWN)
            schedule.sleep(0.3)

    def _disable_all_reisou(self, t):
        ps = t.find_multiple(IMG.TKS_FRIEND_OPTION_SHOW, A_FRIEND_SHOW_BUTTONS)
        for p in ps:
            t.click(p, after_delay=.5)

    def _scan_reisou(self, t, reisou_imgs):
        ps = t.find_multiple(IMG.TKS_FRIEND_OPTION_HIDE, A_FRIEND_SHOW_BUTTONS)
        for p in ps:
            rect = t.surround((p[0] - 500, p[1]), 88, 44)
            for img in reisou_imgs:
                if t.appear(img, t.expand(rect, 2)):
                    return
            reisou_imgs.append([t._crop(rect), None])

    def _enable_reisou(self, t, img):
        if p := t.find(img):
            t.click((p[0] + 500, p[1]), after_delay=.5)
            return True
        return False

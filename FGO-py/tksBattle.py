import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *
from tksCommon import FlowException, TksCommon
from fgoKernel import Battle, Turn, withLock, lock, time

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
        self.context.options_checked = True

    def __call__(self):
        if (not self.context.options_checked) and TksDetect(0, .3).isTurnBegin():
            self.check_options()
        return super().__call__()


class TksBattleGroup:
    def __init__(self, context, run_once=False):
        self.context = context
        self.run_once = run_once
        self.common = TksCommon()
        self.job_config = self.context.cur_job_config()
        self.job_context = self.context.cur_job_context()

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
        if 'teamIndex' in self.job_config:
            team_index = (self.job_config['teamIndex'])
        elif ('easyMode' in self.job_config) and self.job_config['easyMode']:
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
            elif self.common.handle_special_drop(t):
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
                self.job_context.battle_completed += 1
                self.job_context.total_turns += result['turn']
                self.job_context.total_time += result['time']
                self.job_context.material = {i: self.job_context.material.get(i, 0) + result['material'].get(i, 0)
                                             for i in
                                             self.job_context.material | result['material']}
            fgoDevice.device.perform(' ', (600,))
            self.battle_completed()
        else:
            logger.info('battle failed. result ' + str(result))
            self.job_context.battle_failed += 1
            fgoDevice.device.perform('CI', (1000, 1000,))
            self.common.click(P_FAIL_CLOSE, 1)
            if self.job_context.battle_failed > MAX_DEFEATED_TIMES:
                raise DefeatedException()

        # handle battle continue
        if TksDetect().isBattleContinue():
            if self.run_once:
                logger.info('cancel battle continue')
                fgoDevice.device.perform('F', (1000,))
            else:
                logger.info('battle continue')
                fgoDevice.device.press('L', (1000,))

    def choose_friend(self):
        refresh = False
        while not TksDetect(0, .3).isChooseFriend():
            if TksDetect.cache.isNoFriend():
                if refresh: schedule.sleep(10)
                fgoDevice.device.perform('\xBAK', (500, 1000))
                refresh = True
        return fgoDevice.device.press('8')

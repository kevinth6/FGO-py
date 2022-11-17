import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *
from tksCommon import FlowException, TksCommon
from fgoKernel import Battle, Turn, withLock, lock, time

logger = getLogger('TksBattle')


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
            if not self.before_battle():
                logger.info("can't enter battle, exit battle group")
                break
            battle = TksBattle(self.context)
            self.after_battle(battle(), battle.result)
            if self.run_once:
                logger.info('run once done. exit battle group ')
                break

    def choose_team(self):
        team_index = (self.job_config['teamIndex']) if 'teamIndex' in self.job_config else 0
        logger.info('choose team ' + str(team_index))
        if TksDetect.cache.getTeamIndex() != team_index:
            fgoDevice.device.perform('\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79'[team_index], (1000,))

    def battle_completed(self):
        while True:
            t = TksDetect().cache
            if t.isBattleContinue() or t.isMainInterface():
                break
            elif t.isSpecialDropSuspended():
                logger.info('special drop suspended')
                fgoDevice.device.perform('\x1B', (500,))
            elif self.common.find_and_click_dialog_close(t):
                pass
            else:
                fgoDevice.device.press(' ', (600,))

    def before_battle(self):
        while True:
            if TksDetect(1, .7).appear(IMG.TKS_CHOOSE_FRIEND, A_TOP_RIGHT):
                logger.info('choose friend. ')
                self.choose_friend()
                # could enter the battle directly if it's in battle continue
            elif TksDetect.cache.isBattleBegin():
                self.choose_team()
                fgoDevice.device.perform(' ', (5000,))
            elif TksDetect.cache.isApEmpty():
                logger.info('AP empty.')
                if not self.eat_apple():
                    return False
            elif TksDetect.cache.isAddFriend():
                logger.info('add friend')
                fgoDevice.device.perform('X', (300,))
            elif TksDetect.cache.isTurnBegin():
                logger.info('turn begin')
                break
            fgoDevice.device.press('\xBB')
        return True

    def after_battle(self, completed, result):
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

        # handle battle continue
        if TksDetect().isBattleContinue():
            if self.run_once:
                logger.info('cancel battle continue')
                fgoDevice.device.perform('F', (1000,))
            else:
                logger.info('battle continue')
                fgoDevice.device.press('L', (1000,))

    def eat_apple(self):
        if not self.job_context.apple_remaining():
            logger.info('No apple remaining.')
            return fgoDevice.device.press('Z')
        self.job_context.apple_used += 1
        logger.info('Eating an apple. Used ' + str(self.job_context.apple_used))
        apple_kind = (self.job_config['appleKind']) if 'appleKind' in self.job_config else 0
        fgoDevice.device.perform('W4K8'[apple_kind] + 'L', (1000, 2000))
        while TksDetect(.5, .5).isApEmpty():
            pass
        # for i in set('W4K')-{'W4K8'[self.appleKind]}:
        #     if not Detect().isApEmpty():break
        #     fgoDevice.device.perform(i+'L',(600,1200))
        # else:raise ScriptStop('No Apples')
        return self.job_context.apple_used

    def choose_friend(self):
        refresh = False
        while not TksDetect(0, .3).isChooseFriend():
            if TksDetect.cache.isNoFriend():
                if refresh: schedule.sleep(10)
                fgoDevice.device.perform('\xBAK', (500, 1000))
                refresh = True
        return fgoDevice.device.press('8')

import math
import random

import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *
from tksCommon import TksCommon, FlowException
from tksBattle import TksBattleGroup

logger = getLogger('TksCampaign')


class TksCampaign:
    def __init__(self, context, include_free=True):
        self.common = TksCommon()
        self.context = context

    def __call__(self):
        self.common.click(P_CUR_CAMPAIGN, after_delay=1)
        self._run_main_tasks()

    def _run_main_tasks(self):
        tick = 0
        logger.info('Task running start')
        while True:
            t = TksDetect(.5, .5).cache
            if len(ps := t.find_multiple(IMG.TKS_CAMPAIGN_NEXT, threshold=.1)) > 0:
                tick = 0
                logger.info(f'find next tasks, count {len(ps)}')
                if t.is_on_map():
                    idx = random.randint(0, len(ps) - 1)
                    logger.info(f'On map, pick a random task: {idx}, pos: {ps[idx]}')
                    t.click(self._clickable_pos_under_next(ps[idx]), after_delay=.7)
                elif t.is_on_menu():
                    logger.info(f'On menu, iterate tasks.')
                    if not self._iterate_menu_tasks(ps):
                        logger.info('No available tasks')
                        break
            else:
                if t.appear(IMG.TKS_CHOOSE_FRIEND, A_TOP_RIGHT):
                    TksBattleGroup(self.context, True)()
                elif p := t.find(IMG.TKS_CAMPAIGN_BEGIN, A_DIALOG_BUTTONS):
                    tick = 0
                    logger.info('click task begin')
                    t.click(p)
                elif p := t.find(IMG.TKS_DIALOG_BEGIN, A_DIALOG_BUTTONS):
                    tick = 0
                    logger.info('click begin')
                    t.click(p)
                elif p := self.common.find_dialog_close(t):
                    # for all other dialogs, click close
                    tick = 0
                    logger.info('close dialog on ' + str(p))
                    t.click(p)
                elif t.is_on_menu():
                    logger.info("On menu but can't find next task. ")
                    t.click(P_TL_BUTTON)
                elif t.is_on_top():
                    logger.info("Unexpected back to top. ")
                    self.common.click(P_SCROLL_TOP, after_delay=.5)
                    self.common.click(P_CUR_CAMPAIGN, after_delay=1)
                    break
                elif self.common.skip_possible_story():
                    tick = 0

            tick += 1
            if tick > 10:
                logger.info('Exceed max ticks. ')
                break

        logger.info('Exit task running.')

    def _click_task_in_menu(self, pos):
        # task could be unavailable due to the prerequisite not satisfied
        for times in range(0, 4):
            fgoDevice.device.touch(self._clickable_pos_under_next(pos))
            schedule.sleep(.8)
            if not TksDetect().appear(IMG.TKS_CAMPAIGN_NEXT, (pos[0] - 70, pos[1] - 100, pos[0] + 70, pos[1] + 100)):
                return True
        return False

    def _clickable_pos_under_next(self, pos):
        return pos[0], pos[1] + 80

    def _iterate_menu_tasks(self, ps):
        idx = 0
        while idx < len(ps):
            if self._click_task_in_menu(ps[idx]):
                logger.info(f'Found runnable task: {idx}')
                return True
            else:
                logger.info(f'No response after clicking task: {idx}')
                idx += 1
        return False

import random

import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *
from tksCommon import TksCommon, FlowException, safe_get, clamp_rect

logger = getLogger('TksExpBall')


class TksExpBall:
    def __init__(self, context):
        self.common = TksCommon()
        self.context = context
        self.summon_count = 0
        self.synthesis_count = 0
        self.summon_special_count = 0
        cjc = self.context.cur_job_context()
        self.max_synthesis = cjc.max_synthesis() or 20
        self.max_summon_special = cjc.max_summon_special() or 4

    def __call__(self):
        logger.info('ExpBall Start.')
        while self.synthesis_count < self.max_synthesis:
            if not self.summon_fp():
                break
            self.sale_servant()
            self.synthesis_servant()
            self.synthesis_reisou()
            self.synthesis_count += 1
            logger.info(f'Finished synthesis {self.synthesis_count}')
        logger.info('ExpBall End.')

    def summon_fp(self):
        cjc = self.context.cur_job_context()

        self.common.go_menu(MAIN_SUMMON.center)
        while not TksDetect().appear_btn(SUMMON_FP):
            self.common.click(P_SUMMON_SWITCH, after_delay=1.5)

        while not TksDetect().appear_btn(B_SUMMON_AUTO_SALE):
            self.common.click(P_SUMMON_SUMMON, after_delay=1)
        if not cjc.summon_option_checked:
            self._handle_summon_option()

        while not cjc.max_summon() or self.summon_count < cjc.max_summon():
            t = TksDetect()
            if t.appear_btn(B_SUMMON_AUTO_SALE):
                self.summon_count += 1
                logger.info(f'Summon {self.summon_count}.')
                t.click(SUMMON_SUBMIT.center, after_delay=3)
            elif p := t.find_btn(SUMMON_SALE):
                logger.info('Have to sale. Exit this round of summon.')
                self.common.click(p, after_delay=3)
                return True
            elif t.appear_btn(SUMMON_CONTINUE):
                for i in range(10):
                    if not (s := self._find_special(t, i)):
                        continue
                    logger.info(f'Summon special found: {s[0]}')
                    self.common.click(s[1], after_delay=1.5)
                    # self.common.click_and_wait(s[1], IMG.TKS_FAV, A_LEFT_BUTTONS, interval=2)
                    self.common.handle_special_drop(TksDetect(), self.context)
                    if cjc.target_summon_special():
                        if s[0] == cjc.target_summon_special():
                            self.summon_special_count += 1
                    else:
                        self.summon_special_count += 1
                    if self.summon_special_count >= self.max_summon_special:
                        self.common.click(P_TL_BUTTON, after_delay=1.5)
                        return False

                schedule.sleep(.7)
                self.common.click(SUMMON_CONTINUE.center)
            else:
                t.click(P_SPACE, after_delay=.4)

    def sale_servant(self):
        pass

    def synthesis_servant(self):
        pass

    def synthesis_reisou(self):
        pass

    def _handle_summon_option(self):
        # TODO not sure if the settings will be kept after switch account
        pass

    def _find_special(self, t, pos):
        rect = (84 + 187 * (pos % 6 + pos // 6), 187 + 225 * (pos // 6), 258 + 187 * (pos % 6 + pos // 6),
                372 + 225 * (pos // 6))
        for i, j in SUMMON_SPECIAL:
            if p := t.find(j, rect):
                return i, p

import random

import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *
from tksCommon import TksCommon, FlowException

logger = getLogger('TksExpBall')

DFLT_MAX_SYNTHESIS = 5


# some big differences from original ExpBall,
# 1. add servant synthesis
# 2. in burning only sell servants, not dog food or Fou
# 3. reisou synthesis never auto lock star 1 reisous. You have to manually lock + fav some before running.

class TksExpBall:
    def __init__(self, context):
        self.common = TksCommon()
        self.context = context
        self.synthesis_count = 0
        self.summon_special_count = 0
        self.jc = self.context.cur_job_context()
        self.max_synthesis = self.jc.max_synthesis() or DFLT_MAX_SYNTHESIS

    def __call__(self):
        logger.info('ExpBall Start.')
        while self.synthesis_count < self.max_synthesis:
            if not self.summon_fp():
                break
            if not self.jc.disable_burning():
                self.burning()
            else:
                logger.info('burning disabled.')
            
            self.synthesis()
            self.common.back_to_top()
        logger.info('ExpBall End.')

    def synthesis(self):
        self.synthesis_servant()
        num = 0
        while not self.synthesis_reisou(num):
            num+=1
        self.synthesis_count += 1
        logger.info(f'Finished synthesis {self.synthesis_count}')

    def summon_fp(self):
        logger.info('Summon FP Start.')
        self.common.go_menu(B_MAIN_SUMMON.center)
        while True:
            t = TksDetect().cache
            if TksDetect().appear(IMG.TKS_BG_FP, A_CENTER_BG):
                break
            elif p := self.common.find_dialog_close(t):
                t.click(p, after_delay=.8)
            self.common.click(P_SUMMON_SWITCH, after_delay=2)
        self.common.click(P_SUMMON_SUMMON, after_delay=1)

        while not self.jc.max_summon() or self.jc.summon_count < self.jc.max_summon():
            t = TksDetect()
            if t.appear_btn(B_SUMMON_AUTO_SALE):
                if not self.jc.summon_option_checked:
                    self._handle_summon_option()
                    self.jc.summon_option_checked = True
                self.jc.summon_count += 1
                logger.info(f'Summon {self.jc.summon_count}.')
                t.click(B_SUMMON_SUBMIT.center, after_delay=3)
            elif t.find_btn(B_SUMMON_SALE):
                logger.info('Full. Exit this round of summon.')
                return True
            elif t.appear_btn(B_SUMMON_CONTINUE):
                for i in range(10):
                    if s := self._find_special(t, i):
                        logger.info(f'Summon special found: {s[0]}')
                        if not self._handle_summon_special(s[0], s[1]):
                            return False
                    else:
                        continue
                schedule.sleep(.7)
                self.common.click(B_SUMMON_CONTINUE.center)
            else:
                t.click(P_SPACE, after_delay=.4)

    def burning(self):
        logger.info('Burning start.')
        if TksDetect().appear_btn(B_SUMMON_SALE):
            self.common.click(B_SUMMON_SALE.center, 3) \
                .wait_btn(B_SELECT_FINISH)
        else:
            self.common.back_to_top() \
                .go_menu(P_MENU_SHOP) \
                .scroll_and_click(IMG.TKS_MENU_BURNING, A_SUB_MENUS) \
                .wait_btn(B_SELECT_FINISH)

        logger.info('Burn servants.')
        self.common.click(P_SELECT_SERVANT)
        if not self.jc.servant_burning_checked:
            self._handle_servant_burning_option()
            self.jc.servant_burning_checked = True
        self._burn_all()
 
        if not self.jc.reisou_burn_min_star() or self.jc.reisou_burn_min_star() <=3:
            logger.info('Burn reisou.')
            self.common.click(P_SELECT_REISOU)
            if not self.jc.reisou_burning_checked:
                self._handle_reisou_burning_option()
                self.jc.reisou_burning_checked = True
            self._burn_all()

        logger.info('Burn command codes.')
        self.common.click(P_SELECT_CODE)
        burn = True
        if not self.jc.code_burning_checked:
            if self._handle_code_burning_option():
                self.jc.code_burning_checked = True
            else:
                burn = False
        if burn:
            self._burn_all()

        logger.info('Burning end.')

    def synthesis_servant(self):
        logger.info('Synthesis servant Start.')
        self.common.back_to_top() \
            .go_menu(P_MAIN_SYNTHESIS) \
            .click(P_SCROLL_TOP, .7) \
            .click(P_SYNTHESIS_SERVANT, 3) \
            .wait_btn(B_SYNTHESIS_LOAD)

        offset_x = 60
        while True:
            self.common.click(B_SYNTHESIS_LOAD.center, 3)
            if not self.jc.synthesis_servant_checked:
                self._handle_synthesis_servant_option()
                self.jc.synthesis_servant_checked = True

            self.common.click(B_SELECT_LOCK.offset(offset_x, 0).center, after_delay=2)
            if TksDetect().appear_btn(B_SYNTHESIS_BTN_DISABLED):
                logger.info("Servant selected.")
            else:
                logger.warning('Unable to select servant for synthesis')
                return

            self.common.click(P_SYNTHESIS_ENTER, 1) \
                .wait(B_SELECT_FINISH.img, A_BR_BUTTONS)

            if not self.jc.synthesis_servant_food_checked:
                self._handle_synthesis_servant_food_option()
                self.jc.synthesis_servant_food_checked = True

            while True:
                if not self._select_food_and_synthesis():
                    return
                if TksDetect().appear(IMG.TKS_SERVANT_LEVEL_MAX, A_SERVANT_LEVEL_MAX_NOTICE):
                    logger.warning('Exp full for this servant')
                    offset_x = 193
                    break
                elif TksDetect.cache.find_and_click(IMG.TKS_CROSS, A_TR_BUTTONS):
                    pass
                self.common.click(P_SYNTHESIS_ENTER) \
                    .wait(B_SELECT_FINISH.img, A_BR_BUTTONS)

    def synthesis_reisou(self, num):
        logger.info('Synthesis reisou Start.')
        self.common.back_to_top() \
            .go_menu(P_MAIN_SYNTHESIS) \
            .click(P_SCROLL_TOP, .7) \
            .click(P_SYNTHESIS_SYNTHESIS, after_delay=3) \
            .wait_and_click_btn(B_SYNTHESIS_LOAD, after_delay=3)

        if not self.jc.synthesis_reisou_checked:
            self._handle_synthesis_reisou_option()
            self.jc.synthesis_reisou_checked = True

        for i in range(3):
            if num > 0 or random.randint(0,1) == 1:
                pos = self._find_first_locked_reisou()
            else:
                pos = self._find_last_locked_reisou()
            if pos:
                break
            schedule.sleep(2)
        if not pos:
            raise FlowException('No reisou for synthesis.')

        logger.info(f'Found reisou for synthesis {pos}.')
        self.common.click(pos, offset=(60, 0), after_delay=1.5) \
            .wait_btn(B_BACK) \
            .click(P_SYNTHESIS_ENTER, 1) \
            .wait_btn(B_SELECT_FINISH)

        if not self.jc.synthesis_reisou_food_checked:
            self._handle_synthesis_reisou_food_option()
            self.jc.synthesis_reisou_food_checked = True

        while True:
            if not self._select_food_and_synthesis():
                return True
            if TksDetect().appear_btn(B_SYNTHESIS_LOAD):
                logger.warning('ExpBall Created')
                return False
            self.common.click(P_SYNTHESIS_ENTER) \
                .wait_btn(B_SELECT_FINISH)

    def _handle_summon_option(self):
        self.common.click(B_SUMMON_AUTO_SALE.center) \
            .wait(IMG.TKS_DIALOG_DECIDE, A_DIALOG_BUTTONS)
        t = TksDetect()
        if self.jc.exp_only():
            t.find_and_click(B_FILTER_STAR_1_OFF.img, A_SUMMON_OPTION_EXP, threshold=0.01)
            t.find_and_click(B_FILTER_STAR_2_OFF.img, A_SUMMON_OPTION_EXP, threshold=0.01)
            t.find_and_click(B_FILTER_STAR_3_OFF.img, A_SUMMON_OPTION_EXP, threshold=0.01)
            t.find_and_click(B_FILTER_STAR_1_OFF.img, A_SUMMON_OPTION_FOU, threshold=0.015)
            t.find_and_click(B_FILTER_STAR_2_OFF.img, A_SUMMON_OPTION_FOU, threshold=0.015)
            t.find_and_click(B_FILTER_STAR_3_OFF.img, A_SUMMON_OPTION_FOU, threshold=0.015)
            t.find_and_click(B_FILTER_STAR_1_OFF.img, A_SUMMON_OPTION_REISOU, threshold=0.015)
            t.find_and_click(B_FILTER_STAR_2_OFF.img, A_SUMMON_OPTION_REISOU, threshold=0.015)
            t.find_and_click(B_FILTER_STAR_3_OFF.img, A_SUMMON_OPTION_REISOU, threshold=0.015)
        else:
            t.find_and_click(B_FILTER_STAR_1_OFF.img, A_SUMMON_OPTION_EXP, threshold=0.01)
            t.find_and_click(B_FILTER_STAR_2_OFF.img, A_SUMMON_OPTION_EXP, threshold=0.01)
            t.find_and_click(B_FILTER_STAR_3_OFF.img, A_SUMMON_OPTION_EXP, threshold=0.01)
            t.find_and_click(B_FILTER_STAR_1_OFF.img, A_SUMMON_OPTION_FOU, threshold=0.015)
            t.find_and_click(B_FILTER_STAR_2_OFF.img, A_SUMMON_OPTION_FOU, threshold=0.015)
            t.find_and_click(B_FILTER_STAR_3_ON.img, A_SUMMON_OPTION_FOU, threshold=0.015)
            t.find_and_click(B_FILTER_STAR_1_OFF.img, A_SUMMON_OPTION_REISOU, threshold=0.015)
            t.find_and_click(B_FILTER_STAR_2_ON.img, A_SUMMON_OPTION_REISOU, threshold=0.015)
            t.find_and_click(B_FILTER_STAR_3_ON.img, A_SUMMON_OPTION_REISOU, threshold=0.015)

        t.find_and_click(IMG.TKS_DIALOG_DECIDE, A_DIALOG_BUTTONS)

    def _handle_sort_option(self, fav=True):
        while not TksDetect().appear_btn(B_SORT_FILTER_ON):
            self.common.click(B_SORT_FILTER_ON.center, 1)
        if fav:
            while not TksDetect().appear_btn(B_SORT_FAV_ON):
                self.common.click(B_SORT_FAV_ON.center, 1)
        self.common.click(P_SORT_SUBMIT, 1)
        while not TksDetect().appear_btn(B_SORT_DEC):
            self.common.click(B_SORT_DEC.center, 1)

    def _select_food_and_synthesis(self):
        logger.info(f'Selected all food.')
        self._select_all()
        if TksDetect().appear(B_SELECT_FINISH.img, A_BR_BUTTONS):
            logger.info(f'No food any more.')
            return False
        # trick here, although the pos of servant B_SELECT_FINISH is different, the center still can be clicked
        self.common.click(B_SELECT_FINISH.center, 1) \
            .click(B_SELECT_FINISH.center, .5) \
            .click(B_SUMMON_SUBMIT.center, .8) \
            .click(B_SUMMON_SUBMIT.center, 2)
        while not TksDetect().appear_btn(B_BACK):
            self.common.click(P_SPACE, .5)
        return True

    def _handle_synthesis_reisou_option(self):
        logger.info('Handle systhesis reisou option')
        while not TksDetect().appear_btn(B_SELECT_GIRD):
            self.common.click(B_SELECT_GIRD.center, 2)
        self.common.click(P_FILTER_FILTER, 1) \
            .click(P_FILTER_RESET, .7) \
            .click(P_OPTIONS_SCROLL_START, .7) \
            .click(B_FILTER_STAR_1_OFF.center, .7) \
            .click(B_FILTER_SUBMIT.center, 1) \
            .click(P_SORT_SORT, 1) \
            .click(P_SORT_BYLEVEL, .7)
        self._handle_sort_option()

    def _handle_synthesis_reisou_food_option(self):
        logger.info('Handle systhesis reisou food option')
        while not TksDetect().appear_btn(B_SELECT_GIRD):
            self.common.click(B_SELECT_GIRD.center, 2)
        self.common.click(P_FILTER_FILTER, 1) \
            .click(P_FILTER_RESET, .7) \
            .click(P_OPTIONS_SCROLL_START, .7) \
            .click(B_FILTER_STAR_1_OFF.center, .7) \
            .click(B_FILTER_STAR_2_OFF.center, .7) \
            .click(B_FILTER_SUBMIT.center, 1) \
            .click(P_SORT_SORT, 1) \
            .click(P_SORT_BYRANK, .7)
        self._handle_sort_option()

    def _handle_synthesis_servant_option(self):
        logger.info('Handle systhesis servant option')
        while not TksDetect().appear_btn(B_SELECT_GIRD):
            self.common.click(B_SELECT_GIRD.center, 2)
        self.common.click(P_FILTER_FILTER, 1) \
            .click(P_FILTER_RESET, .7) \
            .click(P_OPTIONS_SCROLL_START, .7) 
        self.common.scroll_and_click(IMG.TKS_NOT_MAX_LEVEL, A_OPTIONS_LEFT_BTNS, end_pos=P_OPTIONS_SCROLL_END, 
                                     max_swipe=10, top_pos=P_OPTIONS_SCROLL_START, scroll_area=A_SWIPE_CENTER_DOWN_S)
        #     .click(P_OPTIONS_SCROLL_START, .7) 
        #     .click(P_OPTIONS_SCROLL_SECTION1, .7) \
        #     .click(P_NOT_MAX_LEVEL, .7) \
        self.common.click(B_FILTER_SUBMIT.center, 1) \
            .click(P_SORT_SORT, 1) \
            .click(P_SORT_BYLEVEL, .7)
        self._handle_sort_option(False)

    def _handle_synthesis_servant_food_option(self):
        logger.info('Handle systhesis servant food option')
        while not TksDetect().appear_btn(B_SELECT_GIRD):
            self.common.click(B_SELECT_GIRD.center, 2)
        self.common.click(P_FILTER_FILTER, 1) \
            .click(P_FILTER_RESET, .7) \
            .click(P_OPTIONS_SCROLL_START, .7) \
            .click(P_OPTIONS_SCROLL_SECTION1, .7)
            # .click(P_SERVANT_OPTION_EXP, .7) \
            # .click(P_SERVANT_OPTION_FOU, .7) \
        self.common.click(B_FILTER_SUBMIT.center, 1) \
            .click(P_SORT_SORT, 1) \
            .click(P_SORT_BYLEVEL, .7)
        self._handle_sort_option()

    def _handle_servant_burning_option(self):
        logger.info('Handle servant burning option')
        while not TksDetect().appear_btn(B_SELECT_GIRD):
            self.common.click(B_SELECT_GIRD.center, 2)
        self.common.click(P_FILTER_FILTER, 1) \
            .click(P_FILTER_RESET, .7) \
            .click(P_OPTIONS_SCROLL_START, .7)
        self.common.scroll_and_click(IMG.TKS_SERVANT_SELECT, A_OPTIONS_LEFT_BTNS, end_pos=P_OPTIONS_SCROLL_END, 
                                     max_swipe=10, threshold=.02, top_pos=P_OPTIONS_SCROLL_START, scroll_area=A_SWIPE_CENTER_DOWN_S)         
        self.common.click(B_FILTER_SUBMIT.center, 1) \
            .click(P_SORT_SORT, 1) \
            .click(P_SORT_BYLEVEL, .7)
        self._handle_sort_option()

    def _handle_reisou_burning_option(self):
        logger.info('Handle reisou burning option')
        while not TksDetect().appear_btn(B_SELECT_GIRD):
            self.common.click(B_SELECT_GIRD.center, 3)
        self.common.click(P_FILTER_FILTER, 1) \
            .click(P_FILTER_RESET, .7) \
            .click(P_OPTIONS_SCROLL_START, .7) 
        if not self.jc.reisou_burn_min_star() or self.jc.reisou_burn_min_star() <= 3: 
            self.common.click(B_FILTER_STAR_3_OFF.center, .7)
        if self.jc.reisou_burn_min_star() and self.jc.reisou_burn_min_star() <= 2: 
            self.common.click(B_FILTER_STAR_2_OFF.center, .7)
        if self.jc.reisou_burn_min_star() and self.jc.reisou_burn_min_star() <= 1: 
            self.common.click(B_FILTER_STAR_1_OFF.center, .7)
        self.common.click(B_FILTER_SUBMIT.center, 1)

    def _handle_code_burning_option(self):
        logger.info('Handle command code burning option')
        while not TksDetect().appear_btn(B_SELECT_GIRD):
            self.common.click(B_SELECT_GIRD.center, 3)
        self.common.click(P_FILTER_FILTER, 1) \
            .click(P_FILTER_RESET, .7) \
            .click(P_OPTIONS_SCROLL_START, .7) \
            .click(B_FILTER_STAR_1_OFF.center, .7)
        if self.jc.code_burn_max_star() and self.jc.code_burn_max_star() >= 2:
            self.common.click(B_FILTER_STAR_2_OFF.center, .7)
        if TksDetect().appear_btn(B_FILTER_NOT_EXIST):
            self.common.click(P_FILTER_CANCEL, .7)
            return False
        else:
            self.common.click(B_FILTER_SUBMIT.center, 1)
            return True

    def _handle_summon_special(self, name, pos):
        self.common.click(pos, after_delay=1.5)
        # self.common.click_and_wait(s[1], IMG.TKS_FAV, A_LEFT_BUTTONS, interval=2)
        self.common.handle_special_drop(TksDetect(), self.context)
        if self.jc.target_summon_special():
            if name == self.jc.target_summon_special():
                self.summon_special_count += 1
        else:
            self.summon_special_count += 1
        if self.jc.max_summon_special() and self.summon_special_count >= self.jc.max_summon_special():
            self.common.click(P_TL_BUTTON, after_delay=1.5)
            return False
        return True

    def _find_first_locked_reisou(self):
        t = TksDetect()
        for i, j in ((i, j) for i in range(4) for j in range(7)):
            btn = B_SELECT_LOCK.offset(133 * j, 142 * i)
            if t.appear_btn(btn):
                return btn.center
        return None

    def _find_last_locked_reisou(self):
        prev = None
        t = TksDetect()
        for i, j in ((i, j) for i in range(4) for j in range(7)):
            btn = B_SELECT_LOCK.offset(133 * j, 142 * i)
            if not t.appear_btn(btn):
                break
            prev = btn.center
        return prev

    def _select_all(self):
        for i, j in ((i, j) for i in range(4) for j in range(7)):
            self.common.click((133 + 133 * j, 253 + 142 * i), after_delay=.15)
        schedule.sleep(1)

    def _burn_all(self):
        while True:
            logger.info('burn all')
            self._select_all()
            if TksDetect().appear_btn(B_SELECT_FINISH):
                break
            self.common.click(B_SELECT_FINISH.center, 1) \
                .click(P_SORT_SUBMIT, 1) \
                .wait_and_click_btn(B_SELL_RESULT, after_delay=1) \
                .wait_btn(B_SELECT_FINISH)

    def _find_special(self, t, pos):
        rect = (84 + 187 * (pos % 6 + pos // 6), 187 + 225 * (pos // 6), 258 + 187 * (pos % 6 + pos // 6),
                372 + 225 * (pos // 6))
        for i, j in SUMMON_SPECIAL:
            if p := t.find(j, rect):
                return i, p

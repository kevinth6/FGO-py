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


# flag bits (from right to left):
# 1 : could be on map
# 2 : could be on instance menu
# 3 : could be on rewards
# 4 : could go to battle
# 5 : could have pre dialog
# 6 : could have post dialog
# 7 : could have AP dialog
# 8 : could go to story


class TksCampaign:
    def __init__(self, context, include_main=True):
        self.common = TksCommon()
        self.context = context
        self.free_instances = []
        self.scanned_instances = []

    def __call__(self):
        self.common.click(P_CUR_CAMPAIGN, after_delay=1)
        if self.include_main:
            ret = self._run_main_tasks()
        if ret:
            ret = self._run_first_free()
        if ret:
            ret = self._run_regular_free()
        return ret

    def _run_main_tasks(self):
        flag = 0b0000011
        logger.info('Main tasks running start')
        while True:
            t = TksDetect(.5, .5).cache
            if flag & 0x1 and t.is_on_map():
                if p := t.find(IMG.TKS_REWARD_AVAILABLE, A_TOP_RIGHT, threshold=.02):
                    logger.info('Found available rewards. Go to reward view.')
                    t.click(p)
                    flag = 0b00000100
                elif len(ps := t.find_multiple(IMG.TKS_CAMPAIGN_NEXT, threshold=.1)) > 0:
                    if self._iterate_map_tasks(ps):
                        flag = 0b11011000
                    else:
                        logger.info('Iterated all tasks on map. Nothing to do.')
                        if TksDetect().is_on_menu():
                            self.common.click(P_TL_BUTTON)
                        break
            elif flag & 0x2 and t.is_on_menu():
                if len(ps := t.find_multiple(IMG.TKS_CAMPAIGN_NEXT, threshold=.1)) > 0 \
                        and self._iterate_menu_tasks(ps):
                    flag = 0b11011000
                else:
                    logger.info("On menu but nothing to do. ")
                    t.click(P_TL_BUTTON)
                    flag = 0b00000001
            elif flag & 0x4 and t.is_on_shop():
                self._handle_rewards()
                flag = 0b00000001
            elif flag & 0x8 and t.appear(IMG.TKS_CHOOSE_FRIEND, A_TOP_RIGHT):
                TksBattleGroup(self.context, True)()
                flag = 0b10100111
            elif flag & 0x10:
                if p := t.find(IMG.TKS_CAMPAIGN_BEGIN, A_DIALOG_BUTTONS):
                    logger.info('click task begin')
                    t.click(p)
                elif p := t.find(IMG.TKS_DIALOG_BEGIN, A_DIALOG_BUTTONS):
                    logger.info('click begin')
                    t.click(p)
                flag = 0b11111111
            else:
                flag = self._check_misc_flow(flag, t)
                if not flag:
                    return False

        logger.info('Main tasks running exit.')
        return True

    def _check_misc_flow(self, flag, t):
        if flag & 0x40 and t.isApEmpty():
            logger.info('AP empty.')
            if not self.common.eat_apple(self.context):
                logger.info('Exit due to no AP.')
                return None
            else:
                return 0b11111111
        elif flag & 0x20:
            if self.common.handle_special_drop(t):
                return 0b10100111
        elif p := self.common.find_dialog_close(t):
            logger.info('close dialog on ' + str(p))
            t.click(p)
        elif t.is_on_top():
            logger.info("Unexpected back to top. ")
            return None
        elif flag & 0x80 and self.common.skip_possible_story():
            return 0b10111111
        else:
            fgoDevice.device.perform('\xBB', (800,))

        return flag

    def _run_first_free(self):
        self.scanned_instances.clear()
        self.common.swipe_on_map_and_do(lambda t, st: self._scan_free(t, st, self._find_first_free))
        print(len(self.free_instances))

    def _run_regular_free(self):
        pass

    def _click_task_in_menu(self, pos):
        # task could be unavailable due to the prerequisite not satisfied
        a = (pos[0] - 70, pos[1] - 100, pos[0] + 70, pos[1] + 100)
        for times in range(0, 3):
            fgoDevice.device.touch(self._clickable_pos_under_next(pos))
            schedule.sleep(.8)
            if not TksDetect().appear(IMG.TKS_CAMPAIGN_NEXT, a, threshold=.1):
                TksDetect.cache.save()
                print("True")
                return True
        return False

    def _clickable_pos_under_next(self, pos):
        return pos[0], pos[1] + 80

    def _iterate_map_tasks(self, ps):
        logger.info('Iterate map tasks.')
        idx = 0
        while idx < len(ps):
            logger.info(f'Pick task: {idx}, pos: {ps[idx]}')
            pos = self._clickable_pos_under_next(ps[idx])
            if self.common.click_and_wait_for_menu_view(pos, interval=.7):
                if self.common.scroll_and_find_func(lambda t, i: self._iterate_menu_tasks()):
                    return True
                else:
                    self.common.click(P_TL_BUTTON, 1)
            else:
                logger.info("Can't open section menu.")

            idx += 1
        if idx == len(ps):
            return False

    def _iterate_menu_tasks(self):
        logger.info('Iterate menu tasks.')
        ps = TksDetect.cache.find_multiple(IMG.TKS_CAMPAIGN_NEXT, threshold=.1)
        idx = 0
        while idx < len(ps):
            if self._click_task_in_menu(ps[idx]):
                logger.info(f'Found runnable task: {idx}')
                return True
            else:
                logger.info(f'No response after clicking task: {idx}')
                idx += 1

        logger.info('No available menu tasks')
        return False

    def _handle_rewards(self):
        logger.info('Handle campaign rewards')
        while True:
            t = TksDetect(.2, .5).cache
            if t.appear(IMG.TKS_CAMPAIGN_REWARD_ON, A_CAMPAIGN_REWARD_TABS, threshold=.01):
                if t.appear(IMG.TKS_REWARD_READY, A_CAMPAIGN_REWARD_VIEWS):
                    if p := t.find(IMG.TKS_REWARD_COMPLETED, A_CAMPAIGN_REWARD_1ST_READY):
                        logger.info('Find ready reward. Get it.')
                        t.click(p, after_delay=.7)
                    else:
                        logger.info('No ready reward any more.')
                        t.click(P_TL_BUTTON, after_delay=.7)
                        break
                else:
                    t.click(P_CAMPAIGN_REWARD_VIEW, after_delay=.7)
            elif p := t.find(IMG.TKS_CAMPAIGN_REWARD_OFF, A_CAMPAIGN_REWARD_TABS):
                logger.info('Not in reward view. Go to reward view')
                t.click(p, after_delay=.7)
            elif self.common.handle_special_drop(t):
                pass
            elif p := self.common.find_dialog_close(t):
                t.click(p, after_delay=.7)
            else:
                fgoDevice.device.perform('\xBB', (700,))

    def _scan_free(self, t, st, find_func):
        logger.info(f'iterate first free sections on map. screen: {st}')
        if len(ps := t.find_multiple(IMG.TKS_FREE_MARK_S, threshold=.1)) > 0:
            idx = 0
            while idx < len(ps):
                logger.info(f'Find section: {idx}, pos: {ps[idx]}')
                if self.common.click_and_wait_for_menu_view(ps[idx], (-20, 0)):
                    func = (lambda t, i: find_func(t, st, ps[idx], i))
                    self.common.scroll_and_find_func(func)
                    self.common.click(P_TL_BUTTON, 1)
                else:
                    logger.info("Can't open section menu.")
                idx += 1

    def _find_first_free(self, t, map_screen, map_pos, menu_scroll):
        ret = False
        ret = self._find_free_instance(t, IMG.TKS_INSTANCE_BRONZE, map_screen, map_pos, menu_scroll, 1) or ret
        ret = self._find_free_instance(t, IMG.TKS_INSTANCE_SILVER, map_screen, map_pos, menu_scroll, 2) or ret
        ret = self._find_free_instance(t, IMG.TKS_INSTANCE_GOLD, map_screen, map_pos, menu_scroll, 3) or ret
        # ret = self._find_free_instance(t, IMG.TKS_INSTANCE_GREEN, map_screen, map_pos, menu_scroll, 4) or ret
        return ret

    def _find_free_instance(self, t, img, map_screen, map_pos, menu_scroll, level):
        for mp in t.find_multiple(img, A_CAMPAIGN_INSTANCE_REWARD):
            logger.info(f'Found instance in menu. level: {level}, scroll: {menu_scroll}, pos:{mp}')
            mp_ab = (mp[0] + A_CAMPAIGN_INSTANCE_REWARD[0], mp[1] + A_CAMPAIGN_INSTANCE_REWARD[1])
            cls = self._detect_cls(t, mp_ab)
            if self._instance_scanned(t, mp_ab, level, cls):
                logger.info(f'Instance already scanned.')
            else:
                instance = FreeInstance(map_screen, map_pos, menu_scroll, mp, level, cls)
                self.free_instances.append(instance)
                logger.info(f'Instance added {instance}')
        return False

    def _instance_scanned(self, t, new_pos, level, cls):
        rect = t.surround((new_pos[0] - 274, new_pos[1] - 61), 180, 20)
        for instance in self.scanned_instances:
            if instance[1] == level and instance[2] == cls and t.appear(instance[0], t.expand(rect, 2), threshold=.003):
                return True
        self.scanned_instances.append(([t._crop(rect), None], level, cls))
        return False

    def _detect_cls(self, t, pos_reward):
        area = (pos_reward[0] + 24, pos_reward[1] - 65, pos_reward[0] + 104, pos_reward[1] + 15)
        ret = None
        for cls in CLASSES_S:
            if t.appear(CLASSES_S[cls], area):
                if ret:
                    # more than one class found
                    return None
                ret = cls
        return ret


class FreeInstance:
    def __init__(self, map_screen, map_pos, menu_scroll, menu_pos, level, cls):
        self.map_screen = map_screen
        self.map_pos = map_pos
        self.menu_scroll = menu_scroll
        self.menu_pos = menu_pos
        self.level = level  # 1 bronze, 2 silver, 3 gold, 4 green
        self.cls = cls  #

    def __repr__(self):
        return f"FreeInstance(map_screen:{self.map_screen}, map_pos:{self.map_pos}, menu_scroll:{self.menu_scroll}, " \
               f"menu_pos:{self.menu_pos}, level:{self.level}, cls:{self.cls})"

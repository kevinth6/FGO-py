import math
import random

import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *
from tksCommon import TksCommon, FlowException, safe_get
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
    def __init__(self, context):
        self.common = TksCommon()
        self.context = context
        self.regular_free = []
        self.first_free = []
        self.scanned_instances = []
        self.scanned_sections = []

    def __call__(self, skip_main=False):
        self.common.click(P_CUR_CAMPAIGN, after_delay=1)
        cjc = self.context.cur_job_config()
        if not skip_main:
            skip_main = ('skipMain' in cjc) and cjc['skipMain']
        ret = True
        if not skip_main:
            ret = self._run_main_tasks()
        else:
            logger.info('Main task skipped on required.')

        if ret:
            ret = self._run_free()
        return ret

    def _run_main_tasks(self):
        flag = 0b0000011
        logger.info('Main tasks running start')
        while True:
            t = TksDetect(.3, .5).cache
            if flag & 0x4 and t.is_on_shop():
                self._handle_rewards()
                flag = 0b00000011
            elif flag & 0x8 and t.appear(IMG.TKS_CHOOSE_FRIEND, A_TOP_RIGHT):
                TksBattleGroup(self.context, True)()
                flag = 0b10100111
            elif flag & 0x10 and t.find_and_click(IMG.TKS_CAMPAIGN_BEGIN, A_DIALOG_BUTTONS):
                logger.info('click task begin')
                flag = 0b11111111
            elif flag & 0x10 and t.find_and_click(IMG.TKS_DIALOG_BEGIN, A_DIALOG_BUTTONS):
                logger.info('click begin')
                flag = 0b11111111
            elif flag & 0x40 and t.isApEmpty():
                logger.info('AP empty.')
                if not self.common.eat_apple(self.context):
                    logger.info('Exit due to no AP.')
                    return False
                else:
                    flag = 0b11111111
            elif flag & 0x20 and self.common.handle_special_drop(t):
                flag = 0b10100111
            elif p := self.common.find_dialog_close(t):
                logger.info('close dialog on ' + str(p))
                t.click(p)
            elif flag & 0x1 and t.is_on_map():
                if p := t.find(IMG.TKS_REWARD_AVAILABLE, A_TOP_RIGHT, threshold=.02):
                    logger.info('Found available rewards. Go to reward view.')
                    t.click(p)
                    flag = 0b00000101
                else:
                    ret = self._iterate_map_tasks(t)
                    if ret:
                        flag = 0b11011000
                    else:
                        # go back and forth to find the task
                        if f := self._back_and_forth_find_task(t):
                            flag = f
                        else:
                            break
            elif flag & 0x2 and t.is_on_menu():
                if self._iterate_menu_tasks():
                    flag = 0b11011000
                else:
                    logger.info("On menu but nothing to do. ")
                    t.click(P_TL_BUTTON)
                    flag = 0b00000011
            elif t.is_on_top():
                logger.info("Unexpected back to top. ")
                return False
            elif flag & 0x80 and (p := t.find(IMG.TKS_OPTION_STUCK)):
                t.click(p)
            elif flag & 0x80 and self.common.skip_possible_story():
                flag = 0b10111111
            else:
                fgoDevice.device.perform('\xBB', (800,))

        logger.info('Main tasks running exit.')
        return True

    def _run_free(self):
        logger.info('Free instances running start.')
        self.scanned_instances.clear()
        self.scanned_sections.clear()
        self.first_free.clear()
        self.regular_free.clear()
        while not TksDetect().is_on_map():
            TksDetect().cache.find_and_click_btn(B_MAIN_TL_CLOSE, after_delay=1)

        self.common.swipe_on_map_and_do(lambda t, st: self._scan_free_instances(t, st))
        logger.info(f'Instance scanned. first free: {len(self.first_free)}, regular free: {len(self.regular_free)}')

        ret = True
        for instance in self.first_free:
            logger.info(f'Run first free instance: {instance}')
            if not self._run_free_instance(instance):
                ret = False
                break
        if not ret:
            return ret

        self.regular_free = self.regular_free + self.first_free
        bak_instances = []
        while True:
            idx = random.randint(0, len(self.regular_free) - 1)
            instance = self.regular_free.pop(idx)
            bak_instances.append(instance)
            logger.info(f'Run regular free instance, idx: {idx}, instance: {instance}')
            if not self._run_free_instance(instance):
                ret = False
                break

            if len(self.regular_free) == 0:
                self.regular_free = self.regular_free + bak_instances
                bak_instances.clear()

        logger.info('Free instances running exit.')
        return ret

    def _back_and_forth_find_task(self, t):
        logger.info('Go back and forth to find a task')
        self.common.back_to_top()
        self.common.click(P_CUR_CAMPAIGN, after_delay=1)
        while not TksDetect(.5, .5).is_on_map():
            pass
        schedule.sleep(1.5)

        if p := t.find(IMG.TKS_REWARD_AVAILABLE, A_TOP_RIGHT, threshold=.02):
            logger.info('Found available rewards. Go to reward view.')
            t.click(p)
            return 0b00000101

        ret = self._iterate_map_tasks(t)
        if ret:
            return 0b11011100
        elif ret is None:
            logger.info('Click center to find a task')
            if self.common.click_and_wait_for_menu_view(P_CENTER, interval=.7, max_times=3):
                if self.common.scroll_and_find(lambda t, i: self._iterate_menu_tasks()):
                    return 0b11011100
                else:
                    self.common.click(P_TL_BUTTON, 1)
            else:
                logger.info("Can't open section menu.")
        return None

    def _run_free_instance(self, instance):
        """return False means stop running following. True means continue."""
        cf = self.context.cur_job_config()
        if not instance.first and (('level' in cf) and cf['level'] != instance.level
                                   or ('cls' in cf) and cf['cls'] != instance.cls):
            logger.info(f'Instance not wanted. level:{instance.level}, cls:{instance.cls}')
            return True

        t = TksDetect().cache
        if not t.is_on_map():
            t.find_and_click_btn(B_MAIN_TL_CLOSE, after_delay=1)

        logger.info(f'Go on map and menu. ')
        self.common.go_on_map_and_menu(instance.map_screen, instance.map_pos, instance.menu_scroll,
                                       instance.menu_pos)
        if TksDetect().is_on_map():
            logger.info("Still on map. Unexpected. skip this instance.")
            return True
        return self._run_instance()

    def _run_instance(self):
        logger.info(f'Start instance running.')
        flag = 0b11011000
        while True:
            t = TksDetect().cache
            if flag & 0x8 and t.appear(IMG.TKS_CHOOSE_FRIEND, A_TOP_RIGHT):
                TksBattleGroup(self.context, True)()
                flag = 0b10100111
            elif flag & 0x40 and t.isApEmpty():
                logger.info('AP empty.')
                if not self.common.eat_apple(self.context):
                    logger.info('Exit due to no AP.')
                    return False
                else:
                    flag = 0b11111111
            elif flag & 0x20 and self.common.handle_special_drop(t):
                flag = 0b10100111
            elif p := self.common.find_dialog_close(t):
                logger.info('close dialog on ' + str(p))
                t.click(p)
            elif flag & 0x1 and t.is_on_map():
                logger.info('On map.')
                return True
            elif flag & 0x2 and t.is_on_menu():
                logger.info('On menu, back')
                self.common.click(P_TL_BUTTON)
                flag = 0b00000011
            elif t.is_on_shop():
                logger.info('On shop, unexpected, back')
                self.common.click(P_TL_BUTTON)
                flag = 0b00000001
            elif flag & 0x80 and self.common.skip_possible_story():
                flag = 0b10111111
            else:
                fgoDevice.device.perform('\xBB', (800,))

    def _click_task_in_menu(self, pos):
        # task could be unavailable due to the prerequisite not satisfied
        a = (pos[0] - 70, pos[1] - 100, pos[0] + 70, pos[1] + 100)
        for times in range(0, 3):
            fgoDevice.device.touch(self._clickable_pos_under_next(pos))
            schedule.sleep(.8)
            if not TksDetect().appear(IMG.TKS_CAMPAIGN_NEXT, a, threshold=.1):
                return True
        return False

    def _clickable_pos_under_next(self, pos):
        return pos[0], pos[1] + 80

    def _iterate_map_tasks(self, t):
        logger.info('Iterate map tasks.')
        ps = t.find_multiple(IMG.TKS_CAMPAIGN_NEXT, threshold=.15)
        logger.info(f'Tasks found: {len(ps)}')
        if len(ps) == 0:
            return None
        for p in ps:
            logger.info(f'Pick task: pos: {p}')
            pos = self._clickable_pos_under_next(p)
            if self.common.click_and_wait_for_menu_view(pos, interval=.7):
                if self.common.scroll_and_find(lambda t, i: self._iterate_menu_tasks()):
                    return True
                else:
                    self.common.click(P_TL_BUTTON, 1)
            else:
                logger.info("Can't open section menu.")
        logger.info('Iterated all tasks on map.')
        return False

    def _iterate_menu_tasks(self):
        logger.info('Iterate menu tasks.')
        ps = TksDetect.cache.find_multiple(IMG.TKS_CAMPAIGN_NEXT, threshold=.1)
        idx = 0
        while idx < len(ps):
            if self._click_task_in_menu(ps[idx]):
                logger.info(f'Found runnable task, pos: {ps[idx]}')
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
                        t.click(P_CAMPAIGN_REWARD_VIEW, after_delay=.7)
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
            elif t.is_on_map() or t.is_on_top():
                break
            elif not t.is_on_shop():
                logger.info('Not on shop, exit.')
                t.click(P_TL_BUTTON, after_delay=.7)
            else:
                t.click(P_CAMPAIGN_REWARD_VIEW, after_delay=.7)

    def _scan_free_instances(self, t, st):
        logger.info(f'Scan free sections on map. screen: {st}')
        if len(ps := t.find_multiple(IMG.TKS_FREE_MARK_S, threshold=.1)) > 0:
            idx = 0
            while idx < len(ps):
                if self._section_scanned(t, ps[idx]):
                    logger.info(f'Section already scanned. {ps[idx]}')
                else:
                    logger.info(f'Find section: {idx}, pos: {ps[idx]}')
                    if rps := self.common.click_and_wait_for_menu_view(ps[idx], (-20, 0)):
                        func = (lambda t, i: self._find_regular_free(t, st, rps, i))
                        self.common.scroll_and_find(func)
                        self.common.click(P_TL_BUTTON, 1)
                        self._section_add(t, ps[idx])
                    else:
                        logger.info("Can't open section menu.")
                idx += 1

    def _find_regular_free(self, t, map_screen, map_pos, menu_scroll):
        ret = False
        ret = self._find_free_instance(t, IMG.TKS_INSTANCE_BRONZE, map_screen, map_pos, menu_scroll, 1, True) or ret
        ret = self._find_free_instance(t, IMG.TKS_INSTANCE_SILVER, map_screen, map_pos, menu_scroll, 2, True) or ret
        ret = self._find_free_instance(t, IMG.TKS_INSTANCE_GOLD, map_screen, map_pos, menu_scroll, 3, True) or ret

        # ret = self._find_free_instance(t, IMG.TKS_INSTANCE_BRONZE_DONE, map_screen, map_pos, menu_scroll, 1) or ret
        ret = self._find_free_instance(t, IMG.TKS_INSTANCE_SILVER_DONE, map_screen, map_pos, menu_scroll, 2) or ret
        ret = self._find_free_instance(t, IMG.TKS_INSTANCE_GOLD_DONE, map_screen, map_pos, menu_scroll, 3) or ret
        # ret = self._find_free_instance(t, IMG.TKS_INSTANCE_GREEN, map_screen, map_pos, menu_scroll, 4) or ret
        return ret

    def _find_free_instance(self, t, img, map_screen, map_pos, menu_scroll, level, first=False):
        for mp in t.find_multiple(img, A_CAMPAIGN_INSTANCE_REWARD):
            mp_ab = (mp[0] + A_CAMPAIGN_INSTANCE_REWARD[0], mp[1] + A_CAMPAIGN_INSTANCE_REWARD[1])
            cls = self._detect_cls(t, mp_ab)
            if self._instance_scanned_add(t, mp_ab, level, cls):
                logger.info(f'Instance already scanned. level: {level}, scroll: {menu_scroll}, pos:{mp}')
            else:
                instance = FreeInstance(map_screen, map_pos, menu_scroll, mp_ab, level, cls, first)
                logger.info(f'Instance found: {instance}')
                if first:
                    self.first_free.append(instance)
                else:
                    self.regular_free.append(instance)

    def _instance_scanned_add(self, t, new_pos, level, cls):
        rect = t.surround((new_pos[0] - 274, new_pos[1] - 61), 180, 20)
        for instance in self.scanned_instances:
            if instance[1] == level and instance[2] == cls and t.appear(instance[0], t.expand(rect, 2), threshold=.01):
                return True
        self.scanned_instances.append(([t._crop(rect), None], level, cls))
        return False

    def _section_scanned(self, t, new_pos):
        rect = t.surround((new_pos[0] - 50, new_pos[1]), 100, 20)
        for section in self.scanned_sections:
            if t.appear(section, t.expand(rect, 2), threshold=.01):
                return True
        return False

    def _section_add(self, t, new_pos):
        rect = t.surround((new_pos[0] - 50, new_pos[1]), 100, 20)
        self.scanned_sections.append([t._crop(rect), None])

    def _detect_cls(self, t, pos_reward):
        area = (pos_reward[0] + 24, pos_reward[1] - 65, pos_reward[0] + 104, pos_reward[1] + 15)
        ret = None
        for cls in CLASSES_S:
            if t.appear(CLASSES_S[cls], area, threshold=.1):
                if ret:
                    # more than one class found
                    return None
                ret = cls
        return ret


class FreeInstance:
    def __init__(self, map_screen, map_pos, menu_scroll, menu_pos, level, cls, first):
        self.map_screen = map_screen
        self.map_pos = map_pos
        self.menu_scroll = menu_scroll
        self.menu_pos = menu_pos
        self.level = level  # 1 bronze, 2 silver, 3 gold, 4 green
        self.cls = cls  #
        self.first = first

    def __repr__(self):
        return f"FreeInstance(map_screen:{self.map_screen}, map_pos:{self.map_pos}, menu_scroll:{self.menu_scroll}, " \
               f"menu_pos:{self.menu_pos}, level:{self.level}, cls:{self.cls}, first:{self.first})"

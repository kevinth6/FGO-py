import cv2
import numpy
import os

from fgoDetect import XDetectBase, XDetectCN, coroutine, IMG
from fgoDevice import device
from fgoFuse import fuse
from fgoLogging import getLogger
from fgoSchedule import schedule

logger = getLogger('TksDetect')

# Extension of fgoDetect.
# Add detection supported by the images in the interface, accounts, and instance folder
# FGO-ExpBall - fgoDetect merged.

INTERFACES = {
    i[:-4]: (lambda x: (x[..., :3], x[..., 3]))(
        cv2.imread(f'fgoImage/interface/{i}', cv2.IMREAD_UNCHANGED)
    ) for i in os.listdir('fgoImage/interface') if i.endswith('.png')
}

ACCOUNTS = {
    i[:-4]: (lambda x: (x[..., :3], x[..., 3]))(
        cv2.imread(f'fgoImage/accounts/{i}', cv2.IMREAD_UNCHANGED)
    ) for i in os.listdir('fgoImage/accounts') if i.endswith('.png')
}

# load instances
INSTANCES = {}
for i in os.listdir('fgoImage/instance'):
    if not os.path.isdir('fgoImage/instance/' + i):
        continue
    INSTANCES[i] = {'menus': {}, 'sections': {}, 'instances': {}}
    for j in os.listdir('fgoImage/instance/' + i):
        if not j.endswith('.png'):
            continue
        img = (lambda x: (x[..., :3], x[..., 3]))(cv2.imread(f'fgoImage/instance/{i}/{j}', cv2.IMREAD_UNCHANGED))
        j = j[:-4]
        if j.startswith('menu_'):
            INSTANCES[i]['menus'][j[5:]] = img
        if j.startswith('section_'):
            INSTANCES[i]['sections'][j[8:]] = img
        elif j.startswith('instance_'):
            INSTANCES[i]['instances'][j[9:]] = img

# # load class for menu
# CLASSES_S = {
#     i[:-4]: (lambda x: (x[..., :3], x[..., 3]))(
#         cv2.imread(f'fgoImage/class_s/{i}', cv2.IMREAD_UNCHANGED)
#     ) for i in os.listdir('fgoImage/class_s') if i.endswith('.png')
# }

FRIEND_REISOUS = {
    i[:-4]: (lambda x: (x[..., :3], x[..., 3]))(
        cv2.imread(f'fgoImage/friend_reisou/{i}', cv2.IMREAD_UNCHANGED)
    ) for i in os.listdir('fgoImage/friend_reisou') if i.endswith('.png')
}

FRIEND_SERVANTS = {
    i[:-4]: (lambda x: (x[..., :3], x[..., 3]))(
        cv2.imread(f'fgoImage/friend_servant/{i}', cv2.IMREAD_UNCHANGED)
    ) for i in os.listdir('fgoImage/friend_servant') if i.endswith('.png')
}

SUMMON_SPECIAL = [
    (i[:-4], (lambda x: (x[..., :3], x[..., 3]))(
        cv2.imread(f'fgoImage/summon_special/{i}', cv2.IMREAD_UNCHANGED)
    )) for i in os.listdir('fgoImage/summon_special') if i.endswith('.png')
]


def clamp_rect(rect):
    clp = lambda value, minv, maxv: max(min(value, maxv), minv)
    return clp(rect[0], 0, 1280), clp(rect[1], 0, 720), clp(rect[2], 0, 1280), clp(rect[3], 0, 720)


class Button:
    def __init__(self, center, img_name=None, size=(0, 0), threshold=.08, padding=2):
        """size is half of button width and height"""
        self.center = center
        if img_name:
            png = INTERFACES[img_name]
            l_sub = (lambda x: x[center[1] - size[1]:center[1] + size[1], center[0] - size[0]:center[0] + size[0]])
            self.img = (l_sub(png[0]), l_sub(png[1]))
        self.threshold = threshold
        self.rect = (center[0] - size[0] - padding, center[1] - size[1] - padding,
                     center[0] + size[0] + padding, center[1] + size[1] + padding)

    def offset(self, x, y):
        result = Button((self.center[0] + x, self.center[1] + y))
        result.img = self.img
        result.threshold = self.threshold
        result.rect = (self.rect[0] + x, self.rect[1] + y,
                       self.rect[2] + x, self.rect[3] + y)
        return result


class TksDetect(XDetectCN):
    cache = None
    def __init__(self, ante_latency=.1, post_latency=.1):
        schedule.sleep(ante_latency)
        super().__init__()
        fuse.increase()
        schedule.sleep(post_latency)
        self.device = device
        TksDetect.cache=self

    def _compare(self, *args, **kwargs):
        if super()._compare(*args, **kwargs):
            fuse.reset(self)
            return True
        else:
            return False

    def _find(self, *args, **kwargs):
        if (t := super()._find(*args, **kwargs)) is not None:
            fuse.reset(self)
        return t

    @coroutine
    def _asyncImageChange(self, *args, **kwargs):
        inner = super()._asyncImageChange(*args, **kwargs)
        p = yield None
        while True:
            if t := inner.send(p):
                fuse.reset(self)
            p = yield t

    def appear(self, img, rect=(0, 0, 1280, 720), threshold=.05):
        return self._compare(img, rect, threshold)

    def appear_btn(self, button):
        return self.appear(button.img, button.rect, button.threshold)

    def find(self, img, rect=(0, 0, 1280, 720), threshold=.05):
        return self._find(img, rect, threshold)

    def find_multiple(self, img, rect=(0, 0, 1280, 720), threshold=.05):
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            (cv2.matchTemplate(self._crop(rect), img[0], cv2.TM_SQDIFF_NORMED, mask=img[1]) < threshold).astype(
                numpy.uint8))
        ret = []
        for i in range(num_labels - 1):
            ret.append((stats[i + 1][0] + int(img[0].shape[1] / 2) + rect[0],
                        stats[i + 1][1] + int(img[0].shape[0] / 2) + rect[1]))
        if len(ret) > 0:
            fuse.reset()
        return ret

    def find_btn(self, button):
        return self.find(button.img, button.rect, button.threshold)

    def click(self, pos, after_delay=0.5):
        device.touch(pos)
        schedule.sleep(after_delay)
        return self

    def find_and_click(self, img, rect=(0, 0, 1280, 720), threshold=.05, after_delay=0.5, retry=0):
        for i in range(retry + 1):
            if pos := self.find(img, rect, threshold):
                self.click(pos, after_delay)
                break
            elif retry > 0:
                schedule.sleep(after_delay)
        return pos is not None

    def find_and_click_btn(self, button, after_delay=0.5, retry=0):
        return self.find_and_click(button.img, button.rect, button.threshold, after_delay, retry)

    def is_on_top(self):
        return self.appear_btn(B_TOP_NOTICE)

    def is_on_map(self):
        return self.appear(IMG.TKS_BACK_MGMT, A_TL_BUTTONS)

    def is_on_menu(self):
        return self.appear(IMG.TKS_MAIN_TL_CLOSE, A_TL_BUTTONS)

    def is_on_campaign_shop(self):
        return self.appear(IMG.TKS_CAMPAIGN_SHOP_OFF, A_CAMPAIGN_REWARD_TABS, threshold=.02) \
               or self.appear(IMG.TKS_CAMPAIGN_SHOP_ON, A_CAMPAIGN_REWARD_TABS, threshold=.02) \

    def is_list_end(self, pos):
        return self.appear(IMG.LISTBAR, (pos[0] - 19, 0, pos[0] + 19, 720)) and super()._isListEnd(pos)

    def surround(self, pos, w, h):
        return clamp_rect((pos[0] - (w >> 1), pos[1] - (h >> 1), pos[0] + (w >> 1), pos[1] + (h >> 1)))

    def expand(self, rect, size):
        return clamp_rect((rect[0] - size, rect[1] - size, rect[2] + size, rect[3] + size))


# buttons borrowed from FGO-ExpBall
P_SPACE = (1231, 687)
B_BACK = Button((38, 43), 'summon_continue', (10, 10))
P_MAIN_MAIN = (137, 596)
P_MAIN_ARCHIVE = (304, 596)
P_MAIN_SYNTHESIS = (472, 596)
B_MAIN_SUMMON = Button((640, 596), 'main', (25, 25))
B_SUMMON_FP = Button((672, 42), 'summon_continue', (15, 15))
P_SUMMON_SWITCH = (45, 360)
P_SUMMON_SUMMON = (733, 526)
B_SUMMON_SUBMIT = Button((837, 564), 'summon_submit', (27, 14))
B_SUMMON_CONTINUE = Button((762, 673), 'summon_continue', (104, 14))
B_SUMMON_SALE = Button((345, 477), 'summon_sale', (27, 14))
P_SELECT_SERVANT = (101, 128)
P_SELECT_REISOU = (288, 128)
P_SELECT_CODE = (475, 128)
B_SELECT_GIRD = Button((28, 677), 'sort', (21, 21))
B_SELECT_FINISH = Button((1153, 673), 'lock', (27, 12))
B_SELECT_LOCK = Button((74, 246), 'lock', (6, 8), .15, 6)
B_FILTER_EVENT = Button((804, 130), 'lock', (80, 18))
P_FILTER_FILTER = (980, 130)
P_FILTER_SCROLL = (1135, 565)
P_FILTER_EXP = (639, 385)
P_FILTER_FOU = (852, 385)
P_FILTER_RESET = (227, 641)
B_FILTER_SUBMIT = Button((1054, 638), 'filter', (20, 65))
P_FILTER_CANCEL = (820, 638)
P_SORT_SORT = (1128, 130)
B_SORT_DEC = Button((1248, 132), 'sort', (15, 12))
P_SORT_BYTIME = (742, 384)
P_SORT_BYLEVEL = (318, 232)
P_SORT_BYRANK = (430, 322)
B_SORT_FILTER_ON = Button((578, 474), 'sort', (12, 12))
P_SORT_SUBMIT = (853, 638)
B_SELL_RESULT = Button((640, 629), 'result', (40, 20))
P_SYNTHESIS_SYNTHESIS = (958, 474)
B_SYNTHESIS_LOAD = Button((195, 382), 'synthesis', (80, 80))
P_SYNTHESIS_SELECT = (30, 240)
# P_SYNTHESIS_LOCK = (30, 354) this position is strictly disabled, never touch
P_SYNTHESIS_ENTER = (864, 242)
P_ARCHIVE_ARCHIVE = (958, 627)
P_ARCHIVE_SUBMIT = (836, 602)
P_ARCHIVE_RESULT = (637, 602)

# Buttons created
B_MAIN_TL_CLOSE = Button((88, 42), 'main', (55, 13))
B_TOP_NOTICE = Button((88, 42), 'top_interface', (55, 13))
B_MAIN_MENU_CLOSE = Button((1186, 475), 'main', (83, 23))
B_FRIEND_TL_BACK = Button((88, 42), 'friend_formation', (55, 13))
B_NOTICE = Button((636, 36), 'notice', (89, 17))
B_SUMMON_AUTO_SALE = Button((642, 465), 'summon_submit', (85, 20))
B_FILTER_STAR_3_ON = Button((642, 235), 'filter2', (30, 25))
B_FILTER_STAR_2_ON = Button((831, 235), 'filter', (30, 25))
B_FILTER_STAR_1_ON = Button((1019, 235), 'filter', (30, 25))
B_FILTER_STAR_3_OFF = Button((642, 235), 'filter', (30, 25))
B_FILTER_STAR_2_OFF = Button((831, 235), 'filter2', (30, 25))
B_FILTER_STAR_1_OFF = Button((1019, 235), 'filter2', (30, 25))
B_SORT_FAV_ON = B_SORT_FILTER_ON.offset(442, 0)
B_SYNTHESIS_BTN_DISABLED = Button((1143, 670), 'synthesis', (85, 20))
B_FILTER_NOT_EXIST = Button((1055, 632), 'filter', (66, 16))

P_CENTER = (640, 360)
P_NOTICE_CLOSE = (1242, 36)
P_TL_BUTTON = (48, 42)
P_MAIN_MENU = (1186, 652)
P_MENU_ROOM = (1142, 602)
P_MENU_SHOP = (807, 602)
P_RIGHT_SCROLL_END = (1257, 590)
P_BATTLE_OPTION = (1194, 200)
P_BATTLE_OPTION_CLOSE = (1174, 108)
P_BATTLE_ATTACK = (1154, 626)
P_BATTLE_SPEED = (1130, 62)
P_BATTLE_BACK = (1200, 682)
P_FAIL_CLOSE = (645, 562)
P_CONTRACT_AGREE = (712, 486)
P_SCROLL_TOP = (1256, 92)
P_CUR_CAMPAIGN = (932, 378)
P_SECOND_CAMPAIGN = (932, 519)
P_CAMPAIGN_REWARD_VIEW = (1166, 239)
P_DESKTOP_AWARD_VIEW = (1022, 212)
P_FRIEND_OPTION_SCROLL_TOP = (1084, 61)
P_FRIEND_OPTION_RESET = (507, 321)
P_FRIEND_CAMPAIGN_SERVANT = (490, 216)
P_FRIEND_CAMPAIGN_REISOU = (730, 221)
P_FRIEND_OPTION_SCROLL_MID = (1084, 268)
P_FRIEND_OPTION_SCROLL_END = (1084, 578)
P_FRIEND_SCROLL_TOP = (1255, 186)
P_FRIEND_SCROLL_END = (1255, 708)
P_SYNTHESIS_SERVANT = (958, 174)
P_SERVANT_OPTION_SERVANT = (430, 262)
P_SERVANT_OPTION_EXP = (642, 262)
P_SERVANT_OPTION_FOU = (862, 262)
P_MENU_BURNING = P_SYNTHESIS_SYNTHESIS
P_OPTIONS_SCROLL_START = (1135, 114)
P_OPTIONS_SCROLL_END = (1135, 561)
P_OPTIONS_SCROLL_SECTION1 = (1135, 192)
P_NOT_MAX_LEVEL = (324, 260)
P_UNLIMITED_TAB = (661, 139)
P_UNLIMITED_GET_MULTI = (340, 436)
P_UNLIMITED_GET_ONE = (340, 436)
P_GIFT_BTN_ON_TOP = (433, 675)
P_GIFT_SCROLL_TOP = (935, 172)
P_GIFT_SCROLL_END = (935, 679)
P_POT_BTN = (882, 679)

# Areas
A_SUB_MENUS = (678, 108, 1278, 566)
A_TL_BUTTONS = (8, 8, 220, 200)
A_BR_BUTTONS = (980, 520, 1278, 718)
A_TR_BUTTONS = (1008, 2, 1278, 124)
A_TOP_MIDDLE = (382, 2, 900, 110)
A_INSTANCE_MENUS = (614, 90, 1240, 600)
A_INSTANCE_MENUS_RIGHT = (1020, 90, 1240, 600)
A_DIALOG_BUTTONS = (156, 420, 1080, 680)
A_FULL_DIALOG_CONFIRM = (964, 580, 1266, 704)
A_FULL_DIALOG_CROSS = (1064, 4, 1272, 200)
A_LOGIN_BOX = (456, 208, 820, 542)
A_LIST_BAR = (1220, 90, 1276, 710)
A_SWIPE_CENTER_DOWN = (640, 650, 640, 150)
A_SWIPE_CENTER_DOWN_S = (640, 500, 640, 150)
A_SWIPE_CENTER_UP = (640, 150, 640, 650)
A_SWIPE_RIGHT_DOWN = (950, 600, 950, 200)
A_SWIPE_RIGHT_DOWN_LOW = (950, 680, 950, 280)
A_BATTLE_OPTIONS = (656, 198, 1130, 488)
A_BATTLE_CMD = (1010, 500, 1276, 714)
A_TOP_RIGHT = (1008, 2, 1278, 82)
A_CONTRACT_TITLE = (500, 180, 800, 280)
A_LEFT_BUTTONS = (2, 220, 70, 520)
A_CAMPAIGN_REWARD_TABS = (560, 92, 1276, 212)
A_CAMPAIGN_REWARD_VIEWS = (1065, 200, 1262, 280)
A_DESKTOP_AWARD_VIEWS = (936, 180, 1266, 246)
A_CAMPAIGN_REWARD_1ST_READY = (749, 368, 851, 426)
A_CAMPAIGN_INSTANCE_REWARD = (1082, 128, 1204, 600)
A_AWARD_NOTICE = (465, 600, 590, 718)
A_AWARD_1ST_ICON = (1100, 284, 1212, 394)
A_INSTANCE_TITLE = (690, 100, 1250, 600)
A_FRIEND_OPTIONS_BAR = (726, 92, 1278, 166)
A_FRIEND_SHOW_BUTTONS = (800, 20, 980, 620)
A_SWIPE_FRIEND_OPTION_DOWN = (950, 500, 950, 100)
A_FRIEND_CLASSES = (45, 89, 741, 166)
A_FRIEND_ICONS = (28, 165, 235, 718)
A_FRIEND_NAMES = (340, 166, 750, 694)
A_SERVANT_LEVEL_MAX_NOTICE = (1000, 472, 1238, 535)
A_SUMMON_OPTION_EXP = (319, 229, 984, 315)
A_SUMMON_OPTION_FOU = (319, 309, 984, 400)
A_SUMMON_OPTION_REISOU = (319, 389, 984, 485)
A_UNLIMITED_BUTTONS = (38, 250, 580, 566)
A_GIFT_ICONS = (83, 143, 240, 718)
A_POT_BUTTONS = (752, 628, 930, 718)
A_CENTER_BG = (434, 345, 897, 475)
A_OPTIONS_LEFT_BTNS = (200, 110, 550, 575)


PS_FRIEND_CLASSES = {
    ['any', 'saber', 'archer', 'lancer', 'rider', 'caster', 'assassin', 'berserker', 'ex', 'all'][i]: (91 + i * 68, 128)
    for i in range(10)
}

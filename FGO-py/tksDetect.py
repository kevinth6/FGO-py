import os, cv2, numpy
from fgoDetect import XDetect, coroutine
from fgoSchedule import schedule
from fgoFuse import fuse
from fgoDevice import device

# Extension of fgoDetect.
# Add detection supported by the images in the interface folder
# images in the interface folder is usually a screenshot or part of screenshot which contains multiple resources,
# not just as a single icon.
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
    INSTANCES[i] = {'chapters': {}, 'sections': {}, 'instances': {}}
    for j in os.listdir('fgoImage/instance/' + i):
        if not j.endswith('.png'):
            continue
        img = (lambda x: (x[..., :3], x[..., 3]))(cv2.imread(f'fgoImage/instance/{i}/{j}', cv2.IMREAD_UNCHANGED))
        j = j[:-4]
        if j.startswith('chapter_'):
            INSTANCES[i]['chapters'][j[8:]] = img
        if j.startswith('section_'):
            INSTANCES[i]['sections'][j[8:]] = img
        elif j.startswith('instance_'):
            INSTANCES[i]['instances'][j[9:]] = img


class Button:
    def __init__(self, center, img_name, size=(0, 0), threshold=.08, padding=2):
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


STUCK_MISSES = 100
StuckException = type('StuckException', (Exception,), {})


class TksDetect(XDetect):
    # count for a recoverable stuck. the max misses should be less than fuse
    misses = 0

    def __init__(self, ante_latency=.1, post_latency=0):
        schedule.sleep(ante_latency)
        super().__init__()
        TksDetect.misses = TksDetect.misses + 1
        if TksDetect.misses > STUCK_MISSES:
            raise StuckException()
        fuse.increase()
        schedule.sleep(post_latency)
        self.device = device

    def _compare(self, *args, **kwargs):
        if super()._compare(*args, **kwargs):
            TksDetect.misses = 0
            fuse.reset(self)
            return True
        else:
            return False

    def _find(self, *args, **kwargs):
        if (t := super()._find(*args, **kwargs)) is not None:
            TksDetect.misses = 0
            fuse.reset(self)
        return t

    @coroutine
    def _asyncImageChange(self, *args, **kwargs):
        inner = super()._asyncImageChange(*args, **kwargs)
        p = yield None
        while True:
            if t := inner.send(p):
                TksDetect.misses = 0
                fuse.reset(self)
            p = yield t

    def appear(self, img, rect=(0, 0, 1280, 720), threshold=.05):
        return super()._compare(img, rect, threshold)

    def appear_btn(self, button):
        return self.appear(button.img, button.rect, button.threshold)

    def find(self, img, rect=(0, 0, 1280, 720), threshold=.05):
        return super()._find(img, rect, threshold)

    def find_btn(self, button):
        return self.find(button.img, button.rect, button.threshold)

    def click(self, pos, after_delay=0.3):
        device.touch(pos)
        schedule.sleep(after_delay)
        return self

    def find_and_click(self, img, rect=(0, 0, 1280, 720), threshold=.05, after_delay=0.3, retry=0):
        for i in range(retry + 1):
            if pos := self.find(img, rect, threshold):
                self.click(pos, after_delay)
                break
            else:
                schedule.sleep(after_delay)
        return pos is not None

    def find_and_click_btn(self, button, after_delay=0.3, retry=0):
        return self.find_and_click(button.img, button.rect, button.threshold, after_delay, retry)

    def is_on_top(self):
        return self.appear_btn(TOP_NOTICE)


# buttons borrowed from FGO-ExpBall
P_SPACE = (1231, 687)
BACK = Button((38, 43), 'summon_continue', (10, 10))
P_MAIN_MAIN = (137, 596)
P_MAIN_ARCHIVE = (304, 596)
P_MAIN_SYNTHESIS = (472, 596)
MAIN_SUMMON = Button((640, 596), 'main', (25, 25))
SUMMON_FP = Button((672, 42), 'summon_continue', (15, 15))
P_SUMMON_SWITCH = (45, 360)
P_SUMMON_SUMMON = (733, 526)
SUMMON_SUBMIT = Button((837, 564), 'summon_submit', (27, 14))
SUMMON_CONTINUE = Button((762, 673), 'summon_continue', (104, 14))
SUMMON_SALE = Button((345, 477), 'summon_sale', (27, 14))
P_SELECT_SERVANT = (101, 128)
P_SELECT_REISOU = (288, 128)
P_SELECT_CODE = (475, 128)
SELECT_GIRD = Button((28, 677), 'sort', (21, 21))
SELECT_FINISH = Button((1153, 673), 'lock', (27, 12))
SELECT_LOCK = Button((74, 246), 'lock', (6, 8), .13, 4)
FILTER_EVENT = Button((804, 130), 'lock', (80, 18))
P_FILTER_FILTER = (980, 130)
P_FILTER_STAR_3 = (642, 235)
P_FILTER_STAR_2 = (831, 235)
P_FILTER_STAR_1 = (1019, 235)
P_FILTER_SCROLL = (1135, 565)
P_FILTER_EXP = (639, 385)
P_FILTER_FOU = (852, 385)
P_FILTER_RESET = (227, 641)
FILTER_SUBMIT = Button((1054, 638), 'filter', (20, 65))
P_FILTER_CANCEL = (820, 638)
P_SORT_SORT = (1128, 130)
SORT_DEC = Button((1248, 132), 'sort', (15, 12))
P_SORT_BYTIME = (742, 384)
P_SORT_BYLEVEL = (318, 232)
P_SORT_BYRANK = (430, 322)
SORT_FILTER_ON = Button((578, 474), 'sort', (12, 12))
P_SORT_SUBMIT = (853, 638)
SELL_RESULT = Button((640, 629), 'result', (40, 20))
P_SYNTHESIS_SYNTHESIS = (958, 474)
SYNTHESIS_LOAD = Button((195, 382), 'synthesis', (80, 80))
P_SYNTHESIS_SELECT = (30, 240)
P_SYNTHESIS_LOCK = (30, 354)
P_SYNTHESIS_ENTER = (864, 242)
P_ARCHIVE_ARCHIVE = (958, 627)
P_ARCHIVE_SUBMIT = (836, 602)
P_ARCHIVE_RESULT = (637, 602)

# Buttons created
MAIN_TL_CLOSE = Button((88, 42), 'main', (55, 13))
TOP_NOTICE = Button((88, 42), 'top_interface', (55, 13))
MAIN_MENU_CLOSE = Button((1186, 475), 'main', (83, 23))
NOTICE = Button((636, 36), 'notice', (89, 17))
P_NOTICE_CLOSE = (1242, 36)
P_MAIN_MENU = (1186, 652)
P_MENU_ROOM = (1142, 602)
P_MENU_ENHANCE = (475, 602)
P_SUBMENU_SWIPE_START = (950, 600)
P_SUBMENU_SWIPE_END = (950, 200)

# Areas
A_SUB_MENUS = (678, 108, 1278, 566)
A_DIALOG_BUTTONS = (156, 360, 1080, 660)
A_FULL_DIALOG_CONFIRM = (964, 580, 1266, 704)
A_FULL_DIALOG_CROSS = (1064, 4, 1272, 200)
A_LOGIN_BOX = (456, 208, 820, 542)
A_LIST_BAR = (1220, 90, 1276, 610)

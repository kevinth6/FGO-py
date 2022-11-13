import os, cv2, numpy
from fgoDetect import XDetect, coroutine
from fgoSchedule import schedule
from fgoFuse import fuse
from fgoDevice import device

# Add detection supported by the images in the interface folder
# please notice that all the pngs under interface a PNG24, not the same as PNG32 in fgoImage

INTERFACES = {
    i[:-4]: (lambda x: (x[..., :3], x[..., 3]))(
        cv2.imread(f'fgoImage/interface/{i}', cv2.IMREAD_UNCHANGED)
    ) for i in os.listdir('fgoImage/interface') if i.endswith('.png')
}


class Clickable:
    def __init__(self, center):
        self.center = center


class Button(Clickable):
    def __init__(self, center, img_name, size=(0, 0), threshold=.08, padding=2):
        super().__init__(center)
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
        result.rect = (self.rect[0] + x, self.rect[1] + x,
                       self.rect[2] + y, self.rect[3] + y)
        return result


class TksDetect(XDetect):
    def __init__(self, ante_latency=.1, post_latency=0):
        schedule.sleep(ante_latency)
        super().__init__()
        fuse.increase()
        schedule.sleep(post_latency)

    def _compare(self, *args, **kwargs):
        return super()._compare(*args, **kwargs) and fuse.reset(self)

    def _find(self, *args, **kwargs):
        if (t := super()._find(*args, **kwargs)) is not None: fuse.reset(self)
        return t

    @coroutine
    def _asyncImageChange(self, *args, **kwargs):
        inner = super()._asyncImageChange(*args, **kwargs)
        p = yield None
        while True:
            if t := inner.send(p): fuse.reset(self)
            p = yield t

    def find(self, img, rect=(0, 0, 1280, 720), threshold=.05):
        return super()._find(img, rect, threshold)

    def click(self, clickable, after_delay=0):
        device.touch(clickable.center)
        schedule.sleep(after_delay)
        return self

    def wait(self, button, after_delay=.5, interval=.2):
        while not self.appear(button, interval):
            pass
        schedule.sleep(after_delay)
        return self

    def appear(self, button, after_delay=0):
        schedule.sleep(after_delay)
        return super()._compare(button.img, button.rect, button.threshold)

    def click(self, clickable, after_delay=0):
        device.touch(clickable.center)
        schedule.sleep(after_delay)
        return self


# buttons borrowed from FGO-ExpBall
C_SPACE = Clickable((1231, 687))
BACK = Button((38, 43), 'summon_continue', (10, 10))
C_MAIN_MAIN = Clickable((137, 596))
C_MAIN_ARCHIVE = Clickable((304, 596))
C_MAIN_SYNTHESIS = Clickable((472, 596))
MAIN_SUMMON = Button((640, 596), 'main', (25, 25))
SUMMON_FP = Button((672, 42), 'summon_continue', (15, 15))
C_SUMMON_SWITCH = Clickable((45, 360))
C_SUMMON_SUMMON = Clickable((733, 526))
SUMMON_SUBMIT = Button((837, 564), 'summon_submit', (27, 14))
SUMMON_CONTINUE = Button((762, 673), 'summon_continue', (104, 14))
SUMMON_SALE = Button((345, 477), 'summon_sale', (27, 14))
C_SELECT_SERVANT = Clickable((101, 128))
C_SELECT_REISOU = Clickable((288, 128))
C_SELECT_CODE = Clickable((475, 128))
SELECT_GIRD = Button((28, 677), 'sort', (21, 21))
SELECT_FINISH = Button((1153, 673), 'lock', (27, 12))
SELECT_LOCK = Button((74, 246), 'lock', (6, 8), .13, 4)
FILTER_EVENT = Button((804, 130), 'lock', (80, 18))
C_FILTER_FILTER = Clickable((980, 130))
C_FILTER_STAR_3 = Clickable((642, 235))
C_FILTER_STAR_2 = Clickable((831, 235))
C_FILTER_STAR_1 = Clickable((1019, 235))
C_FILTER_SCROLL = Clickable((1135, 565))
C_FILTER_EXP = Clickable((639, 385))
C_FILTER_FOU = Clickable((852, 385))
C_FILTER_RESET = Clickable((227, 641))
FILTER_SUBMIT = Button((1054, 638), 'filter', (20, 65))
C_FILTER_CANCEL = Clickable((820, 638))
C_SORT_SORT = Clickable((1128, 130))
SORT_DEC = Button((1248, 132), 'sort', (15, 12))
C_SORT_BYTIME = Clickable((742, 384))
C_SORT_BYLEVEL = Clickable((318, 232))
C_SORT_BYRANK = Clickable((430, 322))
SORT_FILTER_ON = Button((578, 474), 'sort', (12, 12))
C_SORT_SUBMIT = Clickable((853, 638))
SELL_RESULT = Button((640, 629), 'result', (40, 20))
C_SYNTHESIS_SYNTHESIS = Clickable((958, 474))
SYNTHESIS_LOAD = Button((195, 382), 'synthesis', (80, 80))
C_SYNTHESIS_SELECT = Clickable((30, 240))
C_SYNTHESIS_LOCK = Clickable((30, 354))
C_SYNTHESIS_ENTER = Clickable((864, 242))
C_ARCHIVE_ARCHIVE = Clickable((958, 627))
C_ARCHIVE_SUBMIT = Clickable((836, 602))
C_ARCHIVE_RESULT = Clickable((637, 602))

# Buttons created
MAIN_TL_CLOSE = Button((86, 41), 'main', (52, 13))
MAIN_MENU_CLOSE = Button((1186, 475), 'main', (83, 23))
NOTICE = Button((636, 36), 'notice', (89, 17))
C_NOTICE_CLOSE = Clickable((1242, 36))

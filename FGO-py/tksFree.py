import fgoDevice
import fgoSchedule
from fgoDetect import IMG
from fgoLogging import getLogger
from tksDetect import *
from tksCommon import FlowException

logger = getLogger('TksFree')


class TksFree:
    def __init__(self, config, common):
        self.config = config
        self.common = common

    def go_section_in_chapter(self):
        pass

    def go_instance(self, instance):
        pass

    def go_free_instance(self, chapter, section=None, instance=None):
        if not (chapter in INSTANCES):
            raise FlowException('unknown chapter ' + chapter)

        self.common.back_to_top()
        if chapter in INSTANCES[chapter]['chapters']:
            self.common.wait_for_submenu()
            self.common.swipe_and_click_sub_menu(chapter)

        if section and section in INSTANCES[chapter]['chapters'][chapter]:
            self.common.wait_for_main_interface()
            self.go_section_in_chapter(section)

        self.common.wait_for_main_interface()
        self.go_instance(instance)

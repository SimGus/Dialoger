#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import *
from .Action import ActionUtter


class ActionAskSlotValue(ActionUtter):
    """Represents the action of asking the user for the value of some slot."""
    def __init__(self, name, template_msgs, context, slot_to_ask):
        # (str, [str], Context, {"summary": str, ...}) -> ()
        super(ActionAskSlotValue, self).__init__(name, template_msgs, context)
        self.slot = slot_to_ask

    def generate_msg(self, fetched_info=dict()):
        # ({str: str}) -> (str)
        chosen_template = choose(self.template_msgs)  # will never return `None`
        return chosen_template.generate(self.context,
                                        {"slot-name": self.slot["summary"]})

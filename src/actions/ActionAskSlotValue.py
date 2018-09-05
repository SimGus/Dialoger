#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import *
from .Action import ActionUtter, BotErrorMessage
import bot.config as cfg


class ActionAskSlotValue(ActionUtter):
    """Represents the action of asking the user for the value of some slot."""
    def __init__(self, context, slot_description):
        # (Context, {"summary": str, ...}) -> ()
        if not isinstance(slot_description, dict):
            raise TypeError("Tried to create an 'ask slot' utterance action "+
                            "with a slot description of invalid type: "+
                            type(slot_description).__name__+" instead of dict.")
        name = cfg.ASK_SLOT_VAL_ACTION_NAME
        template_msgs = cfg.get_utterances_templates()[name]
        super(ActionAskSlotValue, self).__init__(name, template_msgs, context)
        self.slot_description = slot_description

    def generate_msg(self, fetched_info=dict()):
        # ({str: str}) -> (str)
        if isinstance(fetched_info, BotErrorMessage):
            return fetched_info.msg
        chosen_template = choose(self.template_msgs)  # will never return `None`
        return chosen_template.generate(self.context,
                                        {"slot-name": self.slot_description["summary"]})


    def get_expected_replies(self):
        """
        Returns a list of all expected replies
        to the question `self` represents.
        """
        # () -> ([{"intent-name": str}])
        return [cfg.INFORM_INTENT_PREFIX+self.slot_description["name"]]


    def __str__(self):
        return type(self).__name__+": '"+self.name+"' asking for '"+ \
               self.slot_description["name"]+"'"

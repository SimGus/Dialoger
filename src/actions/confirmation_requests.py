#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import *
from .Action import ActionUtter
import bot.config as cfg


class ActionUtterConfirmIntent(ActionUtter):
    """
    Represents a confirmation request utterance about intents, that is the bot asks the
    user to confirm if it understood well intents.
    The `generate_msg` method is not callable anymore in this class (this is the
    only kind of subclass of `ActionUtter` that should have this behavior).
    The `generate_confirmation_request` method can be given which intent
    the bot should ask confirmation for.
    """
    def __init__(self, context, intent_to_confirm):
        # (Context, {"summary": str, ...}) -> ()
        if not isinstance(intent_to_confirm, dict):
            raise TypeError("Tried to create a confirmation request intent action with an "+
                            "intent to confirm of invalid type: "+
                            type(intent_to_confirm).__name__+" instead of dict.")
        name = cfg.REQUEST_CONFIRMATION_INTENT_ACTION_NAME
        template_msgs = cfg.get_utterances_templates()[name]
        super(ActionUtterConfirmIntent, self).__init__(name, template_msgs, context)
        self.intent_to_confirm = intent_to_confirm  # dict as described in the config, {"summary": str, ...}

    def generate_msg(self, fetched_info=dict()):
        raise TypeError("Tried to generate a confirmation request message without giving "+
                        "it something to confirm.")

    def generate_confirmation_request(self):
        """Generates a message to confirm the intent `self.intent_to_confirm`."""
        # () -> (str)
        chosen_template = choose(self.template_msgs)  # will never return `None`
        return chosen_template.generate(self.context,
                                        {"intent-summary":
                                        self.intent_to_confirm["summary"]})


    def __str__(self):
        return type(self).__name__+": '"+self.name+"' asks confirmation for intent '"+ \
               self.intent_to_confirm["name"]+"'"

class ActionUtterConfirmEntity(ActionUtter):
    """
    Represents a confirmation request utterance about entities, that is
    the bot asks the user to confirm if it understood well an entity.
    The `generate_msg` method is not callable anymore in this class(this is the
    only subclass of `ActionUtter` that should have this behavior).
    The `generate_confirmation_request` method can be given which slot
    the bot should request confirmation for.
    """
    def __init__(self, context, slot_to_confirm, slot_value):
        # (Context, {"summary": str, ...}, str) -> ()
        if not isinstance(slot_to_confirm, dict):
            raise TypeError("Tried to create an entity confirmation request action with "+
                            "a slot to confirm of invalid type: "+
                            type(slot_to_confirm).__name__+" instead of dict.")
        if not isinstance(slot_value, str):
            import sys
            if sys.version_info[0] == 2:
                if not isinstance(slot_value, unicode):
                    raise TypeError("Tried to create an entity confirmation request "+
                                    "action with a slot value of invalid type: "+
                                    type(slot_value).__name__+" instead of str.")
        name = cfg.REQUEST_CONFIRMATION_SLOT_VAL_ACTION_NAME
        template_msgs = cfg.get_utterances_templates()[name]
        super(ActionUtterConfirmEntity, self).__init__(name, template_msgs, context)
        self.slot_to_confirm = slot_to_confirm
        self.slot_value = slot_value

    def generate_msg(self, fetched_info=dict()):
        raise TypeError("Tried to generate a confirmation request message without giving "+
                        "it something to confirm.")

    def generate_confirmation_request(self, slot_to_confirm, value):
        """
        Generates a message asking the user to confirm
        the value of the slot `self.slot_to_confirm`.
        """
        # () -> (str)
        chosen_template = choose(self.template_msgs)  # will never return `None`
        return chosen_template.generate(self.context,
                                        {"slot-summary":
                                        self.slot_to_confirm["summary"],
                                        "slot-value": self.slot_value})


    def __str__(self):
        return type(self).__name__+": '"+self.name+"' asks confirmation for slot '"+ \
               self.slot_to_confirm["name"]+"'"

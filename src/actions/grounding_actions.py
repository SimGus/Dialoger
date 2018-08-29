#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import *
from .Action import ActionUtter


class ActionUtterGroundIntent(ActionUtter):
    """
    Represents a grounding utterance about intents, that is the bot asks the
    user to confirm if it understood well intents.
    The `generate_msg` method is not callable anymore in this class (this is the
    only kind of subclass of `ActionUtter` that should have this behavior).
    The `generate_grounding` method can be given which intent the bot should
    ground.
    """
    def __init__(self, name, template_msgs, context, intent_to_ground):
        # (str, [str], Context, {"summary": str, ...}) -> ()
        super(ActionUtterGroundIntent, self).__init__(name, template_msgs, context)
        self.intent_to_ground = intent_to_ground  # dict as described in the config, {"summary": str, ...}

    def generate_msg(self, fetched_info=dict()):
        raise TypeError("Tried to generate a grounding message without giving "+
                        "it something to ground.")

    def generate_grounding(self):
        """Generates a message to ground the intent `self.intent_to_ground`."""
        # () -> (str)
        chosen_template = choose(self.template_msgs)  # will never return `None`
        return chosen_template.generate(self.context,
                                        {"intent-summary":
                                        self.intent_to_ground["summary"]})

class ActionUtterGroundEntity(ActionUtter):
    """
    Represents a grounding utterance about entities, that is the bot asks the
    user to confirm if it understood well an entity.
    The `generate_msg` method is not callable anymore in this class(this is the
    only subclass of `ActionUtter` that should have this behavior).
    The `generate_grounding` methdo can be given which slot the bot should
    ground.
    """
    def __init__(self, name, template_msgs, context, slot_to_ground, slot_value):
        # (str, [str], Context, {"summary": str, ...}) -> ()
        super(ActionUtterGroundEntity, self).__init__(name, template_msgs, context)
        self.slot_to_ground = slot_to_ground
        self.slot_value = slot_value

    def generate_msg(self, fetched_info=dict()):
        raise TypeError("Tried to generate a grounding message without giving "+
                        "it something to ground.")

    def generate_grounding(self, slot_to_ground, value):
        """
        Generates a message to ground
        the value of the slot `self.slot_to_ground`.
        """
        # () -> (str)
        chosen_template = choose(self.template_msgs)  # will never return `None`
        return chosen_template.generate(self.context,
                                        {"slot-summary":
                                        self.slot_to_ground["summary"],
                                        "slot-value": self.slot_value})

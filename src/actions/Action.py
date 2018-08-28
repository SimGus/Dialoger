#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import *


class Action(object):
    """
    Superclass for actions the bot can take. Each action is characterized by a
    name and a code to run and uses a context (with slot values, a current
    goal and so forth).
    """
    def __init__(self, name, context):
        if name is None:
            raise ValueError("Tried to create an action without a name.")
        self.name = name
        self.context = context

    def run(self):
        pass

class UtterAction(Action):
    """Superclass for utterance actions (i.e. the bot speaks)."""
    def __init__(self, name, context, template_msgs):
        super(UtterAction, self).__init__(name, context)
        if len(template_msgs) <= 0:
            raise ValueError("Tried to create an utterance action without "+
                             "template messages to utter.")
        self.template_msgs = template_msgs

    def generate_msg(self):
        """Returns a string that can be sent to be displayed to the user."""
        chosen_template = choose(self.template_msgs)  # will never return `None`
        return chosen_template.generate(self.context)


class MsgTemplate(object):
    """
    Represents a template that will generate messages to utter to the user.
    A template is made of string parts and of parts that will be replaced by
    slot values.
    A template is a string and each part that should be replaced by the value of
    a slot must be the slot name prepended and appended with a dollar sign ($).
    """
    def __init__(self, template):
        self.template = template

    def generate(self, context):
        msg = self.template
        for slot_name in context.slots:
            msg = msg.replace('$'+slot_name+'$',
                              context.get_slot_value(slot_name))
        return msg

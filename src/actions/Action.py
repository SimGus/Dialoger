#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re

from utils import *


class Action(object):
    """
    Superclass for actions the bot can take. Each action is characterized by a
    name and a code to run and uses a context (with slot values, a current
    goal and so forth).
    Actions should always be immutable.
    """
    def __init__(self, name, context):
        if name is None:
            raise ValueError("Tried to create an action without a name.")
        self.name = name
        self.context = context

    def run(self):
        """Runs the action and returns the potentially fetched informations."""
        # () -> ({str: str} or BotErrorMessage)
        return dict()

    def promote_needed_optional_slots(self, context_to_update):
        """
        Using all the slot values that are already filled, checks if
        a slot marked as 'optional' needs to be promoted to 'mandatory' and
        makes all the needed promotions in the context `context_to_update`.
        Returns `True` if at least one promotion was made, `False` if none was
        made.
        """
        return False

    def __str__(self):
        return type(self).__name__+": '"+self.name+"'"

class ActionUtter(Action):
    """Superclass for utterance actions (i.e. the bot speaks)."""
    def __init__(self, name, template_msgs, context):
        # (str, [str], Context) -> ()
        super(ActionUtter, self).__init__(name, context)
        if template_msgs is None or len(template_msgs) <= 0:
            raise ValueError("Tried to create an utterance action without "+
                             "template messages to utter.")
        self.template_msgs = [MsgTemplate(template)
                              for template in template_msgs]

    def generate_msg(self, fetched_info=dict()):
        """
        Returns a string that can be sent to be displayed to the user.
        `fetched_info` is a dict containing all the information that was fetched
        by previous actions.
        """
        # ({str: str} or BotErrorMessage) -> (str)
        if isinstance(fetched_info, BotErrorMessage):
            return fetched_info.msg
        chosen_template = choose(self.template_msgs)  # will never return `None`
        return chosen_template.generate(self.context, fetched_info)


class MsgTemplate(object):
    """
    Represents a template that will generate messages to utter to the user.
    A template is made of string parts and of parts that will be replaced by
    slot values.
    A template is a string and each part that should be replaced by the value of
    a slot must be the slot name prepended and appended with a pipe (|).
    NOTE: this special character is stored into
    `MsgTemplate.TEMPLATE_BOUNDARY_CHAR`.
    We can also denote parts that should be replaced by a value if it exist and
    by nothing if it doesn't exist using the same technique with tildes (~).
    NOTE: this special character is stored into
    `MsgTemplate.OPTIONAL_TEMPLATE_BOUNDARY_CHAR`.
    The same thing can be done with info that would have been fetched by a
    directly previous action (and thus put in `fetched_info`), with the same
    syntax (if there is a conflict between a slot name and an info name, the
    slot will take precedence).
    """
    TEMPLATE_BOUNDARY_CHAR = '|'
    OPTIONAL_TEMPLATE_BOUNDARY_CHAR = '~'
    OPTIONAL_TEMPLATE_REGEX = \
        re.compile(r"(?<!\\)"+OPTIONAL_TEMPLATE_BOUNDARY_CHAR+
                   r".*?(?<!\\)"+OPTIONAL_TEMPLATE_BOUNDARY_CHAR)

    def __init__(self, template):
        if not isinstance(template, str):
            import sys
            if sys.version_info[0] == 2:
                if not isinstance(template, unicode):
                    raise ValueError("Tried to create a template with a "+
                                     "message of invalid type ("+
                                     type(template).__name__+")")
            else:
                raise ValueError("Tried to create a template with a "+
                                 "message of invalid type ("+
                                 type(template).__name__+")")
        self.template = template

    def generate(self, context, fetched_info=dict()):
        """
        Generates a message sendable to the user and uses for this the slot
        values from the `context` and the `fetched_info` fetched by previous
        actions.
        """
        # (Context, {str: str}) -> (str)
        msg = self.template
        for slot_name in context.slots:
            slot_value = context.get_slot_value(slot_name)
            if slot_value is not None:
                slot_value = str(slot_value)
                try:
                    if context.slots[slot_name].type_str == "percentage":
                        slot_value = "{:.1f}".format((100*float(slot_value)))  # To display it in percents
                    elif context.slots[slot_name].type_str == "float":
                        slot_value = "{:.1f}".format(float(slot_value))
                except ValueError:
                    import warnings
                    warnings.warn("A slot of type 'float' or 'percentage' has "+
                                  "a value of another type ('"+slot_value+"').")

            if slot_value is not None:
                msg = msg.replace(MsgTemplate.TEMPLATE_BOUNDARY_CHAR + slot_name +
                                  MsgTemplate.TEMPLATE_BOUNDARY_CHAR,
                                  slot_value)
                msg = msg.replace(MsgTemplate.OPTIONAL_TEMPLATE_BOUNDARY_CHAR+
                                  slot_name+
                                  MsgTemplate.OPTIONAL_TEMPLATE_BOUNDARY_CHAR,
                                  slot_value)
        for info_name in fetched_info:
            if fetched_info[info_name] is not None:
                piece_of_info = fetched_info[info_name]
                if isinstance(piece_of_info, float):
                    piece_of_info = "{:.1f}".format(piece_of_info)
                else:
                    piece_of_info = str(piece_of_info)
                msg = msg.replace(MsgTemplate.TEMPLATE_BOUNDARY_CHAR + info_name +
                                  MsgTemplate.TEMPLATE_BOUNDARY_CHAR,
                                  piece_of_info)
                msg = msg.replace(MsgTemplate.OPTIONAL_TEMPLATE_BOUNDARY_CHAR+
                                  info_name+
                                  MsgTemplate.OPTIONAL_TEMPLATE_BOUNDARY_CHAR,
                                  piece_of_info)
        msg = re.sub(MsgTemplate.OPTIONAL_TEMPLATE_REGEX, "", msg)
        return msg

class BotErrorMessage(object):
    """
    An instance of a class will be returned by 'fetching' actions (custom
    actions) in case the context is incoherent or the required information can't
    be found. If any other problem occurs, an instance of this class could also
    be returned.
    Such an object contains an error message which will be displayed to the user
    instead of a normal templated utterance in case it is returned.
    """
    def __init__(self, error_message="An error occurred."):
        if (   error_message is None or error_message == ""
            or not is_str(error_message)):
            raise ValueError("Tried to instantiate an error with a message of "+
                             "invalid type ("+type(error_message).__name__+"): "+
                             str(error_message)+".")
        self.msg = error_message

    def __str__(self):
        return "<BotErrorMessage: "+self.msg+">"

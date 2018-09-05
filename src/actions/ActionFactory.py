#!/usr/bin/env python
# -*- coding: utf-8 -*-

import importlib

from .Action import *
from .confirmation_requests import *
from .ActionAskSlotValue import ActionAskSlotValue
import bot.config as cfg

from utils import is_API_accessible
from .ActionNoAPI import ActionNoAPI


def import_action_class(class_name, module_name=None):
    """
    Given the module name and path of an action class, tries to retrieve
    the class.
    The loaded class can be used to instantiate new objects.
    """
    # type: (str) -> (Class)
    if not is_API_accessible():
        return ActionNoAPI
    if module_name is None:
        # The action class is put in a file with the same name
        module_name = cfg.get_custom_actions_module_path()+class_name

    # load the module, will raise an `ImportError` if the module cannot be loaded
    m = importlib.import_module(module_name)
    # get the class, will raise `AttributeError` if the class cannot be found
    return getattr(m, class_name)


class ActionFactory(object):
    """
    A factory for actions: creates actions based solely on their name and loads
    their templates if needed.
    """
    def __init__(self, templates):
        """
        `templates` is a dict indexed with utterances name and whose values are
        lists of templates for this utterance.
        """
        # ({str: [str]}) -> ()
        if not isinstance(templates, dict):
            raise TypeError("Tried to create an action factory with a template "+
                            "inventory of invalid type: "+
                            type(templates).__name__+" instead of dict.")
        self.templates = templates

        self.intents_descriptions = cfg.get_intents_descriptions()
        self.slots_descriptions = cfg.get_slots_descriptions()

    def new_action(self, action_name, context):
        """
        Creates an action with name `action_name`.
        If the action is an utterance, an `ActionUtter` is returned.
        """
        if action_name is None or action_name == "":
            raise ValueError("Tried to instantiate an action with no name.")
        # Check if `action_name` doesn't refer to a special action
        if action_name in cfg.PARAMETRIZED_ACTIONS_NAMES:
            raise RuntimeError("Tried to instantiate a special action ('"+
                               action_name+"') without giving its parameters.")
        # Check if `action_name` refers to an utterance action
        if (   action_name in cfg.SPECIAL_ACTIONS_NAMES
            or action_name.startswith(cfg.UTTERANCE_ACTION_PREFIX)):
            return self.new_utterance(action_name, context)
        # Try to return the right action
        try:
            action_class = import_action_class(action_name)
        except (ImportError, AttributeError) as e:
            raise ValueError("Couldn't instantiate action '"+action_name+
                             "': this class doesn't exist.")
        return action_class(action_name, context)

    def new_utterance(self, utterance_name, context):
        """
        Creates an `ActionUtter` with name `utterance_name` and templates linked
        to this specific name (in utterances templates file).
        """
        if utterance_name is None or utterance_name == "":
            raise ValueError("Tried to create an utterance action without a name.")
        if utterance_name not in self.templates:
            raise ValueError("Couldn't create an utterance action named '"+
                             utterance_name+"', this name doesn't exist.")
        return ActionUtter(utterance_name, self.templates[utterance_name],
                           context)

    def new_confirmation_request_utterance(self, intent_or_entity, context):
        """
        Returns a confirmation request action for an intent or a slot and its value.
        Does the first case when `intent_or_entity` is an intent description and
        the second when `intent_or_entity` is a tuple with a slot description and
        a value.
        """
        # (str or (str, str), Context) -> (ActionUtterConfirmIntent or ActionUtterConfirmEntity)
        if isinstance(intent_or_entity, tuple):
            # Request a confirmation of slot and value
            slot_description = self.slots_descriptions[intent_or_entity[0]]
            return ActionUtterConfirmEntity(context, slot_description,
                                           intent_or_entity[1])
        else:
            # Request a confirmation of intent
            intent_description = self.intents_descriptions[intent_or_entity]
            return ActionUtterConfirmIntent(context, intent_description)

    def new_ask_for_slot_utterance(self, slot_name, context):
        """
        Returns an `ActionAskSlotValue` asking the user
        for the value of `slot_name`.
        """
        slot_description = self.slots_descriptions[slot_name]
        return ActionAskSlotValue(context, slot_description)

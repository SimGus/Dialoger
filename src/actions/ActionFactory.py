#!/usr/bin/env python
# -*- coding: utf-8 -*-

import importlib

from .Action import *
from .grounding_actions import *


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
        self.templates = templates

    def new_action(self, action_name, context):
        """
        Creates an action with name `action_name`.
        """
        # Try to return an action with name `action_name`
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

    def new_grounding_utterance(self, intent_or_entity, context):
        """
        Returns a grounding action for an intent or a slot and its value.
        Does the first case when `intent_or_entity` is an intent description and
        the second when `intent_or_entity` is a tuple with a slot description and
        a value.
        """
        # ({"summary": str, ...} or ({"summary": str, ...}, str)) -> (ActionUtterGroundIntent or ActionUtterGroundEntity)
        if isinstance(intent_or_entity, dict):
            # Ground intent
            return ActionUtterGroundIntent("ground_intent",  # TODO: a more explicit name would be nice
                                           self.templates["ground-intent"],
                                           context, intent_or_entity)
        else:
            # Ground slot and value
            return ActionUtterGroundEntity("ground_entity",  # TODO: a more explicit name would be nice
                                           self.templates["ground-slot-value"],
                                           context,
                                           intent_or_entity[0],
                                           intent_or_entity[1])

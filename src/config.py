#!/usr/bin/env python
# -*- coding: utf-8 -*-

# In this file, you will find all the configurations that is specific to the bot.
# Things like config files paths and the handling of their opening is done here.
#
# Yes, global variables are a bad practice but it would be more complicated to
# use a config singleton that would be defined here ;)

# NOTE: the current working directory is the folder containing 'main.py'

import io
import yaml

from utils import *


############### NLU configuration ######################
NLU_DATA_PATH = "../data/nlu/nlu-data.json"
NLU_CONFIG_PATH = "../nlu-config.yml"
MODELS_PATH = "../models/current/"
NLU_MODEL_NAME = "nlu"

############### Intents descriptions ###################
INFORM_INTENT_PREFIX = "inform_"


INTENTS_DESCRIPTIONS_FILEPATH = "../data/dialog/intents-descriptions.yml"
INTENTS_DESCRIPTIONS = None

def _load_intents_descriptions():
    """
    Loads the data from `INTENTS_DESCRIPTIONS_FILEPATH`
    into `INTENTS_DESCRIPTIONS` and checks that it is well formatted
    """
    global INTENTS_DESCRIPTIONS
    with io.open(INTENTS_DESCRIPTIONS_FILEPATH, 'r') as f:
        tmp = yaml.load(f, Loader=yaml.BaseLoader)  # BaseLoader disables automatic casting
        for intent_name in tmp:
            tmp[intent_name]["name"] = intent_name
        INTENTS_DESCRIPTIONS = cast_to_unicode(tmp)
    # Check the format
    for intent_name in INTENTS_DESCRIPTIONS:
        current_intent_desc = INTENTS_DESCRIPTIONS[intent_name]
        if "category" not in current_intent_desc:
            raise SyntaxError("The intent named '"+intent_name+"' is lacking a "+
                              "category in its description.")
        if "summary" not in current_intent_desc:
            raise SyntaxError("The intent named '"+intent_name+"' is lacking a "+
                              "summary in it description.")
        if (   current_intent_desc["category"] == "confirmation-request-answer"
            or current_intent_desc["category"] == "triggering"):
            if "sub-category" not in current_intent_desc:
                raise SyntaxError("The intent named '"+intent_name+"' is "+
                                  "lacking a sub-category in its description.")
def get_intents_descriptions():
    """Loads the intents descriptions if needed and returns them"""
    # () -> ({str: {"category": str, "sub-category": str}})
    if INTENTS_DESCRIPTIONS is None:
        _load_intents_descriptions()
    return INTENTS_DESCRIPTIONS

############### Slots descriptions #######################
SLOTS_DESCRIPTIONS_FILEPATH = "../data/slots-descriptions.yml"
SLOTS_DESCRIPTIONS = None

def _load_slots_descriptions():
    """
    Loads the data from `SLOTS_DESCRIPTIONS_FILEPATH` into `SLOTS_DESCRIPTIONS`
    and checks that it is well formatted.
    """
    global SLOTS_DESCRIPTIONS
    with io.open(SLOTS_DESCRIPTIONS_FILEPATH, 'r') as f:
        tmp = yaml.load(f, Loader=yaml.BaseLoader)  # BaseLoader disables automatic casting
        for slot_name in tmp:
            tmp[slot_name]["name"] = slot_name
        SLOTS_DESCRIPTIONS = cast_to_unicode(tmp)
    # Check the format
    for slot_name in SLOTS_DESCRIPTIONS:
        current_slot_desc = SLOTS_DESCRIPTIONS[slot_name]
        if (   "type" not in current_slot_desc
            or "summary" not in current_slot_desc
            or "values" not in current_slot_desc
            or not isinstance(current_slot_desc["values"], list)):
                raise SyntaxError("The file containing the slots descriptions ("+
                                  SLOTS_DESCRIPTIONS_FILEPATH+") is proper YAML "+
                                  "but is incorrectly formatted: each slot name "+
                                  "must have a 'summary', a 'type' and "+
                                  "a list of values called 'values'.")
def get_slots_descriptions():
    """Loads the slots descriptions if needed and returns them"""
    # () -> ({str: {"type": str, "values": [str]}})
    if SLOTS_DESCRIPTIONS is None:
        _load_slots_descriptions()
    return SLOTS_DESCRIPTIONS


################ Goals and actions descriptions ########################
#--------------- Actions ----------------
UTTERANCE_ACTION_PREFIX = "utter"

REQUEST_CONFIRMATION_INTENT_ACTION_NAME = "ask-confirm-intent"
REQUEST_CONFIRMATION_SLOT_VAL_ACTION_NAME = "ask-confirm-slot-value"
ASK_SLOT_VAL_ACTION_NAME = "ask-slot-value"

PARAMETRIZED_ACTIONS_NAMES = [REQUEST_CONFIRMATION_INTENT_ACTION_NAME,
                              REQUEST_CONFIRMATION_SLOT_VAL_ACTION_NAME,
                              ASK_SLOT_VAL_ACTION_NAME]
SPECIAL_ACTIONS_NAMES = ["ask-rephrase", "ask-start-over"]

#-------------- Goals --------------------
GOALS_DESCRIPTIONS_FILEPATH = "../data/dialog/goals.yml"
GOALS_DESCRIPTIONS = None
CUSTOM_ACTIONS_MODULE_PATH = None


def _load_goals_descriptions():
    """
    Loads the data from `GOALS_DESCRIPTIONS_FILEPATH` into `GOALS_DESCRIPTIONS`
    and checks that it is well formatted.
    `CUSTOM_ACTIONS_MODULE_PATH` is also set at this point.
    """
    def is_reserved_action_name(action_name):
        return (   action_name in PARAMETRIZED_ACTIONS_NAMES
                or action_name in SPECIAL_ACTIONS_NAMES)

    global GOALS_DESCRIPTIONS, CUSTOM_ACTIONS_MODULE_PATH
    with io.open(GOALS_DESCRIPTIONS_FILEPATH, 'r') as f:
        file_data = cast_to_unicode(yaml.load(f, Loader=yaml.BaseLoader))  # BaseLoader disables automatic casting
        CUSTOM_ACTIONS_MODULE_PATH = file_data["actions-path"].replace('/', '.')
        if not CUSTOM_ACTIONS_MODULE_PATH.endswith('.'):
            CUSTOM_ACTIONS_MODULE_PATH += '.'
        GOALS_DESCRIPTIONS = file_data["goals"]
    # Check the format
    intents = set()
    for goal_name in GOALS_DESCRIPTIONS:
        current_goal_desc = GOALS_DESCRIPTIONS[goal_name]
        if "triggering-intent" not in current_goal_desc:
            raise SyntaxError("The goal '"+goal_name+"' has no triggering intent "+
                              "in the goals description file.")
        if "actions" in current_goal_desc:
            for action_name in current_goal_desc["actions"]:
                if is_reserved_action_name(action_name):
                    raise SyntaxError("Cannot use reserved action name '"+
                                      action_name+"' inside a goal's actions.")
        intents.add(current_goal_desc["triggering-intent"])
    if len(intents) != len(GOALS_DESCRIPTIONS):
        raise SyntaxError("There are duplicate triggering intents in the goals "+
                          "descriptions file (an intent may trigger only one goal).")
def get_goals_descriptions():
    """Loads the goals descriptions if needed and returns it."""
    # () -> ({str: {str: ...}})
    global GOALS_DESCRIPTIONS
    if GOALS_DESCRIPTIONS is None:
        _load_goals_descriptions()
    return GOALS_DESCRIPTIONS
def get_custom_actions_module_path():
    """
    Loads the goals descriptions if needed and
    returns `CUSTOM_ACTIONS_MODULE_PATH`.
    """
    # () -> (str)
    global CUSTOM_ACTIONS_MODULE_PATH
    if CUSTOM_ACTIONS_MODULE_PATH is None:
        _load_goals_descriptions()
    return CUSTOM_ACTIONS_MODULE_PATH

############# Utterance templates descriptions ##################
UTTERANCES_TEMPLATES_DESCRIPTIONS_FILEPATH = \
    "../data/dialog/utterance-templates.yml"
UTTERANCES_TEMPLATES = None

def _load_utterances_templates():
    """
    Loads the data from `UTTERANCES_TEMPLATES_DESCRIPTIONS_FILEPATH` into
    `UTTERANCES_TEMPLATES` and checks that it is well formatted.
    """
    global UTTERANCES_TEMPLATES
    with io.open(UTTERANCES_TEMPLATES_DESCRIPTIONS_FILEPATH, 'r') as f:
        UTTERANCES_TEMPLATES = cast_to_unicode(yaml.load(f, Loader=yaml.BaseLoader))  # BaseLoader disables automatic casting
    # Check the format
    for utterance_name in UTTERANCES_TEMPLATES:
        if not isinstance(UTTERANCES_TEMPLATES[utterance_name], list):
            raise SyntaxError("The templates for utterance '"+utterance_name+
                              "' is not a list.")
def get_utterances_templates():
    """Loads the utterances templates if needed and returns them."""
    # () -> ({str: [str]})
    global UTTERANCES_TEMPLATES
    if UTTERANCES_TEMPLATES is None:
        _load_utterances_templates()
    return UTTERANCES_TEMPLATES

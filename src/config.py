#!/usr/bin/env python

# In this file, you will find all the configurations that is specific to the bot.
# Things like config files paths and the handling of their opening is done here.

# NOTE: the current working directory is the folder with 'main.py'

import io
import yaml

from utils import *
from dialog_management_components import Goal


############### Slots descriptions #######################
SLOTS_DESCRIPTIONS_FILEPATH = "../data/accepted-slot-values.yml"
SLOTS_DESCRIPTIONS = None

def _load_slots_descriptions():
    """
    Loads the data from `SLOTS_DESCRIPTIONS_FILEPATH` into `SLOTS_DESCRIPTIONS`
    and checks that it is well formatted.
    """
    global SLOTS_DESCRIPTIONS
    with io.open(SLOTS_DESCRIPTIONS_FILEPATH, 'r') as f:
        SLOTS_DESCRIPTIONS = \
            cast_to_unicode(yaml.load(f, Loader=yaml.BaseLoader))  # BaseLoader disables automatic casting
    # Check the format
    for slot_name in SLOTS_DESCRIPTIONS:
        if "type" not in SLOTS_DESCRIPTIONS[slot_name] or \
           "values" not in SLOTS_DESCRIPTIONS[slot_name] or \
           not isinstance(SLOTS_DESCRIPTIONS[slot_name]["values"], list):
                raise SyntaxError("The file containing the slots descriptions ("+
                                  SLOTS_DESCRIPTIONS_FILEPATH+") is proper YAML "+
                                  "but is incorrectly formatted: each slot name "+
                                  "must have a 'type' and a list of values "+
                                  "called 'values'.")
def get_slots_descriptions():
    """Loads the slots descriptions if needed and returns them"""
    # () -> ({str: {"type": str, "values": [str]}})
    if SLOTS_DESCRIPTIONS is None:
        _load_slots_descriptions()
    return SLOTS_DESCRIPTIONS


################ Goals descriptions ########################
GOALS_DESCRIPTIONS_FILEPATH = "../data/dialog/goals.yml"
GOALS_DESCRIPTIONS = None
GOALS = None
ACTIONS_FOLDER_PATH = None

def _load_goals_descriptions():
    """
    _Loads the data from `GOALS_DESCRIPTIONS_FILEPATH` into `GOALS_DESCRIPTIONS`
    and checks that it is well formatted.
    `ACTIONS_FOLDER_PATH` is also set at this point.
    """
    _global GOALS_DESCRIPTIONS
    with io.open(GOALS_DESCRIPTIONS_FILEPATH, 'r') as f:
        file_data = cast_to_unicode(yaml.load(f, Loader=yaml.BaseLoader))  # BaseLoader disables automatic casting
        ACTIONS_FOLDER_PATH = file_data["actions-path"]
        GOALS_DESCRIPTIONS = file_data["goals"]
    # Check the format
    intents = set()
    for goal_name in GOALS_DESCRIPTIONS:
        if "triggering-intent" not in GOALS_DESCRIPTIONS[goal_name]:
            raise SyntaxError("The goal '"+goal_name+"' has no triggering intent "+
                              "in the goals description file.")
        intents.add(GOALS_DESCRIPTIONS[goal_name]["triggering-intent"])
    if len(intents) != len(GOALS_DESCRIPTIONS):
        raise SyntaxError("There are duplicate triggering intents in the goals "+
                          "descriptions file (an intent may trigger only one goal).")
def get_goals():
    """Loads the goals descriptions if needed and makes a list of goals from it.
    Puts this list in `GOALS` and returns it."""
    # () -> ({str: Goal})
    global GOALS
    if GOALS is None:
        _load_goals_descriptions()
        GOALS = []
        for goal_name in GOALS_DESCRIPTIONS:
            current_goal_desc = GOALS_DESCRIPTIONS[goal_name]
            mandatory_slots = []
            if "slots-to-fill" in current_goal_desc and \
               "mandatory" in current_goal_desc["slots-to-fill"]:
               mandatory_slots = current_goal_desc["slots-to-fill"]["mandatory"]
            optional_slots = []
            if "slots-to-fill" in current_goal_desc and \
               "optional" in current_goal_desc["slots-to-fill"]:
               optional_slots = current_goal_desc["slots-to-fill"]["optional"]
            actions = []
            if "actions" in current_goal_desc:
                actions = current_goal_desc["actions"]
            GOALS.append(Goal(goal_name, current_goal_desc["triggering-intent"],
                              mandatory_slots, optional_slots, actions))
    return GOALS
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .config import *


class Slot(object):
    """Represents a slot, with a type and a value (empty or not)"""
    def __init__(self, name, type):
        self.name = name
        self.type = None
        if type == "categorical":
            self.type = str
        elif type == "integer":
            self.type = int
        elif type == "float" or type == "percentage":
            self.type == float
        elif type == "bool":
            self.type == bool
        else:
            raise AttributeError("Unexpected slot type: "+str(type))
        self.value = None

    def set(self, value):
        if not isinstance(value, self.type):
            raise AttributeError("Tried to set a slot of type "+
                self.type.__name__+" with a value of another type ("+str(value)+")")
        self.value = value
    def unset(self):
        self.value = None
    def is_set(self):
        return (self.value is not None)


class Goal(object):
    """
    Represents a goal with an identifier, a triggering intent, slots to fill
    (mandatory and optional filling) and actions to take when the goal is met.
    A goal is created by only giving its name, the rest will be taken out of the
    descriptions of goals (cf. `config.py`).

    Note: mandatory slot MUST be in order for the goal to be met; optional slots
    may be filled and may be in some cases upgraded to mandatory; all other
    slots shouldn't get filled and may not be upgraded to mandatory for this
    goal. Mandatory slots cannot be downgraded.
    """
    goals_descriptions = get_goals_descriptions()

    def __init__(self, name):  # TODO: read from the description, no need for all those arguments
        # (str) -> ()
        if name is None:
            raise ValueError("Tried to create a goal without a name.")
        if not Goal.is_valid(name):
            raise ValueError("Tried to create a goal without a description ('"+name+"').")
        self.name = name

        current_goal_desc = Goal.goals_descriptions[name]
        self.triggering_intent = current_goal_desc["triggering-intent"]
        self.mandatory_slots = []
        if "slots-to-fill" in current_goal_desc and \
           "mandatory" in current_goal_desc["slots-to-fill"]:
           self.mandatory_slots = current_goal_desc["slots-to-fill"]["mandatory"]
        self.optional_slots = []
        if "slots-to-fill" in current_goal_desc and \
           "optional" in current_goal_desc["slots-to-fill"]:
           self.optional_slots = current_goal_desc["slots-to-fill"]["optional"]
        self.actions = []
        if "actions" in current_goal_desc:
            self.actions = current_goal_desc["actions"]


    def is_met(self, context):  # QUESTION: is this useful?
        for slot_name in self.mandatory_slots:
            if not context.is_set(slot_name):
                return False
        return True

    def make_mandatory(self, slot_name):
        """
        Upgrades a slot from optional to mandatory.
        If the slot wasn't optional, raises an `ValueError`.
        """
        if slot_name not in self.optional_slots:
            raise ValueError("Tried to make mandatory a slot that was "+
                             "not optional in goal '"+self.name+"' (slot: '"+
                             slot_name+"'.")
        self.optional_slots.remove(slot_name)
        self.mandatory_slots.append(slot_name)

    @staticmethod
    def is_valid(goal_name):
        """
        Static method that returns `True` iff `goal_name` references
        a valid goal.
        """
        return goal_name in Goal.goals_descriptions


class Context(object):
    """
    Represents the current context of the dialog, i.e. which goal is currently
    being worked on, which slots are filled and their value and what kind of
    intent is expected in the next utterance of the user.
    """
    def __init__(self, goal):
        # (Goal) -> ()
        self.current_goal = goal
        self.expected_replies = []  # contains a list of possible replies (broad: intent categories or precise: intent names)
        self.potential_upcoming_goal_name = None

        self.intents_descriptions = get_intents_descriptions()
        slots_descriptions = get_slots_descriptions()
        self.slots = {slot_name: Slot(slot_name,
                                      slots_descriptions[slot_name]["type"])
                      for slot_name in slots_descriptions}

        self.grounding_count = 0
        self.rephrase_count = 0

        self.init()
    def init(self):
        """Puts `self` in its initial state."""
        self.expected_replies = [{"category": "triggering"}]

    def set_slot(self, slot_name, value):
        if slot_name not in self.slots:
            raise ValueError("Tried to set the value of a non-existing slot ("+
                             slot_name+").")
        self.slots[slot_name].set(value)
    def is_set(self, slot_name):
        if slot_name not in self.slots:
            raise ValueError("Tried to get the state of a non-existing slot ("+
                             slot_name+").")
        return self.slots[slot_name].is_set()
    def get_slot_value(self, slot_name):
        if slot_name not in self.slots:
            raise ValueError("Tried to get the value of a non-existing slot ("+
                             slot_name+").")
        return self.slots[slot_name].value
    def get_lacking_info(self):
        """
        Returns the name of an empty mandatory slot in the current goal
        or `None` if there was none.
        """
        for slot_name in self.current_goal.mandatory_slots:
            if not self.is_set(slot_name):
                return slot_name
        return None

    def expect(self, expected_replies):
        """
        Changes the expected replies to `expected_replies`
        An expected reply is a dict charaterizing the type of reply expected.
        It can be broad, containing the intent category expected; less broad,
        containing both the intent category and sub-category expected; or
        precise, containing the intent name.
        """
        # ([{str: str}]) -> ()
        if not isinstance(expected_replies, list):
            raise ValueError("Tried to change the expected intents to a "+
                             "variable that was not a list ("+
                             expected_replies+").")
        self.expected_replies = expected_replies
    def expect_also(self, expected_reply):
        """Adds an expected reply to the expected replies list."""
        # ({str: str}) -> ()
        if not isinstance(expected_reply, dict):
            raise ValueError("Tried to add an illegal expected reply to "+
                             "the list: "+str(expected_reply))
        self.expected_replies.append(expected_reply)

    def is_expecting(self, intent_name):
        """Returns `True` if `intent_name` was expected in this context"""
        # (str) -> (bool)
        # NOTE: this mimicks some kind of object-oriented representation of intents:
        #       `self.expected_replies` indeed contains dicts such as, from less
        #       precise to most precise: {"category": str},
        #       {"category": str, "sub-category": str} or {"intent-name": str}
        for expected_reply in self.expected_replies:
            if (    "intent-name" in expected_reply
                and intent_name == expected_reply["intent-name"]):
                return True
            if (    "category" in expected_reply
                and self.intents_descriptions[intent_name]["category"] == expected_reply["category"]):
                if "sub-category" not in expected_reply:
                    return True
                elif expected_reply["sub-category"] == self.intents_descriptions[intent_name]["sub-category"]:
                    return True
        return False

    def set_upcoming_goal(self, goal_name):
        """
        Stores the name of a potential upcoming goal.
        If the next user reply is `affirm`, the current goal should be changed
        to the upcoming goal.
        """
        # (str) -> ()
        self.potential_upcoming_goal_name = goal_name

    def reset_counts(self):
        self.grounding_count = 0
        self.rephrase_count = 0

    def update_from(self, next_actions):
        """Using the list of actions the bot is going to take, update the context."""
        # To update it is needed to only look at the last action,
        # since the bot issues messages one by one
        last_action = next_actions[-1]
        if (   isinstance(last_action, ActionUtterGroundIntent)
            or isinstance(last_action, ActionUtterGroundEntity)):
            # Will ground
            self.grounding_count += 1
            self.rephrase_count = 0
            self.expected_replies = [{"category": "grounding-answer"},
                                     {"category": "informing"}]
        elif (  isinstance(last_action, ActionUtter)
            and last_action.name == "ask-rephrase"):
            # Will request a rephrase
            self.rephrase_count += 1
            self.grounding_count = 0
            self.expected_replies = [{"category": "triggering"}]
        elif isinstance(last_action, ActionAskSlotValue):
            # Will ask for the value of a slot
            self.reset_counts()
            self.expected_replies = [{"category": "informing"}]  # TODO: this should be more precise (get the intent name)
        else:
            # Will utter anything else
            self.reset_counts()

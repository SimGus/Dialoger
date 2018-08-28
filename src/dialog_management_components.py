#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .config import get_slots_descriptions


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

class Context(object):
    """
    Represents the current context of the dialog, i.e. which goal is currently
    being worked on, which slots are filled and their value and what kind of
    intent is expected in the next utterance of the user.
    """
    def __init__(self, goal):
        # (Goal) -> ()
        self.current_goal = goal
        self.expected_intents = []

        slots_descriptions = get_slots_descriptions()
        self.slots = {slot_name: Slot(slot_name,
                                      slots_descriptions[slot_name]["type"])
                      for slot_name in slots_descriptions}

    def set_slot(self, slot_name, value):
        if slot_name not in self.slots:
            raise AttributeError("Tried to set the value of a non-existing slot ("+
                                 slot_name+").")
        self.slots[slot_name].set(value)
    def is_set(self, slot_name):
        if slot_name not in self.slots:
            raise AttributeError("Tried to get the state of a non-existing slot ("+
                                 slot_name+").")
        return self.slots[slot_name].is_set()

    def expect(self, expected_intents):
        # ([str]) -> ()
        if not isinstance(expected_intents, list):
            raise AttributeError("Tried to change the expected intents to a "+
                                 "variable that was not a list ("+
                                 expected_intents+").")
        self.expected_intents = expected_intents
    def expecting(self, intent):
        # (str) -> (bool)
        return (intent in self.expected_intents)


class Goal(object):
    """
    Represents a goal with an identifier, a triggering intent, slots to fill
    (mandatory and optional filling) and actions to take when the goal is met.

    Note: mandatory slot MUST be in order for the goal to be met; optional slots
    may be filled and may be in some cases upgraded to mandatory; all other
    slots shouldn't get filled and may not be upgraded to mandatory for this
    goal. Mandatory slots cannot be downgraded.
    """
    def __init__(self, name, triggering_intent, mandatory_slots=[],
                 optional_slots=[], actions=[]):
        # (str, str, [str], [str], [str]) -> ()
        if name is None:
            raise AttributeError("Tried to create a goal without a name.")
        if triggering_intent is None:
            raise AttributeError("Tried to create a goal without a triggering intent.")
        self.name = name
        self.triggering_intent = triggering_intent
        self.mandatory_slots = mandatory_slots
        self.optional_slots = optional_slots
        self.actions = actions

    def is_met(self, context):
        for slot_name in self.mandatory_slots:
            if not context.is_set(slot_name):
                return False
        return True

    def make_mandatory(self, slot_name):
        """
        Upgrades a slot from optional to mandatory.
        If the slot wasn't optional, raises an `AttributeError`.
        """
        if slot_name not in self.optional_slots:
            raise AttributeError("Tried to make mandatory a slot that was "+
                                 "not optional in goal '"+self.name+"' (slot: '"+
                                 slot_name+"'.")
        self.optional_slots.remove(slot_name)
        self.mandatory_slots.append(slot_name)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from copy import deepcopy

from . import config as cfg
from .actions import Action as action, confirmation_requests as confirm, ActionAskSlotValue as ask


class Slot(object):
    """Represents a slot, with a type and a value (empty or not)"""
    def __init__(self, name, type):
        self.name = name
        self.type_str = type
        if type == "categorical":
            self.type = str
            import sys
            if sys.version_info[0] == 2:
                self.type = unicode
        elif type == "integer":
            self.type = int
        elif type == "float" or type == "percentage":  # TODO: there is a percentage that has value 'not fully' somewhere (that will crash everything)
            self.type = float
        elif type == "bool":
            self.type = bool
        else:
            raise AttributeError("Unexpected slot type: "+str(type))
        self.value = None  # str

    def set(self, value):
        # (str) -> ()
        try:
            # Check that the value is in a format that seems coherent with the announced type
            # NOTE: the casted value is NOT used as the value since using slot
            #       values is not a hard constraint (for example 'not 100%'
            #       could be logical in a percentage), hence the warning.
            #       `self.value` is thus a `str` (`unicode` in Python 2).
            casted_value = self.type(value)
        except ValueError:
            import warnings
            warnings.warn("Tried to set a slot of type "+self.type.__name__+
                          " to a value of another type ('"+str(value)+"': "+
                          type(value).__name__+")")
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
    goals_descriptions = cfg.get_goals_descriptions()

    def __init__(self, name):
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
        If the slot wasn't optional, raises an `KeyError`.
        """
        if slot_name not in self.optional_slots:
            raise KeyError("Tried to make mandatory a slot that was "+
                           "not optional in goal '"+self.name+"' (slot: '"+
                           slot_name+"'.")
        self.optional_slots.remove(slot_name)
        self.mandatory_slots.append(slot_name)


    def __eq__(self, other):
        """
        Two goals are considered equal if they have the same name,
        not the same state.
        """
        if not isinstance(other, Goal):
            return NotImplemented
        return (self.name == other.name)
    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "Goal: "+self.name


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
    MAX_CONSECUTIVE_MISUNDERSTANDING_MSG = 3
    MAX_CONSECUTIVE_ASK_REPHRASE = 2
    MAX_CONSECUTIVE_ASK_CONFIRMATION = 1

    def __init__(self, goal):
        # (Goal) -> ()
        self.current_goal = deepcopy(goal)
        self.expected_replies = []  # contains a list of possible replies (broad: intent categories or precise: intent names)

        self.intents_descriptions = cfg.get_intents_descriptions()
        slots_descriptions = cfg.get_slots_descriptions()
        self.slots = {slot_name: Slot(slot_name,
                                      slots_descriptions[slot_name]["type"])
                      for slot_name in slots_descriptions}

        self._confirmation_request_count = 0
        self._rephrase_count = 0
        self._consecutive_misunderstanding_count = 0

        self.potential_new_goal = None
        self.entity_pending_for_confirmation = None  # stores a dict: {"slot-name": str, "value": str}

        self.init()
    def init(self):
        """Puts `self` in its initial state."""
        self.expected_replies = [{"category": "triggering"}]

    #========== Slot related methods ===============
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
    def reset_slots(self):
        slots_descriptions = cfg.get_slots_descriptions()
        self.slots = {slot_name: Slot(slot_name,
                                      slots_descriptions[slot_name]["type"])
                      for slot_name in slots_descriptions}

    def get_lacking_slot_names(self):
        """
        Returns the name of an empty mandatory slot in the current goal
        or `None` if there was none.
        """
        for slot_name in self.current_goal.mandatory_slots:
            if not self.is_set(slot_name):
                return slot_name
        return None

    def promote_slot(self, slot_name):
        """
        Promotes the optional slot named `slot_name` to 'mandatory'.
        Returns `True` if the slot was promoted and `False` otherwise (the slot
        was not optional). Raises a `KeyError` if the slot does not exist.
        """
        if slot_name not in self.slots:
            raise KeyError("Tried to promote an inexistant slot from "+
                           "'optional' to 'mandatory' ('"+slot_name+"').")
        try:
            self.current_goal.make_mandatory(slot_name)
            return True
        except KeyError:
            return False

    #========== Expected message related methods ============
    #---------- Type of message ------------
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
        # TODO: expected answer class?
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

    #----------- Pending new goal confirmation ------------
    def set_potential_new_goal(self, goal):
        """
        Stores a potential upcoming goal.
        If the next user reply is `confirm`, the current goal should be changed
        to the upcoming goal. Drops all pending entities.
        """
        # (str) -> ()
        self.potential_new_goal = deepcopy(goal)
        self.entity_pending_for_confirmation = None
    def new_goal_confirmed(self):
        """
        Sets the current goal to the potential new goal (user confirmed) and
        forgets everything that has been done before.
        """  # TODO: it might be interesting to keep some info?
        if self.potential_new_goal is not None:
            self.current_goal = self.potential_new_goal
            self.potential_new_goal = None
            # Forget everything else
            self.reset_slots()
            self.reset_counts()
            self.discard_pending_entity()
    def discard_potential_new_goal(self):
        """Drops the potential new goal (user denied wanting to change)."""
        self.potential_new_goal = None

    #----------- Pending entity confimation ------------
    def set_entity_pending_for_confirmation(self, slot_name, value):
        """
        Informs the context that the bot is waiting for
        a confirmation of the entity for slot `slot_name` with value `value`.
        """
        self.entity_pending_for_confirmation = {"slot-name": slot_name,
                                                "value": value}
    def pending_entity_confirmed(self):
        """
        Informs the context that the entity pending to be confirmed
        was confirmed by the user.
        """
        if self.entity_pending_for_confirmation is not None:
            self.set_slot(self.entity_pending_for_confirmation["slot-name"],
                          self.entity_pending_for_confirmation["value"])
    def discard_pending_entity(self):
        """
        Drops the entity pending for confirmation
        (it was denied by the user).
        """
        self.entity_pending_for_confirmation = None

    #=========== Rephrasing permisions related methods ============
    def reset_counts(self):
        self._confirmation_request_count = 0
        self._rephrase_count = 0
        self._consecutive_misunderstanding_count = 0

    def may_ask_confirmation(self):
        """Returns `True` if the bot is allowed to ask for a confirmation."""
        return (    self._confirmation_request_count < Context.MAX_CONSECUTIVE_ASK_CONFIRMATION
                and self._consecutive_misunderstanding_count < Context.MAX_CONSECUTIVE_MISUNDERSTANDING_MSG)
    def may_ask_rephrase(self):
        """Returns `True` if the bot is allowed to ask for a rephrase."""
        return (    self._rephrase_count < Context.MAX_CONSECUTIVE_ASK_REPHRASE
                and self._consecutive_misunderstanding_count < Context.MAX_CONSECUTIVE_MISUNDERSTANDING_MSG)

    #=========== Updaters ==================
    def update_from(self, next_actions):
        """Using the list of actions the bot is going to take, update the context."""
        # To update it is needed to only look at the last action,
        # since the bot issues messages one by one
        last_action = next_actions[-1]
        if isinstance(last_action, confirm.ActionUtterConfirmIntent):
            # Will request a confirmation for an intent (yes/no)
            self._consecutive_misunderstanding_count += 1
            self._confirmation_request_count += 1
            self._rephrase_count = 0
            self.expected_replies = [{"category": "confirmation-request-answer"}]
        elif isinstance(last_action, confirm.ActionUtterConfirmEntity):
            # Will request a confirmation for an entity (yes/no/correction)
            self._consecutive_misunderstanding_count += 1
            self._confirmation_request_count += 1
            self._rephrase_count = 0
            self.expected_replies = [{"category": "confirmation-request-answer"},
                                     {"category": "informing"}]
        elif (  isinstance(last_action, action.ActionUtter)
            and last_action.name == "ask-rephrase"):
            # Will request a rephrase
            self._consecutive_misunderstanding_count += 1
            self._rephrase_count += 1
            self._confirmation_request_count = 0
            # expected replies stay the same (as the user should rephrase)
        elif isinstance(last_action, ask.ActionAskSlotValue):
            # Will ask for the value of a slot
            self.reset_counts()
            self.expected_replies = last_action.get_expected_replies()  # TODO: this should be more precise (get the intent name)
        else:
            # Will utter anything else
            self.reset_counts()
            self.expected_replies = [{"category": "triggering"}]
        print("updated context: confcount: "+str(self._confirmation_request_count))
        print("\trephrase count: "+str(self._rephrase_count))
        print("\texpecting: "+str(self.expected_replies))

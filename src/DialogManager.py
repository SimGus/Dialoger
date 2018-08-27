#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import *
from .dialog_management_components import *
from .config import get_goals


class DialogManager(object):
    """
    Given the intents and (correct) entities found in the user's messages,
    decides what to do/answer. This is a goal-based dialog manager.
    Relies on a configuration of goals and on a stack of conversation contexts.
    """
    # Thresholds on the confidence values:
    # Any intent/entity with confidence < hard threshold is considered as not understood;
    # any intent/entity with confidence < soft threshold is grounded.
    # Those values are different when treating an expected message or an unexpected one.
    EXPECTED_HARD_THRESHOLD = 0.4
    EXPECTED_SOFT_THRESHOLD = 0.7
    UNEXPECTED_HARD_THRESHOLD = 0.5
    UNEXPECTED_SOFT_THRESHOLD = 0.8

    def __init__(self):
        self.build_goals_dict()
        self.context = Context(self.goals_by_trigger["_init"])
    def build_goals_dict(self):
        """
        Using a list of the goals, creates a dict containing all the goals
        indexed using their triggering intents.
        """
        self.goals_by_trigger = {goal.triggering_intent: goal
                                 for goal in get_goals()}

    def handle_user_msg(self, intent_and_entities):
        """
        Called when a new user message is issued, handles the message
        (represented as a dict with an intent and one or several optional
        entities) and returns the action/utterance to do.
        Takes into account the current context and the confidences values to
        make a decision.
        """
        combinatorial_entities_confidence = self.compute_final_confidence()
        combinatorial_intent_confidence = \
            mean(intent_and_entities["intent"]["confidence"],
                 combinatorial_entities_confidence)

    def compute_final_confidence(self, intent_and_entities):
        """
        Computes a new value of confidence based on the confidence of
        understanding the intent and which entities were detected
        in the message (with their confidences).
        Returns the value of the confidence it has in all the entity values.
        The formulae will be:
        M = sum_x(confidence)/sum_x(1) for x in mandatory slots
        P = sum_x(confidence)/sum_x(1) for x in optional slots
        U = sum_x(confidence)/sum_x(1) for x in unexpected slots
        C_OM = log_2(M+1)/(log_2(P+1)+1) + 1/(2-log_2(P)) is the confidence in the expected slots found
        F = C_MO/(log_2(U+1)+1) is the final confidence the bot has about the entities given the intent it understood
        The final confidence in the intent will then be the mean value of this and the intent confidence
        (not computed by this method).
        """
        # TODO

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from numpy import log2

from utils import *
from .dialog_management_components import *
from .config import get_goals_descriptions, get_intents_descriptions


def make_goals_list():
    goals_descriptions = get_goals_descriptions()
    return [Goal(goal_name) for goal_name in goals_descriptions]


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
        self.goals_by_trigger = {goal.triggering_intent: goal
                                 for goal in make_goals_list()}

        self.context = Context(self.goals_by_trigger["_init"])
        self.intents_descriptions = get_intents_descriptions()


    def handle_user_msg(self, intent_and_entities):
        """
        Called when a new user message is issued, handles the message
        (represented as a dict with an intent and one or several optional
        entities) and returns the action/utterance to do.
        Takes into account the current context and the confidences values to
        make a decision.
        """
        # (...) -> ([Action])
        understood_intent = intent_and_entities["intent"]
        if self.context.is_expecting(understood_intent["name"]):
            print("expected")
            cumulative_intent_confidence = \
                self.compute_final_confidence(intent_and_entities,
                                              understood_intent["name"])
            printDBG("confidence: "+str(understood_intent["confidence"])+" -> "+
                     str(cumulative_intent_confidence))
            # Confident in your understanding
            if cumulative_intent_confidence > DialogManager.EXPECTED_SOFT_THRESHOLD:
                print("confident")
                return self.pursue_goal()
            # Doubtful in your understanding
            elif cumulative_intent_confidence > DialogManager.EXPECTED_HARD_THRESHOLD:
                print("doubtful")
                return ["ground"]  # TODO
            # Not understood
            else:
                print("not understood")
                return ["rephrase"]
        else:
            print("unexpected")

    def pursue_goal(self):
        """
        If the goal is met, returns the actions to take;
        otherwise, returns an action of asking for missing information.
        """
        # () -> ([str])  # TODO: should they be objects rather than str?
        # Check for missing information
        lacking_slot_name = self.context.get_lacking_info()
        if lacking_slot_name is None:  # Goal is met
            printDBG("Goal "+self.context.current_goal.name+" is met")
            # TODO: check if some slots need to be upgraded before returning
            return ["actions"]  # TODO
        else:  # Goal is not met
            printDBG("Goal "+self.context.current_goal.name+" is not met")
            return [lacking_slot_name]


    def compute_final_confidence(self, intent_and_entities, intent_name):
        """
        Computes a new value of confidence for the intent `intent_name`
        based on the confidence of understanding this intent and
        on which entities were detected in the message (with their confidences).
        This is used to compute the probability that the understood intent is
        correct.
        The formulae will be:
            M = sum_x(confidence)/sum_x(1) for x in mandatory slots
            P = sum_x(confidence)/sum_x(1) for x in optional slots
            U = sum_x(confidence)/sum_x(1) for x in unexpected slots
            C_MO = log_2(M+1)/(log_2(0.8*P+1)+1) + 1/(2-log_2(P))
                is the confidence in the expected slots found
            F = C_MO/(log_2(U+1)+1)
                is the final confidence the bot has about the entities
                given the intent it understood
        The final confidence in the intent will then be the weighted mean value
        of this and the intent confidence and will be returned by this method.
        """
        # ({"intent": {"name": str, "confidence": float},
        # "entities": [{"confidence": float, ...}],
        # "intent_ranking": [{"name": str, "confidence": float}],
        # "text": str}) -> (float)
        # NOTE: the input format is shown here: http://rasa.com/docs/nlu/0.12.3/tutorial/
        relevant_goal = None
        if intent_name not in self.goals_by_trigger:
            # This intent doesn't trigger any goals
            if intent_and_entities["intent"]["name"] == intent_name:
                return intent_and_entities["intent"]["confidence"]
            intent_confidence = None
            for intent in intent_and_entities["intent_ranking"]:
                if intent["name"] == intent_name:
                    intent_confidence = intent["confidence"]
                    break
            return intent_confidence
        # TODO: check what the expected slots where
        else:
            relevant_goal = self.goals_by_trigger[intent_name]

        M_sum_confidences = 0
        M_count = 0
        for detected_entity in intent_and_entities["entities"]:
            if detected_entity["entity"] in relevant_goal.mandatory_slots:
                M_count += 1
                M_sum_confidences += detected_entity["confidence"]
        M = 0.0
        if M_count > 0:
            M = float(M_sum_confidences)/float(M_count)

        P_sum_confidences = 0
        P_count = 0
        for detected_entity in intent_and_entities["entities"]:
            if detected_entity["entity"] in relevant_goal.optional_slots:
                P_count += 1
                P_sum_confidences += detected_entity["confidence"]
        P = 0.0
        if P_count > 0:
            P = float(P_sum_confidences)/float(P_count)

        U_sum_confidences = 0
        U_count = 0
        for detected_entity in intent_and_entities["entities"]:
            if (    detected_entity["entity"] not in relevant_goal.mandatory_slots
                and detected_entity["entity"] not in relevant_goal.optional_slots):
                U_count += 1
                U_sum_confidences += detected_entity["confidence"]
        U = 0.0
        if U_count > 0:
            U = float(U_sum_confidences)/float(U_count)

        C_MO = log2(M+1)/(log2(0.8*P+1)+1)
        if P != 0:
            C_MO += 1/(2-log2(P))
        F = C_MO/(log2(U+1)+1)

        intent_confidence = None
        for intent in intent_and_entities["intent_ranking"]:
            if intent["name"] == intent_name:
                intent_confidence = intent["confidence"]
                break

        printDBG("F = "+str(F))
        answer = (2*intent_confidence + F)/3.0  # weighted average
        if answer > 1.0:
            answer = 1.0
        return answer

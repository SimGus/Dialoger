#!/usr/bin/env python
# -*- coding: utf-8 -*-

from numpy import log2
from copy import deepcopy

from utils import *
from . import bot_utils
from .dialog_management_components import *
from . import config as cfg
from . import entity_checker

from .actions.ActionFactory import ActionFactory
from .actions import confirmation_requests as confirm
from .actions.Action import ActionUtter


def make_goals_list():
    goals_descriptions = cfg.get_goals_descriptions()
    return [Goal(goal_name) for goal_name in goals_descriptions]


class DialogManager(object):
    """
    Given the intents and (correct) entities found in the user's messages,
    decides what to do/answer. This is a goal-based dialog manager.
    Relies on a configuration of goals and on a stack of conversation contexts.
    """
    # Thresholds on the confidence values:
    # Any intent/entity with confidence < hard threshold is considered as not understood;
    # any intent/entity with confidence < soft threshold gets asked for confirmation.
    # Those values are different when treating an expected message or an unexpected one.
    EXPECTED_HARD_THRESHOLD = 0.4
    EXPECTED_SOFT_THRESHOLD = 0.7
    UNEXPECTED_HARD_THRESHOLD = 0.5
    UNEXPECTED_SOFT_THRESHOLD = 0.8

    RESET_MSG = "restart"

    def __init__(self):
        self.goals_by_trigger = {goal.triggering_intent: goal
                                 for goal in make_goals_list()}  # should always be deepcopied into a new context (never used as is)

        self.context = Context(self.goals_by_trigger["_init"])
        self.intents_descriptions = cfg.get_intents_descriptions()
        self.slots_descriptions = cfg.get_slots_descriptions()

        self.action_factory = ActionFactory(cfg.get_utterances_templates())


    def reset(self):
        """Reset `self` to its initial state."""
        self.context = Context(self.goals_by_trigger["_init"])


    def manage_user_msg(self, intent_and_entities):
        """
        Called when a new user message is issued, handles the message
        (represented as a dict with an intent and one or several optional
        entities) and returns the action/utterance to do.
        Takes into account the current context and the confidences values to
        make a decision.
        """
        # (...) -> ([Action])
        # Manage restarting of the bot by the user
        if intent_and_entities["text"] == DialogManager.RESET_MSG:
            self.reset()
            return self.pursue_goal()

        # Correct correctable entities and ditch others
        intent_and_entities["entities"] = \
            entity_checker.check_entities_val(intent_and_entities["entities"])

        # Build actions
        actions = self.formulate_answer(intent_and_entities)
        actions =  self.filter_repeated_confirmation_and_rephrase(actions)
        self.context.update_from(actions)
        return actions

    def formulate_answer(self, intent_and_entities):
        """
        Using the context and what's been understood from the last user message,
        tries to formulate an answer (may that be asking a rephrase, a
        confirmation request about what was unclear, asking for additionnal info
        or answering a question) and returns this list of actions.
        """
        # (...) -> ([Action])
        understood_intent = intent_and_entities["intent"]
        cumulative_intent_confidence = \
            self.compute_final_confidence(intent_and_entities,
                                          understood_intent["name"])
        printDBG("confidence: "+str(understood_intent["confidence"])+" -> "+
                 str(cumulative_intent_confidence))
        # User message was expected
        if self.context.is_expecting(understood_intent["name"]):
            print("expected")
            # Confident in your understanding
            if cumulative_intent_confidence > DialogManager.EXPECTED_SOFT_THRESHOLD:
                print("confident: "+understood_intent["name"])
                if bot_utils.is_triggering(understood_intent["name"]):
                    # Change goal and formulate answer
                    next_goal = self.goals_by_trigger[understood_intent["name"]]
                    print("New goal: "+str(next_goal))
                    print("GOAL'S MANDATORY SLOTS: "+str(next_goal.mandatory_slots))
                    # change the context (forget the current slot values)
                    self.context = Context(next_goal)
                elif bot_utils.is_informing(understood_intent["name"]):
                    pass
                elif bot_utils.is_confirmation_request_answer(understood_intent["name"]):
                    if self.context.potential_new_goal is not None:
                        # User confirmed
                        if bot_utils.is_confirming(understood_intent["name"]):
                            self.context.new_goal_confirmed()
                        # User denied
                        else:
                            self.context.discard_potential_new_goal()
                            if self.context.current_goal.is_met(self.context):
                                # Get back to the initial goal
                                self.reset()
                            # Otherwise continue asking for info about the current goal, you certainly misunderstood
                        return self.pursue_goal()
                    else:
                        if bot_utils.is_confirming(understood_intent["name"]):
                            self.context.pending_entity_confirmed()
                        else:
                            self.context.discard_pending_entity()
                    return self.pursue_goal()
                else:
                    # Unreachable
                    print("unreachable (not understood then)")
                    rephrase_utterance = self.action_factory \
                                             .new_utterance("ask-rephrase",
                                                            self.context)
                    return [rephrase_utterance]

                slot_confirmation_request_action = \
                    self.fill_slots(intent_and_entities, msg_was_expected=True)
                if slot_confirmation_request_action is not None:
                    return [slot_confirmation_request_action]
                return self.pursue_goal()
            # Doubtful in your understanding
            elif cumulative_intent_confidence > DialogManager.EXPECTED_HARD_THRESHOLD:
                print("doubtful")
                if bot_utils.is_triggering(understood_intent["name"]):
                    print("potential new goal")
                    self.context.set_potential_new_goal(
                        self.goals_by_trigger[understood_intent["name"]]
                    )
                    confirmation_utterance = self.action_factory \
                                                .new_confirmation_request_utterance(
                                                    understood_intent["name"],
                                                    self.context
                                                )
                    return [confirmation_utterance]
                elif bot_utils.is_informing(understood_intent["name"]):
                    # Consider you understood well
                    print("not sure but ok")
                    slot_confirmation_request_action = \
                        self.fill_slots(intent_and_entities, msg_was_expected=True)
                    if slot_confirmation_request_action is not None:
                        return [slot_confirmation_request_action]
                    return self.pursue_goal()
                elif bot_utils.is_confirmation_request_answer(understood_intent["name"]):
                    # Consider you understood well
                    if self.context.potential_new_goal is not None:
                        # User confirmed
                        if bot_utils.is_confirming(understood_intent["name"]):
                            self.context.new_goal_confirmed()
                        # User denied
                        else:
                            if self.context.current_goal.is_met(self.context):
                                # Get back to the initial goal
                                self.reset()
                            # Otherwise continue asking for info about the current goal, you certainly misunderstood
                        return self.pursue_goal()
                    else:
                        if bot_utils.is_confirming(understood_intent["name"]):
                            self.context.pending_entity_confirmed()
                        else:
                            self.context.discard_pending_entity()
                    return self.pursue_goal()
            # Not understood
            else:
                print("not understood")
                rephrase_utterance = \
                    self.action_factory.new_utterance("ask-rephrase",
                                                      self.context)
                return [rephrase_utterance]
        # User message was not expected
        else:
            print("unexpected")
            # Confident in your understanding
            if cumulative_intent_confidence > DialogManager.UNEXPECTED_SOFT_THRESHOLD:
                if bot_utils.is_triggering(understood_intent["name"]):
                    print("potential new goal")
                    self.context.set_potential_new_goal(
                        self.goals_by_trigger[understood_intent["name"]]
                    )
                    confirmation_utterance = self.action_factory \
                                                .new_confirmation_request_utterance(
                                                    understood_intent["name"],
                                                    self.context
                                                )
                    return [confirmation_utterance]
                elif self.context.potential_new_goal is not None:
                    print("potential new goal again?")
                    # Try to confirm the new goal again
                    confirmation_utterance = self.action_factory \
                                                .new_confirmation_request_utterance(
                                                    understood_intent["name"],
                                                    self.context
                                                )
                    return [confirmation_utterance]
                elif bot_utils.is_informing(understood_intent["name"]):
                    # Consider you understood well
                    print("not sure but ok")
                    slot_confirmation_request_action = \
                        self.fill_slots(intent_and_entities, msg_was_expected=True)
                    if slot_confirmation_request_action is not None:
                        return [slot_confirmation_request_action]
                    return self.pursue_goal()
                else:
                    print("not really understood")
                    rephrase_utterance = \
                        self.action_factory.new_utterance("ask-rephrase",
                                                          self.context)
                    return [rephrase_utterance]
            # Not understood # TODO: should it do something else when hard_threshold < confidence < soft_threshold
            else:
                print("not understood")
                rephrase_utterance = \
                    self.action_factory.new_utterance("ask-rephrase",
                                                      self.context)
                return [rephrase_utterance]

    def pursue_goal(self):
        """
        If the goal is met, returns the actions to take;
        otherwise, returns an action of asking for missing information.
        This will never return grouding or rephrasing utterances.
        """
        # () -> ([str])  # TODO: should they be objects rather than str?
        # Check for missing information
        lacking_slot_name = self.context.get_lacking_slot_names()
        if lacking_slot_name is None:  # All mandatory slots are filled
            actions = [self.action_factory.new_action(action_name,
                                                      deepcopy(self.context))
                       for action_name in self.context.current_goal.actions]
            # Check if some slots need to be promoted from 'optional' to 'mandatory'
            promotion_happened = False
            for action in actions:
                promotion_happened = action.promote_needed_optional_slots(self.context)
                if promotion_happened:
                    lacking_slot_name = self.context.get_lacking_slot_names()
                    break
            if lacking_slot_name is None:  # Goal is met
                printDBG("Goal "+self.context.current_goal.name+" is met")
                return actions
        # Goal is not met
        printDBG("Goal "+self.context.current_goal.name+" is not met")
        return [self.action_factory
                .new_ask_for_slot_utterance(lacking_slot_name,
                                            deepcopy(self.context))]

    def fill_slots(self, intent_and_entities, msg_was_expected=False):
        """
        Fills the slots with the entities found and asks for a confirmation request
        in case one of them is not clearly understood, i.e. it returns an
        `ActionUtterConfirmEntity`. Returns `None` if everything was clear.
        `msg_was_expected` is a boolean set to `True` if the message was
        expected: the confidence threshold will thus be higher.
        """
        def choose_which_to_request_confirmation(entity1, entity2):
            if entity1 is None:
                return entity2
            mandatory_slots = self.context.current_goal.mandatory_slots
            if entity1 in mandatory_slots and entity2 not in mandatory_slots:
                return entity1
            elif entity1 not in mandatory_slots and entity2 in mandatory_slots:
                return entity2
            elif entity1["confidence"] >= entity2["confidence"]:
                return entity1
            return entity2

        hard_threshold = DialogManager.UNEXPECTED_HARD_THRESHOLD
        soft_threshold = DialogManager.UNEXPECTED_SOFT_THRESHOLD
        if msg_was_expected:
            hard_threshold = DialogManager.EXPECTED_HARD_THRESHOLD
            soft_threshold = DialogManager.EXPECTED_SOFT_THRESHOLD
        entity_to_confirm = None
        for entity in intent_and_entities["entities"]:
            if entity["confidence"] >= soft_threshold:
                self.context.set_slot(entity["entity"], entity["value"])
            elif (    entity["confidence"] >= hard_threshold
                and entity["confidence"] < soft_threshold):
                entity_to_confirm = \
                    choose_which_to_request_confirmation(entity_to_confirm,
                                                         entity)
            # otherwise discard the entity
        if entity_to_confirm is not None:
            slot_name = entity_to_confirm["entity"]
            value = entity_to_confirm["value"]
            self.context.set_entity_pending_for_confirmation(slot_name, value)
            return self.action_factory \
                       .new_confirmation_request_utterance((slot_name, value),
                                                self.context)
        return None

    def filter_repeated_confirmation_and_rephrase(self, actions):
        """
        Using the history of the conversation, avoids repeating the same
        confirmation request or a rephrase asking twice in a row. Returns the action to do
        instead.
        If the bot wants to utter a confirmation request to the answer
        to a previous confirmation request, it should rather ask a rephrase.
        If the bot wants to ask a rephrase a third time in a row, it should
        rather ask to start the conversation over.
        """
        # ([Action]) -> ([Action])
        utterance_action = actions[-1] # TODO: this might be improved
        if (   isinstance(utterance_action, confirm.ActionUtterConfirmIntent)
            or isinstance(utterance_action, confirm.ActionUtterConfirmEntity)):
            # Wanted to request confirmation
            if self.context.may_ask_confirmation():
                return actions
            else:
                return [self.action_factory.new_utterance("ask-rephrase",
                                                          self.context)]
        elif (  isinstance(utterance_action, ActionUtter)
            and utterance_action.name == "ask-rephrase"):
            # Wanted to ask to rephrase
            if self.context.may_ask_rephrase():
                return actions
            else:
                return [self.action_factory.new_utterance("ask-start-over",
                                                          self.context)]
        # Neither a confirmation or rephrase request
        return actions

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
        """ # TODO: problem if there is no slots to fill
        # ({"intent": {"name": str, "confidence": float},
        # "entities": [{"confidence": float, ...}],
        # "intent_ranking": [{"name": str, "confidence": float}],
        # "text": str}) -> (float)
        # NOTE: the input format is shown here: http://rasa.com/docs/nlu/0.12.3/tutorial/
        intent_description = None
        intent_descriptions = cfg.get_intents_descriptions()
        if intent_name not in intent_descriptions:
            raise RuntimeError("The bot understood an inexistant intent ('"+
                               intent_name+"').")
        else:
            intent_description = intent_descriptions[intent_name]

        print("expected: "+str(intent_description["expected-entities"]))
        print("allowed: "+str(intent_description["allowed-entities"]))
        C_MO = None
        if (    len(intent_description["expected-entities"]) <= 0
            and len(intent_description["allowed-entities"]) <= 0):
            print("no expected or allowed entities => no correction")
            return intent_and_entities["intent"]["confidence"]
        elif len(intent_description["expected-entities"]) <= 0:
            print("no expected entities")
            P_sum_confidences = 0
            P_count = 0
            for detected_entity in intent_and_entities["entities"]:
                if detected_entity["entity"] in intent_description["allowed-entities"]:
                    P_count += 1
                    P_sum_confidences += detected_entity["confidence"]
            P = 0.0
            if P_count > 0:
                P = float(P_sum_confidences)/float(P_count)

            C_MO = (log2(P+1)/2.0)+1

            print("\tP = "+str(P)+"\tC_MO = "+str(C_MO))
        else:
            print("expected entities and allowed entities")
            M_sum_confidences = 0
            M_count = 0
            for detected_entity in intent_and_entities["entities"]:
                if detected_entity["entity"] in intent_description["expected-entities"]:
                    M_count += 1
                    M_sum_confidences += detected_entity["confidence"]
            M = 0.0
            if M_count > 0:
                M = float(M_sum_confidences)/float(M_count)

            P_sum_confidences = 0
            P_count = 0
            for detected_entity in intent_and_entities["entities"]:
                if detected_entity["entity"] in intent_description["allowed-entities"]:
                    P_count += 1
                    P_sum_confidences += detected_entity["confidence"]
            P = 0.0
            if P_count > 0:
                P = float(P_sum_confidences)/float(P_count)

            C_MO = log2(M+1)/(log2(0.8*P+1)+1)
            if P != 0:
                C_MO += 1/(2-log2(P))

            print("\tM = "+str(M)+"\tP = "+str(P)+"\tC_MO = "+str(C_MO))

        U_sum_confidences = 0
        U_count = 0
        for detected_entity in intent_and_entities["entities"]:
            if (    detected_entity["entity"] not in intent_description["expected-entities"]
                and detected_entity["entity"] not in intent_description["allowed-entities"]):
                U_count += 1
                U_sum_confidences += detected_entity["confidence"]
        U = 0.0
        if U_count > 0:
            U = float(U_sum_confidences)/float(U_count)

        print("\tU = "+str(U))

        F = C_MO/(log2(U+1)+1)

        intent_confidence = None
        for intent in intent_and_entities["intent_ranking"]:
            if intent["name"] == intent_name:
                intent_confidence = intent["confidence"]
                break

        print("\tF = "+str(F))
        answer = (4*intent_confidence + 3*F)/7.0  # weighted average
        if answer > 1.0:
            answer = 1.0
        return answer

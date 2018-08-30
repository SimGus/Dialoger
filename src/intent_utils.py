#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file contains utility methods for managing intents as they are
returned by Rasa NLU (dicts unclear to handle).
"""

from .config import get_intents_descriptions

def is_triggering(intent_name):
    intents_descriptions = get_intents_descriptions()
    return (intents_descriptions[intent_name]["category"] == "triggering")
def is_informing(intent_name):
    intents_descriptions = get_intents_descriptions()
    return (intents_descriptions[intent_name]["category"] == "informing")
def is_confirmation_request_answer(intent_name):
    intents_descriptions = get_intents_descriptions()
    return (intents_descriptions[intent_name]["category"] == \
            "confirmation-request-answer")

def is_confirming(intent_name):
    if not is_confirmation_request_answer(intent_name):
        raise ValueError("Tried to check if an intent was confirming something "+
                         "while the intent wasn't a confirmation request answer: '"+
                         intent_name+"'.")
    intents_descriptions = get_intents_descriptions()
    return (intents_descriptions[intent_name]["sub-category"] == "confirm")
def is_denying(intent_name):
    if not is_confirmation_request_answer(intent_name):
        raise ValueError("Tried to check if an intent was denying something "+
                         "while the intent wasn't a confirmation request answer: '"+
                         intent_name+"'.")
    intents_descriptions = get_intents_descriptions()
    return (intents_descriptions[intent_name]["sub-category"] == "deny")

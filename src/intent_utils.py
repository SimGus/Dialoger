#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This file contains utility methods for managing intents as they are
returned by Rasa NLU (dicts unclear to handle).
"""

from .config import get_intents_descriptions

def is_triggering(intent_name):
    intents_descriptions = get_intents_descriptions()
    return (intents_descriptions[intent_name] == "triggering")
def is_informing(intent_name):
    intents_descriptions = get_intents_descriptions()
    return (intents_descriptions[intent_name] == "informing")
def is_grounding_answer(intent_name):
    intents_descriptions = get_intents_descriptions()
    return (intents_descriptions[intent_name] == "grounding-answer")

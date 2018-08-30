#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import yaml
import copy
import re

from utils import *
from .config import get_slots_descriptions


regex_int = re.compile(r"[0-9]+")
regex_float = re.compile(r"[0-9]+(\.[0-9]+)?")  # NOTE: finds percentages as well


def check_entities_val(entities):
    """
    Checks that the entities have a value that is
    in the list of accepted entities for the current client.
    Returns a list with only correct entity values. (TODO maybe just mark incorrect entities?)
    """
    slots_descriptions = get_slots_descriptions()

    correct_entities = []
    for entity in entities:
        corrected = False
        current_slot_name = entity["entity"]
        if current_slot_name not in slots_descriptions:
            raise ValueError("Unexpected entity type: "+str(entity["entity"]))
        # Has the NLU module understood the entity correctly?
        if entity["value"].strip() in slots_descriptions[current_slot_name]:
            correct_entities.append(
                build_correct_entity(entity, entity["value"].strip(), 0.01)
            )
            corrected = True
            continue
        # Can you find the closest match?  # TODO should rather use the edit distance and look if the closest is not too far
        for accepted_val in slots_descriptions[current_slot_name]["values"]:
            if accepted_val in entity["value"]:
                correct_entities.append(
                    build_correct_entity(entity, accepted_val, 0.1)
                )
                corrected = True
                break
            # TODO other checks
        if corrected:
            continue
        # Try to find numbers in the entity if the slot type is numerical
        if slots_descriptions[current_slot_name]["type"] == "integer":
            try:
                found_str = regex_int.search(entity["value"]).group()
                found_val = int(found_str)
                correct_entities.append(
                    build_correct_entity(entity, found_str, 0.2)
                )
                corrected = True
            except (AttributeError, ValueError):
                pass
        elif slots_descriptions[current_slot_name]["type"] == "float":
            try:
                found_str = regex_float.search(entity["value"]).group()
                found_val = float(found_str)
                correct_entities.append(
                    build_correct_entity(entity, found_str, 0.2)
                )
                corrected = True
            except (AttributeError, ValueError):
                pass
        elif slots_descriptions[current_slot_name]["type"] == "percentage":
            try:
                found_str = regex_float.search(entity["value"]).group()
                found_val = float(found_str)
                if found_val > 1.0:
                    found_str = str(found_val/100)  # transform percents into floats
                correct_entities.append(
                    build_correct_entity(entity, found_str, 0.2)
                )
                corrected = True
            except (AttributeError, ValueError):
                pass

        if not corrected:
            printDBG("Discarding incorrect entity '"+entity["value"]+"' for '"+current_slot_name+"'")
    return correct_entities


def build_correct_entity(entity, correct_val, confidence_drop=0.10):
    printDBG("Correcting '"+entity["value"]+"' -> '"+correct_val+"'")
    correct_entity = copy.deepcopy(entity)
    correct_entity["value"] = correct_val
    correct_entity["confidence"] -= confidence_drop
    return correct_entity


def levenshtein_edit_distance(s1, s2):
    """
    Returns the edit distance between the two strings.
    source: https://stackoverflow.com/questions/2460177/edit-distance-in-python
    """ # TODO: use later
    # NOTE: two strings can be considered the same (typos) when their distance is < len/50
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

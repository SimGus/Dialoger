#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import yaml
import copy
import re

from utils import *
from . import config as cfg


regex_int = re.compile(r"[0-9]+")
regex_float = re.compile(r"[0-9]+(\.[0-9]+)?")  # NOTE: finds percentages as well

_MAX_EDIT_DISTANCE_FACTOR = 5.0*1/50.0
# NOTE: two strings can be considered the same (typos)
#       when their distance is < max(len)/50.
#       => Here we consider that you can add/remove a word or two and still have
#          the same string.

def check_entities_val(entities):
    """
    Checks that the entities have a value that is
    in the list of accepted entities for the current client.
    Returns a list with only correct entity values. (TODO maybe just mark incorrect entities?)
    """
    slots_descriptions = cfg.get_slots_descriptions()
    slot_values_synonyms = cfg.get_slots_values_synonyms()

    correct_entities = []
    for entity in entities:
        corrected = False
        current_slot_name = entity["entity"]
        current_str = entity["value"]
        if current_slot_name not in slots_descriptions:
            raise ValueError("Unexpected entity type: "+str(entity["entity"]))

        # Has the NLU module understood the entity correctly?
        if current_str.strip() in slots_descriptions[current_slot_name]:
            correct_entities.append(
                _build_correct_entity(entity, current_str.strip(), 0.0)
            )
            corrected = True
            continue
        # Can you find the closest match?
        for accepted_val in slots_descriptions[current_slot_name]["values"]:
            edit_distance = _levenshtein_edit_distance(accepted_val,
                                                               current_str)
            (len1, len2) = (len(accepted_val), len(current_str))
            if edit_distance <= _MAX_EDIT_DISTANCE_FACTOR*max(len1, len2):
                correct_entities.append(_build_correct_entity(entity,
                                                              accepted_val,
                                                              0.02*edit_distance))
                corrected = True
                print("found "+current_str+" ~= "+accepted_val)
                break
            if (   accepted_val.lower() in current_str
                or accepted_val.upper() in current_str):
                correct_entities.append(_build_correct_entity(entity,
                                                              accepted_val,
                                                              min(0.1, 0.02*edit_distance)))
                corrected = True
                break
            # OPTIMIZE: other checks
        if corrected:
            continue
        # Try to find numbers in the entity if the slot type is numerical
        if slots_descriptions[current_slot_name]["type"] == "integer":
            try:
                found_str = regex_int.search(current_str).group()
                found_val = int(found_str)
                correct_entities.append(
                    _build_correct_entity(entity, found_str, 0.08)
                )
                corrected = True
            except (AttributeError, ValueError):
                pass
        elif slots_descriptions[current_slot_name]["type"] == "float":
            try:
                found_str = regex_float.search(current_str).group()
                found_val = float(found_str)
                correct_entities.append(
                    _build_correct_entity(entity, found_str, 0.08)
                )
                corrected = True
            except (AttributeError, ValueError):
                pass
        elif slots_descriptions[current_slot_name]["type"] == "percentage":
            try:
                found_str = regex_float.search(current_str).group()
                found_val = float(found_str)
                if found_val > 1.0:
                    found_str = str(found_val/100)  # transform percents into floats
                correct_entities.append(
                    _build_correct_entity(entity, found_str, 0.08)
                )
                corrected = True
            except (AttributeError, ValueError):
                pass
        if corrected:
            continue

        # Look into synonyms
        for slot_value in slot_values_synonyms:
            if slot_value in slots_descriptions[current_slot_name]["values"]:
                for syn in slot_values_synonyms[slot_value]:
                    edit_distance = \
                        _levenshtein_edit_distance(syn, current_str)
                    (len1, len2) = (len(syn), len(current_str))
                    if edit_distance <= _MAX_EDIT_DISTANCE_FACTOR*max(len1, len2):
                        correct_entities.append(_build_correct_entity(entity,
                                                                      slot_value,
                                                                      0.02*edit_distance))
                        corrected = True
                        print("found "+current_str+" ~= "+syn)
                        break
                    if (   syn.lower() in current_str
                        or syn.upper() in current_str):
                        correct_entities.append(_build_correct_entity(entity,
                                                                      slot_value,
                                                                      min(0.1, 0.02*edit_distance)))
                        corrected = True
                        break
                if corrected:
                    break
        if corrected:
            continue

        if not corrected:
            printDBG("Discarding incorrect entity '"+current_str+"' for '"+current_slot_name+"'")
    return correct_entities


def _build_correct_entity(entity, correct_val, confidence_drop=0.10):
    printDBG("Correcting '"+entity["value"]+"' -> '"+correct_val+
             "' (confidence drop: "+str(confidence_drop)+")")
    correct_entity = copy.deepcopy(entity)
    correct_entity["value"] = correct_val
    correct_entity["confidence"] -= confidence_drop
    return correct_entity


def _levenshtein_edit_distance(s1, s2):
    """
    Returns the edit distance between the two strings.
    source: https://stackoverflow.com/questions/2460177/edit-distance-in-python
    """
    # OPTIMIZE: this takes a very long time (seeing how many i call it)
    if len(s1) > len(s2):
        s1, s2 = s2, s1
    (len1, len2) = (len(s1), len(s2))
    current_threshold_distance = _MAX_EDIT_DISTANCE_FACTOR*len2
    if len2-len1 > current_threshold_distance:
        return current_threshold_distance+1

    distances = range(len1 + 1)
    for (i2, c2) in enumerate(s2):
        distances_ = [i2+1]
        for (i1, c1) in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

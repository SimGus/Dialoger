#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .Action import Action

class ActionNoAPI(Action):
    """
    This action will be used instead of custom actions in case
    the API of MPlanner is not accessible (i.e. the script was ran from outside
    MPlanner) to prevent the script crashing when trying to import the API.
    """
    def promote_needed_optional_slots(self, context_to_update):
        from random import randint
        if bool(randint(0,1)):
            if len(context_to_update.current_goal.optional_slots) > 0:
                optional_slot_name = \
                    context_to_update.current_goal.optional_slots[0]
                return context_to_update.promote_slot(optional_slot_name)
        return False

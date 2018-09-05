#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bot.actions.Action import Action, BotErrorMessage

import Phi


class ActionLookUpMachinePlanning(Action):
    def promote_needed_optional_slots(self, context_to_update):
        """
        From the context `context_to_update`, checks whether there is missing
        information in order to be able to answer the question. Here
        specifically, checks whether there is a need for a production line
        number to know which production line the user is talking about.
        Returns `False` if there is no need to promote the slot to 'mandatory'
        and `True` if it needs to and was promoted in the context.
        """
        prod_line_name = context_to_update.get_slot_value("production_line")
        if prod_line_name is None:
            # Unreachable
            raise RuntimeError("Tried to check if optional slots needed a "+
                               "promotion while all mandarory slots where not "+
                               "filled ('production_line' missing).")

        if Phi.findLine(prod_line_name) is None:
            return context_to_update.promote_slot("line_number")
        return False

    def run(self):
        """
        Fetches and returns the information so that the bot can tell the user:
            - The number of time buckets during which the line is used at least
              once
            - The total number of time buckets
            - The percentage of the time the line is used
            - ... TODO?
        """
        line = self._get_relevant_line()
        if line is None:
            line_name = self._get_line_name()
            print("Line "+str(line_name)+" not found")
            return BotErrorMessage("I <b>couldn't find the line "+str(line_name)+
                                   "</b>. I'm afraid it doesn't exist.")
        print("Found line "+str(line.getName()))

        nb_buckets = Phi.getNumberOfTimeBuckets()
        nb_buckets_of_use = 0
        utilization_percent = 0.0
        for i in range(nb_buckets):
            current_utilization = line.getUtilisation(Phi.getTimeBucket(i))
            if current_utilization > 0.0:
                nb_buckets_of_use += 1
                utilization_percent += current_utilization
        utilization_percent *= 100/nb_buckets

        info = {
            "total-number-buckets": nb_buckets,
            "number-buckets-of-use": nb_buckets_of_use,
            "utilization-percentage": utilization_percent,
        }
        print("finally: "+str(info))
        return info

    def _get_line_name(self):
        """Finds, caches and returns the line name."""
        # () -> (str)
        if not hasattr(self, "_line_name"):
            line_name = self.context.get_slot_value("production_line")
            if line_name is None:
                # Unreachable
                raise RuntimeError("Tried to get the name of a production line "+
                                   "while this slot wasn't filled yet. This should "+
                                   "not have happened.")
            line_nb = self.context.get_slot_value("line_number")
            if line_nb is not None:
                line_name += str(line_nb)
            self._line_name = line_name
        return self._line_name
    def _get_relevant_line(self):
        """
        Finds the line the user talked about and returns it.
        Returns `None` if the line wasn't found.
        """
        # () -> (Phi.Line)
        line_name = self._get_line_name()
        print("looking for "+str(line_name))
        return Phi.findLine(line_name)

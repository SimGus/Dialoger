#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import float_equal
from bot.actions.Action import Action, BotErrorMessage

import Phi


class ActionLookUpWhyMachineUtilization(Action):
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
        Checks several things about the requested line to try and analyze why a
        line wouldn't be used at its full potential.
        """
        line = self._get_relevant_line()
        if line is None:
            line_name = self._get_line_name()
            print("Line "+str(line_name)+" not found")
            return BotErrorMessage("I <b>couldn't find the line "+str(line_name)+
                                   "</b>. I'm afraid it doesn't exist.")
        print("Found line "+str(line.getName()))

        # Check if the user believes the line is not used as it really is.
        # Results of this checking will be used to display or not a "actually"
        # in the bots answer.
        print("checking user's beliefs")
        user_utilization_ratio = self.context.get_slot_value("utilization")
        try:
            user_utilization_ratio = float(user_utilization_ratio)
        except Exception:
            user_utilization_ratio = None

        precision_adverb = None
        if (    user_utilization_ratio is not None
            and not float_equal(user_utilization_ratio*100,
                                self._get_real_utilization(line))):
            precision_adverb = "actually"

        # Check 0: is the line saturated?
        print("doing check #0")
        if float_equal(self._get_real_utilization(line), 100.0):
            print("Line "+str(self._get_line_name())+" is saturated")
            return {
                "fetched-utilization": 100.0,
                "precision-adverb": precision_adverb,
                "machine-utilization-explanation":
                    "which means it is <b>saturated</b>. The point is to "+
                    "fulfill a maximum number of orders, right?",
            }

        # Check 1: is all demand planned?
        print("doing check #1")
        nb_orders = Phi.getNumOrders()
        horizon_date = \
            Phi.getTimeBucket(Phi.getNumberOfTimeBuckets()-1).getEndDate()
        nb_orders_planned = 0
        orders = []
        unplanned_orders = []
        nb_orders_forbidden = 0
        for i in range(nb_orders):
            current_order = Phi.getOrder(i)
            orders.append(current_order)
            completion_date = current_order.getCompletionDate()
            if completion_date < horizon_date:  # QUESTION: should the horizon date be included?
                nb_orders_planned += 1
            else:
                unplanned_orders.append(current_order)
            if current_order.isForbidden():
                nb_orders_forbidden += 1

        if nb_orders - nb_orders_forbidden == nb_orders_planned:
            return {
                "fetched-utilization": self._get_real_utilization(line),
                "precision-adverb": precision_adverb,
                "machine-utilization-explanation":
                    "because <b>all the orders are planned</b>: "+
                    str(nb_orders_planned)+" out of "+str(nb_orders)+" are "+
                    "planned (where "+str(nb_orders_forbidden)+" orders are "+
                    "forbidden)",
            }

        # Check 2: is there a part of the unplanned demand that actually goes through this line?
        print("doing check #2")
        nb_buckets = Phi.getNumberOfTimeBuckets()
        unplanned_goes_through_line = False
        for order in unplanned_orders:
            current_product_family = order.getFinalPF()  # QUESTION: what to do if this returns `None`?
            if (    current_product_family is not None
                and line.isPFUsed(current_product_family) != 0):
                unplanned_goes_through_line = True
                break
        if not unplanned_goes_through_line:
            return {
                "fetched-utilization": self._get_real_utilization(line),
                "precision-adverb": precision_adverb,
                "machine-utilization-explanation":
                    "because it seems there is <b>no unplanned orders "+
                    "that need to go through this production line</b>",
            }


        # Check 3: is it possible to plan the unplanned orders within the horizon (are they already late)?
        print("doing check #3")
        orders_already_late = False
        for order in orders:
            due_date = order.getDueDate()
            if due_date is not None and due_date > horizon_date:
                orders_already_late = True
                break
        if orders_already_late:
            return {
                "fetched-utilization": self._get_real_utilization(line),
                "precision-adverb": precision_adverb,
                "machine-utilization-explanation":
                    "because <b>some orders have their due date after the time "+
                    "horizon</b> (the end time of the last time bucket), "+
                    "therefore the solver decided not to plan them",
            }

        # Check 4: are there other lines which are saturated over the horizon?
        print("doing check #4")
        other_saturated_line = None
        nb_lines = Phi.getNumberOfLines()  # TODO: in the API you also have another function named `getNumLines()` which seems to do the same thing, you might want to look into this.
        for i in range(nb_lines):
            other_line = Phi.getLine(i)
            if (    other_line is not None
                and self._is_line_saturated(other_line)):
                # Check whether an unplanned goes through this line
                for order in unplanned_orders:
                    current_product_family = order.getFinalPF()  # QUESTION: what to do if this returns `None`?
                    if (    current_product_family is not None
                        and line.isPFUsed(current_product_family) != 0
                        and other_line.isPFUsed(current_product_family) != 0):
                        # current unplanned order should go through both lines
                            other_saturated_line = other_line
                            break
                if other_saturated_line is not None:
                    break
        if other_saturated_line is not None:
            return {
                "fetched-utilization": self._get_real_utilization(line),
                "precision-adverb": precision_adverb,
                "machine-utilization-explanation":
                    "because <b>production line "+
                    str(other_saturated_line.getName())+" is saturated</b> "+
                    "which prevents some of the unplanned commands that go "+
                    "through line "+str(line.getName())+" to be completed. "+
                    "The solver does not plan such commands completely",
            }

        # Check 5: are there any limiting flow constraints on the line?
        print("doing check #5")
        # Check 6: are there any stock max constraints on some successive lines?
        print("doing check #6")

        return {
            "fetched-utilization": self._get_real_utilization(line),
            "precision-adverb": precision_adverb,
            "machine-utilization-explanation":
                "but I <b>couldn't find out why</b>.\nIf after analyzing the "+
                "plan, you still can't understand why this is the case, don't "+
                "hesitate to <b>call a consultant</b>",
        }

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

    def _get_real_utilization(self, line):
        """
        Finds out, caches and returns the utilization of a machine as a
        percentage (i.e. a ratio multiplied by 100).
        """
        # () -> (float)
        if not hasattr(self, "real_utilization"):
            nb_buckets = Phi.getNumberOfTimeBuckets()
            utilization_ratio = 0.0
            for i in range(nb_buckets):
                utilization_ratio += line.getUtilisation(Phi.getTimeBucket(i))
            utilization_ratio /= float(nb_buckets)
            self.real_utilization = 100.0*utilization_ratio
        return self.real_utilization

    @staticmethod
    def _is_line_saturated(line):
        """Returns `True` if the production line `line` is saturated."""
        pass

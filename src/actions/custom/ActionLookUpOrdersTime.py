#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bot.actions.Action import Action, BotErrorMessage

import Phi


class ActionLookUpOrdersTime(Action):
    def promote_needed_optional_slots(self, context_to_update):
        return False

    def run(self):
        """
        Fetches the information (and returns it) so that the bot can tell the
        user:
            - the number of orders that have the characteristic they asked
              (here, is it completed on time or late?)
            - the total number of orders there are
            - the number of orders that are forbidden
            - a small list of the names of the first few orders that have the
              characteristic
        """
        print("beginning to run action lookup orders based on completion time")

        # ~List all the orders that are late
        if self.context.get_slot_value("filter_time") == "late":
            filter_late_orders = True
        # ~List all the orders that are on time
        else:  # slot value should be "on time" (always)
            filter_late_orders = False

        nb_orders = Phi.getNumOrders()
        nb_forbidden_orders = 0
        filtered_orders = []
        for i in range(nb_orders):
            current_order = Phi.getOrder(i)
            planned_lateness_buckets = \
                current_order.getPlannedBucketsOfLateness()
            if filter_late_orders and planned_lateness_buckets > 0:
                filtered_orders.append(current_order)
            elif not filter_late_orders and planned_lateness_buckets <= 0:
                filtered_orders.append(current_order)
            if current_order.isForbidden():
                nb_forbidden_orders += 1

        nb_filtered_orders = len(filtered_orders)
        if filter_late_orders:
            nb_late_orders = nb_filtered_orders
        else:
            nb_late_orders = nb_orders-nb_filtered_orders
        if nb_filtered_orders > 0:
            if nb_filtered_orders <= 3:
                small_list_orders_str = "Here is a list of their names:"
                for order in filtered_orders:
                    small_list_orders_str += "\n- "+str(order.getName())
            else:
                small_list_orders_str = "Here are the names of the first 3 ones:"
                for i in range(3):
                    small_list_orders_str += "\n- "+str(filtered_orders[i].getName())
                small_list_orders_str += "\n- ..."
        else:
            small_list_orders_str = None
        if nb_late_orders > 0:
            percentage_late_orders_forbidden = \
                100.0 * (float(nb_forbidden_orders)/float(nb_late_orders))
        else:
            percentage_late_orders_forbidden = 0.0

        info = {
            "total-number-orders": nb_orders,
            "number-filtered-orders": len(filtered_orders),
            "orders-list": small_list_orders_str,
            "number-forbidden-orders": nb_forbidden_orders,
            "percentage-late-orders-forbidden": percentage_late_orders_forbidden,
        }
        print("finally "+str(info))
        return info

#!/usr/bin/env python
# -*- coding: utf-8 -*-

def mean(a, b):
    return float(a)+float(b)/2.0

def choose(list):
    """Same as `random.choice(list)` but doesn't throw an error if list is empty"""
    # ([anything]) -> anything or None
    list_len = len(list)
    if list_len <= 0:
        return None
    return list[randint(0, list_len-1)]

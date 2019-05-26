#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np

class Line():
    """
        Line class for storing the points found by the Hough Transform and
        fitting them to a 1st order polynomial.
    """

    def __init__(self, frameDimensions, color):
        self.frameDimensions = frameDimensions
        self.color = color
        self.w = frameDimensions[0]
        self.h = frameDimensions[1]
        self.x = []
        self.y = []
        self.poly = None

    def add(self, x0, y0, x1, y1):
        """
            Adds a set of points to the arrays used to create the fit.
        """
        self.x.extend([x0, x1])
        self.y.extend([y0, y1])

    def clear(self):
        """
            Clears all points for the arrays.
        """
        self.x = []
        self.y = []

    def fit(self):
        """
            Fits the data to a first order polynomial. Returns the fitted polynomial
            as a function of the -y coordinate, ie. x = f(y) = m * y + b.

        """
        if len(self.x) > 0 and len(self.y) > 0:
            self.poly = np.poly1d(np.polyfit(self.y, self.x, deg=1))
        else:
            self.poly = None    
        return self.poly

    def eval(self, y0, y1):
        """
            Evaluate the fitted polynomial to a set of -y coordinates in order to obtain
            points for drawing a line.
        """
        y0Px = int(self.h * y0)
        y1Px = int(self.h * y1)
        if self.poly:
            return [
                int(self.poly(y0Px)),
                y0Px,
                int(self.poly(y1Px)),
                y1Px
            ]
        else:
            return [0, y0Px, 0, y1Px]
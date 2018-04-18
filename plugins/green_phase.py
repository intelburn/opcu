from opc import color_utils
import random

@color_utils.pixel_source
class GreenPhase(color_utils.PixelGenerator):
    def pixel_color(self, t, ii):
        """Compute the color of a given pixel.

        t: time in seconds since the program started.
        ii: which pixel this is, starting at 0
        coord: the (x, y, z) position of the pixel as a tuple
        n_pixels: the total number of pixels

        Returns an (r, g, b) tuple in the range 0-255

        """
        x, y, z = self._layout[ii]

        w1 = color_utils.cos(t, period=17)
        #r = g = b = color_utils.cos(x+y, offset=w1, period=1, minn=0.0, maxx=0.4)
        #(r,g,b) = color_utils.contrast((r,g,b), 0.5, 4)
        r = 0
        b = 0
        g = color_utils.cos(x+y+z, offset=t/4, period=1, minn=0.0, maxx=1.0)
        return (r, g, b)

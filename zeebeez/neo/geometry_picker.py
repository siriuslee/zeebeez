import matplotlib.pyplot as plt
import numpy as np
from roman import toRoman


def plot(type="8x2", *args, **kwargs):

    if type == "8x2":
        return plot_8x2(*args, **kwargs)

def plot_8x2(startswith=1):

    base_geom = np.array([[7, 8],
                          [6, 9],
                          [5, 10],
                          [4, 11],
                          [3, 12], 
                          [2, 13],
                          [1, 14],
                          [0, 15]])

    nrows, ncols = base_geom.shape

    coordinates = {"LB": base_geom + startswith,
                   "LT": np.flipud(base_geom) + startswith,
                   "RT": np.flipud(np.fliplr(base_geom)) + startswith,
                   "RB": np.fliplr(base_geom) + startswith}

    fig = plt.figure(facecolor="white")

    axsel = AxesSelector()
    axs = []

    for ii, coord in enumerate(["LB", "LT", "RT", "RB"]):
        ax = fig.add_subplot(2, 2, ii + 1)
        ax.text(.05, .95, toRoman(ii + 1), transform=ax.transAxes, horizontalalignment="left", verticalalignment="top", fontsize=20, color=[.7, .7, .7], fontweight="bold")
        ax.set_label(coord)
        e_numbers = coordinates[coord]
        for row in xrange(nrows):
            for col in xrange(ncols):
                enum = e_numbers[row, col]
                ax.text(col, nrows - row, "%d"%enum, horizontalalignment="center", verticalalignment="center")
        ax.set_ylim([0, 9])
        ax.set_xlim([-1, 2])
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color([0.7, 0.7, 0.7])

        axsel.append(ax, e_numbers)
        axs.append(ax)

    # Add descriptive texts
    x = axs[0].get_position().x1
    y = np.mean([axs[0].get_position().y0, axs[2].get_position().y1])
    fig.text(x, y, "$\leftarrow$ Medial", verticalalignment="center", horizontalalignment="right", fontsize=20)

    x = axs[1].get_position().x0
    fig.text(x, y, "Lateral $\\rightarrow$", verticalalignment="center", horizontalalignment="left", fontsize=20)

    x = np.mean([axs[0].get_position().x1, axs[1].get_position().x0])
    y = axs[0].get_position().y0
    fig.text(x, y, "Rostral $\\rightarrow$", verticalalignment="bottom", horizontalalignment="center", rotation=90, fontsize=20)

    y = axs[2].get_position().y1
    fig.text(x, y, "$\leftarrow$ Caudal", verticalalignment="top", horizontalalignment="center", rotation=90, fontsize=20)
    plt.show()

    axsel.connect()
    axsel.wait_until()
    axsel.disconnect()
    chosen = axsel.chosen
    # plt.close(plt.gcf()) # Some real bullshit going on here... but it's close

    # del axsel

    return chosen


class AxesSelector(object):

    def __init__(self, axes=[], coords=[]):

        if type(axes) is not list:
            axes = [axes]
        if type(coords) is not list:
            coords = [coords]

        self.axes = axes
        self.coords = coords

    def append(self, ax, coord):
        
        ax.set_picker(5)
        self.axes.append(ax)
        self.coords.append(coord)

    def connect(self):
        
        self.cid_pick = self.axes[0].figure.canvas.mpl_connect('pick_event', self.on_pick)

    def disconnect(self):
        
        self.axes[0].figure.canvas.mpl_disconnect(self.cid_pick)
        # plt.close(self.axes[0].figure)        
        # self.axes = []
        # self.coords = []

    def on_pick(self, event):

        print "There are currently %d axes in the list" % len(self.axes)

        if event.mouseevent.inaxes not in self.axes:
            return

        print "Selection occured!"
        ind = self.axes.index(event.mouseevent.inaxes)
        self.chosen = self.coords[ind]

    def wait_until(self):

        plt.waitforbuttonpress()





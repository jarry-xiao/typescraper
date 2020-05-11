import os
import json
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable


class Keyboard:

    def __init__(self, cfg):
        with open(cfg) as json_file:
            self.cfg = json.load(json_file)
        self.img_file = os.path.join(os.path.dirname(cfg), self.cfg["image"])
        self.shape = (self.cfg["x"], self.cfg["y"])
        self.colormap = np.zeros((*self.shape, 3))
        self.heatmap = np.zeros(self.shape)
        self.key_map = self.__make_map()
        self.left_shift = self.cfg["left_shift"] 
        self.right_shift = self.cfg["right_shift"] 

    def __reset_heatmap(self):
        self.heatmap = np.zeros(self.shape)
        
    def __reset_colormap(self):
        self.colormap = np.zeros((*self.shape, 3))

    def __make_map(self):
        char_map = {}
        width = self.cfg["width"]
        height = self.cfg["height"]
        for row in self.cfg["char_data"]:
            r, c = row[0], row[1]
            chars = row[2]
            for i, char in enumerate(chars.split(' ')):
                char_map[char] = ((r, c + i*width), (r+height, c + (i+1)*width))
        for key, locs in self.cfg["char_map"].items():
            x1, y1, x2, y2 = locs
            char_map[key] = ((x1, y1), (x2, y2))
        return char_map
    
    def get_cells(self, e):
        row_range = range(e[0][0], e[1][0])
        col_range = range(e[0][1], e[1][1])
        return [(r,c) for r in row_range for c in col_range]
    
    def get_cells_for_char(self, char):
        try:
            char_map = self.key_map
            key = [x for x in char_map.keys() if char in x][0]
            cell_edges = char_map[key]
            cells = self.get_cells(cell_edges)
            if char in self.left_shift:
                cells += self.get_cells(char_map['lshift'])
            elif char in self.right_shift:
                cells += self.get_cells(char_map['rshift'])
            return cells
        except Exception:
            raise KeyError(f'{char} not found in the map')
        
    def __fill_heatmap(self, char_dict):
        for char, freq in char_dict.items():
            self.__fill_freq(char, freq)
        self.heatmap /= np.sum(self.heatmap)
        
    def __fill_freq(self, char, freq):
        cells = self.get_cells_for_char(char)
        for r,c in cells:
            self.heatmap[r][c] += freq 
            
    def fill_color(self, char, color):
        cells = self.get_cells_for_char(char)
        value = np.array(matplotlib.colors.to_rgb(color))
        for r,c in cells:
            self.colormap[r][c] += value 

    def scale(self, char, factor):
        if char in ("lshift", "rshift"):
            cells = self.get_cells(self.key_map[char])
        else:
            key = [x for x in self.key_map.keys() if char in x][0]
            cell_edges = self.key_map[key]
            cells = self.get_cells(cell_edges)
        for r, c in cells:
            self.heatmap[r][c] *= factor

    def make_heatmap(self, data, alpha=0.8, save=False, op_path=None, **kwargs):
        self.__reset_heatmap()
        normalize = True
        if isinstance(data, dict):
            self.__fill_heatmap(data)
        elif isinstance(data, str):
            chars, counts = np.unique([ch for ch in data], return_counts=True)
            char_dict = dict(zip(chars, counts))
            self.__fill_heatmap(char_dict)
        else:
            print('Datatype not handled yet')
            raise Exception("Unknown datatype, can not make image")
        self.show_heatmap(alpha, save, op_path, **kwargs)

    def show_heatmap(self, alpha=0.8, save=False, op_path=None, **kwargs):
        self.start_plot()
        divider = make_axes_locatable(self.ax)
        cax = divider.append_axes('right', size='5%', pad=0.05)
        im = self.ax.imshow(
            self.heatmap,
            zorder=1,
            alpha=alpha,
            **kwargs,
        )
        self.fig.colorbar(im, cax=cax, orientation='vertical')
        self.finish_plot(save=save, op_path=op_path)
        
    def make_colormap(self, alpha=0.5, save=False, op_path=None, **kwargs):
        self.start_plot()
        a_map = (np.sum(self.colormap, axis=2) > 0) * alpha
        data = np.dstack([self.colormap, a_map])
        self.ax.imshow(
            data,
            zorder=1,
            **kwargs,
        )
        self.finish_plot(save=save, op_path=op_path)
        self.__reset_colormap()
        
    def start_plot(self):
        self.fig, self.ax = plt.subplots()
        plt.xticks([])
        plt.yticks([])
        plt.axis('off')
        self.fig.set_size_inches(15, 45)
    
    def finish_plot(self, save=False, op_path=None):
        img = plt.imread(self.img_file) 
        self.ax.imshow(img, zorder=0, extent=[0, self.shape[1], self.shape[0], 0])
        if save:
            self.save(op_path)
        
    def save(self, op_path, save_dir='.', dpi=265, **kwargs):
        self.fig.savefig(
            op_path,
            dpi=dpi,
            pad_inches=0,
            transparent=True,
            bbox_inches='tight',
            **kwargs
        )

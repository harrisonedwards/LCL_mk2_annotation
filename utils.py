import argparse
from sys import getsizeof
import cv2, os
import scipy
from skimage import measure
import numpy as np
import argparse
from skimage.util import img_as_ubyte


def get_unique_names(directory):
    files = os.listdir(directory)
    fl = []
    for f in files:
        if '.yml' not in f and 'stitched' not in f and '.jpg' not in f and os.path.isfile(os.path.join(directory, f)):
            fl.append(f.rpartition('-')[0])
    return set(fl), files


def get_all_paths_and_channels(directory, selection, fl):
    paths, channels = [], []
    for f in fl:
        if f.rpartition('-')[0] == selection:
            paths.append(os.path.join(directory, f))
            channels.append(f.rpartition('-')[2].rpartition('.tif')[0])
    return dict(zip(channels, paths))


def main():
    unique_names, fl = get_unique_names()
    s = '\n'.join(unique_names)
    selection = input(f'Please type the file set to annotate from:\n{s}\n')
    channels = get_all_paths_and_channels(selection, fl)
    print(channels)

def get_objs(img, thresh_val):
    '''
    takes a dapi image and returns list of slices with objects above the thresh_val
    '''
    # clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    # img = clahe.apply(img)
    _,thresh1 = cv2.threshold(img, thresh_val, 255, cv2.THRESH_BINARY)
    blobs_labels = measure.label(thresh1.astype(np.uint8), background=0)
    objs = scipy.ndimage.find_objects(blobs_labels)
    return objs

def draw_objects(img, objs, color):
    '''
    takes a BF image and draws boxes over the objects in it, then returns it
    '''
    for obj in objs:
        cv2.rectangle(img,(obj[1].start,obj[0].start),(obj[1].stop,obj[0].stop), color, 3)
    return img

def get_obj_channels(d, channelThreshValues=None):
    '''
    takes a well image directory and returns the boxes for all of the fluorescence channels
    '''
    obj_channels = {}
    tempDict = {}
    color_name = ['red', 'green', 'blue']
    i = 0
    for f in os.listdir(d):
        if '.tif' in f and 'Default' not in f:
            name = f.split('-')[-1].split('.tif')[0]
            print('processing:', name, 'to be boxed in', color_name[i])
            img = cv2.imread(os.path.join(d, f), 0)
            if channelThreshValues != None:
                # threshold on the values we have input
                objs = get_objs(img, channelThreshValues[name])
                tempDict[name] = channelThreshValues[name]
            else:
                # otherwise threshold on the preset, and return it
                objs = get_objs(img, np.median(img) + 3 * scipy.stats.iqr(img))
                tempDict[name] = np.median(img) + 3 * scipy.stats.iqr(img)
            obj_channels[name] = objs
            i += 1
    return obj_channels, tempDict

def draw_all_channels(d):
    '''
    returns an image with all fluorescence channel boxes drawn on it
    '''
    obj_channels = get_obj_channels(d)
    for f in os.listdir(d):
        if '.tif' in f and 'Default' in f:
            img = cv2.imread(os.path.join(d,f))
    for i,[k,v] in enumerate(obj_channels.items()):
        colors = [0,0,0]
        colors[i] = 255
        img = draw_objects(img, obj_channels[k], colors)
    return img

def validateDirectoryFormat(dir):
    for f in os.listdir(dir):
        if '.yml' in f:
            return True
    return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Annotator for the LCL mk 2 system.')
    parser.add_argument('directory', help='Directory where the files to be annotated are stored.')
    args = parser.parse_args()
    main()

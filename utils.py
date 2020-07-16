import os
import argparse


def get_unique_names(directory):
    files = os.listdir(directory)
    fl = []
    for f in files:
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Annotator for the LCL mk 2 system.')
    parser.add_argument('directory', help='Directory where the files to be annotated are stored.')
    args = parser.parse_args()
    main()

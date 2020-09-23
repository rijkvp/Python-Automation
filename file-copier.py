import os
import shutil
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "--source", "-s", help="Set the source folder", required=True)
parser.add_argument("--destination", "-d",
                    help="Set the destination folder", required=True)
parser.add_argument("--hidden_files", "-hf",
                    help="Detect hidden files", action='store_true')
parser.add_argument("--only_search", "-os",
                    help="Only search for new files, don't copy them", action='store_true')

args = parser.parse_args()

source_folder = args.source
destination_folder = args.destination

ignore_hidden = not args.hidden_files
only_seach = args.only_search

print("Seaching for new files in '{}' wich aren't already in '{}'..\n".format(
    source_folder, destination_folder))


class FileInfo:
    def __init__(self, subdir, filename):
        self.subdir = subdir
        self.filename = filename

    def __eq__(self, other):
        return self.subdir == other.subdir and self.filename == other.filename

    def get_relative(self):
        return self.subdir + self.filename


source_files = []
destination_files = []
new_files = []

for root, dirs, files in os.walk(source_folder):
    if ignore_hidden:
        files = [f for f in files if not f[0] == '.']
        dirs[:] = [d for d in dirs if not d[0] == '.']

    subdir = str(root)[len(source_folder):] + os.sep
    for name in files:
        source_files.append(FileInfo(subdir, name))

for root, dirs, files in os.walk(destination_folder):
    if ignore_hidden:
        files = [f for f in files if not f[0] == '.']
        dirs[:] = [d for d in dirs if not d[0] == '.']

    subdir = str(root)[len(destination_folder):] + os.sep
    for name in files:
        destination_files.append(FileInfo(subdir, name))

for file in source_files:
    if file not in destination_files:
        print("{} is new!".format(file.get_relative()))
        new_files.append(file)

if not only_seach:
    if (len(new_files) == 0):
        print("Already up-to-date! No new files found!")
    else:
        print("\nCopying {} new file(s)..".format(len(new_files)))
        for file in new_files:
            source = source_folder + file.get_relative()
            destination = destination_folder + file.get_relative()
            dest_directory = destination_folder + file.subdir
            print("Copying {} to {}..".format(
                source, destination))
            os.makedirs(os.path.dirname(dest_directory), exist_ok=True)
            shutil.copy2(source, destination)
else:
    if (len(new_files) == 0):
        print("No new files found!")
    else:
        print("Found {} new files!".format(len(new_files)))

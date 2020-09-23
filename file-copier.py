import os
import shutil
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "--source", "-s", help="set the source folder", required=True)
parser.add_argument("--destination", "-d",
                    help="set the destination folder", required=True)

args = parser.parse_args()

source_folder = args.source
destination_folder = args.destination

print("Seaching for new files in '{}' wich aren't in '{}'..\n".format(
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
    subdir = str(root)[len(source_folder):] + os.sep
    for name in files:
        source_files.append(FileInfo(subdir, name))

for root, dirs, files in os.walk(destination_folder):
    subdir = str(root)[len(destination_folder):] + os.sep
    for name in files:
        destination_files.append(FileInfo(subdir, name))
for file in source_files:
    if file not in destination_files:
        print("{} is new!".format(file.get_relative()))
        new_files.append(file)
if (len(new_files) == 0):
    print("Already up-to-date! No new files found!")
else:
    print("\nCopying {} new files..".format(len(new_files)))
    for file in new_files:
        source = source_folder + file.get_relative()
        destination = destination_folder + file.get_relative()
        dest_directory = destination_folder + file.subdir
        print("Copying {} to {}..".format(
            source, destination))
        os.makedirs(os.path.dirname(dest_directory), exist_ok=True)
        shutil.copy2(source, destination)
